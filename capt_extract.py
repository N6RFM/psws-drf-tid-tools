#!/usr/bin/env python3
"""
capt_extract.py — Constrained Adaptive Phase Tracking (CAPT) extractor
Version: 0.1.0

Reads a CAPT seed JSON (from tid_spect_click.py S key) and a Digital RF
directory, then extracts a Doppler-vs-time CSV using a Kalman filter that
propagates phase forward and backward from the seed region.

The seed clicks define the initial carrier position and approximate period.
The Kalman filter state is [doppler_hz, doppler_rate_hz_per_s]. Process
noise is tuned to TID physics — slow, smooth carrier evolution. Measurement
noise is estimated from the FFT SNR at each block.

Usage:
    python3 capt_extract.py seed.json --drf-dir /path/to/drf [options]

Examples:
    python3 capt_extract.py examples/tid_event_20260119/n6rfm_tid_zoom_clean_capt_seed.json \\
        --drf-dir ~/Downloads/tid_event_20260119/n6rfm \\
        --start 2026-01-19T00:00:00Z --end 2026-01-19T01:15:00Z \\
        --output examples/tid_event_20260119/n6rfm_capt_tid.csv

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

__version__ = "0.1.0"

# ── Kalman filter constants (TID physics) ─────────────────────────────────────
# State: [doppler_hz, doppler_rate_hz_per_s]
# Typical MSTID: period 20-60 min, amplitude 0.1-2 Hz
# Max rate of change: ~2 Hz / (20 min * 60) ≈ 0.0017 Hz/s
DT_S = 60.0             # nominal block cadence (seconds)
PROC_NOISE_HZ = 0.02    # process noise on doppler (Hz per sqrt(step))
PROC_NOISE_RATE = 2e-4  # process noise on rate (Hz/s per sqrt(step))
MAX_STEP_HZ = 0.5       # max Doppler change per block — rejects jumps
SEARCH_BAND_HZ = 5.0    # FFT search band (Hz either side of 0)
INIT_COV = 0.5          # initial state covariance


def load_seed(seed_path):
    """Load and validate CAPT seed JSON."""
    with open(seed_path) as f:
        seed = json.load(f)
    clicks = seed.get("seed_clicks", [])
    if len(clicks) < 2:
        sys.exit(f"ERROR: seed has {len(clicks)} clicks — need ≥2")
    t = np.array([c["t_hours"] for c in clicks])
    d = np.array([c["doppler_hz"] for c in clicks])
    return seed, t, d


def seed_to_initial_state(t_hours, d_hz, t_query_hours):
    """
    Estimate initial Kalman state [doppler_hz, rate_hz_per_s] at t_query
    by fitting a PCHIP spline through the seed clicks and evaluating
    its first derivative.
    """
    interp = PchipInterpolator(t_hours, d_hz, extrapolate=True)
    d0 = float(interp(t_query_hours))
    # rate: derivative of spline in Hz/hour → Hz/s
    rate0 = float(interp(t_query_hours, 1)) / 3600.0
    return np.array([d0, rate0]), interp


def estimate_fft(iq_block, fs_hz, search_lo=None, search_hi=None):
    """FFT peak frequency within search band. Returns (freq_hz, snr_db)."""
    n = len(iq_block)
    if n < 16:
        return np.nan, 0.0
    w = np.hanning(n)
    spec = np.abs(np.fft.fftshift(np.fft.fft(iq_block * w)))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs_hz))
    if search_lo is not None and search_hi is not None:
        mask = (freqs >= search_lo) & (freqs <= search_hi)
    else:
        mask = np.abs(freqs) <= SEARCH_BAND_HZ
    if not mask.any():
        return np.nan, 0.0
    sub = spec[mask]
    sub_freqs = freqs[mask]
    idx = int(np.argmax(sub))
    # Quadratic interpolation
    if 0 < idx < len(sub) - 1:
        a, b, c = sub[idx-1], sub[idx], sub[idx+1]
        denom = a - 2*b + c
        if denom != 0:
            offset = 0.5 * (a - c) / denom
            df = sub_freqs[1] - sub_freqs[0]
            peak = sub_freqs[idx] + offset * df
        else:
            peak = sub_freqs[idx]
    else:
        peak = sub_freqs[idx]
    snr = 20 * np.log10(sub[idx] / (np.median(sub) + 1e-12))
    return float(peak), float(snr)


def estimate_autocorr(iq_block, fs_hz):
    """Lag-1 complex autocorrelation instantaneous frequency."""
    if len(iq_block) < 4:
        return np.nan, 0.0
    x = np.asarray(iq_block, dtype=complex)
    R1 = np.sum(x[1:] * np.conj(x[:-1]))
    freq = float(np.angle(R1) / (2 * np.pi * (1.0 / fs_hz)))
    snr = 20 * np.log10(np.abs(R1) / (np.std(np.abs(x)) + 1e-12))
    return freq, float(snr)


def kalman_step(x, P, z, dt, meas_noise_var):
    """
    One Kalman filter predict+update step.

    State: x = [doppler_hz, doppler_rate_hz_per_s]
    F = [[1, dt], [0, 1]]  (constant-rate model)
    H = [1, 0]             (we observe doppler only)

    Returns updated (x, P, innovation).
    """
    # Predict
    F = np.array([[1.0, dt], [0.0, 1.0]])
    Q = np.array([[PROC_NOISE_HZ**2 * dt, 0.0],
                  [0.0, PROC_NOISE_RATE**2 * dt]])
    x_pred = F @ x
    P_pred = F @ P @ F.T + Q

    # Update (if measurement valid)
    if np.isnan(z):
        return x_pred, P_pred, np.nan

    H = np.array([[1.0, 0.0]])
    R = np.array([[meas_noise_var]])
    y = z - H @ x_pred                      # innovation
    S = H @ P_pred @ H.T + R
    K = P_pred @ H.T @ np.linalg.inv(S)     # Kalman gain
    x_upd = x_pred + (K @ y).flatten()
    P_upd = (np.eye(2) - K @ H) @ P_pred
    return x_upd, P_upd, float(y[0])


def snr_to_meas_noise(snr_db):
    """Convert SNR dB to measurement noise variance (heuristic)."""
    # Low SNR → high noise → trust prediction more
    # High SNR → low noise → trust measurement more
    # Tuned so SNR=30dB → var=0.01 Hz², SNR=15dB → var=0.5 Hz²
    snr_lin = max(10 ** (snr_db / 20.0), 1.0)
    return max(0.005, 2.0 / snr_lin)


def extract_capt(drf_dir, subchannel, start_utc, end_utc,
                 seed_t_hours, seed_d_hz, dt_s=DT_S,
                 max_step_hz=MAX_STEP_HZ,
                 method='fft',
                 period_hint_s=None, verbose=False):
    """
    Main CAPT extraction loop.

    Returns a DataFrame with columns: timestamp_utc, doppler_hz, snr_db
    """
    try:
        import digital_rf as drf_lib
    except ImportError:
        sys.exit("ERROR: digital_rf not installed. "
                 "pip install digital_rf")

    reader = drf_lib.DigitalRFReader(str(drf_dir))
    channels = reader.get_channels()
    if not channels:
        sys.exit(f"ERROR: no channels found in {drf_dir}")
    channel = channels[0]

    props = reader.get_properties(channel)
    fs = props['samples_per_second']
    block_samples = int(dt_s * fs)

    # Convert times to sample indices
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    t0_s = int((start_utc - epoch).total_seconds())
    t1_s = int((end_utc - epoch).total_seconds())
    t0_samp = t0_s * int(fs)
    t1_samp = t1_s * int(fs)

    # Build block timestamps
    block_starts = np.arange(t0_samp, t1_samp, block_samples)
    n_blocks = len(block_starts)
    if n_blocks == 0:
        sys.exit("ERROR: no blocks in requested window")

    # Seed region: find blocks that fall within seed click time range
    seed_t0_h = seed_t_hours.min()
    seed_t1_h = seed_t_hours.max()

    def samp_to_hours(samp):
        utc_s = samp / float(fs)
        dt = datetime.fromtimestamp(utc_s, tz=timezone.utc)
        return dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # ── Pass 1: extract raw FFT measurements for all blocks ──────────────────
    if verbose:
        print(f"  Extracting {n_blocks} blocks at {dt_s}s cadence...")

    raw_t = []
    raw_d = []
    raw_snr = []
    raw_ts = []

    for i, samp0 in enumerate(block_starts):
        samp1 = samp0 + block_samples
        try:
            iq = reader.read_vector(samp0, block_samples, channel,
                                    sub_channel=subchannel)
        except Exception:
            raw_d.append(np.nan)
            raw_snr.append(0.0)
            raw_t.append(samp_to_hours(samp0 + block_samples // 2))
            raw_ts.append(datetime.fromtimestamp(
                (samp0 + block_samples // 2) / float(fs), tz=timezone.utc))
            continue

        t_mid = samp_to_hours(samp0 + block_samples // 2)
        if method == 'autocorr':
            freq, snr = estimate_autocorr(iq, float(fs))
        else:
            freq, snr = estimate_fft(iq, float(fs))
        raw_t.append(t_mid)
        raw_d.append(freq)
        raw_snr.append(snr)
        raw_ts.append(datetime.fromtimestamp(
            (samp0 + block_samples // 2) / float(fs), tz=timezone.utc))

        if verbose and i % 20 == 0:
            print(f"    block {i+1}/{n_blocks}  "
                  f"t={t_mid:.3f}h  fft={freq:.3f}Hz  snr={snr:.1f}dB")

    raw_t = np.array(raw_t)
    raw_d = np.array(raw_d)
    raw_snr = np.array(raw_snr)

    # ── Seed-method: replace raw measurements with spline values ──────────────
    if method == 'seed':
        # Evaluate seed spline at every block timestamp
        # Uses a fixed low measurement noise — trusts the user clicks
        _, seed_interp_full = seed_to_initial_state(
            seed_t_hours, seed_d_hz, seed_t_hours.mean())
        raw_d = np.array([float(seed_interp_full(t)) for t in raw_t])
        # Low SNR outside seed region to increase measurement noise
        # (extrapolation less trusted than interpolation)
        seed_t0 = seed_t_hours.min()
        seed_t1 = seed_t_hours.max()
        raw_snr = np.where(
            (raw_t >= seed_t0) & (raw_t <= seed_t1),
            50.0,   # inside seed region: high confidence
            25.0    # outside seed region: lower confidence
        )
        if verbose:
            print(f'  Seed method: using PCHIP spline as measurements')
            print(f'  Seed region: {seed_t0:.3f}–{seed_t1:.3f}h')

    # ── Pass 2: Kalman filter forward from seed midpoint ─────────────────────
    seed_mid_h = (seed_t0_h + seed_t1_h) / 2.0

    # Find block closest to seed midpoint
    seed_block_idx = int(np.argmin(np.abs(raw_t - seed_mid_h)))

    # Initial state from seed spline at seed midpoint
    x0, seed_interp = seed_to_initial_state(seed_t_hours, seed_d_hz,
                                             seed_mid_h)
    P0 = INIT_COV * np.eye(2)

    if verbose:
        print(f"\n  Seed midpoint: t={seed_mid_h:.3f}h  "
              f"d0={x0[0]:.3f}Hz  rate={x0[1]*1000:.3f}mHz/s")
        print(f"  Seed block index: {seed_block_idx}")

    capt_d = np.full(n_blocks, np.nan)
    capt_snr = raw_snr.copy()

    # Forward pass (seed_block_idx → end)
    x, P = x0.copy(), P0.copy()
    for i in range(seed_block_idx, n_blocks):
        z_raw = raw_d[i]
        meas_var = snr_to_meas_noise(raw_snr[i]) if not np.isnan(raw_snr[i]) else 1.0

        # Reject measurement if it's too far from prediction (wrong-peak lock)
        if not np.isnan(z_raw) and abs(z_raw - x[0]) > max_step_hz:
            z = np.nan  # use prediction only
        else:
            z = z_raw

        x, P, innov = kalman_step(x, P, z, DT_S, meas_var)
        capt_d[i] = x[0]

    # Backward pass (seed_block_idx-1 → start)
    # Run Kalman on reversed time series then flip
    x, P = x0.copy(), P0.copy()
    for i in range(seed_block_idx - 1, -1, -1):
        z_raw = raw_d[i]
        meas_var = snr_to_meas_noise(raw_snr[i]) if not np.isnan(raw_snr[i]) else 1.0
        if not np.isnan(z_raw) and abs(z_raw - x[0]) > max_step_hz:
            z = np.nan
        else:
            z = z_raw
        x, P, innov = kalman_step(x, P, z, DT_S, meas_var)
        capt_d[i] = x[0]

    # ── Build output DataFrame ────────────────────────────────────────────────
    df = pd.DataFrame({
        "timestamp_utc": [ts.strftime("%Y-%m-%dT%H:%M:%SZ") for ts in raw_ts],
        "doppler_hz":    np.round(capt_d, 4),
        "snr_db":        np.round(capt_snr, 1),
    })
    return df


def main():
    p = argparse.ArgumentParser(
        description="CAPT — Constrained Adaptive Phase Tracking extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("seed", metavar="SEED_JSON",
                   help="CAPT seed JSON from tid_spect_click.py (S key)")
    p.add_argument("--drf-dir", required=True, metavar="DIR",
                   help="Digital RF directory for this station")
    p.add_argument("--subchannel", type=int, default=0, metavar="N",
                   help="DRF subchannel index (default: 0)")
    p.add_argument("--start", default=None, metavar="ISO",
                   help="Start time UTC (ISO 8601, e.g. 2026-01-19T00:00:00Z). "
                        "Defaults to t_start from seed sidecar axes or DRF start.")
    p.add_argument("--end", default=None, metavar="ISO",
                   help="End time UTC. Defaults to t_end from seed or DRF end.")
    p.add_argument("--cadence", type=float, default=60.0, metavar="S",
                   help="Block cadence in seconds (default: 60)")
    p.add_argument("--output", default=None, metavar="CSV",
                   help="Output CSV path. Default: {seed_stem}_capt_tid.csv")
    p.add_argument("--method", default="fft",
                   choices=["fft", "seed", "autocorr"],
                   help="Measurement source for Kalman filter. "
                        "fft: FFT peak (default). "
                        "seed: PCHIP spline through seed clicks — no FFT, "
                        "Kalman smooths and extrapolates user-defined trace. "
                        "autocorr: lag-1 complex autocorrelation.")
    p.add_argument("--max-step", type=float, default=MAX_STEP_HZ, metavar="HZ",
                   help=f"Max Doppler jump per block before rejecting measurement "
                        f"(default: {MAX_STEP_HZ} Hz)")
    p.add_argument("--verbose", action="store_true",
                   help="Print block-by-block progress")
    p.add_argument("--version", action="version",
                   version=f"capt_extract.py {__version__}")
    args = p.parse_args()

    seed_path = Path(args.seed)
    if not seed_path.exists():
        sys.exit(f"ERROR: seed file not found: {seed_path}")

    seed, seed_t, seed_d = load_seed(seed_path)

    # Determine output path
    out_path = Path(args.output) if args.output else \
        seed_path.with_name(seed_path.stem.replace("_capt_seed", "") + "_capt_tid.csv")

    # Parse start/end times
    def parse_iso(s):
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        sys.exit(f"ERROR: could not parse time: {s}")

    if args.start:
        start_utc = parse_iso(args.start)
    elif "t_start_utc_hours" in seed:
        h = seed["t_start_utc_hours"]
        date_s = seed.get("date_utc", "2026-01-19")
        base = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_utc = base.replace(hour=int(h), minute=int((h % 1) * 60),
                                  second=int((h * 3600) % 60))
    else:
        sys.exit("ERROR: --start required (no t_start_utc_hours in seed)")

    if args.end:
        end_utc = parse_iso(args.end)
    elif "t_end_utc_hours" in seed:
        h = seed["t_end_utc_hours"]
        date_s = seed.get("date_utc", "2026-01-19")
        base = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_utc = base.replace(hour=int(h), minute=int((h % 1) * 60),
                                second=int((h * 3600) % 60))
    else:
        sys.exit("ERROR: --end required (no t_end_utc_hours in seed)")


    print(f"capt_extract.py {__version__}")
    print(f"  Seed:     {seed_path.name}  ({len(seed_t)} clicks)")
    print(f"  Station:  {seed.get('station', '?')}")
    print(f"  DRF:      {args.drf_dir}")
    print(f"  Window:   {start_utc.strftime('%H:%M')}–{end_utc.strftime('%H:%M')} UTC")
    print(f"  Cadence:  {args.cadence}s  max_step={args.max_step}Hz  method={args.method}")

    df = extract_capt(
        drf_dir=args.drf_dir,
        subchannel=args.subchannel,
        start_utc=start_utc,
        end_utc=end_utc,
        seed_t_hours=seed_t,
        seed_d_hz=seed_d,
        dt_s=args.cadence,
        max_step_hz=args.max_step,
        method=args.method,
        verbose=args.verbose,
    )

    df.to_csv(out_path, index=False)
    print(f"\nCAPT CSV written: {out_path}  ({len(df)} rows)")
    print(f"  Doppler range: {df.doppler_hz.min():.3f} – "
          f"{df.doppler_hz.max():.3f} Hz")
    print(f"  SNR range:     {df.snr_db.min():.1f} – "
          f"{df.snr_db.max():.1f} dB")


if __name__ == "__main__":
    main()
