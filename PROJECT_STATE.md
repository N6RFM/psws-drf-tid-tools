# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-25 (end of session)  |  **Status: ACTIVE RESEARCH — research_gui branch active; awaiting Gwyn reply on method discrepancy**

---

## 1. One-paragraph status

Main is at **v1.6.7** with a complete, tested, end-to-end mixed
FFT/autocorr workflow.

**`research_gui`** (active) — complete guided extraction workflow implemented
and validated 2026-05-24. Tools: tid_quicklook.py (TID window selection),
drf_spectrogram.py (zoomed spectrogram + axes sidecar), tid_spect_click.py
(corridor clicking with consistency check + overlay), drf_to_doppler.py
--method sgolay-ridge (2D STFT ridge tracker), tid_doa.py.

**4-station result (W7LUX, AC0G_ND, N4RVE, N5BRG, 18:29-19:06 UTC):**
sgolay-ridge: 267 m/s from 242° (WSW), all diagnostics pass.
auto FFT fails 2 diagnostics; autocorr fails 1.
IPP midpoint coordinates used (WWV transmitter 40.68N, 105.04W).

**Critical open question:** diagnostics measure internal consistency only —
not physical correctness. Gwyn's result (979 m/s, 157° SSE) disagrees by
~95° direction and ~4x speed. Root cause unknown. True validation requires
independent measurement (GNSS TEC, ionosonde) or reconciliation with Gwyn.

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
Data: `~/Downloads/gwyn_tid_event_20240517/`
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

- `~/Downloads/gwyn_tid_event_20240517/` — May 2024 LSTID
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
    cd ~/Downloads/gwyn_tid_event_20240517
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

---
## 14. sgolay-ridge method — status (2026-05-23)

### Implementation complete
- `drf_to_doppler.py --method sgolay-ridge --corridor JSON`
- Reads all I/Q at once, builds full 2D STFT spectrogram
- Power-weighted centroid within corridor at each time step
- SGOLAY smoothing across time (--sgolay-window, default 21 min)

### Results vs automated FFT (W7LUX May 2024 LSTID)
| Metric | Auto FFT | SGOLAY-ridge |
|--------|----------|-------------|
| Speed | 605 m/s | 587 m/s |
| Direction | 4.0° | 4.5° |
| Closure | 3.6% | 8.3% |
| Correlation | 0.574 | 0.699 |
| All-pass | Yes | Yes |

Better correlations, slightly worse closure. Both all-pass.
Closure gap because sgolay-ridge applied to W7LUX only —
needs all stations to use same method for bias to cancel.

### Next steps
1. Apply sgolay-ridge to all 3 stations simultaneously
2. Need good corridor clicks on AC0G_ND and N4RVE
3. Compare 3-station sgolay-ridge DOA vs automated baseline

**Fundamental reframe (important):**
The corridor is a PRIOR CONSTRAINT — the user defines where to look,
not what the carrier looks like. Clicks bracket the carrier band;
the extraction algorithm finds the carrier within that band.

User does NOT need to click on the carrier precisely — just draw a
band that contains it. Much easier on contaminated spectrograms.

Correct flow:
  1. User clicks corridor bounds (bracket the carrier region)
  2. drf_to_doppler.py --method sgolay-ridge extracts carrier within band
  3. The extracted CSV IS the carrier — no sinusoid fitting needed
  4. tid_doa.py computes DOA from extracted CSVs

Revised clicking guidance:
- Click at several time points where the carrier band is clearly visible
- Each click should be roughly centred on the carrier track
- Spacing: every 20-30 min is sufficient
- half_bw 0.5 Hz means clicks within 0.5 Hz of true carrier are fine
- Wide enough to contain carrier, narrow enough to exclude E-region

---
## 15. Corridor design review — key decisions

### Fundamental reframe (agreed 2026-05-24)
The corridor is a PRIOR CONSTRAINT — the user defines where to look,
not what the carrier looks like. Clicks bracket the carrier band;
the extraction algorithm (sgolay-ridge) finds the carrier within it.

### Design decisions
1. Corridor JSON stores raw clicked points — linear interpolation
   between clicks for the centre frequency. This is correct because
   the corridor is a search region, not a carrier model.
2. Outside clicked range: flat extrapolation to nearest endpoint.
   Acceptable if clicks cover the full analysis window.
3. half_bw default 0.5 Hz — wide enough for F-region carrier,
   narrow enough to exclude most E-region contamination.
4. Consistency check on X press: xcorr offset >60s warns user.
5. sgolay-ridge preview (green curve) shows extracted result
   on spectrogram so user can verify before committing.

