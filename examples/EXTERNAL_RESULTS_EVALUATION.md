# External Results Evaluation — Jan 2026 Worked Example

This document describes how to independently evaluate a TID
direction-of-arrival (DOA) result using publicly available space weather
data. It covers the three automated tools shipped with this toolkit, the
manual browser-based sources, and the Jan 2026 event as a worked example.

---

## Overview

> **Quick reference:** See `docs/COOKBOOK.md` — 'How do I verify my DOA result is physically real?' for the two-step direction/speed verification guide.


A DOA result (phase speed and azimuth) from `tid_doa.py` is an internal
consistency estimate — it tells you whether the pairwise time lags are
consistent with a single plane wave, but it cannot confirm the result is
physically real. External evaluation uses independent data sources that
are not derived from the HF Doppler recordings.

### What external data can verify

| Data source | Can verify | Cannot verify |
|-------------|-----------|---------------|
| Kp index | Geomagnetic storm context | Speed, direction |
| AE/SME index | Substorm onset timing | Speed, direction |
| Peak succession | Propagation direction | Speed magnitude |
| GloTEC TEC maps | Storm-time context | TID speed/direction at std res |
| GPS TEC (IONEX) | Wavefront speed + direction | Requires auth |
| Ionosondes (foF2) | Period, amplitude | US data gap since 2023 |
| SuperDARN | Spatial ionospheric structure | Browser only |

---

## Automated Tools

Four scripts automate the retrieval and analysis of external data:
- `evaluate_external.py` — Kp + AE + GloTEC combined report
- `fetch_ae_index.py` — AE index only
- `fetch_glotec.py` — GloTEC TEC anomaly analysis
- `fetch_madrigal_tec.py` — Madrigal GPS TEC retrieval + TID xcorr

Requirements: `pip install requests matplotlib numpy Pillow madrigalWeb`

---

### evaluate_external.py — combined validation report

The primary evaluation tool. Fetches Kp, AE, and optionally analyses
GloTEC maps in one run.

```bash
python3 evaluate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 239 \
    --azimuth-from 30 \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --output-dir ./evaluation
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `--date` | Event date YYYY-MM-DD |
| `--event-start` | Event window start (ISO 8601 UTC) |
| `--event-end` | Event window end (ISO 8601 UTC) |
| `--speed-m-s` | DOA phase speed in m/s |
| `--azimuth-from` | Wave coming FROM azimuth (degrees true) |
| `--glotec-dir` | Path to extracted GloTEC directory (optional) |
| `--output-dir` | Output directory (default: current dir) |
| `--skip-ae` | Skip AE fetch if WDC Kyoto unavailable |

**Outputs:**

| File | Description |
|------|-------------|
| `kp_plot.png` | Kp index with event window and predicted substorm onset |
| `ae_plot.png` | AE index full day + zoom |
| `glotec_event_montage.png` | CONUS anomaly maps spanning event window |
| `glotec_before_after.png` | Before / during / after comparison |
| `glotec_diff.png` | Pixel difference: event end − event start |
| `evaluation_report.txt` | Full text summary of all findings |

**Travel time logic:**

The tool computes the expected substorm onset time as:

```
onset = event_start − (distance_km × 1000) / speed_m_s / 3600
```

where `distance_km = 3300` km (approximate auroral zone to mid-latitude
US array). If Kp is elevated (≥ 2.0) within ±2 hours of this predicted
onset, the timing is flagged as consistent.

---

### fetch_ae_index.py — AE index retrieval and plotting

Fetches 1-minute AE from the WDC Kyoto real-time repository.

```bash
python3 fetch_ae_index.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 239 \
    --output-dir ./validation
```

**Data source:**
```
https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/data_dir/YYYY/MM/DD/aeYYMMDD
```

**File format:**
Each line covers one hour. Values start at column 40 and are 60
consecutive 1-minute AE values in nT. Line prefix identifies the hour:
```
AEALAOAU    260119E00AE QUICKLK       73    70    70 ...
                  ^^^
                  E00 = hour 00 UTC
