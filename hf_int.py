#!/usr/bin/env python3
"""
hf_int.py — HF Interferometry method for TID detection from Doppler data
Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)

Adapts the HF-Int method (Altadill et al., 2020, J. Space Weather Space Clim.)
from ionosonde foF2/MUF(3000)F2 to HF Doppler shift time series extracted
by tid_spline_click.py or tid_spect_click.py.

The original HF-Int method uses three steps:
  1. Detrend  — remove daily trend (here: remove polynomial or running mean)
  2. Spectral — Lomb-Scargle periodogram to find dominant TID period
  3. Xcorr    — cross-correlate station pairs to get time lags, then
                least-squares solve slowness vector for speed + azimuth

Reference:
  Altadill D, Segarra A, Blanch E, Juan JM, Paznukhov VV, et al. (2020)
  A method for real-time identification and tracking of traveling
  ionospheric disturbances using ionosonde data: first results.
  J. Space Weather Space Clim. 10, 2.
  https://doi.org/10.1051/swsc/2019042

Usage:
  python3 hf_int.py \\
      --event-dir examples/tid_event_20260119 \\
      --stations N6RFM,-100.93,36.87 AA6BD,-94.70,38.29 \\
                 W7LUX,-108.50,37.94 AC0G_ND,-100.94,43.78 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --output-dir ./hf_int_results

  # With known DOA for comparison:
  python3 hf_int.py \\
      --event-dir examples/tid_event_20260119 \\
      --stations N6RFM,-100.93,36.87 AA6BD,-94.70,38.29 \\
                 W7LUX,-108.50,37.94 AC0G_ND,-100.94,43.78 \\
      --event-start 2026-01-19T00:00:00Z \\
      --event-end   2026-01-19T01:15:00Z \\
      --ref-station AA6BD \\
      --doa-speed 239 --doa-azimuth-from 30 \\
      --output-dir ./hf_int_results

Input CSV format (one file per station, named {callsign}_spline_tid.csv):
  timestamp_utc,doppler_hz,snr_db
  2026-01-19 00:00:00+00:00,-0.195,50.0
  ...

Station coordinates should be IPP midpoints (between station and WWV).

Outputs:
  hf_int_periodogram.png   Lomb-Scargle periodograms for all stations
  hf_int_detrended.png     Detrended Doppler time series
  hf_int_xcorr.png         All pairwise cross-correlations
  hf_int_result.png        Velocity vector map + result summary
  hf_int_report.txt        Full text report

CRITICAL LIMITATION — SHORT WINDOW DATASETS:
  The HF-Int method as published requires a minimum of 3 full TID cycles
  in the analysis window. Altadill et al. use a 6-hour rolling window with
  24-hour background detrending. With typical PSWS/HamSCI Doppler datasets
  of 1-3 hours, the method is unreliable:

  - With <3 cycles, the Lomb-Scargle period estimate is unstable
  - The xcorr peak can land on the wrong half-cycle (180° direction flip)
  - The 24-hour detrending cannot be applied to short event windows

  For the Jan 2026 event (75-min window, ~2 cycles at 39 min):
  - HF-Int gave 267 m/s from 176° (SSW) — opposite to DOA result (30° NNE)
  - This is the expected half-cycle alias artifact, NOT a physical result
  - tid_doa.py is better suited to short datasets because the spline
    extraction isolates the TID phase directly from the spectrogram

  The May 2024 dataset (190-min window, 2.5 cycles) is a better test case
  but still borderline. This tool is provided for methodological comparison
  and longer future datasets only.

  See FINDINGS Entry 53 for full discussion.

Requirements:
  pip install numpy matplotlib scipy astropy

Created by N6RFM with help from Claude AI, adapted from Altadill et al. (2020).
Version: 1.0.0
License: MIT (do whatever you want, no warranty).
"""

import argparse
import datetime
import math
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from scipy.optimize import least_squares

try:
    from astropy.timeseries import LombScargle
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

VERSION = "1.0.0"
REF_ALT_KM = 300.0   # reference ionospheric altitude for IPP projection (km)
R_EARTH_KM = 6371.0


# ── Geometry ──────────────────────────────────────────────────────────────

