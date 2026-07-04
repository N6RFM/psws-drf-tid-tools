# Synthetic Test Suite for psws-drf-tid-tools

End-to-end validation of the TID direction-of-arrival pipeline using
synthetic Digital RF (DRF) data with known ground truth.

**Current suite: 29 test conditions, 26/29 pass with autocorr.**

## What this does

Generates synthetic I/Q recordings that mimic real HamSCI Grape/
WSPRDaemon station data, with a known TID embedded at a specified
speed, azimuth, period, amplitude, and noise type. Runs the full
pipeline on these recordings and compares the recovered parameters
against the known ground truth.

Since real ionospheric events have no independently known ground
truth, this is the only way to rigorously validate the toolkit.

---

## Ground truth table (all 27 test conditions)

| # | Name | Speed (m/s) | From (°) | Period (min) | Amp (Hz) | SNR (dB) | Noise | Array | Pass? |
|---|------|-------------|----------|--------------|----------|----------|-------|-------|-------|
| 1 | `nominal` | 500 | 30 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 2 | `fast_tid` | 800 | 30 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 3 | `slow_tid_south` | 150 | 180 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 4 | `slow_tid_alias` | 150 | 30 | 60 | 0.5 | 20 | AWGN | EW-3stn | **no** |
| 5 | `az_south` | 300 | 180 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 6 | `az_east_alias` | 300 | 90 | 60 | 0.5 | 20 | AWGN | EW-3stn | **no** |
| 7 | `az_northwest` | 500 | 315 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 8 | `period_60_compact` | 300 | 30 | 60 | 0.5 | 20 | AWGN | compact | yes |
| 9 | `period_120` | 300 | 30 | 120 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 10 | `period_180` | 300 | 30 | 180 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 11 | `weak_signal` | 500 | 30 | 60 | 0.1 | 20 | AWGN | EW-3stn | yes |
| 12 | `strong_signal` | 500 | 30 | 60 | 1.0 | 20 | AWGN | EW-3stn | yes |
| 13 | `high_snr` | 500 | 30 | 60 | 0.5 | 40 | AWGN | EW-3stn | yes |
| 14 | `low_snr` | 500 | 30 | 60 | 0.5 | 10 | AWGN | EW-3stn | yes |
| 15 | `very_low_snr` | 500 | 30 | 60 | 0.5 | 5 | AWGN | EW-3stn | **no** |
| 16 | `realistic_noise` | 500 | 30 | 60 | 0.5 | 20 | realistic | EW-3stn | yes |
| 17 | `realistic_low_snr` | 500 | 30 | 60 | 0.5 | 10 | realistic | EW-3stn | yes |
| 18 | `wide_array_alias` | 300 | 30 | 60 | 0.5 | 20 | AWGN | wide | **no** |
| 19 | `mixed_4stn` | 509 | 137 | 60 | 0.5 | 20 | AWGN | 4stn | yes |
| 20 | `stress_worst` | 150 | 90 | 120 | 0.1 | 5 | realistic | compact | **no** |
| 21 | `two_wave` | 500 | 30 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 22 | `two_wave_strong` | 500 | 30 | 60 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 23 | `period_chirp` | 500 | 30 | 60→66 | 0.5 | 20 | AWGN | EW-3stn | yes |
| 24 | `eregion` | 500 | 30 | 60 | 0.5 | 20 | AWGN+spikes | EW-3stn | **no** |
| 25 | `coloured_noise` | 500 | 30 | 60 | 0.5 | 20 | 1/f | EW-3stn | yes |
| 26 | `snr_fading` | 500 | 30 | 60 | 0.5 | 10–30 | AWGN | EW-3stn | yes |
| 27 | `carrier_offset` | 500 | 30 | 60 | 0.5+0.08 | 20 | AWGN | EW-3stn | yes |
| 28 | `snr_8db` | 500 | 30 | 60 | 0.5 | 8 | AWGN | EW-3stn | **no** |
| 29 | `realistic_8db` | 500 | 30 | 60 | 0.5 | 8 | realistic | EW-3stn | **no** |

**"From (°)"** = true bearing the wave comes FROM (0°=N, 90°=E, 180°=S, 270°=W).

**"Pass?"** = whether the toolkit is expected to recover the correct
result for automated methods (autocorr, fft, cwt). Tests marked **no**
are deliberately outside the reliable operating range and demonstrate
known limitations.

### Station arrays

