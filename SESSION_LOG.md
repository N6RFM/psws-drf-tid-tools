# Session Log — psws-drf-tid-tools

---

## Session 2026-05-25

### Branch
research_gui

### Resume prompt
"Continuing psws-drf-tid-tools research session. Read PROJECT_STATE.md
sections 17-21 and FINDINGS entries 21-29 on research_gui branch.
Key open question: reconcile our 267 m/s WSW result with Gwyn's
979 m/s SSE. Email to Gwyn drafted and ready to send."

### Best DOA result
4 stations (W7LUX, AC0G_ND, N4RVE, N5BRG), sgolay-ridge, IPP coords.
267 m/s from 242° (WSW), all diagnostics pass. Window 18:29-19:06 UTC.

### Tools implemented
- tid_quicklook.py — fullday spectrogram TID window selector
- tid_spect_click.py — corridor clicking + sgolay-ridge preview
- drf_to_doppler.py --method sgolay-ridge — 2D STFT ridge tracker
- tid_workflow.py — complete 10-step guided workflow wrapper

### Key findings
- Entry 22: 4-station IPP result 267 m/s WSW
- Entry 23: auto FFT fails diagnostics, sgolay-ridge passes
- Entry 24: full method comparison FFT/autocorr/sgolay-ridge
- Entry 26: CRITICAL — diagnostics are internal consistency only
- Entry 28: comprehensive method comparison summary
- Entry 29: EMD correctly finds LSTID at 90 min, 540s phase offset
  vs sgolay-ridge

### Critical open questions
1. Gwyn 979 m/s SSE vs our 267 m/s WSW — email drafted, needs sending
2. EMD DOA — run on all 4 stations, compare with sgolay-ridge
3. tid_workflow.py thumbnail window hardcoded to 17-21h

### Pending work (priority order)
1. Send email to Gwyn
2. EMD on all 4 stations → DOA comparison
3. FIF implementation if EMD mode mixing is a problem
4. --method cwt-track (CWT + linear extrapolation, Gwyn approach)
5. Test tid_workflow.py on fresh event with well-aligned windows
6. Method cleanup (autocorr, cwt, bandpass) — deferred

### Commits this session
Run: git log --oneline research_gui | head -30
