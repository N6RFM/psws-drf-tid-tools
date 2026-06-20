# PROJECT_STATE.md
# psws-drf-tid-tools — project state log
# Sections 1-35 reconstructed from git history and FINDINGS entries.

---
## 1. Initial release v1.0.0 — 2026-05-12
First public release of psws-drf-tid-tools. Core tools: drf_to_doppler.py
(FFT extraction), tid_pair.py (2-station cross-correlation), tid_doa.py
(multi-station DOA inversion), drf_spectrogram.py. README with full
methodology documentation.

---
## 2. Documentation and README updates — 2026-05-12/13
Step 1 (identify TID region) added to methodology. Window parameter
documentation. Multiple README clarifications. PRs #1-#3.

---
## 3. Driver script and automation — 2026-05-13
analyze_event.sh: interactive driver script for the full TID analysis
pipeline. AUTOMATION.md documentation. PR #4.

---
## 4. Quality scoring tools — 2026-05-14
quality_summary.py: per-station Doppler quality scoring with worked
example. find_event_stations.py: filter magnetometers, include
reference station. PRs #5-#8. v1.2.0.

---
## 5. G3ZIL feedback round 1 — 2026-05-14
Doc clarifications from Gwyn Griffiths G3ZIL review. Five corrections
to tid_pair output, tutorial, methodology. Viewer stdio fix. Progress
dots for drf_spectrogram.py. PRs #9-#11. v1.2.1.

---
## 6. G3ZIL feedback round 2 — 2026-05-15
Three improvements from G3ZIL feedback. Driver script fixes (tee
ordering, viewer instance management, stage 1b survey feedback).
PRs #12-#16. v1.3.0, v1.4.0.

---
## 7. First May 2024 LSTID analysis — 2026-05-16
FINDINGS 1-3. First run on self-downloaded copy of May 17 2024 event.
N4RVE/N5BRG investigation: noise issues, dual-channel discovery.
Self-download thread closed — need Gwyn's processed data.

---
## 8. Autocorr extractor and first results — 2026-05-17
FINDINGS 4-5. Gwyn replies with processed data. Autocorr (lag-1
complex autocorrelation) extractor implemented — G3ZIL method, 2-3x
smoother than FFT. First contaminated-pair cross-correlation results.
Autocorr vs FFT comparison on N4RVE/N5BRG.

---
## 9. Lag discrepancy investigation — 2026-05-17/18
FINDINGS 6. Lag discrepancy found between our results and Gwyn's.
Clarification email sent. Root cause: different array geometry
assumptions (receiver coords vs IPP midpoints).

---
## 10. Synthetic Monte Carlo experiment — 2026-05-18
FINDINGS 7. Synthetic wave propagation with known speed/direction.
Verified DOA inversion accuracy. Confirmed: plane-wave assumption
holds for MSTID-scale wavelengths on the PSWS array.

---
## 11. Jan 2026 MSTID four-configuration comparison — 2026-05-18
FINDINGS 8. Four-station comparison on Jan 19 2026 event. Multiple
extraction method configurations tested. Identified sensitivity to
extraction method and station subset.

---
## 12. v1.6.x toolkit — overlay, method selection, workflow — 2026-05-18/19
FINDINGS 9. drf_to_doppler.py: --method flag (fft/autocorr/cwt),
overlay spectrograms with extraction trace, method comparison plots.
Systematic method evaluation framework.

---
## 13. May 2024 LSTID re-run with mixed methods — 2026-05-19
FINDINGS 10. Mixed-method DOA on May 2024 event. Discovery:
collinear array geometry limits direction resolution. Station
midpoints nearly co-linear → direction poorly constrained.

---
## 14. CWT multi-peak tracker — 2026-05-19/20
FINDINGS 11. CWT (Continuous Wavelet Transform) multi-peak tracker
implemented. Tracks multiple spectral peaks through time, handles
peak crossings. Better than FFT on contaminated signals but still
automated (no user guidance).

---
## 15. Adaptive bandpass and multi-peak xcorr — 2026-05-20
FINDINGS 12-13. Adaptive bandpass pre-filter for xcorr. Multi-peak
xcorr selector in tid_doa.py: when multiple correlation peaks exist,
select the one most consistent with the plane-wave model.

---
## 16. Multi-peak xcorr results and parabolic interpolation — 2026-05-22
FINDINGS 14-15. Multi-peak xcorr selector tested on May 2024 collinear
array. Parabolic lag interpolation fixes discretisation closure error —
key improvement for lag precision.

---
## 17. Interactive guided extraction tools — 2026-05-22/23
FINDINGS 16-17. research_gui branch created. tid_spect_click.py:
interactive spectrogram click tool for carrier identification.
Click-guided corridor extraction: user defines frequency corridor,
algorithm tracks carrier within it.

---
## 18. Post-processing limitations — 2026-05-23
FINDINGS 18. Post-processing detrending (Savitzky-Golay, outlier
rejection) cannot fix wrong-peak lock. Key insight: extraction must
be correct at source — no amount of post-processing can recover a
trace that locked onto the wrong spectral feature.

---
## 19. Bandpass and CWT extraction comparison — 2026-05-23
FINDINGS 19. Bandpass and CWT extraction comparison on AC0G_ND.
Method comparison matrix showing which extraction approaches work
on contaminated stations.

---
## 20. sgolay-ridge: first complete 4-station result — 2026-05-24
FINDINGS 20-21. sgolay-ridge extraction on all stations. First
complete 4-station DOA result using guided extraction. Validated
the corridor-based approach as superior to automated methods on
contaminated stations.

---
## 21. 4-station DOA with N5BRG and IPP coordinates — 2026-05-24/25
FINDINGS 22-23. Added N5BRG as fourth station. IPP (Ionospheric
Pierce Point) coordinate system implemented for more physical
midpoint calculation. Automated FFT vs sgolay-ridge comparison.

---
## 22. Full method comparison — 2026-05-25
FINDINGS 24-25. Systematic comparison: FFT vs autocorr vs sgolay-ridge.
Array geometry comparison with Gwyn's method. Identified: sgolay-ridge
gives consistent results where FFT/autocorr fail due to contamination.

---
## 23. Critical limitation identified — 2026-05-25
FINDINGS 26. Key finding: DOA diagnostics (closure, residual, SVR)
are internal consistency checks, not independent validation. A result
can pass all diagnostics and still be wrong. External validation
(GPS TEC, ionosonde, Kp/AE) is essential.

---
## 24. tid_workflow.py implementation — 2026-05-26
FINDINGS 27-28. Complete guided workflow wrapper: station discovery,
spectrogram generation, window selection, extraction, DOA — all in
one interactive command. Strategy summary: sgolay-ridge for
contaminated stations, FFT/autocorr for clean ones.

---
## 25. EMD test and GUI cleanup — 2026-05-26
FINDINGS 29-31. EMD (Empirical Mode Decomposition) tested on W7LUX
May 2024 — did not improve extraction. GUI cleanup: amplitude panel
and sinusoid fit removed from spectrogram viewer. Clean launch fix.

