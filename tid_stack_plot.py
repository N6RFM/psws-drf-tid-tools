r"""
tid_stack_plot.py — render a stacked multi-station Doppler comparison plot

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial release.

OVERVIEW
========
Reads multiple Doppler CSVs (from drf_to_doppler.py) and produces a single
multi-panel figure with one panel per station, all aligned on a common time
axis. Visually clarifies inter-station phase relationships in a TID
event and is the natural companion figure for tid_doa.py results.

Each panel shows the same time window with synchronized x-axes; the wave
lead/lag between stations becomes immediately apparent visually.

Optionally overlays a vertical reference line on a chosen feature (e.g.
peak of station 1's wave) across all panels to make the lag visible.

USAGE
=====
Basic usage with manual station list:

    python tid_stack_plot.py \
        --stations N6RFM:n6rfm.csv AA6BD:aa6bd.csv \
                   W7LUX:w7lux.csv AC0G_ND:ac0g_nd.csv \
        --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
        --title "4-station Doppler comparison, 19 Jan 2026" \
        --output stack_jan19.png

Or load from a tid_doa.py config JSON:

    python tid_stack_plot.py --config event_20260119.json \
        --output stack_jan19.png

Mark a reference time across all panels (e.g. peak time at first station):

    python tid_stack_plot.py --config event_20260119.json \
        --output stack_jan19.png \
        --reference-time 2026-01-19T01:13:00

OPTIONS
=======
    --stations N:F N:F ...   List of NAME:FILE pairs (one per station)
    --config FILE.json        Read station list from tid_doa.py config
    --start, --end            Time window (ISO format)
    --output PATH             Output PNG path (required)
    --reference-time T        UTC time at which to draw a vertical
                              reference line in every panel
    --ylim "low,high"         Doppler axis limits in Hz (default auto)
    --title T                 Figure title (default auto-generated)
    --height-per-panel N      Vertical inches per station (default 1.6)

REQUIREMENTS
============
    pip install pandas numpy matplotlib

SEE ALSO
========
    drf_to_doppler.py     produces the Doppler CSVs this script consumes
    tid_doa.py            consumes the same CSVs for DOA analysis
"""

import argparse
import json
import os
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

__version__ = "1.0.0"


def load_doppler(csv_path, t_start=None, t_end=None):
    """Load a Doppler CSV and return (datetime_index, doppler_array)."""
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    tcol = next(c for c in df.columns
                if "time" in c or "stamp" in c or "utc" in c)
    dcol = next(c for c in df.columns if "dop" in c or "freq" in c)
    df[tcol] = pd.to_datetime(df[tcol], utc=True)
    df = df.sort_values(tcol).set_index(tcol)
    if t_start is not None or t_end is not None:
        df = df.loc[t_start:t_end]
    return df.index.to_pydatetime(), df[dcol].to_numpy()


