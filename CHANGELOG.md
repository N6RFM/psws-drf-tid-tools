## v2.3.50 — 2026-05-30

### New features

- **tid_doa.py: xcorr_start_utc / xcorr_end_utc — trim xcorr window**
  Optional keys in the event JSON config. When present, cross-correlation
  and DOA inversion operate on the sub-window; full event window is still
  used for plotting. Backward compatible — omitting the keys preserves
  prior behaviour. Suggested by Gwyn Griffiths G3ZIL.
  Example:
  ```json
  "xcorr_start_utc": "2026-01-19T00:10:00Z",
  "xcorr_end_utc":   "2026-01-19T01:10:00Z"
  ```

---

## v2.3.49 — 2026-05-30

### Changes

- **Terminology: validation → evaluation throughout**
  All "validate/validation" language replaced with "evaluate/evaluation"
  project-wide. `validate_external.py` renamed to `evaluate_external.py`.
  Evaluation folder renamed accordingly. All docs and references updated.

### Bug fixes

- Removed accidentally committed n6rfm@hamsci.org file.

---

## v2.3.48 — 2026-05-30

### Documentation

- **EXTERNAL_RESULTS_EVALUATION.md comprehensive update**
  Added `fetch_madrigal_tec.py` to tool reference. Fixed Madrigal
  data-availability note (Jan 2026 data already ingested — 2–4 week
  latency, not 6–12 months as previously noted). Fixed title, tool
  count, and IONEX filename format.

---

## v2.3.47 — 2026-05-30

### Bug fixes

- **COOKBOOK: direction/speed verification guide — wording fix**
  Minor wording correction to the verification guide added in v2.3.46.

---

## v2.3.46 — 2026-05-30

### Documentation

- **COOKBOOK and EXTERNAL_RESULTS_EVALUATION: direction/speed verification guide**
  New section covering how to cross-check DOA speed and direction against
  independent data sources (GPS TEC, AE index, GloTEC). Covers
  `fetch_madrigal_tec.py`, `fetch_ae_index.py`, and `evaluate_external.py`
  in a unified workflow.

---

## v2.3.45 — 2026-05-30

### New features

- **fetch_madrigal_tec.py — MIT Haystack Madrigal GPS TEC retrieval**
  Queries the Madrigal Web API (cedar.openmadrigal.org) for gridded
  GPS TEC data around station IPP locations. Detrends with a 2nd-order
  polynomial to remove storm background, then cross-correlates TEC
  perturbations across station pairs for independent lag estimation.
  Generates four output plots:
  - `madrigal_tec_stations.png` — station map with IPP boxes
  - `madrigal_tec_detrended.png` — detrended TEC time series
  - `madrigal_tec_1min.png` — raw 1-min TEC data
  - `madrigal_tec_xcorr.png` — pairwise cross-correlation curves
  No account required. Jan 2026 data already ingested as of May 2026.

---

## v2.3.44 — 2026-05-30

### Documentation

- **README: Claude AI assistance note**
  Added acknowledgement that Claude (Anthropic) assisted with code
  development and documentation.

---

## v2.3.43 — 2026-05-30

### Documentation

- **CONTRIBUTORS.md: added Claude (Anthropic)**

---

## v2.3.41–v2.3.42 — 2026-05-29

### Documentation

- **docs/EXTERNAL_RESULTS_EVALUATION.md** — new tool reference document
  covering all external evaluation tools (`evaluate_external.py`,
  `fetch_ae_index.py`, `fetch_glotec.py`, `fetch_madrigal_tec.py`).
  Updated README and COOKBOOK with cross-references.
- Removed stale `docs/EXTERNAL_VALIDATION.md` (superseded by
  `examples/EXTERNAL_RESULTS_EVALUATION.md`).

---

## v2.3.37–v2.3.40 — 2026-05-29

### Changes

- **EXTERNAL_VALIDATION.md → EXTERNAL_RESULTS_EVALUATION.md**
  Renamed for clarity. All references updated across README, COOKBOOK,
  and evaluate_external.py. The document now covers all external
  evaluation methods, not just validation.
- `validate_external.py` → `evaluate_external.py` (see v2.3.49 for
  the project-wide terminology change that followed).

### Documentation

- Added `EXTERNAL_VALIDATION.md` / `EXTERNAL_RESULTS_EVALUATION.md`
  to examples/ — documents the Jan 2026 external evaluation session,
  tools used, and results.
- Added external evaluation usage to README and COOKBOOK.

---

## v2.3.35–v2.3.36 — 2026-05-29

### New features

- **validate_external.py (now evaluate_external.py) — external evaluation tool**
  Automates Kp index fetch (GFZ), AE index fetch (SuperMAG/Kyoto),
  and GloTEC montage retrieval for a given event date. Produces a
  text report summarising geomagnetic conditions at event time.
  Usage:
  ```
  python3 evaluate_external.py event.json
  ```
