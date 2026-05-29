# Cookbook

Task-oriented recipes for everyday use of **psws-drf-tid-tools**.
For a full narrative walkthrough of a complete analysis, see the
[workflow tutorial](../WORKFLOW_TUTORIAL.md). For when something goes wrong, see the
[troubleshooting guide](TROUBLESHOOTING.md).

Every script accepts `--help` and `--version`.

---

## Station discovery

### How do I find candidate stations for my event?

```bash
python3 find_event_stations.py \
    --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 \
    --my-call "N6RFM/5"
```

The first run takes 3–5 minutes to build a directory of all PSWS
stations (cached for a week in `.psws_station_cache.json`).

### How do I tune the geometric scoring?

The default favors paths of 700–1400 km with midpoints close to your
own. Override with:

```bash
--min-path-km 500        # accept shorter paths
--max-path-km 2000       # accept longer paths
--max-mid-dist-km 2000   # accept midpoints further from yours
```

### How do I refresh the station cache manually?

```bash
rm .psws_station_cache.json
```

### How do I find only stations with DRF I/Q (not just CSV)?

That is the default. The script filters by filename pattern
(`OBS<date>T<time>` indicates DRF). To include legacy CSV-only stations:

```bash
--include-csv
```

---

## DRF inspection

### How do I check which subchannel is 10 MHz on a multi-subchannel station?

```bash
python3 drf_inspect.py ./station_dir --frequency 10
```

Look for the row marked `*** YES ***` in the subchannel table.

### How do I batch-inspect every station in a folder?

```bash
python3 drf_inspect.py --all . --frequency 10
```

### How do I just read the metadata without identifying a frequency?

```bash
python3 drf_inspect.py ./station_dir
```

(Same command, without `--frequency`.)

### How do I tell which subchannels are actually active vs empty?

`drf_inspect.py` automatically prints a signal-level table at the end
of its output. EMPTY-flagged subchannels have RMS magnitude more than
10x below the median.

---

## Doppler extraction

### How do I extract a clean Doppler-vs-time CSV?

```bash
python3 drf_to_doppler.py ./station_dir \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 \
    --output station.csv --plot station.png
```

### What cadence should I use?

| Cadence | Use case |
|---|---|
| `--decim-seconds 60` | 24-hour surveys (low resolution, small files) |
| `--decim-seconds 10` | TID analysis (default, good resolution) |
| `--decim-seconds 1`  | Prompt flare signatures (SFD/SWF), high time res |

### How do I extract from a multi-subchannel station?

Pass `--subchannel N` where N is what `drf_inspect.py` reported:

```bash
python3 drf_to_doppler.py ./ac0g_nd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 4 \
    --output ac0g_nd.csv --plot ac0g_nd.png
```

### How do I widen the carrier search if Doppler exceeds ±5 Hz?

```bash
--search-band-hz 10
```

(Defaults to 5 Hz, which is the standard Grape baseband range.)

---


### How do I use the autocorr extraction method?

Use `--method autocorr` for the lag-1 complex autocorrelation estimator
(G3ZIL method). It is 2-3x smoother than FFT and preferred for heavily
E-region-contaminated MSTID pairs where the lag is less than 30% of
the wave period:

```bash
python3 drf_to_doppler.py ./ac0g_nd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 4 --method autocorr \
    --output ac0g_nd_autocorr.csv
```

Default is `--method fft`. For best results on contaminated stations,
use the interactive spline extraction (see recipe below).

### How do I compare FFT and autocorr side by side?

Extract both and overlay on the spectrogram:

```bash
python3 drf_to_doppler.py ./station --method fft --output station_fft.csv ...
python3 drf_to_doppler.py ./station --method autocorr --output station_autocorr.csv ...
python3 drf_spectrogram.py ./station --output overlay.png \
    --overlay "station_fft.csv:FFT" \
    --overlay "station_autocorr.csv:Autocorr:#FF9800"
```