---
## 26. Jan 2026 event analysis begins — 2026-05-27
FINDINGS 32-33. sgolay-ridge vs FFT comparison on Jan 2026 event.
Document speed error identified in earlier analysis — corrected.

---
## 27. max_lag_seconds constraint — 2026-05-27
FINDINGS 34. max_lag_seconds constraint in tid_doa.py improves
result by preventing alias peak lock. Key parameter for DOA quality.

---
## 28. Sign convention reconciliation with Gwyn — 2026-05-27
FINDINGS 35-36. Gwyn's email identifies sign convention difference.
Full cross-check: our "coming from" = Gwyn's "heading toward" + 180°.
Results agree once convention is aligned. Critical for comparing
results between groups.

---
## 29. Corridor extraction variability — 2026-05-27
FINDINGS 37. Jan 2026 corridor extraction variability investigation.
Lag consistency across different corridor placements. Finding:
corridor width and placement affect lags — need reproducible method.

---
## 30. cwt-prophet implementation — 2026-05-27
FINDINGS 38. CWT-prophet hybrid: CWT ridge detection + Facebook
Prophet time-series model for smooth carrier tracking. Comparison
with cwt and sgolay-ridge on Jan 2026 event.

---
## 31. AA6BD carrier identification — 2026-05-27
FINDINGS 39. AA6BD carrier identification: the strong near-zero
feature is NOT the F-region carrier. sgolay-ridge correctly tracks
the displaced carrier arc. Key finding for understanding why
automated methods fail on this station.

---
## 32. Jan 2026 final sgolay-ridge result — 2026-05-28
FINDINGS 40. Final sgolay-ridge result on Jan 2026 event. AC0G_ND
lag analysis: this station consistently degrades the DOA result.
Dropping AC0G_ND gives cleaner results.

---
## 33. May 2024 cwt-prophet and spline extraction — 2026-05-28
FINDINGS 41-43. May 2024 event: cwt-prophet DOA result.
tid_spect_click.py: spline extraction and Prophet-guided modes.
Jan 2026 best DOA result with spline extraction.

---
## 34. May 2024 best results and wave-fit — 2026-05-28/29
FINDINGS 44-49. May 2024 LSTID: first successful 4-station DOA.
Window selection criterion and max-lag tightening. Wave-fit
reconstruction prototype: A·sin(2π/T·t + φ) fit to clicked cycle
points. DOA comparison: wave-fit vs spline vs prophet. v2.2.0.

---
## 35. External validation session — 2026-05-29/30
FINDINGS 50-52. Jan 2026 external validation: Kp/AE indices,
GloTEC TEC anomaly maps, IONEX GPS TEC analysis, Madrigal GPS
TEC cross-correlation. evaluate_external.py, fetch_ae_index.py,
fetch_glotec.py, fetch_madrigal_tec.py. v2.3.x series.


---
## 36. End of session — 2026-05-28 (late)

### Accomplished
- IPP prompt tested on May 2024 event — working correctly
  - IPP mode: 570 m/s from 354° N, 0/5 flags, closure 7.2%, residual 2.4%
  - Station coords mode: 701 m/s from 1.5° N, same diagnostics
  - Both agree on northward-origin wave — consistent with Gwyn 157° SSE
  - Previous run (17:30-20:30 window) gave wrong direction (189° S)
  - This run (19:15-22:28 window) gives correct direction (354° N)
- Window matters: later window (19:15-22:28) gives cleaner xcorr and
  correct wave direction vs earlier window (17:30-20:30)
- Stale A=accept removed from Step 6 console output
- pre-commit hook installed to block accidental commits to main

### Key result update
Best May 2024 result (supersedes FINDINGS Entry 44):
  570 m/s from 354° N (IPP coords), 3 stations N4RVE/N5BRG/W7LUX
  Window: 2024-05-17T19:15-22:28 UTC
  All 5 diagnostics pass, closure 7.2%, residual 2.4%

### Open issues
1. Fix N4RVE KNOWN_STATIONS coords (48.54N, 123.17W)
2. Add FINDINGS Entry 45 for updated May 2024 result
3. Send updated results to Gwyn

### Resume command
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 34-36
and FINDINGS entries 43-44 on research_gui branch.
Priority: (1) add FINDINGS Entry 45 for May 2024 best result
570 m/s from 354 N, (2) fix N4RVE KNOWN_STATIONS coords,
(3) send updated results to Gwyn."

---
## 37. End of session — 2026-05-28 (very late)

### Accomplished
- IPP prompt verified on --resume: skipped correctly, result reproducible
- max-lag tightening test: 20 min is tightest safe value for May 2024 event
  (true lags +18-19 min; 20 min captures them, excludes aliased -40 min peaks)
- Window selection documented: early window (17:30-20:30) gives wrong xcorr
  peaks due to multipath fading dropouts during F-region recovery post skip zone;
  late window (19:15-22:28) gives clean unambiguous peaks
- FINDINGS Entries 46 added
- max_lag_seconds updated to 1200 s (20 min) in event_20240517.json

### Open issues
1. Send Gwyn email — draft ready, use 570 m/s from 354° N
2. xcorr period-alias: grid search already implemented (tid_doa.py lines 468-530);
   only fix is clean window + tight max-lag. No code change needed.
3. Add --max-lag CLI flag to tid_doa.py (currently config-only)

### Resume command
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 35-37
and FINDINGS entries 44-46 on research_gui branch.
Priority: (1) send updated results to Gwyn: May 2024 570 m/s from
354 N, window 19:15-22:28 UTC, max-lag 20 min recommendation,
(2) grid search peak selector in tid_doa.py,
(3) --max-lag CLI flag for tid_doa.py."

---
## 38. End of session — 2026-05-28 (very late, continued)

### Accomplished
- Synthetic cycle tiling prototype — tested on May 2024 and Jan 2026
- May 2024: W7LUX/N5BRG synthetics work well (xcorr 0.880)
  N4RVE unreliable (asymmetric period, contamination)
  Jan 2026: <1 cycle visible — tiling not applicable
- FINDINGS Entry 47 added
- Minimum cycle requirement established: 1.5-2 full cycles needed

### Open issues
1. Send Gwyn email
2. Implement T=tile key in tid_spect_click.py (optional, future)
3. xcorr period-alias discussion with Gwyn

### Resume command
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 36-38
and FINDINGS entries 45-47 on research_gui branch.
Priority: (1) send updated results to Gwyn: May 2024 570 m/s from
354 N, window 19:15-22:28 UTC, (2) implement T=tile in
tid_spect_click.py, (3) xcorr period-alias discussion with Gwyn."

---
## 39. End of session — 2026-05-29

### Accomplished
- Wave-fit reconstruction implemented in tid_spect_click.py (W key + F key)
  - Multi-point click mode — user clicks along visible cycle
  - F key triggers fit: A*sin(2π/T*(t-t_centre) + φ) + offset
  - Period dialog asks user what fraction of cycle was marked
  - Fit uses ONLY user click points (not spline data)
  - DC offset as free parameter — overlay aligns with clicked points
  - Brown diamond markers show click positions
  - Blue overlay shows wave-fit result on spectrogram
