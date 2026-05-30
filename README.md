# psws-drf-tid-tools

**A Python pipeline for analyzing Traveling Ionospheric Disturbances (TIDs)
from HamSCI Grape Digital RF I/Q recordings.**

## Travelling Ionospheric Disturbance (TID)

A wave-like disturbance in the ionosphere that propagates over long
distances, often caused by atmospheric or geomagnetic events. TIDs
propagate towards the equator during storms, and can disrupt GNSS/GPS
navigation, radio communications, and satellite operations.

## IMPORTANT CAVEAT

There are numerous ways to extract TID information from DRF data and/or spectrograms.

The goals of this toolset are 1) allow citizen scientists a means to explore TIDs and
2) obtain estimates of TID propagation speed and direction. The extraction tools available
here serve as place holders until more refined and accurate TID extraction tools become
available and integrated into this toolset. In short, results obtained may not be accurate.
At this time, consider this work experimental in nature. Several user selectable options
for TID extraction are included.

## What this toolkit does


Given Digital RF (DRF) I/Q recordings from several HamSCI Grape or
WSPRDaemon stations all recording the same WWV carrier, this toolkit
lets you:

- find which other stations were on the air during your event of interest
- inspect a DRF recording and identify the correct subchannel for 10 MHz
- extract Doppler-vs-time CSVs from raw I/Q using multiple methods:
  interactive spline (cwt-prophet, recommended), FFT, autocorr (G3ZIL method),
  CWT, or wave-fit (sine reconstruction from user-clicked cycle points)
- render annotated Doppler spectrograms with optional overlay of
  extracted Doppler traces for visual method validation
- run the complete pipeline in one guided interactive session
- run a full multi-station direction-of-arrival (DOA) inversion
- visualize results as stacked Doppler traces and array-geometry maps

The reference event is the **X1.9 solar flare and subsequent LSTID of
19 January 2026**, analyzed end-to-end with this toolkit.

---

## Quickstart

```bash
git clone https://github.com/N6RFM/psws-drf-tid-tools.git
cd psws-drf-tid-tools
pip install -r requirements.txt
pip install -r requirements-optional.txt   # for nicer maps
```

### Recommended: use a virtual environment

The toolkit's dependencies (particularly `digital_rf`, `cartopy`, and
older `numpy`/`scipy` constraints from upstream HamSCI tools) can
conflict with packages already installed on your system.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-optional.txt
python3 drf_inspect.py --version
```

When done: `deactivate`. To resume: `source .venv/bin/activate`.

---

## Analysis Workflow

### Step 0: find companion stations

If you only have data from your own station, discover which other
HamSCI PSWS stations recorded the same event:

```bash
python3 find_event_stations.py \
    --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 \
    --my-call N6RFM
```

Download DRF data for the top candidates from https://pswsnetwork.eng.ua.edu/

### Recommended: guided workflow (new in v2.0)

```bash
python3 tid_workflow.py \
    --event-dir /path/to/tid_event_20260119 \
    --stations N6RFM,AA6BD,W7LUX,AC0G_ND \
    --max-lag 30
```

The guided workflow handles all 8 steps interactively:

1. Station discovery and subchannel selection
2. Full-day spectrogram generation
3. TID window selection (interactive)
4. Zoomed spectrogram generation
5. Optional window refinement
6. Doppler extraction (interactive spline via cwt-prophet, wave-fit, or automated)
7. Extraction output and visual validation
8. Direction-of-arrival inversion with interactive drop-station loop

State is saved after each step — use `--resume` to continue an
interrupted session. `--max-lag` limits the xcorr search to prevent
period aliasing (recommended: ~1/3 of expected TID period).

See **[`WORKFLOW_TUTORIAL.md`](WORKFLOW_TUTORIAL.md)** for a complete
walkthrough.

### Manual step-by-step

For full control over each step, or to run only part of the pipeline:

```bash
# 1. Inspect subchannels
python3 drf_inspect.py --all ./n6rfm --frequency 10

