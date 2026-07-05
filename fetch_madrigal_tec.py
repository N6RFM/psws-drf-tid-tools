#!/usr/bin/env python3
"""
fetch_madrigal_tec.py — retrieve and analyse MIT Haystack Madrigal GPS TEC
for TID DOA corroboration
Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)

Retrieves gridded GPS TEC from the MIT Haystack Madrigal database, extracts
TEC time series at station locations, detrends to remove storm background,
and cross-correlates station pairs to independently estimate TID phase lags.

PREREQUISITES:
  pip install madrigalWeb matplotlib numpy scipy

  Madrigal requires user registration (free, no auth token needed):
  Simply provide your name, email, and affiliation when calling the script.
  No account creation required — Madrigal uses open access.

  Instrument code for GPS TEC: 8000
  Database URL: https://cedar.openmadrigal.org/

DATA FILE TYPES (kindat):
  3500  gps*g.*.hdf5       Gridded global TEC (recommended — use this)
  3505  los_*.h5           Line-of-sight TEC (very large, not recommended)
  3506  site_*.h5          Site TEC
  3507  roti_*.h5          Rate of TEC index

USAGE:
  # Basic — extracts TEC at station locations, detrends, cross-correlates
  python3 fetch_madrigal_tec.py \\
      --date 2026-01-19 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --stations N6RFM,-97.21,32.94 AA6BD,-85.13,35.06 W7LUX,-111.71,35.10 AC0G_ND,-96.83,46.88 \\
      --user-name "Your Name" \\
      --user-email your@email.com \\
      --user-affiliation "Your Institution" \\
      --doa-lags AA6BD,N6RFM,1253 AA6BD,W7LUX,1481 N6RFM,W7LUX,228 \\
      --output-dir ./evaluation

  # With DOA speed/direction for projected lag comparison
  python3 fetch_madrigal_tec.py \\
      --date 2026-01-19 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --stations N6RFM,-97.21,32.94 AA6BD,-85.13,35.06 W7LUX,-111.71,35.10 AC0G_ND,-96.83,46.88 \\
      --user-name "Your Name" \\
      --user-email your@email.com \\
      --user-affiliation "Your Institution" \\
      --doa-lags AA6BD,N6RFM,1253 AA6BD,W7LUX,1481 N6RFM,W7LUX,228 \\
      --doa-speed 239 \\
      --doa-azimuth-from 30 \\
      --output-dir ./evaluation

OUTPUTS:
  madrigal_tec_raw.png         Raw TEC time series at all stations
  madrigal_tec_detrended.png   Detrended TEC + AA6BD vs N6RFM xcorr
  madrigal_tec_xcorr.png       All pairwise cross-correlations
  madrigal_tec_report.txt      Full text summary of results

HOW IT WORKS:
  1. Connects to Madrigal at https://cedar.openmadrigal.org/
  2. Searches for GPS TEC experiments on the event date (instrument 8000)
  3. Finds the gridded TEC file (kindat=3500)
  4. Extracts TEC at each station using isprint with spatial filters
  5. Bins to 1-minute grid (mean of all GPS links in ±3°×4° box)
  6. Removes 2nd-order polynomial trend (storm background)
  7. Cross-correlates all station pairs
  8. Compares GPS TEC lags to DOA spline lags (if provided)
  9. Computes implied true phase speed from GPS TEC lags

INTERPRETING RESULTS:
  - GPS TEC amplitude ~0.1-0.5 TECU during LSTID events
  - Storm-time TEC enhancement can be 10-20x larger — detrending essential
  - 1-min bins give ~90 points over 75-min window — adequate for xcorr
  - Primary xcorr peak at lag=0 often reflects correlated storm background
  - Look for secondary peak near the DOA-predicted lag
  - Along-baseline speed ≠ true phase speed — use projected_lag for comparison

KNOWN LIMITATIONS:
  - Gridded TEC (3500) has ~1° resolution — adequate for LSTID not MSTID
  - Station boxes (±3°×4°) average over spatial TID structure
  - Storm-time TEC gradient can mimic TID lags if not fully detrended
  - Madrigal data typically available with 2-4 week latency

WORKED EXAMPLE — Jan 2026 LSTID:
  Event: 2026-01-19 00:00-01:15 UTC
  DOA result: 239 m/s from 30° NNE (4 stations, 1/5 flags)
  
  GPS TEC results:
    AA6BD→W7LUX: GPS TEC lag 22 min vs DOA 24.7 min (12% agreement)
    AA6BD→N6RFM: ambiguous (peak at 0 lag — storm background dominates)
    N6RFM→W7LUX: ambiguous (3.8 min DOA lag < 1 bin resolution)
  
  Implied true speed from GPS TEC (AA6BD→W7LUX):
    Along-baseline: 914 m/s (GPS) vs 815 m/s (DOA)
    True phase speed: ~423 m/s (GPS) vs 239 m/s (DOA)
  
  The AA6BD→W7LUX baseline (272°, nearly E-W) is 62° from the wave
  direction — the large along-baseline speed reflects geometric projection,
  not the true wave speed. The GPS TEC confirms NNE propagation direction.

Author: N6RFM with Claude AI
Version: 1.1.0

Change log:
  v1.1.0  Added DOA CROSS-CHECK INTERPRETATION: an automated verdict
          (CONSISTENT / MOSTLY CONSISTENT / INCONSISTENT) summarizing
          agreement between DOA-predicted and GPS-TEC-observed lags,
          plus per-station mean disagreement and outlier-station
          flagging. Computed directly from xcorr_results (no text
          parsing), printed to console AND written to report.txt --
          previously only visible if the dashboard parsed it out of
          the saved report file after the fact. New --tec-tolerance-min
          flag (default 20.0 min). No change to any existing computed
          value; purely additive.
"""

