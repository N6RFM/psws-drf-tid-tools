# External Evaluation

After obtaining a DOA result from `tid_doa.py`, users are encouraged to corroborate it with
independent space weather data using the evaluation tools. All outputs
should be saved to `<event_dir>/runs/external_evaluations/`.

For example, HF signals refract or reflect from the ionosphere, so HF measurements are extremely
sensitive to small changes in layer height, gradients, and propagation path length.

Conversely, GNSS signals pass through the ionosphere and measure changes in total electron
content (TEC) along the path, making GNSS excellent for mapping the spatial structure,
direction, wavelength, and speed of TIDs over large regions.

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

## Tools

| Tool | Data source | What it checks |
|------|-------------|----------------|
| `fetch_ae_index.py` | AE index (WDC Kyoto) | Substorm activity at event time |
| `fetch_madrigal_tec.py` | GPS TEC (MIT Haystack Madrigal) | Independent TID lag/direction |


## 1. Full evaluation (evaluate_external.py)

```bash
python3 evaluate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 304 --azimuth-from 10 \
    --output-dir <event_dir>/runs/external_evaluations
```

## 2. AE index only

```bash
python3 fetch_ae_index.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 304 \
    --output-dir <event_dir>/runs/external_evaluations
```

Fetches 1-minute AE from WDC Kyoto. Plots full day + zoom with event
window and predicted substorm onset marker.

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

\`\`\`bash
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

## 4. Kp index

```bash
python3 fetch_kp_index.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --output-dir <event_dir>/runs/external_evaluations
```

Fetches 3-hour Kp from GFZ Potsdam. Plots full day bar chart with
storm threshold lines (Kp 3, Kp 5) and event window shaded.
Stats box shows event condition (quiet/unsettled/storm), event max/mean Kp,
and day max Kp.

## Output directory

Save all evaluation outputs to the event data directory:
`<event_dir>/runs/external_evaluations/`

Example: `~/Downloads/tid_event_20260119/runs/external_evaluations/`

## xcorr aliasing note

For LSTID events with ~60 min period, set `--max-lag 20` (minutes)
to prevent alias peak lock. See `docs/ASSESSING_RESULTS.md` for details.

## Additional Resources

- SuperMAG: https://supermag.jhuapl.edu/indices/
- SuperDARN: http://vt.superdarn.org
- NASA Earthdata: https://urs.earthdata.nasa.gov/
- See `docs/COOKBOOK.md` for task-oriented recipes
