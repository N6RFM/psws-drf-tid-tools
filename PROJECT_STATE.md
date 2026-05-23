# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-22  |  **Status: ACTIVE RESEARCH — awaiting G3ZIL reply on blockers; research_gui branch active**

---

## 1. One-paragraph status

Main is at **v1.6.7** with a complete, tested, end-to-end mixed
FFT/autocorr workflow. Two active research branches:

**`research`** — xcorr algorithmic improvements complete (Entries 13-15):
multi-peak selector + parabolic lag interpolation reduce May 2024 LSTID
collinear array closure from 26% to 3.6% (FFT, all diagnostics pass).
Trusted result: 605 m/s, from 4.0°. Paused pending Gwyn's reply on
speed discrepancy (605 vs 979 m/s).

**`research_gui`** — new interactive guided extraction tools (2026-05-22):
`tid_guided_extract.py` (click on Doppler trace) and `tid_spect_click.py`
(click on spectrogram PNG). `drf_spectrogram.py` now writes `_axes.json`
sidecar. End-to-end test on May 2024 LSTID: guided result 600 m/s / 9.6°
vs automated 605 m/s / 4.0° — agree within 6°, both all-pass.

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

| Method | Speed | Direction | Closure (argmax) | Closure (multi-peak+interp) |
|--------|-------|-----------|-----------------|----------------------------|
| All FFT | 605 m/s | 4.0° | 26% ✗ | **3.6% ✓** |
| All autocorr | 163 m/s | 5.9° | 41% ✗ | 1.1% ✓ (speed wrong⚠️) |
| All CWT | 288 m/s | 261° | 52% ✗ | 1.7% ✓ (speed/dir wrong⚠️) |
| Gwyn V1.2 | 979 m/s | 157° | — | — |

**Trusted result:** FFT with multi-peak selector + parabolic interpolation:
605 m/s, from 4.0° (southward LSTID), all 5 diagnostics pass (Entries 13-15).
**Key finding (updated):** closure failures were wrong-peak lock + discretisation,
not station geometry. Multi-peak selector (Entry 13) + parabolic interpolation
(Entry 15) reduced FFT closure from 26% to 3.6%. Speed discrepancy vs Gwyn
(605 vs 979 m/s) remains open — see blocker 1.

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

**Completed this session (2026-05-22):**
- ✅ Multi-peak xcorr selector tested on May 2024 LSTID collinear array
- ✅ Parabolic lag interpolation implemented and validated
- ✅ FFT closure reduced from 26% to 3.6% (all diagnostics pass)
- ✅ Autocorr/CWT closure also improved but speeds/directions unreliable
- ✅ Trusted result: 605 m/s, from 4.0° (southward LSTID)
- ✅ Jan 2026 MSTID regression confirmed clean (0.6% closure)

**Still blocked on Gwyn reply:**
1. Resolve lag discrepancy (our 19-21 min vs his 27-35 min on AC0G_ND/W7LUX)
   and speed discrepancy (605 vs 979 m/s) for May 2024 LSTID.
2. Confirm N5BRG subchannel — re-run Entry 5 if different.
3. Consider additional stations with azimuthal spread for May 2024 event.

**Low-priority deferred:**
4. Autocorr subharmonic alias fix (speed wrong on May 2024; FFT is reliable).
5. Bandpass pre-filter test on May 2024 event (untested per Entry 12 table).
6. Write formal finding with full table and honest caveats once lag
   discrepancy with Gwyn is resolved.

---

## 9. Working discipline

- Always on `main` when running the pipeline.
- `research-doppler-extraction` only for FFT vs autocorr investigation.
- Always pull before pushing (Gwyn has write access).
- Do not start new analysis until Gwyn replies and blockers resolved.
- This is a pause point.

---
## 10. GUI tools (research_gui branch)

### 10.1 Overview
Two interactive tools for human-guided Doppler extraction, plus a
drf_spectrogram.py enhancement. Use when automated extraction fails
or to validate automated results.

