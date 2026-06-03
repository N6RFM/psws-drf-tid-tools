# Manual Step-by-Step Tutorial

This tutorial covers the complete TID direction-of-arrival analysis
pipeline using individual command-line tools. Use this approach when
you want full control over each step, need to run only part of the
pipeline, or are debugging a specific issue.

The reference event is the **19 January 2026 LSTID** recorded by four
HamSCI Grape stations during a geomagnetic storm.

---

## Prerequisites

```bash
git clone https://github.com/N6RFM/psws-drf-tid-tools.git
cd psws-drf-tid-tools
pip install -r requirements.txt
pip install PyQt5 pyqtgraph Pillow
```

You need DRF data directories for each station:

```
tid_event_20260119/
  aa6bd/          AA6BD DRF recording
  ac0g_nd/        AC0G/ND DRF recording
  n6rfm/          N6RFM DRF recording
  w7lux/          W7LUX DRF recording
```

---

## Step 0 -- Find companion stations

If you only have DRF data from your own station, run this first to discover
which other HamSCI PSWS stations recorded the same event:

```bash
python3 find_event_stations.py \
    --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 \
    --my-call N6RFM \
    --frequency 10.000
```

This queries the PSWS portal and returns a ranked list of candidate stations
scored by baseline geometry, path length, and SNR. Choose 3-5 stations from
different azimuth quadrants for best DOA geometry.

Download DRF data for the selected stations from:
https://pswsnetwork.eng.ua.edu/

Then proceed with Step 1 below.

---

## Step 1 -- Inspect the DRF recording

Verify what subchannels are available and which contains WWV 10 MHz.

```bash
python3 drf_inspect.py --all ./n6rfm --frequency 10
```

Note the subchannel index for each station before proceeding.
For single-channel Grape v1 stations this is always subchannel 0.
For multi-channel WSPRDaemon stations (e.g. AC0G/ND) it varies.

---

## Step 2 -- Generate full-day spectrogram

```bash
python3 drf_spectrogram.py ./n6rfm \
    --subchannel 0 \
    --output n6rfm_fullday.png \
    --start 00:00 --end 24:00 \
    --ylim=-5,5 --dpi 100 \
    --callsign N6RFM --grid EM12jw
```

Repeat for each station. Look for a slow sinusoidal oscillation in
the carrier track near 0 Hz -- this is the TID.

---

## Step 3 -- Select TID analysis window

```bash
python3 tid_quicklook.py --spectrogram n6rfm_fullday.png
```

Drag the yellow region to bracket the TID. Press S to save.
Writes `n6rfm_fullday_window.json`.

For the Jan 2026 event: 00:00-02:00 UTC covers one full TID cycle.

---

## Step 4 -- Generate zoomed spectrogram

```bash
python3 drf_spectrogram.py ./n6rfm \
    --subchannel 0 \
    --output n6rfm_zoom.png \
    --window n6rfm_fullday_window.json \
    --ylim=-5,5 --dpi 150 \
    --callsign N6RFM --grid EM12jw
```

---

## Step 5 -- Doppler extraction

### Option A: anchor-guided cwt-prophet extraction (recommended)

Launch the interactive click tool:

```bash
python3 tid_spect_click.py \
    --spectrogram n6rfm_zoom.png \
    --name N6RFM \
    --drf-dir ./n6rfm \
    --subchannel 0 \
    --corridor-width 0.4 \
    --seg-start 0 --seg-end 2 \
    --event-json event.json
```

`--event-json` is optional but recommended: on export (X or E key),
the matching station entry in the event JSON is updated with the
file path and method, making the extraction reproducible.

**Pass 0 (automatic):** On open, cwt-prophet runs automatically and
shows a green trace overlay. Inspect it.

**Key bindings (shown in status bar):**

    Click   Add anchor point on carrier (black dot)
    P       Re-run Prophet with anchors as constraints
    X       Export spline CSV (updates --event-json if supplied)
    E       Export prophet CSV (cwt-prophet Pass 0 trace)
    W       Enter wave-fit mode (click cycle points, F to fit)
    Z       Undo last click
    R       Reset all clicks
    C       Clear all (clicks + calibration)
    Q       Quit

**Workflow:**
1. Inspect Pass 0 trace (green overlay) — this is the cwt-prophet
   automatic extraction
2. If good: press **E** to export prophet CSV (0 clicks needed)
3. If excursions: click anchor points on the carrier where Prophet
   went wrong (2+ clicks) — live spline preview updates after each click
4. Press **P** to re-run Prophet with your anchors as hard constraints
   — Prophet re-fits the carrier, constrained to pass through your
   anchor points. This is the key step: the result is a smooth,
   physically motivated trace, not a raw spline through clicks.
