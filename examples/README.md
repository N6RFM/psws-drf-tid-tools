# Examples

This directory contains event configuration files and analysis reports.
Raw DRF recordings are hosted on the HamSCI PSWS data archive — see links below.

---

## Event 1 — 19 January 2026 LSTID

**Config:** `event_20260119.json`  
**Report:** `event_20260119_doa_report.pdf`

### Summary
Large-scale TID observed across the central US. 4-station array using WWV
10 MHz Doppler recordings. Best result from 3-station subset (AA6BD/N6RFM/W7LUX):

| Parameter | Value |
|-----------|-------|
| Phase speed | 304 m/s |
| Coming from | 10° NNE |
| Window | 2026-01-19T00:00–01:15 UTC |
| Stations | N6RFM, AA6BD, W7LUX (AC0G_ND dropped — E-region) |
| Flags | 0/5 |

### Stations
| Callsign | Location | Grid | Channel-num |
|----------|----------|------|------------|
| N6RFM | Texas | EM12jw | 0 |
| AA6BD | Alabama | EM75kb | 0 |
| W7LUX | Arizona | DM45dc | 0 |
| AC0G_ND | North Dakota | EN16ov | 4 (E-region contamination) |

### Raw data
DRF recordings are available from the HamSCI PSWS database.
If you have data from one station, use `find_event_stations.py` to
discover which other stations recorded the same event window:

````bash
python3 find_event_stations.py --drf-dir /path/to/your/station \
    --start 2026-01-19T00:00:00 --end 2026-01-19T02:00:00
````

This queries the HamSCI archive and returns a list of stations with
overlapping recordings that can be downloaded for multi-station DOA.

### Reproducing the analysis
```bash
# Download DRF data to a local directory, then:
python3 tid_workflow.py --event-dir /path/to/tid_event_20260119 \
    --tx-lat 40.68 --tx-lon -105.04 --tx-name WWV \
    --tx-freq-mhz 10.0 --max-lag 40

# Or run DOA directly on extracted CSVs:
python3 tid_doa.py examples/event_20260119.json
```

---

## Example 2 — Synthetic ground-truth test

Unlike Event 1 above, this one needs no downloaded data and is always
available: `mock_psws_server.py` serves realistic fake stations
(TESTKEY/TESTA/TESTB/TESTC) with a real, known ground truth built in
— 400 m/s arriving from 270° true bearing, 60-minute period — so you
can check the pipeline's recovered result against a real answer
instead of just confirming it runs.

```bash
# Terminal 1
python3 mock_psws_server.py

# Terminal 2
export PSWS_BASE_URL=http://127.0.0.1:8765
python3 download_companions.py --date 2099-01-01 \
    --stations TESTKEY TESTA TESTB TESTC \
    --out-dir ~/Downloads/tid_event_20990101
python3 tid_workflow.py --event-dir ~/Downloads/tid_event_20990101 \
    --stations TESTKEY,TESTA,TESTB,TESTC --my-station TESTKEY --max-lag 30
```

A `wave-fit` run with the same window applied to all four stations
should land in the neighborhood of the 400 m/s / 270° ground truth —
see [`docs/TESTING_WITHOUT_LIVE_DATA.md`](../docs/TESTING_WITHOUT_LIVE_DATA.md)
for full details, expected precision, and how this differs from the
`synthetic_tests/` batch validation suite.

---

## Adding your own event

Copy one of the JSON configs above and edit the station list, window times,
and file paths. See `WORKFLOW_TUTORIAL.md` for a complete walkthrough.
