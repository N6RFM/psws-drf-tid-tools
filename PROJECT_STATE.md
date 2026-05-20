# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-20 (evening)  |  **Status: PAUSED — awaiting G3ZIL reply**

---

## 1. One-paragraph status

Main is at **v1.6.7** with a complete, tested, end-to-end mixed
FFT/autocorr workflow. The research branch (`research-doppler-extraction`)
is paused pending Gwyn's reply on two questions. The investigation
into FFT vs autocorr Doppler extraction is substantially complete —
two real events analysed, 1,260 synthetic Monte Carlo trials run,
two PDF reports written, and the full decision workflow integrated
into `analyze_event.sh`. The research branch content (FINDINGS.md,
research/ folder, PDF reports) was merged to main by Gwyn on
2026-05-19 and is now visible to all users. **Do not start new
analysis until Gwyn replies on the two blockers.**

---

## 2. Main branch — release history (v1.5.0 → v1.6.7)

| Version | Feature |
|---------|---------|
| v1.5.0 | Result diagnostics + per-run log (tid_doa.py) |
| v1.6.0 | drf_spectrogram.py --overlay for visual inspection |
| v1.6.1 | Fix inter-method r display (remove tautological FFT r=1.000) |
| v1.6.2 | tid_doa.py optional "method" field for per-station provenance |
| v1.6.3 | analyze_event.sh per-station FFT vs autocorr method selection |
| v1.6.4 | analyze_event.sh interactive resume menu |
| v1.6.5 | drf_to_doppler.py v1.1.1 --method fft\|autocorr on main |
| v1.6.6 | Fix: wire extract_with_overlay into Stage 8 |
| v1.6.7 | Fix: cp same-file error in extract_with_overlay |

**Branches:** main only (v1.6.7).
research-doppler-extraction deleted 2026-05-19 — all content merged to main.
All feature/fix/changelog branches deleted after merging.

---

## 3. Complete mixed-method pipeline (main v1.6.7)

```
drf_inspect.py          → confirm subchannel
analyze_event.sh        → full pipeline:
  Stage 1:  drf_spectrogram.py   → visual scan, identify TID window
  Stage 3:  extract_with_overlay() → reference station:
              - FFT + autocorr extractions
              - drf_spectrogram --overlay shows inter-method r, RMS diff
              - operator chooses method, recorded in station_methods.txt
  Stage 7:  drf_inspect → station_subchannels.txt
  Stage 8:  extract_with_overlay() per companion station (same as Stage 3)
  Stage 10: event.json with "method" field per station
  tid_doa.py → DOA with method in run log
```

**Interactive resume menu:** when state file exists, shows numbered
menu (0-12) to jump to any stage. Useful when data already downloaded.

---

## 4. Research branch — evidence summary

### 4.1 Falsifiable gate — PASSED
Clean W7LUX, 17 May 2024: SNR delta 0.0 dB, r=0.933, autocorr
3x smoother (btb std 0.13 vs 0.38 Hz).

### 4.2 Real data — 17 May 2024 LSTID
Data: `~/Downloads/gywn_tid_event_20240517/`
Window: 18:00-20:00 UTC, 60s cadence.
Gwyn's result (V1.2): 979 ±80 m/s @ 157°, period ~58 min.

| Pair | Band | FFT r | Autocorr r | Delta |
|------|------|-------|------------|-------|
| AC0G_ND/W7LUX | 60-120 min | 0.752 | 0.929 | +0.177 |
| AC0G_ND/W7LUX | Raw curve | 0.576 @+19min | 0.705 @+22min | +0.129 |
| N4RVE/N5BRG | 60-120 min | 0.740 | 0.894 | +0.154 |
| N4RVE/N5BRG | Raw curve | 0.556 @-29min | 0.485 @-27min | -0.071 |

Our DOA results (W7LUX + AC0G_ND + N4RVE, midpoint geometry):

| Method | Speed | Direction | Triangle closure |
|--------|-------|-----------|-----------------|
| All FFT | 596 m/s | 178° | 26% ✗ |
| AC0G_ND+N4RVE autocorr | 606 m/s | 175° | 26% ✗ |
| All autocorr | 543 m/s | 178° | 41% ✗ |
| Gwyn V1.2 | 979 m/s | 157° | — |

