#!/usr/bin/env python3
"""
synthetic_drf.py -- Generate a complete synthetic DRF event directory
for testing psws-drf-tid-tools end-to-end.

Creates one DRF station directory per station, each containing:
  <station>/
    ch0/
      rf@<timestamp>.h5   (I/Q data files)
      metadata/           (center_frequencies, callsign, lat/lon)

The generated event has a known TID (speed, azimuth, period, amplitude)
whose phase delays are encoded in the per-station Doppler time series.
Running the full pipeline on this directory should recover the input
parameters within tolerance.

Usage:
    python3 synthetic_drf.py --config test_conditions.py::nominal
    python3 synthetic_drf.py --list-tests
    python3 synthetic_drf.py --all --output-root ~/psws-tools-pr/synthetic_tests/events
"""
import argparse
import json
import math
import pathlib
import sys
import numpy as np

try:
    import digital_rf as drf
    _HAVE_DRF = True
except ImportError:
    _HAVE_DRF = False

from test_conditions import ARRAYS, TEST_CONDITIONS
from synthetic_signal import (
    generate_iq, compute_station_lag, great_circle_midpoint,
    WWV_LAT, WWV_LON
)

# DRF parameters
SAMPLE_RATE_HZ = 1000          # 1 ksps (Grape-like)
F_CARRIER_HZ   = 10.0e6        # 10 MHz WWV
EVENT_START_UTC = 1737244800   # 2026-01-19T00:00:00Z (arbitrary synthetic epoch)
EVENT_DURATION_MULTIPLIER = 2.0  # event window = 2x the TID period


# ---------------------------------------------------------------------------
# DRF writer
# ---------------------------------------------------------------------------
def write_station_drf(output_dir, station, iq_samples, start_unix_s,
                      sample_rate_hz, f_carrier_hz):
    """Write DRF + metadata for one station."""
    import digital_rf as drf_lib
    import numpy as np

    ch_dir = pathlib.Path(output_dir) / station["name"] / "ch0"
    ch_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = ch_dir / "metadata"
    meta_dir.mkdir(exist_ok=True)

    start_sample = int(start_unix_s * sample_rate_hz)

    # Write I/Q data
    writer = drf_lib.DigitalRFWriter(
        str(ch_dir),
        dtype=np.complex64,
        subdir_cadence_secs=3600,
        file_cadence_millisecs=3600000,  # 1-hour files -- reduces spectrogram boundary artifacts
        start_global_index=start_sample,
        sample_rate_numerator=int(sample_rate_hz),
        sample_rate_denominator=1,
        is_complex=True,
        num_subchannels=1,
    )
    writer.rf_write(iq_samples)
    writer.close()

    # Write metadata
    mwriter = drf_lib.DigitalMetadataWriter(
        str(meta_dir),
        subdir_cadence_secs=3600,
        file_cadence_secs=3600,
        sample_rate_numerator=int(sample_rate_hz),
        sample_rate_denominator=1,
        file_name="metadata",
    )
    mwriter.write(start_sample, {
        "center_frequencies": np.array([f_carrier_hz]),
        "callsign": station["name"],
        "latitude": station["lat"],
        "longitude": station["lon"],
        "antenna": "Grape v1 synthetic",
        "synthetic": True,
    })


