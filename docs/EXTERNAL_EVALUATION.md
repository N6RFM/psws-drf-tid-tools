# External Evaluation

After obtaining a DOA result from `tid_doa.py`, users are encouraged to corroborate it with
independent space weather data using the evaluation tools. All outputs
should be saved to `<event_dir>/runs/external_evaluations/`.

For example, HF signals refract or reflect from the ionosphere, so HF measurements are extremely
sensitive to small changes in layer height, gradients, and propagation path length.

Conversely, GNSS signals pass through the ionosphere and measure changes in total electron
content (TEC) along the path, making GNSS excellent for mapping the spatial structure,
direction, wavelength, and speed of TIDs over large regions.

## Tools

| Tool | Data source | What it checks |
|------|-------------|----------------|
| `fetch_ae_index.py` | AE index (WDC Kyoto) | Substorm activity at event time |
| `fetch_madrigal_tec.py` | GPS TEC (MIT Haystack Madrigal) | Independent TID lag/direction |

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