| Tool | Input | Use when |
|------|-------|----------|
| tid_spect_click.py | Spectrogram PNG + CSV | Carrier visible in spectrogram |
| tid_guided_extract.py | CSV only | No spectrogram available |

### 10.2 Quick-start tutorial — tid_spect_click.py

**Step 1: Generate spectrogram with sidecar**

    python drf_spectrogram.py ./w7lux \
        --subchannel 0 \
        --output w7lux_spect.png \
        --start 16:00 --end 22:00 \
        --ylim="-5,5" --dpi 150 \
        --overlay w7lux_fft_clean.csv:FFT

This writes w7lux_spect.png and w7lux_spect_axes.json (sidecar).
The sidecar stores the time/Doppler axis limits so the click tool
knows how to map pixel coordinates to physical units.

**Step 2: Launch the click tool**

    python tid_spect_click.py \
        --spectrogram w7lux_spect.png \
        --csv w7lux_fft_clean.csv \
        --name W7LUX \
        --seg-start 18 --seg-end 20 \
        --period-hint 3600

The sidecar is auto-detected. --seg-start/end sets the analysis
window in decimal UTC hours. --period-hint is the expected TID
period in seconds — use if clicks do not span a full cycle.

**Step 3: Click phase samples**
- The spectrogram appears with the automated Doppler trace overlaid in grey
- The yellow region marks the analysis segment (drag edges to adjust)
- Click 5-7 points along the carrier track (the wavy red/orange line)
  within the segment — aim for crests, troughs, and zero-crossings
- Red dots appear at each click

**Step 4: Fit and write**
- Press F — sinusoid fitted through clicks, overlaid in blue
- Check status bar: amplitude, period, phase should look reasonable
- Press W — writes w7lux_fft_clean_guided.csv

**Step 5: Run DOA on guided CSVs**
Update your event config to point to the _guided.csv files and
run tid_doa.py as normal.

### 10.3 Subchannel notes (May 2024 LSTID event)
- W7LUX: subchannel 0 (10 MHz, SNR 51.6 dB) — clean, guided tool works well
- AC0G_ND: subchannel 4 (10 MHz, SNR 42 dB) — E-region contaminated,
  guided tool marginal; use automated FFT CSV
- N4RVE: subchannel 4 (10 MHz, SNR 42.3 dB) — usable, guided tool works

### 10.4 Known limitations
- --period-hint required when clicks span less than one full TID cycle
- Y-axis view includes amplitude subplot from PNG — scroll to zoom ±1 Hz
- Contaminated stations: if no coherent carrier visible, use automated CSV
- Sidecar workflow strongly preferred over interactive 4-click calibration

### 10.5 Validation result — May 2024 LSTID
| Method | Speed | From | Closure | All-pass |
|--------|-------|------|---------|---------|
| Spectrogram-guided | 600 m/s | 9.6° | 3.2% | Yes |
| Automated FFT | 605 m/s | 4.0° | 3.6% | Yes |
Agreement within 5 m/s and 6 degrees. Guided tool confirmed automated result.

---
## 11. Future improvements — guided extraction tool

Current approach: user clicks drive a sinusoid fit which replaces the
CSV in the segment window. Three better alternatives identified:

**Option 1 — Spline interpolation through clicks**
Fit a smooth spline directly through the clicked (t, doppler) points.
No sinusoid assumption — honors the actual wave shape. Good when the
TID is asymmetric or has varying amplitude. Implement with
scipy.interpolate.CubicSpline or UnivariateSpline.

**Option 2 — Click-anchored offset correction (preferred)**
Use clicked points to measure the offset between the automated trace
and the true carrier at each click location. Interpolate the correction
between clicks and apply it to the full automated CSV. Preserves the
fine-grained shape of the automated extraction but removes gross errors
(wrong peak lock, E-region jumps). Most physically motivated approach —
"the automated extractor is right locally, just tracking the wrong
carrier; my clicks tell you where the right one is."

**Option 3 — Local regression**
Fit a low-order polynomial or Gaussian process through clicks in each
local time window. More flexible than sinusoid, more constrained than
spline. Probably overkill given Options 1 and 2.

