r"""
tid_doa.py — multi-station TID direction-of-arrival analyzer


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.2.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.2.0  Added RESULT DIAGNOSTICS: five observational checks
          (geometry conditioning, plane-wave residual,
          pairwise correlation spread, triangle closure,
          speed range) shown after the result; flag-don't-
          fail, default on, --no-diagnostics to suppress.
          Added a per-run log under ./runs/. No change to
          any computed value.
  v1.1.0  Default cross-correlation now operates on raw (mean-subtracted)
          Doppler instead of bandpass-filtered. Bandpass was producing
          multi-lobed correlation functions causing the lag-finder to lock
          onto wrong secondary peaks. New config flag use_bandpass restores
          the previous behavior if needed. max_lag_seconds is now auto-
          computed from the largest baseline divided by min_expected_speed.
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
Given Doppler-vs-time CSVs from 3 or more HamSCI Grape DRF stations recording
the same WWV carrier during the same TID event, this tool computes:

  - The TID's true horizontal phase speed (m/s)
  - The TID's azimuth -- the direction the wave is moving, in degrees
    true, plus its complement (where the wave is coming from)
  - Pairwise cross-correlation lags and correlations for every station
    pair (diagnostic)

This is the "real" direction-of-arrival analysis. Unlike tid_pair.py
(which only measures along-baseline propagation between two stations),
the slowness-vector inversion here resolves the full 2D wave velocity
vector when the array has >= 3 non-collinear stations.

METHOD
======
The full processing pipeline:

  1. Load each station's Doppler CSV; clip to the event window; resample
     to a common cadence.
  2. Compute each station's WWV-path great-circle midpoint -- this is
     the approximate ionospheric reflection point at F-region heights
     (~250 km altitude) for single-hop 10 MHz propagation.
  3. Project all midpoints onto a local east-north tangent plane
     centered on the array centroid.
  4. Bandpass-filter each Doppler series to a chosen TID period band
     (3rd-order Butterworth, filtfilt for zero phase delay).
  5. For every pair (i, j) of stations, cross-correlate the filtered
     traces to find the time lag tau_ij at which the signals best align,
     restricted to |tau_ij| < max_lag_seconds.
  6. Solve the overdetermined linear system

        tau_ij = s . (r_j - r_i)    for all pairs

     for the 2D slowness vector s = (sx, sy) in s/m, using
     numpy.linalg.lstsq.
  7. Convert to azimuth and speed:
        speed = 1 / |s|
        azimuth (heading toward) = atan2(sx, sy), wrapped to [0, 360)
        azimuth (coming from)    = azimuth_to + 180 (mod 360)

The least-squares fit minimizes the residuals across all N*(N-1)/2 pairs
simultaneously, so 3+ stations gives an over-determined system and the
result is robust to any single bad lag.

CONFIG FORMAT
=============
The event is described by a JSON config file. Example:

    {
      "event_start_utc": "2026-01-19T00:00:00Z",
      "event_end_utc":   "2026-01-19T01:15:00Z",
      "resample_seconds": 10,
      "use_bandpass": false,
      "min_expected_speed_m_s": 100,
      "stations": [
        {"name": "N6RFM",   "file": "n6rfm.csv",      "method": "fft",      "lat": 32.94, "lon":  -97.21},
        {"name": "AA6BD",   "file": "aa6bd.csv",      "method": "fft",      "lat": 35.06, "lon":  -85.13},
        {"name": "W7LUX",   "file": "w7lux.csv",      "method": "fft",      "lat": 35.10, "lon": -111.71},
        {"name": "AC0G_ND", "file": "ac0g_nd_autocorr.csv", "method": "autocorr", "lat": 46.88, "lon":  -96.83}
      ]
    }

Optional advanced fields:
    "max_lag_seconds":     manually override the auto-computed lag window
    "period_band_seconds": only used if use_bandpass=true

Run `python tid_doa.py` with no arguments to write an example template
to example_event.json.

PARAMETER GUIDANCE
==================
  event_start_utc / event_end_utc
      Bracket the TID event. Window should contain at least 1-2 full
      wave cycles. For an 80-min wave aim for >= 90-180 min of data.

  resample_seconds
      Common cadence to resample all stations to. 10 s is plenty for
      TID work (TIDs evolve over minutes). Should match the cadence
      you used in drf_to_doppler.py.

  use_bandpass  (default: false)
      Whether to bandpass-filter each Doppler trace before correlation.
      The default (FALSE) is right for almost all cases. Set TRUE only
      if your raw Doppler is dominated by content outside the TID band
      (e.g. a strong terminator gradient or carrier drift) that
      confuses the cross-correlation.

      WHY DEFAULT OFF: bandpassing produces nearly-sinusoidal signals
      whose autocorrelation has multiple lobes one period apart. The
      lag-finder can then grab a SECONDARY peak instead of the true
      lag, giving a wrong (often opposite-sign or magnitude-wrong)
      answer with a deceptively high correlation. This was a real
      failure mode hit during development of this script -- raw lags
      were ~15-22 min while bandpass-filtered lags were 1-3 min for
      the SAME pairs, leading to a wildly wrong direction-of-arrival.

      If you do enable bandpass, ensure max_lag_seconds < shortest
      period / 2.

  period_band_seconds [low, high]
      Used only when use_bandpass=true. Bandpass filter range in
      seconds:
        [900,  3600]  =  15-60 min   (typical MSTID)
        [1800, 5400]  =  30-90 min   (MSTID/early LSTID)
        [3600, 7200]  =  60-120 min  (LSTID)
        [1800, 7200]  =  30-120 min  (broad band)

  max_lag_seconds  (optional)
      Maximum |lag| considered in the cross-correlation peak search.
      If omitted, the script computes a SMART default:

         max_lag = largest_pair_baseline_km * 1000 / min_expected_speed

      The default min_expected_speed is 100 m/s, giving a comfortable
      upper bound for plausible TID lags across your array. Override
      with min_expected_speed_m_s in the config if you have prior
      info on the wave type (e.g. 300 m/s for known LSTID).

  min_expected_speed_m_s  (default: 100)
      Used only when max_lag_seconds is auto-computed (see above).

OUTPUT INTERPRETATION
=====================
The output prints:

  - Loaded station information and their WWV-path midpoints (including
    the optional "method" field recording which Doppler extractor was
    used per station: "fft" or "autocorr"; default "fft")
  - Pairwise lag table: each row gives the cross-correlation lag and
    correlation peak for one (station_i, station_j) pair. Positive lag
    means station_j lags station_i (wave reached i first).
  - The least-squares slowness vector inversion result:
      Phase speed
      Wave heading toward (azimuth degrees true)
      Wave coming from (180-degree complement)
  - A type classification (MSTID / LSTID) based on speed.

QUALITY ASSESSMENT
==================
The result is trustworthy if:

  - Pairwise correlations are mostly > 0.7 across stations
  - Pairwise lags are all comfortably within +/- max_lag_seconds (none
    pegged at the edge)
  - Speed is in 100-1500 m/s range
  - Azimuth is consistent across multiple filter bands (run the
    analysis 2-3 times with different period_band_seconds)
  - Adding/removing one station doesn't change the answer by more than
    ~10 degrees in azimuth or ~20% in speed

If multiple of these conditions fail, the array may have a poor bearing
distribution, the wave may not be planar, or there may be multiple
overlapping waves. With 4 stations you can sometimes drop the lowest-
correlation pair and re-run with the remaining 3 to test robustness.

REQUIREMENTS
============
    pip install numpy scipy pandas

SEE ALSO
========
    tid_pair.py            two-station baseline analysis
    drf_to_doppler.py      input data extractor (DRF I/Q -> CSV)
    find_event_stations.py find companion stations for a given event date
"""