The legend shows inter-method Pearson r and RMS diff. r > 0.95 and
RMS < 0.10 Hz means both methods are equivalent — use FFT. See
`docs/METHODOLOGY.md` Step 1b for the full decision guide.

### How do I use the interactive spline extraction (recommended)?

The interactive spline tool gives the most reliable results, especially
for stations with E-region contamination. Launch via `tid_workflow.py`
(recommended, method 1) or directly:

```bash
python3 tid_spect_click.py \
    --spectrogram station_tid_zoom_clean.png \
    --name STATION \
    --drf-dir ./station \
    --subchannel 0 \
    --corridor-width 0.4 \
    --seg-start 0 --seg-end 2
```

On open, cwt-prophet runs automatically (Pass 0). Key bindings:

    Click   Add anchor on F-region carrier (slow oscillation near 0 Hz)
    P       Re-run Prophet with anchors as constraints
    X       Export spline CSV
    W       Enter wave-fit mode (click cycle points, F to fit)
    R       Reset clicks
    Q       Quit

The PCHIP spline through anchor clicks IS the extracted Doppler.
No wrong-peak lock possible. Output: `station_spline_tid.csv`

**Multi-region corrections:** after pressing X, click on another
problem region and press X again. Each X sets the exported CSV as
the new baseline.

### How do I use anchor-guided cwt-prophet extraction?

Pass an anchors JSON (written automatically by `tid_spect_click.py`)
to constrain the CWT search around a user-defined spline:

```bash
python3 drf_to_doppler.py ./station \
    --subchannel 0 \
    --start 2026-01-19T00:00:00 --end 2026-01-19T02:00:00 \
    --decim-seconds 60 --method cwt-prophet \
    --anchors station_tid_zoom_clean_anchors.json \
    --corridor-width 0.4 \
    --output station_cwt_prophet_tid.csv
```


### How do I use wave-fit extraction (--wave-only)?

Use when the TID shows at least 1.5 clear cycles in the window and you
want to fit a sine wave directly to the carrier. No Prophet run needed:

```bash
python3 tid_spect_click.py \
    --spectrogram station_tid_zoom_clean.png \
    --name STATION \
    --seg-start 0.0 --seg-end 2.0 \
    --wave-only
```

On open, the tool goes straight to wave-fit mode. Key bindings:

    Click   Mark a point on the TID cycle (brown diamond marker)
    F       Fit sine wave to clicked points
            (dialog asks: 1=half cycle, 2=full cycle, custom multiplier)
    W       Redo wave-fit (clear markers and start again)
    Q       Save and quit

Output: `station_wave_tid.csv`

**Note:** wave-fit DOA works best when TID period is similar across
all stations. If periods differ significantly, consider using spline
extraction instead.

---
## Spectrograms

### How do I make an annotated spectrogram?

```bash
python3 drf_spectrogram.py ./station_dir \
    --output spectrogram.png \
    --ylim=-2,2 \
    --annotate "00:00,01:15,DOA analysis window"
```

The `=` in `--ylim=-2,2` is required when the value starts with a
minus sign (argparse otherwise treats `-2,2` as a flag).

### How do I add a callsign or grid to the title?

For Grape v1.x DRFs whose metadata omits callsign/grid:

```bash
--callsign "N6RFM/5" --grid "EM12jw"
```

### How do I annotate multiple regions on one spectrogram?

Repeat `--annotate`:

```bash
python3 drf_spectrogram.py ./station_dir \
    --output annotated.png \
    --annotate "17:45,18:30,X1.9 flare SWF" \
    --annotate "22:30,24:00,LSTID onset"
```

Each annotation gets its own color (cyan, then magenta, then orange,
green).

### How do I add a single vertical event marker?

```bash
--vline "18:09,X1.9 flare peak"
```

### How do I restrict to a sub-window of the day?

```bash
--start "16:00" --end "23:59"
```

(Both HH:MM in UTC. Without these, defaults to 24 hours.)

### How do I make a higher-time-resolution spectrogram?

```bash
--window-minutes 0.25
```

(Defaults to 1.0 min. Smaller values give better time but worse
frequency resolution.)

