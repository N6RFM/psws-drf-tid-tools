# External Results Evaluation

This document describes how to independently evaluate a TID
direction-of-arrival (DOA) result using publicly available space weather
data sources. For a worked example using the Jan 2026 event, see
`examples/EXTERNAL_RESULTS_EVALUATION.md`.

---

## Verification Strategy — Direction and Speed

Two independent checks address the two key DOA outputs separately.

---

### Verifying direction — peak succession (internal, no external data)

The most reliable direction check uses only the pairwise lag table
produced by `tid_doa.py`. No external data required.

**Method:**
For a wave propagating toward azimuth θ, the station geometrically
closest to the source (in the FROM direction) should show its Doppler
peak first — it has the most negative lag relative to all other stations.

**Example (Jan 2026, wave from 30° NNE):**

| Pair | Lag (s) | Sign correct? |
|------|---------|---------------|
| AA6BD → N6RFM | +1253 | ✓ AA6BD (easternmost) leads |
| AA6BD → W7LUX | +1481 | ✓ AA6BD leads |
| N6RFM → W7LUX | +228  | ✓ N6RFM (more eastern) leads |

All three pairs confirm NNE origin. This is a model-free directional
verification — no inversion, no external network.

**When succession fails:** if any lag sign disagrees with the predicted
direction, suspect a 180° alias or wrong-peak lock in that pair.
The diagnostic [4] triangle closure check in `tid_doa.py` flags this.

---

### Verifying speed — Madrigal GPS TEC cross-correlation

The `fetch_madrigal_tec.py` tool provides independent speed evidence
by cross-correlating GPS TEC time series at station locations.

**Key considerations:**

1. **Geometry is critical.** The GPS TEC xcorr measures the
   along-baseline lag, not the true phase lag. The relationship is:

   ```
   along-baseline lag = true lag × cos(angle between wave and baseline)
   ```

   When the baseline is perpendicular to the wave (angle = 90°),
   the along-baseline lag → 0 regardless of true speed. When
   parallel (angle = 0°), along-baseline lag = true lag.

2. **Choose the best baseline.** For GPS TEC speed verification,
   use the station pair whose baseline is most aligned with the wave
   propagation direction (angle < 45°). Discard pairs with angle > 60°.

3. **Primary xcorr peak ≠ TID peak.** The primary peak at lag=0
   reflects correlated storm-time TEC background. Look for a
   secondary peak near the DOA-predicted lag.

4. **Amplitude limit.** GPS TEC TID amplitude is ~0.1-0.5 TECU.
   During geomagnetic storms, background TEC changes 10-20× faster.
   Detrending (polynomial removal) is essential but imperfect.

**Jan 2026 worked example:**

| Pair | Baseline° | Angle to wave | GPS TEC lag | DOA lag | Agreement |
|------|-----------|---------------|-------------|---------|-----------|
| AA6BD→W7LUX | 272° | 62° | 22 min | 24.7 min | 12% on lag |
| AA6BD→N6RFM | 256° | 46° | 0 min (ambiguous) | 20.9 min | — |
| N6RFM→W7LUX | 282° | 72° | 0 min (ambiguous) | 3.8 min | — |

The AA6BD→W7LUX baseline is 62° from the wave direction — not ideal
but the best available. The 12% lag agreement is encouraging; the
implied true speed (~423 m/s) differs from the DOA result (239 m/s)
partly due to this geometric projection uncertainty.

**Ideal geometry for future events:** arrange station pairs so at
least one baseline runs roughly parallel to the expected wave
propagation direction (NNE-SSW for auroral LSTIDs over CONUS).

---

## Overview

A DOA result (phase speed and azimuth) from `tid_doa.py` is an internal
consistency estimate — it tells you whether the pairwise time lags are
consistent with a single plane wave, but it cannot confirm the result is
physically real. External evaluation uses independent data sources not
derived from the HF Doppler recordings.

### What external data can verify

| Data source | Can verify | Cannot verify |
|-------------|------------|---------------|
| Kp index | Geomagnetic storm context | Speed, direction |
| AE/SME index | Substorm onset timing | Speed, direction |
| Peak succession | Propagation direction | Speed magnitude |
| GPS TEC (IONEX) | Wavefront speed + direction | Requires NASA Earthdata auth |
| Ionosondes (foF2) | Period, amplitude | US data gap since late 2023 |
| SuperDARN | Spatial ionospheric structure | RTI = range only; fan = browser |

---

## Automated Tools

Three scripts ship with this toolkit and require only:
```bash
pip install requests matplotlib numpy Pillow
```

---

### evaluate_external.py — combined evaluation report

The primary tool. Fetches Kp and AE automatically, and optionally