- --wave-only flag: skips Prophet Pass 0, opens directly in wave-fit mode
- Spline CSV no longer required for wave-fit (time grid from seg bounds)
- Console caveat printed when --wave-only: suggests spline if periods differ
- Wave-fit limitations documented (FINDINGS Entry 48):
  - Requires 1.5–2 full cycles visible
  - Periods must be similar across stations for coherent xcorr
  - Jan 2026 dataset: <1 cycle visible, wave-fit not applicable
  - May 2024 dataset: 2.5 cycles, wave-fit worth retesting
- Versions v2.3.5 through v2.3.19 shipped

### Open issues
1. Send Gwyn email
2. Re-run May 2024 with wave-fit (2.5 cycles visible — good testbed)
3. Document wave-fit workflow in WORKFLOW_TUTORIAL.md and MANUAL_TUTORIAL.md
4. Review all docs for accuracy

### Resume command
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 37-39
and FINDINGS entries 46-48 on research_gui branch.
Priority: (1) review all docs for accuracy, (2) re-run May 2024
with --wave-only and compare DOA to spline result,
(3) send updated results to Gwyn."

---
## 40. May 2024 wave-fit DOA — 2026-05-29

### Results
- Wave-fit DOA: 442 m/s from 10° N (1/5 flags, min corr 0.736)
- Spline DOA (best): 570 m/s from 354° N (0/5 flags)
- Direction agreement: 16° difference — within array uncertainty
- Wave-fit validated: works well on 2.5-cycle dataset

### Periods
W7LUX: 79.9 min, N5BRG: 94.8 min (last run; 82.8 min first run better),
N4RVE: 78.4 min

### Open issues
1. Send Gwyn email
2. Consider adding compare/accept step to wave-fit so user can
   choose best fit from multiple F presses

---
## 41. External evaluation session — 2026-05-30

### Session goals
Independently verify Jan 2026 DOA result (239 m/s from 30° NNE)
using external space weather data.

### Accomplished
- Kp index (GFZ Potsdam): 3.3-3.7, substorm timing consistent
- AE index (WDC Kyoto): ~100 nT event, 200-300 nT at predicted onset
- SuperMAG SME (browser): 200-300 nT Jan 18 18:00-22:00 UTC
- SuperDARN RTI (browser): 6 radars, quiet during event window
- GloTEC (NOAA NCEI): downloaded glotec_2026_01_19.tar.gz (270 MB)
  - anomcus product: CONUS TEC anomaly PNG images, 10-min cadence
  - Storm-time +15 TECU enhancement visible; TID not resolvable
  - Difference map: anomaly retreats northward over event window

### Tools created
- validate_external.py (committed to main and research_gui)
  Automates: Kp fetch, AE fetch, GloTEC montage, validation report
  Usage: python3 validate_external.py --date 2026-01-19
         --event-start ...Z --event-end ...Z
         --speed-m-s 239 --azimuth-from 30
         --glotec-dir ~/Downloads/glotec_2026_01_19
         --output-dir ./validation

### What verifies direction (not speed)
- Peak succession: AA6BD leads all stations → confirms NNE origin ✓
- Kp/AE timing: substorm 3-4h before event ✓
- GloTEC: broad storm context consistent ✓

### What remains unverified
- Speed magnitude: needs IONEX or ionosonde foF2
- IONEX: files at CDDIS confirmed, auth required (free NASA Earthdata)
- Additional HamSCI stations: find_event_stations.py not yet run
- Gwyn comparison: 180° alias likely; speed discrepancy unresolved

### Open items
1. Send Gwyn email with all results
2. Register NASA Earthdata → IONEX → verify speed
3. Run find_event_stations.py for cross-validation DOA
4. Commit validation PNGs to examples/ or a new validation/ folder

---

---
## 42. IONEX GPS TEC analysis — 2026-05-30

### Accomplished
- Registered NASA Earthdata (n6rfm), authorized CDDIS_Archive + CDDIS Cloud
- Downloaded JPL 2-hour and UPC 15-minute IONEX for Jan 19 2026
- Parsed IONEX format, extracted VTEC at all 4 station locations
- Plotted raw and detrended TEC time series
- FINDINGS Entry 51 written

### Result
IONEX at standard resolution cannot assess 239 m/s:
- Time resolution (15 min) insufficient for inter-station lag (~17 min)
- Spatial resolution (2.5x5 deg) too coarse for TID wavefront tracking
- Storm-time TEC enhancement dominates over TID amplitude

### Outputs
- ionex_tec_stations.png, ionex_upc_15min_event.png
  (in examples/tid_event_20260119/evaluation/)

---
## 43. Madrigal GPS TEC cross-correlation — 2026-05-30

### Key finding
Jan 2026 GPS TEC data IS ingested in Madrigal (confirmed May 2026).
Typical latency is 2-4 weeks, not 6-12 months as previously assumed.

### Data
- MIT Haystack Madrigal, instrument 8000 (GPS TEC)
- File: gps260119g.002.hdf5 (kindat=3500, gridded TEC)
- Experiment id=100311059
- Access: cedar.openmadrigal.org (open access, no account needed)
- Tool: fetch_madrigal_tec.py (automated retrieval + xcorr)

### Method
- madrigalWeb isprint API, 1-min bins, ≥3 GPS links per bin
- ±3° lat, ±4° lon boxes around each IPP
- 2nd-order polynomial detrend to remove storm background
- Pairwise cross-correlation of detrended TEC

### Results
AA6BD→W7LUX (272° baseline, 1207 km, angle 62° to wave):
  GPS TEC lag:  22 min vs DOA 24.7 min (12% agreement on lag)
  Along-baseline speed: GPS 914 m/s vs DOA 815 m/s
  Implied true speed: ~423 m/s (assumes direction = 30° NNE)

AA6BD→N6RFM, N6RFM→W7LUX: ambiguous (peak at lag=0)

### Interpretation
Direction confirmed NNE by GPS TEC lag sign.
Speed uncertain — GPS TEC implies ~423 m/s vs DOA 239 m/s.
Discrepancy partly geometric (62° angle between baseline and wave).
FINDINGS Entry 52 written.

### Outputs
- madrigal_tec_stations.png, madrigal_tec_detrended.png
- madrigal_tec_1min.png, madrigal_tec_xcorr.png
  (in examples/tid_event_20260119/evaluation/)

---
## 44. Terminology fix: validation→evaluation — 2026-05-30

### Accomplished
- All "validation/validate" (implying certifying truth) removed throughout
- examples/tid_event_20260119/validation/ → evaluation/
- validation_report.txt → evaluation_report.txt
- evaluate_external.py (was validate_external.py) — all internal refs fixed
- All docs, tutorials, scripts updated
- Retained acceptable uses: "cross-validated" (scientific term),
  "visually assess" (checking a trace)
- v2.3.49 tagged

### Open items
1. Send Gwyn email — Jan 2026 results + GPS TEC xcorr finding
2. Run find_event_stations.py for independent DOA cross-check

