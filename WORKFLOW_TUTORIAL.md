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

## Finding companion stations

If you only have DRF data from your own station, use `find_event_stations.py`
to discover which other HamSCI PSWS stations recorded the same event window:

```bash
python3 find_event_stations.py \
    --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 \
    --my-call N6RFM \
    --frequency 10.000
```

The tool queries the PSWS network portal, scores candidates by geometry
(baseline azimuth spread, path length, SNR) and returns a ranked shortlist.

**Tips:**
- Pick 3-5 stations from different azimuth quadrants for best DOA geometry
- For LSTID studies, add `--min-path-km 900` to exclude nearby stations
- Download DRF data for the top candidates from https://pswsnetwork.eng.ua.edu/
- Verify SNR and continuity for your event window before committing

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

After all stations are confirmed, choose the extraction method
and DOA coordinate system:

    Extraction method:
      1. cwt-prophet   (anchor-guided -- recommended)
      2. fft           (automated)
      3. autocorr      (automated, Gwyn G3ZIL method)
      4. cwt           (automated, CWT multi-peak tracker)
    Choose [1]:

Also prompted: DOA coordinate system (IPP midpoints recommended).

**Recommended method: cwt-prophet** (option 1) -- anchor-guided
extraction via tid_spect_click.py. Pass 0 auto-runs CWT+Prophet;
if auto-trace looks good press E; if not, click the carrier
and press X to export your trace.

| Method | Best for | Requires GUI |
|--------|----------|-------------|
| cwt-prophet | All stations, best accuracy | Yes |
| fft | Quick automated first look | No |
| autocorr | Smooth carriers, G3ZIL validation | No |
| cwt | Multi-peak ambiguous carriers | No |

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

### Step 6 -- Extraction

Five extraction options are available. Choose based on signal quality,
contamination level, and how many TID cycles are visible.

---

#### Option A: Anchor-guided cwt-prophet extraction — recommended

A `tid_spect_click` window opens showing the zoomed spectrogram.
Use `--event-json event.json` to auto-update the event config on export.

**Pass 0 (automatic):** The tool immediately runs cwt-prophet and
shows the result as a green overlay. No clicks needed — inspect
the trace first.

**If the Pass 0 trace looks good:** press **E** to export the
prophet CSV and move to the next station.

**If the trace has excursions:** click anchor points on the carrier
where Prophet went wrong, then press **P** to re-run Prophet with
your anchors as hard constraints:

    Key bindings (shown in status bar at top):
      Click   Add anchor point on carrier (black dot)
      P       Re-run Prophet with current anchors as constraints
      E       Export prophet CSV (recommended — smooth, guided trace)
      X       Export raw spline CSV (PCHIP through clicks only)
      W       Switch to wave-fit mode (Option B)
      Z       Undo last click
      R       Reset all clicks
      C       Clear all (clicks + calibration)
      Q       Quit

**What to click for Option A (spline):**

The spectrogram shows frequency on the vertical axis and time on
the horizontal axis. The WWV carrier appears as a **bright ridge**
near 0 Hz that slowly drifts up and down as the TID passes —
this is the F-region carrier you want to track.

- Click **on the bright ridge** at the carrier's current position
- Click where the Pass 0 green trace has gone wrong (excursions,
  flat sections, jumps to the wrong ridge)
- Place clicks at the **start and end** of the problem region,
  plus 2–3 points inside it
- Do NOT click on the E-region flat band near 0 Hz (if present)
- The black dot markers show your click positions
- The live spline preview (red/orange curve) updates immediately

**Multi-region editing workflow:**
1. Inspect Pass 0 automatic trace (green)
2. Click 2+ anchor points on the carrier in any problem region —
   live spline preview updates immediately
3. Press **P** to re-run Prophet with your anchors as constraints
4. Inspect the new prophet overlay — add more anchors and press
   P again if needed. Press Z to undo a misplaced click.
5. When satisfied: press **E** to export the prophet CSV
6. Or press **X** to export the raw spline (without Prophet smoothing)