import argparse
import datetime
import math
import os
import pathlib
import sys
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

try:
    import madrigalWeb.madrigalWeb as mad
except ImportError:
    print("ERROR: madrigalWeb not installed. Run: pip install madrigalWeb")
    sys.exit(1)

VERSION = "1.1.0"
MADRIGAL_URL = "https://cedar.openmadrigal.org/"
GPS_TEC_CODE = 8000      # Madrigal instrument code for GPS TEC
GRIDDED_KINDAT = 3500    # kindat for gridded global TEC


# ── Geometry helpers ──────────────────────────────────────────────────────

def gc_dist_km(lon1, lat1, lon2, lat2):
    """Great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = (np.sin(dphi/2)**2 +
         np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2)
    return 2*R*np.arcsin(np.sqrt(a))


def bearing_deg(lon1, lat1, lon2, lat2):
    """Bearing from point 1 to point 2 (degrees clockwise from N)."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlam = np.radians(lon2 - lon1)
    x = np.sin(dlam)*np.cos(phi2)
    y = np.cos(phi1)*np.sin(phi2) - np.sin(phi1)*np.cos(phi2)*np.cos(dlam)
    return np.degrees(np.arctan2(x, y)) % 360


def projected_lag_s(dist_km, az_toward_deg, baseline_bear_deg, speed_ms):
    """
    Expected lag (seconds) for wave propagating at speed_ms from az_toward_deg,
    projected onto baseline with bearing baseline_bear_deg.
    Positive = second station lags first.
    """
    proj = np.cos(np.radians(az_toward_deg) - np.radians(baseline_bear_deg))
    return (dist_km * 1000 * proj) / speed_ms


# ── Madrigal access ───────────────────────────────────────────────────────

def connect_madrigal():
    print(f"Connecting to Madrigal at {MADRIGAL_URL}...")
    m = mad.MadrigalData(MADRIGAL_URL)
    print("  Connected OK")
    return m


def find_gridded_file(m, date_str):
    """Find the gridded GPS TEC file for the given date."""
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    print(f"Searching for GPS TEC experiments on {date_str}...")
    exps = m.getExperiments(
        GPS_TEC_CODE,
        dt.year, dt.month, dt.day, 0, 0, 0,
        dt.year, dt.month, dt.day, 23, 59, 59
    )
    if not exps:
        raise RuntimeError(f"No GPS TEC experiments found for {date_str}")

    # Find experiment matching the date (not the day before)
    day_str = dt.strftime("%d%b%y").lower()  # e.g. "19jan26"
    target = [e for e in exps if day_str in e.url.lower()]
    if not target:
        target = exps  # fallback: use all

    print(f"  Found {len(target)} experiment(s)")
    for exp in target:
        print(f"    id={exp.id}  url={exp.url}")
        files = m.getExperimentFiles(exp.id)
        for f in files:
            if f.kindat == GRIDDED_KINDAT:
                print(f"    Gridded TEC file: {f.name.split('/')[-1]}"
                      f"  status={f.status}")
                return f.name

    raise RuntimeError(f"No gridded TEC file (kindat={GRIDDED_KINDAT}) found")


