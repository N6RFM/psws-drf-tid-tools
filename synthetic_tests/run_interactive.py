#!/usr/bin/env python3
"""
run_interactive.py -- One-command launcher for interactive extraction
(cwt-prophet or wave-fit) on synthetic test events.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.1
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.1  Renamed --subchannel to --channel-num in the drf_spectrogram.py
          subprocess call, matching that tool's own rename. "Subchannel"
          incorrectly implied a single combined signal demultiplexed
          into related sub-streams; what's actually happening is
          several independent, unrelated frequencies packed into one
          DRF directory's data columns. No functional change.
  v1.0.0  Initial release.

Collapses the 9-step manual workflow into 3:
  1. Run this script
  2. Click in each spectrogram window (unavoidable)
  3. See pass/fail result

Usage:
    # All stations, cwt-prophet
    python3 run_interactive.py --test nominal --method cwt-prophet

    # All stations, wave-fit
    python3 run_interactive.py --test nominal --method spline

    # Specific stations only
    python3 run_interactive.py --test nominal --method cwt-prophet \
        --stations SYN_AA6BD,SYN_W7LUX

    # Re-do one station (skip others that already have CSVs)
    python3 run_interactive.py --test nominal --method cwt-prophet \
        --stations SYN_N6RFM --force

    # All 27 test conditions (batch interactive -- opens one station
    # at a time across all tests, evaluates after each test completes)
    python3 run_interactive.py --all --method cwt-prophet

What it does for each station:
  1. Generates synthetic DRF if not cached
  2. Runs drf_spectrogram.py with sensible defaults (ylim=-1,1)
  3. Opens tid_spect_click.py and waits for user to finish
  4. Copies output CSV to events directory
  5. After all stations: runs DOA and prints pass/fail vs ground truth

Options:
  --test NAME       Test condition name (e.g. nominal)
  --method METHOD   cwt-prophet or spline (wave-fit)
  --stations A,B    Comma-separated station names (default: all)
  --force           Re-extract even if CSV already exists
  --all             Run all test conditions sequentially
  --output-root     Root directory for DRF events
  --ylim LO,HI      Spectrogram y-axis range in Hz (default: -1,1)
  --dpi N           Spectrogram DPI (default: 150)
  --skip-existing   Skip stations that already have CSVs (default: True)
"""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys
import datetime

# Locate toolkit root and synthetic_tests/
SYNTH_DIR   = pathlib.Path(__file__).parent
TOOLKIT_DIR = SYNTH_DIR.parent
EVENTS_DIR  = SYNTH_DIR / "events"
PLOTS_DIR   = SYNTH_DIR / "plots"

sys.path.insert(0, str(SYNTH_DIR))
from test_conditions import TEST_CONDITIONS


def find_script(name):
    p = TOOLKIT_DIR / name
    if p.exists():
        return str(p)
    raise FileNotFoundError(f"Cannot find {name} in {TOOLKIT_DIR}")


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def generate_drf(test_name, output_root):
    """Generate synthetic DRF if not already present."""
    event_dir = pathlib.Path(output_root) / f"synthetic_{test_name}"
    gt_path = event_dir / "ground_truth.json"
    if gt_path.exists():
        print(f"  [{ts()}] DRF cached: {event_dir.name}")
        return event_dir, json.loads(gt_path.read_text())

    print(f"  [{ts()}] Generating DRF for {test_name}...")
    r = subprocess.run(
        [sys.executable,
         str(SYNTH_DIR / "run_tests.py"),
         "--test", test_name,
         "--methods", "autocorr",
         "--output-root", str(output_root)],
        capture_output=True, text=True
    )
    if not gt_path.exists():
        print(f"  ERROR: DRF generation failed\n{r.stderr[:200]}")
        return None, None
    return event_dir, json.loads(gt_path.read_text())


def generate_spectrogram(station_dir, station_name, t_start_hhmm, t_end_hhmm,
                         output_png, ylim="-1,1", dpi=150):
    """Run drf_spectrogram.py and return path to PNG + sidecar."""
    output_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, find_script("drf_spectrogram.py"),
        str(station_dir),
        "--channel-num", "0",
        "--start", t_start_hhmm,
        "--end",   t_end_hhmm,
        f"--ylim={ylim}",
        "--dpi", str(dpi),
        "--output", str(output_png),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not output_png.exists():
        print(f"  ERROR: spectrogram generation failed\n{r.stderr[:200]}")
        return False
    sidecar = output_png.parent / (output_png.stem + "_axes.json")
    if sidecar.exists():
        print(f"  [{ts()}] Spectrogram + sidecar: {output_png.name}")
    else:
        print(f"  [{ts()}] Spectrogram (no sidecar): {output_png.name}")
    return True


