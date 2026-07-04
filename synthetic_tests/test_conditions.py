#!/usr/bin/env python3
"""
test_conditions.py -- 20 representative synthetic test conditions for
psws-drf-tid-tools end-to-end validation.

Each condition is a tuple:
  (name, speed_m_s, az_from_deg, period_min, amp_hz,
   snr_db, noise_type, array_name, expect_pass, notes)

expect_pass=False means the test is expected to fail -- either because
the conditions are genuinely beyond the toolkit's capability (e.g. sub-
cycle period, very low SNR) or because the geometry creates inherent
cross-correlation aliasing (max pairwise lag > period/2).

Aliasing condition: when any station-pair lag exceeds period/2, the
cross-correlation of a sinusoidal signal is ambiguous -- the correlator
cannot distinguish lag=L from lag=L-T. This is NOT a code bug; it is
a fundamental constraint of the cross-correlation method applied to
quasi-sinusoidal TIDs.

Alias-safe tests use either:
  - High speed (short lags relative to period)
  - South/SE azimuth (wave travels along N-S axis, E-W array lags small)
  - Compact array (short baselines, small lags)
  - Long period (large T/2 threshold)
"""

# Station array definitions (receiver lat/lon)
ARRAYS = {
    "array_3stn_eastwest": [
        {"name": "SYN_AA6BD", "lat": 35.06,   "lon": -85.13},
        {"name": "SYN_N6RFM", "lat": 32.94,   "lon": -97.21},
        {"name": "SYN_W7LUX", "lat": 35.10,   "lon": -111.71},
    ],
    "array_4stn_mixed": [
        {"name": "SYN_JJMP",    "lat": 40.88,  "lon": -75.00},
        {"name": "SYN_KV0S_MO", "lat": 38.88,  "lon": -92.42},
        {"name": "SYN_AC0G_ND", "lat": 46.875, "lon": -96.833},
        {"name": "SYN_N6RFM5",  "lat": 32.94,  "lon": -97.21},
    ],
    "array_compact": [
        {"name": "SYN_A", "lat": 38.0, "lon": -97.0},
        {"name": "SYN_B", "lat": 42.5, "lon": -97.0},
        {"name": "SYN_C", "lat": 38.0, "lon": -91.5},
    ],
    "array_wide": [
        {"name": "SYN_A", "lat": 35.0, "lon": -80.0},
        {"name": "SYN_B", "lat": 35.0, "lon": -100.0},
        {"name": "SYN_C", "lat": 47.0, "lon": -90.0},
    ],
}

# Pass/fail criteria
CRITERIA_STRICT = {"speed_pct": 12, "azimuth_deg": 5}   # expect_pass=True
CRITERIA_LOOSE  = {"speed_pct": 20, "azimuth_deg": 15}  # expect_pass=False (stress)

