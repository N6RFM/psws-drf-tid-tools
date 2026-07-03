#!/usr/bin/env python3
"""
synthetic_signal.py -- TID signal model for synthetic DRF generation.

Generates complex I/Q samples representing a WWV carrier with a
TID-induced Doppler shift at a given station, with controllable
noise type and level.

Signal model:
  I/Q(t) = A_carrier * exp(j*2*pi*(f_carrier + f_doppler(t))*t) + noise(t)

  f_doppler(t) = amp_hz * sin(2*pi*t/period_s + phase_rad)

  phase_rad = 2*pi * tau_k / period_s
  tau_k     = slowness . position_k   (DOA geometry, AE projection)

Noise types:
  'awgn'     -- additive white Gaussian noise only
  'realistic' -- AWGN + slow ionospheric drift + occasional fading
"""
import math
import numpy as np


# ---------------------------------------------------------------------------
# DOA geometry (matches tid_doa.py exactly)
# ---------------------------------------------------------------------------
EARTH_R_KM = 6371.0
WWV_LAT, WWV_LON = 40.6776, -105.0405


def _to_rad(d):
    return d * math.pi / 180.0


def great_circle_midpoint(lat1, lon1, lat2, lon2):
    """Great-circle midpoint -- matches tid_doa.great_circle_midpoint."""
    f1, l1 = _to_rad(lat1), _to_rad(lon1)
    f2, l2 = _to_rad(lat2), _to_rad(lon2)
    Bx = math.cos(f2) * math.cos(l2 - l1)
    By = math.cos(f2) * math.sin(l2 - l1)
    f3 = math.atan2(math.sin(f1) + math.sin(f2),
                    math.sqrt((math.cos(f1) + Bx)**2 + By**2))
    l3 = l1 + math.atan2(By, math.cos(f1) + Bx)
    return math.degrees(f3), math.degrees(l3)


def latlon_to_local_xy(lat, lon, lat0, lon0):
    """Azimuthal equidistant projection -- matches tid_doa.latlon_to_local_xy."""
    f0, l0 = _to_rad(lat0), _to_rad(lon0)
    f1, l1 = _to_rad(lat), _to_rad(lon)
    dl = l1 - l0
    cos_c = (math.sin(f0)*math.sin(f1) +
             math.cos(f0)*math.cos(f1)*math.cos(dl))
    cos_c = max(-1.0, min(1.0, cos_c))
    c = math.acos(cos_c)
    dist_m = c * EARTH_R_KM * 1000.0
    if c < 1e-7:
        return 0.0, 0.0
    sin_az = math.cos(f1)*math.sin(dl)/math.sin(c)
    cos_az = (math.sin(f1)-math.sin(f0)*cos_c)/(math.cos(f0)*math.sin(c))
    az = math.atan2(sin_az, cos_az)
    return dist_m*math.sin(az), dist_m*math.cos(az)


def compute_station_lag(station_lat, station_lon,
                        speed_m_s, azimuth_from_deg,
                        array_midpoints):
    """
    Compute the TID arrival lag at this station relative to the array
    centroid, using the same geometry as tid_doa.py.

    Parameters
    ----------
    station_lat, station_lon : float
        Station receiver coordinates.
    speed_m_s : float
        True TID phase speed.
    azimuth_from_deg : float
        True direction wave is coming FROM (degrees true bearing).
    array_midpoints : list of (lat, lon)
        IPP midpoints of all stations, for computing the centroid.

    Returns
    -------
    lag_s : float
        Arrival lag in seconds (positive = wave arrives later than centroid).
    midpoint : (lat, lon)
        IPP midpoint for this station.
    """
    midpoint = great_circle_midpoint(WWV_LAT, WWV_LON, station_lat, station_lon)

    # Array centroid
    lats = [m[0] for m in array_midpoints]
    lons = [m[1] for m in array_midpoints]
    lat0 = sum(lats) / len(lats)
    lon0 = sum(lons) / len(lons)

    # AE-projected position
    x, y = latlon_to_local_xy(midpoint[0], midpoint[1], lat0, lon0)

    # Slowness vector (wave heading TOWARD azimuth_from + 180)
    az_toward_rad = _to_rad((azimuth_from_deg + 180) % 360)
    sx = math.sin(az_toward_rad) / speed_m_s
    sy = math.cos(az_toward_rad) / speed_m_s

    lag_s = sx * x + sy * y
    return lag_s, midpoint


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def generate_iq(
    duration_s,
    sample_rate_hz,
    f_carrier_hz,
    tid_amp_hz,
    tid_period_s,
    tid_phase_rad,
    snr_db,
    noise_type="awgn",
    rng=None,
):
    """
    Generate complex I/Q samples for one station.

    Parameters
    ----------
    duration_s : float
    sample_rate_hz : int
    f_carrier_hz : float
        WWV carrier frequency (e.g. 10e6).
    tid_amp_hz : float
        TID Doppler amplitude in Hz.
    tid_period_s : float
        TID period in seconds.
    tid_phase_rad : float
        Phase offset at t=0 (encodes the station's DOA lag).
    snr_db : float
        Signal-to-noise ratio in dB.
    noise_type : str
        'awgn' or 'realistic'.
    rng : np.random.Generator, optional

    Returns
    -------
    iq : np.ndarray, complex64
        I/Q samples.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n = int(duration_s * sample_rate_hz)
    t = np.arange(n) / sample_rate_hz

    # TID Doppler shift (Hz)
    f_doppler = tid_amp_hz * np.sin(2 * np.pi * t / tid_period_s + tid_phase_rad)

    if noise_type == "realistic":
        # Slow ionospheric background drift (random walk + sinusoidal component)
        drift_rate = rng.normal(0, 0.002)           # Hz/min
        drift = drift_rate * t / 60.0
        # Slow sinusoidal background (~3-6 hour period, much longer than TID)
        bg_period = rng.uniform(3 * 3600, 6 * 3600)
        bg_amp = rng.uniform(0.05, 0.3)
        bg_phase = rng.uniform(0, 2 * np.pi)
        background = bg_amp * np.sin(2 * np.pi * t / bg_period + bg_phase)
        f_doppler = f_doppler + drift + background

        # Fading: one or two Gaussian dips in amplitude
        n_fades = rng.integers(0, 3)
        amplitude_env = np.ones(n)
        for _ in range(n_fades):
            t_fade = rng.uniform(0.1 * duration_s, 0.9 * duration_s)
            tau_fade = rng.uniform(0.05 * duration_s, 0.15 * duration_s)
            depth = rng.uniform(0.3, 0.8)
            amplitude_env *= (1 - depth * np.exp(-((t - t_fade) / tau_fade) ** 2))
    else:
        amplitude_env = np.ones(n)

    # Integrate Doppler to get instantaneous phase
    # phi(t) = 2*pi * integral(f_carrier + f_doppler) dt
    # Since f_carrier is large but constant, it cancels in cross-correlation
    # so we only need to track the Doppler phase for the baseband signal
    doppler_phase = 2 * np.pi * np.cumsum(f_doppler) / sample_rate_hz
    iq_clean = amplitude_env * np.exp(1j * doppler_phase).astype(np.complex128)

    # Add AWGN
    signal_power = np.mean(np.abs(iq_clean) ** 2)
    snr_linear = 10 ** (snr_db / 10.0)
    noise_power = signal_power / snr_linear
    noise_std = np.sqrt(noise_power / 2)
    noise = noise_std * (rng.standard_normal(n) + 1j * rng.standard_normal(n))

    iq = (iq_clean + noise).astype(np.complex64)
    return iq