---
## 45. xcorr trim feature (Gwyn G3ZIL suggestion) — 2026-05-31

### Implemented
- `xcorr_start_utc` / `xcorr_end_utc` optional keys added to event JSON
- tid_doa.py: trims xcorr/DOA window independently of plot window
- Backward compatible — omitting keys preserves prior behaviour
- Confirmation print: `xcorr window trimmed to HH:MM–HH:MM UTC (NNN min)`
- FINDINGS Entry 53 written

### Outcome
Feature works correctly. Applied to Jan 2026 event — results still
inconsistent across CSV file combinations. Root cause is source CSV
quality, not the trim logic (see §46 and Entry 54).

### Open items
1. Send Gwyn email — Jan 2026 results + GPS TEC xcorr finding
2. Re-run cwt-prophet to get reproducible event JSON
3. find_event_stations.py DOA cross-check

---
## 46. Reproducibility investigation — 2026-05-31

### Finding
239 m/s result cannot be reproduced from exported CSVs.
Root cause: GUI cwt-prophet extraction applies phase locking
not preserved in prophet_preview.csv exports.

### xcorr trim feature
Works correctly. Limited by data quality of exported CSVs.

### Action
Re-run cwt-prophet in GUI, save event JSON with max_lag_seconds.
Add reproducibility notes to WORKFLOW_TUTORIAL.md.

### Open items
1. Send Gwyn email
2. Re-run cwt-prophet to get reproducible event JSON
3. find_event_stations.py DOA cross-check

---
## 47. cwt-prophet re-run + reproducible result — 2026-05-31

### Accomplished
- Added `--event-json` CLI arg to tid_spect_click.py (commit 87fd282)
- Wired `E` key to `_export_prophet_csv` (was previously unreachable)
- Re-ran Pass 0 cwt-prophet on all 4 stations
- prophet_preview CSVs committed to examples/tid_event_20260119/
- event_20260119.json updated: all stations method=cwt-prophet
- Best reproducible result: **304 m/s from 10° NNE, 0/5 flags**
  (3 stations: N6RFM + AA6BD + W7LUX, drop AC0G_ND)
- FINDINGS Entry 55 written

### Key finding
239 m/s (Entry 50) is not reproducible from committed files.
304 m/s from 10° NNE is the new canonical reproducible result.
Direction is consistent across both results and GPS TEC confirmation.

### Open items
1. Send Gwyn email — 304 m/s NNE result
2. find_event_stations.py — better 4th station
3. Add --drop-station flag to tid_doa.py
4. WORKFLOW_TUTORIAL.md reproducibility notes ✓ (done this session)

---
## 48. CAPT: Constrained Adaptive Phase Tracking — first results — 2026-06-01

### Implemented
- `capt_extract.py` v0.1.0: Kalman filter extractor seeded from GUI clicks
- `tid_spect_click.py`: S key saves CAPT seed JSON (2–N clicks)
- Committed: `aafc2b0` on research_gui
- FINDINGS Entry 56 written

### Jan 2026 result
- 4-station: 652 m/s, 37° NNE, 2/5 flags
- 3-station (drop AC0G_ND): **211 m/s from 10.6° NNE, 0/5 flags**
- Direction matches prophet canonical (10.3°) to 0.3°
- Better residual and closure than prophet on same subset

### Open items
1. Run CAPT on May 2024 Gwyn event — the real test
2. Tune Kalman parameters for contaminated stations
3. Add to tid_workflow.py
4. Share with Gwyn
5. Send Gwyn email — Jan 2026 results + CAPT first results
6. find_event_stations.py — better 4th station

---
## 49. CAPT limitation finding + extraction roadmap — 2026-06-01

### Added
- `capt_extract.py --method fft|seed|autocorr` (commit 3e08d39)
- `tid_spect_click.py`: Z key undo, live PCHIP spline preview
- Defaults unchanged (method=fft, max_step=0.5)

### Key finding
CAPT does not solve the AA6BD displaced-carrier case. When FFT locks
onto the wrong (near-zero) feature, neither CAPT mode tracks the real
carrier. `--method seed` is equivalent to spline export (X key).
Canonical Jan 2026 result remains prophet (304 m/s, 0/5 flags).

### Extraction roadmap
1. Constrained FFT search (search ±band of previous block) — recommended next
2. Spectrogram ridge-following (path-find on image intensity)
3. Multi-hypothesis tracking (parallel trackers, user picks)

### Open items
1. Implement constrained FFT search
2. Run CAPT on May 2024 Gwyn event — the real test
3. Send Gwyn email
4. find_event_stations.py — better 4th station

---
## 50. Session wrap-up: tooling, docs, workflow fixes — 2026-06-01/02

### Code changes (all merged to main)

**capt_extract.py:**
- `--method tracked`: constrained FFT search ±track-band around Kalman prediction
- `--track-band` (default 0.3 Hz): search half-width for tracked mode
- `--proc-noise` (default 0.02): Kalman process noise tuning
- Sort seed clicks by time (fixes PchipInterpolator error for out-of-order clicks)
- Finding: tracked mode does not solve broad/diffuse carriers (AA6BD)

**tid_spect_click.py:**
- `--no-prophet`: skips Pass 0 auto-run for CAPT seeding and pure spline
- Context-specific key bindings: status bar shows only relevant keys
  (prophet mode vs no-prophet mode vs wave-only mode)

**tid_workflow.py:**
- 7 extraction methods in menu (added wave-fit and CAPT)
- Clear instruction boxes for all methods before GUI launch
- Retry loops when seed/CSV not saved (CAPT, wave-fit, cwt-prophet)
- DOA CSV priority: selected method first (was always spline first — bug)
- Extraction file summary printed before DOA
- Console output logger: full session saved to <event_dir>/runs/<ts>_workflow_console.log

**tid_doa.py:**
- Run logs written to <event_dir>/runs/ (derived from station CSV paths)
- Extraction method summary line in run log output

### Documentation (all merged to main, all consistent)

| Document | Updates |
|----------|---------|
| README | 6-method table, CAPT, --drop, --event-json, Madrigal, tool listing |
| MANUAL_TUTORIAL | Option A=anchor-guided (recommended), Options D+E added, all keys |
| WORKFLOW_TUTORIAL | Option A renamed, Options D+E added, Step 7 output table, Step 8 --drop |
| METHODOLOGY | 6-method table, Step 1d=anchor-guided, Step 1e=CAPT, Step 1f=sgolay-ridge |
| COOKBOOK | cwt-prophet recipe updated (E+P keys), CAPT recipe added |
| TROUBLESHOOTING | --drop in Step 4, CAPT entries, key bindings reference |
| ASSESSING_RESULTS | --drop in station perturbation |
| CHANGELOG | v2.3.51 entry covering all new features |

### Structural fixes
- FINDINGS entries 1-13 promoted from ### work log to ## Entry format
- Both preamble blocks removed (The question / The gate / Open deps)
- Duplicate entries 14-49 removed (earlier session)
- FINDINGS numbering verified clean: 1-57

