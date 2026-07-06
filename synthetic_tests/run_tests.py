#!/usr/bin/env python3
"""
run_tests.py -- Automated test runner for psws-drf-tid-tools synthetic
validation suite.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.2
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.2  Renamed run_extraction()'s subchannel parameter and the
          --subchannel drf_to_doppler.py subprocess arg to channel_num/
          --channel-num, matching that tool's own rename. "Subchannel"
          incorrectly implied a single combined signal demultiplexed
          into related sub-streams; what's actually happening is
          several independent, unrelated frequencies packed into one
          DRF directory's data columns. No functional change.
  v1.0.1  find_script() now gives a specific, actionable error (what
          paths it tried, how to fix it) instead of a bare
          FileNotFoundError. --show-commands' wave-fit/cwt-prophet
          output comments corrected -- they described the eventual
          auto-copied destination path as if it were the immediate
          save location, which doesn't match where tid_spect_click.py
          actually writes the file first (next to the spectrogram
          PNG). No change to any test-running logic.
  v1.0.0  Initial versioned release (version annotation added
          retroactively during the repo-wide annotation audit; no
          prior version history existed).

Modes:
  --automated   Run all tests non-interactively using autocorr and cwt
                extraction (no GUI required). Fast, suitable for CI.
  --interactive Run tests using tid_workflow.py in guided mode (requires
                display). User selects extraction method per station.
  --test NAME   Run a single named test condition.
  --methods M   Comma-separated extraction methods to test
                (default: autocorr,cwt for automated; all for interactive)

For each test:
  1. Generate synthetic DRF event directory (via synthetic_drf.py)
  2. Run extraction on each station DRF
  3. Build event.json config
  4. Run tid_doa.py
  5. Compare result against ground truth
  6. Record pass/fail

Output:
  results/summary.json     Machine-readable results
  results/summary.txt      Human-readable table
  results/plots/           Speed/azimuth error plots per test
"""
import argparse
import datetime
import json
import math
import pathlib
import subprocess
import sys
import time

# Import test definitions
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_conditions import TEST_CONDITIONS, ARRAYS
from evaluate import evaluate
from synthetic_drf import generate_event, EVENT_START_UTC, SAMPLE_RATE_HZ

# Path to psws-drf-tid-tools scripts (default: parent of synthetic_tests/)
TOOLKIT_DIR = pathlib.Path(__file__).parent.parent


def find_script(name):
    """Find a toolkit script. Tries, in order: the repo root (parent of
    synthetic_tests/, __file__-relative so this works regardless of cwd),
    then the actual current working directory (in case someone's running
    from an unusual layout), then gives a specific, actionable error
    instead of a bare FileNotFoundError.
    """
    p = TOOLKIT_DIR / name
    if p.exists():
        return str(p)
    p2 = pathlib.Path.cwd() / name
    if p2.exists():
        return str(p2)
    raise FileNotFoundError(
        f"Cannot find {name}. Looked in:\n"
        f"  {TOOLKIT_DIR} (repo root, relative to this script's location)\n"
        f"  {pathlib.Path.cwd()} (your current directory)\n"
        f"If the repo layout is non-standard, set TOOLKIT_DIR at the top "
        f"of run_tests.py, or run this from either the repo root "
        f"(python3 synthetic_tests/run_tests.py ...) or from inside "
        f"synthetic_tests/ (python3 run_tests.py ...) -- both work.")