- **fetch_ae_index.py** — standalone AE index retrieval (SuperMAG API
  or Kyoto WDC fallback). Plots AE vs time with event window marked.
- **fetch_glotec.py** — standalone GloTEC TEC anomaly retrieval
  (NOAA SWPC). Generates montage of TEC anomaly maps around event time.

### Examples

- Added external evaluation PNGs and report for Jan 2026 event to
  `examples/tid_event_20260119/evaluation/`.

---

## v2.3.32–v2.3.34 — 2026-05-29

### Examples

- Added spline CSVs and spectrograms for the Jan 2026 MSTID event
  to `examples/tid_event_20260119/`.
- `examples/event_20260119.json` updated: added `use_ipp`, `max_lag_seconds`,
  fixed station filenames. Corrected result annotation to 239 m/s.
- Removed `examples/event_20240517.json` (moved to
  `~/Downloads/gwyn_tid_event_20240517/` working directory).

---

## v2.3.31 — 2026-05-29

### Documentation

- **CHANGELOG: added entries for v2.3.1–v2.3.30** (wave-fit series)

---

## v2.3.29–v2.3.30 — 2026-05-29

### New features

- **tid_spect_click.py: wave-fit compare/accept step (A key)**
  After pressing F to fit, the result is shown as a candidate — not
  immediately saved. Press A to accept (writes final `{stn}_wave_tid.csv`),
  W to discard and redo with new points, or Q to quit without saving.
  This prevents the last F press silently overwriting earlier better fits.

### Documentation

- WORKFLOW_TUTORIAL, MANUAL_TUTORIAL, COOKBOOK updated with A=accept key

---

## v2.3.28 — 2026-05-29

### Bug fixes

- **tid_spect_click.py: warn when <4 click points in wave-fit**
  With fewer than 4 clicks the 3-parameter fit (A, φ, offset) is
  under-constrained. A console NOTE is now printed to alert the user.
  scipy OptimizeWarning is suppressed (was noisy and uninformative).

---

## v2.3.5–v2.3.27 — 2026-05-28/29

### New features

- **tid_spect_click.py: W key wave-fit reconstruction**
  New interactive wave-fit mode alongside the existing spline/cwt-prophet
  workflow. Press W to enter wave-fit mode, click multiple points along
  the visible TID cycle, press F to fit. The tool fits:
  `A·sin(2π/T·(t−t₀)+φ) + C`
  to the click points only — user clicks define the wave exactly.
  - Brown diamond markers show click positions
  - Blue overlay shows the fitted wave on the spectrogram
  - Period dialog after F: 1=half cycle, 2=full cycle, or custom multiplier
  - DC offset as free parameter — overlay aligns with clicked points
  - Exports `{stn}_wave_tid.csv` for use with `tid_doa.py`
  - Each station independently estimates T, A, φ, C — no shared period assumption

- **tid_spect_click.py: --wave-only flag**
  Skip Pass 0 (Prophet auto-run) and open directly in wave-fit mode.
  No spline CSV required — time grid built from segment bounds.
  Console caveat printed if periods may differ between stations.

  ```bash
  python3 tid_spect_click.py --spectrogram zoom.png --name N6RFM \
      --seg-start 0.0 --seg-end 2.05 --wave-only
  ```

### Known limitations of wave-fit

- Requires at least 1.5–2 full cycles visible in the analysis window
- If TID period differs significantly between stations, xcorr between
  wave-fit CSVs will be incoherent — use spline extraction instead
- Jan 2026 dataset (<1 cycle visible): wave-fit not applicable
- May 2024 dataset (2.5 cycles visible): validated — 442 m/s from 10° N
  (vs spline 570 m/s from 354° N, 16° azimuth difference)

### Bug fixes (v2.3.5–v2.3.27)
- Wave-fit: correct phase alignment (centred time axis)
- Wave-fit: DC offset parameter added for correct overlay alignment
- Wave-fit: blocked X during wave-fit click mode
- Wave-fit: brown diamond markers for click points
- Wave-fit: multi-point mode (F to trigger, not auto on 2 clicks)
- Wave-fit: spline CSV dependency removed
- Wave-fit: pathlib local import fixed
- Wave-fit: state management — ignore clicks after done, draw overlay

### Documentation (v2.3.1–v2.3.27)
- README: extraction methods updated, wave-fit described, repo listing fixed,
  find_event_stations added, citation version updated