**Recommendation for next session:**
Implement Option 2 first — it is the most useful and requires the least
change to the existing tool structure. Add a --correction-mode flag to
tid_spect_click.py with values: sinusoid (current default), spline, offset.

---
## 12. How to resume in a new session

**Opening prompt:**
"Continuing psws-drf-tid-tools research session. Read PROJECT_STATE.md
and FINDINGS.md on the [branch] branch to get current state. We are
on the [branch] branch."

**Which branch:**
- Algorithmic work (xcorr, DOA): research
- GUI tools: research_gui
- Production pipeline: main

**Key past chat sessions (search claude.ai):**
- 2026-05-22: multi-peak selector + parabolic interpolation +
  GUI tools (tid_guided_extract.py, tid_spect_click.py)
  URL: https://claude.ai/chat/46433a60-59b2-4f5e-920e-7a7cd3af4cfb
- 2026-05-23: corridor extraction implementation + validation +
  consistency check + visual overlay + Guerra et al. FIF/SGOLAY analysis
  URL: https://claude.ai/chat/f3b5d8a2-9c1e-4f7e-b8d3-2e5c1a6f9b4e

**Next session opening prompt:**
"Continuing psws-drf-tid-tools research session. Read PROJECT_STATE.md
and FINDINGS.md on the research_gui branch. Top priority: test
--method bandpass and --method cwt on AC0G_ND May 2024 event to see
if better extraction methods reduce wrong-peak lock without corridor.
Then consider FIF on 2D spectrogram as long-term solution."

**Quick-start commands for next session:**
    cd ~/psws-tools-pr && git checkout research_gui
    git log --oneline -5
    cat PROJECT_STATE.md | grep -A5 "## 13"
    # Test bandpass on AC0G_ND:
    cd ~/Downloads/gywn_tid_event_20240517
    python3 ~/psws-tools-pr/drf_to_doppler.py ./ac0g_nd \
        --subchannel 4 --start 2024-05-17T18:00:00 \
        --end 2024-05-17T20:00:00 --decim-seconds 60 \
        --method bandpass --output ac0g_nd_bandpass.csv

**First commands in a new session:**
    cd ~/psws-tools-pr
    git branch --show-current
    git log --oneline -5
    cat PROJECT_STATE.md
    tail -50 FINDINGS.md

---
## 13. Corridor extraction — status (2026-05-23)

### What was implemented
- `tid_spect_click.py`: X key exports corridor JSON (clicked points + half_bw)
- `drf_to_doppler.py`: --corridor flag restricts FFT peak search to
  time-varying frequency band around user-clicked carrier track
- `GUI_TUTORIAL.md`: clicking guidelines added

### What was learned
Corridor extraction correctly identifies the true TID carrier (lower SNR,
physically smooth) vs the automated extractor which locks onto stronger
spurious E-region features (higher SNR, wrong peak). Validated on W7LUX.

**Key problem identified:** applying corridor to only one station creates
a systematic ~180s lag shift relative to the automated extractions on the
other stations. This breaks triangle closure and causes the DOA solver to
pick an alias solution (180° direction flip).

**Root cause:** the corridor tracks a slightly different phase of the
carrier than the automated extractor. The difference (~180s = 3 resamples)
is small but enough to shift the xcorr peak, especially when the other
stations use automated CSVs.

### Status (updated 2026-05-23)
1. ✅ **Consistency check** — xcorr between corridor centres and automated
   CSV on X press. Shows offset in seconds and correlation. Warns if >60s.
2. ✅ **Visual corridor overlay** — yellow dashed boundary lines shown on
   spectrogram after X is pressed.
3. ⏳ **Apply corridor to all stations** — clicking contaminated stations
   (AC0G_ND, N4RVE) remains difficult. Better clicking guidance added to
   GUI_TUTORIAL.md. Wider half_bw may help.
4. **Key finding (Entry 18):** post-processing (SGOLAY, outlier rejection)
   cannot fix sustained wrong-peak lock — must be solved at extraction.
   FIF on 2D spectrogram is the correct long-term approach.
