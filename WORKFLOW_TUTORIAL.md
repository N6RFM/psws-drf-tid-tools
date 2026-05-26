# Guided Workflow Tutorial — tid_workflow.py

`tid_workflow.py` is the recommended starting point for new TID analyses.
It guides you through all 8 steps interactively, saves state after each
step so you can resume if interrupted, and runs the DOA automatically.

## Prerequisites

- DRF data directories for each station (e.g. `./n6rfm`, `./aa6bd`)
- Python packages installed: `pip install -r requirements.txt`
- PyQt5 and pyqtgraph for the interactive windows:
  `pip install PyQt5 pyqtgraph Pillow`

---

## Quick start

```bash
python3 tid_workflow.py --event-dir /path/to/event/directory
```

If you only want to use a subset of stations in the directory:

```bash
python3 tid_workflow.py \
    --event-dir /path/to/event \
    --stations N6RFM,AA6BD,W7LUX,AC0G_ND
```

To limit the xcorr lag search (recommended when TID period is known):

```bash
python3 tid_workflow.py \
    --event-dir /path/to/event \
    --stations N6RFM,AA6BD,W7LUX,AC0G_ND \
    --max-lag 30
```

`--max-lag 30` means ±30 minutes maximum lag. Use approximately 1/3 of
the expected TID period. For a ~90-minute LSTID, `--max-lag 30` is
appropriate.

To resume an interrupted session:

```bash
python3 tid_workflow.py --event-dir /path/to/event --resume
```

---

## The 8 steps

### Step 1 — Station discovery and subchannel selection

The workflow scans the event directory for DRF subdirectories, probes
each one for subchannels, generates thumbnail spectrograms (saved to
`<station>_subchannels/`), and asks you to confirm the subchannel for
WWV 10 MHz. The subchannel with the highest SNR near 10 MHz is
suggested automatically.

```
Station: AA6BD  (subchannel 0)
  Top subchannels by SNR:
    subchannel 0: 18.0 dB
  Enter subchannel [0]:         <- press Enter to accept
```

Open the thumbnail directory to verify — look for a clear carrier
near 0 Hz with visible slow oscillations in the TID window.

After all stations are confirmed, choose the extraction method:

```
Extraction method:
  1. sgolay-ridge  (corridor GUI — recommended)
  2. fft           (automated)
  3. autocorr      (automated, Gwyn G3ZIL method)
  4. cwt           (automated, CWT multi-peak tracker)
Choose [1]:
```

**When to use each method:**

| Method | Best for | Requires GUI |
|--------|----------|-------------|
| sgolay-ridge | Contaminated stations, best accuracy | Yes |
| fft | Clean stations, quick first look | No |
| autocorr | Smooth carriers, G3ZIL validation | No |
| cwt | Multi-peak ambiguous carriers | No |

**Key finding from validation:** sgolay-ridge correctly identifies the
F-region carrier when E-region contamination is present. FFT can give
internally consistent but physically wrong lags on contaminated stations.

---

### Step 2 — Full-day spectrogram

A full 24-hour spectrogram is generated for each station at 100 dpi.
This is used in Step 3 to select the TID window. No user input required.

---

### Step 3 — Select TID window

A `tid_quicklook` window opens showing the full-day spectrogram. The
TID appears as a slow sinusoidal oscillation in the carrier track near
0 Hz.

**Controls:**
- Drag the yellow highlighted region to bracket the TID event
- `S` — save window and quit
- `Q` — quit without saving

After the first station's window is saved:

```
Apply 00:00–02:00 to all remaining stations? [y/N]:
```

Type `y` to use the same window for all stations (recommended when the
TID is visible across all stations over the same time range). Type `N`
to set windows individually.

---

### Step 4 — Zoomed spectrogram

A higher-resolution (150 dpi) spectrogram is generated covering just
the selected TID window. This is the image used for corridor clicking
in Step 6. No user input required.

---

### Step 5 — Optionally refine TID window (opt-in)

```
Refine window for AA6BD? [y/N]:
```

Default is **N** (skip). Type `y` only if you want to fine-tune the
window on the zoomed spectrogram. The yellow region is pre-positioned
to the Step 3 window.

---

### Step 6 — Extraction

**sgolay-ridge path:** A `tid_spect_click` corridor clicking window
opens showing the zoomed spectrogram. Click ~6 points bracketing the
F-region carrier across the full time span.

**How to click a good corridor:**
- Look for the slowly varying carrier near 0 Hz
- Ignore bright E-region loops above ±1 Hz
- Cover the full time span — start and end gaps cause extraction errors
- Press `X` to export and preview (green curve)
- Verify the green curve follows the carrier smoothly
- Re-click if it tracks the wrong feature
- Press `Q` to accept and proceed

