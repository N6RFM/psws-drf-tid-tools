#!/usr/bin/env python3
"""
synthetic_signal.py v2 -- Enhanced TID signal model for synthetic DRF
generation.

Enhancements over v1:
1. Asymmetric fading: upper/lower sideband fade independently
2. Non-sinusoidal/period chirp: period drifts linearly over event
3. Two superimposed TIDs: second wave at different speed/azimuth
4. Coloured (1/f) noise: more realistic than flat AWGN
5. E-region spikes: random narrow-band bursts
6. Carrier frequency offset: DC bias on all stations
7. Time-varying SNR: sinusoidal SNR modulation

All enhancements are optional -- v1 behaviour is preserved when
new parameters are not specified.
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
    midpoint = great_circle_midpoint(WWV_LAT, WWV_LON,
                                     station_lat, station_lon)
    lats = [m[0] for m in array_midpoints]
    lons = [m[1] for m in array_midpoints]
    lat0 = sum(lats) / len(lats)
    lon0 = sum(lons) / len(lons)
    x, y = latlon_to_local_xy(midpoint[0], midpoint[1], lat0, lon0)
    az_toward_rad = _to_rad((azimuth_from_deg + 180) % 360)
    sx = math.sin(az_toward_rad) / speed_m_s
    sy = math.cos(az_toward_rad) / speed_m_s
    lag_s = sx * x + sy * y
    return lag_s, midpoint


# ---------------------------------------------------------------------------
# Noise helpers
# ---------------------------------------------------------------------------

def _coloured_noise(n, rng, exponent=1.0):
    """Generate 1/f^exponent coloured noise (exponent=1 -> pink noise)."""
    white = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    freqs = np.fft.rfftfreq(n)
    freqs[0] = 1.0  # avoid division by zero at DC
    spectrum = np.fft.rfft(white.real)
    spectrum /= np.power(freqs, exponent / 2.0)
    spectrum[0] = 0.0  # zero DC
    coloured = np.fft.irfft(spectrum, n)
    # Normalise to unit variance
    coloured /= (coloured.std() + 1e-12)
    return coloured.astype(np.float32)


def _eregion_spikes(n, sample_rate_hz, rng,
                    n_spikes=5, spike_bandwidth_hz=0.5,
                    spike_amplitude=5.0):
    """Generate random narrow-band E-region spike bursts."""
    spikes = np.zeros(n, dtype=np.complex64)
    for _ in range(n_spikes):
        # Random timing (avoid first/last 5%)
        t_spike = rng.uniform(0.05 * n, 0.95 * n)
        dur_samples = int(rng.uniform(1, 4) * sample_rate_hz)  # 1-4s
        t0 = max(0, int(t_spike) - dur_samples // 2)
        t1 = min(n, t0 + dur_samples)
        # Random Doppler offset
        f_spike = rng.uniform(-3.0, 3.0)
        t_idx = np.arange(t0, t1) / sample_rate_hz
        burst = np.exp(1j * 2 * np.pi * f_spike * t_idx).astype(np.complex64)
        # Amplitude taper
        env = np.hanning(t1 - t0).astype(np.float32)
        spikes[t0:t1] += spike_amplitude * env * burst
    return spikes


# ---------------------------------------------------------------------------
# Main signal generation
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
    # Enhancement 1: asymmetric fading
    asymmetric_fading=False,
    # Enhancement 2: period chirp
    chirp_rate=0.0,          # fractional period change per hour (e.g. 0.1 = 10%/h)
    # Enhancement 3: second TID
    second_tid_amp_hz=0.0,
    second_tid_period_s=None,
    second_tid_phase_rad=0.0,
    # Enhancement 4: coloured noise
    coloured_noise_fraction=0.0,  # 0=pure AWGN, 1=pure 1/f
    # Enhancement 5: E-region spikes
    eregion_spikes=False,
    n_eregion_spikes=5,
    # Enhancement 6: carrier offset
    carrier_offset_hz=0.0,
    # Enhancement 7: time-varying SNR
    snr_variation_db=0.0,    # peak-to-peak SNR variation in dB
    snr_variation_period_s=None,  # period of SNR modulation
    rng=None,
):
    if rng is None:
        rng = np.random.default_rng(42)

    n = int(duration_s * sample_rate_hz)
    t = np.arange(n) / sample_rate_hz

    # ── Enhancement 2: period chirp ─────────────────────────────────────────
    # Period drifts linearly: T(t) = T0 * (1 + chirp_rate * t / 3600)
    # Integrated phase: phi(t) = 2*pi * integral(1/T(t)) dt
    if chirp_rate != 0.0:
        # Instantaneous frequency with linear chirp
        T_t = tid_period_s * (1.0 + chirp_rate * t / 3600.0)
        f_tid_inst = tid_amp_hz * np.sin(
            2 * np.pi * np.cumsum(1.0 / T_t) / sample_rate_hz + tid_phase_rad)
    else:
        f_tid_inst = tid_amp_hz * np.sin(
            2 * np.pi * t / tid_period_s + tid_phase_rad)

    # ── Enhancement 6: carrier offset ───────────────────────────────────────
    f_doppler = f_tid_inst + carrier_offset_hz

    # ── Enhancement 3: second TID ────────────────────────────────────────────
    if second_tid_amp_hz > 0.0:
        T2 = second_tid_period_s if second_tid_period_s else tid_period_s
        f_doppler = f_doppler + second_tid_amp_hz * np.sin(
            2 * np.pi * t / T2 + second_tid_phase_rad)

    # ── Realistic noise components ───────────────────────────────────────────
    if noise_type in ("realistic", "awgn"):
        if noise_type == "realistic":
            # Slow ionospheric background drift (linear)
            drift_rate = rng.normal(0, 0.002)
            f_doppler = f_doppler + drift_rate * t / 60.0
            # Slow sinusoidal background
            bg_period = rng.uniform(3 * 3600, 6 * 3600)
            bg_amp = rng.uniform(0.05, 0.3)
            bg_phase = rng.uniform(0, 2 * np.pi)
            f_doppler = f_doppler + bg_amp * np.sin(
                2 * np.pi * t / bg_period + bg_phase)

    # ── Integrate Doppler to phase ───────────────────────────────────────────
    doppler_phase = 2 * np.pi * np.cumsum(f_doppler) / sample_rate_hz

    # ── Enhancement 1: asymmetric fading ─────────────────────────────────────
    if noise_type == "realistic" or asymmetric_fading:
        n_fades = rng.integers(0, 3)
        amp_upper = np.ones(n)
        amp_lower = np.ones(n)
        for _ in range(n_fades):
            t_fade = rng.uniform(0.1 * duration_s, 0.9 * duration_s)
            tau_fade = rng.uniform(0.05 * duration_s, 0.15 * duration_s)
            depth = rng.uniform(0.3, 0.8)
            env = 1 - depth * np.exp(-((t - t_fade) / tau_fade) ** 2)
            # Upper and lower fade independently
            if rng.random() > 0.5:
                amp_upper *= env
            else:
                amp_lower *= env
        # Construct asymmetrically faded signal
        iq_upper = amp_upper * np.exp(+1j * doppler_phase)
        iq_lower = amp_lower * np.exp(-1j * doppler_phase)
        iq_clean = (iq_upper + iq_lower).astype(np.complex128)
    else:
        iq_clean = np.exp(1j * doppler_phase).astype(np.complex128)

    # ── Enhancement 7: time-varying SNR ─────────────────────────────────────
    if snr_variation_db > 0.0:
        tau_snr = snr_variation_period_s if snr_variation_period_s else 1800.0
        phi_snr = rng.uniform(0, 2 * np.pi)
        snr_db_t = snr_db + (snr_variation_db / 2) * np.sin(
            2 * np.pi * t / tau_snr + phi_snr)
        snr_linear_t = 10 ** (snr_db_t / 10.0)
        signal_power = np.mean(np.abs(iq_clean) ** 2)
        noise_std_t = np.sqrt(signal_power / (snr_linear_t * 2))
        noise = (noise_std_t *
                 (rng.standard_normal(n) + 1j * rng.standard_normal(n)))
    else:
        signal_power = np.mean(np.abs(iq_clean) ** 2)
        snr_linear = 10 ** (snr_db / 10.0)
        noise_power = signal_power / snr_linear
        noise_std = np.sqrt(noise_power / 2)
        noise = noise_std * (rng.standard_normal(n) +
                             1j * rng.standard_normal(n))

    # ── Enhancement 4: coloured noise blend ─────────────────────────────────
    if coloured_noise_fraction > 0.0:
        pink = _coloured_noise(n, rng, exponent=1.0)
        noise_power_total = np.mean(np.abs(noise) ** 2)
        pink_scaled = pink * np.sqrt(noise_power_total)
        noise = ((1 - coloured_noise_fraction) * noise +
                 coloured_noise_fraction * pink_scaled)

    iq = (iq_clean + noise).astype(np.complex64)

    # ── Enhancement 5: E-region spikes ──────────────────────────────────────
    if eregion_spikes:
        spikes = _eregion_spikes(n, sample_rate_hz, rng,
                                  n_spikes=n_eregion_spikes)
        iq = iq + spikes

    return iq
