#!/usr/bin/env python3
r"""
tid_doa_compare.py — side-by-side comparison of tid_doa.py run logs

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.1.0  Real, live-testing-found problem: a runs/ directory
          genuinely accumulates dozens of logs across weeks of real
          use -- confirmed directly against 52 real, accumulated run
          logs -- and the original wide, side-by-side table doesn't
          degrade gracefully at that scale, it becomes flatly
          unreadable well before that point (52 columns wide is not a
          usable terminal display by any measure). Added a compact,
          one-row-per-run view (timestamp/speed/heading/diagnostics/
          station-count/method) that kicks in automatically above 4
          runs, with a note suggesting how to narrow down to the
          detailed side-by-side view instead. Also fixed a column-
          width bug found in the same testing pass: the timestamp
          field's width exactly matched the timestamp string's own
          length (18 chars), leaving zero buffer space and causing
          the next column to run directly into it with no visible
          gap. Verified: both the small-count (side-by-side,
          unchanged) and large-count (new compact) paths tested
          directly, including colorize=True for the new compact view.
  v1.0.0  Initial release. Item #5 from the post-v4.1.0 UX priority
          list (PROJECT_STATE #111): tid_doa.py already writes a
          self-contained, timestamped run log per invocation (CLI or
          GUI, since the dashboard's own extraction pipeline calls
          tid_doa.py the same way) -- but comparing two runs meant
          manually re-reading old terminal output or opening two log
          files side by side by hand. This is the CLI-native version
          of that comparison; a GUI "pin runs to compare" feature
          would be a visual wrapper around this exact same
          parse-and-diff logic, not a separate implementation.

Why a separate script rather than a new tid_doa.py flag: comparing
already-written run logs is a genuinely different mode of operation
than running a new DOA computation from a station config -- tid_doa.py's
own CLI already assumes a single config-file argument throughout, and
overloading that with an entirely different input shape (multiple log
paths, no config at all) would have complicated its argparse setup for
a use case that doesn't touch any of its own computation logic. This
script only ever reads what tid_doa.py already wrote; it recomputes
nothing.

Usage:
    tid_doa_compare.py run1.log run2.log [run3.log ...]
    tid_doa_compare.py --dir /path/to/event/runs          # compare the
                                                            # 2 most recent
    tid_doa_compare.py --dir /path/to/event/runs --all     # compare all

The parser reads tid_doa.py's own run-log section markers
(--- INPUTS ---, --- RESULT ---, --- PAIRWISE ---, --- DIAGNOSTICS ---,
--- PROVENANCE ---) directly -- if that format ever changes, this
parser is the one place that needs updating to match, not every
individual comparison.
"""

import argparse
import glob
import os
import re
import sys

# Reuse tid_doa.py's own ANSI color helpers directly rather than
# duplicating them -- same colors, same isatty()-gated behavior.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from tid_doa import _c, _ANSI_RED, _ANSI_YELLOW, _ANSI_GREEN, _ANSI_BOLD
except Exception:
    # tid_doa.py should always be right next to this script in a normal
    # checkout -- but never let an import hiccup crash comparison of
    # already-written text files over a purely cosmetic dependency.
    _ANSI_RED = _ANSI_YELLOW = _ANSI_GREEN = _ANSI_BOLD = ""

    def _c(text, color, enabled):
        return text