def run_extraction(station_dir, output_csv, method, t_start_iso, t_end_iso,
                   decim_seconds=60, channel_num=0):
    """Run drf_to_doppler.py on one station."""
    cmd = [
        sys.executable, find_script("drf_to_doppler.py"),
        str(station_dir),
        "--channel-num", str(channel_num),
        "--start", t_start_iso,
        "--end",   t_end_iso,
        "--decim-seconds", str(decim_seconds),
        "--method", method,
        "--output", str(output_csv),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr
    return True, r.stdout


def run_doa(event_json_path):
    """Run tid_doa.py and return (speed_m_s, az_from_deg, n_flags, raw_output)."""
    cmd = [sys.executable, find_script("tid_doa.py"), str(event_json_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    output = r.stdout + r.stderr

    speed, az_from, n_flags = None, None, None
    for line in output.splitlines():
        if "Phase speed:" in line:
            try:
                speed = float(line.split(":")[1].split("m/s")[0].strip())
            except Exception:
                pass
        if "Wave coming from:" in line:
            try:
                az_from = float(line.split(":")[1].split("°")[0].strip().rstrip("°"))
            except Exception:
                pass
        if "diagnostic(s) outside typical ranges" in line:
            try:
                n_flags = int(line.strip().split()[2])
            except Exception:
                pass
        if "All five diagnostics fall within typical ranges" in line:
            n_flags = 0

    # Default None to 0 -- DOA ran but flag line wasn't found
    if speed is not None and n_flags is None:
        n_flags = 0

    return speed, az_from, n_flags, output


def azimuth_error(measured, true):
    """Signed azimuth error in degrees, accounting for wrap."""
    diff = (measured - true + 180) % 360 - 180
    return diff




def run_one_test(tc, method, output_root, verbose=True):
    """Run one test condition with one extraction method."""
    (name, speed, az, period_min, amp, snr, noise,
     array_name, expect_pass, notes) = tc

    period_s   = period_min * 60
    event_dir, gt = generate_event(name, output_root)

    # ISO timestamps
    t_start = datetime.datetime.fromtimestamp(EVENT_START_UTC, tz=datetime.timezone.utc)
    t_end   = datetime.datetime.fromtimestamp(EVENT_START_UTC + int(period_s * 2.0), tz=datetime.timezone.utc)
    t_start_iso = t_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    t_end_iso   = t_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    stations = ARRAYS[array_name]
    station_cfgs = []
    csvs = {}

    # Interactive methods (cwt-prophet, spline) -- look for pre-existing
    # CSV from tid_spect_click.py rather than running extraction
    INTERACTIVE_METHODS = {"cwt-prophet", "spline", "wave-fit"}

    # Extract Doppler for each station
    if verbose:
        print(f"  Extracting with method={method}...")
    for s in stations:
        stn_dir = event_dir / s["name"]
        csv_path = event_dir / f"{s['name'].lower()}_{method}.csv"
        if method in INTERACTIVE_METHODS:
            # Don't run extraction -- user must have run tid_spect_click.py
            # tid_spect_click.py writes CSV alongside the spectrogram PNG
            # so also check plots dir for <station>_spectrogram_wave_tid.csv
            # (wave-fit) or <station>_spectrogram_prophet_tid.csv (cwt-prophet)
            if not csv_path.exists():
                plots_dir = pathlib.Path(__file__).parent / 'plots' / name
                stn_lower = s['name'].lower()
                # Look for tid_spect_click.py output in plots dir
                candidates = [
                    plots_dir / f"{s['name']}_spectrogram_wave_tid.csv",
                    plots_dir / f"{s['name']}_spectrogram_prophet_tid.csv",
                    plots_dir / f"{s['name']}_spectrogram_guided.csv",
                ]
                found = next((c for c in candidates if c.exists()), None)
                if found:
                    import shutil
                    shutil.copy(found, csv_path)
                    if verbose:
                        print(f"    {s['name']}: copied {found.name} -> {csv_path.name}")
                else:
                    if verbose:
                        print(f"    {s['name']}: CSV not found -- run interactively:")
                        print(f"      python3 run_tests.py --show-commands --test {name}")
                    return {"test": name, "method": method,
                            "overall_pass": False,
                            "note": f"CSV not found -- run tid_spect_click.py first: "
                                    f"python3 run_tests.py --show-commands --test {name}"}
            if verbose:
                print(f"    {s['name']}: using pre-existing CSV {csv_path.name}")
        else:
            ok, msg = run_extraction(stn_dir, csv_path, method,
                                      t_start_iso, t_end_iso)
            if not ok:
                if verbose:
                    print(f"    {s['name']}: EXTRACTION FAILED -- {msg[:80]}")
                return {"test": name, "method": method,
                        "overall_pass": False, "note": f"extraction failed: {msg[:80]}"}
        csvs[s["name"]] = csv_path
        station_cfgs.append({
            "name": s["name"],
            "file": str(csv_path),
            "method": method,
            "lat": s["lat"],
            "lon": s["lon"],
        })

    # Build event.json with correct max_lag_seconds from ground truth lags
    from synthetic_signal import compute_station_lag, great_circle_midpoint, WWV_LAT, WWV_LON
    mids = [great_circle_midpoint(WWV_LAT, WWV_LON, s["lat"], s["lon"])
            for s in stations]
    all_lags = []
    for s in stations:
        lag, _ = compute_station_lag(s["lat"], s["lon"], speed, az, mids)
        all_lags.append(lag)
    n = len(stations)
    max_pairwise = max(abs(all_lags[j]-all_lags[i])
                       for i in range(n) for j in range(i+1, n))
    # Set max_lag to 1.15x the true max pairwise lag (tight window, prevents
    # wrong-period aliases while still covering the true lag)
    max_lag_s = min(max_pairwise * 1.15, period_s * 0.49)
    # For aliased cases, max_lag is also bounded by T/2 (prevents aliasing
    # from being "solved" by accident -- we want the test to fail naturally)

    event_cfg = {
        "event_start_utc": t_start_iso,
        "event_end_utc":   t_end_iso,
        "resample_seconds": 60,
        "use_bandpass": False,
        "use_ipp": True,
        "min_expected_speed_m_s": 100,
        "max_lag_seconds": round(max_lag_s),
        "stations": station_cfgs,
    }
    event_json = event_dir / f"event_{method}.json"
    event_json.write_text(json.dumps(event_cfg, indent=2))

    # Run DOA
    if verbose:
        print(f"  Running DOA (max_lag={round(max_lag_s)}s)...")
    spd, az_meas, n_flags, doa_output = run_doa(event_json)

    if verbose:
        if spd:
            print(f"    Result: {spd:.1f} m/s @ {az_meas:.1f}° ({n_flags} flags)")
            print(f"    Truth:  {speed:.1f} m/s @ {az:.1f}°")

    # Evaluate
    gt["notes"] = notes  # ensure notes available for evaluate()
    gt["snr_db"] = snr
    gt["noise_type"] = noise
    gt["method"] = method  # for per-method thresholds
    result = evaluate(spd, az_meas, n_flags, gt)
    result["test"] = name
    result["method"] = method
    result["expect_pass"] = expect_pass
    result["notes"] = notes
    result["max_lag_s"] = round(max_lag_s)
    result["alias_demo"] = not expect_pass and "ALIAS" in notes

    if verbose:
        status = "PASS" if result["overall_pass"] else "FAIL"
        expected = "expected" if (result["overall_pass"] == (expect_pass or not expect_pass)) else "UNEXPECTED"
        print(f"    {status} ({expected}): "
              f"speed_err={result.get('speed_error_pct','?')}%  "
              f"az_err={result.get('azimuth_error_deg','?')}deg  "
              f"flags={n_flags}")

    return result


def print_summary(results):
    """Print a formatted summary table."""
    print("\n" + "="*100)
    print("SYNTHETIC TEST SUITE RESULTS")
    print("="*100)
    print(f"{'Test':25} {'Method':10} {'Speed err':>10} {'Az err':>8} "
          f"{'Flags':>6} {'Pass?':>6} {'Expected':>9}")
    print("-"*100)

    n_total = n_pass = n_unexpected = 0
    for r in results:
        n_total += 1
        overall = r.get("overall_pass", False)
        expect  = r.get("expect_pass", True)
        if overall:
            n_pass += 1
        # UNEXPECTED only for expect_pass=True tests that fail
        # Alias/stress tests passing our eval is expected, not unexpected
        unexpected = (not overall and expect)
        if unexpected:
            n_unexpected += 1

        spd_err = f"{r.get('speed_error_pct','?')}%" if r.get('speed_error_pct') is not None else "N/A"
        az_err  = f"{r.get('azimuth_error_deg','?')}°" if r.get('azimuth_error_deg') is not None else "N/A"
        flags   = str(r.get('n_flags', '?'))
        status  = "PASS" if overall else "FAIL"
        exp_str = "yes" if expect else "no (stress)"
        mark    = " <<UNEXPECTED" if unexpected else ""

        print(f"{r['test']:25} {r['method']:10} {spd_err:>10} {az_err:>8} "
              f"{flags:>6} {status:>6} {exp_str:>9}{mark}")

    print("-"*100)
    print(f"Total: {n_total}  Pass: {n_pass}  Unexpected: {n_unexpected}")
    print("="*100)


def _show_interactive_commands(test_name, output_root, results_dir):
    """Print tid_spect_click.py commands for interactive extraction."""
    import json as _json
    toolkit_dir = pathlib.Path(__file__).parent.parent
    spect_click = toolkit_dir / 'tid_spect_click.py'
    plot_dir = pathlib.Path(__file__).parent / 'plots'

    conditions = ([next(t for t in TEST_CONDITIONS if t[0] == test_name)]
                  if test_name else TEST_CONDITIONS)

    print('=== Interactive extraction commands ===')
    print('Run these to extract with cwt-prophet or wave-fit,')
    print('then evaluate with --methods cwt-prophet or --methods spline')
    print()

    for tc in conditions:
        name = tc[0]
        period_min = tc[3]
        event_dir = pathlib.Path(output_root) / f'synthetic_{name}'
        gt_path = event_dir / 'ground_truth.json'
        if not gt_path.exists():
            print(f'[{name}] not generated yet -- run:'
                  f' python3 run_tests.py --test {name} --methods autocorr')
            continue

        gt = _json.loads(gt_path.read_text())
        t_start = gt['event_start_utc']
        t_end   = gt['event_end_utc']
        # Convert to decimal hours for --tlim
        import datetime as _dt
        t0 = _dt.datetime.fromisoformat(t_start.replace('Z','+00:00'))
        t1 = _dt.datetime.fromisoformat(t_end.replace('Z','+00:00'))
        h0 = t0.hour + t0.minute/60 + t0.second/3600
        h1 = t1.hour + t1.minute/60 + t1.second/3600

        print(f'--- {name} ---')
        print(f'  True: {gt["true_speed_m_s"]} m/s from '
              f'{gt["true_az_from_deg"]}deg, '
              f'{gt["true_period_min"]} min period')
        print()

        for s in gt['stations']:
            stn = s['name']
            drf_dir = event_dir / stn
            png = plot_dir / name / f'{stn}_spectrogram.png'
            if not png.exists():
                print(f'  # Generate spectrogram first:')
                print(f'  python3 plot_spectrograms.py --test {name}')
                print()

            out_csv_prophet = event_dir / f'{stn.lower()}_cwt-prophet.csv'
            out_csv_spline  = event_dir / f'{stn.lower()}_spline.csv'

            axes_json = png.with_name(png.stem + '_axes.json')
            has_sidecar = axes_json.exists()
            sidecar_note = ('  # sidecar axes.json found -- axis mapping auto'
                            if has_sidecar else
                            '  # NOTE: run plot_spectrograms.py first for sidecar')
            print(f'  # {stn} -- cwt-prophet: {sidecar_note}')
            print(f'  python3 {spect_click} \\' )
            print(f'    --spectrogram {png} \\' )
            print(f'    --drf-dir {drf_dir} \\' )
            print(f'    --name {stn} \\' )
            print(f'    --period-hint {period_min*60:.0f}')
            print(f'  # tid_spect_click.py saves next to the spectrogram PNG '
                  f'first (e.g. {png.with_name(png.stem + "_wave_tid.csv")});')
            print(f'  # this run_tests.py --methods cwt-prophet evaluation '
                  f'step below finds it there and copies it to:')
            print(f'  #   {out_csv_prophet}')
            print()
            print(f'  # {stn} -- wave-fit (--wave-only): {sidecar_note}')
            print(f'  python3 {spect_click} \\' )
            print(f'    --spectrogram {png} \\' )
            print(f'    --drf-dir {drf_dir} \\' )
            print(f'    --name {stn} \\' )
            print(f'    --period-hint {period_min*60:.0f} \\' )
            print(f'    --wave-only')
            print(f'  # Same pattern: saved next to the PNG first, then '
                  f'--methods spline below auto-copies it to:')
            print(f'  #   {out_csv_spline}')
            print()

        print(f'  # After extraction, evaluate:')
        print(f'  python3 run_tests.py --test {name} --methods cwt-prophet')
        print(f'  python3 run_tests.py --test {name} --methods spline')
        print()


def main():
    ap = argparse.ArgumentParser(description="Run synthetic TID test suite")
    ap.add_argument("--automated", action="store_true",
                    help="Run all tests non-interactively (autocorr + cwt)")
    ap.add_argument("--test", metavar="NAME",
                    help="Run a single named test")
    ap.add_argument("--methods", default="autocorr,cwt",
                    help="Comma-separated extraction methods (default: autocorr,cwt)")
    ap.add_argument("--output-root", default=str(pathlib.Path(__file__).parent / "events"),
                    help="Root directory for generated events")
    ap.add_argument("--results-dir", default="results",
                    help="Directory for test results (default: results/)")
    ap.add_argument("--list", action="store_true",
                    help="List all test conditions and exit")
    ap.add_argument("--show-commands", action="store_true",
                    help="Print tid_spect_click.py commands for interactive "
                         "extraction (cwt-prophet, spline/wave-fit) without "
                         "running them. Run these manually, then use "
                         "--methods cwt-prophet or --methods spline to evaluate.")
    args = ap.parse_args()

    if args.show_commands:
        _show_interactive_commands(
            args.test, args.output_root, args.results_dir)
        return

    if args.list:
        pass  # TEST_CONDITIONS already imported
        for tc in TEST_CONDITIONS:
            name, spd, az, per, amp, snr, noise, arr, exp, notes = tc
            print(f"  {name:25} speed={spd:4} az={az:4} period={per:4}min "
                  f"snr={snr:2}dB noise={noise:9} expect_pass={str(exp):5}")
        return

    methods = [m.strip() for m in args.methods.split(",")]
    results_dir = pathlib.Path(args.results_dir)
    results_dir.mkdir(exist_ok=True)

    if args.test:
        tc = next((t for t in TEST_CONDITIONS if t[0] == args.test), None)
        if tc is None:
            sys.exit(f"Unknown test: {args.test}")
        all_results = []
        for method in methods:
            print(f"\n[{args.test} / {method}]")
            r = run_one_test(tc, method, args.output_root, verbose=True)
            all_results.append(r)
        print_summary(all_results)
        return

    if args.automated:
        all_results = []
        t0 = time.time()
        for tc in TEST_CONDITIONS:
            for method in methods:
                print(f"\n[{tc[0]} / {method}]")
                r = run_one_test(tc, method, args.output_root, verbose=True)
                all_results.append(r)

        print_summary(all_results)

        # Save results
        results_file = results_dir / "summary.json"
        results_file.write_text(json.dumps(all_results, indent=2))
        print(f"\nResults saved: {results_file}")
        elapsed = time.time() - t0
        print(f"Total time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