**Key points:**
- Prophet provides a smooth, physically motivated carrier estimate
- Anchor clicks correct only the regions where Prophet fails
- Most of the trace is Prophet's work — user intervenes only where needed
- Prefer **E** (prophet) over **X** (raw spline) when Prophet fits well
- Use **X** only when the carrier is too complex for Prophet
- Minimum clicks needed = quality metric: clean stations need 0

**Output:**
- E key: `<station>_prophet_tid.csv` (recommended)
- X key: `<station>_spline_tid.csv`

---

#### Option B: Wave-fit extraction (--wave-only)

Use when the TID shows ≥1.5 clear cycles in the window and you want
to fit a sine wave directly to the carrier. Each station independently
estimates its own period — handles dispersive TIDs.

Open in wave-fit mode (skips Prophet entirely):

```bash
python3 tid_spect_click.py --spectrogram zoom.png --name N6RFM \\
    --seg-start 0.0 --seg-end 2.0 --wave-only
```

**What to click for Option B (wave-fit):**

The TID appears as a **slow sinusoidal oscillation** of the bright
carrier ridge — drifting above 0 Hz (peak) then below 0 Hz (trough)
with a period of 20–90 minutes. You are clicking on the **centre
of that bright ridge** to trace out its shape.

- Click the **peak** (highest point of the ridge)
- Click the **trough** (lowest point of the ridge)
- Click **zero crossings** (where the ridge crosses 0 Hz)
- Add intermediate points along the slope for better fit
- 5–8 points spread across the cycle gives a reliable fit
- Brown diamond markers show your click positions
- Do NOT click random points — each click directly defines
  the wave's amplitude and phase at that time

**Cycle fraction dialog (after pressing F):**
- Enter **1** if you clicked from trough to peak (half cycle)
- Enter **2** if you clicked from peak to peak or trough to trough
  (full cycle)
- Enter a custom value if you marked a different fraction
  (e.g. **1.33** for ¾ cycle)

**Workflow:**
1. Click multiple points along the visible TID cycle
   (brown diamond markers appear at each click)
2. Press **F** to fit — a dialog asks what fraction of the cycle
   you marked (1=half cycle, 2=full cycle, or custom multiplier)
3. Blue overlay shows the fitted sine wave — press **A** to accept,
   **W** to redo with new points, or **Q** to quit without saving

Output: `<station>_wave_tid.csv`

**When to use wave-fit vs spline:**
- Wave-fit: ≥1.5 full cycles visible, coherent signal
- Spline: <1.5 cycles, E-region contamination, or noisy signal
- If TID period differs significantly between stations,
  consider spline extraction instead

---

#### Option C: Automated extraction (no GUI)

For clean stations with no E-region contamination. Runs without
opening a window — useful for batch processing:

```bash
python3 drf_to_doppler.py ./n6rfm --subchannel 0 \\
    --start 2026-01-19T00:00:00 --end 2026-01-19T02:00:00 \\
    --decim-seconds 60 --method autocorr --output n6rfm_autocorr_tid.csv
```

Methods: `autocorr` (G3ZIL method), `cwt`.
Fully automated, no GUI interaction. Not recommended when
E-region contamination is present — use Option A 

---

### Step 7 -- Extraction output

| Option | Key/command | Output file |
|--------|-------------|-------------|
| A (cwt-prophet, recommended) | E key | `<station>_prophet_tid.csv` |
| A (raw spline) | X key | `<station>_spline_tid.csv` |
| B (wave-fit) | A key (accept) | `<station>_wave_tid.csv` |
| C (automated) | drf_to_doppler.py | `<station>_<method>_tid.csv` |

An overlay spectrogram is generated for visual assessment.

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

When running `tid_doa.py` directly (outside the workflow), use the
`--drop` flag instead of the interactive prompt:

```bash
python3 tid_doa.py event.json --drop W7LUX
python3 tid_doa.py event.json --drop W7LUX --drop AC0G_ND
```

---

## Interpreting the DOA diagnostics

| # | Diagnostic | Good range | If flagged |
|---|-----------|-----------|-----------|
| 1 | Geometry SVR | < 30 | Near-collinear -- need more stations |
| 2 | Plane-wave residual | < 25% | TID non-stationary or wrong peaks |
| 3 | Pairwise correlation | min > 0.4 | Drop suggested station (`--drop` or interactive loop) |
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
preview shows the correction. Press X to export.