def parse_station_arg(s):
    """Parse 'NAME:path/to/file.csv'."""
    if ":" not in s:
        raise argparse.ArgumentTypeError(
            f"Bad --stations entry {s!r}, expected NAME:FILE")
    name, path = s.split(":", 1)
    return name.strip(), path.strip()


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring for full details.",
    )
    ap.add_argument("--stations", nargs="+", type=parse_station_arg,
                    default=None,
                    help="Station list as NAME:CSVPATH pairs.")
    ap.add_argument("--config", default=None,
                    help="Alternative to --stations: read a tid_doa.py "
                         "config JSON and use its stations list.")
    ap.add_argument("--start", default=None,
                    help="UTC start of window, ISO format. If --config "
                         "is given, defaults to its event_start_utc.")
    ap.add_argument("--end", default=None,
                    help="UTC end of window.")
    ap.add_argument("--output", "-o", required=True,
                    help="Output PNG path.")
    ap.add_argument("--reference-time", default=None,
                    help="Draw a vertical reference line at this UTC "
                         "time across all panels. Useful for marking a "
                         "feature peak time visible at one station and "
                         "showing the lag at others.")
    ap.add_argument("--ylim", default=None,
                    help="Doppler axis limits 'low,high' in Hz. Default: "
                         "auto. If you want negative values, use "
                         "--ylim=-2,2 (with =).")
    ap.add_argument("--title", default=None,
                    help="Figure title. Default: auto-generated.")
    ap.add_argument("--height-per-panel", type=float, default=1.6,
                    help="Figure height in inches per station panel. "
                         "Default: 1.6")
    ap.add_argument("--smooth", type=float, default=None,
                    metavar="N",
                    help="apply Savitzky-Golay smoothing with N-second "
                         "window for PEAK DETECTION only (display trace "
                         "stays raw; helps avoid picking noise spikes "
                         "instead of the true wave peak)")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    # Resolve station list
    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        station_pairs = [(s["name"], s["file"]) for s in cfg["stations"]]
        if not args.start:
            args.start = cfg["event_start_utc"]
        if not args.end:
            args.end = cfg["event_end_utc"]
    elif args.stations:
        station_pairs = args.stations
    else:
        sys.exit("Must provide either --stations or --config.")

    if not args.start or not args.end:
        sys.exit("Must specify --start and --end (or use --config).")

    t_start = pd.Timestamp(args.start.replace("Z", "+00:00"))
    if t_start.tzinfo is None:
        t_start = t_start.tz_localize("UTC")
    t_end = pd.Timestamp(args.end.replace("Z", "+00:00"))
    if t_end.tzinfo is None:
        t_end = t_end.tz_localize("UTC")

    # Load all stations
    print(f"Loading {len(station_pairs)} stations over "
          f"{t_start} to {t_end}...")
    data = []
    for name, csv_path in station_pairs:
        if not os.path.exists(csv_path):
            sys.exit(f"CSV not found: {csv_path}")
        times, doppler = load_doppler(csv_path, t_start, t_end)
        print(f"  {name:<12s} N={len(times)}  range={doppler.min():.2f} "
              f"to {doppler.max():.2f} Hz")
        data.append((name, times, doppler))

    # Build figure
    n_panels = len(data)
    fig_height = max(4.5, n_panels * args.height_per_panel + 1.0)
    fig, axes = plt.subplots(n_panels, 1,
                              figsize=(11, fig_height),
                              sharex=True)
    if n_panels == 1:
        axes = [axes]

    title_str = args.title or (
        f"Multi-station Doppler comparison, "
        f"{t_start.strftime('%Y-%m-%d %H:%M')} – "
        f"{t_end.strftime('%H:%M')} UTC")
    fig.suptitle(title_str, fontsize=13, y=0.995, weight="bold")

    # Determine common ylim
    if args.ylim:
        ylim_lo, ylim_hi = (float(x) for x in args.ylim.split(","))
    else:
        all_d = np.concatenate([d for _, _, d in data])
        ylim_lo = float(np.percentile(all_d, 1))
        ylim_hi = float(np.percentile(all_d, 99))
        margin = (ylim_hi - ylim_lo) * 0.1
        ylim_lo -= margin
        ylim_hi += margin

    # Parse reference time
    ref_time = None
    if args.reference_time:
        ref_time = pd.Timestamp(args.reference_time.replace("Z", "+00:00"))
        if ref_time.tzinfo is None:
            ref_time = ref_time.tz_localize("UTC")

    # Plot each station
    panel_colors = ["#0066cc", "#cc0033", "#009933", "#9900cc",
                    "#ff6600", "#0099aa"]
    for i, (name, times, doppler) in enumerate(data):
        ax = axes[i]
        color = panel_colors[i % len(panel_colors)]
        ax.plot(times, doppler, color=color, linewidth=1.0)
        ax.set_ylabel(f"{name}\nDoppler (Hz)", fontsize=10)
        ax.set_ylim(ylim_lo, ylim_hi)
        ax.axhline(0, color="gray", linewidth=0.5, alpha=0.4)
        ax.grid(True, alpha=0.25)

        # Find and mark this station's peak time.
        # If --smooth N is given, find peak on the smoothed series so
        # noise spikes don't dominate; otherwise use raw.
        if args.smooth is not None:
            try:
                from scipy.signal import savgol_filter
                if len(times) > 1:
                    dt_est = (times[1] - times[0]).total_seconds()
                else:
                    dt_est = 10.0
                poly_order = 3
                n_samples = int(round(args.smooth / dt_est))
                if n_samples < poly_order + 2:
                    n_samples = poly_order + 2
                if n_samples % 2 == 0:
                    n_samples += 1
                smoothed_for_peak = savgol_filter(doppler, n_samples, poly_order)
            except ImportError:
                smoothed_for_peak = doppler
        else:
            smoothed_for_peak = doppler
        peak_idx = int(np.argmax(smoothed_for_peak))
        peak_time = times[peak_idx]
        peak_value = doppler[peak_idx]
        ax.plot(peak_time, peak_value, "v", color=color, markersize=8,
                markeredgecolor="black", zorder=5)
        ax.annotate(f"peak {peak_time.strftime('%H:%M:%S')}",
                    xy=(peak_time, peak_value),
                    xytext=(6, -4), textcoords="offset points",
                    fontsize=8, color=color, weight="bold")

        # Reference time line (same vertical line on every panel)
        if ref_time is not None:
            ax.axvline(ref_time, color="black", linestyle="--",
                       linewidth=1.2, alpha=0.6, zorder=4)

    # Format the shared x-axis
    axes[-1].set_xlabel(f"UTC on {t_start.strftime('%Y-%m-%d')}")
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[-1].xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 15, 30, 45]))

    # Add a legend describing markers
    legend_lines = ["▼ = each station's Doppler peak"]
    if ref_time is not None:
        legend_lines.append(f"╎ dashed = reference time "
                            f"{ref_time.strftime('%H:%M:%S UTC')}")
    fig.text(0.99, 0.005, "  ".join(legend_lines), ha="right", va="bottom",
             fontsize=8, style="italic", color="#555555")

    plt.tight_layout(rect=[0, 0.01, 1, 0.99])
    plt.savefig(args.output, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
