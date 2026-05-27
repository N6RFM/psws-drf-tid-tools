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
pip install PyQt5 pyqtgraph Pillow   # for interactive GUI windows
```

You need DRF data directories for each station:

```
tid_event_20260119/
├── aa6bd/          AA6BD DRF recording
├── ac0g_nd/        AC0G/ND DRF recording
├── n6rfm/          N6RFM DRF recording
└── w7lux/          W7LUX DRF recording
```

---

## Step 1 — Inspect the DRF recording

Verify what subchannels are available and which contains WWV 10 MHz.

```bash
python3 drf_inspect.py --all ./n6rfm --frequency 10
```

Look for a subchannel with a clear carrier near 0 Hz and high SNR.
For single-channel Grape v1 stations this is always subchannel 0.
For multi-channel WSPRDaemon stations (e.g. AC0G/ND) the subchannel
varies — probe all and check the thumbnails.

Note the subchannel index for each station before proceeding.

---

## Step 2 — Generate full-day spectrogram

Generate a 24-hour spectrogram to identify the TID event window.

```bash
python3 drf_spectrogram.py ./n6rfm \
    --subchannel 0 \
    --output n6rfm_fullday.png \
    --start 00:00 --end 24:00 \
    --ylim=-5,5 --dpi 100 \
    --callsign N6RFM
```

Repeat for each station (aa6bd, ac0g_nd, w7lux), adjusting
`--subchannel` and `--callsign` as needed.

**What to look for:** a slow sinusoidal oscillation in the carrier
track near 0 Hz. For auroral LSTIDs this typically appears in the
hours after local midnight and lasts 1-2 hours.

---

## Step 3 — Select TID analysis window

Open the full-day spectrogram interactively to bracket the TID window.

```bash
python3 tid_quicklook.py --spectrogram n6rfm_fullday.png
```

Drag the yellow region to bracket the TID. Press `S` to save.
Writes `n6rfm_fullday_window.json` with the selected time range.

For the Jan 2026 event: 00:00–02:00 UTC covers one full TID cycle.

Repeat for each station, or copy the JSON file and edit the
`spectrogram_png` field to apply the same window to all stations:

```bash
# Apply same window to all stations
for stn in aa6bd ac0g_nd w7lux; do
    cp n6rfm_fullday_window.json ${stn}_fullday_window.json
    # Edit spectrogram_png field in each copy
    sed -i "s/n6rfm_fullday/${stn}_fullday/g" ${stn}_fullday_window.json
done
```

---

## Step 4 — Generate zoomed spectrogram

Generate a higher-resolution spectrogram of just the TID window.
This is the image used for corridor clicking in Step 5.

```bash
python3 drf_spectrogram.py ./n6rfm \
    --subchannel 0 \
    --output n6rfm_zoom.png \
    --window n6rfm_fullday_window.json \
    --ylim=-5,5 --dpi 150 \
    --callsign N6RFM
```

Repeat for each station.

---

## Step 5 — Doppler extraction

Choose one of the following extraction methods for each station.

---

### Option A: sgolay-ridge (recommended for contaminated stations)

This method requires corridor clicking — you define the region of the
spectrogram containing the F-region carrier, and a 2D STFT ridge
tracker extracts the Doppler within that region.

**Step 5a: Click corridor**

```bash
python3 tid_spect_click.py \
    --spectrogram n6rfm_zoom.png \
    --name N6RFM \
    --drf-dir ./n6rfm \
    --subchannel 0 \
    --sgolay-window 21
```

**How to click a good corridor:**
- Click ~6 points bracketing the F-region carrier from left to right,
  spanning the full time window
- Each click places a corridor boundary point — aim for ±0.5 Hz
  around the carrier centre
- Ignore bright E-region loops and spikes above ±1 Hz
- Cover the full time span — gaps at start/end cause extraction errors
- Press `X` to export the corridor and preview the sgolay extraction
  (shown as a green curve)
- Verify the green curve follows the carrier smoothly
- If the green curve tracks the wrong feature, press `X` again to
  re-click from scratch
- Press `Q` to accept and exit

This writes `n6rfm_zoom_corridor.json`.

**Step 5b: Run sgolay-ridge extraction**

```bash
python3 drf_to_doppler.py ./n6rfm \
    --subchannel 0 \
    --start 2026-01-19T00:00:00 \
    --end   2026-01-19T02:00:00 \
    --decim-seconds 60 \
    --method sgolay-ridge \
    --corridor n6rfm_zoom_corridor.json \
    --sgolay-window 21 \
    --output n6rfm_sgolay_tid.csv
