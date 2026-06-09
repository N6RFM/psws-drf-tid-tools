# External Evaluation

After obtaining a DOA result from `tid_doa.py`, users are encouraged to corroborate it with
independent space weather data using the evaluation tools. All outputs
may be saved to `<event_dir>/runs/external_evaluations/`.

HF signals refract or reflect from the ionosphere, making HF TID measurements involving a limited 
number of stations extremely sensitive to small changes in layer height, gradients, and propagation path length.  

Amateur radio spot data (RBN, PSKReporter, WSPRNet) provides an independent view using a much larger dataset
— the gross spatial signature of an LSTID across the entire amateur radio network. 

GNSS signals pass through the ionosphere and measure changes in total electron
content (TEC) along the path, making GNSS highly valuable for mapping the spatial structure,
direction, wavelength, and speed of TIDs over large regions. 

---

## Geomagnetic Indices: Kp and AE

Kp and AE are not TID measurement tools. They are **forcing indicators** — they tell you
whether the ionosphere is being driven from above, and if so, how strongly. Think of them
as space weather context knobs that help you interpret *why* you are seeing a TID and
*what type it likely is*.

### Kp index (global geomagnetic activity)

Kp is a 3-hour planetary index derived from midlatitude magnetometers worldwide. It measures
the overall level of geomagnetic disturbance — essentially how disturbed the ionosphere is
at any given time.

| Kp  | Condition  | TID expectation                              |
|-----|------------|----------------------------------------------|
| 0–2 | Quiet      | MSTIDs may be present; atmosphere-driven     |
| 3–4 | Unsettled  | Mixed regime; weak storm effects possible    |
| 5+  | Storm      | LSTIDs very likely; auroral source dominant  |

Because Kp is a 3-hour average it cannot time individual TIDs or resolve substorm structure.
It is most useful for the broad question: *is this a storm-time ionosphere?* If Kp ≥ 5 and
you are seeing strong equatorward-propagating Doppler shifts, the connection to geomagnetic
forcing is likely.

### AE index (auroral electrojet activity)

AE is a high-latitude index measuring the strength of auroral ionospheric currents. Unlike
Kp, AE responds on timescales of minutes, making it useful for **timing the source** of an
LSTID rather than just characterizing the background condition.

The typical sequence for a storm-driven LSTID:

1. AE spike (substorm onset)
2. Energy deposition in the auroral zone (Joule heating, particle precipitation)
3. Atmospheric heating and expansion at high latitudes
4. LSTID launched 10–60 minutes after the spike
5. Wave propagates equatorward into CONUS

When you see an AE spike 15–45 minutes before your HF Doppler disturbance begins, that is
strong circumstantial evidence for an auroral source. This is where AE timing alignment with
your extracted trace becomes powerful.

### Quiet vs. storm-time signatures in HF Doppler

**Quiet conditions (Kp ≤ 2, low AE):** MSTIDs dominate. Expect clean periodic oscillations,
typically southwestward propagation, driven by atmospheric gravity waves rather than auroral
forcing. HF Doppler shows organized, relatively stable waveforms.

**Unsettled (Kp 3–4, moderate AE):** Mixed regime. Both MSTIDs and weak storm effects may
be present simultaneously, producing overlapping wave systems and more complex or irregular
HF signatures.

**Storm time (Kp ≥ 5, high AE spikes):** Strong LSTIDs dominate. Expect large-amplitude
equatorward-propagating wavefronts, large TEC perturbations, and strong HF Doppler shifts.
This is the regime where combining your DOA result with AE timing and Madrigal GPS TEC gives
the most complete picture.

---



## Tools

