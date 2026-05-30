#!/usr/bin/env python3
"""
fetch_glotec.py — browse, download, and analyse GloTEC TEC anomaly maps
Part of psws-drf-tid-tools

GloTEC is NOAA's GPS TEC assimilation product (replaced US-TEC in 2015).
It provides global and CONUS TEC maps at 10-minute cadence as PNG images.

Usage:
  # Step 1: download GloTEC tar.gz from NOAA NCEI
  #   Browse to: https://www.ngdc.noaa.gov/stp/iono/ustec/
  #   Search date, download glotec_2026_01_19.tar.gz
  #   tar xzf glotec_2026_01_19.tar.gz

  # Step 2: run analysis
  python3 fetch_glotec.py \\
      --glotec-dir ~/Downloads/glotec_2026_01_19 \\
      --date 2026-01-19 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --output-dir .

Outputs:
  glotec_products.txt          List of all product types in archive
  glotec_event_montage.png     CONUS anomaly maps spanning event window
  glotec_before_after.png      Before / during / after comparison
  glotec_diff.png              Pixel difference: event end − event start
  glotec_na_montage.png        North America anomaly maps (wider view)

Product types in GloTEC archive:
  anomcus   CONUS TEC anomaly (diff from 30-day median) ← most useful for TID
  anomna    North America TEC anomaly
  anomaly   Global TEC anomaly
  anomalyp  Global TEC anomaly with position error
  100asm    CONUS absolute TEC
  100asmp   CONUS absolute TEC with position error
  100cus    CONUS TEC (alternate projection)
  100na     North America absolute TEC
  ray       CONUS ray paths
  rayp      CONUS ray paths with position error

Colour scale:
  Orange/brown = positive anomaly (TEC above 30-day median)
  Purple/blue  = negative anomaly (TEC below 30-day median)
  Scale: approximately ±30 TECU

TID detection notes:
  - LSTID at 239 m/s with ~70 min period → wavelength ~1000 km
  - GloTEC grid ~2° (~200 km) — in principle sufficient
  - But assimilation smoothing and storm-time enhancements can mask TIDs
  - For Jan 19 2026: storm-time +15 TECU enhancement dominates
  - Higher-resolution line-of-sight TEC (MIT Haystack Madrigal) needed
    to isolate individual wavefronts

Data source:
  NOAA NCEI GloTEC archive
  https://www.ngdc.noaa.gov/stp/iono/ustec/
"""

import argparse
import datetime
import math
import pathlib
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import requests
from PIL import Image


def list_products(glotec_dir, date_str):
    """List all product types in the GloTEC directory."""
    d = pathlib.Path(glotec_dir)
    types = {}
    for f in d.glob("glotec_*_urt_*.png"):
        m = re.match(r'glotec_([^_]+(?:_[^_]+)?)_urt_', f.name)
        if m:
            pt = m.group(1)
            types[pt] = types.get(pt, 0) + 1
    return types


def parse_time(fpath, date_str):
    m = re.search(r'T(\d{6})\.png$', str(fpath))
    if not m:
        return None
    return datetime.datetime.strptime(
        f"{date_str.replace('-','')}T{m.group(1)}", "%Y%m%dT%H%M%S"
    ).replace(tzinfo=datetime.timezone.utc)


def get_files(glotec_dir, date_str, product='anomcus'):
    d = pathlib.Path(glotec_dir)
    files = sorted(d.glob(
        f"glotec_{product}_urt_{date_str.replace('-','')}T*.png"))
    return [(parse_time(f, date_str), f) for f in files
            if parse_time(f, date_str)]