def parse_run_log(path):
    """Parse one tid_doa.py run-log file into a flat dict of the
    fields worth comparing. Returns None (with a warning on stderr,
    not a hard failure) if the file doesn't look like a genuine
    tid_doa.py run log -- comparing a typo'd or unrelated path should
    never crash the whole comparison.
    """
    try:
        with open(path, "r", errors="replace") as f:
            text = f.read()
    except OSError as e:
        # REAL BUG FOUND testing this directly: only the "file exists
        # but doesn't look like a run log" case was handled gracefully
        # -- a genuinely missing/unreadable path crashed the whole
        # comparison with an uncaught traceback instead of being
        # skipped the same way, exactly the failure mode this
        # function's own docstring says it avoids.
        print(f"  (skipping {path}: {e})", file=sys.stderr)
        return None

    if "psws-drf-tid-tools run log" not in text:
        print(f"  (skipping {path}: doesn't look like a tid_doa.py run log)",
              file=sys.stderr)
        return None

    info = {"_path": path}

    def _grab(pattern, default=None, cast=str):
        m = re.search(pattern, text)
        if not m:
            return default
        try:
            return cast(m.group(1))
        except Exception:
            return default

    info["timestamp"] = _grab(r"Timestamp:\s+(\S+)")
    info["event_start"] = _grab(r"Event start:\s+(\S+)")
    info["event_end"] = _grab(r"Event end:\s+(\S+)")
    info["speed_m_s"] = _grab(r"Phase speed:\s+([\-\d.]+)\s*m/s", cast=float)
    info["heading_to"] = _grab(r"Heading toward:\s+([\-\d.]+)\s*deg", cast=float)
    info["heading_from"] = _grab(r"Coming from:\s+([\-\d.]+)\s*deg", cast=float)
    info["git_hash"] = _grab(r"git commit:\s+(\S+)")
    info["command"] = _grab(r"command:\s+(.+)")

    # Station lines look like:
    #   n6rfm          file=...  method=cwt-prophet  lat=32.94 lon=-97.21
    stations = []
    for m in re.finditer(
            r"^\s{2}(\S+)\s+file=(\S+)\s+method=(\S+)\s+lat=(\S+)\s+lon=(\S+)",
            text, re.MULTILINE):
        stations.append({
            "name": m.group(1), "file": m.group(2), "method": m.group(3),
            "lat": m.group(4), "lon": m.group(5),
        })
    info["stations"] = stations

    # Diagnostics summary line -- either the all-clear or the flagged
    # count. Written plain in the log (format_diagnostics(colorize=False)
    # is always what gets passed to _write_run_log), so no ANSI codes
    # to strip here regardless of how the original run was printed.
    if re.search(r">> All five diagnostics fall within typical ranges\.",
                 text):
        info["flagged"] = 0
    else:
        m = re.search(r">> (\d+) of 5 diagnostic\(s\) outside typical", text)
        info["flagged"] = int(m.group(1)) if m else None

    return info


def _fmt(v, suffix="", none="?"):
    if v is None:
        return none
    if isinstance(v, float):
        return f"{v:.1f}{suffix}"
    return f"{v}{suffix}"


_SIDE_BY_SIDE_MAX = 4  # beyond this, the wide table becomes genuinely
                       # unreadable rather than just wide -- confirmed
                       # directly: 52 real accumulated run logs produced
                       # an unusable wall of text, not just an inconvenient one


def compare(infos, colorize):
    """Dispatch to the side-by-side table (small counts, the original
    design) or the compact list (larger counts) -- a runs/ directory
    genuinely accumulates dozens of logs across weeks of real testing,
    and the wide table's per-column width doesn't degrade gracefully,
    it becomes flatly unreadable well before that point."""
    if len(infos) <= _SIDE_BY_SIDE_MAX:
        _compare_side_by_side(infos, colorize)
    else:
        _compare_compact(infos, colorize)


def _method_summary(info):
    methods = sorted(set(s["method"] for s in info["stations"]))
    return methods[0] if len(methods) == 1 else "mixed:" + ",".join(methods)


