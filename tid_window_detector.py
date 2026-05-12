r"""
tid_window_detector.py — automatic TID time-window detector


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
Given a Doppler-vs-time CSV from drf_to_doppler.py -- typically a
24-hour survey at 60-second cadence -- this tool scans for time windows
where a TID-like oscillation is present, scores each window by signal
quality, and ranks them so you can pick the best ones for downstream
cross-correlation analysis.

This is most useful when you don't yet know WHEN a TID happened on your
recording day. Run it on a 24-hour survey from your station and it
returns a short list of candidate event windows ranked by how clean
the wave signature looks. You can then re-extract those windows at
higher cadence with drf_to_doppler.py and run tid_pair.py or tid_doa.py.

METHOD
======
The detection pipeline:

  1. Load the Doppler-vs-time CSV.
  2. Apply a high-pass filter to remove the slow diurnal trend (which
     would otherwise dominate spectral analysis).
  3. Slide a window of duration --slice-minutes across the day, step by
     --slice-step-minutes.
  4. For each slice, compute the Fourier spectrum and measure:

       in_power   = sum of spectral power within the TID period band
                    (--period-min to --period-max)
       out_power  = sum of spectral power outside that band but
                    inside the analyzable range
       SNR        = in_power / out_power
       concentration = 1 - normalized_entropy(in-band spectrum)
                       (high = power concentrated at one period;
                        low = smeared across the band)

  5. Combined score = tanh(log10(SNR + 0.1)) * concentration.
     The tanh squashes very large SNRs so they don't dominate the
     ranking; concentration penalizes windows where the energy is
     diffuse.

  6. Merge contiguous high-score slices (slices with score >
     --min-score) into windows; keep the best score per merged window.

  7. Compute the solar elevation at the window's midpoint and flag
     windows that straddle a sunrise/sunset terminator. Terminator
     passages produce large Doppler swings that look TID-like but
     aren't propagating waves.

OUTPUT
======
For each top window the script reports:

    Start UTC, End UTC      -- the time window
    Period                  -- dominant period within the window (min)
    SNR                     -- in-band over out-of-band spectral power
    Conc                    -- spectral concentration, 0-1
    Score                   -- combined score, 0-1
    flag                    -- "clean" or "terminator-overlap"

The PNG (if --plot) shows the full 24-hour Doppler trace, a
spectrogram in the TID period band, and the detected windows
highlighted.

If --write-configs is given, the script writes one ready-to-run
tid_doa.py config JSON per top window into that directory, with
period_band_seconds, max_lag_seconds, and event_start/end pre-filled
based on the detected window. You then add the companion station files
and run tid_doa.py.

PARAMETER GUIDANCE
==================
  --period-min / --period-max
      The period range to search, in minutes.
        15-90  (default): standard MSTID / mixed range
        30-120: LSTID-focused
        5-30:  fast acoustic-gravity or short-period MSTID

  --slice-minutes
      Each slice is one Fourier-analysis chunk. Must be at least 2-3
      times longer than --period-max for the FFT to resolve those
      periods. Default 120 min works for periods up to ~60 min; use
      240 min for LSTID work.

  --slice-step-minutes
      How far to step the slice between analyses. Smaller = finer
      time resolution but more redundant work. Default 30 min is fine.

  --min-score
      Score threshold for considering a slice a candidate. Default
      0.15. Lower to find weaker events; higher to be more selective.
      In practice, real TID wavetrains score 0.3-0.5; background ranges
      from 0.0-0.1.

  --lat / --lon
      Your receiver's coordinates. Used only for terminator detection
      (computing approximate sunrise/sunset times for the WWV path
      midpoint).

USAGE
=====
Detect candidate TID windows in a 24-hour survey:

    python tid_window_detector.py survey.csv         --lat 32.94 --lon -97.21         --plot survey_windows.png         --top 5

Find LSTIDs only:

    python tid_window_detector.py survey.csv         --lat 32.94 --lon -97.21         --period-min 60 --period-max 180         --slice-minutes 240

Generate DOA config templates for the top windows:

    python tid_window_detector.py survey.csv         --lat 32.94 --lon -97.21         --top 3 --write-configs ./configs/

REQUIREMENTS
============
    pip install numpy scipy pandas matplotlib

SEE ALSO
========
    drf_to_doppler.py      generate the survey CSV from raw DRF
    tid_pair.py            two-station follow-up analysis
    tid_doa.py             multi-station follow-up analysis
"""