def extract_tec(m, fname, station_name, lon, lat,
                ev_start_h, ev_end_h,
                user_name, user_email, user_affil,
                lat_box=3.0, lon_box=4.0):
    """
    Extract TEC at a station location using Madrigal isprint.
    Returns array of [lat, lon, uth, tec] rows.
    """
    outfile = f"/tmp/madrigal_tec_{station_name}.txt"
    filter_str = (
        f"filter=UTH,{ev_start_h-0.1},{ev_end_h+0.5} "
        f"filter=GDLAT,{lat-lat_box},{lat+lat_box} "
        f"filter=GLON,{lon-lon_box},{lon+lon_box}"
    )
    m.isprint(
        fname, "GDLAT,GLON,UTH,TEC",
        filter_str,
        user_name, user_email, user_affil,
        outputFile=outfile
    )
    rows = []
    if os.path.exists(outfile):
        with open(outfile) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('GDLAT') and not line.startswith('Traceback'):
                    try:
                        parts = line.split()
                        if len(parts) >= 4:
                            rows.append([float(x) for x in parts[:4]])
                    except:
                        pass
    return np.array(rows) if rows else None


def bin_tec(arr, t_start, t_end, bin_min=1.0, min_links=3):
    """
    Bin TEC to regular time grid.
    Returns (t_hours, tec_tecu, n_links) arrays.
    """
    bins = np.arange(t_start, t_end + bin_min/60, bin_min/60)
    t_out, tec_out, n_out = [], [], []
    half = (bin_min/60) / 2
    for tb in bins:
        mask = np.abs(arr[:, 2] - tb) < half
        if mask.sum() >= min_links:
            t_out.append(tb)
            tec_out.append(arr[mask, 3].mean())
            n_out.append(int(mask.sum()))
    return np.array(t_out), np.array(tec_out), np.array(n_out)


def detrend_tec(t, tec, poly_order=2):
    """Remove polynomial trend from TEC time series."""
    if len(t) < poly_order + 2:
        return tec, np.zeros_like(tec)
    coeffs = np.polyfit(t, tec, poly_order)
    trend = np.polyval(coeffs, t)
    return tec - trend, trend


def xcorr_lags(d1, d2, dt_min=1.0, max_lag_min=60):
    """
    Cross-correlate two detrended TEC series.
    Returns (lags_min, xcorr, peak_lag_min).
    """
    n = len(d1)
    xc = np.correlate(d1 - d1.mean(), d2 - d2.mean(), mode='full')
    denom = np.std(d1) * np.std(d2) * n
    if denom > 0:
        xc /= denom
    lags = (np.arange(len(xc)) - n + 1) * dt_min
    # Restrict to max_lag_min
    mask = np.abs(lags) <= max_lag_min
    lags_r = lags[mask]
    xc_r = xc[mask]
    peak_lag = lags_r[np.argmax(xc_r)]
    return lags_r, xc_r, peak_lag


# ── Plotting ──────────────────────────────────────────────────────────────