---


---

### How do I increase the output image resolution?

Use `--dpi N` to set the PNG resolution. Default is 140 dpi (good for
screen viewing). Use 200-300 for publication quality, or 600 for
maximum detail:

```bash
python3 drf_spectrogram.py ./n6rfm --output n6rfm_hires.png --dpi 300 ...
```

Note: increasing DPI makes each spectrogram column physically larger
on screen but does not add new frequency or time information. The
spectrogram's information content is set by --window-minutes and
the recording sample rate, not by DPI.

### How do I overlay extracted Doppler traces on a spectrogram?

Use `--overlay CSV:label` (repeatable) to superimpose one or more
Doppler CSV traces on the spectrogram panel:

```bash
python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_overlay.png \
    --annotate "00:00,01:15,Analysis window" \
    --overlay "n6rfm_fft.csv:FFT" \
    --overlay "n6rfm_autocorr.csv:Autocorr:#FF9800"
```

The legend shows per-trace SNR and std, plus a single inter-method
summary line with Pearson r and RMS diff between the two traces.
Optionally specify a hex color as a third colon-separated field.

## TID window detection

### How do I find candidate TID windows automatically in a 24-hour survey?

```bash
python3 tid_window_detector.py survey.csv \
    --lat 32.94 --lon -97.21 \
    --plot survey_windows.png \
    --top 5
```

Real TID wavetrains typically score 0.3–0.5; background scores 0–0.1.

### How do I search for LSTIDs (longer periods)?

```bash
--period-min 60 --period-max 180 --slice-minutes 240
```

### How do I generate ready-to-run DOA configs from detected windows?

```bash
--write-configs ./configs/
```

The directory will contain one JSON per top window, each with
event_start/end and period_band pre-filled. You then add companion
stations to each.

---

## Two-station cross-correlation

### How do I run a quick two-station check?

```bash
python3 tid_pair.py n6rfm.csv aa6bd.csv \
    --lat1 32.94 --lon1 -97.21 --name1 N6RFM \
    --lat2 35.06 --lon2 -85.13 --name2 AA6BD \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00
```

Reports lag and correlation across raw + 4 standard bands. Look for
consistent lag values across bands (within ~10%) and correlation > 0.5.

### What does a negative lag mean?

`tid_pair.py` reports lag of station 2 relative to station 1. Negative
lag means station 2's signal arrives **before** station 1's, i.e. the
wave reached station 2 first. The "Direction" column translates this
to a true-bearing direction of motion assuming the wave moves along
the baseline.

### What is "apparent speed"?

`apparent_speed = baseline_distance / |lag|`. This is a **lower bound**
on the true horizontal phase speed. The true speed equals the apparent
speed only if the wave is exactly aligned with the baseline.

---

## Multi-station direction-of-arrival

### How do I build a DOA config interactively?

```bash
python3 tid_doa_config.py --output event.json --scan .
```

`--scan .` auto-discovers CSVs and matching DRF dirs in the current
directory; the script pre-fills station coordinates from DRF metadata,
suggests an event window from the CSV time overlap, and prompts you
for anything missing.

### How do I build a config non-interactively?

```bash
python3 tid_doa_config.py --output event.json --scan . --auto
```

Uses discovered values + safe defaults with no prompts.

### How do I run the DOA inversion?

```bash
python3 tid_doa.py event.json
```

The script prints pairwise lags and the final slowness-vector solution.

### Should I use bandpass filtering?

**No, in almost every case.** The default `use_bandpass: false` is
correct. Bandpassing slow TID signals produces nearly-sinusoidal traces
whose autocorrelation has multiple lobes one period apart, causing the
lag-finder to grab a secondary peak. (See the
[troubleshooting guide](TROUBLESHOOTING.md) for the gory details.)

If you do enable bandpass, set `max_lag_seconds` < `period_band_seconds[0]/2`.

### How do I override the auto-computed max-lag?

Add to your config:

```json
"max_lag_seconds": 1200
```

