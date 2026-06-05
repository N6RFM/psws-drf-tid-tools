#!/usr/bin/env python3
"""
fetch_kp_index.py — fetch and plot Kp index from WDC Kyoto for a given date
Part of psws-drf-tid-tools

Usage:
  python3 fetch_kp_index.py --date 2026-01-19 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --output-dir .

Data source:
  WDC Kyoto Kp/Ap index repository
  https://wdc.kugi.kyoto-u.ac.jp/kp/index.html

Format:
  Kp is reported as 8 values per day (one per 3-hour interval)
  Retrieved via GFZ Potsdam JSON API (no authentication required)
  https://kp.gfz-potsdam.de/app/json/?start=YYYY-MM-DDT00:00:00Z&end=YYYY-MM-DDT23:59:59Z&index=Kp

Output:
  kp_YYYYMMDD.png  — full day bar chart with storm threshold lines + event window
  kp_YYYYMMDD.csv  — 3-hour Kp values with timestamps
"""

import argparse
import datetime
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import requests


# Kp storm thresholds
KP_UNSETTLED = 3
KP_STORM     = 5


def fetch_kp(date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    start = f"{dt.strftime('%Y-%m-%d')}T00:00:00Z"
    end   = f"{dt.strftime('%Y-%m-%d')}T23:59:59Z"
    url = (f"https://kp.gfz-potsdam.de/app/json/"
           f"?start={start}&end={end}&index=Kp")
    print(f"Fetching: {url}")
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    data = r.json()
    times = data["datetime"]
    kp    = data["Kp"]

    print(f"  {len(kp)} Kp values for {date_str}")
    return times, kp


def save_csv(times, kp, out_path):
    lines = ["datetime_utc,kp"]
    for t, v in zip(times, kp):
        lines.append(f"{t},{v:.2f}")
    out_path.write_text("\n".join(lines) + "\n")
    print(f"  Saved CSV: {out_path.name}")


def plot_kp(times, kp, date_str, ev_start, ev_end, out_path):
    dt0 = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc)

    # Convert 3-hour interval start times to hours-since-midnight
    t_h = []
    for t in times:
        dt = datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
        t_h.append((dt - dt0).total_seconds() / 3600.0)
    t_h  = np.array(t_h)
    kp_a = np.array(kp, dtype=float)

    ev_s = (ev_start - dt0).total_seconds() / 3600
    ev_e = (ev_end   - dt0).total_seconds() / 3600

    # Bar colours: green=quiet, yellow=unsettled, red=storm
    colors = []
    for v in kp_a:
        if v >= KP_STORM:
            colors.append('#d62728')
        elif v >= KP_UNSETTLED:
            colors.append('#ff7f0e')
        else:
            colors.append('#2ca02c')

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.bar(t_h, kp_a, width=2.8, align='edge', color=colors,
           edgecolor='white', linewidth=0.5, zorder=2)

    # Storm threshold lines
    ax.axhline(KP_UNSETTLED, color='#ff7f0e', lw=1.2, ls='--',
               label=f'Kp {KP_UNSETTLED} — unsettled', zorder=3)
    ax.axhline(KP_STORM, color='#d62728', lw=1.5, ls='--',
               label=f'Kp {KP_STORM} — storm', zorder=3)

    # Event window
    ax.axvspan(ev_s, ev_e, alpha=0.35, color='steelblue',
               label='Event window', zorder=1)

    ax.set_xlim(0, 24)
    ax.set_ylim(0, 9)
    ax.set_yticks(range(10))
    ax.set_xlabel(f'Hours UTC on {date_str}')
    ax.set_ylabel('Kp')
    ax.set_title(
        f'Kp Index — {date_str}\n'
        f'Source: GFZ Potsdam (kp.gfz-potsdam.de)  |  '
        f'3-hour resolution',
        fontsize=10)
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(True, axis='y', alpha=0.3, zorder=0)

    # Condition label for event window
    ev_mask = (t_h >= ev_s - 3) & (t_h <= ev_e)   # include interval containing ev_s
    if ev_mask.any():
        kp_event_max = kp_a[ev_mask].max()
        kp_event_mean = kp_a[ev_mask].mean()
        if kp_event_max >= KP_STORM:
            condition = "STORM"
            ccolor = '#d62728'
        elif kp_event_max >= KP_UNSETTLED:
            condition = "UNSETTLED"
            ccolor = '#ff7f0e'
        else:
            condition = "QUIET"
            ccolor = '#2ca02c'

        stats = [
            f"Event condition: {condition}",
            f"Event max Kp:    {kp_event_max:.1f}",
            f"Event mean Kp:   {kp_event_mean:.1f}",
            f"Day max Kp:      {kp_a.max():.1f}",
        ]
        ax.text(0.98, 0.97, "\n".join(stats), transform=ax.transAxes,
                va='top', ha='right', fontsize=8, family='monospace',
                color=ccolor,
                bbox=dict(boxstyle='round', fc='white', alpha=0.85))

    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved plot: {out_path.name}")


def main():
    p = argparse.ArgumentParser(description="Fetch and plot Kp index from GFZ Potsdam")
    p.add_argument("--date",        required=True, help="YYYY-MM-DD")
    p.add_argument("--event-start", required=True, help="ISO8601 UTC")
    p.add_argument("--event-end",   required=True, help="ISO8601 UTC")
    p.add_argument("--output-dir",  default=".", help="Output directory")
    args = p.parse_args()

    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ev_start = datetime.datetime.fromisoformat(
        args.event_start.replace('Z', '+00:00'))
    ev_end   = datetime.datetime.fromisoformat(
        args.event_end.replace('Z', '+00:00'))

    times, kp = fetch_kp(args.date)
    date_compact = args.date.replace('-', '')
    save_csv(times, kp, out / f"kp_{date_compact}.csv")
    plot_kp(times, kp, date_str=args.date,
            ev_start=ev_start, ev_end=ev_end,
            out_path=out / f"kp_{date_compact}.png")

    print("Done.")


if __name__ == "__main__":
    main()