# fmt: off
# (name, speed, az, period_min, amp_hz, snr_db, noise, array, expect_pass, notes)
TEST_CONDITIONS = [
    # ── Baseline ──────────────────────────────────────────────────────────
    ("nominal",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Baseline: alias-safe speed (500 m/s), clean AWGN, 2-cycle window"),

    # ── Speed sweep (alias-safe at 60-min: need speed>=500 for E-W array) ─
    ("fast_tid",
     800, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Fast LSTID upper bound, alias-safe"),

    ("slow_tid_south",
     150, 180, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Slow TID (150 m/s) from due south: E-W array lag small, alias-safe"),

    ("slow_tid_alias",
     150, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", False,
     "ALIAS DEMO: 150 m/s from NNE, max lag 4232s > T/2 1800s -- "
     "expect wrong lag peak, toolkit should flag high RMS residual"),

    # ── Azimuth sweep ──────────────────────────────────────────────────────
    ("az_south",
     300, 180, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Due south: E-W baselines contribute little, N-S baselines dominate"),

    ("az_east_alias",
     300, 90, 60, 0.5, 20, "awgn", "array_3stn_eastwest", False,
     "ALIAS DEMO: due east, max lag 4021s > T/2 -- entire E-W baseline "
     "ambiguous"),

    ("az_northwest",
     500, 315, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "NW propagation, alias-safe at 500 m/s"),

    # ── Period sweep ───────────────────────────────────────────────────────
    ("period_60_compact",
     300, 30, 60, 0.5, 20, "awgn", "array_compact", True,
     "60-min period, compact array (baselines ~500km): alias-safe at 300 m/s"),

    ("period_120",
     300, 30, 120, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "120-min period: 1 cycle in 2-hour window, T/2=3600s >> max lag 2116s"),

    ("period_180",
     300, 30, 180, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "180-min period, sub-cycle (0.67 cycles): cross-correlation of slow "
     "trend still recovers good result -- toolkit more robust than expected"),

    # ── Amplitude sweep ────────────────────────────────────────────────────
    ("weak_signal",
     500, 30, 60, 0.1, 20, "awgn", "array_3stn_eastwest", True,
     "Weak TID (0.1 Hz Doppler amplitude), alias-safe speed"),

    ("strong_signal",
     500, 30, 60, 1.0, 20, "awgn", "array_3stn_eastwest", True,
     "Strong TID (1.0 Hz), alias-safe speed"),

    # ── SNR sweep ──────────────────────────────────────────────────────────
    ("high_snr",
     500, 30, 60, 0.5, 40, "awgn", "array_3stn_eastwest", True,
     "Clean signal (40 dB SNR) -- all methods should pass easily"),

    ("low_snr",
     500, 30, 60, 0.5, 10, "awgn", "array_3stn_eastwest", True,
     "Near-threshold SNR (10 dB)"),

    ("very_low_snr",
     500, 30, 60, 0.5, 5, "awgn", "array_3stn_eastwest", False,
     "STRESS: below-threshold SNR (5 dB) -- expect failures"),

    # ── Noise type ─────────────────────────────────────────────────────────
    ("realistic_noise",
     500, 30, 60, 0.5, 20, "realistic", "array_3stn_eastwest", True,
     "Realistic noise: AWGN + ionospheric drift + fading"),

    ("realistic_low_snr",
     500, 30, 60, 0.5, 10, "realistic", "array_3stn_eastwest", True,
     "Realistic noise + low SNR (10 dB)"),

    # ── Array geometry ─────────────────────────────────────────────────────
    ("wide_array_alias",
     300, 30, 60, 0.5, 20, "awgn", "array_wide", False,
     "ALIAS DEMO: wide array (~2000km baselines), 300 m/s, 60-min period "
     "-- max lag exceeds T/2"),

    ("mixed_4stn",
     509, 137, 60, 0.5, 20, "awgn", "array_4stn_mixed", True,
     "4-station mixed geometry (June 6 array), 509 m/s from 137 deg"),

    # ── Stress tests ───────────────────────────────────────────────────────
    ("stress_worst",
     150, 90, 120, 0.1, 5, "realistic", "array_compact", False,
     "STRESS: slow+east+weak+low-SNR+realistic -- expect all methods fail"),

    # ── Enhanced realism conditions ──────────────────────────────────────
    ("two_wave",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Two superimposed TIDs: primary 500 m/s @ 30deg + secondary 200 m/s @ 270deg "
     "at 30% amplitude. Primary wave should be recoverable by DOA."),

    ("two_wave_strong",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Two TIDs at 50% amplitude ratio: primary still recoverable (3.2% speed "
     "error in testing). Second wave detectable via tid_doa_residual.py."),

    ("period_chirp",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "TID period drifts linearly from 54 to 66 min over 2h (10%/h chirp). "
     "Tests period spread diagnostic [6] and extractor robustness."),

    ("eregion",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", False,
     "STRESS: E-region spikes (8 random bursts). autocorr/fft fail "
     "(33% error); cwt-prophet expected to pass via spike rejection."),

    ("coloured_noise",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "1/f (pink) noise instead of flat AWGN. More realistic background spectrum."),

    ("snr_fading",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Time-varying SNR: sinusoidal modulation 10-30 dB over 30-min period. "
     "Tests extractor robustness to fading signal quality."),

    # ── Additional SNR conditions ─────────────────────────────────────────
    ("snr_8db",
     500, 30, 60, 0.5, 8, "awgn", "array_3stn_eastwest", False,
     "SNR at exactly the [7] diagnostic POOR threshold (8 dB AWGN). "
     "Calibrates whether the flag threshold is meaningful for DOA."),

    ("realistic_8db",
     500, 30, 60, 0.5, 8, "realistic", "array_3stn_eastwest", False,
     "STRESS: 8 dB + realistic noise (drift + fading). "
     "Combination of poor SNR and ionospheric noise."),

    ("carrier_offset",
     500, 30, 60, 0.5, 20, "awgn", "array_3stn_eastwest", True,
     "Carrier DC offset +0.08 Hz on all stations (DRF calibration error). "
     "Tests whether extractor DC bias affects DOA accuracy."),
]
# fmt: on

if __name__ == "__main__":
    from synthetic_signal import compute_station_lag, great_circle_midpoint, WWV_LAT, WWV_LON
    print(f"{'Test':25} {'Speed':>5} {'Az':>4} {'Per':>4} "
          f"{'Max lag':>8} {'T/2':>6} {'Alias':>6} {'Pass':>5}  Notes")
    print("-" * 100)
    for tc in TEST_CONDITIONS:
        name, spd, az, per, amp, snr, noise, arr, exp, notes = tc
        period_s = per * 60
        stations = ARRAYS[arr]
        mids = [great_circle_midpoint(WWV_LAT, WWV_LON, s["lat"], s["lon"])
                for s in stations]
        lags = []
        for s in stations:
            lag, _ = compute_station_lag(s["lat"], s["lon"], spd, az, mids)
            lags.append(lag)
        n = len(stations)
        max_pw = max(abs(lags[j]-lags[i]) for i in range(n) for j in range(i+1,n))
        alias = max_pw > period_s/2
        print(f"{name:25} {spd:5} {az:4} {per:4} "
              f"{max_pw:8.0f} {period_s/2:6.0f} {str(alias):>6} {str(exp):>5}  "
              f"{notes[:40]}")