# 2. Full-day spectrogram
python3 drf_spectrogram.py ./n6rfm --subchannel 0 \
    --output n6rfm_fullday.png --start 00:00 --end 24:00 \
    --ylim=-5,5 --dpi 100 --callsign N6RFM

# 3. Select TID window interactively
python3 tid_quicklook.py --spectrogram n6rfm_fullday.png

# 4. Zoomed spectrogram
python3 drf_spectrogram.py ./n6rfm --subchannel 0 \
    --output n6rfm_zoom.png \
    --window n6rfm_fullday_window.json \
    --ylim=-5,5 --dpi 150 --callsign N6RFM

# 5a. Interactive spline extraction (cwt-prophet — recommended)
#     Pass 0 auto-runs on open. Click F-region carrier to correct
#     excursions. P=re-run  X=export  W=wave-fit  F=fit  R=reset  Q=quit
python3 tid_spect_click.py --spectrogram n6rfm_zoom.png \
    --name N6RFM --drf-dir ./n6rfm --subchannel 0

# 5b. Wave-fit only (skip Prophet, fit sine to clicked cycle points)
#     Best when >=1.5 cycles visible in window
python3 tid_spect_click.py --spectrogram n6rfm_zoom.png \
    --name N6RFM --seg-start 0.0 --seg-end 2.0 --wave-only

# 5c. Automated extraction (clean stations, no GUI needed)
python3 drf_to_doppler.py ./n6rfm --subchannel 0 \
    --start 2026-01-19T00:00:00 --end 2026-01-19T02:00:00 \
    --decim-seconds 60 --method fft --output n6rfm_fft_tid.csv

# 6. Run DOA (use --max-lag ~20 min for LSTID with ~60 min period)
python3 tid_doa.py event.json --max-lag 20
```

See **[`MANUAL_TUTORIAL.md`](MANUAL_TUTORIAL.md)** for the complete
step-by-step guide including all stations, event.json format, IPP
coordinate calculation, and result interpretation.

---

## Doppler Extraction Methods

`tid_spect_click.py` is the primary interactive extraction tool.
`drf_to_doppler.py` provides automated extraction via `--method`:

- `cwt-prophet` **(recommended)**: interactive spline extraction via
  `tid_spect_click.py`. Pass 0 auto-runs CWT+Prophet to seed the
  spline; click the F-region carrier to correct excursions. Handles
  E-region contamination and wrong-peak lock. Use for any event where
  contamination is present or automated methods give inconsistent lags.
- `sgolay-ridge`: interactive corridor-based extraction (legacy).
  Precursor to cwt-prophet; still available but superseded.
- `fft`: FFT-based carrier tracker. Fully automated. Good for clean
  stations with no E-region contamination.
- `autocorr`: Lag-1 complex autocorrelation instantaneous-frequency
  estimator (G3ZIL method). 2-3x smoother output than fft.
- `cwt`: CWT multi-peak tracker with linear extrapolation.
- `wave-fit` (`--wave-only`): user clicks multiple points along the
  visible TID cycle; tool fits A·sin(2π/T·t + φ) + offset to those
  points and reconstructs the full window. No Prophet run needed.
  Works best when ≥1.5 full cycles are visible. Each station
  independently estimates its own period — handles dispersive TIDs.
  Exports `{stn}_wave_tid.csv` for use with `tid_doa.py`.

**xcorr aliasing note:** for LSTID events with ~60 min period, set
`--max-lag 20` (minutes) to prevent alias peak lock. See
`ASSESSING_RESULTS.md` for details.

See `MANUAL_TUTORIAL.md` for the full extraction method comparison.

---

## Documentation

- **[`WORKFLOW_TUTORIAL.md`](WORKFLOW_TUTORIAL.md)** — complete guided
  workflow walkthrough using `tid_workflow.py`. **Start here.**
- **[`MANUAL_TUTORIAL.md`](MANUAL_TUTORIAL.md)** — step-by-step manual
  pipeline for users who want full control over each tool.
- **[`CHANGELOG.md`](CHANGELOG.md)** — version history.
- **[`CONTRIBUTORS.md`](CONTRIBUTORS.md)** — N6RFM and G3ZIL.

---

## What's in this repo

```
psws-drf-tid-tools/
├── README.md
├── CHANGELOG.md
├── WORKFLOW_TUTORIAL.md        guided workflow tutorial (start here)
├── MANUAL_TUTORIAL.md          manual step-by-step tutorial
├── CONTRIBUTORS.md
├── LICENSE                     MIT
├── CITATION.cff
├── requirements.txt
├── requirements-optional.txt
│
├── tid_workflow.py             guided 8-step workflow (NEW in v2.0)
├── tid_quicklook.py            interactive TID window selector
├── tid_spect_click.py          interactive spline extraction (cwt-prophet + wave-fit)
├── drf_spectrogram.py          spectrograms + --overlay for validation
├── drf_to_doppler.py           Doppler extraction (fft/autocorr/cwt/sgolay-ridge)
├── drf_inspect.py              verify DRF metadata + subchannel
├── find_event_stations.py      companion-station discovery
├── tid_doa.py                  multi-station DOA inversion
├── tid_stack_plot.py           stacked Doppler comparison
├── tid_map.py                  array geometry map
│
├── docs/
│   ├── ASSESSING_RESULTS.md    technical basis for DOA estimates
│   ├── COOKBOOK.md             task-oriented recipes
│   ├── METHODOLOGY.md          signal processing details
│   └── TROUBLESHOOTING.md      failure modes and fixes
│
└── examples/
    ├── README.md               event descriptions and data access
    ├── event_20260119.json     Jan 2026 4-station DOA config
    ├── event_20240517.json     May 2024 3-station DOA config
    ├── event_20260119_doa_report.pdf  full DOA analysis report
    └── tid_event_20260119/     extracted CSVs, spectrograms, run logs