def _compare_compact(infos, colorize):
    """One row per run -- speed, heading, diagnostics, methods, station
    count. Scales to dozens of runs; doesn't attempt the full detail
    the side-by-side table shows (git commit, per-station breakdown),
    since that level of detail isn't readable at this scale anyway --
    narrow to specific runs (fewer paths, or --dir without --all) for
    that."""
    print(_c("=== tid_doa.py run comparison "
             f"({len(infos)} runs -- compact view) ===", _ANSI_BOLD, colorize))
    print("(Narrow to specific run-log paths, or --dir without --all, "
          "for the detailed side-by-side view.)")
    print()
    header = (f"  {'Timestamp':<20}{'Speed':>10}{'Heading':>10}"
              f"{'Diag':>12}{'N':>3}  {'Method(s)'}")
    print(_c(header, _ANSI_BOLD, colorize))
    for i in infos:
        ts = i["timestamp"] or "?"
        speed = _fmt(i["speed_m_s"], " m/s") if i["speed_m_s"] is not None else "?"
        hdg = _fmt(i["heading_to"], "°") if i["heading_to"] is not None else "?"
        f = i["flagged"]
        diag = "all clear" if f == 0 else (f"{f} flagged" if f is not None else "?")
        diag_color = _ANSI_GREEN if f == 0 else (_ANSI_RED if f else "")
        n = len(i["stations"])
        method = _method_summary(i)
        if diag_color:
            # Only the diagnostics field itself is colored here (not
            # the whole line, unlike the side-by-side table's
            # per-row highlighting) -- at this many rows, coloring
            # entire lines would be visual noise rather than signal.
            plain_prefix = f"  {ts:<20}{speed:>10}{hdg:>10}"
            plain_suffix = f"{n:>3}  {method}"
            print(f"{plain_prefix}{_c(f'{diag:>12}', diag_color, colorize)}{plain_suffix}")
        else:
            line = (f"  {ts:<20}{speed:>10}{hdg:>10}"
                    f"{diag:>12}{n:>3}  {method}")
            print(line)