def generate_event(test_name, output_root):
    """Generate a complete synthetic event directory for one test condition."""
    if not _HAVE_DRF:
        sys.exit("digital_rf not installed: pip install digital_rf")

    # Find test condition
    tc = next((t for t in TEST_CONDITIONS if t[0] == test_name), None)
    if tc is None:
        sys.exit(f"Unknown test: {test_name}. Use --list-tests to see available.")

    tc_tuple = tc
    name, speed_m_s, az_from_deg, period_min, amp_hz, snr_db, noise_type, array_name, expect_pass = tc_tuple[:9]
    tc_notes = tc_tuple[9] if len(tc_tuple) > 9 else ""

    period_s    = period_min * 60.0
    duration_s  = int(period_s * EVENT_DURATION_MULTIPLIER)
    stations    = ARRAYS[array_name]

    event_dir = pathlib.Path(output_root) / f"synthetic_{name}"
    # If event_dir already exists with ground_truth.json, skip regeneration
    gt_existing = event_dir / "ground_truth.json"
    if gt_existing.exists():
        import json as _json
        gt = _json.loads(gt_existing.read_text())
        # Update notes in case test conditions changed
        gt["notes"] = tc_notes
        gt_existing.write_text(_json.dumps(gt, indent=2))
        print(f"  [reusing existing DRF: {event_dir}]")
        return event_dir, gt
    event_dir.mkdir(parents=True, exist_ok=True)

    # Compute IPP midpoints for all stations (needed for centroid)
    midpoints = [great_circle_midpoint(WWV_LAT, WWV_LON, s["lat"], s["lon"])
                 for s in stations]

    # Generate I/Q for each station
    rng = np.random.default_rng(42)
    station_cfgs = []

    print(f"Generating: {name}")
    print(f"  Speed={speed_m_s} m/s  Az={az_from_deg}deg  "
          f"Period={period_min}min  Amp={amp_hz}Hz  "
          f"SNR={snr_db}dB  Noise={noise_type}")
    print(f"  Array={array_name} ({len(stations)} stations)")
    print(f"  Duration={duration_s}s ({duration_s/3600:.2f}h)")

    for i, station in enumerate(stations):
        lag_s, midpoint = compute_station_lag(
            station["lat"], station["lon"],
            speed_m_s, az_from_deg, midpoints
        )
        phase_rad = -2 * math.pi * lag_s / period_s  # negative: positive lag = wave arrives later = phase behind

        print(f"  {station['name']:15s} lag={lag_s:+8.1f}s  "
              f"phase={math.degrees(phase_rad):+7.1f}deg  "
              f"mid=({midpoint[0]:.2f},{midpoint[1]:.2f})")

        # Build enhanced parameters based on test name
        _kw = dict(
            duration_s=duration_s,
            sample_rate_hz=SAMPLE_RATE_HZ,
            f_carrier_hz=F_CARRIER_HZ,
            tid_amp_hz=amp_hz,
            tid_period_s=period_s,
            tid_phase_rad=phase_rad,
            snr_db=snr_db,
            noise_type=noise_type,
            rng=rng,
        )
        if name == 'two_wave':
            # Second TID: 200 m/s from 270deg, 30% amplitude
            _lag2, _ = compute_station_lag(
                station['lat'], station['lon'], 200, 270, midpoints)
            _phase2 = -2 * math.pi * _lag2 / period_s
            _kw.update(second_tid_amp_hz=amp_hz * 0.30,
                       second_tid_period_s=period_s,
                       second_tid_phase_rad=_phase2)
        elif name == 'two_wave_strong':
            # Second TID at 50% amplitude (comparable to primary)
            _lag2, _ = compute_station_lag(
                station['lat'], station['lon'], 200, 270, midpoints)
            _phase2 = -2 * math.pi * _lag2 / period_s
            _kw.update(second_tid_amp_hz=amp_hz * 0.50,
                       second_tid_period_s=period_s,
                       second_tid_phase_rad=_phase2)
        elif name == 'period_chirp':
            _kw.update(chirp_rate=0.10)  # 10% period change per hour
        elif name == 'eregion':
            _kw.update(eregion_spikes=True, n_eregion_spikes=8)
        elif name == 'coloured_noise':
            _kw.update(coloured_noise_fraction=0.7)  # 70% pink, 30% AWGN
        elif name == 'snr_fading':
            _kw.update(snr_variation_db=20.0,
                       snr_variation_period_s=1800.0)  # 10-30 dB, 30-min period
        elif name == 'carrier_offset':
            _kw.update(carrier_offset_hz=0.08)
        elif noise_type == 'realistic':
            _kw.update(asymmetric_fading=True)
        iq = generate_iq(**_kw)

        write_station_drf(
            event_dir, station, iq,
            EVENT_START_UTC, SAMPLE_RATE_HZ, F_CARRIER_HZ
        )

        station_cfgs.append({
            "name": station["name"],
            "lat": station["lat"],
            "lon": station["lon"],
            "true_lag_s": lag_s,
        })

    # Write ground truth JSON
    t_start = EVENT_START_UTC
    t_end   = EVENT_START_UTC + duration_s
    ground_truth = {
        "test_name":       name,
        "true_speed_m_s":  speed_m_s,
        "true_az_from_deg": az_from_deg,
        "true_period_min": period_min,
        "true_amp_hz":     amp_hz,
        "snr_db":          snr_db,
        "noise_type":      noise_type,
        "array_name":      array_name,
        "expect_pass":     expect_pass,
        "event_start_utc": f"{'1970-01-01T00:00:00Z'[:-1]}"[:-1],  # placeholder
        "event_start_unix": t_start,
        "event_end_unix":   t_end,
        "stations":        station_cfgs,
        "pass_criteria": {
            "speed_error_pct_max": 10 if expect_pass else 20,
            "azimuth_error_deg_max": 5 if expect_pass else 15,
        },
    }
    # Fix the event start UTC string
    import datetime
    ground_truth["event_start_utc"] = datetime.datetime.utcfromtimestamp(
        t_start).strftime("%Y-%m-%dT%H:%M:%SZ")
    ground_truth["event_end_utc"] = datetime.datetime.utcfromtimestamp(
        t_end).strftime("%Y-%m-%dT%H:%M:%SZ")

    gt_path = event_dir / "ground_truth.json"
    ground_truth["notes"] = tc_notes
    gt_path.write_text(json.dumps(ground_truth, indent=2))
    print(f"  Ground truth: {gt_path}")
    print(f"  Event dir:    {event_dir}")
    return event_dir, ground_truth


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Generate synthetic DRF event directories for testing")
    ap.add_argument("--test", metavar="NAME",
                    help="Generate one specific test condition")
    ap.add_argument("--all", action="store_true",
                    help="Generate all 20 test conditions")
    ap.add_argument("--list-tests", action="store_true",
                    help="List all available test conditions")
    ap.add_argument("--output-root", default=str(pathlib.Path(__file__).parent / "events"),
                    help="Root directory for generated events (default: ~/psws-tools-pr/synthetic_tests/events)")
    args = ap.parse_args()

    if args.list_tests:
        print(f"{'Name':25} {'Speed':>6} {'Az':>4} {'Per':>4} "
              f"{'Amp':>5} {'SNR':>4} {'Noise':>10} {'Array':>22} {'Pass?':>6}")
        print("-" * 95)
        for tc in TEST_CONDITIONS:
            name, spd, az, per, amp, snr, noise, arr, exp = tc
            print(f"{name:25} {spd:6} {az:4} {per:4} "
                  f"{amp:5.1f} {snr:4} {noise:>10} {arr:>22} {str(exp):>6}")
        return

    if args.all:
        for tc in TEST_CONDITIONS:
            generate_event(tc[0], args.output_root)
            print()
        return

    if args.test:
        generate_event(args.test, args.output_root)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