```

**Outputs:** `ae_YYYYMMDD.png`, `ae_YYYYMMDD.csv`

**Note on data availability:** WDC Kyoto real-time AE is available from
December 2024 onwards via the `data_dir` repository. For earlier dates
use the provisional or final AE archive at
https://wdc.kugi.kyoto-u.ac.jp/aedir/index.html

---

### fetch_glotec.py — GloTEC TEC anomaly analysis

Analyses GloTEC CONUS anomaly maps from a downloaded daily archive.

**Step 1 — download the archive:**
1. Browse to https://www.ngdc.noaa.gov/stp/iono/ustec/
2. Click "Download Data", search for your event date
3. Download `glotec_YYYY_MM_DD.tar.gz` (~270 MB per day)
4. Extract: `tar xzf glotec_YYYY_MM_DD.tar.gz`

**Step 2 — run analysis:**
```bash
python3 fetch_glotec.py \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --output-dir ./evaluation
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `--glotec-dir` | Path to extracted GloTEC directory |
| `--date` | Event date YYYY-MM-DD |
| `--event-start` | Event window start |
| `--event-end` | Event window end |
| `--product` | GloTEC product type (default: `anomcus`) |
| `--output-dir` | Output directory |

**Product types in GloTEC archive:**

| Code | Description | Best for |
|------|-------------|----------|
| `anomcus` | CONUS TEC anomaly (diff from 30-day median) | TID detection |
| `anomna` | North America TEC anomaly | Wider spatial context |
| `anomaly` | Global TEC anomaly | Global storm context |
| `100asm` | CONUS absolute TEC | Background level |
| `100na` | North America absolute TEC | Background level |
| `ray` | CONUS ray paths | Data coverage check |

**Colour scale:**
- Orange/brown = positive anomaly (TEC above 30-day median)
- Purple/blue = negative anomaly (TEC below 30-day median)
- Scale: approximately ±30 TECU

**Outputs:** `glotec_products.txt`, `glotec_event_montage.png`,
`glotec_before_after.png`, `glotec_diff.png`, `glotec_na_montage.png`

**TID detectability at GloTEC resolution:**

GloTEC's assimilation grid is ~2° (~200 km). An LSTID at 239 m/s with
~70 min period has wavelength ≈ 1000 km — in principle resolvable.
However, in the presence of a geomagnetic storm (Kp > 3) the broad
storm-time TEC enhancement (+15 TECU) dominates and masks the TID
amplitude (~1-2 TECU). The wavefront appears as a broad enhancement
retreating northward as the storm decays, not as discrete stripes.

For direct wavefront tracking at higher resolution, use the MIT Haystack
GPS TEC data in the Madrigal database (see below).

---

### fetch_madrigal_tec.py — Madrigal GPS TEC retrieval and TID xcorr

See `docs/EXTERNAL_RESULTS_EVALUATION.md` for full argument reference.
The Jan 2026 command and results are in the Worked Example section below.

Requirements: `pip install madrigalWeb`
No account needed — Madrigal uses open access (name/email only).

---

## Manual Evaluation Sources

These require browser access but no registration.

### SuperMAG SME index

URL: https://supermag.jhuapl.edu/indices/

SuperMAG SME is a high-station-count equivalent of the AE index. It is
more sensitive to substorm onset than Kp because it uses hundreds of
ground magnetometers rather than a handful.

**How to use:**
1. Navigate to the URL above
2. Under "Auroral Electrojet Indices" check **SME** and **SML**
3. Set time range: event date − 6h through event date + 3h
4. Click "Plot Indices"

**What to look for:**
- SME spike of 200+ nT occurring 3–4 hours before the event window
- This is the substorm that launched the LSTID
- Travel time calculation: distance (~3300 km) / speed (m/s) = hours

### SuperDARN RTI plots