- WORKFLOW_TUTORIAL: Step 6 restructured as Option A/B/C with click guides
- MANUAL_TUTORIAL: Option C wave-fit, use_ipp coords, find_event_stations
- ASSESSING_RESULTS: reference speed updated to 239 m/s, stray asterisks fixed
- COOKBOOK: wave-fit recipe, gitignore note, May 2024 example config
- METHODOLOGY: extraction method table, wave-fit Step 1c, spline Step 1d
- TROUBLESHOOTING: tid_spect_click entries, wave-fit issues, closure note
- requirements.txt: PyQt5, pyqtgraph, Pillow added
- requirements-optional.txt: prophet added with installation note
- examples/: README, event_20240517.json, DOA report PDF, tid_event_20260119/ data

---

## v2.3.0 — 2026-05-28

### New features

- **tid_workflow.py: IPP vs station coords prompt**
  Workflow now asks the user to choose the DOA coordinate system at
  method selection time:
  - Option 1 (default): IPP midpoints — great-circle midpoint between
    station and WWV, the physically correct coord for Doppler TID analysis
  - Option 2: station coordinates — raw receiver lat/lon, useful for
    comparison or when IPP is pre-computed externally
  Choice is saved to state and skipped on resume.

### Bug fixes

- **tid_workflow.py: remove stale A=accept from Step 6 console output**
  The A key binding was removed from tid_spect_click.py in v2.2.0 but
  the Step 6 instruction string was not updated. Now shows:
  `P=re-run  X=export  R=reset  Q=quit`

## v2.2.1 — 2026-05-28

### Bug fixes

- **tid_workflow.py / tid_doa.py: double-midpointing fix (`use_ipp`)**
  `tid_workflow.py` was writing pre-computed IPP midpoints as `lat/lon`
  in the event JSON. `tid_doa.py` then re-applied `great_circle_midpoint`,
  giving ~¼-baseline coordinates and ~¼ the true phase speed (e.g. 128 m/s
  instead of ~510 m/s on the May 2024 event).

  Fix: `tid_workflow.py` now writes actual receiver coordinates with
  `"use_ipp": true`. `tid_doa.py` reads `use_ipp` (default `true`) and
  computes IPP midpoints internally. Set `"use_ipp": false` in a config
  to use coordinates as-is (e.g. manually pre-computed IPP coords).

- **tid_workflow.py: zoom_window t_end taken from axes sidecar**
  When Step 3 window drag saved `t_end` as the DRF recording end
  (e.g. 23:41 UTC) rather than the event end, that value was passed
  as `--seg-end` to `tid_spect_click.py` — wrong extraction range
  and malformed window size.

- **tid_workflow.py: apply-to-all writes `_fullday_window.json`**
  When applying a window to all remaining stations, only state was
  updated — the `_fullday_window.json` file was never written, causing
  `FileNotFoundError` in `drf_spectrogram.py --window`.

### New example
- `examples/event_20240517.json` — 3-station config for 17 May 2024
  LSTID event (W7LUX/N5BRG/N4RVE, 17:30–20:30 UTC). See FINDINGS
  Entry 44 on research_gui for analysis notes.

## v2.2.0 — 2026-05-27

### Interactive spline extraction (tid_spect_click.py)

Major rewrite of the extraction GUI. The new workflow:

1. **Pass 0 (automatic):** On open, cwt-prophet runs automatically and
   shows a green trace overlay. No clicks needed for clean stations.
2. **Click to correct:** Click on the F-region carrier at any excursion
   (black dots with white border). Live PCHIP spline preview updates
   after each click.
3. **P** to re-run Prophet with current anchor clicks as constraints.
4. **X** to export the final spline CSV and set it as baseline for
   further corrections.
5. **R** to reset all clicks. **Q** to quit.

The spline through user anchor clicks IS the extracted Doppler — no
wrong-peak lock possible. Click count is a quality metric: clean
stations need 0 clicks.

Key bindings are always shown in the status bar.

### tid_workflow.py: cwt-prophet as default method

- cwt-prophet is now method 1 (recommended) and opens the interactive
  spline window automatically
- sgolay-ridge also opens the interactive spline window
- Negative segment start times are clamped to 00:00 UTC

### Validated result

Best result to date on the Jan 2026 LSTID event (4 stations, spline
extraction): **239 m/s from 30° NNE**, only 1 of 5 diagnostics
flagged, triangle closure 13%.

### Documentation cleanup

- Removed obsolete docs: `docs/TUTORIAL.md`, `docs/AUTOMATION.md`,
  `docs/QUALITY_SUMMARY_WORKED_EXAMPLE.md`, `docs/pipeline_flow.*`
- Removed research-only files from main: `FINDINGS.md`,
  `PROJECT_STATE.md`, `SESSION_LOG.md`, `GUI_TUTORIAL.md`, `research/`
- Updated cross-references in `docs/COOKBOOK.md`, `METHODOLOGY.md`,
  `TROUBLESHOOTING.md`, `ASSESSING_RESULTS.md`
- `WORKFLOW_TUTORIAL.md` and `MANUAL_TUTORIAL.md` updated for v2.2.0

## v2.0.1 — 2026-05-27

