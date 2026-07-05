r"""
tid_doa_config.py — interactive builder for tid_doa.py event configs

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial release.

OVERVIEW
========
Building tid_doa.py config files by hand is error-prone: typos in
station coordinates, forgotten fields, wrong CSV paths, units mismatches.
This script walks you through assembling a config interactively.

It can also auto-discover candidate stations:
  - Scans the current directory for Doppler CSVs (output of
    drf_to_doppler.py)
  - Reads each CSV's bounding time window to suggest event_start/end
  - Optionally reads station metadata from a matching DRF directory
    (the one drf_inspect.py would inspect) to fill in callsign/lat/lon
    automatically -- no typing needed

USAGE
=====
Interactive mode (recommended):

    python tid_doa_config.py --output event.json

Pre-fill from local DRF directories AND interactive review:

    python tid_doa_config.py --output event.json --scan .

Fully non-interactive (use whatever the scanner finds + defaults):

    python tid_doa_config.py --output event.json --scan . --auto

WHAT IT FILLS IN
================
For each candidate station the script tries to populate, in order:

  1. Station name      : DRF metadata 'callsign' field, falling back to
                         the CSV filename stem.
  2. CSV file path     : The discovered .csv file next to the DRF dir.
  3. Lat/Lon           : DRF metadata 'lat'/'long' fields, falling back
                         to the Maidenhead grid_square, falling back to
                         manual entry.

It also suggests:
  - event_start_utc/end_utc from the intersection of all CSVs' time
    ranges (largest window all stations cover).
  - resample_seconds from the median CSV cadence.
  - use_bandpass = false (safe default; see tid_doa.py docstring for why).

REQUIREMENTS
============
    pip install pandas
    Plus optionally digital_rf to read DRF metadata.

SEE ALSO
========
    tid_doa.py            consumer of the config file we build here
    drf_inspect.py        per-station metadata inspector
    drf_to_doppler.py     produces the .csv inputs
"""

import argparse
import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

import pandas as pd

__version__ = "1.0.0"

# Optional dependency: digital_rf for reading DRF metadata
try:
    import digital_rf as drf
    _HAVE_DRF = True
except ImportError:
    drf = None
    _HAVE_DRF = False


# ----------------------------------------------------------------------------
# Maidenhead grid -> lat/lon (in case DRF metadata only has grid square)
# ----------------------------------------------------------------------------
def grid_to_latlon(grid):
    g = grid.strip()
    if len(g) < 4:
        return None
    try:
        A = ord(g[0].upper()) - ord('A')
        B = ord(g[1].upper()) - ord('A')
        C = int(g[2]); D = int(g[3])
        lon = -180 + A*20 + C*2
        lat = -90 + B*10 + D*1
        if len(g) >= 6:
            E = ord(g[4].lower()) - ord('a')
            F = ord(g[5].lower()) - ord('a')
            lon += E*(2/24) + (1/24)
            lat += F*(1/24) + (0.5/24)
        else:
            lon += 1.0; lat += 0.5
        return lat, lon
    except Exception:
        return None


# ----------------------------------------------------------------------------
# DRF metadata extractor
# ----------------------------------------------------------------------------
def read_drf_metadata(drf_dir):
    """Try to read callsign/lat/lon/grid from a DRF station directory.
    Returns dict or {} if not available."""
    if not _HAVE_DRF:
        return {}
    metadata_dir = os.path.join(drf_dir, "ch0", "metadata")
    if not os.path.isdir(metadata_dir):
        return {}
    try:
        m = drf.DigitalMetadataReader(metadata_dir)
        b = m.get_bounds()
        sample = m.read(b[0], b[0] + 1)
        if sample:
            return dict(list(sample.values())[0])
    except Exception:
        pass
    return {}


# ----------------------------------------------------------------------------
# CSV time range
# ----------------------------------------------------------------------------
def csv_time_range(csv_path):
    """Return (start_utc, end_utc, median_cadence_seconds) for a CSV."""
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return None, None, None
    df.columns = [c.lower() for c in df.columns]
    tcol = next((c for c in df.columns
                 if "time" in c or "utc" in c or "stamp" in c), None)
    if tcol is None:
        return None, None, None
    try:
        ts = pd.to_datetime(df[tcol], utc=True)
    except Exception:
        return None, None, None
    if len(ts) == 0:
        return None, None, None
    diffs = ts.diff().dropna().dt.total_seconds()
    median_dt = float(diffs.median()) if len(diffs) else 10.0
    return ts.iloc[0], ts.iloc[-1], median_dt


# ----------------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------------
def discover_csvs(folder):
    """Find .csv files in folder. Return list of paths."""
    csvs = []
    for ext in ("*.csv",):
        csvs.extend(sorted(glob.glob(os.path.join(folder, ext))))
    return csvs


