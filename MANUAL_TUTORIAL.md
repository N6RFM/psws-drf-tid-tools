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

### Option A: spline extraction (recommended)

Launch the interactive click tool:

```bash
python3 tid_spect_click.py \
    --spectrogram n6rfm_zoom.png \
    --name N6RFM \
    --drf-dir ./n6rfm \
    --subchannel 0 \
    --corridor-width 0.4 \
    --seg-start 0 --seg-end 2
```

**Pass 0 (automatic):** On open, cwt-prophet runs automatically and
shows a green trace overlay. Inspect it.

**Key bindings (shown in status bar):**

    Click   Add anchor point on carrier (black dot)
    P       Re-run Prophet with anchors as constraints
    A       Accept current region, clear clicks for next region
    X       Export final spline CSV
    R       Reset all clicks
    Q       Quit

**Workflow:**
1. Inspect Pass 0 trace
2. If good: press X to export immediately (0 clicks needed)
3. If excursions: click on carrier at problem region (2+ clicks)
   -- live spline preview updates after each click
4. Press A to accept and freeze that region
5. Click next problem region -- A to accept
6. Press X when all regions are correct

Output: `n6rfm_spline_tid.csv`

**Why spline extraction?** The user clicks directly on the carrier.
The PCHIP spline interpolates smoothly between clicks. No wrong-peak
lock possible. The number of clicks needed is a quality metric --
clean stations need 0 clicks.

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

**Anchor-guided cwt-prophet:** pass an anchors JSON from the click
tool to constrain the CWT search around a user-defined spline:

```bash
python3 drf_to_doppler.py ./n6rfm \
    --subchannel 0 \
    --start 2026-01-19T00:00:00 \
    --end   2026-01-19T02:00:00 \
    --decim-seconds 60 \
    --method cwt-prophet \
    --anchors n6rfm_zoom_anchors.json \
    --corridor-width 0.4 \
    --output n6rfm_cwt_prophet_tid.csv
```

The anchors JSON is written automatically by `tid_spect_click.py`
when anchor points are placed.

**Validate visually:**

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
| autocorr | Smooth carriers, G3ZIL validation |
| cwt | Multi-peak ambiguous carriers |
| cwt-prophet | CWT + Prophet prediction (G3ZIL comparison) |

**Important:** validation on the Jan 2026 event showed fft and
cwt-prophet give wrong lags on AC0G/ND due to E-region contamination.
The spline extraction (Option A) correctly avoids this.

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
    "event_end_utc":   "2026-01-19T02:00:00Z",
    "resample_seconds": 60,
    "use_bandpass": false,
    "min_expected_speed_m_s": 100,
    "max_lag_seconds": 1800,
    "stations": [
        {"name": "N6RFM",   "file": "n6rfm_spline_tid.csv",
         "method": "spline", "lat": 36.81, "lon": -101.13},
        {"name": "AA6BD",   "file": "aa6bd_spline_tid.csv",
         "method": "spline", "lat": 37.87, "lon": -95.09},
        {"name": "W7LUX",   "file": "w7lux_spline_tid.csv",
         "method": "spline", "lat": 37.89, "lon": -108.37},
        {"name": "AC0G_ND", "file": "ac0g_nd_spline_tid.csv",
         "method": "spline", "lat": 43.78, "lon": -100.94}
    ]
}
```

**Use IPP midpoint coordinates** (halfway between WWV and receiver):

```
IPP lat = (40.68 + receiver_lat) / 2
IPP lon = (-105.04 + receiver_lon) / 2
```

**max_lag_seconds:** set to ~1/3 of expected TID period to prevent
period aliasing. For Jan 2026 (~90 min period): 1800 s (30 min).

---

## Step 8 -- Run DOA inversion

```bash
python3 tid_doa.py event.json
```

Run log written to `runs/<timestamp>_run.log`.

Test robustness by dropping a station:

```bash
python3 -c "
import json
e = json.load(open('event.json'))
e['stations'] = [s for s in e['stations'] if s['name'] != 'AC0G_ND']
json.dump(e, open('event_3stn.json','w'), indent=2)
"
python3 tid_doa.py event_3stn.json
```

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
| spline (8-10 anchors) | 218-257 m/s | 35-37 NNE | Best result |
| sgolay-ridge | 218-257 m/s | 35-37 NNE | Comparable to spline |
| fft | 99 m/s | 167 deg | Wrong -- AC0G/ND wrong-peak lock |
| cwt-prophet | 99 m/s | 167 deg | Identical to fft |
| Peak-time direct | ~281 m/s | ~33 deg | Independent cross-check |

The spline approach gives the physically correct result by letting the
user define the carrier position directly, bypassing automated peak
selection entirely.

---

## Reference result -- Jan 2026 event

| Metric | Value |
|--------|-------|
| Stations | N6RFM, AA6BD, W7LUX, AC0G/ND |
| Phase speed | 218-283 m/s |
| Coming from | 30-37 deg (NNE) |
| Heading toward | ~215 deg (SSW) |
| Classification | LSTID, auroral origin |

---

## Further reading

- `WORKFLOW_TUTORIAL.md` -- guided workflow using tid_workflow.py
- `FINDINGS.md` -- research work log documenting method validation
- `drf_to_doppler.py --help` -- full extraction options
- `tid_doa.py --help` -- DOA config format and diagnostic thresholds
- `tid_spect_click.py --help` -- spline extraction options