### Branch state
- main, gwyn-g3zil, research_gui all synced
- All PR branches deleted (local + remote)
- Only 3 branches remain: main, research_gui, gwyn-g3zil

### Open items
1. Run CAPT on May 2024 Gwyn event — the real test
2. Gwyn email — Jan 2026 results + CAPT status
3. find_event_stations.py — better 4th station
4. CAPT tuning slider tool (interactive parameter exploration)

---
## 51. v2.4.0 release — simplified workflow + cleanup — 2026-06-02

### Summary
Major UX overhaul of the extraction workflow. Prophet gets one shot
(E=accept or click+X). Removed CAPT, sgolay-ridge, FFT from workflow
menu. Added resume menu, coords cache, console logging.

### Removed
- capt_extract.py and all CAPT references (code, docs, examples)
- S key (CAPT seed) from tid_spect_click.py
- sgolay-ridge, FFT, CAPT from tid_workflow.py extraction menu
- P=re-run from all status messages and instruction boxes

### Added
- Interactive resume menu (--resume): per-station progress, redo options
- station_coords.json: persistent lat/lon cache in event directory
- ConsoleLogger: full session output to <event_dir>/runs/
- Run logs to event data dir (not repo dir)
- Context-specific key bindings (cwt-prophet vs no-prophet vs wave-only)
- --no-prophet flag for pure spline clicking
- Wave-fit keys (W/F/A) only in --wave-only mode
- Clear instruction boxes for all extraction methods
- Retry loops for all interactive extractions

### Extraction workflow (simplified)
1. Auto-trace shown (Prophet Pass 0)
2. Good → E (accept and export)
3. Not good → click carrier from left to right → X (export spline)
4. Wave-fit: F=fit+save, W=redo, Q=done

### Four extraction methods in workflow menu
1. cwt-prophet (anchor-guided — recommended)
2. autocorr (automated, G3ZIL method)
3. cwt (automated, CWT multi-peak)
4. wave-fit (sine fit to clicked cycle points)

FFT, sgolay-ridge still available via CLI (drf_to_doppler.py --method)
but removed from the guided workflow.

### Open items
1. Run CAPT concepts on May 2024 Gwyn event (if revisited)
2. Gwyn email — results + workflow status
3. find_event_stations.py — better 4th station
4. Test resume menu on real workflow run
5. Merge to main via PR

---
## 52. v2.4.1 — doc/UX fixes — 2026-06-03

### UX
- Prophet one-shot: E=accept, X=click trace (no P=re-run)
- W/F/A only in --wave-only; no live preview in cwt-prophet
- Wave-fit: F=fit+save, W=redo, Q=done
- Clear instruction boxes for all methods
- Status bar cleanup throughout

### Docs
- docs/EXTERNAL_EVALUATION.md created (moved from README)
- Sgolay-ridge removed from both tutorials
- Madrigal example: all required args shown
- Eval output: <event_dir>/runs/external_evaluations/
- PROJECT_STATE 1-35 backfilled from git history
- All docs consistent with simplified workflow

### Open items
1. Gwyn email — results + workflow status
2. find_event_stations.py — better 4th station
3. May 2024 Gwyn event analysis
4. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 53. GloTEC removal + final doc cleanup — 2026-06-03

### Removed
- fetch_glotec.py deleted entirely
- GloTEC analysis removed from evaluate_external.py (functions,
  --glotec-dir arg, report section, main flow)
- GloTEC references removed from all docs, examples, CONTRIBUTORS

### Documentation
- Created docs/EXTERNAL_EVALUATION.md (moved eval section from README)
- Added ASSESSING_RESULTS.md + EXTERNAL_EVALUATION.md to README
  Documentation section (alphabetical listing)
- Renamed EXAMINING_RESULTS.md back to ASSESSING_RESULTS.md
- Removed sgolay-ridge sections from both tutorials
- Wave-fit: ≥0.5 cycles minimum, ≥1.5 recommended (was ≥1.5 required)
- README 5c=autocorr (recommended), 5d=fft (basic)
- Madrigal example: all required args (--stations, --user-*)
- Eval output dir: <event_dir>/runs/external_evaluations/
- Method comparison table: replaced fft with wave-fit
- Workflow Option A: simplified to prophet one-shot (no P=re-run)

### Branch state
- main, research_gui, gwyn-g3zil all synced
- All PR branches cleaned
- v2.4.1 tag + GitHub release created

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 54. EXTERNAL_EVALUATION.md numbering fix — 2026-06-05

### Change
- Added missing ## 1. Full evaluation (evaluate_external.py) heading
- Sections now correctly numbered 1-3
- Merged via PR fix/external-eval-numbering → main, synced all branches

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 55. Kp/AE narrative + fetch_kp_index.py — 2026-06-05

### Added
- fetch_kp_index.py: Kp retrieval from GFZ Potsdam, bar chart with
  storm thresholds (Kp 3, Kp 5), event window, stats box
- EXTERNAL_EVALUATION.md: Geomagnetic Indices section (Kp/AE narrative)
  inserted before Tools table
- EXTERNAL_EVALUATION.md: Kp added to Tools table
- EXTERNAL_EVALUATION.md: ## 4. Kp index section with usage example
- EXTERNAL_EVALUATION.md: Madrigal GNSS TEC narrative added to ## 3.
- Merged via PRs #215, #216 → main, all branches synced

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 56. EXTERNAL_EVALUATION.md cleanup — 2026-06-05

### Changes
- Simplified to 2 numbered sections (was 4)
- ## 1. renamed: "Full evaluation" → "Combined Kp and AE (evaluate_external.py)"
- ## 2. AE index only — removed (redundant with ## 1.)
- ## 3. Kp index standalone — removed (redundant with ## 1.)
- Tools table: fetch_kp_index.py + fetch_ae_index.py removed,
  evaluate_external.py added
- Merged via PR #217 → main, all branches synced

### Note
fetch_kp_index.py and fetch_ae_index.py remain in repo as CLI tools
but are not featured in the guided workflow docs.

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 57. ADVANCED_EVALUATION.md rename — 2026-06-05

### Changes
- docs/EXTERNAL_RESULTS_EVALUATION.md → docs/ADVANCED_EVALUATION.md
- examples/EXTERNAL_RESULTS_EVALUATION.md → examples/ADVANCED_EVALUATION.md
- Internal references updated in ADVANCED_EVALUATION.md
- COOKBOOK.md and README.md references updated
- Link added from EXTERNAL_EVALUATION.md → ADVANCED_EVALUATION.md
- Merged via PR #218 → main, all branches synced

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 58. Cleanup + COOKBOOK.md v2.4.1 fixes — 2026-06-05

### Changes
- COOKBOOK.md: cwt-prophet key bindings updated (removed P, C; fixed E, X descriptions)
- COOKBOOK.md: recommended workflow text corrected for prophet one-shot
- COOKBOOK.md: removed standalone AE index recipe (redundant with evaluate_external.py)
- evaluation/ and evaluation_sw/ output dirs removed from repo (May 2026 event test runs)
- .gitignore: added evaluation/, evaluation_sw/
- Merged via PRs #219, #220 → main, all branches synced

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 59. Doc sweep: stale anchor/Prophet workflow text — 2026-06-06