```bash
python3 evaluate_external.py \
    --date YYYY-MM-DD \
    --event-start YYYY-MM-DDTHH:MM:SSZ \
    --event-end   YYYY-MM-DDTHH:MM:SSZ \
    --speed-m-s SPEED \
    --azimuth-from AZIMUTH \
    --output-dir ./evaluation
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `--date` | Yes | Event date YYYY-MM-DD |
| `--event-start` | Yes | Event window start ISO 8601 UTC |
| `--event-end` | Yes | Event window end ISO 8601 UTC |
| `--speed-m-s` | Yes | DOA phase speed in m/s |
| `--azimuth-from` | Yes | Wave coming FROM azimuth (degrees true) |
| `--output-dir` | No | Output directory (default: current dir) |
| `--skip-ae` | No | Skip AE fetch if WDC Kyoto unavailable |

**Outputs:**

| File | Description |
|------|-------------|
| `kp_plot.png` | Kp index with event window + predicted substorm onset |
| `ae_plot.png` | AE index full day + zoom with event window |
| `evaluation_report.txt` | Full text summary of all findings |

**Travel time logic:**

The tool computes the expected substorm onset time as:

```
onset = event_start − (distance_km × 1000) / speed_m_s / 3600
```

where `distance_km = 3300` km (approximate auroral zone to mid-latitude
US array). If Kp ≥ 2.0 within ±2 hours of this predicted onset, the
timing is flagged as consistent.

---

### fetch_ae_index.py — AE index retrieval and plotting

Fetches 1-minute AE from the WDC Kyoto real-time repository and
produces a full-day + zoom plot with event window and travel time marker.

```bash
python3 fetch_ae_index.py \
    --date YYYY-MM-DD \
    --event-start YYYY-MM-DDTHH:MM:SSZ \
    --event-end   YYYY-MM-DDTHH:MM:SSZ \
    --speed-m-s SPEED \
    --output-dir ./evaluation
```

**Data source:**
```
https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/data_dir/YYYY/MM/DD/aeYYMMDD
```

**File format:**
Each line covers one hour of 1-minute AE values. Values start at
column 40. Line prefix identifies the hour (E00 = 00 UTC, E23 = 23 UTC):
```
AEALAOAU    YYMMDDEHH AE QUICKLK    val val val ...
```

**Outputs:** `ae_YYYYMMDD.png`, `ae_YYYYMMDD.csv`

**Data availability:** WDC Kyoto real-time AE is available from
December 2024 onwards via the `data_dir` path above. For earlier dates
use the provisional/final archive at:
`https://wdc.kugi.kyoto-u.ac.jp/aedir/index.html`

---

## Manual Evaluation Sources

These require only a browser — no registration needed.

---

### Kp index — GFZ Potsdam

**URL:** `https://kp.gfz-potsdam.de/en/data`

**API (used by evaluate_external.py):**
```
https://kp.gfz-potsdam.de/app/json/?start=YYYY-MM-DDTHH:MM:SSZ&end=...&index=Kp
```

**What to look for:**
- Kp ≥ 3 in the hours preceding the event — moderate geomagnetic
  activity consistent with auroral LSTID generation
- Kp spike approximately `distance / speed / 3600` hours before the
  event window — this is the substorm onset that launched the TID

---

### AE / SME index — SuperMAG

**URL:** `https://supermag.jhuapl.edu/indices/`

SuperMAG SME uses hundreds of ground magnetometers and is more
sensitive to substorm onset than Kp. No registration required for
browser plotting.

**How to use:**
1. Navigate to the URL above
2. Under "Auroral Electrojet Indices" check **SME** and **SML**
3. Set time range: event date − 6h through event date + 3h
4. Click "Plot Indices"

**What to look for:**
- SME spike ≥ 200 nT occurring ~3-4 hours before the event window
  (for a mid-latitude US array and auroral source)
- Onset timing: travel time (hours) = 3300 km / speed_m_s / 3.6

---

### SuperDARN RTI plots

**URL:** `http://vt.superdarn.org`

SuperDARN is an HF radar network that directly measures ionospheric
convection. Range-Time Intensity (RTI) plots show echo strength and
line-of-sight velocity vs range and time.

**Best radars for mid-latitude US events:**

| Radar | Code | Location | Coverage |
|-------|------|----------|----------|
| Fort Hays East | FHE | Kansas | Central US |
| Fort Hays West | FHW | Kansas | Central US |
| Blackstone | BKS | Virginia | US East |
| Christmas Valley East | CVE | Oregon | Western US |
| Christmas Valley West | CVW | Oregon | Western US |
| Wallops Island | WAL | Virginia | US East coast |

**How to use:**
1. Go to `http://vt.superdarn.org` → Data Library → RTI Plots
2. Select radar, date and time range covering the event
3. Look for: dense ground scatter band (strong echoes at 1200-1700 km
   slant range) and whether its boundary moves equatorward over time

**Limitation:** RTI shows range vs time but not azimuth — a moving
ground scatter boundary is consistent with a TID but cannot give
direction without fan plots (fan plots require registration).

---

## GPS TEC — Speed and Direction Verification