### New extraction method: cwt-prophet

`drf_to_doppler.py --method cwt-prophet` implements CWT peak-finding
with Facebook Prophet time-series prediction instead of linear
extrapolation, enabling direct comparison with Gwyn Griffiths' (G3ZIL)
`grape_fft_CWT_tracking_prophet.py` approach.

Comparison on the Jan 2026 event shows cwt-prophet gives identical
results to fft on both clean and contaminated stations — Prophet's
Bayesian prediction provides no advantage over linear extrapolation
for smooth slowly-varying TID signals. Only sgolay-ridge reliably
avoids wrong-peak lock on contaminated stations.

Requires: `pip install prophet` (already available in most scientific
Python environments).

### tid_workflow.py: longitude display

Coordinates are now displayed with W/E suffix rather than signed East:

    Before: Coords from callsign DB (AC0G_ND): 46.8750N, -96.8333E
    After:  Coords from callsign DB (AC0G_ND): 46.8750N, 96.8333W

### tid_workflow.py: grid squares in spectrogram titles

Grid squares added to KNOWN_STATIONS for all built-in stations.
`--grid` is now passed to all `drf_spectrogram.py` calls, so
spectrogram titles show the correct grid square:

    Before: Doppler spectrogram - AA6BD (?) at 10.000 MHz
    After:  Doppler spectrogram - AA6BD (EM75kb) at 10.000 MHz

## v2.0.0 — 2026-05-26

### Guided workflow (tid_workflow.py) — major new feature

A complete 8-step guided workflow that takes you from raw DRF data to
a validated DOA result in a single interactive session:

1. Station discovery and subchannel selection with thumbnail spectrograms
2. Full-day spectrogram generation
3. Interactive TID window selection (tid_quicklook.py)
4. Zoomed spectrogram generation
5. Optional window refinement (opt-in, default skip)
6. Doppler extraction — corridor clicking (sgolay-ridge) or automated
7. Extraction output and visual validation
8. DOA inversion with interactive drop-station loop and comparison table

Key features:
- State saved after each interactive step — `--resume` to continue
- `--stations A,B,C` to use a subset of stations in the event directory
- `--max-lag MIN` to constrain xcorr search and prevent period aliasing
- "Same window for all stations" prompt after first window is set
- Window review with per-station redo before extraction begins
- Post-DOA interactive drop-station loop with comparison table
- DOA diagnostics suggest specific station to drop when flagged

### New extraction method: sgolay-ridge

`drf_to_doppler.py --method sgolay-ridge` implements a 2D STFT ridge
tracker with a user-defined corridor. Combined with `tid_spect_click.py`
for corridor clicking, this is the recommended method for events with
E-region contamination.

Validation on the Jan 2026 event: sgolay-ridge gave 262 m/s from 37°
NNE (physically correct) while fft locked on the wrong xcorr peak
(99 m/s from 167°, opposite direction) due to AC0G/ND contamination.

### New extraction method: cwt

`drf_to_doppler.py --method cwt` implements a CWT multi-peak tracker
with linear extrapolation (in addition to the existing fft and autocorr).

### tid_quicklook.py improvements

- Duplicate axes hidden — pyqtgraph axes were overlapping the axes
  baked into the spectrogram PNG
- `--seg-start` / `--seg-end` flags to pre-position the yellow region

### tid_spect_click.py improvements

- Removed sinusoid fit workflow (replaced by sgolay-ridge extraction)
- Removed CSV overlay and FFT consistency check (no longer needed)
- X key: export corridor and run sgolay preview (green curve)

### drf_spectrogram.py improvements

- Removed bottom amplitude panel (single-panel figure)
- `--callsign` now passed through automatically by tid_workflow.py
  so spectrogram titles show station name instead of (?)
- `date_utc` field added to sidecar JSON

### tid_doa.py improvements

- Diagnostics [3] and [4] now suggest a specific station to drop
  (names the station with most weak pairs / lowest mean corr in
  worst closure triple)

### Documentation

- `WORKFLOW_TUTORIAL.md` — complete guided workflow walkthrough
- `MANUAL_TUTORIAL.md` — step-by-step manual pipeline tutorial
- `README.md` updated to reflect v2.0 guided workflow as primary method

### Validated scientific result

First physically validated result from psws-drf-tid-tools:
- Event: 19 January 2026 LSTID (00:00–01:36 UTC)
- Stations: N6RFM, AA6BD, W7LUX, AC0G/ND
- Result: 254–283 m/s from 30–35° NNE (equatorward auroral LSTID)
- Validation: peak-time cross-check from stacked spectrogram gives
  ~280 m/s on two independent baselines, consistent with DOA result