### Changes
- MANUAL_TUTORIAL.md: Step 0 → "Before you begin", removed C key
- WORKFLOW_TUTORIAL.md: removed C key from Step 6 Option A
- README.md: Step 0 → "Before you begin", added missing step 6 to guided list
- TROUBLESHOOTING.md: removed P/C keys, fixed X key section
- METHODOLOGY.md: replaced anchor workflow description with v2.4.1 E/X workflow
- CI: added .github/workflows/block-research-docs.yml to block
  FINDINGS.md and PROJECT_STATE.md from main via GitHub Action
- Merged via PRs → main, all branches synced

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 60. v2.4.2 release — 2026-06-06

### Summary
Documentation-only release. No code changes to extraction or DOA.

### Changes
- fetch_kp_index.py added (new tool)
- EXTERNAL_EVALUATION.md major rewrite
- ADVANCED_EVALUATION.md renamed
- COOKBOOK.md, MANUAL_TUTORIAL.md, WORKFLOW_TUTORIAL.md,
  TROUBLESHOOTING.md, METHODOLOGY.md, README.md — stale
  anchor/Prophet workflow text removed throughout
- CI: block-research-docs GitHub Action added
- v2.4.2 tag + GitHub release created

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 61. Merge ADVANCED_EVALUATION into EXTERNAL_EVALUATION — 2026-06-07

### Changes
- docs/ADVANCED_EVALUATION.md deleted
- docs/EXTERNAL_EVALUATION.md expanded with: verification strategy,
  peak succession check, GPS TEC geometry note, what external data
  can verify table, SuperMAG SME, SuperDARN RTI, IONEX, summary table
- docs/COOKBOOK.md: updated refs from ADVANCED to EXTERNAL_EVALUATION.md
- README.md: removed ADVANCED_EVALUATION.md from file tree
- examples/ADVANCED_EVALUATION.md retained as Jan 2026 worked example
- Merged via PR → main, all branches synced

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 62. README/WORKFLOW_TUTORIAL cleanup — 2026-06-07

### Changes
- WORKFLOW_TUTORIAL.md: added "Manual step-by-step" section with
  quick command reference (steps 1-6)
- README.md: replaced large manual code block with pointer to
  MANUAL_TUTORIAL.md and WORKFLOW_TUTORIAL.md
- docs/EXTERNAL_EVALUATION.md: merged ADVANCED_EVALUATION content
  (verification strategy, peak succession, GPS TEC geometry,
  SuperMAG, SuperDARN, IONEX, summary table)
- docs/ADVANCED_EVALUATION.md: deleted
- Merged via PRs → main, all branches synced

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 63. v2.4.3 release — 2026-06-07

### Summary
Documentation-only release. No code changes.

### Changes
- EXTERNAL_EVALUATION.md: merged ADVANCED_EVALUATION.md content
- ADVANCED_EVALUATION.md: deleted
- WORKFLOW_TUTORIAL.md: manual step-by-step section added
- MANUAL_TUTORIAL.md: Options A-D restructured, FFT removed
- "sine wave" → "sinusoidal model" throughout
- CI: block-research-docs GitHub Action
- v2.4.3 tag + GitHub release created

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 64. MANUAL_TUTORIAL + WORKFLOW_TUTORIAL doc improvements — 2026-06-07

### Changes
- MANUAL_TUTORIAL.md: Options A-D restructured (cwt-prophet, autocorr,
  cwt, wave-fit); FFT removed from workflow options
- MANUAL_TUTORIAL.md: Step 7 — added tid_doa_config.py instructions
- MANUAL_TUTORIAL.md: max_lag_seconds behavior clarified
- MANUAL_TUTORIAL.md + WORKFLOW_TUTORIAL.md: DRF directory structure
  added with fenced code blocks for correct GitHub rendering
- "sine wave" → "sinusoidal model" throughout all docs
- All stale local branches deleted

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 65. v2.4.4 release — 2026-06-08

### Changes
- METHODOLOGY.md: full waveform cross-correlation explanation added
- README.md: HamSCI PSWS Spectrogram Atlas link added to Documentation;
  various edits
- EXTERNAL_EVALUATION.md: HamSCI LSTID Detection section (## 2.),
  numbering fixed (1-3), Tools table updated, intro expanded
- MANUAL_TUTORIAL.md: Options A-D, Step 7 tid_doa_config.py,
  max_lag_seconds clarified, DRF directory structure added
- WORKFLOW_TUTORIAL.md: manual step-by-step added, DRF structure added
- METHODOLOGY.md: two minor edits
- "sinusoidal model" wording throughout

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 66. v2.4.5 release — 2026-06-09

### Summary
Documentation cleanup release. No code changes.

### Changes
- EXTERNAL_EVALUATION.md: removed off-topic content, minor edits
- README.md: various edits and cleanup
- v2.4.5 tag + GitHub release created

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)

---
## 67. fetch_madrigal_tec.py --config support — 2026-06-11

### Changes
- fetch_madrigal_tec.py: added --config FILE option, auto-fills
  --date, --event-start, --event-end, --stations from
  tid_workflow_event.json. CLI args still override config values.
  Verified working against June 2026 event (Madrigal data not yet
  available for that date — 2-4 week latency, expected).

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event: best DOA result so far is 533 m/s @ 137°
   (JJMP, KV0S_MO, AC0G_ND, N6RFM_5, 1 flag); Madrigal TEC
   verification pending data availability

---
## 68. Madrigal availability check + --my-station — 2026-06-11

### Changes
- docs/EXTERNAL_EVALUATION.md: added Madrigal data-availability check
  command (getExperiments) and updated usage example to --config
- tid_workflow.py: added --my-station NAME option to process the
  user's own station first in Step 3 (window selection)
- WORKFLOW_TUTORIAL.md: documented --my-station in CLI reference
- Confirmed Madrigal GPS TEC data available through 2026-06-04 only
  (June 6 event TEC verification still pending)

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event: best DOA result 533 m/s @ 137° (JJMP, KV0S_MO,
   AC0G_ND, N6RFM_5, 1 flag); Madrigal TEC verification pending
   data availability (check again late June/early July)

---
## 69. v2.5.0 release — 2026-06-11

### Summary
Feature + doc release.

### Changes
- fetch_madrigal_tec.py: --config support
- tid_workflow.py: --my-station support
- METHODOLOGY.md, EXTERNAL_EVALUATION.md, README.md, WORKFLOW_TUTORIAL.md
  doc improvements
- v2.5.0 tag + GitHub release created

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event: best DOA result 533 m/s @ 137° (JJMP, KV0S_MO,
   AC0G_ND, N6RFM_5, 1 flag); Madrigal TEC verification pending
   data availability (check again late June/early July)