| Array | Stations | Baseline | Notes |
|-------|----------|----------|-------|
| EW-3stn | SYN_AA6BD, SYN_N6RFM, SYN_W7LUX | ~1200 km E-W | Geometry from Jan 2026 event |
| compact | SYN_A, SYN_B, SYN_C | ~500 km | Short baselines, alias-safe |
| wide | SYN_A, SYN_B, SYN_C | ~2000 km | Long baselines, alias-prone |
| 4stn | SYN_JJMP, SYN_KV0S_MO, SYN_AC0G_ND, SYN_N6RFM5 | ~1000 km mixed | 4-station mixed N-S/E-W geometry |

### Enhanced conditions (tests 21-27)

| Test | Enhancement | What it tests |
|------|-------------|---------------|
| `two_wave` | Second TID at 200 m/s / 270° / 30% amplitude | Primary wave recovery with superimposed wave |
| `two_wave_strong` | Second TID at 50% amplitude | Primary still recoverable; second wave detectable via `tid_doa_residual.py` |
| `period_chirp` | Period drifts linearly 60→66 min over 2h | Extractor robustness to slowly varying period |
| `eregion` | 8 random E-region spike bursts per station | Spike rejection: autocorr fails, cwt-prophet expected to pass |
| `coloured_noise` | 70% pink (1/f) noise, 30% AWGN | Realistic noise spectrum |
| `snr_fading` | SNR varies 10→30 dB sinusoidally (30-min period) | Time-varying signal quality |
| `carrier_offset` | +0.08 Hz DC offset on all stations | DRF calibration error robustness |
| `snr_8db` | 8 dB AWGN (exactly at [7] POOR threshold) | Calibrates whether SNR diagnostic threshold is meaningful |
| `realistic_8db` | 8 dB + realistic noise | Combination stress: poor SNR + ionospheric noise |

---

## Files

```
synthetic_tests/
├── README.md                  this file
├── synthetic_signal.py        TID I/Q signal model (all noise/enhancement types)
├── synthetic_drf.py           DRF writer (generates HDF5 station directories)
├── test_conditions.py         27 test condition definitions + array geometry
├── run_tests.py               automated batch runner + interactive command helper
├── evaluate.py                tiered pass/fail evaluation (per method, per condition)
├── plot_spectrograms.py       Doppler spectrogram visualisation
├── conftest.py                pytest CI integration
├── test_pipeline.py           pytest test cases
├── .gitignore                 excludes events/ and plots/ from git
└── events/                    generated DRF data (~700MB, created on first run)
    └── synthetic_<name>/
        ├── ground_truth.json  known parameters for comparison
        ├── <STATION>/ch0/     DRF I/Q HDF5 files
        └── <STATION>_<method>.csv  extracted Doppler (created on first run)
```

---

## Requirements

```bash
pip install digital_rf pytest numpy scipy pandas matplotlib
```

---

## Quick start — automated methods

Automated methods (autocorr, fft, cwt, bandpass) run without user
interaction and are suitable for CI.

```bash
cd ~/psws-tools-pr/synthetic_tests
source ../.venv/bin/activate

# List all 27 test conditions with ground truth
python3 run_tests.py --list

# Run one test (~30-60s to generate DRF on first run, ~5s cached)
python3 run_tests.py --test nominal --methods autocorr

# Run with multiple automated methods
python3 run_tests.py --test nominal --methods autocorr,cwt,fft

# Run all 27 tests with autocorr (~45 min first run, ~8 min cached)
python3 run_tests.py --automated --methods autocorr

# Generate spectrogram for visual inspection
python3 plot_spectrograms.py --test nominal
eog plots/nominal/SYN_AA6BD_spectrogram.png
```

---

## Quick start — interactive methods (cwt-prophet, wave-fit)

Interactive methods require a display and user clicks on the spectrogram.
The workflow for each test condition is:

### Step 1: Generate DRF and spectrogram

```bash
# Generate DRF (automated extraction first ensures DRF exists)
python3 run_tests.py --test nominal --methods autocorr

# Generate spectrogram using drf_spectrogram.py (NOT plot_spectrograms.py)
# drf_spectrogram.py produces the format tid_spect_click.py expects
cd ~/psws-tools-pr
python3 drf_spectrogram.py \
    synthetic_tests/events/synthetic_nominal/SYN_AA6BD \
    --subchannel 0 --start 00:00 --end 02:00 \
    --ylim=-1,1 \
    --output /tmp/syn_aa6bd.png
```