```

Output: `n6rfm_sgolay_tid.csv` with columns `timestamp_utc`,
`doppler_hz`, `snr_db`.

---

### Option B: automated extraction (fft / autocorr / cwt / cwt-prophet)

No corridor clicking required.

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

**Which method to use:**

| Method | Best for |
|--------|----------|
| fft | General purpose, default |
| autocorr | Smooth carriers, G3ZIL validation |
| cwt | Multi-peak ambiguous carriers |
| cwt-prophet | CWT + Facebook Prophet predictor (G3ZIL comparison) |

**Validate visually** by overlaying the extracted trace on the
spectrogram:

```bash
python3 drf_spectrogram.py ./n6rfm \
    --subchannel 0 \
    --output n6rfm_overlay.png \
    --window n6rfm_fullday_window.json \
    --ylim=-5,5 --dpi 150 \
    --callsign N6RFM \
    --overlay n6rfm_fft_tid.csv:FFT
```

**Important:** validation on the Jan 2026 event showed FFT can give
internally consistent but physically wrong lags when AC0G/ND is
contaminated with E-region signal. If in doubt, use sgolay-ridge.

---

## Step 6 — Repeat for all stations

Repeat Steps 2–5 for AA6BD, AC0G/ND, and W7LUX.

**Special notes for AC0G/ND:**
- Multi-subchannel WSPRDaemon DRF — probe with `drf_inspect.py` first
- Look for a subchannel with SNR > 40 dB and a carrier near 0 Hz
- The corridor must be clicked carefully near 0 Hz — avoid the bright
  E-region loops at ±2–4 Hz
- If the full-day spectrogram shows a strong DC line at exactly 0 Hz,
  the station may be receiving ground wave — try a different subchannel

---

## Step 7 — Build DOA event config

Create `event.json` referencing the extracted CSV files.

```json
{
    "event_start_utc": "2026-01-19T00:00:00Z",
    "event_end_utc":   "2026-01-19T02:00:00Z",
    "resample_seconds": 60,
    "use_bandpass": false,
    "min_expected_speed_m_s": 100,
    "max_lag_seconds": 1800,
    "stations": [
        {
            "name": "N6RFM",
            "file": "n6rfm_sgolay_tid.csv",
            "method": "sgolay-ridge",
            "lat": 36.81,
            "lon": -101.13
        },
        {
            "name": "AA6BD",
            "file": "aa6bd_sgolay_tid.csv",
            "method": "sgolay-ridge",
            "lat": 37.87,
            "lon": -95.09
        },
        {
            "name": "W7LUX",
            "file": "w7lux_sgolay_tid.csv",
            "method": "sgolay-ridge",
            "lat": 37.89,
            "lon": -108.37
        },
        {
            "name": "AC0G_ND",
            "file": "ac0g_nd_sgolay_tid.csv",
            "method": "sgolay-ridge",
            "lat": 43.78,
            "lon": -100.94
        }
    ]
}
```

**Important — use IPP midpoint coordinates**, not receiver coordinates.
The lat/lon values should be the halfway point between WWV (40.68N,
105.04W) and each receiver:

```
IPP lat = (40.68 + receiver_lat) / 2
IPP lon = (-105.04 + receiver_lon) / 2
```

Example for N6RFM (receiver: 32.94N, 97.21W):

```
IPP lat = (40.68 + 32.94) / 2 = 36.81N
IPP lon = (-105.04 + -97.21) / 2 = -101.13W
```

**`max_lag_seconds`:** set to approximately 1/3 of the expected TID
period to prevent period aliasing. For the Jan 2026 event (~90 min
period): `"max_lag_seconds": 1800` (30 minutes).

---

## Step 8 — Run DOA inversion

```bash
python3 tid_doa.py event.json
```

The run log is written to `runs/<timestamp>_run.log` and contains
all inputs, lags, and result diagnostics.

**Example output:**

```
Pairwise time lags:
  AA6BD -> AC0G_ND    lag=  +26.8 s  corr=+0.604
  AA6BD -> N6RFM      lag=+1182.8 s  corr=+0.582
  AA6BD -> W7LUX      lag=+1372.5 s  corr=+0.482
  AC0G_ND -> N6RFM    lag=+1449.9 s  corr=+0.378
  AC0G_ND -> W7LUX    lag=+1659.8 s  corr=+0.371
  N6RFM -> W7LUX      lag=  -10.4 s  corr=+0.845