import json
import math
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, correlate

__version__ = "1.1.0"

WWV_LAT, WWV_LON = 40.6776, -105.0405
EARTH_R_KM = 6371.0


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def to_rad(d): return d * math.pi / 180.0
def to_deg(r): return r * 180.0 / math.pi


def grid_to_latlon(grid):
    g = grid.strip()
    if len(g) < 4:
        return None
    A = ord(g[0].upper()) - ord('A')
    B = ord(g[1].upper()) - ord('A')
    C = int(g[2]); D = int(g[3])
    lon = -180 + A*20 + C*2
    lat = -90 + B*10 + D*1
    if len(g) >= 6:
        E = ord(g[4].lower()) - ord('a')
        F = ord(g[5].lower()) - ord('a')
        lon += E*(2/24) + (1/24)
        lat += F*(1/24) + (0.5/24)
    else:
        lon += 1.0; lat += 0.5
    return lat, lon


def great_circle_midpoint(lat1, lon1, lat2, lon2):
    f1, l1 = to_rad(lat1), to_rad(lon1)
    f2, l2 = to_rad(lat2), to_rad(lon2)
    dl = l2 - l1
    bx = math.cos(f2) * math.cos(dl)
    by = math.cos(f2) * math.sin(dl)
    f3 = math.atan2(math.sin(f1) + math.sin(f2),
                    math.sqrt((math.cos(f1) + bx)**2 + by**2))
    l3 = l1 + math.atan2(by, math.cos(f1) + bx)
    return to_deg(f3), (to_deg(l3) + 540) % 360 - 180


