# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Lives on the
`research-doppler-extraction` branch. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-18  |  **Status: PAUSED — awaiting G3ZIL reply**

---

## 1. One-paragraph status

v1.5.0 is shipped on `main` (protected, PR-only). All active work
is on `research-doppler-extraction`. The investigation into FFT vs
complex-autocorrelation Doppler extraction is **substantially
complete on the analysis side and paused pending Gwyn's reply.**
Results have been obtained on two real events (17 May 2024 LSTID
and 19 Jan 2026 MSTID), a Monte Carlo synthetic experiment
(1,260 trials) has been run, committed, and reported, and all
supporting figures, data, scripts, and two PDF reports have been
committed to the repo. Two clarifying questions remain open:
(1) whether Gwyn's extraction pipeline applies any steps beyond
lag-1 with no detrending, explaining the +13-minute lag discrepancy
on AC0G_ND/W7LUX; and (2) which N5BRG antenna channel he used.
No production PR is warranted until these are resolved and a formal
written finding is complete. **Do not start new analysis until
Gwyn replies.**

## 2. Repo / branch state

- **`main`**: v1.5.0, PROTECTED. Do NOT push directly.
- **`research-doppler-extraction`**: active branch, paused.
  All work committed and pushed. Recent commits (newest first):
  - `latest`   Add xcorr_both_pairs figures (repo audit)
  - `prev`     Add research figures and PDF reports
  - `5c337dd`  Fix ampersand in both report builders
  - `906a028`  Full refresh: PROJECT_STATE and FINDINGS through Entry 8
  - `a45b1ac`  Add synthetic experiment data and figures
  - `776ec22`  Add synthetic Monte Carlo experiment scripts
  - `8fa447b`  METHODOLOGY: clean-vs-contaminated figure
  - `5d6e109`  Fix: remove # method= CSV comment header (v1.1.1)
  - `9bb398a`  Add --method autocorr (G3ZIL lag-1 extractor)

- **Key tools** (invoke by path from inside data folders):
  - `~/psws-tools-pr/drf_to_doppler.py` v1.1.1 — fft/autocorr
  - `~/psws-tools-pr/tid_pair.py` — pairwise cross-correlation
  - `~/psws-tools-pr/tid_doa.py` — multi-station DOA
  - `~/psws-tools-pr/drf_inspect.py` — DRF metadata
  - `~/psws-tools-pr/research/xcorr_lag_plot.py` — xcorr plotter
  - `~/psws-tools-pr/research/synthetic/` — synthetic experiment

- **Workflow note:** always `git pull --no-rebase` before pushing —
  Gwyn has write access and may push independently.

## 3. The research question

> On identical I/Q input, does complex-autocorrelation Doppler
> extraction (G3ZIL method) produce more coherent,
> contamination-robust results than FFT carrier tracking?

**Answer so far: it depends on wave type and lag-period ratio.**
Neither method is universally superior.

## 4. Complete evidence summary

### 4.1 Falsifiable gate — PASSED

Clean W7LUX, 17 May 2024, 18:00-20:00 UTC, 60s cadence:
- SNR delta: 0.0 dB (gate < 5 dB) ✓
- Pearson r between methods: 0.933 (gate > 0.93) ✓
- Autocorr 3x smoother: btb std 0.13 vs 0.38 Hz ✓

### 4.2 Real data — 17 May 2024 LSTID (Gwyn's reference event)

Data: `~/Downloads/gywn_tid_event_20240517/`
Window: 18:00-20:00 UTC, 60s cadence.
Gwyn's result (V1.2 slide): 979 +/-80 m/s @ 157° +/-6°, period ~58 min.
Note: his baselines are midpoint-to-midpoint; lags unaffected,
speeds differ ~8% from station-to-station.

| Pair | Band | FFT r | Autocorr r | Delta |
|------|------|-------|------------|-------|
| AC0G_ND/W7LUX | 40-90 min | 0.829 | 0.896 | +0.067 |
| AC0G_ND/W7LUX | 60-120 min | 0.752 | 0.929 | +0.177 |
| AC0G_ND/W7LUX | Raw curve | 0.576 @+19min | 0.705 @+22min | +0.129 |
| N4RVE/N5BRG | 40-90 min | 0.772 | 0.823 | +0.051 |
| N4RVE/N5BRG | 60-120 min | 0.740 | 0.894 | +0.154 |
| N4RVE/N5BRG | Raw curve | 0.556 @-29min | 0.485 @-27min | -0.071 |

N4RVE/N5BRG raw lag (-27 min) matches Gwyn's 27 min exactly.
AC0G_ND/W7LUX lag discrepancy: our +22 min vs Gwyn's +35 min —
stable across window widths. Pending clarification (blocker 1).

### 4.3 Real data — 19 Jan 2026 MSTID (original reference event)

Data: `~/Downloads/tid_event_20260119/`
Window: 00:00-01:10 UTC, 10s cadence. 6 stations SNR > 30 dB.

| Method | Stations | Speed | Direction | Diagnostics |
|--------|----------|-------|-----------|-------------|
| FFT | 3 (original) | 193 m/s | 190° | All pass ✓ |
| Autocorr | 3 | 335 m/s | 196° | 2 fail ✗ |
| FFT | 6 | 709 m/s | 223° | 2 fail ✗ |
| Autocorr | 6 | 774 m/s | 223° | 2 fail ✗ |

Autocorr wrong-peak lock on N6RFM->AA6BD (lag/period = 1.08).
Triangle closure diagnostic correctly identifies this.
FFT 3-station (193 m/s @ 190°, MSTID) is the only reliable result.

### 4.4 Synthetic Monte Carlo — 1,260 trials