# Changelog
## v1.6.8 — 2026-05-19
### drf_spectrogram.py: add --dpi flag
- **New feature**: `--dpi N` sets output PNG resolution.
  Default 140 unchanged. Use 200-300 for publication quality,
  600 for maximum detail (produces ~8000x4000 px output).

## v1.6.7 — 2026-05-19
### Fix: cp same-file error in analyze_event.sh Stage 8
- **Bug fix**: when the reference station name matched the output
  CSV filename (common case), cp failed with "same file" error
  which killed the script under set -e. Added filename equality
  check before cp in extract_with_overlay().

## v1.6.6 — 2026-05-19
### Fix: wire extract_with_overlay into Stage 8 (analyze_event.sh)
- **Bug fix**: Stage 8 was still using direct drf_to_doppler.py
  calls instead of extract_with_overlay(). Both reference station
  and companions now correctly go through extract_with_overlay(),
  which renders the overlay spectrogram and asks the operator to
  choose FFT or autocorr per station.
- Restores extract_with_overlay() function definition lost during
  a merge conflict resolution.


## v1.6.5 — 2026-05-19
### drf_to_doppler.py v1.1.1: --method fft|autocorr promoted to main
- **New feature**: `--method fft` (default) or `--method autocorr`
  (lag-1 complex autocorrelation, G3ZIL method). Previously only on
  the research branch; now available to all users.
- Required by `drf_spectrogram.py --overlay` and
  `analyze_event.sh extract_with_overlay()`.
- Clean-data gate: SNR delta 0.0 dB, r=0.933, autocorr 3x smoother.

## v1.6.4 — 2026-05-19
### Interactive resume menu in analyze_event.sh
- **New feature**: when a state file is found, shows current state
  summary and numbered menu (0-12) to jump to any pipeline stage.
- Press Enter to continue from where you left off (default).
- Enter 0 to start over; 1-12 to jump directly to any stage.

## v1.6.3 — 2026-05-19
### Per-station FFT vs autocorr method selection (analyze_event.sh)
- **New feature**: at each Doppler extraction step (reference station
  and each companion), the script now runs both FFT and autocorr
  extractions, renders a `drf_spectrogram.py --overlay` showing both
  traces with inter-method r and RMS diff metrics, and asks the
  operator which method better tracks the carrier.
- **New feature**: choices recorded in `station_methods.txt` and
  written into the `"method"` field of each station's `event.json`
  entry, so the run log is fully self-documenting.
- **Decision guide** shown at each station:
  r > 0.95 and RMS < 0.10 Hz → both equivalent, use fft;
  autocorr visually better → autocorr (only if lag < 0.3 * period);
  otherwise → fft (safer for ambiguous lag/period ratios).
- Default is `fft` (press Enter to accept). Backward compatible.
  No change to any computation.

## v1.6.2 — 2026-05-19
### Per-station extraction method provenance (tid_doa.py)
- **New feature**: optional `"method"` field in each station entry
  of the JSON config records which Doppler extraction method was used
  (`"fft"` or `"autocorr"`). Default `"fft"` — omitting the field is
  fully backward compatible.
- **New feature**: method is printed in the run log station list, so
  mixed FFT/autocorr analyses are self-documenting.
- **No change to any computation.** Purely provenance. Result on the
  19 Jan 2026 MSTID verified identical with and without the field.
- Supports the mixed-method workflow enabled by v1.6.0: use
  `drf_spectrogram.py --overlay` to choose the best extraction method
  per station, record the choice in the config, run `tid_doa.py`.

## v1.6.1 — 2026-05-18
### Fix: inter-method r display in drf_spectrogram.py --overlay
- **Bug fix**: FFT trace showed tautological r=1.000 (correlation
  with spectrogram peak track — same operation as FFT extraction).
- Inter-method r and RMS diff now computed once between FFT and
  autocorr traces, shown as a single summary legend entry.
- Per-trace legend now shows SNR and std only.

## v1.6.0 — 2026-05-18
### Doppler overlay for spectrogram visual inspection (drf_spectrogram.py)
- **New feature**: `--overlay CSV:label[:color]` superimposes one or
  more Doppler CSV traces (output of `drf_to_doppler.py`) on the
  spectrogram panel. Supports multiple overlays for FFT vs autocorr
  side-by-side comparison. Color auto-cycles (blue, orange, green,
  red) or can be specified explicitly as a hex value.
- **New feature**: each overlay trace shows four fit metrics in the
  legend: `r` (Pearson correlation between FFT and autocorr traces),
  `RMS diff` (physical magnitude of inter-method disagreement in Hz),
  `SNR` (median signal-to-noise from the CSV), and `std`
  (block-to-block smoothness of the extracted Doppler).
- **New documentation**: `INTERPRETING OVERLAY METRICS` and
  `DECISION WORKFLOW` sections added to the `drf_spectrogram.py`
  docstring, explaining how to use r, RMS diff, and std to choose
  between FFT and autocorr extraction and when each method is
  preferred based on the lag/period ratio.
