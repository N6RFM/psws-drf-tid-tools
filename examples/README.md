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
| Phase speed | 341 m/s |
| Coming from | 25° NNE |
| Window | 2026-01-19T00:01–02:03 UTC |
| Stations (best) | AA6BD, N6RFM, W7LUX |
| Flags | 1/5 |

### Stations
| Callsign | Location | Grid | Subchannel |
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

## Adding your own event

Copy one of the JSON configs above and edit the station list, window times,
and file paths. See `WORKFLOW_TUTORIAL.md` for a complete walkthrough.
