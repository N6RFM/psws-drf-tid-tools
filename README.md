# psws-drf-tid-tools

**A Python pipeline for analyzing Traveling Ionospheric Disturbances (TIDs)
from HamSCI Grape Digital RF I/Q recordings.**

## Travelling Ionospheric Disturbance (TID)

A wave-like disturbance in the ionosphere that propagates over long
distances, often caused by atmospheric or geomagnetic events. TIDs
propagate towards the equator during storms, and can disrupt GNSS/GPS
navigation, radio communications, and satellite operations.

## What this toolkit does

Given Digital RF (DRF) I/Q recordings from several HamSCI Grape or
WSPRDaemon stations all recording the same WWV carrier, this toolkit
lets you:

- find which other stations were on the air during your event of interest
- inspect a DRF recording and identify the correct subchannel for 10 MHz
- extract Doppler-vs-time CSVs from raw I/Q using FFT or complex
  autocorrelation (G3ZIL method)
- render annotated Doppler spectrograms with optional overlay of
  extracted Doppler traces for visual method validation
- detect candidate TID windows automatically
- run two-station cross-correlation or full multi-station
  direction-of-arrival (DOA) inversion
- choose FFT or autocorr extraction per station based on visual
  inspection, with choices recorded in the run log
- visualize results as stacked Doppler traces and array-geometry maps

The reference event is the **X1.9 solar flare and subsequent LSTID of
19 January 2026**, analyzed end-to-end with this toolkit. The completed
case-study writeup is at
https://spectrogram-docs.readthedocs.io/en/latest/index.html.

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

```bash
# 1. Identify the TID region of interest at your reference station.
python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_survey.png \
    --ylim=-2,2 \
    --callsign "N6RFM/5" --grid "EM12jw"

# 2. Extract Doppler with both FFT and autocorr, overlay on spectrogram
#    to choose which method better tracks the carrier.
python3 drf_to_doppler.py ./n6rfm \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 --method fft \
    --output n6rfm_fft.csv --plot n6rfm_fft.png

python3 drf_to_doppler.py ./n6rfm \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 --method autocorr \
    --output n6rfm_autocorr.csv

python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_overlay.png \
    --annotate "00:00,01:15,Analysis window" \
    --overlay "n6rfm_fft.csv:FFT" \
    --overlay "n6rfm_autocorr.csv:Autocorr:#FF9800"
# Legend shows: per-trace SNR and std; inter-method r and RMS diff.
# r > 0.95, RMS < 0.10 Hz -> both equivalent, use FFT (default).
# See docs/METHODOLOGY.md Step 1b for the full decision guide.

# 3. Find companion stations.
python3 find_event_stations.py --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 --my-call "N6RFM/5"

# 4. After downloading DRF tarballs from PSWS, verify each station.
python3 drf_inspect.py --all . --frequency 10

# 5. Extract Doppler CSV for each companion (repeat step 2 per station,
#    recording chosen method in event.json).

# 6. Build the DOA event config. Include "method" field per station.
# Example event.json station entry:
#   {"name": "N6RFM", "file": "n6rfm.csv", "method": "fft",
#    "lat": 32.94, "lon": -97.21}

# 7. Run the direction-of-arrival inversion.
python3 tid_doa.py event.json
# Run log written to runs/<timestamp>_run.log, includes method per station.

# 8. Make the report figures.
python3 drf_spectrogram.py ./n6rfm --output spectrogram.png \
    --annotate "00:00,01:15,DOA analysis window"
python3 tid_stack_plot.py --config event.json --output stack.png
python3 tid_map.py --config event.json --output map.png \
    --azimuth-toward 190 --speed 193
```

---

## Semi-automated workflow

[`analyze_event.sh`](analyze_event.sh) is an interactive driver that
runs the full pipeline, pausing at the points that require human
judgment:

- **Pause 1:** confirm or override the auto-proposed TID time window
- **Pause 2:** pick companion stations
- **Pause 3:** confirm tarballs downloaded and extracted
- **Per-station method selection (Stages 3 and 8):** for each station,
  both FFT and autocorr are extracted, an overlay spectrogram is shown,
  and you choose which method better tracks the carrier. Choices are
  recorded in `station_methods.txt` and written into `event.json`.
- **Pause 4:** quality-check per-station Doppler plots

```bash
analyze_event.sh \
    --date 2026-01-19 \
    --my-call "N6RFM/5" --my-grid "EM12jw" \
    --my-lat 32.94 --my-lon -97.21 \
    --my-station ./n6rfm
```

**Resume menu:** re-running with an existing state file shows a
numbered menu (0–12) to jump to any stage — useful when data is
already downloaded and you only want to re-run DOA or re-choose a
method. Use `--reset` to start fresh.

See [`docs/AUTOMATION.md`](docs/AUTOMATION.md) for full details.

---

## FFT vs Autocorr Doppler Extraction

`drf_to_doppler.py` supports two extraction methods via `--method`:

- `fft` (default): FFT-based carrier tracker. Robust, well-tested.
  Preferred for LSTID events where the lag is 30–50% of the wave period
  (ambiguous cross-correlation peaks).
- `autocorr`: Lag-1 complex autocorrelation instantaneous-frequency
  estimator (G3ZIL method). 2–3× smoother output. Preferred for heavily
  E-region-contaminated MSTID pairs where the lag is less than 30% of
  the wave period.

Use `drf_spectrogram.py --overlay` to compare both methods visually
before choosing. The legend shows inter-method Pearson r and RMS
difference — the key decision metrics. Full guidance in
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) Step 1b.

