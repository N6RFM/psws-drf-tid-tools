# Synthetic Test Suite for psws-drf-tid-tools

End-to-end validation of the TID direction-of-arrival pipeline using
synthetic Digital RF (DRF) data with known ground truth.

## What this does

Generates synthetic I/Q recordings that mimic real HamSCI Grape/
WSPRDaemon station data, with a known TID embedded at a specified speed,
azimuth, period, and amplitude. Runs the full pipeline on these
recordings — DRF generation, Doppler extraction, DOA inversion — and
compares the recovered parameters against the known ground truth.

This is the only way to validate the toolkit against a reference TID,
since real ionospheric events have no independently known ground truth.

## Extraction methods

`drf_to_doppler.py` supports seven extraction methods:

| Method | CLI flag | Automated? | Notes |
|--------|----------|-----------|-------|
| FFT peak-tracking | `--method fft` | ✅ Yes | Default; fast survey |
| Autocorrelation | `--method autocorr` | ✅ Yes | Good for clean signals |
| CWT multi-peak | `--method cwt` | ✅ Yes | Handles E-region better |
| Adaptive bandpass | `--method bandpass` | ✅ Yes | Suppresses fixed interferers |
| Savitzky-Golay ridge | `--method sgolay-ridge` | ✅ Yes | Smooth ridge tracking |
| Anchor-guided cwt-prophet | `--method cwt-prophet` | ⚠️ Semi | Requires user anchor clicks in `tid_spect_click.py` |
| Wave-fit / spline | `--method spline` | ⚠️ Semi | Requires user interaction in `tid_spect_click.py` |

The synthetic test suite runs automated methods only (`fft`, `autocorr`,
`cwt`, `bandpass`). The semi-automated methods (`cwt-prophet`, `spline`)
require a display and user interaction — they are tested separately by
running `tid_spect_click.py` interactively on the synthetic DRF.

**Note on naming:** `fft` and `cwt` are distinct methods — do not use
them interchangeably. `fft` picks the single loudest FFT peak each
block; `cwt` uses a continuous wavelet transform to find multiple
candidate peaks and selects the best one using temporal continuity.

## Test conditions (20 representative cases)

| Category | Tests | Purpose |
|----------|-------|---------|
| Baseline | `nominal` | 500 m/s, 30°, 60-min, clean — all methods should pass |
| Speed | `fast_tid`, `slow_tid_south`, `slow_tid_alias` | Speed range + aliasing demo |
| Azimuth | `az_south`, `az_east_alias`, `az_northwest` | Directional sensitivity |
| Period | `period_60_compact`, `period_120`, `period_180` | 60/120/180-min periods |
| Amplitude | `weak_signal`, `strong_signal` | 0.1 and 1.0 Hz Doppler |
| SNR | `high_snr`, `low_snr`, `very_low_snr` | 40/10/5 dB |
| Noise | `realistic_noise`, `realistic_low_snr` | Drift + fading vs AWGN |
| Geometry | `wide_array_alias`, `mixed_4stn` | Different station arrays |
| Stress | `stress_worst` | Worst-case combination |

Tests marked `expect_pass=False` demonstrate known toolkit limitations:
- **Alias demos**: lag > T/2 → wrong azimuth (confirms aliasing constraint)
- **Stress tests**: conditions beyond the reliable operating range

## Files

```
synthetic_tests/
├── README.md                  this file
├── synthetic_signal.py        TID I/Q signal model (AWGN + realistic noise)
├── synthetic_drf.py           DRF writer (generates HDF5 station directories)
├── test_conditions.py         20 test condition definitions + array geometry
├── run_tests.py               automated batch runner (no GUI required)
├── evaluate.py                tiered pass/fail evaluation logic
├── plot_spectrograms.py       Doppler spectrogram visualisation
├── conftest.py                pytest integration
├── test_pipeline.py           pytest test cases
├── .gitignore                 excludes events/ and plots/ from git
└── events/                    generated DRF data (created on first run)
    ├── README.md
    └── synthetic_<name>/      one directory per test condition
        ├── ground_truth.json  known parameters for comparison
        ├── <STATION>/ch0/     DRF I/Q HDF5 files
        └── <STATION>_<method>.csv  extracted Doppler (after first run)
```

