# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Lives on the
`research-doppler-extraction` branch. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-19  |  **Status: PAUSED — awaiting G3ZIL reply**

---

## 1. One-paragraph status

Main is at **v1.6.5** with a complete end-to-end mixed FFT/autocorr
workflow shipped. The research branch (`research-doppler-extraction`)
is paused pending Gwyn's reply on two questions. The investigation
into FFT vs autocorr Doppler extraction is substantially complete on
the analysis side — two real events, 1,260 synthetic Monte Carlo
trials, two PDF reports, and a full decision workflow now integrated
into the pipeline. **Do not start new analysis until Gwyn replies.**

## 2. Main branch — current release state (v1.6.5)

| Version | Feature |
|---------|---------|
| v1.5.0 | Result diagnostics + per-run log (tid_doa.py) |
| v1.6.0 | drf_spectrogram.py --overlay for visual inspection |
| v1.6.1 | Fix inter-method r display |
| v1.6.2 | tid_doa.py optional "method" field for provenance |
| v1.6.3 | analyze_event.sh per-station method selection |
| v1.6.4 | analyze_event.sh interactive resume menu |
| v1.6.5 | drf_to_doppler.py v1.1.1 --method fft|autocorr on main |

**Complete mixed-method pipeline (all on main v1.6.5):**
```
drf_inspect.py          → confirm subchannel
drf_spectrogram.py      → visual scan, identify TID window
analyze_event.sh        → full pipeline with method selection:
  Stage 3/8: extract_with_overlay() per station
    - runs both FFT and autocorr extractions
    - shows drf_spectrogram --overlay with inter-method metrics
    - asks operator: which method better tracks the carrier?
    - records choice in station_methods.txt
  Stage 10: event.json with "method" field per station
  tid_doa.py            → DOA with method in run log
```

## 3. Research branch — evidence summary

### 3.1 Falsifiable gate — PASSED
Clean W7LUX, 17 May 2024: SNR delta 0.0 dB, r=0.933, autocorr
3x smoother (btb std 0.13 vs 0.38 Hz).

### 3.2 Real data — 17 May 2024 LSTID
Data: `~/Downloads/gywn_tid_event_20240517/`
Window: 18:00-20:00 UTC, 60s cadence.

| Pair | Band | FFT r | Autocorr r | Delta |
|------|------|-------|------------|-------|
| AC0G_ND/W7LUX | 60-120 min | 0.752 | 0.929 | +0.177 |
| AC0G_ND/W7LUX | Raw curve | 0.576 @+19min | 0.705 @+22min | +0.129 |
| N4RVE/N5BRG | 60-120 min | 0.740 | 0.894 | +0.154 |
| N4RVE/N5BRG | Raw curve | 0.556 @-29min | 0.485 @-27min | -0.071 |

Lag discrepancy: our +22 min vs Gwyn's +35 min on AC0G_ND/W7LUX.
Stable across window widths. Pending clarification (blocker 1).

### 3.3 Real data — 19 Jan 2026 MSTID
Data: `~/Downloads/tid_event_20260119/`
Window: 00:00-01:10 UTC, 10s cadence.

| Method | Stations | Speed | Direction | Diagnostics |
|--------|----------|-------|-----------|-------------|
| FFT | 3 (original) | 193 m/s | 190° | All pass ✓ |
| Autocorr | 3 | 335 m/s | 196° | 2 fail ✗ |
| FFT | 6 | 709 m/s | 223° | 2 fail ✗ |
| Autocorr | 6 | 774 m/s | 223° | 2 fail ✗ |

Autocorr wrong-peak lock on N6RFM->AA6BD (lag/period=1.08).
FFT 3-station is the only reliable result.

### 3.4 Synthetic Monte Carlo — 1,260 trials
Files: `research/synthetic/`. Both PDF reports in `research/`.

