# Synthetic Test Suite for psws-drf-tid-tools

End-to-end validation of the TID direction-of-arrival pipeline using
synthetic Digital RF (DRF) data with known ground truth.

## What this does

Generates synthetic I/Q recordings that mimic real HamSCI Grape/
WSPRDaemon station data, with a known TID embedded at a specified speed,
azimuth, period, and amplitude. Runs the full pipeline on these
recordings — DRF inspection, Doppler extraction, DOA inversion — and
compares the recovered parameters against the known ground truth.

This is the only way to validate the toolkit against a reference TID,
since real ionospheric events have no ground truth to compare against.

## Test conditions (20 representative cases)

| Category | Tests | Purpose |
|----------|-------|---------|
| Baseline | `nominal` | Clean AWGN, alias-safe speed — all methods should pass |
| Speed sweep | `fast_tid`, `slow_tid_south`, `slow_tid_alias` | Speed sensitivity and aliasing demo |
| Azimuth sweep | `az_south`, `az_east_alias`, `az_northwest` | Directional sensitivity |
| Period sweep | `period_60_compact`, `period_120`, `period_180` | 60/120/180-min periods |
| Amplitude | `weak_signal`, `strong_signal` | 0.1 and 1.0 Hz Doppler |
| SNR | `high_snr`, `low_snr`, `very_low_snr` | 40/10/5 dB |
| Noise type | `realistic_noise`, `realistic_low_snr` | Drift + fading vs AWGN |
| Array geometry | `wide_array_alias`, `mixed_4stn` | Different station arrays |
| Stress | `stress_worst` | Worst-case combination |

Tests marked `expect_pass=False` are **expected to fail** — they
demonstrate known toolkit limitations:

- **Alias demos** (`slow_tid_alias`, `az_east_alias`, `wide_array_alias`):
  when any station-pair lag exceeds half the TID period (T/2), the
  cross-correlation is inherently ambiguous. The test passes when the
  toolkit returns the wrong azimuth (confirming the alias).
- **Stress tests** (`very_low_snr`, `stress_worst`): conditions beyond
  the toolkit's reliable operating range.

## Files

```
synthetic_tests/
├── README.md               this file
├── synthetic_signal.py     TID signal model (I/Q generation, noise types)
├── synthetic_drf.py        DRF writer (generates HDF5 station directories)
├── test_conditions.py      20 test condition definitions + station arrays
├── run_tests.py            automated batch runner (no GUI required)
├── evaluate.py             pass/fail evaluation logic
├── conftest.py             pytest integration
├── test_pipeline.py        pytest test cases
├── .gitignore              excludes events/ from git
└── events/                 generated DRF data (created on first run)
    ├── README.md
    └── synthetic_<name>/   one directory per test condition
        ├── ground_truth.json   known parameters for comparison
        ├── <STATION>/ch0/      DRF I/Q data files
        └── <STATION>_<method>.csv  extracted Doppler (after first run)
```

## Requirements

```bash
pip install digital_rf pytest numpy scipy pandas matplotlib
```

The toolkit scripts (`tid_doa.py`, `drf_to_doppler.py`) must be on
the Python path. Run from inside `psws-tools-pr/synthetic_tests/` and
they will be found automatically via the parent directory.

## Quick start

```bash
cd ~/psws-tools-pr/synthetic_tests
source ../.venv/bin/activate

# Run one test (generates DRF on first run, ~30s)
python3 run_tests.py --test nominal --methods autocorr

# Run all 20 tests with autocorr (~30-40 min first run, ~5 min cached)
python3 run_tests.py --automated --methods autocorr

# Run with both autocorr and cwt
python3 run_tests.py --automated --methods autocorr,cwt

# List all test conditions
python3 run_tests.py --list
```

## pytest usage

```bash
# Run all tests (autocorr + cwt by default)
pytest test_pipeline.py -v

# Single method
pytest test_pipeline.py -v --method autocorr

# Specific tests
pytest test_pipeline.py -v -k "nominal or az_south"

# Skip alias demos and stress tests (only expect_pass=True)
pytest test_pipeline.py -v -m expect_pass

# Headless CI (no GUI methods)
PYTEST_METHODS=autocorr,cwt pytest test_pipeline.py -v
```

## Signal model

Each station's I/Q signal is:

```
I/Q(t) = exp(j * 2*pi * f_doppler(t) * t) + noise(t)

f_doppler(t) = amp_hz * sin(2*pi*t/period_s + phase_k)

phase_k = -2*pi * tau_k / period_s
tau_k   = slowness_vector . AE_position_k   (DOA geometry)
```

where `AE_position_k` is the azimuthal equidistant projection of the
station's IPP midpoint — exactly matching `tid_doa.py`'s geometry.

**Noise types:**
- `awgn`: additive white Gaussian noise only
- `realistic`: AWGN + slow ionospheric carrier drift + Gaussian fading
  envelopes at random times

## Key findings from the synthetic validation

From running all 20 conditions with autocorr extraction:

| Condition | Speed error | Azimuth error |
|-----------|-------------|---------------|
| Clean (AWGN, SNR ≥ 20 dB) | < 12% | < 5° |
| Realistic noise (drift + fading) | 15–20% | < 8° |
| High speed (≥ 600 m/s, 60s cadence) | up to 20% | < 5° |
| Sub-cycle window (180-min period, 2h window) | < 2% | < 2° |
| Very low SNR (5 dB) | ~40% | ~12° |

**Important findings:**

1. **Period aliasing** (lag > T/2) produces wrong azimuths regardless
   of `max_lag_seconds`. The new `[!] Aliasing risk` diagnostic in
   `tid_doa.py` flags when this condition is present.

2. **Sub-cycle periods** (180-min TID in a 2-hour window) perform
   better than theory predicts — the cross-correlation of a slow trend
   recovers accurate lags in clean conditions.

3. **Realistic noise is the dominant error source** for real events,
   contributing 15–20% speed uncertainty even at adequate SNR.

4. **Very low SNR (5 dB) does not trigger diagnostic flags** — the
   toolkit's five internal checks measure lag consistency, not signal
   quality. The new `[7] SNR` diagnostic addresses this by reading
   `snr_db` from each station's CSV.

## Pass/fail criteria

| Category | Speed threshold | Azimuth threshold |
|----------|----------------|-------------------|
| Clean (SNR ≥ 30 dB, AWGN) | 15% (high-speed: 22%) | 3° |
| Nominal (SNR ≥ 15 dB, AWGN) | 12% (high-speed: 18%) | 5° |
| Degraded (low SNR or realistic noise) | 20% (high-speed: 30%) | 8° |
| Alias demo (expect_pass=False) | azimuth error > 30° confirms alias | — |
| Stress (expect_pass=False) | error > threshold OR flags ≥ 2 | — |