5. Inspect the new prophet overlay — add more anchors and press P
   again if needed. Press Z to undo a misplaced click.
6. When satisfied: press **E** to export the anchor-guided prophet CSV
7. Or press **X** to export the raw PCHIP spline through clicks only
   (without Prophet smoothing — use when Prophet cannot fit the signal)

Output:
- E key: `n6rfm_prophet_tid.csv` (recommended — smooth, prophet-guided)
- X key: `n6rfm_spline_tid.csv` (raw spline through clicks)

**Why anchor-guided cwt-prophet?** Prophet provides a smooth,
physically motivated carrier estimate. The user's anchor clicks
correct only the regions where Prophet fails (E-region contamination,
wrong-peak lock). Most of the trace is Prophet's work — the user
only intervenes where needed. This gives a better result than raw
spline clicking because Prophet uses the full spectral context, not
just the clicked points. The number of anchor clicks is a station
quality metric — clean stations need 0 clicks.

**E vs X:** prefer E (prophet) when Prophet follows the carrier well
after anchoring. Use X (raw spline) only when the carrier is too
complex for Prophet to fit — e.g. multiple overlapping carriers, or
a carrier that changes character mid-window.

---

### Option B: automated extraction (fft / autocorr / cwt / cwt-prophet)

No GUI required.

```bash
python3 drf_to_doppler.py ./n6rfm \
    --subchannel 0 \
    --start 2026-01-19T00:00:00 \
    --end   2026-01-19T02:00:00 \
    --decim-seconds 60 \
    --method fft \
    --output n6rfm_fft_tid.csv
```

Replace `fft` with `autocorr`, `cwt`, or `cwt-prophet` as needed.

**Check visually:**

```bash
python3 drf_spectrogram.py ./n6rfm \
    --subchannel 0 \
    --output n6rfm_overlay.png \
    --window n6rfm_fullday_window.json \
    --ylim=-5,5 --dpi 150 \
    --callsign N6RFM --grid EM12jw \
    --overlay n6rfm_fft_tid.csv:FFT
```

**Which automated method to use:**

| Method | Best for |
|--------|----------|
| fft | General purpose, default |
| autocorr | Smooth carriers, G3ZIL method |
| cwt | Multi-peak ambiguous carriers |
| cwt-prophet | CWT + Prophet prediction (G3ZIL comparison) |

**Important:** automated methods pick the strongest spectral peak
without constraint. On the Jan 2026 event, fft and cwt-prophet give
wrong lags on AC0G/ND due to E-region contamination. The anchor-guided
cwt-prophet extraction (Option A) avoids this by constraining Prophet
to the user's anchor points on the correct carrier.

### Option C: wave-fit extraction (--wave-only)

Use when the TID shows at least 1.5 clear cycles in the window
and you want to fit a sine wave directly to the carrier:

```bash
python3 tid_spect_click.py \\
    --spectrogram n6rfm_zoom.png \\
    --name N6RFM \\
    --seg-start 0.0 --seg-end 2.0 \\
    --wave-only
```

1. Tool opens directly in wave-fit mode (no Prophet run)
2. Click multiple points along the visible TID cycle
   (brown diamond markers appear at each click)
3. Press **F** — dialog asks what fraction of the cycle you marked
   (1=half cycle, 2=full cycle, or custom multiplier)
4. Blue overlay shows the fitted wave — press **A** to accept,
   **W** to redo, or **Q** to quit without saving

Output: `n6rfm_wave_tid.csv`

**Note:** wave-fit DOA requires similar periods across stations.
If periods differ significantly, use spline extraction instead.

---


### Option D: sgolay-ridge extraction (legacy)

Sgolay-ridge is the precursor to cwt-prophet spline extraction. The
user defines a frequency corridor on the spectrogram; a Savitzky-Golay
ridge-finder tracks the carrier only within that corridor.

```bash
python3 drf_to_doppler.py ./n6rfm \
    --subchannel 0 \
    --start 2026-01-19T00:00:00 \
    --end   2026-01-19T02:00:00 \
    --decim-seconds 60 \
    --method sgolay-ridge \
    --output n6rfm_sgolay_tid.csv
```

Requires a corridor JSON (from tid_spect_click.py anchor clicks).
Superseded by the spline extraction workflow (Option A) which gives
equivalent results with a simpler interface. Still available for
comparison and for users familiar with the corridor approach.

**When sgolay-ridge helps:** contaminated carriers where the user
wants to constrain the search to a specific frequency band without
clicking every point. Gives good results when the corridor is placed
correctly; quality depends entirely on corridor definition.

---

## Step 6 -- Repeat for all stations

Repeat Steps 2-5 for AA6BD, AC0G/ND, and W7LUX.