| Wave | Condition (SNR=40dB) | FFT lock% | AC lock% | Advantage |
|------|----------------------|-----------|----------|-----------|
| MSTID | eps=0.0-0.7 | 100 | 100 | None |
| MSTID | eps=1.0 | 63 | 93 | AC +30pp |
| LSTID | eps=0.5-0.7 | 100 | 60-90 | FFT +10-40pp |
| LSTID | eps=1.0 | 10 | 37 | AC +27pp |

## 4. What is BLOCKING (research branch)

Two open questions pending Gwyn's reply to 2026-05-18 email:

1. **Lag discrepancy on AC0G_ND/W7LUX** — our +22 min vs his +35
   min. Does his pipeline apply phase unwrapping, carrier drift
   removal, or any smoothing beyond lag-1 with no detrending?

2. **N5BRG antenna channel** — S000038 (NS) or S000040 (EW)?

## 5. Synthesis — when to use each method

| Condition | Recommendation |
|-----------|---------------|
| Clean (eps < 0.2) | Either — identical |
| Contaminated, lag < 0.3 periods | Autocorr preferred |
| Contaminated, lag 0.3-0.5 periods | FFT preferred |
| Heavy contamination, ambiguous curve | Neither; use diagnostics |
| Unknown | FFT (default) |

Use `drf_spectrogram.py --overlay` to check inter-method r and RMS
diff before choosing. Decision guide in METHODOLOGY.md Step 1b.

## 6. Complete repo contents (research branch additions)

### Root level
- `FINDINGS.md` — work log entries 1-8
- `PROJECT_STATE.md` — this file
- `CONTRIBUTORS.md` — N6RFM and G3ZIL

### docs/
- `METHODOLOGY.md` — Step 1b visual inspection + clean/contaminated figure
- `fig_clean_vs_contaminated.png`
- `fig_overlay_clean.png`, `fig_overlay_contaminated.png`

### research/
- `build_report.py` — real-data PDF report builder
- `xcorr_lag_plot.py` — xcorr curve plotter (verified)
- `xcorr_both_pairs_fft.png`, `xcorr_both_pairs_autocorr.png`
- `comparison_fft_vs_autocorr_jan19.png`, `comparison_table_jan19.png`
- `event_autocorr_3stn.json`, `event_fft_6stn.json`, `event_autocorr_6stn.json`
- `psws_autocorr_research_report.pdf`

### research/synthetic/
- `synthetic_tid_experiment.py`, `run_chunk.py`, `build_synthetic_report.py`
- `synthetic_full_results.png`, `synthetic_example_traces.png`
- `summary_combined.csv`, `chunks/chunk_*.csv`
- `synthetic_experiment_report.pdf`

## 7. Data (local disk only, NOT in repo)

- `~/Downloads/gywn_tid_event_20240517/` — May 2024 LSTID
  ac0g_nd: subchannel 4. w7lux: single. n4rve: subchannel 4.
  n5brg: S000038 (NS), marginal SNR at event time.
- `~/Downloads/tid_event_20260119/` — Jan 2026 MSTID
  n6rfm, aa6bd, w7lux: subchannel 0. ac0g_nd: subchannel 4.
  kb4se: (33.3958, -84.4583). kc4le: (33.3125, -86.875).

## 8. Next steps (when Gwyn replies)

1. Resolve lag discrepancy — document or implement fix.
2. Confirm N5BRG channel — re-run Entry 5 if different.
3. Run v1.5.0 diagnostics on autocorr extractions, May 2024.
4. Write formal finding — two events + synthetic, full table.
5. Consider merging research docs to main (FINDINGS, CONTRIBUTORS,
   research/ folder) — code is already on main.
6. Production PR for autocorr as documented method only when:
   formal finding written, both events consistent, gate passed.

## 9. Working discipline

- Always on `main` when running the pipeline.
- Research branch only for the FFT vs autocorr investigation.
- Verify before acting. drf_inspect -> SNR check -> correlate.
- Do not overclaim. Two events + synthetic = strong evidence, not
  a conclusion. Lag discrepancy unresolved.
- Always pull before pushing (Gwyn has write access).
- This is a pause point. Do not start new analysis until Gwyn replies.