def plot_raw(binned, ev_start_h, ev_end_h, date_str, out_path):
    fig, ax = plt.subplots(figsize=(13, 5))
    colors = ['blue','red','green','purple','orange','brown']
    for (name, (t, tec, n)), col in zip(binned.items(), colors):
        ax.plot(t*60, tec, '-o', ms=3, lw=1.2, color=col,
                label=f"{name} ({len(t)} bins)")
    ax.axvspan(ev_start_h*60, ev_end_h*60, alpha=0.15, color='green',
               label='Event window')
    ax.set_xlabel('Minutes UTC')
    ax.set_ylabel('VTEC (TECU)')
    ax.set_title(f'Madrigal GPS TEC — {date_str}\n'
                 f'Source: MIT Haystack (cedar.openmadrigal.org)  '
                 f'Instrument 8000  Kindat 3500  1-min bins ≥3 GPS links')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_detrended(det, ev_start_h, ev_end_h, date_str,
                   primary_pair, doa_lags, out_path):
    s1, s2 = primary_pair
    fig, axes = plt.subplots(2, 1, figsize=(13, 9))

    colors = ['blue','red','green','purple','orange','brown']
    ax1 = axes[0]
    for (name, (t, d)), col in zip(det.items(), colors):
        ax1.plot(t*60, d, '-', lw=1, color=col, alpha=0.8,
                 label=f"{name} σ={np.std(d):.3f}")
    ax1.axvspan(ev_start_h*60, ev_end_h*60, alpha=0.15, color='green')
    ax1.axhline(0, color='gray', lw=0.8)
    ax1.set_ylabel('Detrended TEC (TECU)')
    ax1.set_title(f'Detrended GPS TEC — {date_str}\n'
                  f'2nd-order polynomial removed to isolate TID signal')
    ax1.legend(fontsize=8); ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    if s1 in det and s2 in det:
        t_c = np.arange(ev_start_h, ev_end_h + 1/60, 1/60)
        d1 = np.interp(t_c, det[s1][0], det[s1][1])
        d2 = np.interp(t_c, det[s2][0], det[s2][1])
        lags, xc, peak = xcorr_lags(d1, d2)
        doa_lag_min = doa_lags.get((s1,s2), doa_lags.get((s2,s1), None))
        ax2.plot(lags, xc, 'b-', lw=1.5)
        ax2.axvline(peak, color='red', lw=1.5, ls='--',
                    label=f'GPS TEC peak = {peak:.0f} min')
        if doa_lag_min is not None:
            ax2.axvline(doa_lag_min/60, color='orange', lw=1.5, ls='--',
                        label=f'DOA lag = {doa_lag_min/60:.1f} min')
        ax2.axvline(0, color='gray', lw=0.5)
        ax2.set_xlim(-60, 60)
        ax2.set_xlabel(f'Lag (min)  positive = {s2} lags {s1}')
        ax2.set_ylabel('Correlation')
        ax2.set_title(f'Cross-correlation: {s1} vs {s2}')
        ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_xcorr_all(det, ev_start_h, ev_end_h, doa_lags, date_str, out_path):
    names = list(det.keys())
    pairs = [(names[i], names[j])
             for i in range(len(names))
             for j in range(i+1, len(names))]

    ncols = 2
    nrows = math.ceil(len(pairs) / ncols)
    fig, axes = plt.subplots(nrows, ncols,
                              figsize=(14, 4*nrows + 1))
    axes = np.array(axes).reshape(-1)
    t_c = np.arange(ev_start_h, ev_end_h + 1/60, 1/60)

    results = []
    for ax, (s1, s2) in zip(axes, pairs):
        if s1 not in det or s2 not in det:
            ax.axis('off'); continue
        d1 = np.interp(t_c, det[s1][0], det[s1][1])
        d2 = np.interp(t_c, det[s2][0], det[s2][1])
        lags, xc, peak = xcorr_lags(d1, d2)
        doa_s = doa_lags.get((s1,s2), doa_lags.get((s2,s1), None))

        ax.plot(lags, xc, 'b-', lw=1)
        ax.axvline(peak, color='red', lw=1.5, ls='--',
                   label=f'GPS peak={peak:.0f}m')
        if doa_s is not None:
            ax.axvline(doa_s/60, color='orange', lw=1.5, ls='--',
                       label=f'DOA={doa_s/60:.1f}m')
        ax.axvline(0, color='gray', lw=0.5)
        ax.set_xlim(-60, 60)
        ax.set_title(f'{s1} → {s2}', fontsize=9)
        ax.set_xlabel('Lag (min)', fontsize=7)
        ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

        results.append((s1, s2, peak, doa_s))

    for ax in axes[len(pairs):]:
        ax.axis('off')

    plt.suptitle(f'GPS TEC cross-correlations — {date_str}\n'
                 f'Red=GPS TEC peak  Orange=DOA spline prediction',
                 fontsize=10)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")
    return results


