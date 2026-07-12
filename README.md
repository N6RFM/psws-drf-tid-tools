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

The toolkit calculations assume a planar wave, single-hop F-region propagation, and
vertical-incidence reflection at the great-circle midpoint between each receiving
station and the WWV transmitter. Station positions are projected using an azimuthal
equidistant projection (preserving great-circle distances from the array centroid)
for the DOA inversion. Results should be considered as informed estimates.

## What this toolkit does

Given Digital RF (DRF) I/Q recordings from several HamSCI Grape or
WSPRDaemon stations all recording the same WWV carrier, this toolkit
lets you:

- find which other stations were on the air during your event of interest
- inspect a DRF recording and identify the correct channel-num for comparative
  analysis
- extract Doppler-vs-time CSVs from raw I/Q using several methods:
  anchor-guided cwt-prophet, wave-fit, autocorr, and FFT peak-tracking
- render annotated Doppler spectrograms with optional overlay of
  extracted Doppler traces for visual method assessment
- run the complete analysis pipeline in one guided interactive session
  — as a terminal-based guided workflow, or a browser-based GUI
  dashboard for the automated methods
- run a full multi-station direction-of-arrival (DOA) analysis
- visualize results as stacked Doppler traces and array-geometry maps
- validate the pipeline against synthetic DRF data with known ground
  truth using the `synthetic_tests/` suite

The reference event is the **X1.9 solar flare and subsequent LSTID of
19 January 2026**, analyzed end-to-end with this toolkit.

---

## Quickstart

```bash
git clone https://github.com/N6RFM/psws-drf-tid-tools.git
cd psws-drf-tid-tools
pip install -r requirements.txt
```

A handful of packages in `requirements.txt` only affect specific
scripts or extraction methods rather than the whole toolkit --
`prophet` (the cwt-prophet extraction method, one of several
available), `streamlit` (the dashboard GUI), `cartopy` (nicer maps),
`astropy` and `madrigalWeb` (single-script dependencies) -- each
noted individually in the file itself. Everything installs together
with the one command above.

### Recommended: use a virtual environment

The toolkit's dependencies (particularly `digital_rf`, `cartopy`, and
older `numpy`/`scipy` constraints from upstream HamSCI tools) can
conflict with packages already installed on your system.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 check_install.py
```

`check_install.py` verifies every dependency this toolkit actually
imports is present, split into required (core scripts won't run at
all without these) and optional (specific features degrade without
these, everything else still works) -- worth running any time a venv
gets rebuilt from scratch, since a partial reinstall can otherwise go
unnoticed until a specific feature happens to be exercised and fails
with a confusing, buried error.

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

Download DRF data for the top candidates from https://pswsnetwork.eng.ua.edu/,
or automate this step with `download_companions.py`:

```bash
python3 download_companions.py --date 2026-01-19 \
    --stations N6RFM AA6BD W7LUX AC0G_ND
```

This resolves each station nickname to its PSWS Station ID, downloads
its DRF data via the PSWS download API, and organizes it into the
`<station>/ch0/...` layout the rest of the pipeline expects. See
`docs/COOKBOOK.md` for the full option list, or `MANUAL_TUTORIAL.md`
for the manual download steps if you'd rather use the web UI directly.

**A note on `ch0` and "channel-num", since these are easy to conflate.**
Every station's data lives in exactly one folder, always named `ch0`
-- that never changes, including for stations that record several
frequencies at once (rx888/WSPRDaemon/KA9Q-radio-style receivers).
"Channel-num" is *not* a second folder to find or download separately
-- it's a column index inside `ch0`'s own files. A station recording
9 simultaneous WWV frequencies still has just one `ch0` folder; those
9 frequencies are 9 parallel columns sharing one file, one download,
one common time axis, purely for storage convenience on the receiver's
end. Selecting "channel-num 4" tells every tool downstream (spectrogram
generation, extraction, everything) which column to read out of that
one shared folder -- it has no effect on what gets downloaded, and
there is never a `ch1`, `ch4`, etc. to look for. See
`docs/COOKBOOK.md`'s "How do I extract from a multi-channel-num
station?" for the practical side of this.

### Recommended: guided workflow

```bash
python3 tid_workflow.py \
    --event-dir /path/to/tid_event_20260119 \
    --stations N6RFM,AA6BD,W7LUX,AC0G_ND \
    --max-lag 30