- **New documentation**: `docs/METHODOLOGY.md` Step 1b added —
  visual inspection with `--overlay` before cross-correlation,
  including the full decision workflow and link to the research
  report for the underlying synthetic and real-data evidence.
- **Implementation note**: non-breaking. All existing behaviour
  unchanged. `--overlay` is optional; omitting it produces output
  identical to v1.1.1. Requires `pandas` (already in
  requirements.txt).


## v1.5.0 — 2026-05-17

### Result diagnostics + per-run log (tid_doa.py)
- **New feature**: after every DOA result, `tid_doa.py` prints five
  observational diagnostics — geometry conditioning (singular-value
  ratio), plane-wave fit residual, pairwise correlation spread,
  triangle closure, and phase-speed plausibility. They are
  flag-don't-fail: each shows a measured value against a guideline
  range and flags values outside it, but never renders a verdict
  and never alters or suppresses the result. Default on;
  `--no-diagnostics` to suppress.
- **New feature**: each run writes a self-contained record to
  `./runs/<UTC-timestamp>_run.log` (inputs, result, pairwise table,
  diagnostics block, provenance including argv and git hash).
  Default on; `--no-run-log` to suppress. Non-fatal on any error.
- **Implementation note**: every diagnostic value was already
  computed by the inversion (the least-squares residuals, rank, and
  singular values were previously discarded; pairwise corr/lag were
  already stored). No new algorithms, no extra inversions, no change
  to any computed value — verified additive-only against a synthetic
  known-wave case (result byte-identical before/after).

### tid_pair period-band label fix (tid_pair.py)
- **Bug fix**: the output column headed "Interval (min)" and the
  "Full time window" row were misleading — the rows are wave-period
  bandpass filter bands, not time-of-day windows. Header changed to
  "Period band (min)", row labels made self-documenting, an
  explanatory legend added above the table, and the docstring and
  tutorial reconciled. Label/wording only — verified byte-identical
  numeric output before/after.
- **New flag**: `--debug` prints resolved csv1/csv2 paths, row
  counts, time spans, per-band filtered variance and chosen lag, and
  warns explicitly if the two inputs are the same file.
- **Tutorial**: added a period-band explanation and a second worked
  pair using different CSV arguments, to pre-empt the
  "same files relabelled" failure mode.
Feedback from G3ZIL (16 May testing).

### New document: ASSESSING_RESULTS.md
- A reviewer-facing scientific-basis document explaining how a
  defensible result is reasoned from the measurements, the
  supporting mathematics, and the honest provenance of every
  diagnostic threshold: only the phase-speed range is
  literature-derived (Hocke & Schlegel 1996); the triangle-closure
  principle is an exact geometric identity; the remaining four
  threshold values are stated plainly as arbitrary review-guidance
  values. Linked from the README documentation index and repo tree.

### Documentation
- README: stale step-numbering removed from the repo-structure tree
  (replaced with role descriptions), consistent with the earlier
  removal of the "7-step pipeline" prose.

---

## v1.4.0 — 2026-05-16

### Auto-window-tightening at Pause 4 (PR-D)

