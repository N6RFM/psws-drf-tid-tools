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
use the anchor-guided cwt-prophet extraction (see recipe below).

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

### How do I use the anchor-guided cwt-prophet extraction (recommended)?

The anchor-guided cwt-prophet tool gives the most reliable results, especially
for stations with E-region contamination. Launch via `tid_workflow.py`
(recommended, method 1) or directly:

```bash
python3 tid_spect_click.py \
    --spectrogram station_tid_zoom_clean.png \
    --name STATION \
    --drf-dir ./station \
    --subchannel 0 \
    --corridor-width 0.4 \
    --seg-start 0 --seg-end 2 \
    --event-json event.json
```

On open, cwt-prophet runs automatically (Pass 0). Key bindings:

    Click   Add anchor on F-region carrier
    P       Re-run Prophet with anchors as hard constraints
    E       Export prophet CSV (recommended — smooth, guided trace)
    X       Export raw spline CSV (PCHIP through clicks only)
    W       Enter wave-fit mode (click cycle points, F to fit)
    Z       Undo last click
    R       Reset clicks
    C       Clear all (clicks + calibration)
    Q       Quit

**Recommended workflow:** click anchors where Prophet went wrong,
if auto-trace looks good press E; if not, click carrier and press X.
Use X only when the carrier is too complex for Prophet to fit.
`--event-json` auto-updates the event config on export.

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
    A       Accept candidate fit — writes final {stn}_wave_tid.csv
    W       Redo wave-fit (discards candidate, clear markers)
    Q       Quit without saving

Output: `station_wave_tid.csv`

**Note:** wave-fit DOA works best when TID period is similar across
all stations. If periods differ significantly, consider using spline
extraction instead.


---

## How do I evaluate my DOA result against independent data?

Three tools automate external space weather evaluation. They fetch
publicly available data from NOAA, WDC Kyoto, and GFZ Potsdam and
compare the timing and context against your DOA result.

### Quick start — automated evaluation

```bash
python3 evaluate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 239 --azimuth-from 30 \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --output-dir ./evaluation
```

Outputs: `kp_plot.png`, `ae_plot.png`, `glotec_event_montage.png`,
`glotec_before_after.png`, `glotec_diff.png`, `evaluation_report.txt`

### AE index only

```bash
python3 fetch_ae_index.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 239 \
    --output-dir ./evaluation
```

Fetches 1-minute AE from WDC Kyoto. Plots full day + zoom with event
window and predicted substorm onset marker (travel time = distance /
speed). Saves `ae_YYYYMMDD.png` and `ae_YYYYMMDD.csv`.

### GloTEC analysis

GloTEC is NOAA's GPS TEC assimilation product at 10-minute cadence.
Download the daily tar.gz first:

1. Browse to https://www.ngdc.noaa.gov/stp/iono/ustec/
2. Search for your event date, download `glotec_YYYY_MM_DD.tar.gz`
3. `tar xzf glotec_YYYY_MM_DD.tar.gz`
4. Run:

```bash
python3 fetch_glotec.py \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --output-dir ./evaluation
```

Outputs: event montage, before/after comparison, diff map, product list.

The most useful product is `anomcus` (CONUS TEC anomaly — difference
from 30-day median). Orange = positive anomaly, purple = negative.
A TID wavefront appears as diagonal stripes, but at ~2° resolution
large LSTIDs may not be resolvable if a storm-time enhancement is present.

### What each source verifies

| Source | Verifies | Does NOT verify |
|--------|----------|-----------------|
| Kp index | Geomagnetic context, storm timing | Speed, direction |
| AE index | Substorm onset timing | Speed, direction |
| GloTEC | Storm-time TEC context | TID speed/direction at std res |
| Peak succession | Propagation direction | Speed magnitude |
| GPS TEC (IONEX) | Wavefront speed + direction | Needs NASA Earthdata auth |

### Manual evaluation sources (browser only)

- **SuperMAG SME**: https://supermag.jhuapl.edu/indices/
  Select SME index, look for spike 3-4h before event window

- **SuperDARN RTI**: http://vt.superdarn.org
  Use Fort Hays East (FHE) or Blackstone (BKS) for mid-latitude US
  Look for ground scatter boundary moving equatorward

- **GIRO ionosondes**: https://giro.uml.edu/ionoweb/
  Note: US NEXION stations not available after 2023

### Speed verification (requires NASA Earthdata account)

Register free at https://urs.earthdata.nasa.gov/ then:

```bash
# Download IONEX file for event date
echo "machine urs.earthdata.nasa.gov login USER password PASS" >> ~/.netrc
chmod 600 ~/.netrc
curl -n -L -O \
  "https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/jplg0190.26i.gz"
gunzip jplg0190.26i.gz
# Parse IONEX for TEC at station locations (2-hour cadence, 2.5°×5° grid)
```



---


## How do I verify my DOA result is physically real?

Two independent checks are available — one for direction, one for speed.
They use completely different data sources from the HF Doppler recordings.

---

### Step 1: Verify direction — peak succession check (no external data)

The strongest direction check requires no external data. For a wave
propagating from azimuth θ, the station closest to the source should
show its Doppler peak first — most negative lag relative to all others.

**How to read the tid_doa.py lag table:**

```
Pairwise time lags (positive = second station lags first):
   AA6BD -> N6RFM    lag= +1253 s   corr=+0.847
   AA6BD -> W7LUX    lag= +1481 s   corr=+0.812
   N6RFM -> W7LUX    lag=  +228 s   corr=+0.761
```