import argparse
import json
import math
import sys
from datetime import timezone

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, spectrogram


# ---------------------------------------------------------------------------
# Sun position (low-precision, sufficient for terminator timing)
# ---------------------------------------------------------------------------
def solar_elevation_deg(dt_utc, lat, lon):
    """Approximate solar elevation angle in degrees. Good to ~0.5°."""
    # Days since J2000.0
    j2000 = pd.Timestamp("2000-01-01T12:00:00", tz="UTC")
    n = (dt_utc - j2000).total_seconds() / 86400.0
    # Mean longitude and anomaly of the sun
    L = (280.460 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    # Right ascension and declination
    dec = math.asin(math.sin(eps) * math.sin(lam))
    # Hour angle
    gmst = (18.697374558 + 24.06570982441908 * n) % 24    # hours
    lmst_hours = (gmst + lon / 15.0) % 24
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    ha = math.radians(lmst_hours * 15.0) - ra
    lat_r = math.radians(lat)
    sin_alt = math.sin(lat_r) * math.sin(dec) + math.cos(lat_r) * math.cos(dec) * math.cos(ha)
    return math.degrees(math.asin(max(-1, min(1, sin_alt))))


def is_terminator_window(t0, t1, lat, lon, threshold_deg=10):
    """True if the window straddles sunrise/sunset (sun crosses ±threshold)."""
    samples = pd.date_range(t0, t1, periods=12)
    elevs = np.array([solar_elevation_deg(t, lat, lon) for t in samples])
    crosses_zero = (elevs.min() < threshold_deg) and (elevs.max() > -threshold_deg) and \
                   (elevs.min() * elevs.max() < threshold_deg ** 2 * 0.1)
    span = elevs.max() - elevs.min()
    # Strong terminator passage if elevation changes a lot AND crosses zero
    return crosses_zero and span > 15


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def detect_tid_windows(df, period_band_s=(900, 5400),
                        slice_minutes=120, slice_step_minutes=30,
                        min_score=0.4):
    """Slide a window across the trace, score each slice."""
    df = df.dropna(subset=["doppler_hz"]).copy()
    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    times = df["timestamp_utc"].to_numpy()
    sig = df["doppler_hz"].to_numpy()

    # Cadence (use Timedelta.total_seconds for version-independent precision)
    diffs_s = np.array([
        (df["timestamp_utc"].iloc[i+1] - df["timestamp_utc"].iloc[i]).total_seconds()
        for i in range(min(50, len(df)-1))
    ])
    dt = float(np.median(diffs_s))
    fs = 1.0 / dt

    # Pre-detrend with high-pass to kill diurnal trend
    nyq = 0.5 * fs
    hp_cut = (1.0 / (period_band_s[1] * 2)) / nyq
    if 0 < hp_cut < 1:
        b, a = butter(2, hp_cut, btype="high")
        sig = filtfilt(b, a, sig)

    slice_n = int(slice_minutes * 60 / dt)
    step_n = int(slice_step_minutes * 60 / dt)

    candidates = []
    for start in range(0, len(sig) - slice_n, step_n):
        end = start + slice_n
        seg = sig[start:end]
        if np.any(np.isnan(seg)):
            continue

        # FFT of segment
        seg_dm = seg - np.mean(seg)
        seg_dm *= np.hanning(len(seg_dm))
        spec = np.abs(np.fft.rfft(seg_dm))
        freqs = np.fft.rfftfreq(len(seg_dm), d=dt)

        in_band = (freqs >= 1.0 / period_band_s[1]) & (freqs <= 1.0 / period_band_s[0])
        out_band = (freqs > 1.0 / period_band_s[0]) & (freqs < fs / 4)

        if not in_band.any() or not out_band.any():
            continue

        in_power = np.sum(spec[in_band] ** 2)
        out_power = np.sum(spec[out_band] ** 2) + 1e-12

        # SNR: in-band vs out-of-band
        snr = in_power / out_power

        # Spectral concentration: how peaked is the in-band spectrum?
        in_spec = spec[in_band]
        if in_spec.sum() > 0:
            p = in_spec / in_spec.sum()
            entropy = -np.sum(p * np.log(p + 1e-12))
            max_entropy = np.log(len(p))
            concentration = 1.0 - entropy / max_entropy   # 0=flat, 1=spike
        else:
            concentration = 0.0

        # Dominant period inside the band
        dom_idx = int(np.argmax(in_spec))
        dom_freq = freqs[in_band][dom_idx]
        dom_period_s = 1.0 / dom_freq if dom_freq > 0 else 0

        # Combined score: SNR (log scaled) times concentration
        score = math.tanh(math.log10(snr + 0.1)) * concentration

        candidates.append({
            "start": pd.Timestamp(times[start]),
            "end": pd.Timestamp(times[end - 1]),
            "snr": snr,
            "concentration": concentration,
            "dominant_period_s": dom_period_s,
            "score": score,
        })

    return candidates


def merge_overlapping(candidates, min_score):
    """Merge contiguous high-score slices into single windows, keeping best."""
    high = sorted([c for c in candidates if c["score"] >= min_score],
                  key=lambda c: c["start"])
    merged = []
    for c in high:
        if merged and c["start"] <= merged[-1]["end"]:
            # extend
            merged[-1]["end"] = max(merged[-1]["end"], c["end"])
            if c["score"] > merged[-1]["score"]:
                merged[-1]["score"] = c["score"]
                merged[-1]["dominant_period_s"] = c["dominant_period_s"]
                merged[-1]["snr"] = c["snr"]
                merged[-1]["concentration"] = c["concentration"]
        else:
            merged.append(dict(c))
    return merged


def filter_terminators(windows, lat, lon):
    out = []
    for w in windows:
        if is_terminator_window(w["start"], w["end"], lat, lon):
            w["flag"] = "terminator-overlap"
        else:
            w["flag"] = "clean"
        out.append(w)
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def report(windows, top_n):
    clean = [w for w in windows if w["flag"] == "clean"]
    flagged = [w for w in windows if w["flag"] != "clean"]
    clean.sort(key=lambda w: w["score"], reverse=True)
    flagged.sort(key=lambda w: w["score"], reverse=True)

    print(f"\n{'#':>2} {'Start (UTC)':<20} {'End (UTC)':<20} "
          f"{'Period':>7} {'SNR':>6} {'Conc':>5} {'Score':>6}")
    print("-" * 78)
    rank = 1
    for w in clean[:top_n]:
        print(f"{rank:>2} {str(w['start'])[:19]:<20} {str(w['end'])[:19]:<20} "
              f"{w['dominant_period_s']/60:>5.1f}m "
              f"{w['snr']:>6.1f} {w['concentration']:>5.2f} {w['score']:>6.3f}")
        rank += 1

    if flagged:
        print(f"\nFlagged windows (likely terminator contamination):")
        for w in flagged[:3]:
            print(f"   {str(w['start'])[:19]} - {str(w['end'])[:19]}  "
                  f"period={w['dominant_period_s']/60:.0f}min "
                  f"score={w['score']:.2f}  [{w['flag']}]")

    return clean[:top_n]


def write_doa_configs(windows, station_csv, lat, lon, out_dir):
    """Write a starter tid_doa.py config for each top window."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for i, w in enumerate(windows, 1):
        period_s = w["dominant_period_s"]
        # Period band: ±50% around dominant
        band = [max(600, period_s * 0.5), min(7200, period_s * 2.0)]
        # Trim 15 min from each end
        t0 = w["start"] + pd.Timedelta(minutes=15)
        t1 = w["end"]   - pd.Timedelta(minutes=15)
        cfg = {
            "_note": "Replace placeholder companion stations with real ones.",
            "event_start_utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event_end_utc":   t1.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "resample_seconds": 10,
            "period_band_seconds": [round(band[0]), round(band[1])],
            "max_lag_seconds": round(period_s / 2.5),
            "stations": [
                {"name": "ME", "file": station_csv, "lat": lat, "lon": lon},
                {"name": "COMPANION_2", "file": "companion2.csv",
                 "lat": 0, "lon": 0},
                {"name": "COMPANION_3", "file": "companion3.csv",
                 "lat": 0, "lon": 0},
            ],
        }
        path = f"{out_dir}/window_{i}_event.json"
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
        written.append(path)
    return written


def make_plot(df, candidates, top_windows, plot_path, period_band_s):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.dates import DateFormatter
    except ImportError:
        print("matplotlib not available, skipping plot")
        return

    df = df.dropna(subset=["doppler_hz"])
    times = df["timestamp_utc"]
    sig = df["doppler_hz"].to_numpy()
    diffs_s = np.array([
        (df["timestamp_utc"].iloc[i+1] - df["timestamp_utc"].iloc[i]).total_seconds()
        for i in range(min(50, len(df)-1))
    ])
    dt = float(np.median(diffs_s))
    fs = 1.0 / dt

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), sharex=True,
                                         gridspec_kw={"height_ratios": [1, 2, 0.5]})

    # Doppler trace
    ax1.plot(times, sig, lw=0.5, color="tab:blue")
    ax1.set_ylabel("Doppler (Hz)")
    ax1.grid(alpha=0.3)
    ax1.set_title("Doppler trace, spectrogram, and detected TID windows")

    # Spectrogram in TID period band
    nperseg = min(int(7200 / dt), len(sig) // 4)   # 2-hour FFT window
    if nperseg >= 64 and len(sig) > nperseg:
        f, t_spec, S = spectrogram(sig - np.nanmean(sig), fs=fs,
                                    nperseg=nperseg, noverlap=nperseg * 7 // 8,
                                    scaling="spectrum")
        # Convert to periods in minutes
        with np.errstate(divide="ignore"):
            periods_min = 1.0 / f / 60.0
        mask = (periods_min >= period_band_s[0] / 60) & (periods_min <= period_band_s[1] / 60)
        S_sub = S[mask, :]
        periods_sub = periods_min[mask]
        if S_sub.size > 0:
            extent = [times.iloc[0],
                      times.iloc[0] + pd.Timedelta(seconds=t_spec[-1]),
                      periods_sub.min(), periods_sub.max()]
            ax2.imshow(10 * np.log10(S_sub + 1e-20),
                       aspect="auto", origin="lower",
                       extent=[matplotlib.dates.date2num(extent[0]),
                               matplotlib.dates.date2num(extent[1]),
                               extent[2], extent[3]],
                       cmap="viridis")
            ax2.xaxis_date()
    ax2.set_ylabel("Period (min)")
    ax2.grid(alpha=0.3, color="white")

    # Window bars
    ax3.set_ylim(0, 1)
    ax3.set_yticks([])
    for w in candidates:
        color = "tab:gray"
        alpha = 0.15 + 0.5 * max(0, w["score"])
        ax3.axvspan(w["start"], w["end"], color=color, alpha=alpha)
    for i, w in enumerate(top_windows, 1):
        ax3.axvspan(w["start"], w["end"], color="tab:red", alpha=0.4)
        mid = w["start"] + (w["end"] - w["start"]) / 2
        ax3.text(mid, 0.5, f"#{i}", ha="center", va="center",
                 fontsize=10, fontweight="bold", color="white")
    ax3.set_xlabel("UTC")

    ax1.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    plt.tight_layout()
    plt.savefig(plot_path, dpi=120)
    plt.close()
    print(f"Plot saved to {plot_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring at the top of the script for full details, "
               "including method and parameter guidance.",
    )
    ap.add_argument("csv",
                    help="Doppler CSV from drf_to_doppler.py (typically a "
                         "24-hour survey at 60-second cadence).")
    ap.add_argument("--lat", type=float, required=True,
                    help="Receiver latitude (decimal degrees). Used only "
                         "for sunrise/sunset terminator detection.")
    ap.add_argument("--lon", type=float, required=True,
                    help="Receiver longitude (decimal degrees).")
    ap.add_argument("--period-min", type=float, default=15,
                    help="Minimum TID period to search for, in minutes. "
                         "Default: 15")
    ap.add_argument("--period-max", type=float, default=90,
                    help="Maximum TID period to search for, in minutes. "
                         "Default: 90. For LSTID work use 120-180.")
    ap.add_argument("--slice-minutes", type=float, default=120,
                    help="Duration of each spectral analysis slice, in "
                         "minutes. Must be >= 2x period-max for the FFT "
                         "to resolve target periods. Default: 120")
    ap.add_argument("--slice-step-minutes", type=float, default=30,
                    help="Step between consecutive slices, in minutes. "
                         "Default: 30")
    ap.add_argument("--min-score", type=float, default=0.15,
                    help="Score threshold for considering a slice a "
                         "candidate. Real TID wavetrains typically score "
                         "0.3-0.5; background 0-0.1. Default: 0.15")
    ap.add_argument("--top", type=int, default=5,
                    help="Maximum number of top windows to report. "
                         "Default: 5")
    ap.add_argument("--plot", default=None,
                    help="Optional PNG path for a diagnostic plot showing "
                         "the Doppler trace, spectrogram in the TID band, "
                         "and the detected windows highlighted.")
    ap.add_argument("--write-configs", default=None,
                    help="Directory in which to write a ready-to-run "
                         "tid_doa.py JSON config for each top window. "
                         "Each config has event window, period_band, and "
                         "max_lag_seconds pre-filled; you fill in the "
                         "companion stations.")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df.columns = [c.lower() for c in df.columns]
    if "timestamp_utc" not in df.columns or "doppler_hz" not in df.columns:
        sys.exit("CSV must contain timestamp_utc and doppler_hz columns")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    period_band = (args.period_min * 60, args.period_max * 60)
    print(f"Loaded {len(df)} samples, "
          f"{df['timestamp_utc'].iloc[0]} to {df['timestamp_utc'].iloc[-1]}")
    print(f"Searching for TIDs with periods {args.period_min}-{args.period_max} min")

    candidates = detect_tid_windows(
        df, period_band_s=period_band,
        slice_minutes=args.slice_minutes,
        slice_step_minutes=args.slice_step_minutes,
        min_score=args.min_score,
    )
    if not candidates:
        sys.exit("No candidate windows found.")
    print(f"Scored {len(candidates)} candidate slices.")

    merged = merge_overlapping(candidates, args.min_score)
    flagged = filter_terminators(merged, args.lat, args.lon)
    top = report(flagged, args.top)

    if args.plot:
        make_plot(df, candidates, top, args.plot, period_band)

    if args.write_configs and top:
        paths = write_doa_configs(top, args.csv, args.lat, args.lon,
                                   args.write_configs)
        print(f"\nWrote {len(paths)} config templates to {args.write_configs}/")
        for p in paths:
            print(f"   {p}")
        print("Edit each config to add real companion stations, then run tid_doa.py.")


if __name__ == "__main__":
    main()