# ── Report ────────────────────────────────────────────────────────────────

def interpret_doa_tec_agreement(xcorr_results, tolerance_min=20.0):
    """Summarize agreement between the DOA result's predicted lags and the
    independently-measured GPS-TEC lags into a plain verdict plus
    supporting numbers. Flag-don't-fail in spirit, like tid_doa.py's own
    RESULT DIAGNOSTICS -- this doesn't assert ground truth, just surfaces
    where agreement is weak and which station (if any) is dragging it
    down, the same way a person would otherwise eyeball the comparison
    table by hand.

    tolerance_min is deliberately loose (20 min default) -- MSTID-scale
    GPS TEC lags are a blunt cross-check against a DOA fit built from
    Doppler cross-correlation; exact numeric agreement isn't expected,
    only rough directional consistency.

    Returns None if no pair has a DOA lag to compare against (e.g.
    --doa-speed/--doa-azimuth-from weren't supplied), otherwise a dict
    with verdict / mean_diff_min / within_tolerance / total_pairs /
    station_means / flagged_station / spread_min.
    """
    diffs_by_pair = []
    for s1, s2, peak_min, doa_s in xcorr_results:
        if not doa_s:
            continue
        doa_min = doa_s / 60.0
        diffs_by_pair.append((s1, s2, abs(peak_min - doa_min)))

    if not diffs_by_pair:
        return None

    diffs = [d for _, _, d in diffs_by_pair]
    mean_diff = sum(diffs) / len(diffs)
    within = sum(1 for d in diffs if d <= tolerance_min)
    total = len(diffs_by_pair)

    station_diffs = {}
    for s1, s2, d in diffs_by_pair:
        station_diffs.setdefault(s1, []).append(d)
        station_diffs.setdefault(s2, []).append(d)
    station_means = {s: sum(v) / len(v) for s, v in station_diffs.items()}
    worst_station = max(station_means, key=station_means.get)
    best_station = min(station_means, key=station_means.get)
    spread = station_means[worst_station] - station_means[best_station]

    if within == total and mean_diff <= tolerance_min * 0.6:
        verdict = "CONSISTENT"
    elif within >= total * 0.6:
        verdict = "MOSTLY CONSISTENT"
    else:
        verdict = "INCONSISTENT"

    # Only flag a station as a likely outlier if it's clearly separated
    # from the rest, not just nominally the worst of a tight cluster.
    flagged_station = worst_station if spread > tolerance_min else None

    return {
        "verdict": verdict,
        "mean_diff_min": mean_diff,
        "within_tolerance": within,
        "total_pairs": total,
        "tolerance_min": tolerance_min,
        "station_means": station_means,
        "flagged_station": flagged_station,
        "spread_min": spread,
    }


def print_and_append_interpretation(lines, interp):
    """Render an interpretation dict as both report-file lines (appended
    to `lines` in place) and printed directly to the console -- so the
    verdict is visible immediately in CLI usage, not just buried in the
    saved report.txt that write_report() otherwise only confirms by
    filename ('Saved: ...'), never prints the content of."""
    verdict_text = {
        "CONSISTENT": "CONSISTENT with the DOA result.",
        "MOSTLY CONSISTENT": "MOSTLY CONSISTENT with the DOA result -- some pairs disagree.",
        "INCONSISTENT": "does NOT support this DOA result well -- most pairs disagree.",
    }[interp["verdict"]]

    block = [
        "",
        "DOA CROSS-CHECK INTERPRETATION:",
        "",
        f"  Verdict: {interp['verdict']} -- TEC cross-check {verdict_text}",
        f"  {interp['within_tolerance']}/{interp['total_pairs']} pairs agree within "
        f"{interp['tolerance_min']:.0f} min (mean |diff| = {interp['mean_diff_min']:.1f} min)",
        "",
        "  Per-station mean disagreement (minutes):",
    ]
    for s, m in sorted(interp["station_means"].items(), key=lambda x: -x[1]):
        block.append(f"    {s:12s} {m:6.1f}")

    if interp["flagged_station"]:
        block += [
            "",
            f"  >> {interp['flagged_station']} stands out as a likely outlier -- its pairs "
            f"disagree by {interp['spread_min']:.1f} min more, on average, than the "
            f"best-agreeing station. Worth checking that station's data quality "
            f"(e.g. E-region contamination) before trusting the overall DOA result.",
        ]

    block += [
        "",
        "  This is an automated heuristic, not a definitive verdict -- it flags",
        "  where to look closer, the same way tid_doa.py's own RESULT",
        "  DIAGNOSTICS do. Always check the actual cross-correlation plots",
        "  before drawing conclusions.",
    ]

    lines.extend(block)
    print("\n" + "\n".join(block))