| Tool | Data source | What it checks |
|------|-------------|----------------|
| `evaluate_external.py` | Kp + AE (GFZ Potsdam / WDC Kyoto) | Storm level and substorm activity |
| [hamsci_LSTID_detection](https://github.com/HamSCI/hamsci_LSTID_detection) | Amateur radio spots (Madrigal) | Independent LSTID detection across network |
| `fetch_madrigal_tec.py` | GNSS TEC (MIT Haystack Madrigal) | Independent TID lag/direction |

---

## 1. Combined Kp and AE (evaluate_external.py)

```bash
python3 evaluate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 304 --azimuth-from 10 \
    --output-dir <event_dir>/runs/external_evaluations
```
---

## 2. HamSCI LSTID Detection

The [hamsci_LSTID_detection](https://github.com/HamSCI/hamsci_LSTID_detection) toolkit
(HamSCI NASA SWO2R Team) provides an independent automated method for detecting LSTIDs
from amateur radio spot data — RBN, PSKReporter, and WSPRNet — stored in Madrigal HDF5
format. Rather than measuring Doppler shift along individual propagation paths, it bins
millions of spots into range-time heatmaps and detects the moving edge of the ionospheric
reflection region using sinusoidal fitting.

This is complementary to HF Doppler DOA analysis: where psws-drf-tid-tools measures phase delays
between a small number of dedicated receivers, hamsci_LSTID_detection detects the gross spatial
signature of an LSTID across the entire amateur radio network. Agreement between the two methods
— timing, period, and propagation direction — is strong corroboration that a detected event is a
real large-scale wave.

---

## 3. Madrigal GPS TEC cross-correlation

GNSS TEC data from the CEDAR Madrigal Database provides the wide-area spatial coverage
that HF Doppler alone cannot. HF measurements are highly sensitive to ionospheric
disturbances but typically observe only one or a few radio paths — making it difficult
to independently determine a TID's direction, speed, wavelength, or regional extent.

Madrigal maps the disturbance across many simultaneous satellite-receiver paths, allowing
you to see the wavefront propagate across the ionosphere and estimate:

- propagation direction and DOA azimuth
- horizontal speed and wavelength
- regional morphology and wave extent
- timing relationships between stations

The two techniques are complementary. HF Doppler answers *when* the ionosphere changed
along a path; GNSS TEC answers *where* the disturbance is moving. Together they greatly
improve confidence that an HF Doppler signature is a true regional TID rather than a
local propagation effect or multipath artifact.

For storm and auroral forcing context, see the Kp and AE indices above.

```bash
python3 fetch_madrigal_tec.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --stations N6RFM,-100.93,36.87 AA6BD,-94.70,38.29 W7LUX,-108.50,37.94 \
    --user-name "Your Name" \
    --user-email "your@email.com" \
    --user-affiliation "Amateur Radio" \
    --doa-speed 304 --doa-azimuth-from 10 \
    --output-dir <event_dir>/runs/external_evaluations
```

**Required arguments:**
- `--stations`: NAME,LON,LAT triples for each receiver station
- `--user-name`, `--user-email`, `--user-affiliation`: required by
  the Madrigal API (free, no approval needed)
- `--doa-speed`, `--doa-azimuth-from`: your DOA result for comparison

---

## Some Other Manual Evaluation Sources

These require only a browser — no registration needed unless noted.

### SuperMAG SME / AE index

**URL:** `https://supermag.jhuapl.edu/indices/`

SuperMAG SME uses hundreds of ground magnetometers and is more
sensitive to substorm onset than Kp.

**How to use:**
1. Navigate to the URL above
2. Under "Auroral Electrojet Indices" check **SME** and **SML**
3. Set time range: event date − 6h through event date + 3h
4. Click "Plot Indices"

**What to look for:** SME spike ≥ 200 nT occurring ~3–4 hours before
the event window (for a mid-latitude US array and auroral source).
Travel time (hours) = 3300 km / speed_m_s / 3.6

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
3. Look for a dense ground scatter band (strong echoes at 1200–1700 km
   slant range) and whether its boundary moves equatorward over time

**Limitation:** RTI shows range vs time but not azimuth. Fan plots
give direction but require registration.

### IONEX GPS TEC (requires NASA Earthdata auth — free)

IONEX files contain global TEC maps at 2-hour cadence on a 2.5° × 5° grid.

**Register free:** `https://urs.earthdata.nasa.gov/`

```bash
echo "machine urs.earthdata.nasa.gov login USER password PASS" >> ~/.netrc
chmod 600 ~/.netrc

# JPL IONEX for Jan 19 2026 (DOY 019)
curl -n -L \
  "https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz" \
  -o JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz
gunzip JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz

# Browse directory for exact filename:
# https://cddis.nasa.gov/archive/gnss/products/ionex/YYYY/DOY/
```

| Centre | Code | Notes |
|--------|------|-------|
| JPL | `jplg` | Recommended for CONUS |
| CODE Bern | `codg` | Global coverage |
| IGS combined | `igsg` | Multi-centre combination |

---

## Additional Resources

- SuperMAG: https://supermag.jhuapl.edu/indices/
- SuperDARN: http://vt.superdarn.org
- NASA Earthdata: https://urs.earthdata.nasa.gov/