def gc_dist_km(lon1, lat1, lon2, lat2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
    return 2*R_EARTH_KM*np.arcsin(np.sqrt(a))


def bearing_deg(lon1, lat1, lon2, lat2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlam = np.radians(lon2 - lon1)
    x = np.sin(dlam)*np.cos(phi2)
    y = np.cos(phi1)*np.sin(phi2) - np.sin(phi1)*np.cos(phi2)*np.cos(dlam)
    return np.degrees(np.arctan2(x, y)) % 360


def position_vector_km(lon1, lat1, lon2, lat2):
    """
    East (x) and North (y) components of displacement from station 1 to 2.
    Uses flat-Earth approximation valid for baselines < 2000 km.
    Projected at reference ionospheric altitude.
    """
    dist = gc_dist_km(lon1, lat1, lon2, lat2)
    bear = bearing_deg(lon1, lat1, lon2, lat2)
    dx = dist * np.sin(np.radians(bear))   # East
    dy = dist * np.cos(np.radians(bear))   # North
    return dx, dy


# ── Data loading ──────────────────────────────────────────────────────────

def load_station(csv_path, ev_start, ev_end):
    """Load spline CSV, return (t_min, doppler_hz) within event window."""
    rows = []
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('timestamp') or not line:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            try:
                ts = datetime.datetime.fromisoformat(
                    parts[0].replace('Z', '+00:00'))
                val = float(parts[1])
                if ev_start <= ts <= ev_end:
                    rows.append((ts, val))
            except:
                pass
    if not rows:
        return None, None
    rows.sort(key=lambda x: x[0])
    t0 = rows[0][0]
    t_min = np.array([(r[0] - t0).total_seconds()/60 for r in rows])
    dop   = np.array([r[1] for r in rows])
    return t_min, dop


# ── Step 1: Detrending ────────────────────────────────────────────────────

def detrend(t, y, method='poly', poly_order=2, hp_period_min=None):
    """
    Remove slow background trend.
    method='poly': subtract polynomial fit (Altadill et al. approach)
    method='hp':   high-pass filter above hp_period_min (paper's preferred)
    method='diff': first-difference (aggressive, good for short windows)
    """
    if method == 'poly':
        if len(t) <= poly_order:
            return y - y.mean(), np.full_like(y, y.mean())
        coeffs = np.polyfit(t, y, poly_order)
        trend = np.polyval(coeffs, t)
        return y - trend, trend

    elif method == 'hp' and hp_period_min:
        # High-pass: subtract running mean with window = hp_period_min
        w = int(hp_period_min / (t[1]-t[0])) if len(t) > 1 else 1
        w = max(1, min(w, len(y)-1))
        trend = np.convolve(y, np.ones(w)/w, mode='same')
        return y - trend, trend

    elif method == 'diff':
        det = np.diff(y, prepend=y[0])
        return det, y - det

    return y - y.mean(), np.full_like(y, y.mean())


# ── Step 2: Lomb-Scargle periodogram ─────────────────────────────────────

def lomb_scargle_period(t_min, y, period_range=(38, 160),
                        false_alarm_level=0.025):
    """
    Compute Lomb-Scargle periodogram and find dominant TID period.
    Period range 38-160 min as in Altadill et al. (2020).
    Returns (periods, power, peak_period_min, confidence_ok).
    """
    if HAS_ASTROPY:
        ls = LombScargle(t_min, y)
        freq_min = 1.0 / period_range[1]
        freq_max = 1.0 / period_range[0]
        freqs = np.linspace(freq_min, freq_max, 500)
        power = ls.power(freqs)
        periods = 1.0 / freqs
        fap = ls.false_alarm_probability(power.max())
        confidence_ok = fap < false_alarm_level
        peak_period = periods[np.argmax(power)]
    else:
        # Scipy fallback
        freqs = np.linspace(1/period_range[1], 1/period_range[0], 500)
        angular_freqs = 2 * np.pi * freqs
        power = signal.lombscargle(t_min.astype(float),
                                   (y - y.mean()).astype(float),
                                   angular_freqs, normalize=True)
        periods = 1.0 / freqs
        confidence_ok = power.max() > 0.5  # approximate
        peak_period = periods[np.argmax(power)]

    return periods, power, peak_period, confidence_ok


def periods_coherent(periods, threshold=0.30):
    """
    Check if a list of periods are mutually coherent
    (differ by less than 30%, as in Altadill et al.).
    Returns (coherent, mean_period).
    """
    if len(periods) < 2:
        return True, periods[0] if periods else 0
    med = np.median(periods)
    diffs = [abs(p - med)/med for p in periods]
    return all(d < threshold for d in diffs), float(np.mean(periods))


# ── Step 3: Cross-correlation and slowness inversion ─────────────────────

def xcorr_lag(t1, d1, t2, d2, max_lag_min=60, ref_len_min=360):
    """
    Cross-correlate two detrended time series, search within ±max_lag_min.
    Returns (lags_min, xcorr_normalized, peak_lag_min, ccm).
    Mirrors Altadill et al.: search within ±60 min, discard if lag=±60.
    """
    # Interpolate to common 1-min grid
    dt = max(t1[1]-t1[0], t2[1]-t2[0]) if len(t1)>1 and len(t2)>1 else 1.0
    t_common = np.arange(min(t1[0], t2[0]),
                          max(t1[-1], t2[-1]) + dt, dt)
    y1 = np.interp(t_common, t1, d1)
    y2 = np.interp(t_common, t2, d2)

    xc = np.correlate(y1 - y1.mean(), y2 - y2.mean(), mode='full')
    denom = np.std(y1) * np.std(y2) * len(y1)
    if denom > 1e-10:
        xc /= denom
    lags = (np.arange(len(xc)) - len(y1) + 1) * dt

    # Restrict to ±max_lag_min
    mask = np.abs(lags) <= max_lag_min
    lags_r = lags[mask]
    xc_r   = xc[mask]
    peak_idx = np.argmax(xc_r)
    peak_lag = lags_r[peak_idx]
    ccm      = xc_r[peak_idx]

    return lags_r, xc_r, peak_lag, ccm


def solve_slowness(dx_km, dy_km, dt_s, weights=None):
    """
    Least-squares solve for slowness vector (sx, sy) in s/km.
    Equation: dt_i = sx*dx_i + sy*dy_i  (Altadill eq. 3-4)
    Returns (sx, sy, speed_m_s, azimuth_toward_deg, residuals).
    Azimuth is direction wave is moving TOWARD (clockwise from N).
    """
    n = len(dx_km)
    if n < 2:
        return None

    A = np.column_stack([dx_km, dy_km])
    b = np.array(dt_s)

    if weights is not None:
        W = np.diag(weights)
        A = W @ A
        b = W @ b

    result = np.linalg.lstsq(A, b, rcond=None)
    sx, sy = result[0]  # s/km
    residuals = result[1]

    # Speed from slowness magnitude (convert km→m)
    s_mag = np.sqrt(sx**2 + sy**2)  # s/km
    if s_mag < 1e-10:
        return None

    speed_m_s = 1000.0 / s_mag  # m/s

    # Azimuth: direction wave moves TOWARD
    # sx = East component, sy = North component of slowness
    az_toward = np.degrees(np.arctan2(sx, sy)) % 360
    az_from   = (az_toward + 180) % 360

    return sx, sy, speed_m_s, az_toward, az_from, float(residuals[0]) if len(residuals) else 0.0


# ── Plotting ──────────────────────────────────────────────────────────────

def plot_periodograms(periods_data, ev_start, out_path):
    colors = ['blue','red','green','purple','orange','brown']
    n = len(periods_data)
    fig, axes = plt.subplots(n, 1, figsize=(12, 3*n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, (name, (periods, power, peak, ok)), col in \
            zip(axes, periods_data.items(), colors):
        ax.plot(periods, power, color=col, lw=1.2)
        ax.axvline(peak, color='red', lw=1.5, ls='--',
                   label=f'Peak: {peak:.1f} min')
        ax.axvspan(38, 160, alpha=0.05, color='gray')
        ax.set_ylabel('Power', fontsize=8)
        ax.set_title(f'{name}  peak={peak:.1f} min  '
                     f'{"✓ significant" if ok else "✗ not significant"}',
                     fontsize=9, color='green' if ok else 'red')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Period (min)')
    plt.suptitle(f'Lomb-Scargle Periodograms — TID period range 38–160 min\n'
                 f'{ev_start.strftime("%Y-%m-%d")}  '
                 f'(Altadill et al. 2020 method)', fontsize=10)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_detrended(det_data, ev_start, ev_end, t0, out_path):
    colors = ['blue','red','green','purple','orange','brown']
    fig, ax = plt.subplots(figsize=(13, 5))

    for (name, (t, d)), col in zip(det_data.items(), colors):
        t_abs = [t0 + datetime.timedelta(minutes=float(ti)) for ti in t]
        t_h = [ti.hour + ti.minute/60 for ti in t_abs]
        ax.plot(t_h, d, '-', lw=1.2, color=col, label=f'{name}', alpha=0.8)

    ev_s = ev_start.hour + ev_start.minute/60
    ev_e = ev_end.hour   + ev_end.minute/60
    ax.axvspan(ev_s, ev_e, alpha=0.15, color='green', label='Event window')
    ax.axhline(0, color='gray', lw=0.8)
    ax.set_xlabel(f'Hours UTC on {ev_start.strftime("%Y-%m-%d")}')
    ax.set_ylabel('Detrended Doppler (Hz)')
    ax.set_title('Detrended HF Doppler — TID signal\n'
                 '2nd-order polynomial trend removed (Altadill et al. method)')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_xcorr(xcorr_data, ref_station, out_path):
    n = len(xcorr_data)
    ncols = 2
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols,
                              figsize=(14, 4*nrows + 1))
    axes = np.array(axes).reshape(-1)

    for ax, (pair, (lags, xc, lag, ccm, doa_lag)) in \
            zip(axes, xcorr_data.items()):
        s1, s2 = pair
        ax.plot(lags, xc, 'b-', lw=1)
        ax.axvline(lag, color='red', lw=1.5, ls='--',
                   label=f'Peak lag={lag:.0f}m  CCM={ccm:.2f}')
        if doa_lag is not None:
            ax.axvline(doa_lag/60, color='orange', lw=1.5, ls='--',
                       label=f'DOA pred={doa_lag/60:.1f}m')
        ax.axvline(0, color='gray', lw=0.5)
        ax.set_xlim(-60, 60)
        ax.set_title(f'{s1} → {s2}', fontsize=9)
        ax.set_xlabel('Lag (min)', fontsize=7)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    for ax in axes[n:]:
        ax.axis('off')

    plt.suptitle(f'HF-Int Cross-correlations  (ref: {ref_station})\n'
                 f'Red=peak lag  Orange=DOA prediction  '
                 f'Discard if |lag|=60 or CCM<0.5',
                 fontsize=10)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")


def plot_result(stations, slowness_result, ev_start, out_path,
                doa_speed=None, doa_az_from=None):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: velocity vector map
    ax = axes[0]
    lons = [v[0] for v in stations.values()]
    lats = [v[1] for v in stations.values()]
    ax.scatter(lons, lats, s=80, zorder=5, color='blue')
    for name, (lon, lat) in stations.items():
        ax.annotate(name, (lon, lat), textcoords='offset points',
                    xytext=(5, 5), fontsize=8)

    if slowness_result:
        sx, sy, speed, az_toward, az_from, _ = slowness_result
        # Draw arrow showing wave direction (toward)
        cx = np.mean(lons)
        cy = np.mean(lats)
        scale = 8.0 / speed if speed > 0 else 0
        dx = np.sin(np.radians(az_toward)) * scale
        dy = np.cos(np.radians(az_toward)) * scale
        ax.annotate('', xy=(cx+dx, cy+dy), xytext=(cx, cy),
                    arrowprops=dict(arrowstyle='->', color='red', lw=2))
        ax.set_title(f'HF-Int Result\n'
                     f'Speed: {speed:.0f} m/s  '
                     f'From: {az_from:.0f}°  Toward: {az_toward:.0f}°',
                     fontsize=10)

        if doa_speed and doa_az_from:
            doa_toward = (doa_az_from + 180) % 360
            scale2 = 8.0 / doa_speed
            dx2 = np.sin(np.radians(doa_toward)) * scale2
            dy2 = np.cos(np.radians(doa_toward)) * scale2
            ax.annotate('', xy=(cx+dx2, cy+dy2), xytext=(cx, cy),
                        arrowprops=dict(arrowstyle='->',
                                        color='orange', lw=2, ls='dashed'))
            ax.legend([plt.Line2D([0],[0],color='red',lw=2),
                       plt.Line2D([0],[0],color='orange',lw=2,ls='dashed')],
                      ['HF-Int', f'DOA spline ({doa_speed} m/s)'],
                      fontsize=8, loc='lower right')
    else:
        ax.set_title('HF-Int Result\nInsufficient coherent stations',
                     fontsize=10, color='red')

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.grid(True, alpha=0.3)

    # Right: summary table
    ax2 = axes[1]
    ax2.axis('off')
    summary = [
        ['Parameter', 'HF-Int', 'DOA Spline'],
        ['Speed (m/s)',
         f'{slowness_result[2]:.0f}' if slowness_result else '---',
         f'{doa_speed}' if doa_speed else '---'],
        ['From azimuth (°)',
         f'{slowness_result[4]:.0f}' if slowness_result else '---',
         f'{doa_az_from}' if doa_az_from else '---'],
        ['Toward azimuth (°)',
         f'{slowness_result[3]:.0f}' if slowness_result else '---',
         f'{(doa_az_from+180)%360}' if doa_az_from else '---'],
        ['Method', 'Lomb-Scargle + xcorr', 'Spline + xcorr'],
        ['Reference', 'Altadill et al. 2020', 'tid_doa.py'],
    ]
    tbl = ax2.table(cellText=summary[1:], colLabels=summary[0],
                    cellLoc='center', loc='center',
                    bbox=[0, 0.2, 1, 0.7])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    ax2.set_title(f'Method comparison\n{ev_start.strftime("%Y-%m-%d")}',
                  fontsize=10)

    plt.suptitle('HF-Int TID Detection (Altadill et al. 2020 adapted for HF Doppler)',
                 fontsize=11)
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=130)
    plt.close()
    print(f"  Saved: {out_path.name}")


# ── Report ────────────────────────────────────────────────────────────────

def write_report(out_path, ev_start, ev_end, stations, ref_station,
                 periods_data, xcorr_data, slowness_result,
                 doa_speed, doa_az_from):
    lines = [
        "=" * 68,
        "HF-INT TID DETECTION REPORT",
        f"hf_int.py v{VERSION}  —  Altadill et al. (2020) adapted for HF Doppler",
        "=" * 68,
        f"Event:       {ev_start.strftime('%Y-%m-%d')}",
        f"Window:      {ev_start.strftime('%H:%M')}–{ev_end.strftime('%H:%M')} UTC",
        f"Reference:   {ref_station}",
        "",
        "STATIONS (IPP midpoints):",
    ]
    for name, (lon, lat) in stations.items():
        lines.append(f"  {name:10s}  {lat:.2f}°N  {lon:.2f}°E")

    lines += ["", "STEP 1: DETRENDING",
              "  Method: 2nd-order polynomial removal",
              "  (Paper uses DFT upsampling + high-pass filter at T>3h)",
              ""]

    lines += ["STEP 2: LOMB-SCARGLE PERIODOGRAMS",
              "  TID period range: 38–160 min (Altadill et al.)",
              "  Coherence threshold: periods within 30% of each other",
              "  Significance: false alarm probability < 0.025",
              ""]
    sig_periods = []
    for name, (periods, power, peak, ok) in periods_data.items():
        lines.append(f"  {name:10s}  peak={peak:.1f} min  "
                     f"{'significant ✓' if ok else 'not significant ✗'}")
        if ok:
            sig_periods.append(peak)

    if sig_periods:
        coherent, mean_period = periods_coherent(sig_periods)
        lines += [
            f"",
            f"  Significant stations: {len(sig_periods)}/{len(periods_data)}",
            f"  Periods coherent (within 30%): {'YES ✓' if coherent else 'NO ✗'}",
            f"  Mean TID period: {mean_period:.1f} min",
        ]

    lines += ["", "STEP 3: CROSS-CORRELATION (ref: " + ref_station + ")",
              "  Max lag search: ±60 min (Altadill et al.)",
              "  CCM threshold: 0.5 (discard if below)",
              "  Discard if |lag| = 60 min (ambiguous)",
              ""]
    lines.append(f"  {'Pair':20s}  {'Lag(min)':>10s}  {'CCM':>6s}  "
                 f"{'DOA pred(min)':>14s}  {'Used?':>6s}")
    lines.append("  " + "-"*65)

    used_pairs = []
    for (s1, s2), (lags, xc, lag, ccm, doa_lag) in xcorr_data.items():
        used = abs(lag) < 60 and ccm >= 0.5
        if used:
            used_pairs.append((s1, s2, lag, ccm))
        doa_str = f"{doa_lag/60:.1f}" if doa_lag else "---"
        lines.append(f"  {s1}→{s2:10s}  {lag:>10.0f}  {ccm:>6.2f}  "
                     f"{doa_str:>14s}  {'✓' if used else '✗ discard':>6s}")

    lines += ["", "SLOWNESS VECTOR INVERSION (Altadill eq. 3-5)",
              "  Δti = sx·Δxi + sy·Δyi  (least squares)",
              ""]

    if slowness_result:
        sx, sy, speed, az_toward, az_from, residual = slowness_result
        lines += [
            f"  sx (East):   {sx*1000:.4f} s/m  ({sx:.6f} s/km)",
            f"  sy (North):  {sy*1000:.4f} s/m  ({sy:.6f} s/km)",
            f"  Speed:       {speed:.0f} m/s",
            f"  Toward:      {az_toward:.0f}°",
            f"  From:        {az_from:.0f}°",
            f"  Residual:    {residual:.4f}",
        ]
        if sig_periods and periods_coherent(sig_periods)[0]:
            wavelength = speed * periods_coherent(sig_periods)[1] * 60
            lines.append(f"  Wavelength:  {wavelength/1000:.0f} km  "
                         f"({'LSTID ✓' if wavelength > 1000000 else 'check'})")
    else:
        lines += ["  INSUFFICIENT DATA for inversion",
                  "  Need ≥3 stations with CCM>0.5 and |lag|<60 min"]

    if doa_speed and doa_az_from and slowness_result:
        lines += [
            "",
            "COMPARISON WITH DOA SPLINE RESULT:",
            f"  HF-Int speed:     {slowness_result[2]:.0f} m/s  "
            f"from {slowness_result[4]:.0f}°",
            f"  DOA spline speed: {doa_speed} m/s  "
            f"from {doa_az_from}°",
            f"  Speed difference: "
            f"{abs(slowness_result[2]-doa_speed):.0f} m/s  "
            f"({abs(slowness_result[2]-doa_speed)/doa_speed*100:.0f}%)",
            f"  Direction diff:   "
            f"{abs(slowness_result[4]-doa_az_from):.0f}°",
        ]

    lines += [
        "",
        "NOTES:",
        "  This implementation adapts Altadill et al. (2020) from",
        "  ionosonde foF2/MUF(3000)F2 to HF Doppler shift time series.",
        "  Key differences:",
        "  - Input: Doppler Hz (vs foF2 MHz)",
        "  - Window: event window only (vs 6-hour rolling)",
        "  - Stations: 4 US PSWS (vs 10-14 European Digisondes)",
        "  - Spacing: 600-1200 km (vs ~500 km)",
        "",
        "  Reference:",
        "  Altadill D et al. (2020) J. Space Weather Space Clim. 10, 2",
        "  https://doi.org/10.1051/swsc/2019042",
        "",
        "=" * 68,
        f"Generated by hf_int.py v{VERSION}",
        "psws-drf-tid-tools — https://github.com/N6RFM/psws-drf-tid-tools",
        "=" * 68,
    ]

    pathlib.Path(out_path).write_text("\n".join(lines) + "\n")
    print(f"  Saved: {pathlib.Path(out_path).name}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="HF-Int TID detection from HF Doppler (Altadill et al. 2020)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("--event-dir",    required=True,
                   help="Directory containing *_spline_tid.csv files")
    p.add_argument("--stations",     required=True, nargs="+",
                   metavar="NAME,LON,LAT",
                   help="Station IPP coords e.g. N6RFM,-100.93,36.87")
    p.add_argument("--event-start",  required=True, help="ISO 8601 UTC")
    p.add_argument("--event-end",    required=True, help="ISO 8601 UTC")
    p.add_argument("--ref-station",  default=None,
                   help="Reference station (default: first station)")
    p.add_argument("--doa-speed",    type=float, default=None,
                   help="DOA spline speed m/s for comparison")
    p.add_argument("--doa-azimuth-from", type=float, default=None,
                   help="DOA wave coming FROM azimuth for comparison")
    p.add_argument("--detrend-method", default="poly",
                   choices=["poly","hp","diff"],
                   help="Detrending method (default: poly)")
    p.add_argument("--max-lag-min",  type=float, default=60,
                   help="Max xcorr lag in minutes (default: 60)")
    p.add_argument("--ccm-threshold", type=float, default=0.5,
                   help="Min CCM to use a station (default: 0.5)")
    p.add_argument("--output-dir",   default=".",
                   help="Output directory")
    args = p.parse_args()

    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ev_dir = pathlib.Path(args.event_dir)

    ev_start = datetime.datetime.fromisoformat(
        args.event_start.replace('Z','+00:00'))
    ev_end   = datetime.datetime.fromisoformat(
        args.event_end.replace('Z','+00:00'))

    # Parse stations
    stations = {}
    for s in args.stations:
        name, lon, lat = s.split(',')
        stations[name] = (float(lon), float(lat))

    ref = args.ref_station or list(stations.keys())[0]
    if ref not in stations:
        print(f"WARNING: ref station {ref} not in station list, "
              f"using {list(stations.keys())[0]}")
        ref = list(stations.keys())[0]

    print(f"\n{'='*55}")
    print(f"hf_int.py v{VERSION}")
    print(f"Event: {args.event_start[:10]}  "
          f"Window: {ev_start.strftime('%H:%M')}–{ev_end.strftime('%H:%M')} UTC")
    print(f"Reference: {ref}")
    print(f"{'='*55}\n")

    # Load all station data
    print("Loading station data...")
    raw = {}
    t0 = ev_start
    for name in stations:
        csv_files = list(ev_dir.glob(f"{name.lower()}_spline_tid.csv")) + \
                    list(ev_dir.glob(f"{name}_spline_tid.csv"))
        if not csv_files:
            print(f"  {name}: no CSV found in {ev_dir}")
            continue
        t_min, dop = load_station(csv_files[0], ev_start, ev_end)
        if t_min is None or len(t_min) < 10:
            print(f"  {name}: insufficient data ({len(t_min) if t_min is not None else 0} points)")
            continue
        raw[name] = (t_min, dop)
        print(f"  {name}: {len(t_min)} points")

    if len(raw) < 3:
        print(f"\nERROR: Need ≥3 stations, got {len(raw)}")
        sys.exit(1)

    # Check window length vs expected period
    ev_dur_min = (ev_end - ev_start).total_seconds() / 60
    print(f"\nWindow duration: {ev_dur_min:.0f} min")
    print(f"HF-Int requires: ≥3 full TID cycles in window")
    print(f"Typical LSTID period: 50-90 min → need ≥150-270 min minimum")
    if ev_dur_min < 150:
        print(f"\n  WARNING: Window ({ev_dur_min:.0f} min) is likely too short for")
        print(f"  reliable HF-Int results. With <3 cycles, the xcorr peak may")
        print(f"  land on the wrong half-cycle producing a 180° direction flip.")
        print(f"  Results should be treated as unreliable.")
        print(f"  Use tid_doa.py for short datasets — it is better suited.")
    elif ev_dur_min < 270:
        print(f"  CAUTION: Window ({ev_dur_min:.0f} min) is marginal for HF-Int.")
        print(f"  Results may have direction ambiguity. Verify with peak succession.")

    # Step 1: Detrend
    print("\nStep 1: Detrending...")
    det = {}
    for name, (t, y) in raw.items():
        d, trend = detrend(t, y, method=args.detrend_method)
        det[name] = (t, d)
        print(f"  {name}: σ={np.std(d):.4f} Hz")

    plot_detrended(det, ev_start, ev_end, t0,
                   out / "hf_int_detrended.png")

    # Step 2: Lomb-Scargle
    print("\nStep 2: Lomb-Scargle periodograms...")
    periods_data = {}
    for name, (t, d) in det.items():
        periods, power, peak, ok = lomb_scargle_period(t, d)
        periods_data[name] = (periods, power, peak, ok)
        print(f"  {name}: peak={peak:.1f} min  "
              f"{'significant ✓' if ok else 'not significant ✗'}")

    plot_periodograms(periods_data, ev_start,
                      out / "hf_int_periodogram.png")

    sig_periods = [v[2] for v in periods_data.values() if v[3]]
    if sig_periods:
        coherent, mean_T = periods_coherent(sig_periods)
        print(f"\n  Mean TID period: {mean_T:.1f} min  "
              f"Coherent: {'✓' if coherent else '✗'}")
    else:
        print("\n  No significant periods detected")
        mean_T = None

    # Step 3: Cross-correlation
    print(f"\nStep 3: Cross-correlation (ref: {ref})...")
    xcorr_data = {}
    doa_lags = {}
    if args.doa_speed and args.doa_azimuth_from:
        az_toward = (args.doa_azimuth_from + 180) % 360
        for name, (lon, lat) in stations.items():
            if name == ref:
                continue
            rlon, rlat = stations[ref]
            dx, dy = position_vector_km(rlon, rlat, lon, lat)
            proj = (np.sin(np.radians(az_toward))*dx +
                    np.cos(np.radians(az_toward))*dy)
            doa_lags[(ref, name)] = proj * 1000 / args.doa_speed

    for name, (t2, d2) in det.items():
        if name == ref:
            continue
        t1, d1 = det[ref]
        lags, xc, lag, ccm = xcorr_lag(t1, d1, t2, d2,
                                         args.max_lag_min)
        doa_l = doa_lags.get((ref, name), None)
        xcorr_data[(ref, name)] = (lags, xc, lag, ccm, doa_l)
        used = abs(lag) < args.max_lag_min and ccm >= args.ccm_threshold
        print(f"  {ref}→{name}: lag={lag:.0f} min  CCM={ccm:.2f}  "
              f"{'✓ used' if used else '✗ discarded'}")

    plot_xcorr(xcorr_data, ref, out / "hf_int_xcorr.png")

    # Slowness inversion
    print("\nSlowness vector inversion...")
    used_pairs = [(s2, lag, ccm)
                  for (s1,s2),(lags,xc,lag,ccm,_) in xcorr_data.items()
                  if abs(lag) < args.max_lag_min and
                  ccm >= args.ccm_threshold]

    slowness_result = None
    if len(used_pairs) >= 2:
        rlon, rlat = stations[ref]
        dx_list, dy_list, dt_list, w_list = [], [], [], []
        for s2, lag, ccm in used_pairs:
            lon2, lat2 = stations[s2]
            dx, dy = position_vector_km(rlon, rlat, lon2, lat2)
            dx_list.append(dx)
            dy_list.append(dy)
            dt_list.append(lag * 60)  # convert min→s
            w_list.append(ccm)

        slowness_result = solve_slowness(
            np.array(dx_list), np.array(dy_list),
            np.array(dt_list), np.array(w_list))

        if slowness_result:
            sx, sy, speed, az_toward, az_from, res = slowness_result
            print(f"  Speed:    {speed:.0f} m/s")
            print(f"  From:     {az_from:.0f}°")
            print(f"  Toward:   {az_toward:.0f}°")
            if args.doa_speed:
                print(f"\n  vs DOA spline: {args.doa_speed} m/s "
                      f"from {args.doa_azimuth_from}°")
                print(f"  Speed diff:  "
                      f"{abs(speed-args.doa_speed):.0f} m/s "
                      f"({abs(speed-args.doa_speed)/args.doa_speed*100:.0f}%)")
                print(f"  Direction diff: "
                      f"{abs(az_from-args.doa_azimuth_from):.0f}°")
    else:
        print(f"  Only {len(used_pairs)} usable pairs — "
              f"need ≥2 for inversion")

    plot_result(stations, slowness_result, ev_start,
                out / "hf_int_result.png",
                args.doa_speed, args.doa_azimuth_from)

    write_report(out / "hf_int_report.txt",
                 ev_start, ev_end, stations, ref,
                 periods_data, xcorr_data, slowness_result,
                 args.doa_speed, args.doa_azimuth_from)

    print(f"\nAll outputs in: {out.resolve()}")


if __name__ == "__main__":
    main()
