#!/usr/bin/env python3
"""
quality_summary.py — compute and display per-station Doppler quality metrics

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.1
License: MIT

OVERVIEW
========
Reads one or more Doppler-vs-time CSV files (the output of
drf_to_doppler.py) and prints a quality-assessment table to help the
operator decide which stations to keep, drop, or re-extract before
the multi-station DOA inversion.

The metrics are:

  SNR floor    - percentage of samples with SNR < 30 dB. Sub-30 dB
                 segments are unreliable for Doppler tracking.

  Jitter       - standard deviation of consecutive sample differences
                 in Doppler (Hz). High jitter means the Doppler trace
                 is bouncing around between samples (carrier tracker
                 not locked, or genuine high-frequency noise).
                 < 0.10 Hz: clean
                 0.10-0.20 Hz: noisy
                 > 0.20 Hz: very noisy

  Excursions   - count of samples with |Doppler| > 2 Hz. These are
                 usually tracker failures (the carrier was lost and
                 the FFT peak-finder grabbed something at the search-
                 band edge). A few are fine; many indicate bad data.

  End fade     - SNR in the last 10% of samples compared to the
                 middle 50%. A large drop suggests the analysis
                 window extends past where this station's carrier
                 was clean.

  Score        - composite 0-100 score combining the above. Higher
                 is better.

USAGE
=====
  # Score a single CSV
  python3 quality_summary.py n6rfm.csv

  # Score every CSV in the current directory
  python3 quality_summary.py *.csv

  # Score CSVs listed in a tid_doa event config
  python3 quality_summary.py --config event.json

  # Verbose output: print per-station diagnostics, not just the table
  python3 quality_summary.py --verbose n6rfm.csv aa6bd.csv

  # Suggest a shorter end time if end-fade is detected on any station
  python3 quality_summary.py --suggest-shorten *.csv

The script does NOT modify any files. It only reads CSVs and prints
to stdout.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError as e:
    sys.stderr.write(f"ERROR: missing dependency: {e}\n")
    sys.stderr.write("Install with: pip install numpy pandas\n")
    sys.exit(2)


# -----------------------------------------------------------------------------
# Metric computation
# -----------------------------------------------------------------------------

def compute_quality_metrics(csv_path):
    """Compute quality metrics for a single Doppler CSV.

    Returns a dict with keys: name, n_samples, snr_floor_pct, jitter_hz,
    excursions, end_fade_db, score, status.
    """
    df = pd.read_csv(csv_path)
    name = Path(csv_path).stem

    # Expected columns: timestamp_utc, doppler_hz, snr_db
    # (Be defensive — some CSVs might have slightly different column names.)
    doppler_col = next((c for c in df.columns
                        if c.lower().replace(' ', '_').startswith('doppler')), None)
    snr_col = next((c for c in df.columns
                    if c.lower().replace(' ', '_').startswith('snr')), None)

    if doppler_col is None or snr_col is None:
        return {
            'name': name,
            'n_samples': len(df),
            'error': f"CSV missing doppler or SNR column (found: {list(df.columns)})",
        }

    doppler = df[doppler_col].to_numpy()
    snr = df[snr_col].to_numpy()
    n = len(doppler)

    if n < 10:
        return {
            'name': name,
            'n_samples': n,
            'error': f"too few samples ({n}) for meaningful analysis",
        }

    # ----- SNR floor: % of samples below 30 dB -----
    snr_floor_pct = 100.0 * np.mean(snr < 30.0)

    # ----- Jitter: stddev of first-differences in Doppler -----
    diffs = np.diff(doppler)
    jitter_hz = float(np.std(diffs))

    # ----- Out-of-band excursions: |Doppler| > 2 Hz -----
    excursions = int(np.sum(np.abs(doppler) > 2.0))

    # ----- End fade: compare SNR in last 10% vs middle 50% -----
    last10_start = int(0.9 * n)
    mid_start = int(0.25 * n)
    mid_end = int(0.75 * n)
    snr_last10 = float(np.median(snr[last10_start:]))
    snr_middle = float(np.median(snr[mid_start:mid_end]))
    end_fade_db = snr_middle - snr_last10   # positive = SNR dropped at end

    # ----- Composite score 0-100 -----
    # Each component contributes up to 25 points. Anything zeroed-out
    # means that metric is at its worst.
    score = 0.0

    # SNR floor: 0% bad = 25, 50% bad = 0
    score += max(0.0, 25.0 - 0.5 * snr_floor_pct)

    # Jitter: 0.05 Hz = 25, 0.30 Hz = 0
    jitter_score = 25.0 * (1.0 - (jitter_hz - 0.05) / 0.25)
    score += max(0.0, min(25.0, jitter_score))

    # Excursions: 0 = 25, 50+ = 0
    score += max(0.0, 25.0 - 0.5 * excursions)

    # End fade: 0 dB drop = 25, 10 dB drop = 0
    score += max(0.0, 25.0 - 2.5 * max(0.0, end_fade_db))

    score = round(score, 1)

    # Status string
    if score >= 80:
        status = "GOOD"
    elif score >= 60:
        status = "OK"
    elif score >= 40:
        status = "POOR"
    else:
        status = "BAD"

    # Reasons for sub-perfect score
    reasons = []
    if snr_floor_pct > 5:
        reasons.append(f"{snr_floor_pct:.0f}% sub-30 dB")
    if jitter_hz > 0.15:
        reasons.append(f"high jitter ({jitter_hz:.2f} Hz)")
    if excursions > 5:
        reasons.append(f"{excursions} excursions")
    if end_fade_db > 3:
        reasons.append(f"end fades {end_fade_db:.1f} dB")

    return {
        'name': name,
        'n_samples': n,
        'snr_floor_pct': snr_floor_pct,
        'jitter_hz': jitter_hz,
        'excursions': excursions,
        'end_fade_db': end_fade_db,
        'score': score,
        'status': status,
        'reasons': reasons,
        # Keep around for verbose mode
        'snr_middle': snr_middle,
        'snr_last10': snr_last10,
        'last10_start_index': last10_start,
        'doppler_range': (float(np.min(doppler)), float(np.max(doppler))),
        # For end-time shortening suggestions
        'last10_timestamps': df.iloc[last10_start:, 0].tolist() if n > 10 else [],
    }


# -----------------------------------------------------------------------------
# Output formatting
# -----------------------------------------------------------------------------

def print_table(results):
    """Pretty-print the per-station table to stdout."""
    print()
    print("Quality summary:")
    print(f"  {'Station':<14} {'SNR floor':>10} {'Jitter':>8} {'Excur.':>7} "
          f"{'End fade':>9} {'Score':>6}  {'Status':<6}  {'Notes'}")
    print(f"  {'-'*14} {'-'*10} {'-'*8} {'-'*7} {'-'*9} {'-'*6}  {'-'*6}  {'-'*40}")

    for r in results:
        if 'error' in r:
            print(f"  {r['name']:<14} {'ERROR: ' + r['error']}")
            continue
        reasons_str = '; '.join(r.get('reasons', [])) or 'clean'
        print(f"  {r['name']:<14} "
              f"{r['snr_floor_pct']:>9.0f}% "
              f"{r['jitter_hz']:>8.3f} "
              f"{r['excursions']:>7d} "
              f"{r['end_fade_db']:>+8.1f} "
              f"{r['score']:>6.1f}  "
              f"{r['status']:<6}  "
              f"{reasons_str}")
    print()


def print_verbose(r):
    """Print extended diagnostics for one station."""
    if 'error' in r:
        print(f"\n{r['name']}: ERROR: {r['error']}")
        return
    print(f"\n  {r['name']}:")
    print(f"    samples:               {r['n_samples']}")
    print(f"    SNR floor (<30 dB):    {r['snr_floor_pct']:.1f}%")
    print(f"    SNR median (middle):   {r['snr_middle']:.1f} dB")
    print(f"    SNR median (last 10%): {r['snr_last10']:.1f} dB")
    print(f"    end-fade delta:        {r['end_fade_db']:+.1f} dB")
    print(f"    doppler jitter (1st-diff stddev): {r['jitter_hz']:.3f} Hz")
    print(f"    doppler range:         {r['doppler_range'][0]:+.2f} to "
          f"{r['doppler_range'][1]:+.2f} Hz")
    print(f"    excursions (|D|>2 Hz): {r['excursions']}")
    print(f"    score:                 {r['score']:.1f} / 100  ({r['status']})")
    if r['reasons']:
        print(f"    flagged for:           {', '.join(r['reasons'])}")


def print_shortening_suggestion(results):
    """If any station has notable end-fade, suggest a shorter window."""

    def clean_iso(ts):
        """Convert any timestamp-like value to ISO-8601 second precision UTC."""
        try:
            dt = pd.to_datetime(ts, utc=True)
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        except Exception:
            # Fallback: best-effort string truncation
            s = str(ts)
            # Trim microseconds and timezone parts
            for cut in ('.', '+', ' '):
                if cut in s:
                    s = s.replace(' ', 'T', 1).split('.')[0].split('+')[0]
                    break
            return s

    suggestions = []
    for r in results:
        if 'error' in r:
            continue
        if r['end_fade_db'] > 3.0 and r['last10_timestamps']:
            # The end of the clean window is the start of the last-10% block
            suggested_end = clean_iso(r['last10_timestamps'][0])
            suggestions.append((r['name'], r['end_fade_db'], suggested_end))

    if not suggestions:
        return

    print("End-fade suggestions:")
    for name, drop, t in suggestions:
        print(f"  {name}: SNR drops {drop:+.1f} dB in the last 10% of the window.")
        print(f"    Consider shortening the analysis window to end at or before {t}.")
    print()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Compute and display per-station Doppler quality metrics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('USAGE')[1] if 'USAGE' in __doc__ else None,
    )
    ap.add_argument('csv_files', nargs='*', help='Doppler-vs-time CSV file(s)')
    ap.add_argument('--config', help='Read CSV list from a tid_doa event JSON config')
    ap.add_argument('--verbose', '-v', action='store_true',
                    help='Print extended per-station diagnostics in addition to the table')
    ap.add_argument('--suggest-shorten', action='store_true',
                    help='Suggest shorter analysis window if end-fade is detected')
    ap.add_argument('--include-scratch', action='store_true',
                    help='Include survey/quicklook/duplicate CSVs (skipped by default)')
    ap.add_argument('--version', action='version', version='quality_summary.py 1.0.1')

    args = ap.parse_args()

    csv_files = list(args.csv_files)
    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        for s in cfg.get('stations', []):
            f = s.get('file')
            if f and f not in csv_files:
                csv_files.append(f)

    if not csv_files:
        ap.error("no CSV files specified (use positional args or --config)")

    # Filter out survey/scratch CSVs (the 24-hr ones from analyze_event.sh's
    # Stage 1b and similar). Only excluded when the user did not name them
    # explicitly (i.e. came from a glob like *.csv).
    SKIP_PATTERNS = ('_survey', '_quicklook', '_full24h')
    if not args.include_scratch:
        filtered = []
        skipped = []
        for path in csv_files:
            stem = Path(path).stem.lower()
            if any(p in stem for p in SKIP_PATTERNS):
                skipped.append(path)
            else:
                filtered.append(path)
        if skipped:
            sys.stderr.write(
                "Note: skipping scratch/survey CSVs (use --include-scratch to keep):\n"
            )
            for p in skipped:
                sys.stderr.write(f"  {p}\n")
        csv_files = filtered

    # De-duplicate by data fingerprint (case-insensitive station name).
    # When both `n6rfm.csv` and `N6RFM_5.csv` exist (driver sanity-check
    # plus final extraction), they are the same data — keep the first.
    seen = {}
    deduped = []
    for path in csv_files:
        # Use the lowercased non-suffix stem as the dedup key. Strip
        # common suffixes the driver may append.
        key = Path(path).stem.lower()
        for suffix in ('_5', '_full', '_clean'):
            if key.endswith(suffix):
                key = key[: -len(suffix)]
        if key in seen:
            sys.stderr.write(
                f"Note: skipping {path} (duplicate of {seen[key]}; "
                f"use --include-scratch to keep both)\n"
            )
            continue
        seen[key] = path
        deduped.append(path)
    csv_files = deduped

    if not csv_files:
        sys.stderr.write("No usable CSVs after filtering.\n")
        sys.exit(1)

    # Compute metrics for each CSV
    results = []
    for path in csv_files:
        if not Path(path).is_file():
            sys.stderr.write(f"WARNING: {path} not found, skipping\n")
            continue
        try:
            r = compute_quality_metrics(path)
            results.append(r)
        except Exception as exc:
            results.append({'name': Path(path).stem, 'error': str(exc)})

    if not results:
        sys.stderr.write("No usable CSVs to score.\n")
        sys.exit(1)

    print_table(results)

    if args.verbose:
        for r in results:
            print_verbose(r)
        print()

    if args.suggest_shorten:
        print_shortening_suggestion(results)


if __name__ == '__main__':
    main()
