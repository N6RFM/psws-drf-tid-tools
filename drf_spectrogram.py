r"""
drf_spectrogram.py — render an annotated Doppler spectrogram from DRF I/Q

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.1
License: MIT (do whatever you want, no warranty).

Based on the spectrogram approach used by AB4EJ (W. Engelke, University of
Alabama) in plotspectrum_V4a.py.

Change log:
  v1.2.0  Added --overlay CSV:label[:color] to superimpose one or more
          Doppler CSV traces (from drf_to_doppler.py) on the spectrogram.
          Useful for visually validating FFT vs autocorr extraction and
          confirming the extracted Doppler tracks the spectrogram carrier.
  v1.1.0  Added --callsign and --grid overrides so the auto-generated
          title can be completed when Grape v1.x DRFs omit those fields
          from the metadata.
  v1.0.0  Initial release. Reads DRF I/Q at 10 sps, produces a 24-hour
          Doppler spectrogram with a peak-amplitude subplot, and allows
          annotation of the TID region of study with a labeled box plus
          vertical event markers.

OVERVIEW
========
Produces a two-panel figure from a HamSCI Grape DRF recording:

  - Top: Doppler spectrogram across the requested window (default 24 hr),
         showing Doppler shift (Hz) vs time (UTC hours)
  - Bottom: peak amplitude per minute over the same window

The plot serves two purposes in the TID analysis pipeline:

  1. ORIENTATION: a quick visual scan to identify when TIDs were active
     during the recording day, by looking for slow wavy carrier tracks.

  2. PROVENANCE: when reporting a cross-correlation result, the
     spectrogram with the analysis window highlighted provides a clean
     visual reference for the region of study, helping readers see
     exactly what was analyzed.

USAGE
=====
Plot a full-day spectrogram:

    python drf_spectrogram.py ./n6rfm --output n6rfm_spectrogram.png

Plot with the TID analysis window annotated:

    python drf_spectrogram.py ./n6rfm --output n6rfm_spectrogram.png \
        --annotate "00:00,01:45,TID analysis window"

Multiple annotations, plus event markers:

    python drf_spectrogram.py ./n6rfm --output n6rfm_spectrogram.png \
        --annotate "00:00,01:45,LSTID region of study" \
        --annotate "17:50,18:10,X1.9 flare SFD" \
        --vline "17:50,X1.9 peak" --vline "00:00,Jan 19"

Multi-subchannel station:

    python drf_spectrogram.py ./ac0g_nd --output ac0g_spectrogram.png \
        --subchannel 4 \
        --annotate "00:00,01:15,TID region of study"

Overlay FFT and autocorr Doppler traces on the spectrogram:

    python drf_spectrogram.py ./n6rfm --output n6rfm_overlay.png \
        --annotate "00:00,01:10,TID window" \
        --overlay "n6rfm_fft.csv:FFT" \
        --overlay "n6rfm_autocorr.csv:Autocorr:#FF9800"

OVERLAY SYNTAX
==============
--overlay "path/to/doppler.csv:label"
    Superimposes a Doppler-vs-time trace from a drf_to_doppler.py CSV
    on the spectrogram panel. The time column is auto-detected; the
    Doppler column must be named 'doppler_hz'. Multiple --overlay
    flags can be used to compare FFT and autocorr extraction side by
    side on the same spectrogram.

--overlay "path/to/doppler.csv:label:#FF9800"
    As above, with an explicit hex color. Default colors cycle through
    blue, orange, green, red if not specified.

ANNOTATION SYNTAX
=================
--annotate "HH:MM,HH:MM,label"
    Draws a labeled rectangle on the spectrogram spanning the time range.
    Use 24-hour UTC notation. The rectangle is semi-transparent so the
    spectrogram remains visible through it.

--vline "HH:MM,label"
    Draws a single vertical dashed line at the given UTC time with a
    label at the top.

--ylim "-2,2"
    Override the default Doppler-axis range. Default is +/- 5 Hz.

PARAMETER GUIDANCE
==================
  --window-minutes 60
      Each spectrogram column is one FFT of this many seconds of data.
      Default: 60 (1-minute resolution). Smaller values give finer time
      resolution but worse frequency resolution; the trade is governed
      by the time-bandwidth product. 60 sec at 10 sps gives 600 samples
      per FFT, hence ~0.017 Hz frequency resolution.

  --start "HH:MM" / --end "HH:MM"
      Limit the spectrogram to a sub-window (UTC hours/minutes within
      the recorded day). Default: full 24-hour day from the DRF bounds.

INTERPRETING OVERLAY METRICS
============================
When --overlay is used, each trace in the legend shows four metrics.
Here is what they mean and how to use them to choose a method.

  std (Hz)
      Block-to-block standard deviation of the extracted Doppler.
      Measures the extractor's noise floor, not accuracy. Autocorr
      is always smoother than FFT by design (typically 2-3x lower
      std). A smoother trace is not necessarily more accurate.
      Use std to spot noisy blocks, not to choose a method.

  r (inter-method Pearson correlation)
      Correlation between the FFT and autocorr traces over the
      plot window. Measures how similarly the two methods track
      the carrier.
        r > 0.95  Both methods agree. Either is reliable; use FFT.
        r 0.85-0.95  Mild disagreement. Inspect the spectrogram.
        r < 0.85  Significant disagreement. One method may be
                  tracking E-region instead of F-region. Use the
                  spectrogram overlay to decide which is correct.
      Note: r does not tell you which method is right, only whether
      they agree.

  RMS diff (Hz)
      Root-mean-square difference between FFT and autocorr traces.
      More interpretable than r because it is in physical units.
        < 0.10 Hz  Negligible disagreement. Both methods equivalent.
        0.10-0.30 Hz  Noticeable. Worth checking the overlay visually.
        > 0.30 Hz  Substantial. One method is likely off-track.

DECISION WORKFLOW
=================
1. Look at the spectrogram. Is there a visible sinusoidal TID carrier
   (slow, wave-like, bright ridge)? If not, data quality issue; stop.

2. Check r and RMS diff:
     Both agree (r > 0.95, RMS < 0.10 Hz) -> use FFT, proceed to
     cross-correlation. No further inspection needed.
     They disagree -> go to step 3.

3. Look at the overlay traces on the spectrogram. Which trace visually
   follows the bright carrier ridge? That method is tracking the
   F-region TID signal. The other may be pulled toward the E-region
   flat component near 0 Hz.

4. If E-region contamination is visible (flat bright band near 0 Hz
   alongside the TID wave) and autocorr tracks the TID better:
     - Use autocorr IF the lag/period ratio is < 0.3 (unambiguous).
     - Prefer FFT IF the lag/period ratio is 0.3-0.5 (ambiguous
       cross-correlation peaks; autocorr smoothness causes wrong-peak
       lock in this regime — see research/psws_autocorr_research_report.pdf).

5. Record which method was chosen and why in the run log.

REQUIREMENTS
============
    pip install digital_rf numpy matplotlib pandas

SEE ALSO
========
    drf_to_doppler.py     reduces the same DRF data to a peak-tracked CSV
    drf_inspect.py        identifies the subchannel for multi-subchannel
                          recordings
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

__version__ = "1.2.0"

# Lazy imports for matplotlib + digital_rf so --help works without them
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.patches import Rectangle
    _HAVE_MPL = True
except ImportError:
    _HAVE_MPL = False

try:
    import digital_rf as drf
    _HAVE_DRF = True
except ImportError:
    _HAVE_DRF = False


# ----------------------------------------------------------------------------
# Argument parsers for annotation syntax
# ----------------------------------------------------------------------------
def parse_hhmm(s):
    """Parse 'HH:MM' or 'HH:MM:SS' into seconds since midnight UTC."""
    parts = s.split(":")
    if len(parts) == 2:
        h, m = parts; sec = 0
    elif len(parts) == 3:
        h, m, sec = parts
    else:
        raise ValueError(f"Bad time format: {s!r}, expected HH:MM[:SS]")
    return int(h) * 3600 + int(m) * 60 + int(sec)


def parse_annotation(s):
    """Parse 'HH:MM,HH:MM,label'."""
    parts = s.split(",", 2)
    if len(parts) != 3:
        raise ValueError(f"Bad --annotate {s!r}, expected 'HH:MM,HH:MM,label'")
    return parse_hhmm(parts[0]), parse_hhmm(parts[1]), parts[2].strip()


def parse_vline(s):
    """Parse 'HH:MM,label'."""
    parts = s.split(",", 1)
    if len(parts) != 2:
        raise ValueError(f"Bad --vline {s!r}, expected 'HH:MM,label'")
    return parse_hhmm(parts[0]), parts[1].strip()


def parse_overlay(s):
    """Parse 'path/to/file.csv:label' or 'path/to/file.csv:label:color'."""
    parts = s.split(":", 2)
    if len(parts) < 2:
        raise ValueError(
            f"Bad --overlay {s!r}, expected 'CSV_PATH:label' or "
            f"'CSV_PATH:label:color'"
        )
    csv_path = parts[0].strip()
    label    = parts[1].strip()
    color    = parts[2].strip() if len(parts) == 3 else None
    return csv_path, label, color


# ----------------------------------------------------------------------------
# Spectrogram computation
# ----------------------------------------------------------------------------
def compute_spectrogram(reader, channel, subchannel,
                        start_sample, n_seconds, window_seconds, fs_hz):
    """Build the spectrogram array.

    Returns:
        spec:  (n_freq_bins, n_time_columns) array of dB magnitudes
        freqs: (n_freq_bins,) frequency axis (Hz, relative to baseband)
        times: (n_time_columns,) time axis (seconds since start_sample)
    """
    n_per_fft = int(window_seconds * fs_hz)  # samples per FFT column
    n_columns = int(n_seconds / window_seconds)
    spec = np.zeros((n_per_fft, n_columns), dtype=float)

    print(f"Computing spectrogram: "
          f"{n_columns} columns x {n_per_fft} samples/col")
    print(f"  Reading {n_columns * n_per_fft} samples total "
          f"({n_seconds/3600:.2f} hr at {fs_hz:.1f} sps)...")

    progress_every = max(1, n_columns // 40)
    for col in range(n_columns):
        offset = col * n_per_fft
        try:
            if subchannel is not None:
                # Multi-subchannel: returns 2D array (n, num_sub)
                block = reader.read_vector(start_sample + offset,
                                            n_per_fft, channel)
                if block.ndim == 2:
                    block = block[:, subchannel]
            else:
                block = reader.read_vector(start_sample + offset,
                                            n_per_fft, channel)
                if block.ndim == 2:
                    block = block[:, 0]
        except Exception:
            block = np.zeros(n_per_fft, dtype=complex)

        # Window and FFT
        if len(block) < n_per_fft:
            block = np.pad(block, (0, n_per_fft - len(block)))
        windowed = block * np.hanning(n_per_fft)
        fft_mag = np.abs(np.fft.fftshift(np.fft.fft(windowed))) / n_per_fft
        spec[:, col] = 20.0 * np.log10(fft_mag + 1e-12)

        if col % progress_every == 0:
            sys.stdout.write(".")
            sys.stdout.flush()
    print()

    # Frequency axis
    freqs = np.fft.fftshift(np.fft.fftfreq(n_per_fft, d=1.0 / fs_hz))
    times = np.arange(n_columns) * window_seconds  # seconds since start
    return spec, freqs, times


def compute_peak_amplitude(reader, channel, subchannel,
                            start_sample, n_seconds, window_seconds, fs_hz):
    """Read the same window and compute peak amplitude per minute."""
    n_per_bin = int(window_seconds * fs_hz)
    n_columns = int(n_seconds / window_seconds)
    out = np.zeros(n_columns, dtype=float)
    progress_every = max(1, n_columns // 40)
    for col in range(n_columns):
        offset = col * n_per_bin
        try:
            if subchannel is not None:
                block = reader.read_vector(start_sample + offset,
                                            n_per_bin, channel)
                if block.ndim == 2:
                    block = block[:, subchannel]
            else:
                block = reader.read_vector(start_sample + offset,
                                            n_per_bin, channel)
                if block.ndim == 2:
                    block = block[:, 0]
        except Exception:
            out[col] = 0
            continue
        out[col] = float(np.max(np.abs(block)))
        if col % progress_every == 0:
            sys.stdout.write(".")
            sys.stdout.flush()
    print()
    return out


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring for full details.",
    )
    ap.add_argument("drf_dir",
                    help="DRF station directory (contains 'ch0/'). "
                         "Same path you'd pass to drf_to_doppler.py.")
    ap.add_argument("--channel", default="ch0",
                    help="DRF channel name. Default: ch0")
    ap.add_argument("--subchannel", type=int, default=None,
                    help="Subchannel index for multi-subchannel data "
                         "(use drf_inspect.py to find this). Single-"
                         "channel: omit.")
    ap.add_argument("--output", "-o", required=True,
                    help="Output PNG path, e.g. n6rfm_spectrogram.png")
    ap.add_argument("--start", default=None,
                    help="Optional UTC start of plot window (HH:MM or "
                         "HH:MM:SS). Default: start of recording.")
    ap.add_argument("--window", default=None, metavar="JSON",
                    help="TID window JSON from tid_quicklook.py. "
                         "Reads t_start/t_end and uses them as --start/--end. "
                         "Auto-detected as <drf_dir>_fullday_window.json if present.")
    ap.add_argument("--end", default=None,
                    help="Optional UTC end of plot window. Default: "
                         "24 hours after start.")
    ap.add_argument("--window-minutes", type=float, default=1.0,
                    help="Seconds per spectrogram column, in MINUTES. "
                         "Default: 1.0 minute (60 s).")
    ap.add_argument("--ylim", default="-5,5",
                    help="Doppler axis limits as 'low,high' (Hz). "
                         "Default: -5,5. Tip: if your value starts with "
                         "a minus sign, write --ylim=-2,2 (with the '=') "
                         "to keep argparse from interpreting it as a flag.")
    ap.add_argument("--vmin", type=float, default=None,
                    help="Min dB for color scale. Default: auto.")
    ap.add_argument("--vmax", type=float, default=None,
                    help="Max dB for color scale. Default: auto.")
    ap.add_argument("--annotate", action="append", default=[],
                    help="Annotation rectangle: 'HH:MM,HH:MM,label'. "
                         "Can be specified multiple times.")
    ap.add_argument("--vline", action="append", default=[],
                    help="Vertical event marker: 'HH:MM,label'. Can "
                         "be specified multiple times.")
    ap.add_argument("--overlay", action="append", default=[],
                    metavar="CSV:label[:color]",
                    help="Overlay a Doppler CSV trace on the spectrogram. "
                         "Format: 'path/to/doppler.csv:label' or "
                         "'path/to/doppler.csv:label:color'. "
                         "The CSV must have a UTC time column and a "
                         "doppler_hz column (output of drf_to_doppler.py). "
                         "Can be specified multiple times to overlay "
                         "multiple traces (e.g. FFT and autocorr).")
    ap.add_argument("--title", default=None,
                    help="Full plot title override. If you only want to "
                         "fix a missing callsign/grid (some older Grape "
                         "DRFs don't include them in metadata), use "
                         "--callsign and --grid instead.")
    ap.add_argument("--callsign", default=None,
                    help="Override the callsign in the auto-generated "
                         "title. Useful when the DRF metadata is missing "
                         "the callsign field (older Grape v1.x recordings).")
    ap.add_argument("--grid", default=None,
                    help="Override the grid square in the auto-generated "
                         "title.")
    ap.add_argument("--dpi", type=int, default=140,
                    help="Output PNG resolution in dots per inch. "
                         "Default: 140. Use 200-300 for publication quality.")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.2.0")
    args = ap.parse_args()

    if not _HAVE_DRF:
        sys.exit("digital_rf not installed: pip install digital_rf")
    if not _HAVE_MPL:
        sys.exit("matplotlib not installed: pip install matplotlib")

    # Open the DRF
    try:
        reader = drf.DigitalRFReader(args.drf_dir)
    except Exception as e:
        sys.exit(f"Could not open DRF at {args.drf_dir!r}: {e}")

    props = reader.get_properties(args.channel)
    sr_num, sr_den = props["samples_per_second"].as_integer_ratio()
    fs_hz = sr_num / sr_den

    b_start, b_end = reader.get_bounds(args.channel)
    record_start_utc = datetime.fromtimestamp(b_start * sr_den / sr_num,
                                              tz=timezone.utc)
    record_end_utc = datetime.fromtimestamp(b_end * sr_den / sr_num,
                                            tz=timezone.utc)
    print(f"DRF recording: {record_start_utc} to {record_end_utc}")

    # Try to read station metadata for the plot title
    metadata_dir = os.path.join(args.drf_dir, args.channel, "metadata")
    callsign = grid = "?"
    target_freq = None
    if os.path.isdir(metadata_dir):
        try:
            mr = drf.DigitalMetadataReader(metadata_dir)
            mb = mr.get_bounds()
            samp = mr.read(mb[0], mb[0] + 1)
            if samp:
                meta = list(samp.values())[0]
                callsign = meta.get("callsign", "?")
                grid = meta.get("grid_square", "?")
                fr = meta.get("center_frequencies", None)
                if fr is not None:
                    idx = args.subchannel if args.subchannel is not None else 0
                    if idx < len(fr):
                        target_freq = float(fr[idx])
        except Exception as e:
            print(f"  (metadata read failed: {e})")

    # CLI overrides take precedence over metadata
    if args.callsign:
        callsign = args.callsign
    if args.grid:
        grid = args.grid
    # Determine analysis window
    midnight_utc = record_start_utc.replace(hour=0, minute=0, second=0,
                                            microsecond=0)
    # Load window JSON from tid_quicklook.py if provided
    if args.window:
        import json as _json
        with open(args.window) as _f:
            _wj = _json.load(_f)
        def _h2hhmm(h):
            hh = int(h); mm = int(round((h - hh) * 60))
            return f"{hh:02d}:{mm:02d}"
        if not args.start:
            args.start = _h2hhmm(_wj["t_start_utc_hours"])
        if not args.end:
            args.end = _h2hhmm(_wj["t_end_utc_hours"])
        print(f"  Window JSON: {args.start}-{args.end} UTC")
    if args.start:
        start_dt = midnight_utc + timedelta(seconds=parse_hhmm(args.start))
    else:
        start_dt = record_start_utc
    if args.end:
        end_dt = midnight_utc + timedelta(seconds=parse_hhmm(args.end))
    else:
        end_dt = start_dt + timedelta(hours=24)

    # Clip to actual data bounds
    if start_dt < record_start_utc:
        start_dt = record_start_utc
    if end_dt > record_end_utc:
        end_dt = record_end_utc
    n_seconds = (end_dt - start_dt).total_seconds()
    start_sample = int(start_dt.timestamp() * fs_hz)

    window_seconds = args.window_minutes * 60.0
    print(f"Plot window: {start_dt} to {end_dt}  ({n_seconds/3600:.2f} hr)")

    spec, freqs, times = compute_spectrogram(
        reader, args.channel, args.subchannel,
        start_sample, n_seconds, window_seconds, fs_hz)

    print("Computing peak amplitude per minute...")
    peaks = compute_peak_amplitude(
        reader, args.channel, args.subchannel,
        start_sample, n_seconds, window_seconds, fs_hz)

    # Plot
    ylim_lo, ylim_hi = (float(x) for x in args.ylim.split(","))
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(14, 8),
                                         gridspec_kw={"height_ratios": [2.5, 1]})

    # gnuradio-like colormap (black-darkgreen-green-yellow-red)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "gnuradio_like",
        ["#000000", "#003300", "#006600", "#33ff33", "#ffff33", "#ff3333"])

    if args.vmin is None:
        args.vmin = float(np.percentile(spec, 10))
    if args.vmax is None:
        args.vmax = float(np.percentile(spec, 99.5))

    # imshow with explicit extent: x in hours since record midnight
    start_offset_hr = (start_dt - midnight_utc).total_seconds() / 3600.0
    end_offset_hr = (end_dt - midnight_utc).total_seconds() / 3600.0
    extent = [start_offset_hr, end_offset_hr, freqs[0], freqs[-1]]

    im = ax_top.imshow(spec, aspect="auto", origin="lower",
                       extent=extent, cmap=cmap,
                       vmin=args.vmin, vmax=args.vmax,
                       interpolation="nearest")
    ax_top.set_ylim(ylim_lo, ylim_hi)
    ax_top.set_ylabel("Doppler shift (Hz)")

    title_str = args.title
    if not title_str:
        freq_str = f"{target_freq:.3f} MHz" if target_freq else "?"
        date_str = record_start_utc.strftime("%Y-%m-%d")
        title_str = (f"Doppler spectrogram - {callsign} ({grid}) "
                     f"at {freq_str}, {date_str}")
    ax_top.set_title(title_str)

    cbar = plt.colorbar(im, ax=ax_top, pad=0.01)
    cbar.set_label("Power (dB, uncalibrated)")

    # Annotations on the top (spectrogram) panel.
    # Use vertical edge lines + bracket markers to delimit each region;
    # place a callout label with a leader line above the spectrogram
    # so the label never obscures the data and is unambiguously linked
    # to its time range.
    callout_colors = ["#00ffff", "#ff44ff", "#ffaa00", "#00ff66"]
    n_annotations = len(args.annotate)
    for i, ann_str in enumerate(args.annotate):
        t0_s, t1_s, label = parse_annotation(ann_str)
        x0 = t0_s / 3600.0
        x1 = t1_s / 3600.0
        x_center = (x0 + x1) / 2
        color = callout_colors[i % len(callout_colors)]

        # Translucent shaded region marking the analysis window
        ax_top.add_patch(Rectangle((x0, ylim_lo), x1 - x0,
                                   ylim_hi - ylim_lo,
                                   linewidth=0,
                                   facecolor=color,
                                   alpha=0.20,
                                   zorder=10))
        # Vertical edges (bright dashed lines for crispness)
        for x_edge in (x0, x1):
            ax_top.plot([x_edge, x_edge], [ylim_lo, ylim_hi],
                        color=color, linestyle="--", linewidth=1.8,
                        alpha=0.9, zorder=11)
        # Horizontal bracket bar at the TOP of the rectangle
        bracket_y = ylim_hi - (ylim_hi - ylim_lo) * 0.02
        ax_top.plot([x0, x1], [bracket_y, bracket_y],
                    color=color, linewidth=2.5, alpha=0.95, zorder=12)
        # Short tick marks at each end of the bracket
        tick_h = (ylim_hi - ylim_lo) * 0.04
        for x_edge in (x0, x1):
            ax_top.plot([x_edge, x_edge],
                        [bracket_y, bracket_y - tick_h],
                        color=color, linewidth=2.5, alpha=0.95, zorder=12)

        # Stack callout labels ABOVE the plot region with leader lines.
        # Each successive label is placed further above to avoid collision.
        label_y_offset = 0.95 + 0.08 * i   # axes fraction above ylim_hi
        # Convert axes fraction (1.0 = ylim_hi) to data coords
        y_label = ylim_lo + (ylim_hi - ylim_lo) * label_y_offset
        # Leader line from bracket to label
        ax_top.annotate(label,
                        xy=(x_center, bracket_y),
                        xytext=(x_center, y_label),
                        ha="center", va="bottom",
                        fontsize=10, color="black", weight="bold",
                        bbox=dict(boxstyle="round,pad=0.4",
                                  facecolor=color, alpha=0.95,
                                  edgecolor="black", linewidth=1.2),
                        arrowprops=dict(arrowstyle="-",
                                        color=color, linewidth=1.5,
                                        connectionstyle="arc3,rad=0"),
                        annotation_clip=False,
                        zorder=15)

    # Vertical event markers
    for vl_str in args.vline:
        t_s, label = parse_vline(vl_str)
        x = t_s / 3600.0
        ax_top.axvline(x=x, color="white", linestyle="--",
                       linewidth=1.5, alpha=0.7, zorder=9)
        ax_top.annotate(label,
                        xy=(x, ylim_hi),
                        xytext=(2, -2),
                        textcoords="offset points",
                        ha="left", va="top",
                        fontsize=9, color="yellow", weight="bold",
                        zorder=12)

    # Bottom panel: peak amplitude
    peak_times_hr = (np.arange(len(peaks)) * window_seconds) / 3600.0 \
                    + start_offset_hr
    ax_bot.plot(peak_times_hr, peaks, color="steelblue", linewidth=0.8)
    ax_bot.set_xlim(start_offset_hr, end_offset_hr)
    ax_bot.set_ylabel("Peak amplitude\n(uncalibrated)")
    ax_bot.set_xlabel(f"Hours UTC on {record_start_utc.strftime('%Y-%m-%d')}")
    ax_bot.grid(True, alpha=0.3)
    # Mark the same annotation regions on the bottom panel
    ylim_peak = ax_bot.get_ylim()
    for ann_str in args.annotate:
        t0_s, t1_s, _ = parse_annotation(ann_str)
        ax_bot.axvspan(t0_s / 3600.0, t1_s / 3600.0,
                       facecolor="orange", alpha=0.18, zorder=0)
    for vl_str in args.vline:
        t_s, _ = parse_vline(vl_str)
        ax_bot.axvline(x=t_s / 3600.0, color="red", linestyle="--",
                       linewidth=1.0, alpha=0.5)

    # Overlay Doppler CSV traces on the spectrogram panel
    # Default color cycle: blue, orange, green, red, purple, brown
    _overlay_colors = ["#2196F3", "#FF9800", "#4CAF50",
                       "#F44336", "#9C27B0", "#795548"]

    import pandas as pd

    # Collect all overlay series for inter-method comparison at the end
    _overlay_series = {}   # label -> (hr_array, dop_array)

    for ov_idx, ov_str in enumerate(args.overlay):
        try:
            csv_path, ov_label, ov_color = parse_overlay(ov_str)
        except ValueError as e:
            print(f"WARNING: skipping overlay — {e}")
            continue

        try:
            ov_df = pd.read_csv(csv_path, comment="#")
        except Exception as e:
            print(f"WARNING: could not read overlay CSV {csv_path!r}: {e}")
            continue

        tcol = next((c for c in ov_df.columns
                     if any(k in c.lower()
                            for k in ["time", "stamp", "utc", "date"])),
                    None)
        dcol = next((c for c in ov_df.columns
                     if "doppler" in c.lower() or c.lower() == "hz"),
                    None)

        if tcol is None or dcol is None:
            print(f"WARNING: overlay {csv_path!r} — could not find time "
                  f"or doppler column. Columns: {list(ov_df.columns)}")
            continue

        try:
            ov_df[tcol] = pd.to_datetime(ov_df[tcol], utc=True)
        except Exception as e:
            print(f"WARNING: overlay time parse failed: {e}")
            continue

        ov_df["_hr"] = (
            (ov_df[tcol] - pd.Timestamp(midnight_utc)).dt.total_seconds()
            / 3600.0
        )

        mask = ((ov_df["_hr"] >= start_offset_hr) &
                (ov_df["_hr"] <= end_offset_hr))
        ov_plot = ov_df[mask].copy()

        if ov_plot.empty:
            print(f"WARNING: overlay {csv_path!r} has no data in "
                  f"the plot window.")
            continue

        color = ov_color if ov_color else _overlay_colors[
            ov_idx % len(_overlay_colors)]

        # Per-trace metrics: SNR and smoothness (std) only
        # Inter-method r and RMS are computed once below — not per trace
        snr_med = (ov_df["snr_db"].median()
                   if "snr_db" in ov_df.columns else None)
        dop_std = float(ov_plot[dcol].std()) if len(ov_plot) > 1 else None

        parts = [ov_label]
        if snr_med is not None:
            parts.append(f"SNR={snr_med:.1f} dB")
        if dop_std is not None:
            parts.append(f"std={dop_std:.3f} Hz")
        per_trace_label = "  |  ".join(parts)

        ax_top.plot(ov_plot["_hr"], ov_plot[dcol],
                    color=color, linewidth=1.8,
                    linestyle="-", alpha=0.85,
                    label=per_trace_label, zorder=20)

        # Store for inter-method comparison
        _overlay_series[ov_label] = (
            ov_plot["_hr"].values,
            ov_plot[dcol].values
        )

    # Compute inter-method r and RMS diff if exactly two overlays loaded
    if len(_overlay_series) == 2:
        labels    = list(_overlay_series.keys())
        hr_a, d_a = _overlay_series[labels[0]]
        hr_b, d_b = _overlay_series[labels[1]]

        # Interpolate b onto a's time grid for alignment
        d_b_interp = np.interp(hr_a, hr_b, d_b,
                               left=np.nan, right=np.nan)
        valid = (~np.isnan(d_b_interp)) & (~np.isnan(d_a))

        inter_r   = None
        inter_rms = None
        if valid.sum() > 3:
            a = d_a[valid]; b = d_b_interp[valid]
            if a.std() > 1e-9 and b.std() > 1e-9:
                inter_r = float(np.corrcoef(a, b)[0, 1])
            inter_rms = float(np.sqrt(np.mean((a - b) ** 2)))

        # Add a single inter-method summary line to the legend
        summary_parts = [f"Inter-method ({labels[0]} vs {labels[1]})"]
        if inter_r is not None:
            summary_parts.append(f"r={inter_r:.3f}")
        if inter_rms is not None:
            summary_parts.append(f"RMS diff={inter_rms:.3f} Hz")
        summary_label = "  |  ".join(summary_parts)

        # Plot an invisible line just to add the summary to the legend
        ax_top.plot([], [], color="white", linewidth=0,
                    label=summary_label)

        # Print to console
        print(f"  Inter-method: r={inter_r:.3f}" if inter_r else
              "  Inter-method: r=n/a", end="")
        if inter_rms is not None:
            print(f"  RMS diff={inter_rms:.3f} Hz", end="")
        print()

    elif len(_overlay_series) > 2:
        print("  (Inter-method r not computed: more than 2 overlays)")

    if args.overlay:
        ax_top.legend(loc="upper right", fontsize=8.5,
                      framealpha=0.82, facecolor="#111111",
                      labelcolor="white", edgecolor="gray",
                      handlelength=1.5)

    plt.tight_layout()
    if args.annotate:
        # Make room for callout labels above the spectrogram
        fig.subplots_adjust(top=0.86 - 0.04 * (len(args.annotate) - 1))
    # Get axes position BEFORE savefig for accurate plot_fraction
    fig.canvas.draw()  # force layout computation
    _pos_top = ax_top.get_position()
    _fig_w, _fig_h = fig.get_size_inches() * fig.dpi
    # bbox_inches=tight shifts things — measure after draw but use
    # normalized figure coordinates directly
    _pf_from_mpl = [
        _pos_top.x0,                    # left
        _pos_top.x0 + _pos_top.width,   # right
        _pos_top.y0,                    # bottom (from figure bottom)
        _pos_top.y0 + _pos_top.height,  # top
    ]
    print(f"  axes position (MPL): {[round(x,4) for x in _pf_from_mpl]}")
    plt.savefig(args.output, dpi=args.dpi, bbox_inches="tight")
    plt.close()
    print(f"\nWrote {args.output}")

    # Write sidecar JSON with axis metadata for tid_spect_click.py
    import json as _json
    sidecar_path = os.path.splitext(args.output)[0] + "_axes.json"
    # Use matplotlib axes position for accurate plot_fraction
    _pf = _pf_from_mpl
    sidecar = {
        "spectrogram_png": os.path.basename(args.output),
        "t_start_utc_hours": start_offset_hr,
        "t_end_utc_hours":   end_offset_hr,
        "doppler_lo_hz":     ylim_lo,
        "doppler_hi_hz":     ylim_hi,
        "dpi":               args.dpi,
        "plot_fraction":     _pf,
        "_note": "Generated by drf_spectrogram.py for use with tid_spect_click.py"
    }
    with open(sidecar_path, "w") as _f:
        _json.dump(sidecar, _f, indent=2)
    print(f"Wrote {sidecar_path}")


if __name__ == "__main__":
    main()