```

Every script accepts `--help` and `--version`.

---

## Dependencies

Core (required):
- Python 3.10 or newer
- `digital_rf` 2.6+ (MIT Haystack Observatory)
- `numpy`, `scipy`, `pandas`, `matplotlib`
- `requests`, `beautifulsoup4` (for `find_event_stations.py`)
- `PyQt5`, `pyqtgraph`, `Pillow` (for interactive GUI tools)

Optional:
- `cartopy` for nicer `tid_map.py` output with state/country outlines

---

## License

MIT. See [LICENSE](LICENSE).

---

## Citation

If you use this toolkit in a publication, please cite it. The
[CITATION.cff](CITATION.cff) file lets GitHub generate citations
automatically (look for "Cite this repository" in the sidebar), or:

> Mattaliano, R. (N6RFM) and Griffiths, G. (G3ZIL). 2026.
> *psws-drf-tid-tools: a Python pipeline for analyzing Traveling
> Ionospheric Disturbances from HamSCI Grape Digital RF I/Q recordings.*
> Version 2.3.x. https://github.com/N6RFM/psws-drf-tid-tools

---

## Acknowledgments

- Gwyn Griffiths (G3ZIL) for co-development of the autocorr extractor,
  collaborative analysis of the Jan 2026 and May 2024 LSTID events,
  and extensive validation of sign conventions and lag interpretation
- The HamSCI / PSWS infrastructure developers https://hamsci.org/
- Bill Engelke (AB4EJ), University of Alabama, for the original DRF
  processing and spectrogram plotting code
  https://github.com/HamSCI/DRF_processing
- MIT Haystack Observatory for the Digital RF format
  https://github.com/MITHaystack/digital_rf
- The operators of every Grape and WSPRDaemon DRF station whose data
  made this analysis possible

The toolkit was developed collaboratively with Anthropic's Claude AI.

---

## Contact

Bob Mattaliano (N6RFM) — n6rfm1@gmail.com

Issues and pull requests welcome on
[GitHub](https://github.com/N6RFM/psws-drf-tid-tools).