Phase speed:    262 m/s
Coming from:    37 deg (NNE)
Heading toward: 217 deg (SSW)
```

---

## Step 9 — Interpret DOA diagnostics

Five diagnostics are reported after the result. These are **internal
consistency checks** — they cannot confirm a result is physically real.

| # | Check | Good range | If flagged |
|---|-------|-----------|-----------|
| 1 | Geometry SVR | < 30 | Near-collinear — need more stations |
| 2 | Plane-wave residual | < 25% | Non-stationary TID or wrong peaks |
| 3 | Pairwise correlation | min > 0.4 | Drop flagged station |
| 4 | Triangle closure | < 15% | Wrong-peak lock — reduce max_lag |
| 5 | Phase speed | 100-1000 m/s | Likely aliased lags |

When [3] or [4] are flagged, a specific station to drop is suggested.
Test robustness by dropping it and re-running:

```bash
# Create 3-station config without AC0G_ND
python3 -c "
import json
e = json.load(open('event.json'))
e['stations'] = [s for s in e['stations'] if s['name'] != 'AC0G_ND']
json.dump(e, open('event_3stn.json', 'w'), indent=2)
print('Stations:', [s['name'] for s in e['stations']])
"
python3 tid_doa.py event_3stn.json
```

**Physical cross-checks (more reliable than diagnostics):**
- Northern stations must lead southern ones for auroral LSTIDs
  (positive lag = second station lags first station)
- Speed: 100-300 m/s → MSTID; 300-1000 m/s → LSTID
- Direction from 30-45° NNE = consistent with auroral origin
- Verify peak times visually in stacked spectrogram

---

## Step 10 — Visualise results

```bash
# Stacked Doppler comparison showing peak times
python3 tid_stack_plot.py --config event.json --output stack.png

# Array geometry map with wave direction arrow
python3 tid_map.py --config event.json --output map.png \
    --azimuth-toward 217 --speed 262
```

---

## Reference result — Jan 2026 event

| Metric | Value |
|--------|-------|
| Stations | N6RFM, AA6BD, W7LUX, AC0G/ND |
| Method | sgolay-ridge, all stations |
| Phase speed | 254–283 m/s |
| Coming from | 30–35° (NNE) |
| Heading toward | ~215° (SSW) |
| Classification | LSTID, auroral origin |
| Validation | Peak-time cross-check: AC0G/ND leads N6RFM by 23 min |
|             | over 388 km baseline → 280 m/s (matches DOA result) |

---

## Extraction method comparison

From validation on the Jan 2026 event:

| Method | Speed | From | Diagnostics |
|--------|-------|------|-------------|
| sgolay-ridge | 262 m/s | 37° | 3/5 flagged |
| fft | 99 m/s | 167° | 3/5 flagged |
| autocorr | varies | varies | — |

The FFT result is internally consistent but physically wrong — it
locked on the wrong xcorr peak for AC0G/ND due to E-region
contamination. sgolay-ridge correctly tracks the F-region carrier
and gives the physically meaningful result (consistent with
independent peak-time validation).

This illustrates the key advantage of sgolay-ridge: by constraining
the extraction to the F-region corridor, it avoids contamination
from other propagation modes.

---

## Further reading

- `WORKFLOW_TUTORIAL.md` — guided workflow using tid_workflow.py
- `FINDINGS.md` — research work log documenting method validation
- `drf_to_doppler.py --help` — full extraction options
- `tid_doa.py --help` — DOA config format and diagnostic thresholds
- `tid_spect_click.py --help` — corridor clicking options
