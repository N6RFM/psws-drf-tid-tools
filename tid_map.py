r"""
tid_map.py — plot TID array geometry: stations, WWV-path midpoints, and
              the inferred wave propagation direction

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial release.

OVERVIEW
========
Reads a tid_doa.py config JSON and produces a map showing:

  - The WWV transmitter at Fort Collins, CO
  - Each receiving station's location
  - The great-circle path from WWV to each station
  - The WWV-path midpoint for each station (the F-region reflection
    point in the single-hop approximation)
  - Optionally a wave propagation arrow centered on the array,
    pointing in the direction of motion (from --azimuth-toward)

Output is a single PNG suitable for inclusion in a TID writeup as
the array-geometry figure.

USAGE
=====
Basic map from a tid_doa.py config:

    python tid_map.py --config event_20260119.json \
        --output array_map.png

Add a wave direction arrow:

    python tid_map.py --config event_20260119.json \
        --output array_map.png \
        --azimuth-toward 215 \
        --speed 666

Without cartopy installed (uses simple equirectangular projection):

    python tid_map.py --config event_20260119.json \
        --output array_map.png --no-cartopy

REQUIREMENTS
============
    pip install pandas numpy matplotlib

Optionally for nicer maps:
    pip install cartopy

If cartopy isn't installed, falls back to a plain lat/lon plot with a
simple US state outline.

SEE ALSO
========
    tid_doa.py            consumes the same config and produces the
                          direction-of-arrival result that you plot here
    find_event_stations.py picks the stations whose geometry the map
                          visualizes
"""

import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
import numpy as np

__version__ = "1.0.0"

WWV_LAT, WWV_LON = 40.6776, -105.0405
EARTH_R_KM = 6371.0


def to_rad(d): return d * math.pi / 180.0
def to_deg(r): return r * 180.0 / math.pi


def great_circle_midpoint(lat1, lon1, lat2, lon2):
    f1, l1 = to_rad(lat1), to_rad(lon1)
    f2, l2 = to_rad(lat2), to_rad(lon2)
    dl = l2 - l1
    bx = math.cos(f2)*math.cos(dl)
    by = math.cos(f2)*math.sin(dl)
    f3 = math.atan2(math.sin(f1)+math.sin(f2),
                    math.sqrt((math.cos(f1)+bx)**2 + by**2))
    l3 = l1 + math.atan2(by, math.cos(f1)+bx)
    return to_deg(f3), (to_deg(l3) + 540) % 360 - 180


def haversine_km(lat1, lon1, lat2, lon2):
    f1, f2 = to_rad(lat1), to_rad(lat2)
    df = to_rad(lat2 - lat1)
    dl = to_rad(lon2 - lon1)
    a = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def offset_position(lat, lon, distance_km, bearing_deg):
    """Compute (lat, lon) at distance_km / bearing from (lat, lon)."""
    f1 = to_rad(lat); l1 = to_rad(lon)
    br = to_rad(bearing_deg)
    d_over_r = distance_km / EARTH_R_KM
    f2 = math.asin(math.sin(f1)*math.cos(d_over_r) +
                   math.cos(f1)*math.sin(d_over_r)*math.cos(br))
    l2 = l1 + math.atan2(math.sin(br)*math.sin(d_over_r)*math.cos(f1),
                          math.cos(d_over_r) - math.sin(f1)*math.sin(f2))
    return to_deg(f2), (to_deg(l2) + 540) % 360 - 180


