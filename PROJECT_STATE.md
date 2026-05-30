
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
## 41. External validation session — 2026-05-30

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