```

The guided workflow handles all 8 steps interactively:

1. Station discovery and channel-num selection
2. Full-day spectrogram generation
3. TID window selection (interactive)
4. Zoomed spectrogram generation
5. Optional window refinement
6. Doppler extraction
7. Extraction output and visual assessment
8. Direction-of-arrival inversion with interactive drop-station loop

See **[`WORKFLOW_TUTORIAL.md`](WORKFLOW_TUTORIAL.md)** for a complete
walkthrough.

### GUI option: `tid_dashboard.py`

A browser-based control panel wrapping the full extraction → DOA →
Madrigal TEC cross-check pipeline behind one button: point it at an
event directory, pick a window (with a live spectrogram showing
exactly what you've selected), and run — auto-computing
`--doa-lags`/`--doa-speed`/`--doa-azimuth-from` for the TEC cross-check
instead of you typing them by hand.

```bash
pip install streamlit
streamlit run tid_dashboard.py
```

Then open the printed `http://localhost:8501` URL. Everything before
the "Run full pipeline" button — event window selection, station
coordinates, and channel confirmation for multi-channel/RX888-style
stations — happens live as you type, no need to click anything first.

**Extraction methods:** all are available from one dropdown —
`autocorr`, `cwt`, and `fft` run automatically with no further input;
`wave-fit`, `cwt-prophet`, and `spline` open `tid_spect_click.py`'s
own native window per station (the dashboard spawns the same tool
this page already documents, rather than reimplementing spectrogram
clicking in the browser) — click cycle points, fit, **press X to
export**, then close the window, and the dashboard picks up the
result automatically via `--event-json` and moves to the next
station. All stations in a given run use the same method; mixing
methods across stations isn't supported yet.

**Two real constraints on the interactive methods, stated plainly:**
this only works when Streamlit is running locally on the same machine
as the display (same reason the folder-browse button works — a
browser can't be granted access to a remote machine's desktop), and
the browser tab blocks while each native window is open, same as any
other slow step in the pipeline.

**Resumable, and shared with the CLI:** the dashboard reads and writes
the exact same `tid_workflow_state.json` file `tid_workflow.py --resume`
itself uses — a session started via one is fully resumable from the
other. Entering an event directory with existing saved progress shows
a summary of what's already done per station, with the option to
continue or start completely fresh (clearing the file, same as
`tid_workflow.py`'s own choice for this — and also deleting every
intermediate/derived file in the event directory, spectrograms,
extraction CSVs, config files, run logs and all, leaving only the
DRF station directories themselves untouched — shown explicitly
before it happens, given it's a real, irreversible filesystem
operation). Channel-num confirmation,
the event window, keystone-station selection, and — the part that
actually saves real time — extraction itself all persist this way:
a station already extracted in a prior run (dashboard or CLI, either
one) is reused rather than re-run, which matters since extraction is
the genuinely slow step. Returning to an event doesn't mean
re-confirming, re-selecting, or re-extracting things you already
settled. Every discovered station can also be individually excluded
or re-included for a given run (a multiselect right after the resume
summary) without touching that station's own saved progress —
dropping one today doesn't mean re-confirming it if you bring it back
tomorrow. `tid_workflow.py` itself is unmodified by any of this.

A few more details worth knowing: the keystone station is processed
first through every step (channel-num confirmation, extraction) —
the whole reason for selecting one. For interactive extraction
methods specifically, a separate "Clicking order" control lets you
directly pick which station's window opens first, rather than relying
on keystone selection as an indirect way to influence it. "Start
completely fresh" clears
the saved state but keeps your station exclusions, since a full
reset silently pulling an excluded station back into the active set
(forcing its channel-num confirmation all over again) turned out to
be genuinely disruptive rather than helpful. And the event window
actually sent to `tid_doa.py` is computed from the real overlap of
what was extracted for each station — not simply the window-selection
slider, which only guides where extraction happens — matching
`tid_workflow.py`'s own, more robust approach.

The Madrigal cross-check step is optional (toggle in the sidebar) and
can be skipped if you just want speed/azimuth.

For an event with more than 3 stations, a follow-up section lets you
exclude station(s) and re-run just the DOA fit (and optionally the TEC
cross-check) without redoing extraction — the same
`tid_doa.py --drop NAME` workflow used to isolate a bad station
(e.g. E-region contamination), but clickable.

### Manual step-by-step

For full control over each step, run the pipeline directly.
See **[`MANUAL_TUTORIAL.md`](MANUAL_TUTORIAL.md)** for the complete
step-by-step guide.

---

## Doppler Extraction Methods

`tid_spect_click.py` is the primary interactive extraction tool,
providing anchor-guided cwt-prophet, wave-fit, and plain spline
extraction with a visual spectrogram interface.

Six methods are available in total, in order of recommended
preference. `tid_dashboard.py`'s dropdown offers all of these
**except spline**, which requires the CLI directly (see note below):