def discover_drf_dirs(folder):
    """Find subdirectories that look like DRF stations (contain ch0/)."""
    result = {}
    for entry in sorted(os.listdir(folder)):
        full = os.path.join(folder, entry)
        if os.path.isdir(os.path.join(full, "ch0")):
            result[entry.lower()] = full
    return result


def match_csv_to_drf(csv_path, drf_dirs):
    """Best-effort match a CSV to a DRF directory by filename stem."""
    stem = os.path.splitext(os.path.basename(csv_path))[0].lower()
    # Try exact match first
    if stem in drf_dirs:
        return drf_dirs[stem]
    # Then try stem-starts-with-drf-name or drf-name-starts-with-stem
    for name, path in drf_dirs.items():
        if stem.startswith(name) or name.startswith(stem):
            return path
    return None


# ----------------------------------------------------------------------------
# Interactive helpers
# ----------------------------------------------------------------------------
def prompt(label, default=None):
    if default is not None:
        ans = input(f"  {label} [{default}]: ").strip()
        return ans if ans else default
    while True:
        ans = input(f"  {label}: ").strip()
        if ans:
            return ans


def prompt_float(label, default=None):
    while True:
        s = prompt(label, default=str(default) if default is not None else None)
        try:
            return float(s)
        except ValueError:
            print(f"    Not a valid number: {s!r}")


