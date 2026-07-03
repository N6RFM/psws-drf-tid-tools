#!/usr/bin/env python3
"""
run_tests.py -- Automated test runner for psws-drf-tid-tools synthetic
validation suite.

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
    """Find a toolkit script."""
    p = TOOLKIT_DIR / name
    if p.exists():
        return str(p)
    # Try current dir
    p2 = pathlib.Path(".") / name
    if p2.exists():
        return str(p2)
    raise FileNotFoundError(f"Cannot find {name} — set TOOLKIT_DIR or run from repo root")


def run_extraction(station_dir, output_csv, method, t_start_iso, t_end_iso,
                   decim_seconds=60, subchannel=0):
    """Run drf_to_doppler.py on one station."""
    cmd = [
        sys.executable, find_script("drf_to_doppler.py"),
        str(station_dir),
        "--subchannel", str(subchannel),
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

    # Extract Doppler for each station
    if verbose:
        print(f"  Extracting with method={method}...")
    for s in stations:
        stn_dir = event_dir / s["name"]
        csv_path = event_dir / f"{s['name'].lower()}_{method}.csv"
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
        is_alias = r.get("alias_demo", False)
        exp_str = "yes" if expect else ("no (alias)" if is_alias else "no (stress)")
        mark    = " <<UNEXPECTED" if unexpected else ""

        print(f"{r['test']:25} {r['method']:10} {spd_err:>10} {az_err:>8} "
              f"{flags:>6} {status:>6} {exp_str:>9}{mark}")

    print("-"*100)
    print(f"Total: {n_total}  Pass: {n_pass}  Unexpected: {n_unexpected}")
    print("="*100)


def main():
    ap = argparse.ArgumentParser(description="Run synthetic TID test suite")
    ap.add_argument("--automated", action="store_true",
                    help="Run all tests non-interactively (autocorr + cwt)")
    ap.add_argument("--test", metavar="NAME",
                    help="Run a single named test")
    ap.add_argument("--methods", default="autocorr,cwt,fft",
                    help="Comma-separated extraction methods (default: autocorr,cwt,fft)")
    ap.add_argument("--output-root", default=str(pathlib.Path(__file__).parent / "events"),
                    help="Root directory for generated events")
    ap.add_argument("--results-dir", default="results",
                    help="Directory for test results (default: results/)")
    ap.add_argument("--list", action="store_true",
                    help="List all test conditions and exit")
    args = ap.parse_args()

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