def write_report(out_path, date_str, ev_start, ev_end,
                 stations, binned, det, xcorr_results,
                 doa_lags, doa_speed, doa_az_from, madrigal_file,
                 tec_tolerance_min=20.0):

    lines = [
        "=" * 68,
        "MADRIGAL GPS TEC ANALYSIS REPORT",
        f"fetch_madrigal_tec.py v{VERSION}",
        "=" * 68,
        f"Event date:    {date_str}",
        f"Event window:  {ev_start.strftime('%H:%M')}–"
        f"{ev_end.strftime('%H:%M')} UTC",
        f"Madrigal file: {madrigal_file.split('/')[-1]}",
        f"Database:      {MADRIGAL_URL}",
        f"Instrument:    {GPS_TEC_CODE} (GPS TEC)  "
        f"Kindat: {GRIDDED_KINDAT} (gridded)",
        "",
        "STATIONS:",
    ]
    for name, (lon, lat) in stations.items():
        nb = len(binned[name][0]) if name in binned else 0
        lines.append(f"  {name:10s}  lat={lat:.2f}°N  lon={lon:.2f}°E  "
                     f"bins={nb}")

    lines += ["", "DATA EXTRACTION:", "  Method: madrigalWeb isprint API",
              "  Parameters: GDLAT, GLON, UTH, TEC",
              "  Spatial box: ±3° lat, ±4° lon around station IPP",
              "  Temporal: event window ±30 min",
              "  Binning: 1-minute mean of all GPS links (min 3 links/bin)",
              "  Detrending: 2nd-order polynomial removed",
              ""]

    if doa_speed and doa_az_from:
        lines += [
            f"DOA REFERENCE:",
            f"  Speed:     {doa_speed} m/s",
            f"  From:      {doa_az_from}° (toward {(doa_az_from+180)%360}°)",
            "",
        ]

    lines += ["CROSS-CORRELATION RESULTS:", ""]
    lines.append(f"  {'Pair':20s}  {'GPS lag(min)':>12s}  "
                 f"{'DOA lag(min)':>12s}  {'Diff(min)':>10s}")
    lines.append("  " + "-"*60)

    for s1, s2, peak_min, doa_s in xcorr_results:
        doa_min = doa_s/60 if doa_s else None
        diff = f"{peak_min - doa_min:.1f}" if doa_min else "---"
        doa_str = f"{doa_min:.1f}" if doa_min else "---"
        lines.append(f"  {s1}→{s2:10s}  {peak_min:>12.0f}  "
                     f"{doa_str:>12s}  {diff:>10s}")

    if doa_speed and doa_az_from and xcorr_results:
        lines += ["", "SPEED ESTIMATES FROM GPS TEC LAGS:"]
        az_toward = (doa_az_from + 180) % 360
        for s1, s2, peak_min, doa_s in xcorr_results:
            if peak_min == 0 or s1 not in stations or s2 not in stations:
                continue
            lon1, lat1 = stations[s1]
            lon2, lat2 = stations[s2]
            dist = gc_dist_km(lon1, lat1, lon2, lat2)
            bear = bearing_deg(lon1, lat1, lon2, lat2)
            angle = abs(np.degrees(np.radians(az_toward) -
                                   np.radians(bear)) % 360)
            if angle > 180: angle = 360 - angle
            along_spd = dist * 1000 / (peak_min * 60)
            proj = abs(np.cos(np.radians(az_toward - bear)))
            true_spd = along_spd * proj if proj > 0.1 else float('nan')
            lines.append(
                f"  {s1}→{s2}: dist={dist:.0f}km  bear={bear:.1f}°  "
                f"angle={angle:.1f}°  along={along_spd:.0f}m/s  "
                f"true≈{true_spd:.0f}m/s")

    interp = interpret_doa_tec_agreement(xcorr_results, tolerance_min=tec_tolerance_min)
    if interp:
        print_and_append_interpretation(lines, interp)

    lines += [
        "",
        "NOTES:",
        textwrap.fill(
            "Primary xcorr peak at lag=0 often reflects correlated "
            "storm-time TEC background not fully removed by polynomial "
            "detrending. Look for secondary peaks near the DOA-predicted "
            "lag for the TID signal.",
            width=66, initial_indent="  ", subsequent_indent="  "),
        "",
        textwrap.fill(
            "Along-baseline speed is much higher than true phase speed "
            "when the baseline is nearly perpendicular to the wave "
            "direction. Use the projected true speed for comparison.",
            width=66, initial_indent="  ", subsequent_indent="  "),
        "",
        "=" * 68,
        f"Generated by fetch_madrigal_tec.py v{VERSION}",
        "psws-drf-tid-tools — https://github.com/N6RFM/psws-drf-tid-tools",
        "=" * 68,
    ]

    pathlib.Path(out_path).write_text("\n".join(lines) + "\n")
    print(f"  Saved: {pathlib.Path(out_path).name}")