## 70. Combined Madrigal wrapper + EXTERNAL_EVALUATION restructure — 2026-06-12
### Changes
- New script run_madrigal_tools.py: combined wrapper for the two
  Madrigal-based external evaluation tools (fetch_madrigal_tec.py for
  GNSS TEC, hamsci_LSTID_detection for HF LSTID detection).
  - --setup: one-time shared Madrigal user info, saved to
    ~/.config/psws/madrigal_user.json, reused by both tools
  - --event <event_dir> --tool gnss|lstid|both [--download] [--dry-run]
  - GNSS TEC output -> <event_dir>/gnss_tec/
  - HF LSTID plots/summary -> <event_dir>/lstid/
- docs/EXTERNAL_EVALUATION.md: added new "Combined wrapper" section
  (placed after Kp/AE, before the individual Madrigal tool sections;
  sections renumbered accordingly), expanded HamSCI LSTID Detection
  section with setup/run instructions and the polars[rtcompat] fix
  for CPUs lacking AVX2/FMA/BMI (SIGILL crash otherwise).
- Verified end-to-end on June 6 2026 event:
  - GNSS TEC: now available and working (fetch_madrigal_tec.py ran
    successfully, report + plots generated)
  - HF LSTID: pipeline runs cleanly after polars[rtcompat] fix;
    Madrigal instrument 8308 (HF spots) has no data for 2026-06 yet
    (confirmed via globalDownload.py — 2025 dates work fine)
### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event: best DOA result 533 m/s @ 137° (JJMP, KV0S_MO,
   AC0G_ND, N6RFM_5, 1 flag); GNSS TEC now retrieved (see
   gnss_tec/madrigal_tec_report.txt) — review cross-correlation
   results against DOA. HF LSTID (Madrigal inst 8308) still has no
   June 2026 data — retry late June/early July alongside any further
   TEC follow-up.
---
## 71. Madrigal HF spot data gap (2026) + GNSS TEC review — 2026-06-12
### Changes
- GNSS TEC review for June 6 2026 event (533 m/s @ 137°, 1/5 flags):
  cross-correlation lags across the 4-station tetrad are internally
  inconsistent for a single plane wave (e.g. JJMP->N6RFM_5 = +40 min
  vs JJMP->KV0S_MO + KV0S_MO->N6RFM_5 = -35 min). This corroborates
  the DOA tool's own flagged residual — likely multi-wave
  superposition rather than a single coherent LSTID.
- GNSS TEC review for Jan 19 2026 event (195 m/s @ 9°, reference
  event in fetch_madrigal_tec.py docs): AA6BD->N6RFM baseline gives
  GPS TEC lag 60 min -> true phase speed ~95 m/s, same order of
  magnitude as DOA (195 m/s) but off by ~2x. AA6BD->W7LUX and
  N6RFM->W7LUX both show lag=0 (likely storm-background, per the
  tool's own caveat) -- inconclusive. Weak-to-moderate corroboration
  overall.
- **Madrigal HF spot data gap discovered**: instrument 8308
  (RBN/PSKReporter/WSPRNet spots, used by hamsci_LSTID_detection) has
  NO experiments uploaded for any date in 2026 so far (checked
  2026-01-01 through 2026-06-06; Nov-Dec 2025 uploads are present and
  complete except one gap on 2025-12-10). This is NOT a 2-4 week
  latency issue -- it's a 5+ month gap starting ~2026-01-01.
  - Confirmed via: `globalDownload.py ... --inst=8308` for
    01/01/2026-01/14/2026 returns zero "Analyzed exp" lines.
  - Effect: hamsci_LSTID_detection (and run_madrigal_tools.py --tool
    lstid) cannot currently produce results for any 2026 event --
    pipeline runs cleanly but always reports "No HDF5 files found".
  - This is independent of the local polars[rtcompat] fix (§70),
    which remains correct/needed.
  - Likely worth flagging to HamSCI/hamsci_LSTID_detection
    maintainers, as it affects their tool generally, not just this
    wrapper.
### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event: best DOA result 533 m/s @ 137° (JJMP, KV0S_MO,
   AC0G_ND, N6RFM_5, 1 flag); GNSS TEC retrieved but internally
   inconsistent across baselines -- consistent with multi-wave
   superposition already flagged by the DOA tool. HF LSTID unusable
   until Madrigal inst 8308 resumes 2026 uploads (see above).
4. Madrigal inst 8308 (HF spots) has no 2026 data as of 2026-06-12 --
   periodically recheck (`globalDownload.py --inst=8308`) and/or
   report the gap upstream to HamSCI.
---

## 72. Reference event search — 2026-06-16

### Goal
Identify a well-studied LSTID event for which all three data sources
exist simultaneously:
- Grape HF Doppler (PSWS network, available from late 2019 onward)
- Madrigal inst 8308 (HF spots: RBN/PSKReporter/WSPRNet, available
  through end of 2025)
- Madrigal inst 8000 (GNSS TEC, typically 2-4 week latency)

### Rationale
Need a ground-truth event with independently agreed direction and speed
to validate the toolkit end-to-end. The Nov 3 2017 event (Frissell et al.
2022 GRL, ~163°, ~1200 km/hr) predates the Grape network. The usable
window is late 2019 through end of 2025.

### Primary candidate
May 10-12 2024 Mother's Day storm (G5, most intense storm since 2003).
- Heavily studied in the literature with agreed equatorward LSTID
- Grape network well-deployed by May 2024
- Madrigal inst 8308 should have 2024 data
- Madrigal inst 8000 GNSS TEC available
- Need: confirm Madrigal availability for both instruments, identify
  a clean single-LSTID window within the storm

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event follow-up (see §71)
4. Madrigal inst 8308 2026 data gap — recheck periodically
5. Reference event: check Madrigal inst 8308 + 8000 availability
   for May 10-12 2024; identify clean LSTID window
## 73. Reference event confirmed — 2026-06-16

### Result
May 10-12 2024 Mother's Day storm confirmed as reference event.
All three data sources verified present:
- Madrigal inst 8308 (HF spots): 3 experiments, May 10/11/12
  ids: 100012134, 100012063, 100012089
- Madrigal inst 8000 (GNSS TEC): 4 experiments, May 9/10/11/12
  ids: 100011063, 100011154, 100011008 + May 12
- Grape HF: network well-deployed by May 2024 (Gwyn has processed data)

### Next step
Identify a clean single-LSTID window within the storm for which
Grape DOA, Madrigal HF LSTID detection, and Madrigal GNSS TEC
cross-correlation all agree on direction and speed.
Gwyn's processed May 2024 data is the starting point (see §7).

### Open items
1. May 2024 reference event analysis (this item)
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event follow-up (see §71)
4. Madrigal inst 8308 2026 data gap — recheck periodically

---
## 74. Period-resolved multi-station DOA investigation — 2026-06-12

### Summary
Investigated extending tid_doa.py's broadband cross-correlation DOA
to a period-resolved method, inspired by Crowley & Rodrigues (2012),
"Characteristics of traveling ionospheric disturbances observed by
the TIDDBIT sounder," Radio Science 47, RS0L22,
doi:10.1029/2011RS004959. TIDDBIT performs cross-spectral analysis in
sliding windows to get TID speed/direction/wavelength AS A FUNCTION
OF PERIOD, rather than one broadband estimate per event.