URL: http://vt.superdarn.org

SuperDARN is an HF radar network that directly measures ionospheric
plasma velocity. Range-Time Intensity (RTI) plots show backscatter
echo strength and Doppler velocity vs time.

**Best radars for mid-latitude US events:**

| Radar | Code | Location | Coverage |
|-------|------|----------|---------|
| Fort Hays East | FHE | Kansas | Central US |
| Fort Hays West | FHW | Kansas | Central US |
| Blackstone | BKS | Virginia | US East |
| Christmas Valley E | CVE | Oregon | Western US |

**How to use:**
1. Navigate to http://vt.superdarn.org → Data Library → RTI plots
2. Select radar (FHE recommended for mid-latitude US)
3. Select date and time range
4. Look for: ground scatter boundary (dense band at 1200-1700 km slant
   range) moving equatorward — this tracks the TID wavefront

**Limitation:** RTI shows range vs time but not azimuth. Fan plots
show spatial structure but require registration.

---

## GPS TEC — Speed and Direction Verification

### GloTEC (automated, no auth)

As above — useful for storm context but insufficient resolution for
individual LSTID wavefront tracking.

### IONEX files (requires NASA Earthdata auth)

IONEX (IONosphere map EXchange) files contain global TEC maps at
2-hour cadence on a 2.5° × 5° grid. Multiple analysis centres produce
them daily; JPL and CODE are the most commonly used.

**Register (free):** https://urs.earthdata.nasa.gov/

**Download after registering:**
```bash
echo "machine urs.earthdata.nasa.gov login USER password PASS" >> ~/.netrc
chmod 600 ~/.netrc

# JPL IONEX for Jan 19 2026 (DOY 019)
curl -n -L -O \
  "https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/jplg0190.26i.gz"
gunzip jplg0190.26i.gz
```

**File naming:** `{centre}g{DOY}0.{YY}i.gz`
- `jplg` = JPL, `codg` = CODE, `igsg` = IGS combined
- DOY = day of year (3 digits), YY = 2-digit year

**Parse with Python:**
```python
import numpy as np

# IONEX grid: lat 87.5 to -87.5 step -2.5, lon -180 to 180 step 5
lats = np.arange(87.5, -90, -2.5)
lons = np.arange(-180, 185, 5)

# Read TEC maps (values in 0.1 TECU, 9999 = missing)
# Each map block starts with 'START OF TEC MAP'
# Values follow in rows of up to 16 integers per line
# Divide by 10 for TECU
```

### Madrigal GPS TEC (MIT Haystack)

The Madrigal database has higher-resolution GPS TEC (line-of-sight)
that can resolve individual TID wavefronts.

**Access:** https://cedar.openmadrigal.org/

```python
import madrigalWeb.madrigalWeb as mad
m = mad.MadrigalData("https://cedar.openmadrigal.org/")
exps = m.getExperiments(8000,           # instrument: GPS TEC
                        2026, 1, 19, 0, 0, 0,
                        2026, 1, 19, 23, 59, 59)
```

**Note:** Jan 2026 data IS ingested and confirmed available (May 2026).
GPS TEC typically appears within 2-4 weeks. Use `fetch_madrigal_tec.py`
for automated retrieval — see `docs/EXTERNAL_RESULTS_EVALUATION.md`.

---

## Ionosondes

Ionosondes measure foF2 (F-region critical frequency) every 15 minutes.
A passing TID shows as oscillations in foF2 with the TID period.

**GIRO DIDBase:** https://giro.uml.edu/ionoweb/

**Limitation for 2026:** The US NEXION ionosonde network stopped sharing
data to GIRO after late 2023. US stations (Boulder CO = BC840, etc.)
show no data after 2024 in DIDBase. Non-US stations are unaffected.

**Nearest non-US stations to the Jan 2026 array:**
- No good coverage — the array is mid-continental US

---

## Worked Example — Jan 2026 Event