# ── Main ──────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Retrieve and analyse Madrigal GPS TEC for TID corroboration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("--config", default=None,
                   help="Path to tid_workflow_event.json or event.json — "
                        "auto-fills --date, --event-start, --event-end, "
                        "and --stations from the event config. "
                        "Explicit CLI args override config values.")
    p.add_argument("--date", default=None, help="Event date YYYY-MM-DD")
    p.add_argument("--event-start", default=None, help="ISO 8601 UTC")
    p.add_argument("--event-end",   default=None, help="ISO 8601 UTC")
    p.add_argument("--stations", nargs="+", default=None,
                   metavar="NAME,LON,LAT",
                   help="Station list e.g. N6RFM,-97.21,32.94")
    p.add_argument("--user-name",        required=True)
    p.add_argument("--user-email",       required=True)
    p.add_argument("--user-affiliation", required=True)
    p.add_argument("--doa-lags", nargs="*", default=[],
                   metavar="S1,S2,LAG_S",
                   help="DOA pairwise lags in seconds e.g. AA6BD,N6RFM,1253")
    p.add_argument("--doa-speed",        type=float, default=None,
                   help="DOA true phase speed in m/s")
    p.add_argument("--doa-azimuth-from", type=float, default=None,
                   help="DOA wave coming FROM azimuth (degrees true)")
    p.add_argument("--tec-tolerance-min", type=float, default=20.0,
                   help="Minutes of DOA-vs-GPS-TEC lag disagreement still "
                        "counted as 'agreeing', for the DOA CROSS-CHECK "
                        "INTERPRETATION verdict (default 20.0 -- loose on "
                        "purpose, GPS TEC is a blunt cross-check)")
    p.add_argument("--output-dir", default=".",
                   help="Output directory (default: current dir)")
    p.add_argument("--lat-box", type=float, default=3.0,
                   help="±lat degrees for station box (default 3.0)")
    p.add_argument("--lon-box", type=float, default=4.0,
                   help="±lon degrees for station box (default 4.0)")
    p.add_argument("--bin-min", type=float, default=1.0,
                   help="Time bin size in minutes (default 1.0)")
    p.add_argument("--min-links", type=int, default=3,
                   help="Minimum GPS links per bin (default 3)")
    return p.parse_args()