**Special notes for AC0G/ND:**
- Multi-subchannel WSPRDaemon DRF -- probe with drf_inspect.py first
- May have E-region contamination -- use spline extraction
- Click the corridor carefully near 0 Hz

---

## Step 7 -- Build DOA event config

Create `event.json`:

```json
{
    "event_start_utc": "2026-01-19T00:00:00Z",
    "event_end_utc":   "2026-01-19T01:15:00Z",
    "resample_seconds": 60,
    "use_bandpass": false,
    "use_ipp": true,
    "min_expected_speed_m_s": 100,
    "max_lag_seconds": 1800,
    "stations": [
        {"name": "N6RFM",   "file": "n6rfm_spline_tid.csv",
         "method": "spline", "lat": 32.94, "lon": -97.21},
        {"name": "AA6BD",   "file": "aa6bd_spline_tid.csv",
         "method": "spline", "lat": 35.06, "lon": -85.13},
        {"name": "W7LUX",   "file": "w7lux_spline_tid.csv",
         "method": "spline", "lat": 35.10, "lon": -111.71},
        {"name": "AC0G_ND", "file": "ac0g_nd_spline_tid.csv",
         "method": "spline", "lat": 46.88, "lon": -96.83}
    ]
}
```

**`use_ipp: true`** tells tid_doa.py to compute the great-circle
midpoint between each station and WWV internally. Pass actual
receiver coordinates (not pre-computed IPP midpoints).

**`max_lag_seconds`:** set to ~1/3 of expected TID period to prevent
period aliasing. Override on the command line with `--max-lag MIN`.



---

## Step 8 -- Run DOA inversion

```bash
python3 tid_doa.py event.json
```

Run log written to `runs/<timestamp>_run.log`.

Test robustness by dropping a station:

```bash
python3 tid_doa.py event.json --drop AC0G_ND
python3 tid_doa.py event.json --drop W7LUX --drop AC0G_ND
```

`--drop` is repeatable and case-insensitive. The diagnostics suggest
which station to try dropping when triangle closure or correlation
flags fire.

---

## Step 9 -- Interpret DOA diagnostics

| # | Check | Good range | If flagged |
|---|-------|-----------|-----------|
| 1 | Geometry SVR | < 30 | Near-collinear -- need more stations |
| 2 | Plane-wave residual | < 25% | Non-stationary TID or wrong peaks |
| 3 | Pairwise correlation | min > 0.4 | Drop flagged station |
| 4 | Triangle closure | < 15% | Wrong-peak lock -- reduce max_lag |
| 5 | Phase speed | 100-1000 m/s | Likely aliased lags |

Physical cross-checks:
- Northern stations must lead southern ones for auroral LSTIDs
- Speed 100-300 m/s MSTID; 300-1000 m/s LSTID
- Direction from 30-45 NNE consistent with auroral origin

---

## Step 10 -- Visualise results

```bash
# Stacked Doppler comparison
python3 tid_stack_plot.py --config event.json --output stack.png

# Array geometry map with wave direction
python3 tid_map.py --config event.json --output map.png \
    --azimuth-toward 217 --speed 262
```

---

## Extraction method comparison (Jan 2026 event)

| Method | Speed | From | Notes |
|--------|-------|------|-------|
| spline/cwt-prophet | 239 m/s | 30° NNE | Best result (0/5 flags) |
| sgolay-ridge | 218-257 m/s | 35-37° NNE | Comparable |
| fft | ~281 m/s | ~33° NNE | Automated, 3/5 flags |
| autocorr | similar to fft | — | G3ZIL method |
| Peak-time direct | ~281 m/s | ~33 deg | Independent cross-check |

The spline approach gives the physically correct result by letting the
user define the carrier position directly, bypassing automated peak
selection entirely.

---

## Reference result -- Jan 2026 event

| Metric | Value |
|--------|-------|
| Stations | N6RFM, AA6BD, W7LUX (AC0G_ND dropped) |
| Phase speed | 304 m/s |
| Coming from | 10° NNE |
| Heading toward | ~190° SSW |
| Classification | MSTID, auroral origin |
| Window | 2026-01-19T00:00–01:15 UTC |
| Flags | 0/5 |
| Method | cwt-prophet Pass 0 |
| Command | `python3 tid_doa.py event.json --drop AC0G_ND` |

---

## Further reading

- `WORKFLOW_TUTORIAL.md` -- guided workflow using tid_workflow.py
- `FINDINGS.md` -- research work log documenting method assessment
- `drf_to_doppler.py --help` -- full extraction options
- `tid_doa.py --help` -- DOA config format and diagnostic thresholds
- `tid_spect_click.py --help` -- spline extraction options