Otherwise the script uses `largest_baseline_km * 1000 / min_expected_speed_m_s`
(default 100 m/s).

### How do I tighten the search for a faster-than-LSTID wave?

```json
"min_expected_speed_m_s": 300
```

---

## Visualizations

### How do I make a stacked multi-station comparison?

```bash
python3 tid_stack_plot.py \
    --config event.json \
    --output stack.png \
    --ylim=-2,2
```

Each panel shows one station's Doppler trace on a shared time axis,
with each station's peak marked.

### How do I overlay a reference time line on all panels?

```bash
--reference-time 2026-01-19T00:50:00
```

### How do I use the stack plot with manual station list (not from config)?

```bash
python3 tid_stack_plot.py \
    --stations N6RFM:n6rfm.csv AA6BD:aa6bd.csv \
               W7LUX:w7lux.csv AC0G_ND:ac0g_nd.csv \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --output stack.png
```

### How do I make an array geometry map?

```bash
python3 tid_map.py \
    --config event.json \
    --output map.png \
    --azimuth-toward 215 \
    --speed 666
```

With `cartopy` installed, the map gets US state outlines. Without it,
falls back to a plain lat/lon plot. (Install with
`pip install cartopy`.)

### How do I make a map without the wave arrow (just geometry)?

Omit `--azimuth-toward`:

```bash
python3 tid_map.py --config event.json --output map.png
```

### How do I adjust the wave arrow length?

```bash
--arrow-length-km 600
```

Default is 400 km.

---

## File and config management

### Where do I keep the example configs?

The repo includes example configs and event data. Copy and adapt:

```bash
# Jan 2026 LSTID (4-station)
cp examples/event_20260119.json my_event.json

# May 2024 LSTID (3-station)
cp examples/event_20240517.json my_event.json

# Edit the dates, stations, coordinates...
python3 tid_doa.py my_event.json
```

See `examples/README.md` for event descriptions and data access instructions.

### What does the cache file `.psws_station_cache.json` do?

It stores the list of PSWS stations and their metadata so
`find_event_stations.py` doesn't re-fetch them every run. Refreshed
weekly automatically; force a refresh by deleting the file.

### What about generated files? Should I commit them?

No. The `.gitignore` excludes `*.csv`, `*.png` (except in `docs/`),
`*.pdf` (except in `docs/` and `examples/`), `*.h5`, and `OBS*`
directories. Only source code, example configs, and example data
should be committed.

---

## Quick gotchas reference

| Symptom | Cause | Fix |
|---|---|---|
| Doppler trace looks like a square wave | Wrong `--subchannel` | Re-run `drf_inspect.py`; use the right index |
| `--ylim -2,2` rejected by argparse | Negative value treated as flag | Use `--ylim=-2,2` |
| `find_event_stations.py` first run is slow | Building station cache | Wait 3–5 min; subsequent runs fast |
| Multi-subchannel station has no `*** YES ***` | Frequency not recorded | Check `drf_inspect.py` table; pick nearest |
| `tid_doa.py` correlations < 0.4 across all pairs | Wrong analysis window | Look at spectrograms; pick a cleaner window |
| `tid_doa.py` one lag at the edge of max_lag_s | Pair too noisy or wrong cycle | Reduce `max_lag_seconds` or drop that station |
| `tid_map.py` says "install cartopy" | Optional dep missing | `pip install cartopy` for nicer maps |


## Recipe: handle a noisy companion station

When `quality_summary.py` flags a station as POOR for jitter (typically
> 0.15 Hz), the cross-correlation in `tid_doa.py` may produce a
spurious or unstable lag. Smooth the Doppler series before correlation:

```
python3 tid_doa.py event.json --smooth 30
```

The same flag is available on `drf_to_doppler.py` (smooth the CSV at
extraction time) and `tid_pair.py` (smooth for pair analysis).

When in doubt, run with and without smoothing and compare the DOA
result. If the answer is broadly the same (within ~10°), the wave
signal is robust; if it changes substantially, the station is
contributing more noise than wave information.
