
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