**fft/autocorr/cwt path:** Fully automated — no user input required.
An overlay spectrogram is generated showing the extracted trace.

---

### Step 7 — Sgolay extraction / FFT overlay

**sgolay-ridge:** Extraction runs automatically using the corridor from
Step 6. Output: `<station>_sgolay_tid.csv`

**fft/autocorr/cwt:** An overlay spectrogram is generated for visual
inspection. Output: `<station>_fft_tid.csv` / `_autocorr_tid.csv` /
`_cwt_tid.csv`

---

### Window review (before DOA)

After all stations complete Steps 2-7, a summary is shown:

```
Window summary (before extraction):
  AA6BD        00:00–02:00 UTC
  AC0G_ND      00:00–01:40 UTC
  N6RFM        00:00–02:00 UTC
  W7LUX        00:00–02:00 UTC

  NOTE: to drop a station from DOA, do that AFTER extraction
  Proceed with extraction? [Y] or station name to redo window:
```

Type `Y` to proceed, or a station name (e.g. `AC0G_ND`) to redo that
station's window selection from Step 3.

---

### Step 8 — DOA

The direction-of-arrival inversion runs automatically. Results include:

- Phase speed (m/s)
- Wave heading toward / coming from (degrees true)
- 5 diagnostic checks with guidance
- Suggested station to drop if diagnostics flag problems

After the DOA result, an interactive drop-station loop activates:

```
  Drop a station and re-run DOA? [station name or Enter to finish]:
```

Type a station name to drop it and re-run. A comparison table is shown:

```
  Comparison:
  Stations                               Speed    From  Flags
  ------------------------------------------------------------
  AA6BD,AC0G_ND,N6RFM,W7LUX            262 m/s  37 deg      3
  AA6BD,N6RFM,W7LUX                     96 m/s  12 deg      2
  ------------------------------------------------------------
```

Press Enter to finish.

---

## Interpreting the DOA diagnostics

| # | Diagnostic | Good range | If flagged |
|---|-----------|-----------|-----------|
| 1 | Geometry SVR | < 30 | Near-collinear array — need more stations |
| 2 | Plane-wave residual | < 25% | TID non-stationary or wrong peaks |
| 3 | Pairwise correlation | min > 0.4 | Drop suggested station |
| 4 | Triangle closure | < 15% | Wrong-peak lock — try smaller --max-lag |
| 5 | Phase speed | 100-1000 m/s | Likely aliased lags |

**Important:** diagnostics are internal consistency checks only. They
cannot confirm a result is physically real. Cross-check against:
- Peak timing visible in the spectrogram (northern stations should lead
  for auroral LSTIDs)
- Speed consistent with TID classification (100-300 m/s MSTID,
  300-1000 m/s LSTID)
- Direction consistent with event source (auroral: from NNE, ~30-35°)

---

## Common issues

**"Corridor coverage gaps: start gap N min"**
Add more clicks near the left and right edges of the spectrogram.

**Lag hits --max-lag boundary exactly**
The xcorr is constrained. Try `--max-lag 60` to widen the search,
or re-click the corridor more carefully.

**Speed unphysical after dropping a station**
The remaining stations may be near-collinear. Check SVR — if > 5,
the array cannot resolve 2D wave velocity without the dropped station.

**Window summary shows negative times (e.g. -1:45)**
The yellow region was dragged past the left edge. This is automatically
clamped to 00:00 for extraction — cosmetic only.

---

## State file

State is saved to `<event-dir>/tid_workflow_state.json` after each
interactive step. Run with `--resume` to continue from where you left
off. To start fresh, delete the state file.

---

## CLI reference

```
tid_workflow.py --event-dir DIR [options]

Required:
  --event-dir DIR       Directory containing DRF station subdirectories

Options:
  --stations A,B,C      Comma-separated station names (default: all found)
  --resume              Resume from saved state
  --max-lag MIN         Max xcorr lag in minutes (default: auto from geometry)
                        Recommended: ~1/3 of expected TID period
  --sgolay-window MIN   Sgolay smoothing window in minutes (default: 21)
  --tx-lat DEG          Transmitter latitude (default: WWV 40.68N)
  --tx-lon DEG          Transmitter longitude (default: WWV -105.04W)
  --tx-freq-mhz MHZ     Transmitter frequency in MHz (default: 10.0)
```

---

## Reference result — Jan 2026 event

For the 19 January 2026 event (00:00–01:36 UTC, 4 stations,
sgolay-ridge extraction):

| Metric | Value |
|--------|-------|
| Phase speed | 254–283 m/s |
| Coming from | 30–35° (NNE) |
| Heading toward | ~215° (SSW) |
| Classification | LSTID, auroral origin |
| Validation | Peak-time cross-check confirms NNE→SSW propagation |