**DOA result:** 239 m/s from 30° NNE (4 stations, 1/5 flags)
**Event window:** 2026-01-19 00:00–01:15 UTC

### Command used

```bash
python3 evaluate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 239 --azimuth-from 30 \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --output-dir examples/tid_event_20260119/evaluation
```

### Results

**Kp index (GFZ Potsdam):**

| Time UTC | Kp |
|----------|-----|
| Jan 18 18:00 | 3.7 |
| Jan 18 21:00 | 3.0 |
| Jan 19 00:00 | 3.3 ← event window |
| Jan 19 03:00 | 0.7 |

Travel time at 239 m/s over 3300 km = 3.83h → predicted onset
~20:10 UTC Jan 18. Kp=3.7 at 18:00 UTC is within ~2h — consistent.

**AE index (WDC Kyoto):**

| Window | AE mean | AE max |
|--------|---------|--------|
| Event (00:00–01:15 UTC) | ~325 nT | ~526 nT |
| Hour 02:00–03:00 UTC | ~115 nT | ~150 nT |

AE 300–500 nT during event window indicates active auroral electrojet —
the TID is being actively driven during the measurement window. The rapid
drop after 02:00 UTC is consistent with the Kp decline to 0.7.

**GloTEC CONUS anomaly:**

Large positive anomaly (+10 to +20 TECU) over northern CONUS during
event window — storm-time F-region enhancement consistent with Kp=3.3.
TID wavefront not resolvable at GloTEC resolution due to dominant
storm-time signal. Anomaly retreats northward between 00:05 and 01:05
UTC as storm decays.

**Peak succession (internal):**

| Pair | Lag | Expected sign | Consistent? |
|------|-----|---------------|-------------|
| AA6BD → N6RFM | +1253 s | + | ✓ |
| AA6BD → W7LUX | +1481 s | + | ✓ |
| N6RFM → W7LUX | +228 s | + | ✓ |

All lags consistent with NNE origin. AA6BD (Alabama, easternmost)
leads all stations as expected for a wave from 30° NNE.

**SuperMAG SME (browser):** SME 200–300 nT at Jan 18 18:00–22:00 UTC —
substorm ~3–4h before event window. Consistent with 239 m/s travel time.

**SuperDARN RTI (browser):** All 6 radars quiet during 00:00–01:15 UTC
event window. Confirms declining storm phase, clean measurement conditions.

### Pre-computed outputs

Validation plots are included in the repository:
```
examples/tid_event_20260119/evaluation/
    kp_plot.png
    ae_plot.png
    ae_index_20260119.png
    glotec_event_montage.png
    glotec_before_after.png
    glotec_diff.png
    glotec_anomaly_montage.png
    evaluation_report.txt
```

### What remains unverified

Speed (239 m/s) is not yet independently verified. The next steps are:

1. Register NASA Earthdata at https://urs.earthdata.nasa.gov/
2. Download IONEX file for the event date from CDDIS
3. Extract TEC at station locations and track wavefront position
   across successive 2-hour maps

---

## Summary of Data Sources

| Source | URL | Auth | Automated? |
|--------|-----|------|-----------|
| Kp index | https://kp.gfz-potsdam.de/app/json/ | None | ✓ evaluate_external.py |
| AE index | https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/ | None | ✓ evaluate_external.py |
| GloTEC | https://www.ngdc.noaa.gov/stp/iono/ustec/ | None | ✓ fetch_glotec.py |
| SuperMAG | https://supermag.jhuapl.edu/indices/ | None | Browser only |
| SuperDARN | http://vt.superdarn.org | None | Browser only |
| IONEX/CDDIS | https://cddis.nasa.gov/archive/gnss/products/ionex/ | NASA Earthdata | Pending |
| Madrigal TEC | https://cedar.openmadrigal.org/ | None | madrigalWeb |
| GIRO ionosondes | https://giro.uml.edu/ionoweb/ | None | US data gap 2024+ |