def latlon_to_local_xy(lat, lon, lat0, lon0):
    """Equirectangular projection to local east-north meters."""
    x = to_rad(lon - lon0) * math.cos(to_rad(lat0)) * EARTH_R_KM * 1000.0
    y = to_rad(lat - lat0) * EARTH_R_KM * 1000.0
    return x, y


# ---------------------------------------------------------------------------
# Signal processing
# ---------------------------------------------------------------------------
def bandpass(series, fs_hz, low_period_s, high_period_s, order=3):
    """Bandpass filter targeting periods between low_period_s and high_period_s.
    Note: low_period_s < high_period_s, so the high frequency cutoff is
    1/low_period_s and the low frequency cutoff is 1/high_period_s."""
    nyq = 0.5 * fs_hz
    low = (1.0 / high_period_s) / nyq
    high = (1.0 / low_period_s) / nyq
    low = max(low, 1e-6)
    high = min(high, 0.99)
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, series)


def cross_correlate_lag(x, y, fs_hz, max_lag_s):
    """Return (lag_seconds, peak_correlation).
    Positive lag means y lags x (i.e., the same feature appears later in y).
    Convention: scipy.signal.correlate(y, x) peaks at index n-1 + k where k
    is the shift such that y[t] ~ x[t-k], so positive k means y is shifted
    later than x, i.e., y lags. lags = (peak_index - (n-1)) / fs.
    """
    x = (x - np.mean(x)) / (np.std(x) + 1e-12)
    y = (y - np.mean(y)) / (np.std(y) + 1e-12)
    n = len(x)
    corr = correlate(y, x, mode="full") / n
    lags = (np.arange(2*n - 1) - (n - 1)) / fs_hz
    mask = np.abs(lags) <= max_lag_s
    if not mask.any():
        return 0.0, 0.0
    sub_corr = corr[mask]
    sub_lags = lags[mask]
    # Use the maximum (positive) correlation peak, not absolute - we want
    # the same feature, not an antiphase match.
    idx = int(np.argmax(sub_corr))
    return float(sub_lags[idx]), float(sub_corr[idx])


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
@dataclass
class StationData:
    name: str
    lat: float
    lon: float
    midpoint: tuple
    times: np.ndarray   # seconds since epoch
    doppler: np.ndarray
    method: str = "fft"   # extraction method: "fft" or "autocorr"


def load_station(cfg, t_start, t_end, target_dt_s, smooth_seconds=None):
    df = pd.read_csv(cfg["file"])
    cols = [c.lower() for c in df.columns]
    df.columns = cols
    tcol = next(c for c in cols if "time" in c or "utc" in c or "stamp" in c)
    dcol = next(c for c in cols if "dop" in c or "freq" in c)
    df[tcol] = pd.to_datetime(df[tcol], utc=True)
    df = df.sort_values(tcol).set_index(tcol)
    df = df.loc[t_start:t_end]
    if df.empty:
        raise ValueError(f"{cfg['name']}: no data in event window")

    # Resample to common cadence
    target = f"{int(target_dt_s)}s"
    df = df[[dcol]].resample(target).mean().interpolate()

    if smooth_seconds is not None:
        from scipy.signal import savgol_filter
        poly_order = 3
        n_samples = int(round(smooth_seconds / target_dt_s))
        min_window = poly_order + 2
        if n_samples < min_window:
            raise ValueError(
                f"--smooth {smooth_seconds:g}s too small for dt={target_dt_s}s; "
                f"need >= {min_window * target_dt_s:g}s for poly_order={poly_order}"
            )
        if n_samples % 2 == 0:
            n_samples += 1
        df[dcol] = savgol_filter(df[dcol].to_numpy(), n_samples, poly_order)

    times = df.index.astype("int64").to_numpy() / 1e9
    doppler = df[dcol].to_numpy()

    if "lat" in cfg:
        lat, lon = cfg["lat"], cfg["lon"]
    else:
        lat, lon = grid_to_latlon(cfg["grid"])

    mid = great_circle_midpoint(WWV_LAT, WWV_LON, lat, lon)
    method = cfg.get("method", "fft")
    return StationData(cfg["name"], lat, lon, mid, times, doppler, method)