### What the sinusoid fit (F key) is for
Visual verification only — confirms clicks are on a coherent
oscillation. The fit is NOT used in extraction. The corridor
boundaries (yellow dashed lines) are what matter.
---
## 16. Complete guided workflow — validated 2026-05-24

Full workflow implemented and validated on May 2024 LSTID event.
Result: 267 m/s from 242° (WSW), all diagnostics pass (4-station, IPP coords).

### Tools in workflow order
1. drf_spectrogram.py --start 00:00 --end 24:00  → fullday.png + _axes.json
2. tid_quicklook.py --spectrogram fullday.png     → fullday_window.json
3. drf_spectrogram.py --window fullday_window.json → zoom.png + _axes.json
4. tid_quicklook.py --spectrogram zoom.png        → zoom_window.json (refined)
5. drf_to_doppler.py --method fft                → fft.csv (for overlay)
6. drf_spectrogram.py --overlay fft.csv:FFT      → zoom.png (with overlay)
7. tid_spect_click.py --spectrogram zoom.png      → corridor.json
8. drf_to_doppler.py --method sgolay-ridge        → sgolay.csv
9. Repeat 1-8 for each station
10. tid_doa.py event.json                         → DOA result

### Known issues / next steps
1. plot_fraction bottom (bf) still unreliable for some image types —
   matplotlib position method works but bbox_inches=tight may shift things
2. Corridor clicks should cover full analysis window — flat extrapolation
   outside clicked range may miss carrier at window edges
3. Consider adding a wrapper script to automate steps 1-10

---
## 17. Current status — 2026-05-24 (end of day)

### What was accomplished today
1. Complete guided workflow implemented and tested end-to-end:
   tid_quicklook.py → drf_spectrogram.py --window → tid_quicklook.py (refine)
   → drf_to_doppler.py --method fft (overlay) → tid_spect_click.py (corridor)
   → drf_to_doppler.py --method sgolay-ridge → tid_doa.py

2. Key bug fixes:
   - drf_spectrogram.py --window: was nested inside if args.start (fixed)
   - drf_spectrogram.py plot_fraction: now uses matplotlib axes position
   - tid_quicklook.py: neutral default region; overlap warning after S
   - tid_spect_click.py: auto-detects _window.json from tid_quicklook.py

3. 4-station DOA result (W7LUX, AC0G_ND, N4RVE, N5BRG):
   - sgolay-ridge: 267 m/s from 242° (WSW), all diagnostics pass ✅
   - auto FFT: 222 m/s from 186° (S), 2 diagnostics fail ❌
   - autocorr: 233 m/s from 188° (S), 1 diagnostic fails ❌
   - IPP midpoint coordinates used (WWV transmitter at 40.68N, 105.04W)

4. Comparison with Gwyn's result (979 m/s, 157° SSE):
   - ~95° direction discrepancy, ~4x speed discrepancy
   - Root cause unknown — methodological difference is key question
   - Our diagnostics are internal consistency checks ONLY — not physical validation