**Trace goes wrong outside the clicked region**
Add anchor clicks at the start and end of the window, or press X
to accept what you have and let the baseline handle the rest.

**Lag hits --max-lag boundary**
Widen with `--max-lag 60`, or re-extract with better anchor coverage.

**Speed unphysical after dropping a station**
Check SVR — if > 5, the remaining array is near-collinear.
Try a different combination via the interactive loop (workflow) or:
```bash
python3 tid_doa.py event.json --drop W7LUX
python3 tid_doa.py event.json --drop AC0G_ND
```

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

tid_doa.py (direct use, outside workflow):
  --drop NAME           Exclude a station by name before DOA
                        (repeatable, case-insensitive)
                        E.g. --drop W7LUX --drop AC0G_ND
  --smooth N            Savitzky-Golay smoothing window in seconds
  --max-lag MIN         Override max xcorr lag in minutes
  --tx-lat DEG          Transmitter latitude (default: WWV 40.68N)
  --tx-lon DEG          Transmitter longitude (default: WWV -105.04W)
  --tx-freq-mhz MHZ     Transmitter frequency in MHz (default: 10.0)
```

---

## Reference result -- Jan 2026 event

For the 19 January 2026 event (00:00-01:36 UTC, 4 stations):

| Metric | Value |
|--------|-------|
| Phase speed | 304 m/s |
| Coming from | 10° NNE |
| Heading toward | ~190° SSW |
| Classification | MSTID, auroral origin |
| Window | 2026-01-19T00:00–01:15 UTC |
| Stations | N6RFM, AA6BD, W7LUX (AC0G_ND dropped) |
| Flags | 0/5 |
| Method | cwt-prophet Pass 0 |
| Command | `python3 tid_doa.py examples/event_20260119.json --drop AC0G_ND` |

---

## Reproducibility notes

### Why results vary between sessions

cwt-prophet Pass 0 extractions are **not fully deterministic** across
sessions. The prophet algorithm is sensitive to initial CWT ridge
selection, which can vary with subchannel noise and display window.
This means running the GUI twice on the same spectrogram may give
slightly different `_prophet_preview.csv` files, and therefore
slightly different DOA results.

**To make a result reproducible:**

1. Use `--event-json` when running tid_spect_click.py:
   ```bash
   python3 tid_spect_click.py \
     --spectrogram examples/tid_event_20260119/n6rfm_tid_zoom_clean.png \
     --name N6RFM \
     --event-json examples/event_20260119.json
   ```
   On export (E or X key), the event JSON is updated automatically
   with the CSV path and method.

2. Press **E** to export the prophet trace directly (recommended),
   or **X** to export a spline. Both update the event JSON.

3. Commit the `_prophet_preview.csv` files along with the event JSON.
   The CSV files are the reproducible record of the extraction.

4. To reproduce from the command line after committing:
   ```bash
   python3 tid_doa.py examples/event_20260119.json
   ```

### Canonical Jan 2026 result (as of 2026-05-31)

The committed `examples/event_20260119.json` points to
cwt-prophet Pass 0 extractions. Best reproducible result:

| Metric | Value |
|--------|-------|
| Phase speed | 304 m/s |
| Coming from | 10° NNE |
| Stations | N6RFM, AA6BD, W7LUX (AC0G_ND dropped) |
| Flags | 0/5 |
| Method | cwt-prophet Pass 0 |
| Files | `*_tid_zoom_clean_prophet_preview.csv` |

The earlier 239 m/s result (Entry 50) was produced interactively
with the GUI and is **not reproducible** from committed files.
Direction (NNE) is consistent between both results and confirmed
independently by Madrigal GPS TEC lag sign (Entry 52).

### When to use E vs X

| Situation | Key | Result |
|-----------|-----|--------|
| Auto-trace follows the carrier | E | Export auto-trace (fast, reproducible) |
| Auto-trace has problems | X | Click carrier from left to right, export your trace |
| Signal has clear sinusoidal cycles | Use wave-fit (Option B) | F=fit+save |

For reproducibility, prefer E (auto-trace) when it looks correct.