# ---------------------------------------------------------------------------
# DOA solver
# ---------------------------------------------------------------------------
def solve_doa(stations, fs_hz, period_band_s, max_lag_s, use_bandpass=False):
    """Returns dict with azimuth_deg, speed_m_s, slowness vector, and pairwise
    lags.

    use_bandpass=False (default) is recommended for most cases. Bandpassing
    can create artificial multi-peak correlation functions where the lag-
    finder grabs a secondary peak instead of the true lag (a real failure
    mode we hit during the Jan 2026 analysis). Use bandpass only when the
    raw Doppler trace has strong content OUTSIDE the TID period band that
    confuses correlation (e.g. terminator gradient, fast carrier drift).
    Most events do not need it.
    """
    # Common length
    n = min(len(s.doppler) for s in stations)
    sigs = []
    for s in stations:
        if use_bandpass:
            sig = bandpass(s.doppler[:n], fs_hz,
                           period_band_s[0], period_band_s[1])
        else:
            # Just remove the mean; cross-correlation is amplitude-invariant
            # after z-normalization in cross_correlate_lag().
            sig = s.doppler[:n] - np.mean(s.doppler[:n])
        sigs.append(sig)

    # Project all midpoints into local EN frame, centered on array centroid
    mids = np.array([s.midpoint for s in stations])
    lat0 = float(np.mean(mids[:, 0]))
    lon0 = float(np.mean(mids[:, 1]))
    pos = np.array([latlon_to_local_xy(lat, lon, lat0, lon0)
                    for lat, lon in mids])  # shape (N,2)

    # Pairwise lags
    N = len(stations)
    pair_rows = []
    pair_taus = []
    pair_info = []
    for i in range(N):
        for j in range(i + 1, N):
            tau, c = cross_correlate_lag(sigs[i], sigs[j], fs_hz, max_lag_s)
            # Model: arrival time at station k is t_k = s . r_k.
            # Lag of j relative to i is tau_ij = t_j - t_i = s . (r_j - r_i).
            dr = pos[j] - pos[i]
            pair_rows.append(dr)
            pair_taus.append(tau)
            pair_info.append({
                "i": stations[i].name,
                "j": stations[j].name,
                "lag_s": tau,
                "corr": c,
                "dx_m": dr[0],
                "dy_m": dr[1],
            })

    A = np.array(pair_rows)            # (M, 2)
    b = np.array(pair_taus)            # (M,)
    # Least-squares solve for slowness vector s [s/m]
    s_vec, residuals, rank, sv = np.linalg.lstsq(A, b, rcond=None)
    sx, sy = float(s_vec[0]), float(s_vec[1])

    slow_mag = math.hypot(sx, sy)
    speed_m_s = 1.0 / slow_mag if slow_mag > 0 else float("inf")
    # Azimuth of propagation direction (where the wave is heading), measured
    # clockwise from north.
    az_rad = math.atan2(sx, sy)
    az_deg = (math.degrees(az_rad) + 360) % 360
    # Direction the wave is COMING FROM is opposite:
    az_from = (az_deg + 180) % 360

    if residuals is not None and len(residuals) > 0:
        sse = float(residuals[0])
    else:
        pred = A.dot(s_vec)
        sse = float(np.sum((b - pred) ** 2))
    m_pairs = int(A.shape[0])
    rms_resid_s = (sse / m_pairs) ** 0.5 if m_pairs > 0 else float("nan")
    sv_arr = [float(v) for v in sv]
    if len(sv_arr) >= 2 and min(sv_arr) > 0:
        sv_ratio = max(sv_arr) / min(sv_arr)
    else:
        sv_ratio = float("inf")
    return {
        "azimuth_to_deg": az_deg,
        "azimuth_from_deg": az_from,
        "speed_m_s": speed_m_s,
        "slowness_s_per_m": (sx, sy),
        "pairs": pair_info,
        "array_center": (lat0, lon0),
        "rms_resid_s": rms_resid_s,
        "sv_ratio": sv_ratio,
        "lstsq_rank": int(rank),
        "n_pairs": m_pairs,
    }


