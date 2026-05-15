r"""
drf_to_doppler.py — extract a Doppler-vs-time CSV from Digital RF I/Q data


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
HamSCI Grape 1-DRF stations record the Fort Collins WWV carrier as
complex baseband I/Q sampled at 10 samples per second, mixed down so the
carrier sits within +/- 5 Hz of zero. Each daily file is stored on disk
in the Digital RF (DRF) format (MIT Haystack's open standard for
streaming RF data) inside a directory like:

    OBS2026-01-19T00-00/
      ch0/
        2026-01-19T00-00-00/   <- hour subdirectories with .h5 data
        2026-01-19T01-00-00/
        ...
        drf_properties.h5      <- channel metadata
        metadata/              <- station info (callsign, grid, freqs)

This tool reads such a directory and produces a CSV of:
    timestamp_utc,  doppler_hz,  snr_db
sampled at a chosen cadence (default 10 s). The Doppler value at each
output sample is estimated by FFT peak-tracking the carrier within the
+/- 5 Hz observation band.

The output CSV is the input format for tid_pair.py and tid_doa.py.

ALGORITHM
=========
For each output sample of duration --decim-seconds (default 10 s):

  1. Read N complex I/Q samples (N = 10 * decim_seconds).
  2. Apply a Hanning window to suppress spectral leakage.
  3. FFT the windowed block.
  4. Find the maximum-magnitude bin within +/- --search-band-hz (default
     5 Hz) of zero.
  5. Apply quadratic interpolation on the three bins centered on the
     peak to estimate sub-bin frequency:

         f_peak = f_bin + 0.5 * (a-c) / (a-2b+c) * df

     where a, b, c are the magnitudes of the bin before/at/after the
     peak. This gives roughly 0.01 Hz precision on a 10-second block.
  6. Estimate SNR as 20*log10(peak / median magnitude) in dB. Median
     (rather than mean) is robust to spurious in-band tones.

This is a "narrowest-bin" tracker rather than a phase-locked loop. It is
robust to brief signal dropouts (each block is independent) but trades
some temporal smoothness for that robustness. Typical SNR > 30 dB
yields ~0.01-0.02 Hz block-to-block noise on the Doppler estimate.

MULTI-SUBCHANNEL DRF
====================
Some stations (notably KA9Q-radio / WSPRdaemon receivers) record multiple
WWV frequencies into a SINGLE DRF channel as parallel "subchannels".
A 10-subchannel station might record 60 kHz, 2.5 / 3.33 / 5 / 7.85 / 10
/ 14.67 / 15 / 20 / 25 MHz simultaneously.

When --subchannel is specified, the script reads that index from the
multi-subchannel data. Single-channel DRF (one frequency only) is auto-
detected and the flag is ignored.

CRITICAL: The mapping from subchannel index to actual frequency varies
between stations. To verify which subchannel is which, read the DRF
metadata:

    python -c "
    import digital_rf as drf
    m = drf.DigitalMetadataReader('./station/ch0/metadata')
    b = m.get_bounds()
    print(m.read(b[0], b[0]+1))
    "

The output contains a 'center_frequencies' array showing which index
corresponds to which MHz value. For example, on N5TNL the array starts
at 2.5 MHz, so 10 MHz is index 4. On KD7EFG the array starts at 60 kHz,
so 10 MHz is index 5. Reading the wrong subchannel produces a noisy
trace that may superficially look like weak signal -- always verify.

USAGE
=====
Single-channel station:

    python drf_to_doppler.py /path/to/station_drf_dir \
        --start 2026-01-19T00:00:00 --end 2026-01-19T01:45:00 \
        --decim-seconds 10 \
        --output station.csv --plot station.png

Multi-subchannel WSPRdaemon station:

    python drf_to_doppler.py ./n5tnl \
        --start 2026-01-19T00:00:00 --end 2026-01-19T01:45:00 \
        --subchannel 4 \
        --output n5tnl.csv --plot n5tnl.png

WHEN TO USE WHAT CADENCE
========================
  --decim-seconds 60   24-hour survey, low resolution. Use for a first-
                       pass look at the whole day; the resulting trace
                       reveals when TIDs are active.
  --decim-seconds 10   Default. Good for TID analysis (TIDs evolve on
                       minutes-to-hours scales).
  --decim-seconds 1    Very high resolution. Useful for capturing prompt
                       solar flare signatures (SFDs) which last seconds
                       to minutes. Larger output file.

SANITY CHECKS
=============
After running, inspect the output PNG:

  - Median SNR in the second panel should be > 30 dB for a usable
    recording. Sub-20 dB sections are fade periods; Doppler estimates
    there are unreliable.
  - Doppler values should generally be within +/- 2 Hz. Excursions
    beyond +/- 5 Hz mean the search band is too narrow or the carrier
    has drifted.
  - Sudden vertical spikes are usually RFI or recording glitches.
    Brief spikes (one sample) get smoothed by downstream bandpass
    filtering; sustained spikes are a problem.
  - For multi-subchannel data, if the trace looks like square-wave
    noise jumping between +/- search_band edges, you've selected an
    EMPTY subchannel. Try a different --subchannel index.

REQUIREMENTS
============
    pip install digital_rf numpy scipy pandas matplotlib
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# digital_rf is required only at runtime, not at import time, so that
# --help works without the package installed.
try:
    import digital_rf as drf
    _HAVE_DRF = True
except ImportError:
    drf = None
    _HAVE_DRF = False


def parse_iso(s):
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def utc_to_drf_sample(dt, sr_num, sr_den):
    """Convert UTC datetime to DRF sample index (samples since 1970-01-01)."""
    epoch_seconds = dt.timestamp()
    return int(round(epoch_seconds * sr_num / sr_den))


def estimate_carrier_freq(iq_block, fs_hz, search_band_hz=5.0):
    """FFT peak frequency of a complex I/Q block, restricted to +/- search_band."""
    n = len(iq_block)
    if n < 16:
        return np.nan, 0.0
    # Window for cleaner peak
    w = np.hanning(n)
    spec = np.fft.fftshift(np.fft.fft(iq_block * w))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs_hz))
    mask = np.abs(freqs) <= search_band_hz
    if not mask.any():
        return np.nan, 0.0
    sub = np.abs(spec[mask])
    sub_freqs = freqs[mask]
    idx = int(np.argmax(sub))
    # Quadratic interpolation for sub-bin precision
    if 0 < idx < len(sub) - 1:
        a, b, c = sub[idx - 1], sub[idx], sub[idx + 1]
        denom = (a - 2 * b + c)
        if denom != 0:
            offset = 0.5 * (a - c) / denom
            df = sub_freqs[1] - sub_freqs[0]
            peak_freq = sub_freqs[idx] + offset * df
        else:
            peak_freq = sub_freqs[idx]
    else:
        peak_freq = sub_freqs[idx]
    snr_db = 20 * np.log10(sub[idx] / (np.median(sub) + 1e-12))
    return float(peak_freq), float(snr_db)



def _apply_smoothing(df, window_seconds, dt_seconds):
    """Apply Savitzky-Golay smoothing to the doppler_hz column.

    Raises ValueError if the window is too small for the chosen
    polynomial order (3).
    """
    from scipy.signal import savgol_filter
    poly_order = 3
    n_samples = int(round(window_seconds / dt_seconds))
    min_window = poly_order + 2
    if n_samples < min_window:
        raise ValueError(
            f"--smooth {window_seconds:g} too small for dt={dt_seconds}s; "
            f"need >= {min_window * dt_seconds:g} sec for poly_order={poly_order}"
        )
    if n_samples % 2 == 0:
        n_samples += 1
    df = df.copy()
    df["doppler_hz"] = savgol_filter(df["doppler_hz"].to_numpy(),
                                       n_samples, poly_order)
    return df, n_samples


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring at the top of the script for full details.",
    )
    ap.add_argument("drf_dir",
                    help="Top-level DRF directory (the one CONTAINING "
                         "'ch0/', not ch0/ itself)")
    ap.add_argument("--channel", default="ch0",
                    help="DRF channel name. Almost always 'ch0' for HamSCI "
                         "Grape stations. Use list_channels in digital_rf to "
                         "check. Default: ch0")
    ap.add_argument("--subchannel", type=int, default=0,
                    help="Subchannel index for multi-subchannel DRF data. "
                         "Single-channel stations: leave at 0. Multi-"
                         "subchannel stations: verify the correct index by "
                         "reading the metadata 'center_frequencies' array "
                         "(see docstring). Default: 0")
    ap.add_argument("--start", required=True,
                    help="UTC start of extraction window in ISO format, "
                         "e.g. '2026-01-19T00:00:00' or '2026-01-19T00:00:00Z'")
    ap.add_argument("--end", required=True,
                    help="UTC end of extraction window in ISO format")
    ap.add_argument("--decim-seconds", type=float, default=10.0,
                    help="Output sample cadence in seconds. Each output "
                         "sample is one FFT block. Use 60 for 24-hour "
                         "surveys; 10 for TID analysis; 1 for prompt flare "
                         "signatures. Default: 10")
    ap.add_argument("--search-band-hz", type=float, default=5.0,
                    help="Half-width of the frequency search window around "
                         "0 Hz, in Hz. The WWV carrier should be within this "
                         "range after baseband mixing. Default: 5.0")
    ap.add_argument("--smooth", type=float, default=None,
                    metavar="N",
                    help="apply Savitzky-Golay smoothing with N-second "
                         "window (default off; recommended: 30 sec for "
                         "noisy stations, never > 1/4 of TID period)")
    ap.add_argument("--output", required=True,
                    help="Output CSV path. Three columns: timestamp_utc, "
                         "doppler_hz, snr_db.")
    ap.add_argument("--plot", default=None,
                    help="Optional PNG path for a quick-look two-panel plot "
                         "(Doppler trace + SNR). Recommended for sanity-"
                         "checking before downstream analysis.")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    t_start = parse_iso(args.start)
    t_end   = parse_iso(args.end)
    if t_end <= t_start:
        sys.exit("end must be after start")

    if not _HAVE_DRF:
        sys.exit("digital_rf not installed. Run: pip install digital_rf")
    reader = drf.DigitalRFReader(args.drf_dir)
    channels = reader.get_channels()
    if args.channel not in channels:
        sys.exit(f"Channel '{args.channel}' not found.  Available: {channels}")

    sr_num, sr_den = reader.get_properties(args.channel)["samples_per_second"].as_integer_ratio()
    fs_hz = sr_num / sr_den
    print(f"DRF channel '{args.channel}': {fs_hz:.1f} sps")

    # Probe one sample to detect multi-subchannel data and report
    bounds_start, bounds_end = reader.get_bounds(args.channel)
    s_start = utc_to_drf_sample(t_start, sr_num, sr_den)
    s_end   = utc_to_drf_sample(t_end,   sr_num, sr_den)
    s_start = max(s_start, bounds_start)
    s_end   = min(s_end,   bounds_end)
    if s_start >= s_end:
        sys.exit("Requested window is outside available DRF data range.")

    block_size = int(round(args.decim_seconds * fs_hz))

    # Read a small probe to detect shape
    try:
        probe = reader.read_vector(s_start, min(block_size, 64), args.channel)
        if probe.ndim == 2:
            n_subs = probe.shape[1]
            print(f"Multi-subchannel DRF detected: {n_subs} subchannels. "
                  f"Using subchannel {args.subchannel}.")
            if args.subchannel >= n_subs:
                sys.exit(f"--subchannel {args.subchannel} >= number of "
                         f"subchannels ({n_subs})")
        else:
            print("Single-channel DRF.")
            if args.subchannel != 0:
                print(f"  (warning: --subchannel {args.subchannel} ignored)")
    except Exception as e:
        sys.exit(f"Could not probe DRF data: {e}")

    n_blocks = (s_end - s_start) // block_size
    print(f"Window: {t_start} to {t_end}")
    print(f"Producing {n_blocks} samples at {args.decim_seconds}s cadence")

    times = []
    dopplers = []
    snrs = []

    for k in range(n_blocks):
        seg_start = s_start + k * block_size
        try:
            iq = reader.read_vector(seg_start, block_size, args.channel)
        except Exception as e:
            print(f"  block {k}: read error {e}, skipping")
            continue

        # Handle multi-subchannel DRF (shape: (N, n_subchannels))
        if iq.ndim == 2:
            iq = iq[:, args.subchannel]

        f_hz, snr = estimate_carrier_freq(iq, fs_hz, args.search_band_hz)
        ts = pd.Timestamp(seg_start * sr_den / sr_num, unit="s", tz="UTC")
        times.append(ts)
        dopplers.append(f_hz)
        snrs.append(snr)

    df = pd.DataFrame({
        "timestamp_utc": times,
        "doppler_hz": dopplers,
        "snr_db": snrs,
    })
    if args.smooth is not None:
        df, n_used = _apply_smoothing(df, args.smooth, args.decim_seconds)
        print(f"  Smoothing applied: Savitzky-Golay window={args.smooth:g}s "
              f"({n_used} samples), polynomial order 3")
        # Add a header comment to the CSV noting smoothing was applied
        with open(args.output, "w") as f:
            f.write(f"# Smoothing: Savitzky-Golay {args.smooth:g}s window "
                    f"({n_used} samples), polynomial order 3\n")
        df.to_csv(args.output, mode="a", index=False)
    else:
        df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} rows to {args.output}")
    print(f"  Median SNR: {np.nanmedian(df['snr_db']):.1f} dB")
    print(f"  Doppler range: {np.nanmin(df['doppler_hz']):+.3f} to "
          f"{np.nanmax(df['doppler_hz']):+.3f} Hz")

    if args.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
            ax1.plot(df["timestamp_utc"], df["doppler_hz"], lw=0.7)
            ax1.set_ylabel("Doppler (Hz)")
            ax1.grid(alpha=0.3)
            label = os.path.basename(args.drf_dir.rstrip("/"))
            ax1.set_title(f"Doppler vs time — {label}")
            ax2.plot(df["timestamp_utc"], df["snr_db"], lw=0.7, color="tab:orange")
            ax2.set_ylabel("SNR (dB)")
            ax2.set_xlabel("UTC")
            ax2.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(args.plot, dpi=120)
            print(f"Plot saved to {args.plot}")
        except ImportError:
            print("matplotlib not available, skipping plot")


if __name__ == "__main__":
    main()