def plot_montage(files_times, title, out_path, ev_start=None, ev_end=None,
                 cols=4):
    n = len(files_times)
    if n == 0:
        return
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols,
                              figsize=(5.5*cols, 4.5*rows + 1.2))
    axes = np.array(axes).reshape(rows, cols)

    for i, (ft, f) in enumerate(files_times):
        r, c = divmod(i, cols)
        ax = axes[r, c]
        ax.imshow(mpimg.imread(str(f)))
        in_ev = (ev_start and ev_end and ev_start <= ft <= ev_end)
        label = ft.strftime('%H:%M UTC') + (' ✓' if in_ev else '')
        ax.set_title(label, fontsize=9,
                     color='green' if in_ev else 'gray',
                     fontweight='bold' if in_ev else 'normal')
        ax.axis('off')

    for i in range(n, rows * cols):
        r, c = divmod(i, cols)
        axes[r, c].axis('off')

    plt.suptitle(title, fontsize=9)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_before_after(glotec_dir, date_str, ev_start, ev_end, out_path):
    files = get_files(glotec_dir, date_str, 'anomcus')
    if not files:
        return

    targets = {
        f'Before\n(−30 min)\n{(ev_start-datetime.timedelta(minutes=30)).strftime("%H:%M UTC")}':
            ev_start - datetime.timedelta(minutes=30),
        f'Mid-event\n{((ev_start+(ev_end-ev_start)/2)).strftime("%H:%M UTC")}':
            ev_start + (ev_end - ev_start) / 2,
        f'After\n(+30 min)\n{(ev_end+datetime.timedelta(minutes=30)).strftime("%H:%M UTC")}':
            ev_end + datetime.timedelta(minutes=30),
    }

    frames = {}
    for label, target in targets.items():
        best_dt, best_f = min(files, key=lambda x: abs((x[0]-target).total_seconds()))
        frames[label] = (best_dt, best_f)

    fig, axes = plt.subplots(1, len(frames), figsize=(6*len(frames), 5.5))
    for ax, (label, (ft, f)) in zip(axes, frames.items()):
        ax.imshow(mpimg.imread(str(f)))
        ax.set_title(label, fontsize=9)
        ax.axis('off')

    plt.suptitle(
        f"GloTEC CONUS TEC Anomaly — Before / During / After\n"
        f"{date_str}  |  Source: NOAA NCEI GloTEC\n"
        f"Orange=positive (+TECU)  Purple=negative (−TECU)  Scale≈±30 TECU",
        fontsize=9)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_diff(glotec_dir, date_str, ev_start, ev_end, out_path):
    files = get_files(glotec_dir, date_str, 'anomcus')
    if not files:
        return

    t0, f0 = min(files, key=lambda x: abs((x[0]-ev_start).total_seconds()))
    t1, f1 = min(files, key=lambda x: abs((x[0]-ev_end).total_seconds()))

    img0 = np.array(Image.open(str(f0)).convert('RGB')).astype(float)
    img1 = np.array(Image.open(str(f1)).convert('RGB')).astype(float)
    diff = img1 - img0
    diff_disp = (diff - diff.min()) / max(diff.max() - diff.min(), 1e-6)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    axes[0].imshow(img0.astype(np.uint8))
    axes[0].set_title(f"Event start\n{t0.strftime('%H:%M UTC')}", fontsize=10)
    axes[0].axis('off')
    axes[1].imshow(img1.astype(np.uint8))
    axes[1].set_title(f"Event end\n{t1.strftime('%H:%M UTC')}", fontsize=10)
    axes[1].axis('off')
    axes[2].imshow(diff_disp)
    axes[2].set_title("Difference (end − start)\nBright=TEC increased  Dark=TEC decreased",
                       fontsize=9)
    axes[2].axis('off')

    plt.suptitle(
        f"GloTEC CONUS Anomaly Change Over Event Window  |  {date_str}\n"
        f"Source: NOAA NCEI GloTEC  |  "
        f"Note: broad storm-time changes dominate at this resolution",
        fontsize=9)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {out_path.name}")


def main():
    p = argparse.ArgumentParser(
        description="Analyse GloTEC TEC anomaly maps for TID event",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("--glotec-dir",  required=True,
                   help="Path to extracted GloTEC directory")
    p.add_argument("--date",        required=True, help="YYYY-MM-DD")
    p.add_argument("--event-start", required=True, help="ISO8601 UTC")
    p.add_argument("--event-end",   required=True, help="ISO8601 UTC")
    p.add_argument("--output-dir",  default=".", help="Output directory")
    p.add_argument("--product",     default="anomcus",
                   help="GloTEC product type (default: anomcus)")
    args = p.parse_args()

    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ev_start = datetime.datetime.fromisoformat(
        args.event_start.replace('Z','+00:00'))
    ev_end   = datetime.datetime.fromisoformat(
        args.event_end.replace('Z','+00:00'))

    # List products
    print("Products in archive:")
    prods = list_products(args.glotec_dir, args.date)
    prod_txt = out / "glotec_products.txt"
    lines = [f"GloTEC archive: {args.glotec_dir}",
             f"Date: {args.date}", "",
             "Product types:"]
    for pt, n in sorted(prods.items()):
        lines.append(f"  {pt:12s}  {n:4d} files")
    prod_txt.write_text("\n".join(lines) + "\n")
    for pt, n in sorted(prods.items()):
        print(f"  {pt:12s}  {n:4d} files")

    # Event montage
    files = get_files(args.glotec_dir, args.date, args.product)
    t0 = ev_start - datetime.timedelta(minutes=10)
    t1 = ev_end   + datetime.timedelta(minutes=20)
    event_files = [(ft, f) for ft, f in files if t0 <= ft <= t1]
    print(f"\nEvent window files ({args.product}): {len(event_files)}")

    if event_files:
        plot_montage(
            event_files,
            f"GloTEC {args.product.upper()} TEC Anomaly — {args.date}\n"
            f"Event: {ev_start.strftime('%H:%M')}–{ev_end.strftime('%H:%M')} UTC  "
            f"(✓ = within window)  Orange=+TECU  Purple=−TECU  "
            f"Source: NOAA NCEI",
            out / f"glotec_event_montage.png",
            ev_start=ev_start, ev_end=ev_end
        )

    # Before/after
    plot_before_after(args.glotec_dir, args.date, ev_start, ev_end,
                      out / "glotec_before_after.png")

    # Diff
    plot_diff(args.glotec_dir, args.date, ev_start, ev_end,
              out / "glotec_diff.png")

    # North America montage if requested
    na_files = get_files(args.glotec_dir, args.date, 'anomna')
    na_event = [(ft, f) for ft, f in na_files if t0 <= ft <= t1]
    if na_event:
        plot_montage(
            na_event,
            f"GloTEC ANOMNA (North America) — {args.date}\n"
            f"Event: {ev_start.strftime('%H:%M')}–{ev_end.strftime('%H:%M')} UTC  "
            f"Source: NOAA NCEI",
            out / "glotec_na_montage.png",
            ev_start=ev_start, ev_end=ev_end
        )

    print(f"\nAll outputs in: {out.resolve()}")
    print("\nNote on TID detection:")
    print("  GloTEC ~2deg resolution can mask individual LSTID wavefronts.")
    print("  Storm-time enhancements dominate when Kp > 3.")
    print("  For wavefront tracking use MIT Haystack Madrigal GPS TEC.")
    print("  Register free: https://urs.earthdata.nasa.gov/")


if __name__ == "__main__":
    main()