# ---------------------------------------------------------------------------
# Result diagnostics (observational, NOT pass/fail). Every value here is
# already computed by the inversion; this only reads and reports it.
# Thresholds are GUIDELINE defaults grounded in the docstring's existing
# advice (mostly > 0.7, LSTID 300-1000 m/s). Tunable.
# ---------------------------------------------------------------------------
DIAG_SV_RATIO_MAX   = 30.0
DIAG_RESID_FRAC_MAX = 0.25
DIAG_CORR_WEAK      = 0.40
DIAG_SPEED_LO       = 100.0
DIAG_SPEED_HI       = 1000.0


def _triangle_closures(pairs):
    """Sum of signed lags around every station triple.

    pair_info stores lag_s for i->j with i<j only. A leg not stored
    in i<j order is the negative of its stored counterpart. Returns
    list of (triple_names, closure_s, mean_leg_s).
    """
    lag = {}
    names = set()
    for p in pairs:
        lag[(p["i"], p["j"])] = p["lag_s"]
        names.add(p["i"]); names.add(p["j"])
    names = sorted(names)

    def leg(a, b):
        if (a, b) in lag:
            return lag[(a, b)]
        if (b, a) in lag:
            return -lag[(b, a)]
        return None

    out = []
    for ia in range(len(names)):
        for ib in range(ia + 1, len(names)):
            for ic in range(ib + 1, len(names)):
                a, bb, c = names[ia], names[ib], names[ic]
                l1, l2, l3 = leg(a, bb), leg(bb, c), leg(c, a)
                if None in (l1, l2, l3):
                    continue
                closure = l1 + l2 + l3
                mean_leg = (abs(l1) + abs(l2) + abs(l3)) / 3.0
                out.append(((a, bb, c), closure, mean_leg))
    return out


