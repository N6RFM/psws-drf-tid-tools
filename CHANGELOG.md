# Changelog

All notable changes to **psws-drf-tid-tools** are recorded here.
The project follows [Semantic Versioning](https://semver.org).

## [1.0.0] - 2026-05-12

Initial public release. Toolkit assembled around the analysis of the
**19 January 2026 X1.9 flare + LSTID event** observed by four HamSCI
Grape stations across the central US.

### Pipeline scripts

| Script | Purpose | Version |
|---|---|---|
| `find_event_stations.py` | Locate companion HamSCI stations for a given event date | 1.0.0 |
| `drf_inspect.py` | Verify DRF metadata and identify the correct subchannel for a target frequency | 1.0.0 |
| `drf_to_doppler.py` | Extract Doppler-vs-time CSV from raw DRF I/Q | 1.0.0 |
| `drf_spectrogram.py` | Render annotated Doppler spectrograms | 1.1.0 |
| `tid_window_detector.py` | Automatically locate TID windows in a Doppler survey | 1.0.0 |
| `tid_pair.py` | Two-station cross-correlation across multiple filter bands | 1.0.0 |
| `tid_doa_config.py` | Interactive config builder for `tid_doa.py` | 1.0.0 |
| `tid_doa.py` | Multi-station direction-of-arrival inversion | 1.1.0 |
| `tid_stack_plot.py` | Stacked multi-station Doppler comparison plot | 1.0.0 |
| `tid_map.py` | TID array geometry map with wave-direction overlay | 1.0.0 |

### Per-script highlights

#### `tid_doa.py` v1.1.0
- Default cross-correlation now operates on raw mean-subtracted Doppler
  (no bandpass). Bandpassing produced multi-lobed correlation functions
  that caused the lag-finder to lock onto wrong secondary peaks. The
  pre-1.1 behavior is still available via `use_bandpass: true` in the
  config.
- `max_lag_seconds` is now auto-computed from the largest pairwise
  baseline divided by `min_expected_speed_m_s` (default 100 m/s).

#### `drf_spectrogram.py` v1.1.0
- Added `--callsign` and `--grid` overrides for stations whose Grape v1.x
  DRF metadata omits those fields.

#### `find_event_stations.py` v1.0.0
- Discovered (and works around) several PSWS observation-portal quirks:
  - `sort=-startDate` uses upload timestamp rather than observation date
  - Multi-subchannel WSPRdaemon stations store comma-separated frequency
    lists that defeat exact-string filters
  - Per-station observation lists must be queried individually (rather
    than scanning the global date-sorted list)
  - File-type classification by filename pattern, not instrument string