- **New feature**: when `quality_summary.py` flags an end-fade (e.g.
  N6RFM's +6.6 dB drop in the last 10% of a 75-minute window), the
  driver now offers to tighten the analysis window. Default is to
  keep the current window (press Enter); type `y` to accept the
  suggested tightening. If accepted, all stations' Doppler CSVs are
  re-extracted at the new window, `quality_summary.py` is re-run,
  and `stack_pause4.png` is re-rendered. The loop runs up to 3
  iterations or until no more suggestions appear.
- **Design notes**: this revives the auto-tightening feature that
  was prototyped but backed out of v1.3.0 because of state-management
  bugs. The clean rewrite:
  - Uses the canonical `WINDOW_END` shell variable (not the broken
    `END_TIME` from the v1.3.0 prototype).
  - Persists `WINDOW_END` to `.analyze_event_state` immediately when
    changed, so Stage 10 and resumes always read the correct value.
  - Reads each station's subchannel from `station_subchannels.txt`
    (already built at Stage 8), correctly handling multi-subchannel
    DRFs like AC0G/ND where 10 MHz is at subchannel 4, not 0.
  - Defaults to safe behavior (Enter = keep current) rather than
    the v1.3.0 prototype's "Enter = accept the change" pattern that
    caused unintended tightening.
  - Stage 11 figure regeneration picks up the tightened window
    automatically because Stage 11 reads from state.

Feedback from G3ZIL (deferred during v1.3.0).

---

## v1.3.0 — 2026-05-15

### Pause 4 UX improvement (PR-C, analyze_event.sh v1.4.3)

- **Stacked Doppler plot rendered at Pause 4**: the driver now
  generates a multi-station overlay (`stack_pause4.png`) and opens
  it BEFORE the "do all stations look good?" prompt. Operators can
  see the array view in one image rather than relying on per-station
  PNGs only. Uses `tid_stack_plot.py --smooth 120` for peak-marker
  accuracy on noisy stations.
- **tid_stack_plot.py `--smooth N` flag**: when set, peak detection
  finds the peak on a smoothed-internal series instead of the raw
  trace. Display traces stay raw (so noise spikes remain visible
  for diagnostic purposes); only the peak-marker selection is
  smoothed. Helps avoid picking noise spikes as the wave peak.

Feedback from real-world testing.

### Substantive code changes (PR-B from G3ZIL feedback round 2 + Phase 2 roadmap)

- **--smooth N flag** added to `drf_to_doppler.py`, `tid_doa.py`, and
  `tid_pair.py`. Off by default; when set, applies a Savitzky-Golay
  filter (polynomial order 3) with N-second window. `drf_to_doppler.py`
  bakes smoothing into the CSV (with a header comment noting that
  smoothing was applied); the other two smooth in-memory before
  cross-correlation, leaving CSVs untouched. Each script prints a
  one-line notice when smoothing is applied.
- **Signed-speed convention in `tid_pair.py`**: the speed column now
  carries a sign (positive when the wave moves along the baseline
  bearing from station2 toward station1, negative for the opposite
  direction). Header reads "Speed (+ along {brg:.0f}°)". Makes sign
  flips between intervals visually obvious, which is exactly the
  diagnostic value of pair analysis. Interpretation hints rewritten
  to describe this convention.
- **--overlay-plot flag in `tid_pair.py`**: writes a paired-Doppler
  overlay PNG showing both station traces on the same axes. Useful
  for visually confirming where the lag comes from and seeing the
  inconsistencies that explain a low or sign-flipping correlation.
- **Driver Pause 4 smoothing prompt**: `analyze_event.sh` v1.4.3 now
  scans the quality_summary output for stations with jitter > 0.15 Hz.
  If any are found, the driver offers to enable `--smooth 30` for the
  Stage 10 DOA inversion. Default is no.
- **TUTORIAL.md / COOKBOOK.md**: added documentation for the new
  --smooth flag, with tuning recommendations.

Feedback from G3ZIL + Phase 2 of the code roadmap.

### Small improvements (PR-A from G3ZIL feedback round 2)

- **find_event_stations.py**: expanded the magnetometer filter to
  include `gmag` (catches W2NAF and similar entries that the
  rm3100/magnetome patterns missed). One-line change to the
  `inst_lc` filter tuple.
- **METHODOLOGY.md**: added a section "Window length, wave-travel
  time, and station coverage" discussing the trade-off between
  capturing the wave's full transit across the array and avoiding
  station-specific data degradation. Acknowledges G3ZIL's point
  about N→S travel time potentially arguing for wider windows.
- **TUTORIAL.md**: refreshed the example station-discovery table
  with values from a recent real run. PSWS station coordinates
  drift as operators update their metadata, so older example numbers
  no longer match what users see. The example is still illustrative
  (see the existing note); refreshing brings it closer to current
  reality without claiming it's permanent.

Feedback from G3ZIL.

### Documentation and output-text corrections (from G3ZIL feedback)

- **tid_pair.py**: renamed the output column header "Band (min)" to
  "Interval (min)" — `Band` could be confused with frequency band,
  while the rows are actually period intervals.
- **tid_pair.py**: renamed the row label "Raw (no filter)" to
  "Full time window" — better describes what the row represents
  (no time-window restriction) without implying a frequency filter
  that is or isn't applied.
- **tid_pair.py + TUTORIAL.md**: corrected an inverted-inequality
  description. The text previously said the apparent speed is a
  *lower bound* on the true phase speed. This is wrong: with the wave
  oblique to the baseline, `apparent = true / cos(theta)`, so
  apparent speed is >= true speed (it overstates). The docstring,
  output-footer note, and tutorial paragraph all now describe this
  correctly.
- **TUTORIAL.md**: changed "We need 3+ stations to get the true speed"
  to "We need 3+ stations to get the true vector velocity" — more
  precise: pair analysis gives a single scalar projection, multi-
  station inversion gives a 2-D vector velocity.
- **METHODOLOGY.md**: added a paragraph on interpreting the correlation
  coefficient as `r²` = explained variance, with thresholds. Helps
  operators see that a correlation of 0.578 represents only ~33% of
  shared variance, leaving ~67% to noise.

Feedback from G3ZIL.

---

## v1.2.1 — 2026-05-15

### Code fixes (drf_spectrogram.py — v1.1.1)
- Added progress dots to the peak-amplitude pass. Previously the
  console appeared frozen for ~30-45 seconds after the "Computing
  peak amplitude per minute..." message during 24-hour renders.
  Now ~40 progress dots flow during this second read pass, matching
  the behavior of the spectrogram pass above it.

### Code fixes (analyze_event.sh — v1.4.2)
- Fixed viewer not displaying when stdio was redirected to /dev/null.
  Some image viewers (notably `feh` on certain systems) exit silently
  without showing a window when their stdout/stderr is `/dev/null`.
  Viewer output now goes to a hidden `.viewer.log` file in the working
  directory, which feh treats as a valid output sink and which doesn't
  clutter the terminal.

### UX improvements (analyze_event.sh — v1.4.2)
- Added hint messages before each annotated-spectrogram render at
  Stage 1b and in the Pause 1 menu, explaining that the operation
  takes ~30-60 seconds. Previously the console appeared frozen during
  these renders.
- Let `drf_spectrogram.py`'s stdout flow through during the same
  renders, so the operator sees its progress dots ("....") rather
  than an unmoving prompt.

Feedback during real-world testing.

---

## v1.2.0 — 2026-05-15

### Documentation
- Tutorial Step 1: added prerequisite paragraph clarifying that
  Step 1 follows from already having noticed an event signature
  in some spectrogram (it's not a discovery step).
- Tutorial: improved azimuthal-spread wording to explicitly say
  "three stations whose WWV-path midpoints sit roughly to the N,
  E, S, or W of your own midpoint".
- Tutorial: added note that the example station-discovery table
  is illustrative; actual rows depend on PSWS's current state.
- Tutorial + AUTOMATION: updated find_event_stations.py timing
  estimate from "3-5 minutes" to "3-10 minutes" (matches
  observed real-world durations).

Feedback from G3ZIL.

### Code fixes (find_event_stations.py)
- Added filter to skip magnetometer-only observations (RM3100 and
  similar) so they no longer appear as candidate radio companions.
- Reference station is now included in the candidate table as a
  marked entry (rank `*`, score `—`, `(your station)` note) instead
  of being silently dropped. Operators can see and verify their own
  station's ObsID and path geometry at a glance.
- Table header widened to accommodate the `(your station)` marker;
  reference-station row is held aside before grid-square dedupe and
  always appears at the top of the table.
- Updated TUTORIAL.md example output to reflect the new format.

Feedback from G3ZIL.

---

All notable changes to **psws-drf-tid-tools** are recorded here.
The project follows [Semantic Versioning](https://semver.org).

## [1.0.0] - 2026-05-12

Initial public release. Toolkit assembled around the analysis of the
**19 January 2026 X1.9 flare + LSTID event** observed by four HamSCI
Grape stations across the central US.

### Pipeline scripts

| Script | Purpose | Version |
|---|---|---|
| `find_event_stations.py` | Locate companion HamSCI stations for a given event date | 1.0.0 |
| `drf_inspect.py` | Verify DRF metadata and identify the correct subchannel for a target frequency | 1.0.0 |
| `drf_to_doppler.py` | Extract Doppler-vs-time CSV from raw DRF I/Q | 1.0.0 |
| `drf_spectrogram.py` | Render annotated Doppler spectrograms | 1.1.0 |
| `tid_window_detector.py` | Automatically locate TID windows in a Doppler survey | 1.0.0 |
| `tid_pair.py` | Two-station cross-correlation across multiple filter bands | 1.0.0 |
| `tid_doa_config.py` | Interactive config builder for `tid_doa.py` | 1.0.0 |
| `tid_doa.py` | Multi-station direction-of-arrival inversion | 1.1.0 |
| `tid_stack_plot.py` | Stacked multi-station Doppler comparison plot | 1.0.0 |
| `tid_map.py` | TID array geometry map with wave-direction overlay | 1.0.0 |

### Per-script highlights

#### `tid_doa.py` v1.1.0
- Default cross-correlation now operates on raw mean-subtracted Doppler
  (no bandpass). Bandpassing produced multi-lobed correlation functions
  that caused the lag-finder to lock onto wrong secondary peaks. The
  pre-1.1 behavior is still available via `use_bandpass: true` in the
  config.
- `max_lag_seconds` is now auto-computed from the largest pairwise
  baseline divided by `min_expected_speed_m_s` (default 100 m/s).

#### `drf_spectrogram.py` v1.1.0
- Added `--callsign` and `--grid` overrides for stations whose Grape v1.x
  DRF metadata omits those fields.

#### `find_event_stations.py` v1.0.0
- Discovered (and works around) several PSWS observation-portal quirks:
  - `sort=-startDate` uses upload timestamp rather than observation date
  - Multi-subchannel WSPRdaemon stations store comma-separated frequency
    lists that defeat exact-string filters
  - Per-station observation lists must be queried individually (rather
    than scanning the global date-sorted list)
  - File-type classification by filename pattern, not instrument string