### IONEX files (requires NASA Earthdata auth — free)

IONEX files contain global TEC maps at 2-hour cadence on a
2.5° × 5° grid from multiple analysis centres.

**Register free:** `https://urs.earthdata.nasa.gov/`

**Download after registering:**
```bash
echo "machine urs.earthdata.nasa.gov login USER password PASS" >> ~/.netrc
chmod 600 ~/.netrc

# Example: JPL IONEX for Jan 19 2026 (DOY 019) — new IGS filename format
curl -n -L \
  "https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz" \
  -o JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz
gunzip JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz

# Note: new IGS filename format (2022+): CCCCSSSSOOO_YYYYDDDHHMM_LEN_SMP_TYP.FMT
# Browse directory first to find exact filename:
# https://cddis.nasa.gov/archive/gnss/products/ionex/YYYY/DOY/
# Authorize CDDIS_Archive at https://urs.earthdata.nasa.gov/ first
```

**File naming:** `{centre}g{DOY}0.{YY}i.gz`

| Centre | Code | Notes |
|--------|------|-------|
| JPL | `jplg` | Recommended for CONUS |
| CODE Bern | `codg` | Global coverage |
| IGS combined | `igsg` | Multi-centre combination |

**Parse with Python:**
```python
import numpy as np

# Standard IONEX grid
lats = np.arange(87.5, -90, -2.5)   # 71 latitudes
lons = np.arange(-180, 185, 5)       # 73 longitudes

# Each TEC map block starts with 'START OF TEC MAP'
# Values in 0.1 TECU (divide by 10); 9999 = missing
# Rows of up to 16 integers per line within each map
```

### Madrigal GPS TEC (MIT Haystack)

Higher spatial resolution than IONEX — line-of-sight TEC at individual
GPS receiver pairs can resolve TID wavefronts.

**Access:** `https://cedar.openmadrigal.org/`

```python
pip install madrigalWeb

import madrigalWeb.madrigalWeb as mad
m = mad.MadrigalData("https://cedar.openmadrigal.org/")

# GPS TEC instrument code = 8000
exps = m.getExperiments(8000,
                        YYYY, MM, DD, 0, 0, 0,
                        YYYY, MM, DD, 23, 59, 59)
```

**Note:** Jan 2026 data IS ingested and confirmed available (May 2026).
GPS TEC typically appears in Madrigal within 2-4 weeks of the event.
Use `fetch_madrigal_tec.py` for automated retrieval and xcorr analysis.
Availability check:
```python
exps = m.getExperiments(8000, YYYY, MM, DD, 0,0,0, YYYY, MM, DD, 23,59,59)
print(f'Found {len(exps)} experiments')
```

---

## Ionosondes

Ionosondes measure the F-region critical frequency (foF2) every
15 minutes. A passing TID produces oscillations in foF2 at the TID
period. Comparing foF2 oscillation timing at two ionosondes gives an
independent along-baseline phase speed estimate.

**GIRO DIDBase:** `https://giro.uml.edu/ionoweb/`

**API:**
```
https://lgdc.uml.edu/common/DIDBGetValues?ursiCode=CODE&charName=foF2
    &fromDate=YYYY.MM.DD&toDate=YYYY.MM.DD
```

**US station limitation:** The NEXION ionosonde network stopped sharing
US data to GIRO after late 2023. US stations (e.g. BC840 = Boulder CO)
show no data after 2024 in DIDBase. Non-US stations are unaffected.

---

## Peak Succession Check (internal — no external data)

For a plane wave from azimuth θ, the station closest to the source
direction should show the Doppler peak first. This can be verified
directly from the pairwise lag table produced by `tid_doa.py`:

1. Identify which station is closest to the source direction
2. Verify that station has negative lag (leads) relative to all others
3. Verify the lag magnitudes are consistent with the inter-station
   distances projected onto the wave vector

This is a model-free directional check requiring no external data.

---

## Summary of Data Sources

| Source | URL | Auth | Tool |
|--------|-----|------|------|
| Kp index | https://kp.gfz-potsdam.de/app/json/ | None | evaluate_external.py |
| AE index | https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/ | None | fetch_ae_index.py |
| SuperMAG SME | https://supermag.jhuapl.edu/indices/ | None | Browser only |
| SuperDARN RTI | http://vt.superdarn.org | None | Browser only |
| IONEX/CDDIS | https://cddis.nasa.gov/archive/gnss/products/ionex/ | NASA Earthdata (free) | curl + Python |
| Madrigal TEC | https://cedar.openmadrigal.org/ | None | ✓ fetch_madrigal_tec.py |
| GIRO ionosondes | https://giro.uml.edu/ionoweb/ | None | Browser / API (US gap 2024+) |

---

*See `examples/EXTERNAL_RESULTS_EVALUATION.md` for a worked example
using the Jan 2026 LSTID event (239 m/s from 30° NNE).*