**Check (wave from 30° NNE — easternmost station should lead):**
1. AA6BD (easternmost) has positive lag vs all others ✓
2. Lag magnitudes consistent with inter-station distances ✓
3. Triangle closure checked by diagnostic [4] in tid_doa.py ✓

This check is **definitive for direction** — no GPS, no ionosonde needed.
If any lag sign disagrees with the predicted direction, suspect a 180°
alias or wrong-peak lock in that pair.

---

### Step 2: Verify speed — Madrigal GPS TEC cross-correlation

`fetch_madrigal_tec.py` retrieves gridded GPS TEC from MIT Haystack
and cross-correlates station pairs independently of the HF Doppler data.

```bash
python3 fetch_madrigal_tec.py \\
    --date YYYY-MM-DD \\
    --event-start YYYY-MM-DDTHH:MM:SSZ \\
    --event-end   YYYY-MM-DDTHH:MM:SSZ \\
    --stations N6RFM,-97.21,32.94 AA6BD,-85.13,35.06 W7LUX,-111.71,35.10 \\
    --user-name "Your Name" --user-email your@email.com \\
    --user-affiliation "Your Institution" \\
    --doa-lags AA6BD,N6RFM,1253 AA6BD,W7LUX,1481 N6RFM,W7LUX,228 \\
    --doa-speed 239 --doa-azimuth-from 30 \\
    --output-dir ./evaluation
```

**Critical caveat — geometry matters:**
GPS TEC xcorr gives the along-baseline lag, not the true phase lag.
Best results when baseline bearing is within ~45° of the wave direction.

```
along-baseline speed = true speed / cos(angle between wave and baseline)
```

---

### Quick reference

| What to verify | Tool | Data needed |
|----------------|------|-------------|
| Direction | Peak succession (tid_doa.py output) | None — internal |
| Speed | fetch_madrigal_tec.py xcorr | Madrigal GPS TEC (free) |
| Geomagnetic context | evaluate_external.py | Kp (GFZ), AE (Kyoto) |
| Storm-time TEC | fetch_glotec.py | NOAA GloTEC (~270 MB) |

See `docs/EXTERNAL_RESULTS_EVALUATION.md` for full methodology and
`examples/EXTERNAL_RESULTS_EVALUATION.md` for the Jan 2026 worked example.

### How do I use Madrigal GPS TEC to corroborate a DOA result?

The `fetch_madrigal_tec.py` tool retrieves gridded GPS TEC from MIT
Haystack, extracts TEC at station locations, detrends to remove the
storm background, and cross-correlates all station pairs to independently
estimate TID phase lags.

No account needed — Madrigal uses open access (just provide name/email):

```bash
python3 fetch_madrigal_tec.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --stations N6RFM,-97.21,32.94 AA6BD,-85.13,35.06 \
               W7LUX,-111.71,35.10 AC0G_ND,-96.83,46.88 \
    --user-name "Your Name" \
    --user-email your@email.com \
    --user-affiliation "Your Institution" \
    --doa-lags AA6BD,N6RFM,1253 AA6BD,W7LUX,1481 N6RFM,W7LUX,228 \
    --doa-speed 239 --doa-azimuth-from 30 \
    --output-dir ./evaluation
```

**Outputs:** `madrigal_tec_raw.png`, `madrigal_tec_detrended.png`,
`madrigal_tec_xcorr.png`, `madrigal_tec_report.txt`

**Data availability:** GPS TEC is typically ingested into Madrigal
within 2-4 weeks of the event. Check availability with:

```python
import madrigalWeb.madrigalWeb as mad
m = mad.MadrigalData("https://cedar.openmadrigal.org/")
exps = m.getExperiments(8000, YYYY, MM, DD, 0,0,0, YYYY, MM, DD, 23,59,59)
print(f"Found {len(exps)} experiments")
```

See `docs/EXTERNAL_RESULTS_EVALUATION.md` for full tool reference
and `examples/EXTERNAL_RESULTS_EVALUATION.md` for the Jan 2026 results.

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
| `tid_doa.py` one lag at the edge of max_lag_s | Pair too noisy or wrong cycle | Reduce `max_lag_seconds` or `--drop` that station |
| `tid_map.py` says "install cartopy" | Optional dep missing | `pip install cartopy` for nicer maps |


## Recipe: drop a station from DOA

When running `tid_doa.py` directly, use `--drop` to exclude a station
by name. When using `tid_workflow.py`, the interactive drop-station
loop activates automatically after the DOA result.

```bash
# Drop one station (direct tid_doa.py use)
python3 tid_doa.py event.json --drop W7LUX

# Drop two stations (need at least 3 remaining)
python3 tid_doa.py event.json --drop W7LUX --drop AC0G_ND
```

`--drop` is case-insensitive and repeatable. Prints `Dropped station(s): ...`
to confirm. Warns if the name is not found in the config.

After dropping, check:
- SVR (diagnostic 1) — if > 5 with 3 stations, the array is near-collinear
- Pairwise correlations — all remaining pairs should be > 0.4
- Direction consistency — should agree within ~20° of the full-array result

The Jan 2026 canonical result uses `--drop AC0G_ND`:
```bash
python3 tid_doa.py examples/event_20260119.json --drop AC0G_ND
# Result: 304 m/s from 10° NNE, 0/5 flags
```

---

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