Repeat `drf_spectrogram.py` for each station (SYN_N6RFM, SYN_W7LUX).

### Step 2: Get the exact commands

```bash
cd synthetic_tests
python3 run_tests.py --show-commands --test nominal
```

This prints the exact `tid_spect_click.py` command for each station
and method, noting whether a sidecar `_axes.json` is available.

### Step 3: Run cwt-prophet or wave-fit

Run each printed command. The spectrogram opens with the true TID
Doppler shown as a **red dashed line** — use it as your reference.

**For cwt-prophet:**
- Press **E** to accept the auto-detected trace
- Or click on the carrier to anchor, then press **E**

**For wave-fit (`--wave-only`):**
- Click **5 or more points** on the bright carrier band
- Spread clicks across the full window (t=0 to t=end)
- Click peaks, troughs, and zero-crossings
- Press **F** to fit — a dialog asks "how many cycles did you span?"
  Count your peak-to-peak intervals and enter the number
  (period-hint is pre-filled — just confirm if correct)
- Check the blue fitted curve covers the full window and follows the carrier
- Press **A** to accept, **W** to redo, **Q** to auto-accept and exit

Output CSV is saved alongside the spectrogram PNG. The test runner
copies it automatically to the events directory.

### Step 4: Evaluate

```bash
python3 run_tests.py --test nominal --methods cwt-prophet
python3 run_tests.py --test nominal --methods spline
```

---

## Understanding pass/fail

### For expect_pass=True tests (automated methods)

| Tier | Speed threshold | Azimuth threshold | When applied |
|------|----------------|-------------------|--------------|
| Clean | 15% | 3° | SNR ≥ 30 dB, AWGN |
| Nominal | 12% | 5° | SNR ≥ 15 dB, AWGN |
| Degraded | 20% | 8° | Low SNR or realistic noise |
| Two-wave | 18% | 5° | Two superimposed TIDs |
| Chirp | 22% | 8° | Period drift |

High-speed TIDs (≥ 600 m/s) get 1.5× speed threshold due to quantization
error at 60-second cadence.

### For expect_pass=False tests

These tests are expected to **fail** — they demonstrate known toolkit
limitations:

| Category | Pass condition | Tests |
|----------|---------------|-------|
| Alias demo | Azimuth error > 30° (wrong-period lag confirmed) | `slow_tid_alias`, `az_east_alias`, `wide_array_alias` |
| Stress | Speed error > threshold OR flags ≥ 2 | `very_low_snr`, `stress_worst`, `eregion` |

### For manual methods (cwt-prophet, wave-fit)

Speed threshold 25%, azimuth threshold 15° — wider than automated
methods to account for click-precision variability.

---

## pytest usage

```bash
# Run all tests with default methods (autocorr, cwt, fft)
pytest test_pipeline.py -v

# Run with specific methods
pytest test_pipeline.py -v --method autocorr

# Run only expect_pass=True tests
pytest test_pipeline.py -v --method autocorr -m expect_pass

# Run only alias demos
pytest test_pipeline.py -v --method autocorr -m alias_demo

# Headless CI
PYTEST_METHODS=autocorr,fft pytest test_pipeline.py -q
```

---

## Key findings from validation

| Condition | Speed error | Azimuth error | Interpretation |
|-----------|-------------|---------------|----------------|
| AWGN, SNR ≥ 20 dB | ~5% | ~1° | Baseline accuracy |
| Realistic noise | 15–20% | 5–8° | Dominant real-world error source |
| Two waves (30%) | ~14% | ~0° | Primary wave recoverable |
| Two waves (50%) | ~3% | ~4° | Primary still dominant |
| Period chirp (10%/h) | ~19% | ~6° | Period drift degrades speed |
| E-region spikes | ~33% | ~9° | autocorr fails; cwt-prophet should pass |
| 1/f noise | ~5% | ~1° | Same as AWGN for autocorr |
| Time-varying SNR | ~5% | ~1° | Minimal impact on autocorr |
| Carrier offset +0.08 Hz | ~5% | ~1° | Cancels in cross-correlation |
| Sub-cycle (180-min, 2h window) | ~0.3% | ~1° | More robust than expected |
| Period aliasing (lag > T/2) | wrong azimuth | 113–144° error | Physical constraint, not a bug |
| 8 dB SNR (AWGN) | ~36% | ~10° | Fails silently — [7] diagnostic cannot detect this gap |
| 8 dB + realistic noise | ~49% | ~45° | Complete failure; run multiple methods to check |
