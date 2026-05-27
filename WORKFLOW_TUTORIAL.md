# Guided Workflow Tutorial — tid_workflow.py

`tid_workflow.py` is the recommended starting point for new TID analyses.
It guides you through all 8 steps interactively, saves state after each
step so you can resume if interrupted, and runs the DOA automatically.

## Prerequisites

- DRF data directories for each station (e.g. `./n6rfm`, `./aa6bd`)
- Python packages installed: `pip install -r requirements.txt`
- PyQt5 and pyqtgraph for the interactive GUI windows:
  `pip install PyQt5 pyqtgraph Pillow`

---

## Quick start

```bash
python3 tid_workflow.py --event-dir /path/to/event/directory
```

With a subset of stations and lag constraint:

```bash
python3 tid_workflow.py \
    --event-dir /path/to/event \
    --stations N6RFM,AA6BD,W7LUX,AC0G_ND \
    --max-lag 30
```

`--max-lag 30` limits xcorr search to +/-30 min. Use approximately 1/3
of the expected TID period. For a ~90 min LSTID, 30 min is appropriate.

To resume an interrupted session:

```bash
python3 tid_workflow.py --event-dir /path/to/event --resume
```

---

## The 8 steps

### Step 1 -- Station discovery and subchannel selection

The workflow scans the event directory for DRF subdirectories, probes
each for subchannels, generates thumbnail spectrograms, and asks you
to confirm the subchannel for WWV 10 MHz. The highest-SNR subchannel
is suggested automatically.

    Station: AA6BD  (subchannel 0)
      Top subchannels by SNR:
        subchannel 0: 18.0 dB
      Enter subchannel [0]:         <- press Enter to accept

After all stations are confirmed, choose the extraction method:

    Extraction method:
      1. sgolay-ridge    (corridor GUI -- recommended)
      2. fft             (automated)
      3. autocorr        (automated, Gwyn G3ZIL method)
      4. cwt             (automated, CWT multi-peak tracker)
      5. cwt-prophet     (automated, CWT + Facebook Prophet predictor)
    Choose [1]:

**Recommended method: sgolay-ridge** (option 1) -- uses the interactive
spline extraction tool described in Step 6.

| Method | Best for | Requires GUI |
|--------|----------|-------------|
| sgolay-ridge | All stations, best accuracy | Yes |
| fft | Quick automated first look | No |
| autocorr | Smooth carriers, G3ZIL validation | No |
| cwt | Multi-peak ambiguous carriers | No |
| cwt-prophet | CWT + Prophet prediction (G3ZIL comparison) | No |

---

### Step 2 -- Full-day spectrogram

Generated automatically at 100 dpi for each station. Used in Step 3
to select the TID window. No user input required.

---

### Step 3 -- Select TID window

A `tid_quicklook` window opens showing the full-day spectrogram.

Controls:
- Drag the yellow highlighted region to bracket the TID event
- S -- save window and quit
- Q -- quit without saving

After the first station's window is saved:

    Apply 00:00-02:00 to all remaining stations? [y/N]:

Type `y` to use the same window for all stations (recommended).

---

### Step 4 -- Zoomed spectrogram

A 150 dpi spectrogram covering just the TID window is generated.
This is the image used for extraction in Step 6.

---

### Step 5 -- Optionally refine TID window (opt-in)

    Refine window for AA6BD? [y/N]:

Default is N (skip). Type `y` only if the zoomed spectrogram
reveals the window needs adjustment.

---

### Step 6 -- Extraction (sgolay-ridge / spline mode)

A `tid_spect_click` window opens showing the zoomed spectrogram.

**Pass 0 (automatic):** The tool immediately runs cwt-prophet
automatically and shows the result as a green overlay. No clicks
needed -- inspect the trace first.

**If the Pass 0 trace looks good:** press X to export and move
to the next station.

**If the trace has excursions:** click on the carrier at the
problem region to add anchor points (black dots), then use the
key bindings below:

    Key bindings (shown in status bar at top):
      Click   Add anchor point on carrier (black dot with white border)
      P       Re-run Prophet with current anchors as constraints
      A       Accept current region -- freeze it, clear clicks for next region
      X       Export final spline CSV and move on
      R       Reset all clicks
      Q       Quit