## Requirements

```bash
pip install digital_rf pytest numpy scipy pandas matplotlib
```

The toolkit scripts (`tid_doa.py`, `drf_to_doppler.py`) must be in the
parent directory (`psws-drf-tid-tools/`). Run from inside
`psws-drf-tid-tools/synthetic_tests/` and they are found automatically.

## Quick start

```bash
cd ~/psws-tools-pr/synthetic_tests
source ../.venv/bin/activate

# List all 20 test conditions
python3 run_tests.py --list

# Run one test (~30s to generate DRF, ~5s cached)
python3 run_tests.py --test nominal --methods autocorr

# Run with multiple methods
python3 run_tests.py --test nominal --methods autocorr,cwt,fft

# Run all 20 tests (~30-40 min first run, ~5 min cached)
python3 run_tests.py --automated --methods autocorr

# Run all tests with all automated methods
python3 run_tests.py --automated --methods autocorr,cwt,fft,bandpass
```

## Spectrogram visualisation

```bash
# Plot spectrogram for all stations in one test (saves to plots/)
python3 plot_spectrograms.py --test nominal

# Overlay extracted Doppler traces on the spectrogram
python3 plot_spectrograms.py --test nominal --overlay autocorr,cwt,fft

# Plot all generated test conditions
python3 plot_spectrograms.py --all

# Plot specific stations only
python3 plot_spectrograms.py --test realistic_noise --stations SYN_AA6BD,SYN_N6RFM
```

## pytest usage

```bash
# Run all tests with autocorr (default)
pytest test_pipeline.py -v --method autocorr

# Run with multiple methods
pytest test_pipeline.py -v --method autocorr,cwt,fft

# Run specific tests
pytest test_pipeline.py -v --method autocorr -k "nominal or az_south"

# Skip alias demos and stress tests
pytest test_pipeline.py -v --method autocorr -m expect_pass

# Headless CI
PYTEST_METHODS=autocorr,cwt pytest test_pipeline.py -v
```

## Signal model

```
I/Q(t) = exp(j * 2*pi * integral(f_doppler) dt) + noise(t)

f_doppler(t) = amp_hz * sin(2*pi*t/period_s + phase_k)
phase_k      = -2*pi * tau_k / period_s
tau_k        = slowness_vector · AE_projected_position_k
```

**Noise types:**
- `awgn`: additive white Gaussian noise only
- `realistic`: AWGN + slow ionospheric carrier drift + Gaussian fading

## Key findings from synthetic validation

| Condition | Speed error | Azimuth error |
|-----------|-------------|---------------|
| Clean AWGN, SNR ≥ 20 dB | < 12% | < 5° |
| Realistic noise (drift + fading) | 15–20% | < 8° |
| High speed (≥ 600 m/s, 60s cadence) | up to 20% | < 5° |
| Sub-cycle (180-min period, 2h window) | < 2% | < 2° |
| Very low SNR (5 dB) | ~40% | ~12° |

Key findings:
1. **Period aliasing** (lag > T/2) produces wrong azimuths — see `[!]` diagnostic
2. **Sub-cycle periods** more robust than expected
3. **Realistic noise** is the dominant error source for real events
4. **Very low SNR** passes all 5 core flags silently — see `[7]` SNR diagnostic
5. **CWT and FFT** produce virtually identical results on synthetic data
   (CWT advantage appears mainly with real E-region contamination)

## Pass/fail thresholds

| Category | Speed | Azimuth |
|----------|-------|---------|
| Clean (SNR ≥ 30 dB, AWGN) | 15% (high-speed: 22%) | 3° |
| Nominal (SNR ≥ 15 dB, AWGN) | 12% (high-speed: 18%) | 5° |
| Degraded (low SNR or realistic) | 20% (high-speed: 30%) | 8° |
| Alias demo (`expect_pass=False`) | azimuth error > 30° confirms alias | — |
| Stress (`expect_pass=False`) | error > threshold OR flags ≥ 2 | — |
