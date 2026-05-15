# Changelog

## Unreleased

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