Signal model: two-phasor I/Q (F-region + E-region at ratio epsilon).
Known ground truth lag. Files: `research/synthetic/`.

| Wave | Condition (SNR=40dB) | FFT lock% | AC lock% | Advantage |
|------|----------------------|-----------|----------|-----------|
| MSTID | eps=0.0-0.7 | 100 | 100 | None |
| MSTID | eps=1.0 | 63 | 93 | AC +30pp |
| LSTID | eps=0.5-0.7 | 100 | 60-90 | FFT +10-40pp |
| LSTID | eps=1.0 | 10 | 37 | AC +27pp (both fail) |

Reproduces both real-event observations mechanistically.
Wrong-peak lock on Jan 2026 MSTID explained by lag-period
ambiguity (lag = 1.08 periods -> comparable xcorr peaks).

## 5. What is BLOCKING

Two open questions, both pending Gwyn's reply to 2026-05-18 email:

1. **Lag discrepancy on AC0G_ND/W7LUX** — our +22 min vs his +35
   min. Does his pipeline apply phase unwrapping, carrier drift
   removal, or any smoothing beyond lag-1 with no detrending?

2. **N5BRG antenna channel** — S000038 (NS) or S000040 (EW)?
   Both differ materially at event time. Affects like-for-like
   validity of Entry 5.

Everything else is resolved and committed. Do not start new
analysis until Gwyn replies.

## 6. Complete repo contents (research branch additions)

### Root level
- `FINDINGS.md` — full work log, entries 1-8
- `PROJECT_STATE.md` — this file
- `CONTRIBUTORS.md` — N6RFM and G3ZIL
- `drf_to_doppler.py` v1.1.1 — adds --method autocorr

### docs/
- `METHODOLOGY.md` — clean-vs-contaminated figure added (§2.2)
- `fig_clean_vs_contaminated.png` — N4RVE/W7LUX vs AC0G_ND/W7LUX

### research/
- `build_report.py` — real-data PDF report builder
- `xcorr_lag_plot.py` — xcorr curve plotter (verified)
- `xcorr_both_pairs_fft.png` — both pairs, FFT extraction
- `xcorr_both_pairs_autocorr.png` — both pairs, autocorr extraction
- `comparison_fft_vs_autocorr_jan19.png` — Jan 2026 pair curves
- `comparison_table_jan19.png` — Jan 2026 4-config summary table
- `event_autocorr_3stn.json` — Jan 2026 autocorr 3-station config
- `event_fft_6stn.json` — Jan 2026 FFT 6-station config
- `event_autocorr_6stn.json` — Jan 2026 autocorr 6-station config
- `psws_autocorr_research_report.pdf` — real-data report

### research/synthetic/
- `synthetic_tid_experiment.py` — signal model, extractors, analysis
- `run_chunk.py` — chunked Monte Carlo runner
- `build_synthetic_report.py` — synthetic PDF report builder
- `synthetic_full_results.png` — 2x4 panel performance figure
- `synthetic_example_traces.png` — example Doppler + xcorr curves
- `summary_combined.csv` — per-condition statistics (84 rows)
- `chunks/chunk_*.csv` — 1,260 raw trial results (6 files)
- `synthetic_experiment_report.pdf` — synthetic experiment report

## 7. The data (reference — NOT in repo, on local disk only)

### 17 May 2024 LSTID
`~/Downloads/gywn_tid_event_20240517/`
ac0g_nd: subchannel 4, 42.0 dB. w7lux: 51.6 dB.
n4rve: subchannel 4, 42.3 dB. n5brg: S000038, 26.4 dB (marginal).

### 19 Jan 2026 MSTID
`~/Downloads/tid_event_20260119/`
n6rfm, aa6bd, w7lux: subchannel 0. ac0g_nd: subchannel 4.
kb4se: (33.3958, -84.4583). kc4le: (33.3125, -86.875).
Config files: event.json (FFT 3-stn) + 3 research/ configs.

**Hard lesson:** always drf_inspect -> confirm subchannel ->
extract -> check event-time SNR -> then correlate.

## 8. Synthesis — when to use each method

| Condition | Recommendation |
|-----------|---------------|
| Clean (eps < 0.2) | Either — identical |
| Contaminated, lag < 0.3 periods | Autocorr preferred |
| Contaminated, lag 0.3-0.5 periods (LSTID typical) | FFT preferred |
| Heavy contamination, ambiguous curve | Neither reliable; use diagnostics |
| Unknown conditions | FFT (default) |

Triangle closure diagnostic correctly identifies wrong-peak locks
regardless of method. Always inspect it and respect it.

## 9. Next steps (when Gwyn replies)

1. Resolve lag discrepancy — document or implement fix.
2. Confirm N5BRG channel — re-run Entry 5 if different.
3. Run v1.5.0 diagnostics (tid_doa.py) on autocorr extractions
   for the 17 May 2024 event (not yet done).
4. Consider band-pass filtering sensitivity in synthetic model —
   tid_pair.py 40-90 and 60-120 min bands not yet tested.
5. Write formal finding — two real events + synthetic validation,
   full table, honest caveats, clear recommendation.
6. Production PR only when: both events consistent, diagnostics
   clean, formal finding written, gate passed.

## 10. Working discipline

- Verify before acting. drf_inspect before extract; check
  event-time SNR before correlate; git log -3 before any reset.
- Do not overclaim. Two real events + synthetic = strong evidence,
  not a conclusion. Lag discrepancy unresolved.
- Negative results recorded with equal weight to positive ones.
- Nothing reaches main without a verified PR.
- Always pull before pushing (Gwyn has write access).
- This is a pause point. Do not start new analysis until Gwyn
  replies and the two blockers are resolved.
