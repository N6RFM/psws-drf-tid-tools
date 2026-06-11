# psws-drf-tid-tools

**A Python pipeline for analyzing Traveling Ionospheric Disturbances (TIDs)
from HamSCI Grape Digital RF I/Q recordings.**

A Travelling Ionospheric Disturbance (TID) propagates over long distances, often caused by atmospheric
or geomagnetic events. TIDs generally propagate towards the equator during storms, and can disrupt GNSS/GPS
navigation, radio communications, and satellite operations.

This toolset provides citizen scientists, using receivers from the HAMSci Grape DRF family, a means
to obtain estimates of TID propagation speed and direction. 

Users are well advised to compare their HF based results to those obtained using other
complementary tools.  

* Geomagnetic indices like the Kp index and and the Auroral Electrojet (AE) Index may help identify
whether the disturbance is likely a quiet-time MSTID or a storm-driven auroral LSTID.

* The hamsci_LSTID_detection toolkit (https://github.com/HamSCI/hamsci_LSTID_detection) provides an independent automated method
for detecting LSTIDs from amateur radio spot data — RBN, PSKReporter, and WSPRNet.

* GNSS TEC data from CEDAR Madrigal Database provides spatial wave structure, propagation
direction, wavelength, and speed estimates. This toolset includes scripts to help obtain those 
types of information for comparative purposes. 

## A Note of Caution

The toolkit calculations assume a planar wave, flat-earth geometry, single hop F region propagation, 
and vertical-incidence reflection at the path midpoint relative to each receiving station. Results 
should be considered as informed estimates.

## What this toolkit does

Given Digital RF (DRF) I/Q recordings from several HamSCI Grape or
WSPRDaemon stations all recording the same WWV carrier, this toolkit
lets you:

- find which other stations were on the air during your event of interest
- inspect a DRF recording and identify the correct subchannel for comparative
  analysis
- extract Doppler-vs-time CSVs from raw I/Q using four methods:
  anchor-guided cwt-prophet (recommended), autocorr,
  CWT, or wave-fit
- render annotated Doppler spectrograms with optional overlay of
  extracted Doppler traces for visual method assessment
- run the complete analysis pipeline in one guided interactive session
- run a full multi-station direction-of-arrival (DOA) analysis
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

### Before you begin — find companion stations

If you only have data from your own station, discover which other
HamSCI PSWS stations recorded the same event:

```bash
python3 find_event_stations.py \
    --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 \
    --my-call N6RFM
```

Download DRF data for the top candidates from https://pswsnetwork.eng.ua.edu/

### Recommended: guided workflow

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
6. Doppler extraction
7. Extraction output and visual assessment
8. Direction-of-arrival inversion with interactive drop-station loop

See **[`WORKFLOW_TUTORIAL.md`](WORKFLOW_TUTORIAL.md)** for a complete
walkthrough.

### Manual step-by-step

For full control over each step, run the pipeline directly.
See **[`MANUAL_TUTORIAL.md`](MANUAL_TUTORIAL.md)** for the complete
step-by-step guide.

---

## Doppler Extraction Methods

`tid_spect_click.py` is the primary interactive extraction tool.
provides experimental Kalman-filter-based extraction.

Four methods are available, in order of recommended preference:

| Method | Tool | User input | Best for |
|--------|------|-----------|----------|
| **Anchor-guided cwt-prophet** | tid_spect_click.py | E=accept auto-trace, or click carrier + X | All events, especially E-region contamination |
| **Wave-fit** | tid_spect_click.py --wave-only | Click cycle points + F to fit | Clean signals with ≥1.5 visible cycles |
| **Autocorr** | drf_to_doppler.py --method autocorr | None | Clean signals|
| **FFT** | drf_to_doppler.py --method fft | None | Clean signals, fast survey |


See `MANUAL_TUTORIAL.md` for the full extraction method comparison
and `docs/METHODOLOGY.md` for the mathematical details of each method.

## External Evaluation Tools

After obtaining a DOA result, you may corroborate it
with independent space weather data. See
[docs/EXTERNAL_EVALUATION.md](docs/EXTERNAL_EVALUATION.md) for tools,
usage examples, and required parameters.

---

## Documentation

For background on interpreting HamSCI PSWS Doppler spectrograms in general —
ionospheric features, propagation modes, solar events, and artifacts — see the
**[HamSCI PSWS Spectrogram Atlas](https://spectrogram-docs.readthedocs.io/en/latest/index.html)**.
This toolkit focuses specifically on one feature from that atlas: Travelling
Ionospheric Disturbances (TIDs) and their direction-of-arrival analysis.


- **[`ASSESSING_RESULTS.md`](docs/ASSESSING_RESULTS.md)** — understanding and validating DOA results.
- **[`CHANGELOG.md`](CHANGELOG.md)** — version history.
- **[`CONTRIBUTORS.md`](CONTRIBUTORS.md)** — N6RFM and G3ZIL.
- **[`EXTERNAL_EVALUATION.md`](docs/EXTERNAL_EVALUATION.md)** — external space weather evaluation tools.
- **[`MANUAL_TUTORIAL.md`](MANUAL_TUTORIAL.md)** — step-by-step manual
  pipeline for users who want full control over each tool.
- **[`WORKFLOW_TUTORIAL.md`](WORKFLOW_TUTORIAL.md)** — complete guided
  workflow walkthrough using `tid_workflow.py`. **Start here.**

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
├── drf_spectrogram.py          spectrograms + --overlay for visual assessment
├── drf_to_doppler.py           Doppler extraction (autocorr/cwt/fft)
├── drf_inspect.py              verify DRF metadata + subchannel
├── find_event_stations.py      companion-station discovery
├── tid_doa.py                  multi-station DOA inversion (--drop to exclude stations)
├── tid_stack_plot.py           stacked Doppler comparison
├── tid_map.py                  array geometry map
├── evaluate_external.py        external space weather evaluation
├── fetch_ae_index.py           fetch + plot AE index (WDC Kyoto)
├── fetch_madrigal_tec.py        Madrigal GPS TEC retrieval + xcorr
│
├── docs/
│   ├── ASSESSING_RESULTS.md         technical basis for DOA estimates
│   ├── EXTERNAL_EVALUATION.md       external space weather evaluation tools
│   ├── COOKBOOK.md                  task-oriented recipes

│   ├── METHODOLOGY.md               signal processing details
│   └── TROUBLESHOOTING.md           failure modes and fixes
│
└── examples/
    ├── README.md               event descriptions and data access
    ├── event_20260119.json     Jan 2026 4-station DOA config
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
> Version 2.4.x https://github.com/N6RFM/psws-drf-tid-tools

---

## Acknowledgments

- Gwyn Griffiths (G3ZIL) for development of the autocorr TID extractor parameters, helping me to analyze TID events and for being a great mentor, Elmer, and friend.
- Nathaniel Frissell (W2NAF),University of Scranton, the visionary and founder of HamSCI, the Ham Radio Science Citizen Investigation initiative. [https://hamsci.org]
- John Gibbons (N8OBJ), Case Western Reserve University, for designing the Grape 1 receiver and it's progeny. [https://www.youtube.com/watch?v=y7w0dLhCfZI]
- Rob Robinett (AI6VN) for developing of the WSPRDaemon software package and webiste. [https://www.wsprdaemon.org/]
- Phil Karn, (KA9Q) for the KA9Q Radio software package, enabling the RX-888 (and other SDRs) to perform accurate and reliable data collection.[https://github.com/ka9q/ka9q-radio]
- Bill Engelke (AB4EJ), University of Alabama, Chief Architect of the HamSCi PSWS Central Database System and for DRF data spectrogram plotting code, [https://github.com/HamSCI/DRF_processing].
- Phil Ericson (W1PJE), Observatory Director) and the MIT Haystack Observatory staff for the Digital RF format [https://github.com/MITHaystack/digital_rf] and for the Madrigal toolsets, which are part   of the observatory's global receiver network [http://millstonehill.haystack.mit.edu/.
- The operators of every Grape and WSPRDaemon DRF station whose data makes these analysis possible!

This toolkit was developed collaboratively with Anthropic's Claude AI.

---

## Contact

Bob Mattaliano (N6RFM) — n6rfm1@gmail.com

Issues and pull requests welcome on
[GitHub](https://github.com/N6RFM/psws-drf-tid-tools).

---

## AI Assistance

This project was developed in collaboration with
[Claude](https://claude.ai) (Anthropic). See [CONTRIBUTORS.md](CONTRIBUTORS.md).
