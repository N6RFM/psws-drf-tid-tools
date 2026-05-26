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
