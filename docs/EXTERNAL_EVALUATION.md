# External Evaluation

After obtaining a DOA result from `tid_doa.py`, corroborate it with
independent space weather data using the evaluation tools. All outputs
should be saved to `<event_dir>/runs/external_evaluations/`.

## Tools

| Tool | Data source | What it checks |
|------|-------------|----------------|
| `evaluate_external.py` | Kp (GFZ), AE (Kyoto), GloTEC (NOAA) | Full automated evaluation |
| `fetch_ae_index.py` | AE index (WDC Kyoto) | Substorm activity at event time |
| `fetch_glotec.py` | GloTEC TEC anomaly (NOAA NCEI) | Storm-time TEC enhancement |
| `fetch_madrigal_tec.py` | GPS TEC (MIT Haystack Madrigal) | Independent TID lag/direction |

## 1. Full automated evaluation (Kp + AE + GloTEC)

```bash
python3 evaluate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 304 --azimuth-from 10 \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --output-dir <event_dir>/runs/external_evaluations
```

Outputs: `kp_plot.png`, `ae_plot.png`, `glotec_event_montage.png`,
`glotec_before_after.png`, `glotec_diff.png`, `evaluation_report.txt`

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

## 3. GloTEC analysis

Download the GloTEC tar.gz for your event date from NOAA NCEI:
https://www.ngdc.noaa.gov/stp/iono/ustec/

```bash
python3 fetch_glotec.py \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --output-dir <event_dir>/runs/external_evaluations
```

**Note:** GloTEC ~2° resolution can mask individual LSTID wavefronts.
For wavefront tracking use Madrigal GPS TEC (below).

## 4. Madrigal GPS TEC cross-correlation

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