def _compare_side_by_side(infos, colorize):
    """Print a side-by-side comparison. infos: list of parsed dicts
    (already filtered to non-None), 2 to _SIDE_BY_SIDE_MAX runs."""
    labels = [os.path.basename(i["_path"]) for i in infos]
    width = max(24, max(len(l) for l in labels) + 2)

    def row(label, values, highlight_diff=False):
        cells = [_fmt(v) for v in values]
        differs = highlight_diff and len(set(cells)) > 1
        line = f"  {label:<20}" + "".join(f"{c:<{width}}" for c in cells)
        if differs:
            line = _c(line, _ANSI_YELLOW, colorize)
        print(line)

    print(_c("=== tid_doa.py run comparison ===", _ANSI_BOLD, colorize))
    print()
    header = "  " + " " * 20 + "".join(f"{l:<{width}}" for l in labels)
    print(_c(header, _ANSI_BOLD, colorize))
    print()

    row("Timestamp", [i["timestamp"] for i in infos])
    row("Event start", [i["event_start"] for i in infos], highlight_diff=True)
    row("Event end", [i["event_end"] for i in infos], highlight_diff=True)
    row("Git commit", [i["git_hash"] for i in infos], highlight_diff=True)
    print()

    row("Speed (m/s)", [i["speed_m_s"] for i in infos], highlight_diff=True)
    row("Heading to (deg)", [i["heading_to"] for i in infos],
        highlight_diff=True)
    row("Heading from (deg)", [i["heading_from"] for i in infos],
        highlight_diff=True)
    print()

    # Diagnostics flag count -- colored red/green like tid_doa.py's own
    # diagnostics block, not just the generic yellow diff-highlight,
    # since pass/fail here has a real, unambiguous meaning.
    flag_cells = []
    for i in infos:
        f = i["flagged"]
        txt = "all clear" if f == 0 else (f"{f} flagged" if f is not None else "?")
        color = _ANSI_GREEN if f == 0 else (_ANSI_RED if f else "")
        cell = f"{txt:<{width}}"
        flag_cells.append(_c(cell, color, colorize) if color else cell)
    print(f"  {'Diagnostics':<20}" + "".join(flag_cells))
    print()

    # Stations used per run, plus a highlighted note if the sets differ.
    # REAL BUG FOUND testing this directly: station names are compared
    # case-sensitively by default, but different runs can genuinely use
    # different case conventions for the same station (e.g. a raw DRF
    # directory name "SYN_AA6BD" in one run's config vs a lowercase
    # "aa6bd" in another) -- normalizing to uppercase for comparison
    # (matching how KNOWN_STATIONS lookups already work elsewhere in
    # this project) avoids a false "station sets differ" warning for
    # what's actually the same station.
    print(_c("  Stations:", _ANSI_BOLD, colorize))
    all_names_norm = sorted(set(s["name"].upper() for i in infos for s in i["stations"]))
    station_sets = [set(s["name"].upper() for s in i["stations"]) for i in infos]
    sets_differ = len(set(frozenset(s) for s in station_sets)) > 1
    for name_norm in all_names_norm:
        marks = []
        for i, sset in zip(infos, station_sets):
            if name_norm in sset:
                stn = next(s for s in i["stations"] if s["name"].upper() == name_norm)
                marks.append(f"{stn['method']:<{width-2}}")
            else:
                marks.append(f"{'--':<{width-2}}")
        line = f"    {name_norm:<18}" + "  ".join(marks)
        if sets_differ:
            line = _c(line, _ANSI_YELLOW, colorize)
        print(line)
    if sets_differ:
        print(_c("  >> Station sets differ between runs -- speed/heading "
                 "differences may simply reflect", _ANSI_YELLOW, colorize))
        print(_c("     a different array geometry, not a change in "
                 "extraction/analysis quality.", _ANSI_YELLOW, colorize))
    print()

    if len(infos) == 2 and infos[0]["speed_m_s"] is not None \
            and infos[1]["speed_m_s"] is not None:
        d_speed = infos[1]["speed_m_s"] - infos[0]["speed_m_s"]
        d_pct = (abs(d_speed) / infos[0]["speed_m_s"] * 100
                 if infos[0]["speed_m_s"] else float("nan"))
        print(f"  Speed delta ({labels[1]} vs {labels[0]}): "
              f"{d_speed:+.1f} m/s ({d_pct:.1f}%)")
        if infos[0]["heading_to"] is not None and infos[1]["heading_to"] is not None:
            d_hdg = infos[1]["heading_to"] - infos[0]["heading_to"]
            print(f"  Heading delta: {d_hdg:+.1f} deg")


def main():
    ap = argparse.ArgumentParser(
        description="Side-by-side comparison of tid_doa.py run logs.")
    ap.add_argument("logs", nargs="*",
                     help="Two or more run-log file paths to compare.")
    ap.add_argument("--dir", default=None,
                     help="Directory of run logs (e.g. an event's runs/ "
                          "folder) -- compares the 2 most recent unless "
                          "--all is given.")
    ap.add_argument("--all", action="store_true",
                     help="With --dir, compare every run log found "
                          "instead of just the 2 most recent.")
    ap.add_argument("--version", action="version",
                     version="%(prog)s 1.1.0")
    args = ap.parse_args()

    paths = list(args.logs)
    if args.dir:
        found = sorted(glob.glob(os.path.join(args.dir, "*_run.log")))
        if not found:
            sys.exit(f"No *_run.log files found in {args.dir}")
        paths.extend(found if args.all else found[-2:])

    if len(paths) < 2:
        sys.exit("Need at least 2 run logs to compare "
                  "(pass paths directly, or use --dir [--all]).")

    infos = []
    for p in paths:
        parsed = parse_run_log(p)
        if parsed is not None:
            infos.append(parsed)

    if len(infos) < 2:
        sys.exit("Fewer than 2 valid run logs after parsing -- nothing "
                  "to compare.")

    compare(infos, colorize=sys.stdout.isatty())


if __name__ == "__main__":
    main()