def great_circle_line(lat1, lon1, lat2, lon2, n=64):
    """Generate intermediate points along the great-circle arc."""
    f1 = to_rad(lat1); l1 = to_rad(lon1)
    f2 = to_rad(lat2); l2 = to_rad(lon2)
    d = 2 * math.asin(math.sqrt(
        math.sin((f2-f1)/2)**2 +
        math.cos(f1)*math.cos(f2)*math.sin((l2-l1)/2)**2))
    if d == 0:
        return [lat1] * n, [lon1] * n
    lats, lons = [], []
    for f in np.linspace(0, 1, n):
        A = math.sin((1-f)*d) / math.sin(d)
        B = math.sin(f*d) / math.sin(d)
        x = A*math.cos(f1)*math.cos(l1) + B*math.cos(f2)*math.cos(l2)
        y = A*math.cos(f1)*math.sin(l1) + B*math.cos(f2)*math.sin(l2)
        z = A*math.sin(f1) + B*math.sin(f2)
        lats.append(to_deg(math.atan2(z, math.sqrt(x*x + y*y))))
        lons.append(to_deg(math.atan2(y, x)))
    return lats, lons


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring for full details.",
    )
    ap.add_argument("--config", required=True,
                    help="tid_doa.py config JSON listing the stations.")
    ap.add_argument("--output", "-o", required=True,
                    help="Output PNG path.")
    ap.add_argument("--azimuth-toward", type=float, default=None,
                    help="Wave propagation azimuth (degrees true, "
                         "direction of motion). If given, draws an "
                         "arrow centered on the array.")
    ap.add_argument("--speed", type=float, default=None,
                    help="Wave phase speed (m/s) for the title.")
    ap.add_argument("--arrow-length-km", type=float, default=400.0,
                    help="Length of the wave-direction arrow, km.")
    ap.add_argument("--no-cartopy", action="store_true",
                    help="Force fallback rendering even if cartopy is "
                         "installed.")
    ap.add_argument("--title", default=None,
                    help="Plot title. Default: auto-generated.")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    stations = cfg["stations"]

    # Compute midpoints and bounding box
    rx_points = [(s["name"], s["lat"], s["lon"]) for s in stations]
    midpoints = [(s["name"],
                  *great_circle_midpoint(WWV_LAT, WWV_LON,
                                          s["lat"], s["lon"]))
                 for s in stations]

    # Bounding box: WWV + all RX + all midpoints
    all_lats = ([WWV_LAT] + [p[1] for p in rx_points] +
                [p[1] for p in midpoints])
    all_lons = ([WWV_LON] + [p[2] for p in rx_points] +
                [p[2] for p in midpoints])

    # Centroid of midpoints (for the wave arrow)
    centroid_lat = float(np.mean([p[1] for p in midpoints]))
    centroid_lon = float(np.mean([p[2] for p in midpoints]))

    # Add a 5-degree margin on each side
    lat_min, lat_max = min(all_lats) - 3, max(all_lats) + 3
    lon_min, lon_max = min(all_lons) - 3, max(all_lons) + 3

    # Try to use cartopy if available
    use_cartopy = False
    if not args.no_cartopy:
        try:
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature
            use_cartopy = True
        except ImportError:
            pass

    if use_cartopy:
        proj = ccrs.PlateCarree()
        fig = plt.figure(figsize=(11, 8))
        ax = plt.axes(projection=proj)
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=proj)
        ax.add_feature(cfeature.STATES.with_scale("50m"),
                       linewidth=0.5, edgecolor="#888888")
        ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
                       linewidth=0.6, edgecolor="#444444")
        ax.add_feature(cfeature.BORDERS.with_scale("50m"),
                       linewidth=0.6, edgecolor="#444444")
        ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.4)
        transform = proj
    else:
        fig, ax = plt.subplots(figsize=(11, 8))
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, linewidth=0.3, alpha=0.4)
        ax.set_xlabel("Longitude (deg)")
        ax.set_ylabel("Latitude (deg)")
        transform = None
        # Note: no state outlines without cartopy. Add a hint.
        ax.text(0.5, 1.02,
                "(install 'cartopy' for state outlines)",
                ha="center", va="bottom", transform=ax.transAxes,
                fontsize=8, style="italic", color="#888888")

    def plot_kwargs():
        return {"transform": transform} if transform else {}

    # Great-circle paths from WWV to each RX, with midpoint markers
    station_colors = ["#0066cc", "#cc0033", "#009933", "#9900cc",
                      "#ff6600", "#0099aa"]
    # Per-station label offsets, in points. Helps avoid label collisions
    # by pushing each label in a sensible direction relative to its marker.
    # Default is up-and-right; some get manual offsets below.
    label_offsets_by_quadrant = {
        # quadrant relative to WWV (approximate)
        "NE": (8, 8), "SE": (8, -16), "SW": (-50, -16), "NW": (-50, 8),
    }
    def quadrant(lat, lon):
        if lat >= WWV_LAT and lon >= WWV_LON: return "NE"
        if lat <  WWV_LAT and lon >= WWV_LON: return "SE"
        if lat <  WWV_LAT and lon <  WWV_LON: return "SW"
        return "NW"

    for i, (name, lat, lon) in enumerate(rx_points):
        color = station_colors[i % len(station_colors)]
        # Great-circle line WWV -> RX
        path_lats, path_lons = great_circle_line(WWV_LAT, WWV_LON,
                                                  lat, lon)
        ax.plot(path_lons, path_lats, color=color, linewidth=0.8,
                alpha=0.55, **plot_kwargs())

        # RX marker
        ax.plot(lon, lat, "s", color=color, markersize=10,
                markeredgecolor="black", markeredgewidth=1.0,
                zorder=5, **plot_kwargs())
        ax.annotate(name, xy=(lon, lat),
                    xytext=label_offsets_by_quadrant[quadrant(lat, lon)],
                    textcoords="offset points",
                    fontsize=10, weight="bold", color=color,
                    bbox=dict(boxstyle="round,pad=0.25",
                              facecolor="white", alpha=0.9,
                              edgecolor=color, linewidth=0.8),
                    zorder=6)

        # Midpoint marker (small circle)
        mp_lat, mp_lon = midpoints[i][1], midpoints[i][2]
        ax.plot(mp_lon, mp_lat, "o", color=color, markersize=8,
                markeredgecolor="black", markeredgewidth=0.8,
                alpha=0.85, zorder=5, **plot_kwargs())

    # WWV transmitter (star)
    ax.plot(WWV_LON, WWV_LAT, "*", color="gold", markersize=22,
            markeredgecolor="black", markeredgewidth=1.2,
            zorder=7, **plot_kwargs())
    ax.annotate("WWV\nFort Collins",
                xy=(WWV_LON, WWV_LAT),
                xytext=(8, -8), textcoords="offset points",
                fontsize=10, weight="bold",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="gold", alpha=0.85,
                          edgecolor="black"),
                zorder=8)

    # Wave-direction arrow centered on the midpoint centroid
    if args.azimuth_toward is not None:
        az = args.azimuth_toward
        half = args.arrow_length_km / 2.0
        tail_lat, tail_lon = offset_position(centroid_lat, centroid_lon,
                                              half, (az + 180) % 360)
        head_lat, head_lon = offset_position(centroid_lat, centroid_lon,
                                              half, az)
        ax.annotate(
            "",
            xy=(head_lon, head_lat),
            xytext=(tail_lon, tail_lat),
            arrowprops=dict(arrowstyle="-|>,head_width=0.8,head_length=1.0",
                            color="red", linewidth=3.5, alpha=0.85),
            zorder=10,
            **plot_kwargs())
        # Label near the arrow head
        label = f"wave -> {az:.0f}°"
        if args.speed is not None:
            label += f"\n{args.speed:.0f} m/s"
        ax.annotate(label,
                    xy=(head_lon, head_lat),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=11, weight="bold", color="darkred",
                    bbox=dict(boxstyle="round,pad=0.35",
                              facecolor="white", alpha=0.92,
                              edgecolor="darkred", linewidth=1.2),
                    zorder=11)

    # Legend
    legend_items = []
    from matplotlib.lines import Line2D
    legend_items.append(Line2D([], [], marker="*", color="gold",
                               markeredgecolor="black", markersize=15,
                               linestyle="None", label="WWV transmitter"))
    legend_items.append(Line2D([], [], marker="s", color="gray",
                               markeredgecolor="black", markersize=10,
                               linestyle="None", label="Receiving station"))
    legend_items.append(Line2D([], [], marker="o", color="gray",
                               markeredgecolor="black", markersize=9,
                               linestyle="None",
                               label="WWV-path midpoint (F-region "
                                     "reflection)"))
    legend_items.append(Line2D([], [], color="gray", linewidth=1.0,
                               alpha=0.55,
                               label="Great-circle propagation path"))
    if args.azimuth_toward is not None:
        legend_items.append(Line2D([], [], color="red", linewidth=3.5,
                                   alpha=0.85,
                                   label="Wave propagation direction"))
    ax.legend(handles=legend_items, loc="lower left", fontsize=9,
              framealpha=0.92)

    # Title
    title_str = args.title
    if not title_str:
        n = len(stations)
        title_str = f"{n}-station HamSCI Grape TID array geometry"
        if args.azimuth_toward is not None:
            title_str += (f"\nWave direction: {args.azimuth_toward:.0f}° "
                          f"true")
            if args.speed is not None:
                title_str += f" at {args.speed:.0f} m/s"
    ax.set_title(title_str, fontsize=12, weight="bold")

    plt.tight_layout()
    plt.savefig(args.output, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