def main():
    args = parse_args()

    # Load from --config if provided, filling in any unset arguments
    if args.config:
        import json as _json
        cfg_path = pathlib.Path(args.config)
        with open(cfg_path) as f:
            cfg = _json.load(f)

        if args.event_start is None and "event_start_utc" in cfg:
            args.event_start = cfg["event_start_utc"]
        if args.event_end is None and "event_end_utc" in cfg:
            args.event_end = cfg["event_end_utc"]
        if args.date is None and args.event_start:
            args.date = args.event_start[:10]
        if args.stations is None and "stations" in cfg:
            args.stations = [
                f"{s['name']},{s['lon']},{s['lat']}"
                for s in cfg["stations"]
                if "lat" in s and "lon" in s
            ]

    # Validate required fields (either from --config or CLI)
    missing = [name for name, val in [
        ("--date", args.date),
        ("--event-start", args.event_start),
        ("--event-end", args.event_end),
        ("--stations", args.stations),
    ] if val is None]
    if missing:
        raise SystemExit(
            f"Missing required argument(s): {', '.join(missing)}. "
            f"Provide them on the command line or via --config."
        )

    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ev_start = datetime.datetime.fromisoformat(
        args.event_start.replace('Z', '+00:00'))
    ev_end = datetime.datetime.fromisoformat(
        args.event_end.replace('Z', '+00:00'))
    ev_s_h = ev_start.hour + ev_start.minute/60
    ev_e_h = ev_end.hour + ev_end.minute/60

    # Parse stations
    stations = {}
    for s in args.stations:
        parts = s.split(',')
        if len(parts) != 3:
            print(f"WARNING: ignoring malformed station '{s}'")
            continue
        name, lon, lat = parts[0], float(parts[1]), float(parts[2])
        stations[name] = (lon, lat)

    # Parse DOA lags
    doa_lags = {}
    for lag_str in args.doa_lags:
        parts = lag_str.split(',')
        if len(parts) == 3:
            doa_lags[(parts[0], parts[1])] = float(parts[2])

    print(f"\n{'='*55}")
    print(f"fetch_madrigal_tec.py v{VERSION}")
    print(f"Event: {args.date}  Window: "
          f"{ev_start.strftime('%H:%M')}–{ev_end.strftime('%H:%M')} UTC")
    print(f"Stations: {', '.join(stations)}")
    print(f"{'='*55}\n")

    # Connect and find file
    m = connect_madrigal()
    fname = find_gridded_file(m, args.date)

    # Extract TEC at each station
    print("\nExtracting TEC at station locations...")
    raw = {}
    for name, (lon, lat) in stations.items():
        print(f"  {name} ({lat:.1f}°N, {lon:.1f}°E)...")
        arr = extract_tec(m, fname, name, lon, lat,
                          ev_s_h - 0.1, ev_e_h + 0.5,
                          args.user_name, args.user_email,
                          args.user_affiliation,
                          args.lat_box, args.lon_box)
        if arr is not None and len(arr) > 0:
            raw[name] = arr
            print(f"    {len(arr)} GPS link records")
        else:
            print(f"    No data")

    # Bin and detrend
    print("\nBinning and detrending...")
    binned = {}
    det = {}
    for name, arr in raw.items():
        t, tec, n = bin_tec(arr, ev_s_h, ev_e_h,
                             args.bin_min, args.min_links)
        if len(t) > 5:
            binned[name] = (t, tec, n)
            d, trend = detrend_tec(t, tec)
            det[name] = (t, d)
            print(f"  {name}: {len(t)} bins  σ={np.std(d):.3f} TECU")

    if not det:
        print("ERROR: No usable TEC data extracted. Check station boxes and date.")
        sys.exit(1)

    # Plots
    print("\nGenerating plots...")
    plot_raw(binned, ev_s_h, ev_e_h, args.date,
             out / "madrigal_tec_raw.png")

    names = list(det.keys())
    primary = (names[0], names[1]) if len(names) >= 2 else (names[0], names[0])
    plot_detrended(det, ev_s_h, ev_e_h, args.date,
                   primary, doa_lags,
                   out / "madrigal_tec_detrended.png")

    xcorr_results = plot_xcorr_all(
        det, ev_s_h, ev_e_h, doa_lags, args.date,
        out / "madrigal_tec_xcorr.png")

    # Report
    print("\nWriting report...")
    write_report(
        out / "madrigal_tec_report.txt",
        args.date, ev_start, ev_end,
        stations, binned, det, xcorr_results,
        doa_lags, args.doa_speed, args.doa_azimuth_from, fname,
        tec_tolerance_min=args.tec_tolerance_min)

    print(f"\n{'='*55}")
    print(f"Done. Outputs in: {out.resolve()}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