### What was tried (POC script, not merged — see archive note below)
1. Single station pair, single-segment CSD (phase lag vs period,
   coherence trivially 1.0) — confirmed mathematically consistent
   with tid_doa.py's broadband lag, decomposed by Fourier period.
   No new diagnostic information by itself.
2. Multi-station (3 stations, Jan 2026 event), Welch-averaged CSD/
   coherence per period bin, period-specific DOA inversion reusing
   tid_doa.py's lstsq slowness-vector geometry. RESULT: coherence
   uniformly low (<0.25) at ALL periods, including the validated
   60-90 min TID band — because Welch averaging needs multiple wave
   cycles within the window to be meaningful, and our typical
   2-3 hour event windows contain fewer than 2 cycles of an
   LSTID-period wave.
3. Multi-station, chunk-consistency check (3 non-overlapping ~44-min
   sub-windows, single-segment CSD per chunk, no coherence filter,
   reliability via cross-chunk agreement instead). RESULT: chunks
   resolve only periods shorter than the chunk length itself
   (11-45 min), well below the actual ~60-90 min TID period, so none
   of the chunks see the real wave — results scatter (300-3000 m/s,
   azimuth swings 160-350 deg) with no convergence near the known
   broadband result (239 m/s @ 30 deg).

### Core finding (NEEDS FURTHER INVESTIGATION, not rejected)
Our standard input is a single ~2-3 hour TID passage (1-2 wave
cycles at LSTID periods) — this is the expected and normal data
shape for HamSCI PSWS event capture, not a limitation to work around
by sourcing longer data. Both FFT-based period-resolution approaches
tried (Welch coherence, chunk consistency) need several independent
wave cycles to produce a reliable period axis, which a single 2-3
hour passage structurally cannot provide. The mismatch is between
the TIDDBIT method's data regime (continuous multi-hour-to-day
sounder campaigns) and ours (one passage per event) — not a tuning
problem, and not something a different dataset choice fixes, since
2-3 hour single-passage events are exactly the intended use case.

### Possible directions for further investigation
- Parametric/model-based period estimation (e.g. matching pursuit,
  Prony's method, or a small number of competing sinusoidal-model
  fits) that may extract more than one period from a single 1-2
  cycle window without needing FFT-style averaging
- Investigate whether the existing wave-fit (--wave-only) extraction,
  applied separately to different candidate period bands per
  station, could substitute for spectral decomposition
- Bayesian/multi-model approach: fit competing single- and dual-wave
  models to the broadband lags directly (already-flagged high RMS
  residual events, like June 6 2026, are the natural test case) and
  compare evidence, rather than trying to resolve a period axis
- Revisit FFT/Welch-based period resolution only if a future
  continuous multi-hour capture mode is added to the toolkit

### Artifacts
- POC script (3 iterations) not merged into repo — exploratory only,
  kept in chat history / outputs, not committed to research_gui or
  main. Re-derive from this PROJECT_STATE entry if revisiting.

### Open items
1. May 2024 Gwyn event analysis
2. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
3. June 6 2026 event: best DOA result 533 m/s @ 137° (JJMP, KV0S_MO,
   AC0G_ND, N6RFM_5, 1 flag); Madrigal TEC verification pending
   data availability (check again late June/early July)
4. Period-resolved multi-station DOA (TIDDBIT-style) — needs a
   different estimation approach suited to 1-2 cycle windows; see
   §70 for what was tried and possible directions

---
## 75. Jan 2026 reference value correction + residual-subtraction validation — 2026-06-12 (2026-06-20 session)

### Correction
§74 (and earlier chat-session notes) cited "239 m/s @ 30°" as the
Jan 2026 reference DOA result. This is WRONG — per §46/§47, 239 m/s
was found non-reproducible from exported CSVs as far back as
2026-05-31. The canonical, reproducible result is:

  **304.3 m/s, wave from 10.3° (true bearing), MSTID**
  3 stations: N6RFM, AA6BD, W7LUX (cwt-prophet extraction,
  AC0G_ND dropped — SNR fades after ~01:18 UTC)
  All 5 diagnostics pass. Config: examples/event_20260119.json
  (station list filtered to drop AC0G_ND).

  Re-verified today: `python3 tid_doa.py` on this 3-station config
  reproduces 304.3 m/s @ 10.3° exactly.

Note: examples/event_20260119.json's "_comment" field still says
"239 m/s from 30° NNE" — this is stale and should be corrected to
304 m/s / 10° in a follow-up doc fix.

### Residual-subtraction method — validated negative control
Built a second POC (tid_doa_residual.py, separate from the §74
period-resolution attempts) implementing the matching-pursuit /
iterative-subtraction approach suggested as a follow-up direction in
§74: fit a single sinusoid per station via nonlinear least squares,
subtract it, re-run the same broadband cross-correlation DOA on the
residual. If a coherent second wave exists, the residual DOA should
show reasonable correlation (>0.4) and a physically plausible speed;
if not, low correlation / unphysical speed is expected.

Run against the CORRECT canonical 3-station Jan 2026 dataset
(N6RFM, AA6BD, W7LUX, cwt-prophet, AC0G_ND dropped):
  - Step 1 (raw, top-peak-only): 298.6 m/s @ 10.1° — matches the
    canonical 304.3 m/s @ 10.3° to ~2% (small difference expected:
    this POC uses top-correlation-peak only, not solve_doa's full
    triangle-closure peak selection)
  - Step 4 (residual after single-wave subtraction): 555.4 m/s @
    333.8°, mean|corr|=0.191 (well below 0.4), RMS lag residual
    100% of mean — NO coherent second wave found

RESULT: clean negative control. The method correctly finds nothing
in a known single-wave event (Jan 2026 passes all 5 tid_doa.py
diagnostics, RMS residual only 0.4-2.8% depending on extraction
method) rather than manufacturing a spurious second wave. This
validates the method is safe to try on the June 6 2026 event, which
DID show a high (41%) plane-wave RMS residual and is a natural
candidate for "is this actually two superimposed waves."

### Artifacts
- tid_doa_residual.py — not yet committed to repo (exploratory POC,
  untracked in working tree). Validated against Jan 2026 control.
  Next step: run unmodified against June 6 2026 event
  (JJMP/KV0S_MO/AC0G_ND/N6RFM_5, 533 m/s @ 137°, 41% RMS residual)
  to test for a real second wave.
- tid_doa_spectral.py — superseded by tid_doa_residual.py; kept only
  for the negative-result documentation in §74. Not committed.

### Open items
1. May 2026 event at ~/Downloads/tid_event_20260516 (--resume)
2. June 6 2026 event: best DOA result 533 m/s @ 137° (JJMP, KV0S_MO,
   AC0G_ND, N6RFM_5, 1 flag, 41% RMS residual); Madrigal TEC
   verification pending data availability (check late June/early July)
3. Run validated tid_doa_residual.py against June 6 2026 event to
   test whether the 41% RMS residual reflects a real second wave
4. Fix stale "239 m/s from 30° NNE" comment in
   examples/event_20260119.json (-> 304 m/s / 10°)
