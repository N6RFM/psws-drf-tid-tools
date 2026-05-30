#!/usr/bin/env python3
"""
fetch_ae_index.py — fetch and plot AE index from WDC Kyoto for a given date
Part of psws-drf-tid-tools

Usage:
  python3 fetch_ae_index.py --date 2026-01-19 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --speed-m-s 239 \\
      --output-dir .

Data source:
  WDC Kyoto real-time AE repository
  https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/data_dir/YYYY/MM/DD/aeYYMMDD

Format:
  Each line = 1 hour of 1-minute AE values
  Line prefix: AEALAOAU    YYMMDDEHH AE QUICKLK
  Values start at column 40

Output:
  ae_YYYYMMDD.png  — full day + zoom plot
  ae_YYYYMMDD.csv  — 1-minute AE values with timestamps
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


AURORAL_ZONE_KM = 3300


def fetch_ae(date_str):
    dt  = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    yr2 = dt.strftime("%y")
    mo2 = dt.strftime("%m")
    dy2 = dt.strftime("%d")
    url = (f"https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/data_dir/"
           f"{dt.year}/{mo2}/{dy2}/ae{yr2}{mo2}{dy2}")
    print(f"Fetching: {url}")
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    ae = []
    for line in r.text.splitlines():
        if 'AE QUICKLK' in line:
            vals = list(map(int, line[40:].split()))
            ae.extend(vals[:60])

    print(f"  {len(ae)} minutes of AE data")
    return ae


def save_csv(ae, date_str, out_path):
    dt0 = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc)
    lines = ["datetime_utc,ae_nt"]
    for i, v in enumerate(ae):
        t = dt0 + datetime.timedelta(minutes=i)
        lines.append(f"{t.isoformat()},{v}")
    out_path.write_text("\n".join(lines) + "\n")
    print(f"  Saved CSV: {out_path.name}")


def plot_ae(ae, date_str, ev_start, ev_end, speed_m_s, out_path):
    dt0 = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc)
    t_h  = np.arange(len(ae)) / 60.0
    ev_s = (ev_start - dt0).total_seconds() / 3600
    ev_e = (ev_end   - dt0).total_seconds() / 3600
    travel_h = AURORAL_ZONE_KM * 1e3 / speed_m_s / 3600

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=False)

    # Full day
    ax1.plot(t_h, ae, 'b-', lw=0.8)
    ax1.axvspan(ev_s, ev_e, alpha=0.25, color='green', label='Event window')
    ax1.axvline(ev_s - travel_h, color='red', lw=1.5, ls='--',
                label=f'Predicted onset (T−{travel_h:.1f}h at {speed_m_s} m/s)')
    ax1.set_ylabel('AE (nT)')
    ax1.set_title(f'AE Index — {date_str}\n'
                  f'Source: WDC Kyoto (wdc.kugi.kyoto-u.ac.jp/ae_realtime/)',
                  fontsize=10)
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 24)

    # Zoom: 6h before event to 3h after
    z0 = max(0.0, ev_s - 6)
    z1 = min(24.0, ev_e + 3)
    mask = (t_h >= z0) & (t_h <= z1)
    ax2.plot(t_h[mask], np.array(ae)[mask], 'b-', lw=1.2)
    ax2.axvspan(ev_s, ev_e, alpha=0.25, color='green', label='Event window')
    ax2.axvline(ev_s - travel_h, color='red', lw=1.5, ls='--',
                label=f'Predicted onset T−{travel_h:.1f}h')
    ax2.axhline(200, color='gray', ls=':', lw=0.8, label='200 nT')

    ev_arr = np.array(ae)
    ev_mask = (t_h >= ev_s) & (t_h <= ev_e)
    if ev_mask.any():
        mean_ae = ev_arr[ev_mask].mean()
        ax2.axhline(mean_ae, color='green', ls='--', lw=0.8,
                    label=f'Event mean {mean_ae:.0f} nT')

    ax2.set_xlabel(f'Hours UTC on {date_str}')
    ax2.set_ylabel('AE (nT)')
    ax2.set_title(f'Zoom: {z0:.0f}h – {z1:.0f}h UTC')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Stats box
    stats = []
    if ev_mask.any():
        stats.append(f"Event mean: {ev_arr[ev_mask].mean():.0f} nT")
        stats.append(f"Event max:  {ev_arr[ev_mask].max():.0f} nT")
    onset_mask = (t_h >= ev_s - travel_h - 1) & (t_h <= ev_s - travel_h + 1)
    if onset_mask.any():
        stats.append(f"Onset peak: {ev_arr[onset_mask].max():.0f} nT")
    stats.append(f"Day max:    {ev_arr.max():.0f} nT @ {t_h[ev_arr.argmax()]:.1f}h")
    ax2.text(0.02, 0.97, "\n".join(stats), transform=ax2.transAxes,
             va='top', fontsize=8, family='monospace',
             bbox=dict(boxstyle='round', fc='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved plot: {out_path.name}")


def main():
    p = argparse.ArgumentParser(description="Fetch and plot AE index from WDC Kyoto")
    p.add_argument("--date",        required=True, help="YYYY-MM-DD")
    p.add_argument("--event-start", required=True, help="ISO8601 UTC")
    p.add_argument("--event-end",   required=True, help="ISO8601 UTC")
    p.add_argument("--speed-m-s",   type=float, default=239,
                   help="DOA speed for travel time marker (default 239)")
    p.add_argument("--output-dir",  default=".", help="Output directory")
    args = p.parse_args()

    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ev_start = datetime.datetime.fromisoformat(args.event_start.replace('Z','+00:00'))
    ev_end   = datetime.datetime.fromisoformat(args.event_end.replace('Z','+00:00'))

    ae = fetch_ae(args.date)
    date_compact = args.date.replace('-','')
    save_csv(ae, args.date, out / f"ae_{date_compact}.csv")
    plot_ae(ae, args.date, ev_start, ev_end, args.speed_m_s,
            out / f"ae_{date_compact}.png")

    print("Done.")


if __name__ == "__main__":
    main()