Research basis: see [`FINDINGS.md`](FINDINGS.md) and
[`research/psws_autocorr_research_report.pdf`](research/psws_autocorr_research_report.pdf).

---

## Documentation

All documentation lives in [`docs/`](docs/):

- **[`TUTORIAL.md`](docs/TUTORIAL.md)** — full narrative walkthrough
  using the 19 Jan 2026 event. **Start here if you're new.**
- **[`COOKBOOK.md`](docs/COOKBOOK.md)** — task-oriented recipes for
  everyday use.
- **[`AUTOMATION.md`](docs/AUTOMATION.md)** — reference for
  `analyze_event.sh` including resume menu and method selection.
- **[`METHODOLOGY.md`](docs/METHODOLOGY.md)** — math and signal
  processing details, including Step 1b visual inspection guide with
  worked clean vs contaminated examples.
- **[`ASSESSING_RESULTS.md`](docs/ASSESSING_RESULTS.md)** — scientific
  basis for trusting a result; honest provenance of every diagnostic
  threshold.
- **[`TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)** — failure modes
  and diagnoses.
- **[`QUALITY_SUMMARY_WORKED_EXAMPLE.md`](docs/QUALITY_SUMMARY_WORKED_EXAMPLE.md)** —
  worked example of how a degraded analysis window is caught.

Research documentation:

- **[`FINDINGS.md`](FINDINGS.md)** — work log for the FFT vs autocorr
  investigation (10 entries, 17–19 May 2026).
- **[`research/psws_autocorr_research_report.pdf`](research/psws_autocorr_research_report.pdf)** —
  formal report on real-data results.
- **[`research/synthetic/synthetic_experiment_report.pdf`](research/synthetic/synthetic_experiment_report.pdf)** —
  Monte Carlo synthetic experiment report (1,260 trials).

---

## What's in this repo

```
psws-drf-tid-tools/
├── README.md
├── CHANGELOG.md                v1.5.0 → v1.6.7 release history
├── FINDINGS.md                 FFT vs autocorr research work log
├── CONTRIBUTORS.md             N6RFM and G3ZIL
├── LICENSE                     MIT
├── CITATION.cff
├── requirements.txt
├── requirements-optional.txt
│
├── analyze_event.sh            interactive pipeline driver
│                               (method selection, resume menu)
├── drf_spectrogram.py          spectrograms + --overlay for method validation
├── drf_to_doppler.py           Doppler extraction (--method fft|autocorr)
├── drf_inspect.py              verify DRF metadata + subchannel
├── find_event_stations.py      companion-station discovery
├── tid_window_detector.py      automatic TID-window detection
├── tid_pair.py                 two-station cross-correlation
├── tid_doa_config.py           build DOA config interactively
├── tid_doa.py                  multi-station DOA inversion
│                               (--method field in config + run log)
├── tid_stack_plot.py           stacked Doppler comparison
├── tid_map.py                  array geometry map
├── quality_summary.py          per-station Doppler quality scoring
│
├── examples/
│   └── event_20260119.json     reference 4-station DOA config
│
├── docs/
│   ├── TUTORIAL.md
│   ├── COOKBOOK.md
│   ├── AUTOMATION.md
│   ├── METHODOLOGY.md          incl. Step 1b visual inspection guide
│   ├── ASSESSING_RESULTS.md
│   ├── TROUBLESHOOTING.md
│   ├── QUALITY_SUMMARY_WORKED_EXAMPLE.md
│   ├── fig_overlay_clean.png         W7LUX clean overlay example
│   ├── fig_overlay_contaminated.png  AC0G_ND contaminated overlay example
│   ├── fig_clean_vs_contaminated.png clean vs contaminated xcorr curves
│   ├── pipeline_flow.png
│   └── pipeline_flow.pdf
│
└── research/                   FFT vs autocorr investigation
    ├── psws_autocorr_research_report.pdf
    ├── build_report.py
    ├── xcorr_lag_plot.py
    ├── xcorr_both_pairs_fft.png
    ├── xcorr_both_pairs_autocorr.png
    ├── comparison_fft_vs_autocorr_jan19.png
    ├── comparison_table_jan19.png
    ├── event_autocorr_3stn.json
    ├── event_fft_6stn.json
    ├── event_autocorr_6stn.json
    └── synthetic/
        ├── synthetic_experiment_report.pdf
        ├── synthetic_tid_experiment.py
        ├── run_chunk.py
        ├── build_synthetic_report.py
        ├── synthetic_full_results.png
        ├── synthetic_example_traces.png
        ├── summary_combined.csv
        └── chunks/chunk_*.csv
```

Every script accepts `--help` and `--version`. Most have a full
docstring with motivation, parameter guidance, and worked examples.

---

## Pipeline overview

![pipeline](docs/pipeline_flow.png)

The blue boxes are scripts in this repo; yellow boxes are data products.
`drf_spectrogram.py` lets you see the wave and validate extraction
methods; `find_event_stations.py` picks companions; `drf_inspect.py`
verifies downloads; `drf_to_doppler.py` reduces raw I/Q to a
Doppler-vs-time CSV (FFT or autocorr); `tid_doa.py` solves for the
wave direction.

---

## Dependencies

Core (required):
- Python 3.10 or newer
- `digital_rf` 2.6+ (MIT Haystack Observatory)
- `numpy`, `scipy`, `pandas`, `matplotlib`
- `requests`, `beautifulsoup4` (for `find_event_stations.py`)

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
> Version 1.6.7. https://github.com/N6RFM/psws-drf-tid-tools

---

## Acknowledgments

- Gwyn Griffiths (G3ZIL) for co-development of the autocorr extractor,
  the 17 May 2024 LSTID reference analysis, and constructive collaboration
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