**Multi-region editing workflow:**
1. Inspect Pass 0 automatic trace (green)
2. Click 2+ points on the carrier in any problem region
   -- live spline preview updates immediately
3. Press A to accept and freeze that region -- clicks clear
4. Click next problem region -- A to accept
5. When all regions are correct -- press X to export

**Key points:**
- Clicks define the carrier position directly
- The PCHIP spline interpolates smoothly between clicks
- Outside the clicked range, the last accepted trace is used as baseline
- Each A freezes the current region; X exports the final output
- Minimum clicks needed = quality metric: clean stations may need 0

---

### Step 7 -- Extraction output

sgolay-ridge: writes `<station>_spline_tid.csv`
fft/autocorr/cwt/cwt-prophet: writes `<station>_<method>_tid.csv`

An overlay spectrogram is generated for visual validation.

---

### Window review (before DOA)

After all stations complete extraction, a summary is shown:

    Window summary:
      AA6BD        00:00-02:00 UTC
      AC0G_ND      00:00-01:40 UTC
      N6RFM        00:00-02:00 UTC
      W7LUX        00:00-02:00 UTC

      Proceed with extraction? [Y] or station name to redo window:

---

### Step 8 -- DOA

The direction-of-arrival inversion runs automatically. After the
result, an interactive drop-station loop activates:

    Drop a station and re-run DOA? [station name or Enter to finish]:

A comparison table shows results with and without the dropped station.

---

## Interpreting the DOA diagnostics

| # | Diagnostic | Good range | If flagged |
|---|-----------|-----------|-----------|
| 1 | Geometry SVR | < 30 | Near-collinear -- need more stations |
| 2 | Plane-wave residual | < 25% | TID non-stationary or wrong peaks |
| 3 | Pairwise correlation | min > 0.4 | Drop suggested station |
| 4 | Triangle closure | < 15% | Wrong-peak lock -- try smaller --max-lag |
| 5 | Phase speed | 100-1000 m/s | Likely aliased lags |

Physical cross-checks (more reliable than diagnostics):
- Northern stations must lead southern ones for auroral LSTIDs
- Speed 100-300 m/s MSTID; 300-1000 m/s LSTID
- Direction from 30-45 NNE consistent with auroral origin

---

## Common issues

**Pass 0 trace has large excursion at one point**
Click 2-3 points on the carrier near the excursion. The live spline
preview shows the correction. Press A to accept, then X.

**Trace goes wrong outside the clicked region**
Add anchor clicks at the start and end of the window, or press A
to accept what you have and let the baseline handle the rest.

**Lag hits --max-lag boundary**
Widen with `--max-lag 60`, or re-extract with better anchor coverage.

**Speed unphysical after dropping a station**
Check SVR -- if > 5, the remaining array is near-collinear.

---

## State file

State is saved to `<event-dir>/tid_workflow_state.json` after each
interactive step. Run with `--resume` to continue from where you left off.

---

## CLI reference

```
tid_workflow.py --event-dir DIR [options]

Required:
  --event-dir DIR       Directory containing DRF station subdirectories

Options:
  --stations A,B,C      Comma-separated station names (default: all found)
  --resume              Resume from saved state
  --max-lag MIN         Max xcorr lag in minutes (default: auto)
                        Recommended: ~1/3 of expected TID period
  --sgolay-window MIN   Sgolay smoothing window in minutes (default: 21)
  --tx-lat DEG          Transmitter latitude (default: WWV 40.68N)
  --tx-lon DEG          Transmitter longitude (default: WWV -105.04W)
  --tx-freq-mhz MHZ     Transmitter frequency in MHz (default: 10.0)
```

---

## Reference result -- Jan 2026 event

For the 19 January 2026 event (00:00-01:36 UTC, 4 stations):

| Metric | Value |
|--------|-------|
| Phase speed | 218-283 m/s |
| Coming from | 30-37 deg (NNE) |
| Heading toward | ~215 deg (SSW) |
| Classification | LSTID, auroral origin |
| Validation | Peak-time cross-check confirms NNE->SSW propagation |