def run_spect_click(spectrogram_png, drf_dir, station_name,
                    method, period_hint_s, test_name=None, ylim="-1,1"):
    """Open tid_spect_click.py and wait for user to finish."""
    cmd = [
        sys.executable, find_script("tid_spect_click.py"),
        "--spectrogram", str(spectrogram_png),
        "--drf-dir",     str(drf_dir),
        "--name",        station_name,
        "--period-hint", str(int(period_hint_s)),
    ]
    if method == "spline":
        cmd.append("--wave-only")

    print(f"\n  [{ts()}] Opening {method} for {station_name}...")
    print(f"  Spectrogram: {spectrogram_png.name}")
    # Show reference spectrogram with true Doppler overlay
    ref_png = (PLOTS_DIR / test_name /
               f"{station_name}_spectrogram_ref.png")
    if not ref_png.exists():
        # Generate reference using plot_spectrograms.py
        import sys as _sys
        _sys.path.insert(0, str(SYNTH_DIR))
        try:
            import plot_spectrograms as _ps
            import importlib, json as _json
            _gt = _json.loads(
                (EVENTS_DIR / f"synthetic_{test_name}" /
                 "ground_truth.json").read_text())
            _ps.SEARCH_HZ = abs(float(ylim.split(",")[1]))
            _ps.plot_station(
                station_name,
                EVENTS_DIR / f"synthetic_{test_name}" / station_name,
                _gt["event_start_unix"],
                _gt["event_end_unix"] - _gt["event_start_unix"],
                _gt, overlay_csvs=None,
                output_path=ref_png)
        except Exception as _e:
            print(f"  (reference spectrogram skipped: {_e})")
    if ref_png.exists():
        subprocess.Popen(["eog", str(ref_png)])
        print(f"  [{ts()}] Reference (with true Doppler): {ref_png.name}")
    if method == "spline":
        print("  TIP: See reference image for true carrier location.")
        print("  Click 5+ points on the bright carrier band across "
              "full window.")
        print("  Press F to fit, confirm cycles, press A to accept.")
    else:
        print("  TIP: See reference image (red dashed = true Doppler).")
        print("  Verify the cyan auto-trace follows the carrier.")
        print("  If correct: press E. If wrong: click carrier to anchor, "
              "then press E.")
    print("  [Waiting for you to finish in the GUI window...]")

    r = subprocess.run(cmd)  # blocks until window closes

    # Find output CSV (tid_spect_click.py writes alongside the PNG)
    spect_dir = spectrogram_png.parent
    candidates = [
        spect_dir / f"{station_name}_spectrogram_wave_tid.csv",
        spect_dir / f"{station_name}_spectrogram_prophet_tid.csv",
        spect_dir / f"{station_name}_spectrogram_guided.csv",
        spect_dir / f"{spectrogram_png.stem}_wave_tid.csv",
        spect_dir / f"{spectrogram_png.stem}_prophet_tid.csv",
    ]
    found = next((c for c in candidates if c.exists()), None)
    if found:
        print(f"  [{ts()}] Output: {found.name}")
    else:
        print(f"  [{ts()}] WARNING: no output CSV found in {spect_dir}")
        # List what IS there
        csvs = list(spect_dir.glob("*.csv"))
        if csvs:
            print(f"  CSVs in plots dir: {[c.name for c in csvs]}")
    return found


