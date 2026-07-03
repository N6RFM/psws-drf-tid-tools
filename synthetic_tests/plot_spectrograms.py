#!/usr/bin/env python3
"""
plot_spectrograms.py -- Generate Doppler spectrograms for synthetic DRF
events, for visual inspection and comparison with real HamSCI recordings.

Usage:
    # Plot all stations for one test condition
    python3 plot_spectrograms.py --test nominal

    # Plot specific stations
    python3 plot_spectrograms.py --test nominal --stations SYN_AA6BD,SYN_N6RFM

    # Plot all test conditions (saves to plots/)
    python3 plot_spectrograms.py --all

    # Overlay extracted Doppler traces on spectrogram
    python3 plot_spectrograms.py --test nominal --overlay autocorr,cwt,fft

Output: plots/<test_name>/<station>_spectrogram.png
"""
import argparse
import pathlib
import sys
import datetime
import numpy as np
import warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

try:
    import digital_rf as drf
    _HAVE_DRF = True
except ImportError:
    sys.exit("digital_rf not installed: pip install digital_rf")

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_conditions import TEST_CONDITIONS, ARRAYS

EVENTS_DIR  = pathlib.Path(__file__).parent / "events"
PLOTS_DIR   = pathlib.Path(__file__).parent / "plots"

# Spectrogram parameters
NFFT        = 1024        # FFT size
HOP_S       = 10          # hop between FFT blocks (seconds)
SEARCH_HZ   = 3.0         # frequency axis half-range (Hz)
CMAP        = "viridis"


def make_spectrogram(iq, fs_hz, nfft=NFFT, hop_s=HOP_S):
    """Compute STFT spectrogram. Returns (freqs_hz, times_min, power_db).
    Uses full complex FFT with fftshift so DC (0 Hz baseband) is centred.
    The synthetic I/Q is already baseband -- the TID Doppler oscillates
    symmetrically around 0 Hz, so the spectrogram should be symmetric
    around the horizontal centre line.
    """
    hop = int(hop_s * fs_hz)
    n = len(iq)
    n_frames = (n - nfft) // hop
    win = np.hanning(nfft)
    spec = np.zeros((nfft, n_frames), dtype=float)
    for i in range(n_frames):
        frame = iq[i * hop: i * hop + nfft] * win
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', np.ComplexWarning)
            S = np.fft.fftshift(np.fft.fft(frame.astype(np.complex128)))
        spec[:, i] = np.abs(S) ** 2

    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / fs_hz))
    times = np.arange(n_frames) * hop / fs_hz / 60.0  # minutes
    power_db = 10 * np.log10(spec + 1e-12)
    return freqs, times, power_db