**Key finding:** method choice (FFT vs autocorr) has little effect on
the DOA result for this array. The limiting factor is station geometry —
W7LUX, AC0G_ND, N4RVE are nearly collinear (SVD ratio 1.2). Speed
discrepancy vs Gwyn is entirely explained by lag difference (our
~19-21 min vs his 27-35 min) — see blocker 1.

### 4.3 Real data — 19 Jan 2026 MSTID
Data: `~/Downloads/tid_event_20260119/`
Window: 00:00-01:10 UTC, 10s cadence.

| Method | Stations | Speed | Direction | Diagnostics |
|--------|----------|-------|-----------|-------------|
| FFT | 3 (original) | 193 m/s | 190° | All pass ✓ |
| Autocorr | 3 | 335 m/s | 196° | 2 fail ✗ |

FFT 3-station is the only reliable result for this event.

### 4.4 Synthetic Monte Carlo — 1,260 trials
Files: `research/synthetic/`. PDF reports in `research/`.

| Wave | Condition (SNR=40dB) | FFT lock% | AC lock% | Advantage |
|------|----------------------|-----------|----------|-----------|
| MSTID | eps=0.0-0.7 | 100 | 100 | None |
| MSTID | eps=1.0 | 63 | 93 | AC +30pp |
| LSTID | eps=0.5-0.7 | 100 | 60-90 | FFT +10-40pp |
| LSTID | eps=1.0 | 10 | 37 | AC +27pp |

---

## 5. What is BLOCKING (research branch)

Two open questions pending Gwyn's reply to 2026-05-18 email:

1. **Lag discrepancy on AC0G_ND/W7LUX** — our +22 min vs his +35
   min. Does his pipeline apply phase unwrapping, carrier drift
   removal, or any smoothing beyond lag-1 with no detrending?
   This directly explains the speed discrepancy (596 vs 979 m/s).

2. **N5BRG antenna channel** — S000038 (NS) or S000040 (EW)?
   Affects like-for-like validity of the N4RVE/N5BRG pair analysis.

---

## 6. Synthesis — when to use each method

| Condition | Recommendation |
|-----------|---------------|
| Clean signal | Either — identical results |
| Contaminated, lag < 0.3 periods | Autocorr preferred |
| Contaminated, lag 0.3-0.5 periods (LSTID typical) | FFT preferred |
| Ambiguous curve (multiple comparable peaks) | FFT (safer) |
| Unknown | FFT (default) |

Use `drf_spectrogram.py --overlay` to check inter-method r and RMS
diff before choosing. Full decision guide in METHODOLOGY.md Step 1b.
Note: for collinear arrays, method choice has negligible effect on
the DOA result — geometry is the dominant uncertainty.

---

## 7. Data (local disk, NOT in repo)

- `~/Downloads/gywn_tid_event_20240517/` — May 2024 LSTID
  ac0g_nd: subchannel 4 (42 dB). w7lux: subchannel 0 (51.6 dB).
  n4rve: subchannel 4 (42.3 dB). n5brg: S000038, marginal SNR.
- `~/Downloads/tid_event_20260119/` — Jan 2026 MSTID
  n6rfm, aa6bd, w7lux: subchannel 0. ac0g_nd: subchannel 4.

---

## 8. Next steps (when Gwyn replies)

1. Resolve lag discrepancy — document or implement fix.
2. Confirm N5BRG channel — re-run Entry 5 if different.
3. Run diagnostics on autocorr extractions for May 2024 event.
4. Write formal finding with full table and honest caveats.
5. Consider whether additional stations with azimuthal spread
   can be found for the May 2024 event to improve DOA geometry.

---

## 9. Working discipline

- Always on `main` when running the pipeline.
- `research-doppler-extraction` only for FFT vs autocorr investigation.
- Always pull before pushing (Gwyn has write access).
- Do not start new analysis until Gwyn replies and blockers resolved.
- This is a pause point.
