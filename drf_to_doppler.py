r"""
drf_to_doppler.py — extract a Doppler-vs-time CSV from Digital RF I/Q data


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.1.0  Add complex-autocorrelation Doppler extractor (Gwyn Griffiths
          G3ZIL method) alongside the FFT tracker. Select with
          --method autocorr; default remains --method fft so existing
          workflows are unchanged.
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
HamSCI Grape 1-DRF stations record the Fort Collins WWV carrier (or
other HF time-standard carrier) as complex baseband I/Q sampled at 10
samples per second, mixed down so the carrier sits within +/- 5 Hz of
zero. Each daily file is stored on disk in the Digital RF (DRF) format
(MIT Haystack's open standard for streaming RF data) inside a directory
like:

    OBS2026-01-19T00-00/
      ch0/
        2026-01-19T00-00-00/   <- hour subdirectories with .h5 data
        2026-01-19T01-00-00/
        ...
        drf_properties.h5      <- channel metadata
        metadata/              <- station info (callsign, grid, freqs)

This tool reads such a directory and produces a CSV of:
    timestamp_utc,  doppler_hz,  snr_db
sampled at a chosen cadence (default 10 s). Two extraction methods are
supported; select with --method:

  fft (default)
    FFT peak-tracking within the +/- search-band-hz observation band,
    with quadratic interpolation for sub-bin precision. Each output
    sample is one independent block. Robust to brief dropouts.

  autocorr
    Complex autocorrelation instantaneous-frequency estimator (Gwyn
    Griffiths / G3ZIL method). For each output sample the lag-1
    autocorrelation is accumulated over the --decim-seconds window and
    the Doppler is recovered as:

        f = arg( sum_n x[n+1] * conj(x[n]) ) / (2 * pi * tau)

    where tau = 1/fs.  No detrending or preprocessing is applied, per
    Gwyn's parameters. This estimator is maximum-likelihood for a
    single complex sinusoid in white Gaussian noise and is theoretically
    more robust to multi-path / E-region contamination than peak-FFT
    because it integrates phase increments coherently rather than
    selecting a spectral bin. The clean-data equivalence gate (see
    VALIDATION below) must be run before trusting its behaviour on
    contaminated data.

The output CSV is the input format for tid_pair.py and tid_doa.py.

ALGORITHM — FFT (--method fft)
================================
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

ALGORITHM — AUTOCORRELATION (--method autocorr)
================================================
For each output sample of duration --decim-seconds (default 10 s):

  1. Read N complex I/Q samples (N = fs * decim_seconds).
  2. Accumulate the lag-1 autocorrelation sum:
         R1 = sum_{n=0}^{N-2}  x[n+1] * conj(x[n])
  3. Recover instantaneous frequency:
         f = arg(R1) / (2 * pi * tau),   tau = 1/fs
     arg() is the complex argument (angle), range (-pi, pi], so the
     unambiguous Doppler range is +/- fs/2 = +/- 5 Hz at 10 sps.
  4. SNR is estimated from the normalised autocorrelation magnitude
     (signal coherence proxy):
         rho = |R1| / (N-1)          <- normalised by max possible
         snr_db = -10 * log10(1 - min(rho, 1-1e-9))
     This converts the coherence estimate to an equivalent SNR in dB,
     analogous to the FFT method's peak/median ratio.

No Hanning window is applied: the lag-1 estimator is already a
coherent integrator and windowing would bias the phase accumulation.
No detrending: per Gwyn's stated parameters. No preprocessing.

VALIDATION (REQUIRED BEFORE PRODUCTION USE)
============================================
The falsifiable gate for the autocorrelation extractor: on a clean,
high-SNR station (e.g. W7LUX, N4RVE — single-path F-layer, SNR > 35
dB), --method autocorr MUST reproduce --method fft within a tolerance
of +/- 0.05 Hz RMS over the analysis window. If it does not, the
extractor is wrong; do not proceed to contaminated-data comparison.

Run the gate before any research comparison:

    python drf_to_doppler.py ./w7lux \
        --start 2024-05-17T18:00:00 --end 2024-05-17T20:00:00 \
        --decim-seconds 60 --output w7lux_fft.csv --method fft

    python drf_to_doppler.py ./w7lux \
        --start 2024-05-17T18:00:00 --end 2024-05-17T20:00:00 \
        --decim-seconds 60 --output w7lux_autocorr.csv --method autocorr

Then compare doppler_hz columns; RMS difference should be < 0.05 Hz.

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
Single-channel station, FFT method (default):

    python drf_to_doppler.py /path/to/station_drf_dir \
        --start 2026-01-19T00:00:00 --end 2026-01-19T01:45:00 \
        --decim-seconds 10 \
        --output station.csv --plot station.png

Single-channel station, autocorrelation method (Gwyn's parameters):

    python drf_to_doppler.py /path/to/station_drf_dir \
        --start 2024-05-17T18:00:00 --end 2024-05-17T20:00:00 \
        --decim-seconds 60 \
        --method autocorr \
        --output station_autocorr.csv --plot station_autocorr.png

Multi-subchannel WSPRdaemon station:

    python drf_to_doppler.py ./n5tnl \
        --start 2026-01-19T00:00:00 --end 2026-01-19T01:45:00 \
        --subchannel 4 \
        --output n5tnl.csv --plot n5tnl.png

WHEN TO USE WHAT CADENCE
========================
  --decim-seconds 60   24-hour survey, low resolution. Use for a first-
                       pass look at the whole day; the resulting trace
                       reveals when TIDs are active. Also Gwyn's window
                       for autocorrelation on the 17 May 2024 event.
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
    has drifted (FFT) or that SNR is too low for the phase estimator
    (autocorr).
  - Sudden vertical spikes are usually RFI or recording glitches.
    Brief spikes (one sample) get smoothed by downstream bandpass
    filtering; sustained spikes are a problem.
  - For multi-subchannel data, if the trace looks like square-wave
    noise jumping between +/- search_band edges, you've selected an
    EMPTY subchannel. Try a different --subchannel index.
  - For --method autocorr: if the SNR panel shows values well below
    the FFT SNR on the same station, coherence is low; the phase
    estimate is unreliable. Do not proceed to contaminated-pair
    comparison until the clean-data gate passes.

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
    """FFT peak frequency of a complex I/Q block, restricted to +/- search_band.

    Returns
    -------
    peak_freq : float
        Estimated Doppler frequency in Hz.
    snr_db : float
        20*log10(peak / median) in dB.
    """
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


def estimate_carrier_freq_autocorr(iq_block, fs_hz, search_band_hz=5.0):
    """Complex autocorrelation (lag-1) instantaneous-frequency estimator.

    Implements Gwyn Griffiths' (G3ZIL) method: accumulate the lag-1
    autocorrelation over the entire block, then recover the instantaneous
    frequency from its argument.

        R1 = sum_{n=0}^{N-2}  x[n+1] * conj(x[n])
        f  = arg(R1) / (2 * pi * tau),   tau = 1/fs_hz

    No windowing (would bias the phase accumulation), no detrending, no
    preprocessing — per Gwyn's stated parameters.

    The search_band_hz parameter is accepted for interface compatibility
    with estimate_carrier_freq but is NOT used here: the lag-1 estimator
    is unambiguous over the full +/- fs/2 range and does not require a
    search window.

    SNR is derived from the normalised autocorrelation magnitude (a
    coherence proxy):

        rho    = |R1| / (N - 1)          # in [0, 1]
        snr_db = -10 * log10(1 - rho)    # maps coherence -> dB

    This is analogous to the FFT method's peak/median ratio and produces
    comparable dB values on strong, clean signals.

    Parameters
    ----------
    iq_block : array-like of complex
        Raw complex I/Q samples for one output epoch.
    fs_hz : float
        Sample rate in samples per second.
    search_band_hz : float
        Ignored; present only for interface compatibility.

    Returns
    -------
    doppler_hz : float
        Estimated instantaneous Doppler frequency in Hz.
    snr_db : float
        Coherence-based SNR proxy in dB.
    """
    x = np.asarray(iq_block, dtype=complex)
    n = len(x)
    if n < 2:
        return np.nan, 0.0

    # Lag-1 autocorrelation sum (vectorised — no Python loop)
    R1 = np.dot(x[1:], x[:-1].conj())

    # Instantaneous frequency from the complex argument
    tau = 1.0 / fs_hz
    doppler_hz = float(np.angle(R1) / (2.0 * np.pi * tau))

    # SNR: FFT peak/median (same as estimate_carrier_freq).
    # Coherence magnitude is NOT used: on a drifting carrier it
    # underestimates coherence and is incomparable to FFT SNR.
    w = np.hanning(n)
    spec = np.abs(np.fft.fftshift(np.fft.fft(x * w)))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs_hz))
    mask = np.abs(freqs) <= search_band_hz
    if mask.any():
        sub = spec[mask]
        snr_db = float(20.0 * np.log10(sub.max() / (np.median(sub) + 1e-12)))
    else:
        snr_db = 0.0

    return doppler_hz, snr_db


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
                         "sample is one estimation block. Use 60 for 24-hour "
                         "surveys or Gwyn's autocorr comparison; 10 for TID "
                         "analysis; 1 for prompt flare signatures. Default: 10")
    ap.add_argument("--search-band-hz", type=float, default=5.0,
                    help="(FFT method only) Half-width of the frequency "
                         "search window around 0 Hz, in Hz. The WWV carrier "
                         "should be within this range after baseband mixing. "
                         "Ignored for --method autocorr. Default: 5.0")
    ap.add_argument("--method", choices=["fft", "autocorr"], default="fft",
                    help="Doppler extraction method. 'fft': FFT peak-tracking "
                         "with quadratic interpolation (default, v1.0 "
                         "behaviour). 'autocorr': complex lag-1 "
                         "autocorrelation instantaneous-frequency estimator "
                         "(Gwyn Griffiths / G3ZIL method; 60s window, one "
                         "lag, no detrending). Run the clean-data validation "
                         "gate before using autocorr results in research "
                         "comparisons (see docstring). Default: fft")
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
                    version="%(prog)s 1.1.0")
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
    print(f"Extraction method: {args.method}")

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

    # Select estimator function once, outside the loop
    if args.method == "autocorr":
        _estimate = estimate_carrier_freq_autocorr
    else:
        _estimate = estimate_carrier_freq

    times = []
    dopplers = []
    snrs = []

    # Progress dots: print roughly 40 across the loop so long extractions
    # (e.g. 24-hour survey at 60s cadence ~= 1438 blocks) show signs of
    # life. For short extractions, dots-per-block ratio still works out
    # to something reasonable.
    dot_interval = max(1, n_blocks // 40)
    for k in range(n_blocks):
        if k % dot_interval == 0:
            sys.stdout.write(".")
            sys.stdout.flush()
        seg_start = s_start + k * block_size
        try:
            iq = reader.read_vector(seg_start, block_size, args.channel)
        except Exception as e:
            print(f"  block {k}: read error {e}, skipping")
            continue

        # Handle multi-subchannel DRF (shape: (N, n_subchannels))
        if iq.ndim == 2:
            iq = iq[:, args.subchannel]

        f_hz, snr = _estimate(iq, fs_hz, args.search_band_hz)
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
            f.write(f"# method={args.method} "
                    f"Smoothing: Savitzky-Golay {args.smooth:g}s window "
                    f"({n_used} samples), polynomial order 3\n")
        df.to_csv(args.output, mode="a", index=False)
    else:
        with open(args.output, "w") as f:
            f.write(f"# method={args.method}\n")
        df.to_csv(args.output, mode="a", index=False)

    if n_blocks > 0:
        sys.stdout.write("\n")
        sys.stdout.flush()
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
            method_label = args.method.upper()
            ax1.set_title(f"Doppler vs time — {label}  [{method_label}]")
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
