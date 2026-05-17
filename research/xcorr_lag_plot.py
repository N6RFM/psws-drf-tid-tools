#!/usr/bin/env python3
"""
xcorr_lag_plot.py — cross-correlation vs lag, for one or more station pairs.

RESEARCH-BRANCH TOOL. Not part of the released toolkit. Not verified
for `main`. Exists to (a) produce the curve-shape figure discussed in
docs/METHODOLOGY.md "Interpreting the correlation curve", and (b) be a
building block for the FFT-vs-autocorrelation comparison harness.

It reproduces the SAME correlation the toolkit computes for lag
estimation, so the plotted curve is the curve the lag-finder actually
sees:
  - resample both series to a common cadence (dt)
  - mean-subtract, then z-normalize each
  - R(tau) = scipy.signal.correlate(y', x', mode='full'), normalized
    to a coefficient in [-1, 1]
  - NO bandpass (toolkit default use_bandpass: false)

This deliberately does not reimplement Doppler extraction. It consumes
already-extracted Doppler CSVs (the output of drf_to_doppler.py, or
any CSV with a UTC time column and a Doppler-Hz column).

Usage:
  xcorr_lag_plot.py PAIR [PAIR ...] --out plot.png
where each PAIR is csvA:csvB or csvA:csvB:Label

CSV format expected: a header row; a time column (ISO8601 or epoch
seconds) and a Doppler column. Column names are auto-detected from a
small candidate list, or set explicitly with --time-col / --dop-col.
"""

import argparse
import sys
import numpy as np

try:
    import pandas as pd
    from scipy.signal import correlate
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as e:
    sys.exit(f"missing dependency: {e} (pip install pandas scipy matplotlib)")


TIME_CANDIDATES = ["utc", "time", "timestamp", "datetime", "t", "epoch"]
DOP_CANDIDATES = ["doppler_hz", "doppler", "dop_hz", "freq_offset_hz",
                  "f_hz", "dop", "hz"]


def _pick(cols, candidates, what):
    low = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand in low:
            return low[cand]
    raise SystemExit(
        f"could not auto-detect the {what} column from {list(cols)}; "
        f"pass it explicitly")


def load_doppler(path, time_col=None, dop_col=None):
    df = pd.read_csv(path)
    tc = time_col or _pick(df.columns, TIME_CANDIDATES, "time")
    dc = dop_col or _pick(df.columns, DOP_CANDIDATES, "Doppler")
    # time -> seconds
    t = df[tc]
    if np.issubdtype(t.dtype, np.number):
        tsec = t.astype(float).to_numpy()
    else:
        tsec = pd.to_datetime(t, utc=True, errors="coerce").astype(
            "int64").to_numpy() / 1e9
    y = df[dc].astype(float).to_numpy()
    m = np.isfinite(tsec) & np.isfinite(y)
    tsec, y = tsec[m], y[m]
    order = np.argsort(tsec)
    return tsec[order], y[order]


def resample_common(ta, ya, tb, yb):
    """Resample both onto a common uniform grid over their overlap."""
    t0 = max(ta[0], tb[0])
    t1 = min(ta[-1], tb[-1])
    if t1 <= t0:
        raise SystemExit("series do not overlap in time")
    # cadence: median sample spacing of the coarser series
    dt = float(max(np.median(np.diff(ta)), np.median(np.diff(tb))))
    if not np.isfinite(dt) or dt <= 0:
        raise SystemExit("could not determine a positive cadence")
    grid = np.arange(t0, t1, dt)
    ga = np.interp(grid, ta, ya)
    gb = np.interp(grid, tb, yb)
    return grid, ga, gb, dt


def znorm(x):
    x = x - np.mean(x)
    s = np.std(x)
    return x / s if s > 0 else x


def xcorr_coeff(x, y):
    """Normalized cross-correlation coefficient vs lag.

    Matches the toolkit: mean-subtract, z-normalize, full correlate,
    divide by N so the zero-shift value of identical z-normed series
    is ~1. Returns (lags_in_samples, r) with r in [-1, 1].
    """
    xz = znorm(x)
    yz = znorm(y)
    n = len(xz)
    r = correlate(yz, xz, mode="full") / n
    lags = np.arange(-(n - 1), n)
    return lags, r


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="+",
                    help="csvA:csvB or csvA:csvB:Label")
    ap.add_argument("--out", default="xcorr_lag.png")
    ap.add_argument("--time-col", default=None)
    ap.add_argument("--dop-col", default=None)
    ap.add_argument("--max-lag-min", type=float, default=None,
                    help="restrict x-axis to +/- this many minutes")
    ap.add_argument("--title", default="Cross-correlation vs lag")
    args = ap.parse_args()

    fig, ax = plt.subplots(figsize=(9, 5.5))

    for spec in args.pairs:
        parts = spec.split(":")
        if len(parts) < 2:
            raise SystemExit(f"bad pair spec '{spec}' (need csvA:csvB[:Label])")
        ca, cb = parts[0], parts[1]
        label = parts[2] if len(parts) > 2 else f"{ca} vs {cb}"

        ta, ya = load_doppler(ca, args.time_col, args.dop_col)
        tb, yb = load_doppler(cb, args.time_col, args.dop_col)
        grid, ga, gb, dt = resample_common(ta, ya, tb, yb)
        lags, r = xcorr_coeff(ga, gb)
        lag_min = lags * dt / 60.0

        if args.max_lag_min is not None:
            keep = np.abs(lag_min) <= args.max_lag_min
            lag_min, r = lag_min[keep], r[keep]

        peak_i = int(np.argmax(r))
        ax.plot(lag_min, r, lw=1.4, label=f"{label}  (peak r={r[peak_i]:.3f} "
                                          f"@ {lag_min[peak_i]:+.1f} min)")
        ax.plot(lag_min[peak_i], r[peak_i], "o", ms=5)

    ax.axhline(0, color="0.6", lw=0.8)
    ax.axvline(0, color="0.6", lw=0.8)
    ax.set_xlabel("Lag (minutes)")
    ax.set_ylabel("Cross-correlation coefficient")
    ax.set_title(args.title)
    ax.set_ylim(-1.05, 1.05)
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
