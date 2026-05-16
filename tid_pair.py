r"""
tid_pair.py — two-station Doppler cross-correlation analyzer for TID events


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
Given two Doppler-vs-time CSVs from a pair of HamSCI Grape DRF stations
recording the same WWV carrier, this tool measures the time lag between
them across multiple bandpass filter bands and reports the apparent
phase speed of the disturbance traveling along the inter-station
baseline.

This is the simplest possible TID analysis -- one number per station
pair (the lag), interpreted geometrically. With only two stations you
cannot fully determine the wave's azimuth, but you can:

  - Confirm a wave was COHERENT between the two stations (correlation
    > 0.5 across multiple filter bands)
  - Establish WHICH station the wave reached first
  - Compute an apparent phase speed = baseline_distance / |lag|
    (this is a LOWER BOUND on the true wave speed; the true speed equals
    apparent speed only if the wave is aligned with the baseline)
  - Determine the SIGN of motion along the baseline axis

For full direction-of-arrival you need three or more non-collinear
stations -- see tid_doa.py.

INPUT FORMAT
============
Each CSV is the output of drf_to_doppler.py and has the columns:
    timestamp_utc, doppler_hz, [snr_db]
The script auto-detects the column names (any column containing "time",
"stamp", or "utc" is treated as time; any column containing "dop" or
"freq" is treated as the signal). Both CSVs are resampled to a common
cadence (--dt, default 10 s) before analysis.

METHOD
======
The full processing pipeline:

  1. Load both CSVs and clip to [--start, --end].
  2. Resample to common cadence --dt.
  3. For each filter band (raw + 4 standard bands), apply a 3rd-order
     Butterworth bandpass via filtfilt (zero phase delay).
  4. Z-normalize both filtered series.
  5. Compute scipy.signal.correlate(y, x, mode='full'), find the
     positive-correlation peak within a maximum lag window. The
     maximum lag is set to half the shortest period in each filter
     band -- this is the aliasing-safe limit for periodic signals.
  6. Compute geometric quantities: midpoint-to-midpoint great-circle
     distance, bearing.
  7. Report (lag, correlation, apparent_speed, direction) per band.

WHY MULTIPLE BANDS
==================
Different ionospheric structures live in different period ranges:

  - 30-60 min:  shorter MSTID components, ripples
  - 40-90 min:  classic MSTID range
  - 60-120 min: LSTID range, post-storm thermospheric response
  - 30-120 min: wide combined band
  - Raw:        includes the slow diurnal background; useful only when
                you already know the wave is much faster than the
                background trend

A wave that is REAL and propagating will show roughly the same lag in
all bands that capture it, with correlation > 0.7. A wave that flips
sign or changes magnitude wildly across bands is either noise, or there
are MULTIPLE waves at different periods moving in different directions.
Both are interesting; the first means "trust the result", the second
means "your event has structure beyond a single planar wave".

SIGN CONVENTION
===============
The reported lag has SIGN. Positive lag means csv2 lags csv1 (i.e., the
wave reached station 1 first). Negative lag means csv2 leads csv1. The
"Direction" column translates this into a true-bearing direction of
wave motion ASSUMING the wave moves directly along the baseline. This
is one of two possible alignment scenarios; without a second baseline
at a different orientation you cannot determine which.

INTERPRETING APPARENT SPEED
===========================
Apparent speed = baseline / |lag|.

Apparent speed is the wave's velocity component along the baseline,
recovered from the time it takes the wavefront to traverse the
baseline projection. If the wave's true direction is exactly along
the baseline, apparent speed equals the true speed. If the wave
moves at angle theta to the baseline:

  apparent speed = true speed / cos(theta)

so apparent speed >= true speed. (When the wave moves nearly
perpendicular to the baseline, cos(theta) is small and the apparent
speed diverges -- the wavefront crosses both midpoints almost
simultaneously, lag is near zero, and the implied baseline-projection
speed becomes very large.)

For 188 km baseline and 14 min lag (our N6RFM/N5TNL Jan 19 result):
  apparent speed = 224 m/s
  true speed could be 224 m/s (wave aligned with baseline) or smaller
  if the wave is partly oblique to the baseline.

Without a second baseline at a different orientation you cannot
distinguish these cases; that is what the multi-station DOA inversion
in tid_doa.py solves.

USAGE
=====
    python tid_pair.py n6rfm.csv n5tnl.csv         --lat1 32.938 --lon1 -97.208 --name1 N6RFM         --lat2 35.333 --lon2 -94.333 --name2 N5TNL         --start 2026-01-19T00:00:00 --end 2026-01-19T01:45:00

OUTPUT INTERPRETATION
=====================
The output table shows, for each filter band:

    Lag (s)            -- time offset of csv2 relative to csv1, in seconds
    Lag (min)          -- same, in minutes
    Corr               -- correlation peak, range -1 to +1; > 0.5 is real
    Apparent speed     -- baseline / |lag|, lower bound on true speed
    Direction          -- which station first + bearing of wave motion

Look for CONSISTENT lag values across bands. If raw, 40-90, 60-120, and
30-120 all give -14 +/- 2 min lag with correlation > 0.7, the result is
robust. A single discrepant band (e.g. 30-60 flipping sign) usually
means that band picked up a different, faster wave riding on top of the
dominant slow wave.

REQUIREMENTS
============
    pip install numpy scipy pandas
"""
import argparse
import math
import sys

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, correlate