def format_diagnostics(result):
    """Return (text_block, n_flagged). Observational; never a verdict."""
    L = []
    flagged = 0
    L.append("=== RESULT DIAGNOSTICS ===")
    L.append("(Guideline ranges, not pass/fail. You decide what is")
    L.append(" acceptable for your event and array.)")
    L.append("")

    svr = result.get("sv_ratio", float("inf"))
    L.append("[1] Geometry conditioning")
    L.append(f"    Singular-value ratio:  {svr:.1f}")
    L.append(f"    Typical good range:    < ~{DIAG_SV_RATIO_MAX:.0f}  "
             f"(higher = near-collinear midpoints,")
    L.append("                           direction poorly constrained)")
    if not (svr < DIAG_SV_RATIO_MAX):
        flagged += 1
        L.append("    >> OUTSIDE typical range. Array geometry may not")
        L.append("       separate speed from heading well; treat the")
        L.append("       direction with caution.")
    L.append("")

    rms = result.get("rms_resid_s", float("nan"))
    pairs = result.get("pairs", [])
    mean_abs_lag = (sum(abs(p["lag_s"]) for p in pairs) / len(pairs)
                    if pairs else float("nan"))
    frac = (rms / mean_abs_lag) if mean_abs_lag and mean_abs_lag > 0 else float("nan")
    L.append("[2] Plane-wave fit residual")
    L.append(f"    RMS lag residual:      {rms:.0f} s  "
             f"({frac*100:.1f}% of mean abs lag {mean_abs_lag:.0f} s)")
    L.append(f"    Typical good range:    < ~{DIAG_RESID_FRAC_MAX*100:.0f}%  "
             f"(higher = lags not consistent")
    L.append("                           with a single coherent wave)")
    if not (frac < DIAG_RESID_FRAC_MAX):
        flagged += 1
        L.append("    >> OUTSIDE typical range. A single plane wave does")
        L.append("       not explain the lags well: possible noise or")
        L.append("       multiple superimposed waves.")
    L.append("")

    corrs = [p["corr"] for p in pairs] if pairs else []
    if corrs:
        cmin, cmax = min(corrs), max(corrs)
        cmean = sum(corrs) / len(corrs)
        L.append("[3] Pairwise correlation")
        L.append(f"    {len(corrs)} pairs: min {cmin:.3f}, mean "
                 f"{cmean:.3f}, max {cmax:.3f}")
        L.append(f"    Guideline:             pairs < {DIAG_CORR_WEAK:.2f} "
                 f"are weak; target >0.7")
        weak = [f"{p['i']}->{p['j']} {p['corr']:.3f}"
                for p in pairs if p["corr"] < DIAG_CORR_WEAK]
        if weak:
            flagged += 1
            L.append(f"    >> {len(weak)} weak pair(s): " + "; ".join(weak))
            L.append("       Consider dropping the least-coherent station")
            L.append("       and re-running to test robustness.")
        L.append("")

    closures = _triangle_closures(pairs)
    if closures:
        worst = max(closures,
                    key=lambda t: (abs(t[1]) / t[2]) if t[2] > 0 else 0)
        tri, cl, ml = worst
        frac_cl = (abs(cl) / ml) if ml > 0 else float("inf")
        L.append("[4] Triangle closure")
        L.append(f"    {len(closures)} triple(s), worst: {abs(cl):.0f} s  "
                 f"({frac_cl*100:.1f}% of mean leg)")
        L.append("    Typical good range:    < ~15%  (higher = at least")
        L.append("                           one pair lag is a wrong peak)")
        if not (frac_cl < 0.15):
            flagged += 1
            L.append(f"    >> OUTSIDE typical range (triple "
                     f"{tri[0]}/{tri[1]}/{tri[2]}). One pair correlation")
            L.append("       likely locked a wrong peak; check the pairwise")
            L.append("       table; a window tighten or drop may help.")
        L.append("")

    sp = result.get("speed_m_s", float("nan"))
    L.append("[5] Phase speed")
    L.append(f"    Result:                {sp:.0f} m/s")
    L.append(f"    Typical TID range:     {DIAG_SPEED_LO:.0f}-"
             f"{DIAG_SPEED_HI:.0f} m/s (LSTID); 100-300 (MSTID)")
    if not (DIAG_SPEED_LO < sp < DIAG_SPEED_HI):
        flagged += 1
        rel = "ABOVE" if sp >= DIAG_SPEED_HI else "BELOW"
        L.append(f"    >> {rel} typical TID speeds. If combined with")
        L.append("       other flags, this pattern is characteristic of")
        L.append("       contaminated lags rather than a real wave.")
    L.append("")

    if flagged == 0:
        L.append("  >> All five diagnostics fall within typical ranges.")
    else:
        L.append(f"  >> {flagged} of 5 diagnostic(s) outside typical "
                 f"ranges.")
        L.append("     This result merits scrutiny before use; see the")
        L.append("     flagged items above.")
    L.append("")
    L.append("Reminder: these are internal consistency checks. They")
    L.append("cannot confirm the result is physically real -- cross-")
    L.append("checking against an independent method or a hand-analysed")
    L.append("event remains the strongest validation.")
    return "\n".join(L), flagged


