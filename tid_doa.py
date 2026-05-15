r"""
tid_doa.py — multi-station TID direction-of-arrival analyzer


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.1.0  Default cross-correlation now operates on raw (mean-subtracted)
          Doppler instead of bandpass-filtered. Bandpass was producing
          multi-lobed correlation functions causing the lag-finder to lock
          onto wrong secondary peaks. New config flag use_bandpass restores
          the previous behavior if needed. max_lag_seconds is now auto-
          computed from the largest baseline divided by min_expected_speed.
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
Given Doppler-vs-time CSVs from 3 or more HamSCI Grape stations recording
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
        {"name": "N6RFM",   "file": "n6rfm.csv",   "lat": 32.94, "lon":  -97.21},
        {"name": "AA6BD",   "file": "aa6bd.csv",   "lat": 35.06, "lon":  -85.13},
        {"name": "W7LUX",   "file": "w7lux.csv",   "lat": 35.10, "lon": -111.71},
        {"name": "AC0G_ND", "file": "ac0g_nd.csv", "lat": 46.88, "lon":  -96.83}
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

  - Loaded station information and their WWV-path midpoints
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
    return StationData(cfg["name"], lat, lon, mid, times, doppler)


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

    return {
        "azimuth_to_deg": az_deg,
        "azimuth_from_deg": az_from,
        "speed_m_s": speed_m_s,
        "slowness_s_per_m": (sx, sy),
        "pairs": pair_info,
        "array_center": (lat0, lon0),
    }


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
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.1.0")
    return ap.parse_args()


if __name__ == "__main__":
    _args = _cli()
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