def confirm(label, default=True):
    suffix = " [Y/n]" if default else " [y/N]"
    ans = input(f"  {label}{suffix}: ").strip().lower()
    if not ans:
        return default
    return ans.startswith("y")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring for full details.",
    )
    ap.add_argument("--output", "-o", required=True,
                    help="Output JSON config path, e.g. event_20260119.json")
    ap.add_argument("--scan", default=None,
                    help="Directory to scan for CSVs and DRF dirs. If "
                         "omitted, you'll be prompted for each station "
                         "manually.")
    ap.add_argument("--auto", action="store_true",
                    help="Don't prompt interactively after the scan; "
                         "use discovered values + defaults straight to "
                         "the output file. Implies --scan if not set.")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    if args.auto and not args.scan:
        args.scan = "."

    candidates = []  # list of dicts: name, file, lat, lon, csv_start, csv_end, csv_dt

    # ---- Discovery ----
    if args.scan:
        scan_dir = os.path.abspath(args.scan)
        print(f"Scanning {scan_dir} ...")
        csvs = discover_csvs(scan_dir)
        drf_dirs = discover_drf_dirs(scan_dir)
        print(f"  Found {len(csvs)} CSV files and {len(drf_dirs)} DRF dirs")
        for csv_path in csvs:
            name = os.path.splitext(os.path.basename(csv_path))[0]
            drf_dir = match_csv_to_drf(csv_path, drf_dirs)
            meta = read_drf_metadata(drf_dir) if drf_dir else {}

            # Pull what we can from metadata
            cs_name = meta.get("callsign", name).strip() if meta else name
            lat = lon = None
            if meta:
                if "lat" in meta and "long" in meta:
                    try:
                        lat = float(meta["lat"])
                        lon = float(meta["long"])
                    except Exception:
                        lat = lon = None
                if (lat is None or lon is None) and "grid_square" in meta:
                    ll = grid_to_latlon(meta["grid_square"])
                    if ll:
                        lat, lon = ll

            # Time bounds from the CSV
            t0, t1, dt = csv_time_range(csv_path)

            candidates.append({
                "name": cs_name,
                "file": os.path.basename(csv_path),
                "lat": lat, "lon": lon,
                "csv_start": t0, "csv_end": t1, "csv_dt": dt,
                "drf_dir": drf_dir,
            })
            print(f"  + {os.path.basename(csv_path):<30s} "
                  f"callsign={cs_name!s}  "
                  f"lat={lat}  lon={lon}  "
                  f"start={t0}")

    # ---- Interactive review/add ----
    if not args.auto:
        print()
        if candidates:
            print(f"Discovered {len(candidates)} station(s). Review:")
            for i, c in enumerate(candidates, 1):
                missing = []
                if c["lat"] is None: missing.append("lat")
                if c["lon"] is None: missing.append("lon")
                flag = f" (MISSING: {', '.join(missing)})" if missing else ""
                print(f"  {i}. {c['name']:<20s} file={c['file']}  "
                      f"lat={c['lat']}  lon={c['lon']}{flag}")

            # Fill in missing lat/lon
            for c in candidates:
                if c["lat"] is None or c["lon"] is None:
                    print(f"\nStation {c['name']} ({c['file']}) is missing "
                          f"coordinates.")
                    grid = input("  Maidenhead grid square (or blank to "
                                 "enter lat/lon directly): ").strip()
                    if grid:
                        ll = grid_to_latlon(grid)
                        if ll:
                            c["lat"], c["lon"] = ll
                            print(f"    -> lat={ll[0]:.4f}, lon={ll[1]:.4f}")
                            continue
                        print(f"    Could not parse grid {grid!r}.")
                    c["lat"] = prompt_float("lat (decimal degrees)")
                    c["lon"] = prompt_float("lon (decimal degrees)")

            # Allow editing names
            print()
            if confirm("Edit any station names?", default=False):
                for c in candidates:
                    new = input(f"  {c['name']!r} -> ").strip()
                    if new:
                        c["name"] = new

            # Add manual stations
            while confirm("Add an additional station manually?", default=False):
                c = {}
                c["name"] = prompt("Station name")
                c["file"] = prompt("CSV filename (relative to working dir)")
                c["lat"] = prompt_float("lat (decimal degrees)")
                c["lon"] = prompt_float("lon (decimal degrees)")
                c["csv_start"] = None; c["csv_end"] = None; c["csv_dt"] = None
                candidates.append(c)
        else:
            # No discovery; build entirely by hand
            print("No stations discovered. Add stations manually.")
            while True:
                c = {}
                c["name"] = prompt("Station name (e.g. N6RFM)")
                c["file"] = prompt("CSV filename")
                grid = input("  Maidenhead grid (blank for lat/lon): ").strip()
                if grid:
                    ll = grid_to_latlon(grid)
                    if ll:
                        c["lat"], c["lon"] = ll
                    else:
                        print(f"    Could not parse grid {grid!r}")
                        c["lat"] = prompt_float("lat")
                        c["lon"] = prompt_float("lon")
                else:
                    c["lat"] = prompt_float("lat")
                    c["lon"] = prompt_float("lon")
                c["csv_start"] = None; c["csv_end"] = None; c["csv_dt"] = None
                candidates.append(c)
                if not confirm("Add another?", default=True):
                    break

    if len(candidates) < 3:
        print(f"\nWarning: only {len(candidates)} station(s); tid_doa.py "
              "requires at least 3.")

    # ---- Suggest event window from CSV intersection ----
    starts = [c["csv_start"] for c in candidates if c["csv_start"] is not None]
    ends = [c["csv_end"] for c in candidates if c["csv_end"] is not None]
    if starts and ends:
        common_start = max(starts)   # latest start = first time all have data
        common_end = min(ends)       # earliest end = last time all have data
        # Round to a nice value
        suggested_start = common_start.replace(microsecond=0).isoformat()
        suggested_end = common_end.replace(microsecond=0).isoformat()
    else:
        suggested_start = "2026-01-19T00:00:00Z"
        suggested_end = "2026-01-19T01:15:00Z"

    dts = [c["csv_dt"] for c in candidates if c["csv_dt"]]
    suggested_dt = int(round(sum(dts) / len(dts))) if dts else 10

    if not args.auto:
        print()
        print(f"Suggested event window from CSV overlap:")
        print(f"  start: {suggested_start}")
        print(f"  end:   {suggested_end}")
        event_start = prompt("event_start_utc",
                             default=suggested_start)
        event_end = prompt("event_end_utc",
                           default=suggested_end)
        dt = int(prompt_float("resample_seconds", default=suggested_dt))
        use_bp = confirm("use_bandpass (False is correct for almost all "
                         "cases; see tid_doa.py docstring)?", default=False)
        min_speed = prompt_float(
            "min_expected_speed_m_s (for auto max_lag; lower = wider search)",
            default=100.0)
    else:
        event_start = suggested_start
        event_end = suggested_end
        dt = suggested_dt
        use_bp = False
        min_speed = 100.0

    # ---- Assemble output ----
    config = {
        "_comment": (f"Generated by tid_doa_config.py on "
                     f"{datetime.now(timezone.utc).isoformat()} UTC"),
        "event_start_utc": event_start,
        "event_end_utc": event_end,
        "resample_seconds": dt,
        "use_bandpass": use_bp,
        "min_expected_speed_m_s": min_speed,
        "stations": [
            {"name": c["name"], "file": c["file"],
             "lat": round(c["lat"], 4), "lon": round(c["lon"], 4)}
            for c in candidates
            if c.get("lat") is not None and c.get("lon") is not None
        ],
    }

    skipped = [c["name"] for c in candidates
               if c.get("lat") is None or c.get("lon") is None]
    if skipped:
        print(f"\nSkipped {len(skipped)} candidate(s) with missing "
              f"coordinates: {', '.join(skipped)}")

    with open(args.output, "w") as f:
        json.dump(config, f, indent=2)

    print()
    print(f"Wrote {args.output} with {len(candidates)} stations.")
    print(f"Now run:")
    print(f"    python tid_doa.py {args.output}")


if __name__ == "__main__":
    main()