WWV_LAT, WWV_LON = 40.6776, -105.0405
EARTH_R_KM = 6371.0


def to_rad(d): return d * math.pi / 180.0
def to_deg(r): return r * 180.0 / math.pi


def great_circle_midpoint(lat1, lon1, lat2, lon2):
    f1, l1 = to_rad(lat1), to_rad(lon1)
    f2, l2 = to_rad(lat2), to_rad(lon2)
    dl = l2 - l1
    bx = math.cos(f2) * math.cos(dl)
    by = math.cos(f2) * math.sin(dl)
    f3 = math.atan2(math.sin(f1) + math.sin(f2),
                    math.sqrt((math.cos(f1) + bx)**2 + by**2))
    l3 = l1 + math.atan2(by, math.cos(f1) + bx)
    return to_deg(f3), (to_deg(l3) + 540) % 360 - 180


def haversine_km(lat1, lon1, lat2, lon2):
    f1, f2 = to_rad(lat1), to_rad(lat2)
    df = to_rad(lat2 - lat1)
    dl = to_rad(lon2 - lon1)
    a = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    f1, f2 = to_rad(lat1), to_rad(lat2)
    dl = to_rad(lon2 - lon1)
    y = math.sin(dl) * math.cos(f2)
    x = math.cos(f1)*math.sin(f2) - math.sin(f1)*math.cos(f2)*math.cos(dl)
    return (to_deg(math.atan2(y, x)) + 360) % 360


def bandpass(sig, fs, low_p, high_p):
    nyq = 0.5 * fs
    low = (1.0/high_p) / nyq
    high = (1.0/low_p) / nyq
    low = max(low, 1e-6)
    high = min(high, 0.99)
    b, a = butter(3, [low, high], btype="band")
    return filtfilt(b, a, sig)


def find_lag(x, y, fs, max_lag_s):
    """Return (lag_seconds, peak_correlation).
    Positive lag = y lags x (y is delayed relative to x)."""
    x = (x - np.mean(x)) / (np.std(x) + 1e-12)
    y = (y - np.mean(y)) / (np.std(y) + 1e-12)
    n = len(x)
    corr = correlate(y, x, mode="full") / n
    lags = (np.arange(2*n - 1) - (n - 1)) / fs
    mask = np.abs(lags) <= max_lag_s
    sub_corr = corr[mask]
    sub_lags = lags[mask]
    idx = int(np.argmax(sub_corr))
    return float(sub_lags[idx]), float(sub_corr[idx])