def _write_run_log(config, result, diag_text):
    """Append a self-contained per-run record to ./runs/<ts>_run.log.

    Non-fatal on any error -- a logging failure must never break a run.
    """
    import os, sys, subprocess, datetime
    runs_dir = os.path.join(os.getcwd(), "runs")
    os.makedirs(runs_dir, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H%M%SZ")
    log_path = os.path.join(runs_dir, f"{ts}_run.log")
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        git_hash = "(unavailable)"
    stations = config.get("stations", [])
    lines = []
    lines.append("=== psws-drf-tid-tools run log ===")
    lines.append(f"Timestamp:   {ts}")
    lines.append("Tool:        tid_doa.py")
    lines.append(f"Working dir: {os.getcwd()}")
    lines.append("")
    lines.append("--- INPUTS (from config) ---")
    lines.append(f"Event start: {config.get('event_start_utc')}")
    lines.append(f"Event end:   {config.get('event_end_utc')}")
    lines.append(f"Resample s:  {config.get('resample_seconds')}")
    lines.append(f"Use bandpass:{config.get('use_bandpass')}")
    if config.get("smooth_seconds"):
        lines.append(f"Smoothing:   Savitzky-Golay "
                     f"{config.get('smooth_seconds')}s")
    lines.append(f"Stations ({len(stations)}):")
    for s in stations:
        method_str = s.get("method", "fft")
        lines.append(f"  {s.get('name','?'):<14} "
                     f"file={s.get('file','?')}  "
                     f"method={method_str}  "
                     f"lat={s.get('lat','?')} lon={s.get('lon','?')}")
    lines.append("")
    lines.append("--- RESULT ---")
    lines.append(f"Phase speed:    {result.get('speed_m_s'):.1f} m/s")
    lines.append(f"Heading toward: {result.get('azimuth_to_deg'):.1f} deg")
    lines.append(f"Coming from:    {result.get('azimuth_from_deg'):.1f} deg")
    lines.append("")
    lines.append("--- PAIRWISE ---")
    for p in result.get("pairs", []):
        lines.append(f"  {p['i']:>10s} -> {p['j']:<10s} "
                     f"lag={p['lag_s']:+7.1f}s corr={p['corr']:+.3f}")
    lines.append("")
    lines.append("--- DIAGNOSTICS ---")
    lines.append(diag_text if diag_text else "(diagnostics suppressed)")
    lines.append("")
    lines.append("--- PROVENANCE ---")
    lines.append(f"git commit:  {git_hash}")
    lines.append(f"command:     {' '.join(sys.argv)}")
    lines.append("")
    with open(log_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Run log written: {log_path}")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def run(config):
    t0 = pd.to_datetime(config["event_start_utc"], utc=True)
    t1 = pd.to_datetime(config["event_end_utc"], utc=True)
    dt_s = config.get("resample_seconds", 10)
    fs_hz = 1.0 / dt_s
    period_band = config.get("period_band_seconds", [900, 5400])  # 15-90 min
    use_bandpass = config.get("use_bandpass", False)
    min_speed_m_s = config.get("min_expected_speed_m_s", 100.0)

    smooth_s = config.get("smooth_seconds")
    stations = [load_station(c, t0, t1, dt_s, smooth_seconds=smooth_s) for c in config["stations"]]
    if len(stations) < 3:
        raise SystemExit("Need at least 3 stations for direction-of-arrival.")

    # Compute the largest pairwise midpoint baseline (km) for a smarter
    # default max_lag_seconds. The maximum lag any pair can have is
    # baseline / min_expected_speed, so this sets the search to JUST cover
    # plausible TID lags rather than half-period-aliasing.
    def _hav_km(lat1, lon1, lat2, lon2):
        f1, f2 = to_rad(lat1), to_rad(lat2)
        df = to_rad(lat2 - lat1)
        dl = to_rad(lon2 - lon1)
        a = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
        return 2 * EARTH_R_KM * math.asin(math.sqrt(a))

    max_baseline_km = 0.0
    for i in range(len(stations)):
        for j in range(i + 1, len(stations)):
            mi, mj = stations[i].midpoint, stations[j].midpoint
            d = _hav_km(mi[0], mi[1], mj[0], mj[1])
            if d > max_baseline_km:
                max_baseline_km = d
    smart_max_lag = max_baseline_km * 1000.0 / min_speed_m_s

    # Use config max_lag_seconds if given; otherwise use the smart default.
    if "max_lag_seconds" in config:
        max_lag_s = config["max_lag_seconds"]
        print(f"Using config max_lag_seconds = {max_lag_s:.0f} s "
              f"(largest baseline {max_baseline_km:.0f} km would imply "
              f"{smart_max_lag:.0f} s at {min_speed_m_s:.0f} m/s).")
    else:
        max_lag_s = smart_max_lag
        print(f"Auto max_lag_seconds = {max_lag_s:.0f} s "
              f"(largest baseline {max_baseline_km:.0f} km / "
              f"{min_speed_m_s:.0f} m/s minimum expected speed).")

    # Aliasing guard (informational; bandpass-only).
    if use_bandpass:
        half_shortest = period_band[0] / 2.0
        if max_lag_s > half_shortest:
            print(f"NOTE: bandpass enabled and max_lag_seconds ({max_lag_s:.0f}) "
                  f"> half shortest period ({half_shortest:.0f} s). With "
                  f"bandpass, lag estimates can alias to the wrong cycle. "
                  f"Disable use_bandpass or lower max_lag_seconds.\n")
    else:
        print(f"Bandpass disabled (default). Raw mean-subtracted signals will be "
              f"cross-correlated. To enable, set \"use_bandpass\": true in "
              f"config.\n")

    print(f"Loaded {len(stations)} stations, "
          f"window {t0} to {t1}, dt={dt_s}s")
    for s in stations:
        print(f"  {s.name:12s} mid=({s.midpoint[0]:.2f},{s.midpoint[1]:.2f}) "
              f"N={len(s.doppler)}")

    result = solve_doa(stations, fs_hz, period_band, max_lag_s,
                       use_bandpass=use_bandpass)

    print("\nPairwise time lags (positive = second station lags first):")
    for p in result["pairs"]:
        print(f"  {p['i']:>10s} -> {p['j']:<10s} "
              f"lag={p['lag_s']:+7.1f} s  corr={p['corr']:+.3f}")

    print("\n=== TID Direction-of-Arrival Result ===")
    print(f"  Phase speed:           {result['speed_m_s']:7.1f} m/s "
          f"({result['speed_m_s']*3.6:.0f} km/h)")
    print(f"  Wave heading toward:   {result['azimuth_to_deg']:6.1f}° "
          f"(true bearing)")
    print(f"  Wave coming from:      {result['azimuth_from_deg']:6.1f}° "
          f"(true bearing)")

    speed = result["speed_m_s"]
    if 100 < speed < 350:
        print("  -> Consistent with medium-scale TID (MSTID).")
    elif 350 <= speed < 1000:
        print("  -> Consistent with large-scale TID (LSTID).")
    else:
        print("  -> Speed outside typical TID range; check filter band and lags.")

    diag_text = ""
    if not globals().get("_NO_DIAGNOSTICS", False):
        diag_text, _nflag = format_diagnostics(result)
        print()
        print(diag_text)

    if not globals().get("_NO_RUNLOG", False):
        try:
            _write_run_log(config, result, diag_text)
        except Exception as _e:
            print(f"(run-log write skipped: {_e})")


# ---------------------------------------------------------------------------
# Example config (write your own to a JSON file and pass it as argv[1])
# ---------------------------------------------------------------------------
EXAMPLE_CONFIG = {
    "event_start_utc": "2026-01-19T00:00:00Z",
    "event_end_utc":   "2026-01-19T01:15:00Z",
    "resample_seconds": 10,
    "use_bandpass": False,
    "min_expected_speed_m_s": 100,
    # max_lag_seconds is auto-computed from the largest baseline and
    # min_expected_speed_m_s; you can override it by adding it here.
    # period_band_seconds is only used if use_bandpass is True.
    "stations": [
        {"name": "N6RFM",   "file": "n6rfm.csv",   "lat": 32.94, "lon":  -97.21},
        {"name": "AA6BD",   "file": "aa6bd.csv",   "lat": 35.06, "lon":  -85.13},
        {"name": "W7LUX",   "file": "w7lux.csv",   "lat": 35.10, "lon": -111.71},
        {"name": "AC0G_ND", "file": "ac0g_nd.csv", "lat": 46.88, "lon":  -96.83}
    ]
}


def _cli():
    import argparse
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("CONFIG FORMAT", 1)[0],
        epilog="See the docstring at the top of the script for full details, "
               "including config-file format, parameter guidance, and "
               "interpretation of output.",
    )
    ap.add_argument("config", nargs="?", default=None,
                    help="Path to event JSON config file. Run without this "
                         "argument to write example_event.json and exit.")
    ap.add_argument("--smooth", type=float, default=None,
                    metavar="N",
                    help="apply Savitzky-Golay smoothing with N-second "
                         "window to each station's Doppler series before "
                         "cross-correlation (default off; recommended for "
                         "stations flagged POOR by quality_summary.py)")
    ap.add_argument("--no-diagnostics", action="store_true",
                    help="suppress the RESULT DIAGNOSTICS block "
                         "(shown by default)")
    ap.add_argument("--no-run-log", action="store_true",
                    help="do not write the per-run log under ./runs/ "
                         "(written by default)")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.2.0")
    return ap.parse_args()


if __name__ == "__main__":
    _args = _cli()
    globals()["_NO_DIAGNOSTICS"] = bool(getattr(_args, "no_diagnostics", False))
    globals()["_NO_RUNLOG"] = bool(getattr(_args, "no_run_log", False))
    if _args.config is None:
        print("No config given. Writing example_event.json template.")
        with open("example_event.json", "w") as f:
            json.dump(EXAMPLE_CONFIG, f, indent=2)
        print("Edit example_event.json with your stations and run:")
        print("    python tid_doa.py example_event.json")
        sys.exit(0)
    with open(_args.config) as f:
        cfg = json.load(f)
    if _args.smooth is not None:
        cfg["smooth_seconds"] = _args.smooth
        print(f"Smoothing enabled: Savitzky-Golay window={_args.smooth:g}s, polynomial order 3")
    run(cfg)