def run_one_interactive(test_name, method, station_filter=None,
                        force=False, output_root=None,
                        ylim="-1,1", dpi=150):
    """Run interactive extraction for one test condition."""
    if output_root is None:
        output_root = EVENTS_DIR

    tc = next((t for t in TEST_CONDITIONS if t[0] == test_name), None)
    if tc is None:
        print(f"ERROR: unknown test '{test_name}'")
        return None

    name, speed, az, period_min, amp, snr, noise, array_name, expect_pass, notes = tc
    period_s = period_min * 60.0

    print(f"\n{'='*60}")
    print(f"Test: {name}  |  Method: {method}")
    print(f"Ground truth: {speed} m/s from {az}°, {period_min}-min period")
    print(f"{'='*60}")

    # Step 1: Generate DRF
    event_dir, gt = generate_drf(test_name, output_root)
    if event_dir is None:
        return None

    # UTC time window
    import datetime as _dt
    t0_unix = gt["event_start_unix"]
    t1_unix = gt["event_end_unix"]
    t0 = _dt.datetime.fromtimestamp(t0_unix, tz=_dt.timezone.utc)
    t1 = _dt.datetime.fromtimestamp(t1_unix, tz=_dt.timezone.utc)
    t_start_hhmm = t0.strftime("%H:%M")
    t_end_hhmm   = t1.strftime("%H:%M")

    stations = gt["stations"]
    if station_filter:
        stations = [s for s in stations
                    if s["name"] in station_filter]
        if not stations:
            print(f"ERROR: none of {station_filter} found in {test_name}")
            return None

    print(f"Stations ({len(stations)}): "
          f"{', '.join(s['name'] for s in stations)}")
    print(f"Window: {t_start_hhmm} - {t_end_hhmm} UTC\n")

    method_suffix = "cwt-prophet" if method == "cwt-prophet" else "spline"
    completed_csvs = {}

    for i, s in enumerate(stations, 1):
        stn = s["name"]
        print(f"--- Station {i}/{len(stations)}: {stn} ---")

        # Check if CSV already exists
        dest_csv = event_dir / f"{stn.lower()}_{method_suffix}.csv"
        if dest_csv.exists() and not force:
            print(f"  [{ts()}] CSV already exists -- skipping "
                  f"(use --force to re-extract)")
            completed_csvs[stn] = dest_csv
            continue

        # Step 2: Generate spectrogram
        spect_dir = PLOTS_DIR / test_name
        spect_png = spect_dir / f"{stn}_spectrogram.png"
        ok = generate_spectrogram(
            event_dir / stn, stn,
            t_start_hhmm, t_end_hhmm,
            spect_png, ylim=ylim, dpi=dpi
        )
        if not ok:
            print(f"  SKIPPING {stn} -- spectrogram failed")
            continue

        # Step 3: Open tid_spect_click.py
        output_csv = run_spect_click(
            spect_png, event_dir / stn, stn, method, period_s,
            test_name=test_name, ylim=ylim)

        # Step 4: Copy CSV to events directory
        if output_csv and output_csv.exists():
            shutil.copy(output_csv, dest_csv)
            print(f"  [{ts()}] Saved: {dest_csv.name}")
            completed_csvs[stn] = dest_csv
        else:
            print(f"  [{ts()}] No CSV for {stn} -- station skipped in DOA")

    if len(completed_csvs) < 2:
        print(f"\nERROR: need at least 2 stations for DOA "
              f"(got {len(completed_csvs)})")
        return None

    # Step 5: Evaluate
    print(f"\n--- Evaluating {name} / {method_suffix} ---")
    sys.path.insert(0, str(SYNTH_DIR))
    from run_tests import run_one_test
    result = run_one_test(tc, method_suffix, str(output_root), verbose=True)

    return result


def main():
    ap = argparse.ArgumentParser(
        description="One-command launcher for interactive synthetic testing")
    ap.add_argument("--test", metavar="NAME",
                    help="Test condition name (e.g. nominal)")
    ap.add_argument("--all", action="store_true",
                    help="Run all test conditions sequentially")
    ap.add_argument("--method", default="spline",
                    choices=["cwt-prophet", "spline"],
                    # Note: cwt-prophet is very slow on synthetic data
                    help="Extraction method (default: cwt-prophet)")
    ap.add_argument("--stations", metavar="A,B,C",
                    help="Comma-separated station names (default: all)")
    ap.add_argument("--force", action="store_true",
                    help="Re-extract even if CSV already exists")
    ap.add_argument("--output-root",
                    default=str(EVENTS_DIR),
                    help=f"DRF events directory (default: {EVENTS_DIR})")
    ap.add_argument("--ylim", default="-1,1",
                    help="Spectrogram y-axis range in Hz (default: -1,1)")
    ap.add_argument("--dpi", type=int, default=150,
                    help="Spectrogram DPI (default: 150)")
    ap.add_argument("--list", action="store_true",
                    help="List available test conditions and exit")
    args = ap.parse_args()

    if args.list:
        print(f"{'Name':25} {'Speed':>5} {'Az':>4} {'Per':>4} "
              f"{'SNR':>4} {'Noise':>10} {'Pass':>5}")
        print("-" * 65)
        for tc in TEST_CONDITIONS:
            n, spd, az, per, amp, snr, noise, arr, exp, notes = tc
            print(f"{n:25} {spd:5} {az:4} {per:4} "
                  f"{snr:4} {noise:>10} {str(exp):>5}")
        return

    station_filter = (set(args.stations.split(","))
                      if args.stations else None)

    if args.all:
        results = []
        for tc in TEST_CONDITIONS:
            r = run_one_interactive(
                tc[0], args.method,
                station_filter=station_filter,
                force=args.force,
                output_root=args.output_root,
                ylim=args.ylim, dpi=args.dpi)
            if r:
                results.append(r)
        # Summary
        print(f"\n{'='*60}")
        print(f"BATCH SUMMARY: {len(results)} conditions")
        passed = sum(1 for r in results if r.get("overall_pass"))
        print(f"Pass: {passed}/{len(results)}")
        return

    if args.test:
        run_one_interactive(
            args.test, args.method,
            station_filter=station_filter,
            force=args.force,
            output_root=args.output_root,
            ylim=args.ylim, dpi=args.dpi)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
