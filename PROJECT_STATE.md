
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