def load(csv_path, t_start, t_end, dt_s):
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    tcol = next(c for c in df.columns if "time" in c or "stamp" in c)
    dcol = next(c for c in df.columns if "dop" in c or "freq" in c)
    df[tcol] = pd.to_datetime(df[tcol], utc=True)
    df = df.sort_values(tcol).set_index(tcol)
    df = df.loc[t_start:t_end]
    target = f"{int(dt_s)}s"
    df = df[[dcol]].resample(target).mean().interpolate()
    return df.index.to_numpy(), df[dcol].to_numpy()


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring at the top of the script for full details.",
    )
    ap.add_argument("csv1",
                    help="First station's Doppler CSV (from drf_to_doppler.py). "
                         "Lag values are reported relative to this station.")
    ap.add_argument("csv2",
                    help="Second station's Doppler CSV. Positive lag in output "
                         "means csv2 lags csv1.")
    ap.add_argument("--lat1", type=float, required=True,
                    help="csv1 station receiver latitude (decimal degrees)")
    ap.add_argument("--lon1", type=float, required=True,
                    help="csv1 station receiver longitude (decimal degrees)")
    ap.add_argument("--lat2", type=float, required=True,
                    help="csv2 station receiver latitude (decimal degrees)")
    ap.add_argument("--lon2", type=float, required=True,
                    help="csv2 station receiver longitude (decimal degrees)")
    ap.add_argument("--name1", default="STN1",
                    help="Display name for csv1 station. Default: STN1")
    ap.add_argument("--name2", default="STN2",
                    help="Display name for csv2 station. Default: STN2")
    ap.add_argument("--start", required=True,
                    help="UTC start of analysis window in ISO format, "
                         "e.g. '2026-01-19T00:00:00'")
    ap.add_argument("--end", required=True,
                    help="UTC end of analysis window in ISO format")
    ap.add_argument("--dt", type=float, default=10.0,
                    help="Resampling cadence in seconds. Both input series "
                         "are resampled to this cadence before correlation. "
                         "Default: 10.0")
    ap.add_argument("--smooth", type=float, default=None,
                    metavar="N",
                    help="apply Savitzky-Golay smoothing with N-second "
                         "window to both Doppler series before correlation "
                         "(default off; recommended for high-jitter stations)")
    ap.add_argument("--overlay-plot", type=str, default=None,
                    metavar="PATH.png",
                    help="write a paired-Doppler overlay PNG to PATH "
                         "(both station traces on the same axes)")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    t0 = pd.Timestamp(args.start.replace("Z","+00:00"))
    if t0.tzinfo is None:
        t0 = t0.tz_localize("UTC")
    t1 = pd.Timestamp(args.end.replace("Z","+00:00"))
    if t1.tzinfo is None:
        t1 = t1.tz_localize("UTC")

    fs = 1.0 / args.dt

    t_a, y_a = load(args.csv1, t0, t1, args.dt)
    t_b, y_b = load(args.csv2, t0, t1, args.dt)

    if args.smooth is not None:
        from scipy.signal import savgol_filter
        poly_order = 3
        n_samples = int(round(args.smooth / args.dt))
        min_window = poly_order + 2
        if n_samples < min_window:
            raise ValueError(
                f"--smooth {args.smooth:g}s too small for dt={args.dt}s; "
                f"need >= {min_window * args.dt:g}s for poly_order={poly_order}"
            )
        if n_samples % 2 == 0:
            n_samples += 1
        y_a = savgol_filter(y_a, n_samples, poly_order)
        y_b = savgol_filter(y_b, n_samples, poly_order)
        print(f"Smoothing applied: Savitzky-Golay window={args.smooth:g}s "
              f"({n_samples} samples), polynomial order 3")
    n = min(len(y_a), len(y_b))
    y_a = y_a[:n]; y_b = y_b[:n]

    # Midpoint geometry
    mid_a = great_circle_midpoint(WWV_LAT, WWV_LON, args.lat1, args.lon1)
    mid_b = great_circle_midpoint(WWV_LAT, WWV_LON, args.lat2, args.lon2)
    baseline_km = haversine_km(mid_a[0], mid_a[1], mid_b[0], mid_b[1])
    brg_a_to_b = bearing_deg(mid_a[0], mid_a[1], mid_b[0], mid_b[1])

    print(f"=== Pair analysis: {args.name1} vs {args.name2} ===")
    print(f"  {args.name1} midpoint: ({mid_a[0]:.3f}, {mid_a[1]:.3f})")
    print(f"  {args.name2} midpoint: ({mid_b[0]:.3f}, {mid_b[1]:.3f})")
    print(f"  Baseline:              {baseline_km:.0f} km")
    print(f"  Bearing {args.name1} -> {args.name2}: {brg_a_to_b:.1f}° true\n")

    print(f"{'Interval (min)':<14} {'Lag (s)':>9} {'Lag (min)':>10}  {'Corr':>6}  {'Speed (+ along {brg:.0f}°)':>26}  Direction".format(brg=brg_a_to_b))
    print("-" * 90)

    bands = [
        ("Full time window", None, None),
        ("30 - 60",   30*60, 60*60),
        ("40 - 90",   40*60, 90*60),
        ("60 - 120",  60*60, 120*60),
        ("30 - 120",  30*60, 120*60),
    ]
    for label, lo, hi in bands:
        if lo is None:
            x_f, y_f = y_a, y_b
            max_lag = (n*args.dt)/3
        else:
            x_f = bandpass(y_a, fs, lo, hi)
            y_f = bandpass(y_b, fs, lo, hi)
            max_lag = lo / 2.0  # half the shortest period
        lag, corr = find_lag(x_f, y_f, fs, max_lag)
        # lag > 0 means csv2 lags csv1; signal arrived at csv1 first
        if abs(lag) < 1e-6:
            signed_speed_str = " (zero lag)"
            direction = "indeterminate"
        else:
            speed_ms = baseline_km * 1000.0 / abs(lag)
            # Signed convention: positive speed when the wave moves
            # from {name2} toward {name1} (i.e. arrives at name1 first,
            # which means it traveled in the direction of brg_a_to_b).
            # Negative speed when the wave moves the other way.
            if lag > 0:
                # csv2 lags csv1 -> wave reached name1 first -> moving
                # from name2 toward name1 -> direction = brg_b_to_a =
                # (brg_a_to_b + 180) % 360. So if we choose positive
                # to mean "along brg_a_to_b", this case is negative.
                signed_speed = -speed_ms
                direction = f"{args.name1} first, wave heading ~{(brg_a_to_b+180)%360:.0f}°"
            else:
                signed_speed = +speed_ms
                direction = f"{args.name2} first, wave heading ~{brg_a_to_b:.0f}°"
            signed_speed_str = f"{signed_speed:>+7.0f} m/s"
        print(f"{label:<14} {lag:>+9.1f} {lag/60:>+10.2f}  {corr:>+6.3f}  {signed_speed_str:>26}  {direction}")

    print("\nInterpretation hints:")
    print(f"- 'Speed' is signed: + means wave moves along {brg_a_to_b:.0f}° (from {args.name2} to {args.name1});")
    print(f"  - means wave moves along {(brg_a_to_b+180)%360:.0f}° (from {args.name1} to {args.name2}).")
    print("- Sign flips between intervals indicate the lag is dominated by noise, not a coherent wave.")
    print("- 'Speed' is the wave's along-baseline projection;")
    print("  if the wave is oblique to the baseline, |speed| > true speed.")
    print("- Intervals where correlation is < 0.4 are unreliable; > 0.7 is strong.")

    # Optional paired-Doppler overlay plot
    if args.overlay_plot is not None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(11, 5), dpi=120)
            ax.plot(t_a, y_a, label=args.name1, linewidth=1.0)
            ax.plot(t_b, y_b, label=args.name2, linewidth=1.0, alpha=0.85)
            ax.set_xlabel("UTC time")
            ax.set_ylabel("Doppler (Hz)")
            title = f"Paired Doppler overlay: {args.name1} vs {args.name2}"
            if args.smooth is not None:
                title += f"  (smoothed {args.smooth:g}s)"
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best")
            fig.autofmt_xdate()
            fig.tight_layout()
            fig.savefig(args.overlay_plot)
            plt.close(fig)
            print(f"\nWrote paired-Doppler overlay to {args.overlay_plot}")
        except ImportError:
            print(f"\nWARNING: matplotlib not available; cannot write overlay plot")


if __name__ == "__main__":
    main()