### Critical open question
Are our diagnostics meaningful? They were tuned on early FFT results
and only measure internal consistency. The 267 m/s WSW result passes
all diagnostics but this does NOT confirm physical correctness.
True validation requires independent measurement (GNSS TEC, ionosonde,
Gwyn's independent method).

### Top priorities for next session
1. Email Gwyn with our results — ask for his exact lag values and method
2. Implement Gwyn's 2-path vector decomposition method for direct comparison
3. Obtain GNSS TEC data for this event for independent validation
4. Fix corridor coverage: clicks should span full analysis window
5. Add wrapper script to automate the 10-step workflow

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md section 17 and
FINDINGS entries 21-26. Key question: validate our 267 m/s WSW result
against Gwyn's 979 m/s SSE — email Gwyn and implement his 2-path method."

---
## 18. tid_workflow.py — status 2026-05-25

### Implemented
Complete 10-step guided workflow wrapper. Auto-discovers stations,
generates thumbnails, handles subchannel selection, computes IPP
midpoints, saves state for resume. Overlap warning fires if <60 min.

### Known issues
1. Subchannel thumbnail window hardcoded to 17-21h — should use
   event time from first station's quicklook selection
2. Window alignment is the most critical user action — overlap
   warning now offers quit/redo option

### Next session opening prompt
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 17-21
and FINDINGS entries 24-30 on research_gui branch.
Priority: send email to Gwyn (drafted). Then test tid_workflow.py
on a fresh event with well-aligned windows."

---
## 19. Future direction: FIF/EMD on 2D spectrogram (no corridor required)

### Concept
The original sgolay-ridge proposal was to apply Fast Iterative Filtering
(FIF, Cicone & Zhou 2021, Guerra et al. 2024) directly to the 2D STFT
spectrogram to automatically separate the slowly-varying TID carrier
from faster contamination — without requiring user corridor clicks.

### How it would work
1. Compute full STFT spectrogram (time × frequency)
2. At each frequency bin, apply FIF/EMD across time to decompose into
   intrinsic mode functions (IMFs)
3. Sum IMFs in the TID period band (45-90 min for LSTID, 10-40 min MSTID)
4. Extract the carrier ridge from the filtered spectrogram
5. No user input required — fully automatic

### Why we stopped
- Cicone's FIF is MATLAB only — no Python package available
- PyPI FIF package was empty/wrong
- All Cicone GitHub repos are .m files

### Path forward
Two options:

**Option A — EMD (available now):**
    pip install emd
EMD (Empirical Mode Decomposition, Huang et al. 1998) is the precursor
to FIF. Similar decomposition into IMFs, slightly slower than FIF but
well-tested in Python. Available immediately.

**Option B — Implement FIF from scratch:**
FIF algorithm is fully described in Cicone & Zhou 2021 (Numer. Math.
147:1-28). Core steps: iterative low-pass filtering using FFT-based
kernel, convergence criterion on IMF. ~100 lines of Python.

### Implementation sketch (Option A with EMD)
    import emd
    # spectrogram shape: (n_times, n_freqs)
    # For each freq bin near 0 Hz (carrier region):
    imfs = emd.sift.sift(spectrogram[:, freq_bin])
    # Sum IMFs with period in TID band
    tid_component = sum IMFs where period in [45, 90] min
    # Find carrier ridge = freq bin with max tid_component at each time

### Relationship to corridor method
FIF/EMD would be a parallel extraction method, not a replacement:
- Corridor + sgolay-ridge: user-guided, best accuracy, slower
- FIF/EMD on spectrogram: fully automatic, no user input, faster
- Could be used to SUGGEST a corridor to the user before clicking

### Priority
Medium — implement after Gwyn discrepancy is resolved and current
workflow is validated on multiple events.

---
## 20. Gwyn's Prophet/CWT approach — relationship to our methods

### Gwyn's method (grape_fft_CWT_tracking_prophet.py)
Reference: https://github.com/g3zil/grapeDRF_doppler_model

1. CWT peak finding — finds ALL spectral peaks per 60s block (not just max)
2. Keeps top 2 peaks — F-region and E-region carriers
3. Facebook Prophet — predicts F-region Doppler one step ahead using
   a Bayesian time-series model trained on recent history
4. Peak selection — if top peak is farther from prediction than second
   peak, swap them (i.e. the other peak is more likely to be F-region)
5. Outputs two separate Doppler traces (F-region + E-region)

### Key insight
Gwyn's Prophet prediction and our user corridor serve the same purpose:
both provide a PRIOR on where the F-region carrier should be. The
difference is:
- Prophet: algorithmic prior from recent carrier history
- Corridor: user visual prior from spectrogram inspection

Prophet is blind to sudden phase jumps (wrong-peak lock can corrupt
the training data). The corridor is immune to this because it's set
by the user before extraction.

### Why we didn't use Prophet
- Heavy dependency (Stan/PyStan compiled C++)
- Slow: seconds per minute of data (120 fits for 2h event)
- Fragile installation (platform-dependent)
- Overkill: linear extrapolation achieves same accuracy for smooth signal

### Future option: CWT + linear extrapolation (no Prophet)
A lighter version of Gwyn's approach:
- CWT peak finding (scipy, already a dependency)
- Rolling linear extrapolation (5-10 samples) instead of Prophet
- Same two-peak tracking logic
- Could be added as --method cwt-track in drf_to_doppler.py

This would be fully automatic (no corridor clicking) and more robust
than the current --method cwt which doesn't do two-peak tracking.

### Priority
Discuss with Gwyn first — he may have already refined this approach
and sharing code/results would avoid duplication.

---
## 21. Method cleanup — deferred

Decision to remove any extraction methods (autocorr, cwt, bandpass)
deferred until after Gwyn's reply on the 267 m/s WSW vs 979 m/s SSE
discrepancy. His response may:
1. Clarify which methods are physically correct
2. Point to extending cwt (his Prophet/CWT approach)
3. Identify the root cause of the direction discrepancy

All methods recoverable from git history if removed and later needed.

---
## 22. GUI cleanup — 2026-05-25 (research_gui)

### Changes made this session

**drf_spectrogram.py:**
- Removed bottom amplitude panel (compute_peak_amplitude, ax_bot, peaks)
- Single-panel figure now (14×6 inches) — spectrogram fills full output
- Dead code (compute_peak_amplitude function) removed
- Added date_utc field to sidecar axes JSON for use by tid_spect_click.py

**tid_spect_click.py:**
- Removed sinusoid fit workflow (F/W keys, fit_curve, fit_dim_curve,
  _fit, _write, _refresh_fit, fit_sinusoid, evaluate_sinusoid_hours)
- Removed CSV overlay (V key, csv_curve, _load_csv, _toggle_csv_overlay,
  _replot_csv, --csv now optional no-op)
- Removed FFT consistency check (xcorr vs automated CSV) — irrelevant
  to corridor+sgolay workflow
- sgolay preview extraction window now uses corridor click extent
  (min/max of clicks_t) not the yellow segment handles
- Corridor output path based on spectrogram stem not CSV stem
- Date for sgolay preview subprocess extracted from sidecar date_utc
- Stale file cleanup uses spectrogram stem

### Current tool interface (tid_spect_click.py)
Required: --spectrogram PNG --name NAME --drf-dir DIR
Optional: --subchannel N --sgolay-window MINUTES --seg-start --seg-end
Keys: X (export corridor + run preview), R (reset clicks),
      C (clear all), Q (quit)

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 19-22
and FINDINGS entries 28-31 on research_gui branch.
Priorities: (1) email Gwyn re 267 m/s WSW vs 979 m/s SSE discrepancy,
(2) EMD 4-station DOA run, (3) tid_workflow.py Step 7 clean PNG fix."

---
## 24. tid_workflow.py improvements — 2026-05-25

### Changes
- Extraction method prompt at start (sgolay-ridge or fft)
- sgolay-ridge path: no FFT step, plain zoom spectrogram → corridor → sgolay
- fft path: fft extraction → overlay spectrogram, no corridor step
- DOA uses correct CSV for chosen method
- Step 5 now opens zoom_clean_png with yellow region pre-set from Step 3
- Window review after all stations complete Steps 3-5: shows summary,
  allows any station to be redone before extraction begins
- date_str KeyError on resume fixed

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 22-24
and FINDINGS entries 30-31 on research_gui branch.
Priority: re-run full workflow on May 2024 event with 17:30-19:30
window, carefully click AC0G_ND corridor on clean F-region carrier."

---
## 25. AC0G_ND unusable for May 2024 event — 2026-05-25

### Finding
AC0G_ND spectrogram shows strong DC ground wave at 0 Hz plus large
E-region loops at +1 to +3 Hz. No visible F-region TID carrier.
Station is unusable for this event regardless of corridor placement.

### 3-station geometry problem
N4RVE/N5BRG/W7LUX triangle has only 24° between baselines — nearly
collinear. Cannot determine 2D TID velocity. Best result with these
3 stations: along-baseline component ~300-390 m/s toward WSW.

### tid_workflow.py bugs fixed this session
- zoom_window now defaults to window after Step 3
- Step 5 shows current window, Q keeps it as-is
- Extraction method prompt (sgolay-ridge/fft) at start
- Window review before extraction with per-station redo
- h_to_hhmm display bug (17:60 → 18:00) fixed
- Step 5 opens zoom_clean_png with correct pre-positioning
- DOA uses correct CSV for chosen method
- date_str KeyError on resume fixed

### Next steps
1. Try AC0G_ND subchannel 0 — may have cleaner signal
2. Find a different event where AC0G_ND is usable
3. Consider adding a 5th station to improve array geometry

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 23-25
on research_gui branch. AC0G_ND unusable on May 2024 event (ground
wave at 0 Hz). Try subchannel 0 for AC0G_ND or find better event."

---
## 26. Jan 2026 event analysis — 2026-05-25

### Event
2026-01-19, 00:00-01:36 UTC, 4 stations: AA6BD, AC0G_ND, N6RFM, W7LUX

### Result (sgolay-ridge)
- Speed: 283 m/s
- Direction from: 30° (NNE) — wave travelling SSW
- Consistent with auroral LSTID travelling equatorward
- 2 of 5 diagnostics outside range (residual 44.8%, closure 38.2%)
- Weak link: AC0G_ND→N6RFM lag (+26.6 min, r=0.576)
- Three of four triangles close within 5 min ✅

### Station quality
- AA6BD: std=0.610 Hz, SNR=45 dB
- AC0G_ND: std=0.387 Hz, SNR=60 dB  ← much better than May 2024
- N6RFM: std=0.373 Hz, SNR=55 dB
- W7LUX: std=0.327 Hz, SNR=58 dB

### Key improvement vs May 2024
AC0G_ND is clean on this event (subchannel 4, SNR=60 dB, no DC ground
wave contamination). Array geometry is better — SVR=1.4 vs 1.6.

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 24-27
and FINDINGS entries 30-33 on research_gui branch.
Priority: update Jan 2026 analysis document with corrected 283 m/s
result, then test on additional events."

---
## 27. Session summary — 2026-05-25 (end of day)

### Accomplished this session
1. GUI cleanup: amplitude panel removed, sinusoid fit removed,
   CSV overlay removed, consistency check removed
2. tid_workflow.py major improvements:
   - Extraction method prompt (sgolay-ridge/fft)
   - Window review with per-station redo before extraction
   - zoom_window defaults to window after Step 3
   - h_to_hhmm display bug fixed (17:60 → 18:00)
   - Negative time clamp in h_to_iso
   - --stations flag for station subset selection
   - DOA uses correct CSV for chosen method
3. May 2024 event: AC0G_ND unusable (DC ground wave at 0 Hz)
   3-station array near-collinear — cannot resolve 2D velocity
4. Jan 2026 event: first clean 4-station sgolay-ridge result
   - 283 m/s from 30° (NNE) — equatorward auroral LSTID
   - Confirmed by peak-time cross-check from Figure 4
   - FFT gives wrong result (99 m/s, 167°) — wrong-peak lock
5. Jan 2026 analysis document: speed error identified
   - Document reports 666 m/s (early FFT analysis, wrong IPP)
   - Correct result: 283 m/s (sgolay + peak-time cross-check)
   - Direction (35° NNE) was already correct

### Critical finding
The sgolay-ridge result (283 m/s) is validated by two independent
methods on the Jan 2026 event:
1. DOA least-squares with sgolay-ridge extracted lags
2. Direct peak-time measurement from Figure 4 spectrogram

This is the first physically validated result from psws-drf-tid-tools.

### Open items
1. Update Jan 2026 analysis document with corrected speed
2. May 2024 event still unresolved — needs better station geometry
3. AC0G_ND May 2024: try subchannel 0 or find event where it is clean
4. Push research_gui branch to origin when ready

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 25-27
and FINDINGS entries 31-33 on research_gui branch.
Priority: update Jan 2026 analysis document with corrected 283 m/s
result and peak-time validation. May 2024 event still unresolved."

---
## 28. End of session — 2026-05-26

### Final commit state
research_gui is 23 commits ahead of origin. All changes local only.

### Last confirmed result
Jan 2026 event with --max-lag 30:
- Speed: 254 m/s from 31° (NNE)
- Extraction: sgolay-ridge, 4 stations
- max_lag_seconds=1800 prevents AC0G_ND→N6RFM aliasing

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 26-28
and FINDINGS entries 32-34 on research_gui branch.
Priority: (1) update Jan 2026 analysis document with 254-283 m/s
corrected result, (2) fix tid_quicklook.py to clamp negative window
values at source, (3) test on additional events,
(4) push research_gui to origin when ready."

---
## 29. Workflow streamlining and DOA improvements — 2026-05-26

### Changes
- Streamlined to 8 steps (removed redundant Step 6 reference PNG)
- Step 5 window refinement now opt-in (y/N, default skip)
- "Same window for all stations" prompt after first window saved
- --max-lag CLI flag added (set max_lag_seconds in event JSON)
- Post-DOA interactive drop-station loop with comparison table
- tid_doa.py suggests specific station to drop in [3] and [4]
- h_to_hhmm clamps negative hours for display

### Jan 2026 event results summary
All runs consistently give 35-37° NNE direction.
Speed varies 202-262 m/s depending on corridors/max_lag.
AC0G_ND essential despite weak pairs — without it array is collinear.
Best estimate: 254-283 m/s from ~31-35° NNE.

### Resume command
cd ~/psws-tools-pr && git checkout research_gui
"Continuing psws-drf-tid-tools. Read PROJECT_STATE.md sections 27-29
and FINDINGS entries 34-37 on research_gui branch.
Priority: (1) update Jan 2026 analysis document with corrected
254-283 m/s result, (2) fix tid_quicklook.py negative window clamping,
(3) push research_gui to origin."