def plot_station(station_name, station_dir, event_start_unix, duration_s,
                 ground_truth, overlay_csvs=None, output_path=None):
    """Generate and save spectrogram for one station."""
    reader_dir = station_dir
    reader = drf.DigitalRFReader(str(reader_dir))
    props  = reader.get_properties("ch0")
    sr     = float(props["samples_per_second"])
    bounds = reader.get_bounds("ch0")

    start_sample = int(event_start_unix * sr)
    end_sample   = int((event_start_unix + duration_s) * sr)
    start_sample = max(start_sample, bounds[0])
    end_sample   = min(end_sample,   bounds[1])
    n_samples    = end_sample - start_sample

    # Read I/Q in chunks to avoid OOM on long events
    CHUNK = int(sr * 600)  # 10-minute chunks
    iq_chunks = []
    pos = start_sample
    while pos < end_sample:
        n = min(CHUNK, end_sample - pos)
        chunk = reader.read_vector(pos, n, "ch0")
        if chunk.ndim == 2:
            chunk = chunk[:, 0]
        iq_chunks.append(chunk.astype(np.complex64))
        pos += n
    iq = np.concatenate(iq_chunks)

    # Compute spectrogram
    freqs, times, power_db = make_spectrogram(iq, sr)

    # Restrict to search band
    band_mask = np.abs(freqs) <= SEARCH_HZ
    freqs_plot = freqs[band_mask]
    power_plot = power_db[band_mask, :]

    # Normalise: subtract per-time median (removes broadband noise shape)
    power_plot -= np.median(power_plot, axis=0, keepdims=True)
    vmin, vmax = np.percentile(power_plot, [5, 98])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.pcolormesh(times, freqs_plot, power_plot,
                  cmap=CMAP, vmin=vmin, vmax=vmax, shading="auto")

    # Plot true TID Doppler trace
    t_min = np.linspace(0, duration_s / 60.0, 500)
    true_speed  = ground_truth["true_speed_m_s"]
    true_az     = ground_truth["true_az_from_deg"]
    true_period = ground_truth["true_period_min"] * 60.0
    true_amp    = ground_truth["true_amp_hz"]

    # Find this station's lag from ground truth
    stn_info = next((s for s in ground_truth["stations"]
                     if s["name"] == station_name), None)
    if stn_info:
        lag_s   = stn_info["true_lag_s"]
        phase   = -2 * np.pi * lag_s / true_period
        t_s     = t_min * 60.0
        doppler = true_amp * np.sin(2 * np.pi * t_s / true_period + phase)
        ax.plot(t_min, doppler, "r--", lw=1.5, label="True TID Doppler", zorder=5)

    # Overlay extracted traces if provided
    if overlay_csvs:
        import pandas as pd
        colors = ["lime", "cyan", "orange", "magenta"]
        for ci, (method, csv_path) in enumerate(overlay_csvs):
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path, parse_dates=["timestamp_utc"])
            t0 = datetime.datetime.fromtimestamp(event_start_unix, tz=datetime.timezone.utc)
            t_mins = [(ts.to_pydatetime() - t0).total_seconds() / 60.0
                      for ts in df["timestamp_utc"]]
            ax.plot(t_mins, df["doppler_hz"],
                    color=colors[ci % len(colors)],
                    lw=1.2, alpha=0.8, label=method, zorder=6)

    ax.set_xlabel("Time (minutes from event start)")
    ax.set_ylabel("Doppler (Hz)")
    ax.set_title(
        f"{station_name} — {ground_truth['test_name']}\n"
        f"True: {true_speed:.0f} m/s from {true_az:.0f}°  "
        f"Period: {ground_truth['true_period_min']} min  "
        f"SNR: {ground_truth['snr_db']} dB  "
        f"Noise: {ground_truth['noise_type']}"
    )
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(0, duration_s / 60.0)
    ax.set_ylim(-SEARCH_HZ, SEARCH_HZ)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=120, bbox_inches="tight")
        print(f"  Saved: {output_path}")
    else:
        plt.show()
    plt.close(fig)


def run_one(test_name, station_filter=None, overlay_methods=None):
    """Plot spectrograms for one test condition."""
    import json
    event_dir = EVENTS_DIR / f"synthetic_{test_name}"
    gt_path   = event_dir / "ground_truth.json"
    if not gt_path.exists():
        print(f"Event not found: {event_dir} -- run generate first:")
        print(f"  python3 run_tests.py --test {test_name} --methods autocorr")
        return

    gt = json.loads(gt_path.read_text())
    stations = [s for s in gt["stations"]
                if station_filter is None or s["name"] in station_filter]

    duration_s = gt["event_end_unix"] - gt["event_start_unix"]

    print(f"\n[{test_name}] {len(stations)} station(s), {duration_s/3600:.1f}h")

    for s in stations:
        stn_dir = event_dir / s["name"]

        # Find overlay CSVs if requested
        overlay_csvs = None
        if overlay_methods:
            overlay_csvs = []
            for method in overlay_methods:
                csv = event_dir / f"{s['name'].lower()}_{method}.csv"
                if csv.exists():
                    overlay_csvs.append((method, csv))

        out = PLOTS_DIR / test_name / f"{s['name']}_spectrogram.png"
        plot_station(
            s["name"], stn_dir,
            gt["event_start_unix"], duration_s,
            gt, overlay_csvs, out
        )


def main():
    ap = argparse.ArgumentParser(
        description="Plot Doppler spectrograms for synthetic DRF events")
    ap.add_argument("--test", metavar="NAME",
                    help="Test condition name (e.g. nominal)")
    ap.add_argument("--all", action="store_true",
                    help="Plot all test conditions with generated events")
    ap.add_argument("--stations", metavar="A,B",
                    help="Comma-separated station names to plot (default: all)")
    ap.add_argument("--overlay", metavar="autocorr,cwt",
                    help="Overlay extracted Doppler CSVs for these methods")
    args = ap.parse_args()

    station_filter = (args.stations.split(",") if args.stations else None)
    overlay_methods = (args.overlay.split(",") if args.overlay else None)

    if args.test:
        run_one(args.test, station_filter, overlay_methods)
        return

    if args.all:
        generated = [p.name.replace("synthetic_", "")
                     for p in sorted(EVENTS_DIR.glob("synthetic_*"))
                     if (p / "ground_truth.json").exists()]
        print(f"Found {len(generated)} generated events")
        for name in generated:
            run_one(name, station_filter, overlay_methods)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