| Method | Tool | User input | Best for |
|--------|------|-----------|----------|
| **Anchor-guided cwt-prophet** | `tid_spect_click.py` | E=accept auto-trace, or click carrier + X | All events; handles E-region contamination |
| **Wave-fit** | `tid_spect_click.py --wave-only` | Click cycle points + F to fit | Clean signals with ≥1.5 visible cycles |
| **Spline** | `tid_spect_click.py --no-prophet` | Click ≥2 anchor points + X to export | Irregular/non-sinusoidal traces a wave-fit model can't capture |
| **Autocorr** | `drf_to_doppler.py --method autocorr` | None (automated) | Clean signals; good general purpose |
| **FFT peak-tracking** | `drf_to_doppler.py --method fft` | None (automated) | Fast survey; default method |
| **CWT peak-tracking** | `drf_to_doppler.py --method cwt` | None (automated) | Multi-peak signals; alternative to FFT |

**Wave-fit vs. spline, precisely:** both are interactive and both use
`tid_spect_click.py`, but they're not variations of the same thing.
Wave-fit fits a single sinusoid through your clicked points (assumes
one clean oscillation); spline interpolates a curve directly through
your clicked anchor points with no assumption about shape at all —
useful when the real trace doesn't look like a clean sine wave.
Config files record whichever one was actually used as `"method":
"wave-fit"` or `"method": "spline"` respectively — they are not
interchangeable labels for the same output.

`drf_to_doppler.py` also supports `bandpass` and `sgolay-ridge`
extraction — special-case methods, not part of the primary 6 above.
`bandpass` is validated via `synthetic_tests/` (27/29 conditions
passing as expected, comparable accuracy to cwt/fft). `sgolay-ridge`
requires `--corridor`, a JSON file written by `tid_spect_click.py`
(press X in the GUI) — it refines an existing carrier track rather
than extracting one standalone, so it needs a prior interactive
session before it can run at all. Not currently covered by the
automated synthetic test suite for this reason.


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
│
├── tid_workflow.py             guided 8-step workflow
├── tid_quicklook.py            interactive TID window selector
├── tid_window_detector.py      automatic TID time-window detector
├── tid_spect_click.py          interactive spectrogram extraction
│                               (cwt-prophet and wave-fit; display required)
├── tid_guided_extract.py       interactive guided Doppler CSV correction
├── tid_dashboard.py            browser GUI, all extraction methods
├── drf_spectrogram.py          full-day and zoomed spectrograms
├── drf_to_doppler.py           automated Doppler extraction
│                               (fft, autocorr; also cwt, bandpass, sgolay-ridge)
├── drf_inspect.py              verify DRF metadata + channel-num
├── find_event_stations.py      companion-station discovery
├── download_companions.py      companion-station download + organize
├── tid_doa.py                  multi-station DOA inversion
├── tid_doa_config.py           interactive builder for tid_doa.py configs
├── tid_doa_residual.py         residual-subtraction second-wave diagnostic
├── tid_pair.py                 two-station Doppler cross-correlation analyzer
├── hf_int.py                   HF interferometry TID detection method
├── quality_summary.py          per-station Doppler quality metrics
├── tid_stack_plot.py           stacked Doppler comparison
├── tid_map.py                  array geometry map
├── run_madrigal_tools.py       combined Madrigal TEC + LSTID wrapper
├── fetch_ae_index.py           fetch + plot AE index (WDC Kyoto)
├── fetch_kp_index.py           fetch + plot Kp index (WDC Kyoto)
├── fetch_madrigal_tec.py       Madrigal GPS TEC retrieval + xcorr,
│                               with loop-closure peak disambiguation
├── evaluate_external.py        external space weather evaluation of DOA
│                               results (Kp/AE + guidance for manual sources)
│
├── docs/
│   ├── ASSESSING_RESULTS.md    understanding and validating DOA results
│   ├── EXTERNAL_EVALUATION.md  external space weather evaluation tools
│   ├── COOKBOOK.md             task-oriented recipes
│   ├── METHODOLOGY.md          signal processing details
│   └── TROUBLESHOOTING.md      failure modes and fixes
│
├── synthetic_tests/            end-to-end validation suite (known ground truth)
│   ├── README.md               suite documentation and usage
│   ├── run_tests.py            automated batch runner
│   ├── plot_spectrograms.py    synthetic DRF spectrogram visualisation
│   └── events/                 generated DRF data (gitignored, ~500MB)
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
- `requests`, `beautifulsoup4` (for `find_event_stations.py` and `download_companions.py`)
- `PyQt5`, `pyqtgraph`, `Pillow` (for interactive GUI tools)

Optional:
- `cartopy` for nicer `tid_map.py` output with state/country outlines
- `streamlit` for `tid_dashboard.py`. `python3-tk` (system package,
  not pip) is also needed for that dashboard's folder-browse button —
  optional, it falls back to manual path entry without it.

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
> https://github.com/N6RFM/psws-drf-tid-tools

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
