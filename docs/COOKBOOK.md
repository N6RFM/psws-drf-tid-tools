# Cookbook

Task-oriented recipes for everyday use of **psws-drf-tid-tools**.
For a full narrative walkthrough of a complete analysis, see the
[workflow tutorial](../WORKFLOW_TUTORIAL.md). For when something goes wrong, see the
[troubleshooting guide](TROUBLESHOOTING.md).

Every script accepts `--help` and `--version`.

---

## Using the browser dashboard (`tid_dashboard.py`)

Everything below this section is the CLI-first path. `tid_dashboard.py`
wraps most of it behind one browser page instead — same underlying
scripts, same math, just clickable. This section covers dashboard-
specific recipes; for troubleshooting an individual step it launches
(extraction methods, DOA diagnostics, Madrigal cross-check), the
regular CLI recipes below still apply, since that's exactly what's
running underneath.

### How do I launch the dashboard?

```bash
pip install streamlit
streamlit run tid_dashboard.py
```

Open the printed `http://localhost:8501` URL. Point it at an event
directory (a folder containing DRF station subdirectories, same
convention as `tid_workflow.py --event-dir`); station coordinates,
channel confirmation, and the event-window spectrogram all appear live
as you type — nothing runs until you click "Run full pipeline."

### Does the dashboard remember my progress if I come back later?

Yes — it reads and writes the exact same `tid_workflow_state.json`
file `tid_workflow.py --resume` uses, so a session started in one is
fully resumable from the other. Entering an event directory with
existing saved progress shows a summary of what's already done per
station, with the choice to continue or start completely fresh
(clearing the file, same as `tid_workflow.py`'s own equivalent
choice, except your station exclusions are kept either way — more on
that below — and it also deletes every intermediate/derived file in
the event directory, not just the state file: spectrograms,
extraction CSVs, config files, run logs. Only the DRF station
directories themselves are left untouched, identified the same way
real station discovery works elsewhere, not a separate heuristic.
Exactly what will be deleted is shown before the button appears,
since this is a real, irreversible filesystem operation — added
after leftover stale files from a previous attempt kept getting
picked back up even once the state file itself was cleared).
Channel-num confirmation, the event window, which
station is the keystone, and extraction itself all persist this way:
returning to an event shows what you already confirmed instead of
asking again, the window slider defaults to your last selection
instead of the full recorded range, and a station already extracted
is reused rather than re-run — the real time-saver, since extraction
is the slow step. The keystone station is also processed first
through every step, the whole reason for picking one -- and for
interactive methods specifically, a "Clicking order" control lets you
pick directly which station's window opens first, rather than
depending on keystone selection to influence it indirectly. One more thing
worth knowing: the event window actually sent to `tid_doa.py` is the
real overlap of what was extracted for each station, not simply the
slider selection — which only guides where extraction happens —
matching `tid_workflow.py`'s own approach.

### How do I exclude a station from a run without losing its progress?

A multiselect right after the saved-progress summary lists every DRF
station directory found in the event folder — uncheck any to exclude
it from this run. Unlike [dropping a station to re-run just the DOA
fit](#how-do-i-drop-a-station-and-re-run-in-the-dashboard) (a
later-stage, DOA-only tool for isolating a bad result after
extraction), this is an earlier-stage choice that skips a station
through the *entire* pipeline, extraction included. Either way,
excluding a station never touches its own saved progress — bringing
it back later (check the box again) doesn't mean re-confirming its
channel-num or anything else about it.

### How do I pick an extraction method in the dashboard?

One dropdown in the sidebar, five methods: `autocorr`, `cwt`, `fft`
run automatically with no further input. `wave-fit` and `cwt-prophet`
open `tid_spect_click.py`'s native window per station — same tool, same
key bindings as the [wave-fit CLI recipe](#how-do-i-use-wave-fit-extraction---wave-only)
below (click, `F` to fit, `X` to export, close the window). The
dashboard waits for each window to close, then moves to the next
station automatically. All stations in one run use the same method —
mixing methods isn't supported yet, so for a mixed-method event (e.g.
Jan 2026's cwt-prophet + autocorr mix) use the CLI tools directly
instead.

### How do I skip the Madrigal cross-check in the dashboard?

Uncheck "Perform Madrigal TEC cross-check" in the sidebar before
running — the Madrigal fields disappear, nothing is required, and the
pipeline stops cleanly right after the DOA result instead of attempting
the network step.

### How do I drop a station and re-run in the dashboard?

For any event with more than 3 stations, an "Investigate further: drop
station(s) and re-run" section appears below the main results — pick
station(s) to exclude from the multiselect and click re-run. This is
the same `--drop NAME` mechanism as the CLI recipe below, just without
retyping the command; it reuses the already-extracted CSVs rather than
re-running extraction, and can optionally re-run the Madrigal
cross-check with the reduced station list too.

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

## Downloading companion station data

Once you have a shortlist of station nicknames from
`find_event_stations.py`, you need their raw DRF data on disk,
organized as `<station>/ch0/...` (the layout `drf_inspect.py`,
`drf_to_doppler.py`, and `tid_workflow.py` all expect).

### Why does this step use a different PSWS access method than station discovery?

`find_event_stations.py` and `download_companions.py` talk to PSWS in
two different ways, and that's intentional rather than an
inconsistency worth "fixing":

- **`find_event_stations.py` scrapes the HTML observation-list and
  station-directory pages** (`requests` + `BeautifulSoup`), because
  its job is *discovery* — scanning potentially dozens of stations
  across many pages of history to figure out which ones have relevant
  data and how good their geometry is. The HTML table rows expose the
  metadata this needs for free: filename (for DRF-vs-CSV
  classification), the raw center-frequency text (for the
  "contains"-match workaround), and instrument-name strings.
- **`download_companions.py` calls the documented `downloadapi`
  endpoint** (`station_id` + date range → zip), because by this point
  you already know exactly which stations and which date you want —
  there's nothing left to discover, just data to fetch.

Using `downloadapi` for discovery too would mean downloading a full
zip (often ~3 GB for multi-channel-num rx888/WSPRDaemon stations) for
every candidate just to check whether it's worth recommending — a bad
trade against scraping a metadata-only HTML row, and one that would
burn through the shared 100-requests/day rate limit before
`download_companions.py` even gets to the stations you actually
selected. `downloadapi` also doesn't expose the raw metadata fields
(filename pattern, center-frequency text, instrument name) that
`find_event_stations.py`'s classification and scoring logic depends
on — you'd only get those by opening the downloaded file.

One consequence: the two scripts use different PSWS ID namespaces.
`find_event_stations.py` resolves nicknames via the numeric
observation-form dropdown value (e.g. `95`), cached in
`.psws_station_cache.json`. `download_companions.py` needs the
separate public `S000095`-style ID `downloadapi` expects, cached
separately in `.psws_station_id_cache.json`. They're not
interchangeable — this is why `download_companions.py` maintains its
own cache rather than reusing `find_event_stations.py`'s.

### How do I download companion stations automatically?

```bash
python3 download_companions.py --date 2026-01-19 \
    --stations AA6BD W7LUX AC0G_ND
```

Or read the list from a file (one nickname per line — paste straight
from `find_event_stations.py`'s "Station" column; `#` comments and
blank lines are ignored):

```bash
python3 download_companions.py --date 2026-01-19 \
    --stations-file companions.txt
```

This resolves each nickname to a public PSWS Station ID, calls the
PSWS download API, extracts the result, and moves it into
`<station>/ch0/...`. It writes `download_manifest.json` recording what
was pulled, from where, and when.

**Multi-word nicknames** (some PSWS stations register with names like
`"KE9SA Grape DRF S48"`) need quoting on the command line:

```bash
--stations "KE9SA Grape DRF S48"
```

`--stations-file` handles these correctly without quoting since each
line is read whole.

### How do I download a multi-day span?

```bash
python3 download_companions.py --start-date 2026-01-18 \
    --end-date 2026-01-20 --stations AA6BD
```

### How do I preview what will be downloaded without using a request?

```bash
python3 download_companions.py --date 2026-01-19 \
    --stations AA6BD W7LUX --dry-run
```

Resolves and prints station IDs only; makes no calls to the download
API.

### Should I pass `--frequency` to filter the download?

**Be careful with this for mixed companion lists.** The PSWS API's
`frequency` parameter does an exact-string match against the
observation's center-frequency field. Single-channel Grape v1.x
stations store one value there (e.g. `"10.000"`) and match fine.
Multi-channel-num rx888/WSPRDaemon stations store a comma-separated
list (e.g. `"10.000 MHz, 5.000 MHz, ..."`), which a bare `10` will
**not** match — the API silently reports "no matching observations"
for a station that actually has your target frequency.

Since you usually can't tell which companions are multi-channel-num
ahead of time, the safest default is to **omit `--frequency` from the
download step entirely** and let `drf_inspect.py --frequency 10`
identify the right `--channel-num` per station afterward. Omitting it
just means multi-channel-num stations download their full file (often
~3 GB instead of ~30-50 MB) rather than being silently dropped.

### Why did I get folders like `<station>_20260126` I didn't ask for?

The PSWS download API's date-range matching isn't perfectly
consistent across station/instrument types — some stations return
exactly the day requested, others can return an adjacent day too. By
default `download_companions.py` discards any day outside your
requested `--date`/`--start-date`..`--end-date` range automatically, so
this shouldn't normally happen. If you explicitly want every day the
API returns (e.g. for a multi-day survey), pass `--keep-extra-days`;
each extra day is then saved as its own folder named by its actual
recording date (`<station>_<YYYYMMDD>`) rather than an ambiguous
numeric suffix.

### How do I avoid re-downloading a station I already have?

By default an existing `<station>/` folder is left alone and skipped
(with a message). Use `--overwrite` to replace it.

### How do I download manually instead, from the PSWS web UI?

See `MANUAL_TUTORIAL.md` for the full manual download walkthrough.
Briefly: filter https://pswsnetwork.eng.ua.edu/observations/observation_list/
by station nickname and UTC date, click the `OBS<date>T<time>` link to
zip and download, then unzip and rename the result to `<station>/`
(lowercase, matching the callsign) so it matches what the rest of the
pipeline expects.

---

## DRF inspection

### How do I check which channel-num is 10 MHz on a multi-channel-num station?

```bash
python3 drf_inspect.py ./station_dir --frequency 10
```

Look for the row marked `*** YES ***` in the channel-num table.

### How do I batch-inspect every station in a folder?

```bash
python3 drf_inspect.py --all . --frequency 10
```

Run this after `download_companions.py` (or a manual download) to get
a ready-to-use `--channel-num N` for every station folder in one pass —
single-channel Grapes are always `0`, but rx888/WSPRDaemon stations
vary per station (e.g. one station's 10 MHz channel-num might be index
4, another's index 5).

### How do I just read the metadata without identifying a frequency?

```bash
python3 drf_inspect.py ./station_dir
```

(Same command, without `--frequency`.)

### How do I tell which channel-nums are actually active vs empty?

`drf_inspect.py` automatically prints a signal-level table at the end
of its output. EMPTY-flagged channel-nums have RMS magnitude more than
10x below the median.

---

## Doppler extraction

### How do I extract a clean Doppler-vs-time CSV?

```bash
python3 drf_to_doppler.py ./station_dir \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --channel-num 0 \
    --output station.csv --plot station.png
```

### What cadence should I use?

| Cadence | Use case |
|---|---|
| `--decim-seconds 60` | 24-hour surveys (low resolution, small files) |
| `--decim-seconds 10` | TID analysis (default, good resolution) |
| `--decim-seconds 1`  | Prompt flare signatures (SFD/SWF), high time res |

### What's the difference between "channel" and "channel-num"?

Easy to conflate, and worth being explicit about since it comes up
constantly with multi-frequency receivers.

**"Channel"** means a real DRF subdirectory -- `ch0`, `ch1`, etc.
Every station this project has ever worked with only has one, always
named `ch0`, regardless of how many frequencies it records. A second,
sibling folder for a "second channel" essentially never comes up here.

**"Channel-num"** means a column index *inside* `ch0`'s own data
files -- not a folder at all. Some receivers (rx888/WSPRDaemon/
KA9Q-radio-style) record several independent, unrelated WWV
frequencies into that single `ch0` folder as parallel data columns,
purely for storage convenience since they share one common time axis.
A station with 9 of these packed frequencies (e.g. 2.5, 3.33, 5,
7.85, 10, 14.67, 15, 20, 25 MHz) still has exactly one `ch0` folder on
disk -- verify directly:

```bash
python3 -c "
import digital_rf as drf
r = drf.DigitalRFReader('./ac0g_nd')
iq = r.read_vector(r.get_bounds('ch0')[0], 100, 'ch0')
print(iq.shape)   # (100, 9) for a 9-channel-num station, (100,) for single
"
```

`--channel-num 4` doesn't point any tool at a different folder --
it tells every downstream step (spectrogram generation, extraction,
everything) which column to read out of `ch0`'s one, shared file.
This is also why `download_companions.py` only ever needs to fetch
`ch0` once per station regardless of how many channel-nums it has --
every column is already sitting in that one download.

### How do I extract from a multi-channel-num station?

Pass `--channel-num N` where N is what `drf_inspect.py` reported:

```bash
python3 drf_to_doppler.py ./ac0g_nd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --channel-num 4 \
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
    --decim-seconds 10 --channel-num 4 --method autocorr \
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

### How do I use the anchor-guided cwt-prophet extraction?

The anchor-guided cwt-prophet tool is one of several extraction methods,
often useful for stations with E-region contamination. Launch via
`tid_workflow.py` (method 1) or directly:

```bash
python3 tid_spect_click.py \
    --spectrogram station_tid_zoom_clean.png \
    --name STATION \
    --drf-dir ./station \
    --channel-num 0 \
    --corridor-width 0.4 \
    --seg-start 0 --seg-end 2 \
    --event-json event.json
```

On open, cwt-prophet runs automatically (Pass 0). Key bindings:

    Click   Mark carrier point (left to right)
    E       Accept auto-trace and export
    X       Export clicked trace (spline through your clicks)
    Z       Undo last click
    R       Reset clicks
    Q       Quit

**Recommended workflow:** if the auto-trace looks good press E to
accept and export. If not, click the carrier from left to right and
press X to export your trace.
`--event-json` auto-updates the event config on export.

### How do I use wave-fit extraction (--wave-only)?

Use when the TID shows at least 0.5 cycles (1.5 recommended) in the window and you
want to fit a sinusoidal model to the carrier. No Prophet run needed:

```bash
python3 tid_spect_click.py \
    --spectrogram station_tid_zoom_clean.png \
    --name STATION \
    --seg-start 0.0 --seg-end 2.0 \
    --wave-only
```

On open, the tool goes straight to wave-fit mode. Key bindings:

    Click   Mark a point on the TID cycle (brown diamond marker)
    F       Fit sinusoidal model to clicked points
            (dialog asks how many complete cycles your clicks span --
            see below)
    A       Accept candidate fit — writes final {stn}_wave_tid.csv
    X       Same as A (accept) -- works either key
    W       Redo wave-fit (discards candidate, clear markers)
    Q       Quit without saving

**The cycle-count dialog:** after pressing F, a dialog asks how many
complete TID cycles your clicked points span (e.g. 0.5 = half cycle,
1.0 = one full, 1.5 = one and a half). Click **6 or more points**
before pressing F and the dialog auto-seeds itself with a real,
data-driven estimate -- it fits the sine model at a range of
candidate cycle counts directly against your own clicks and suggests
whichever fits best, so you're confirming a number rather than
guessing one from scratch. Below 6 points this estimate isn't
reliable enough to attempt (a 3-parameter sine fit against only 3-5
points is fundamentally underdetermined), so the dialog falls back to
a plain "1.0" default instead -- count cycles yourself by eye in that
case, or add more clicks and redo the fit. Either way, always check
the suggested number against what you can actually see on the
spectrogram before accepting.

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
    --speed-m-s 304 --azimuth-from 10 \
    --output-dir <event_dir>/runs/external_evaluations
```

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
python3 fetch_madrigal_tec.py \
    --date YYYY-MM-DD \
    --event-start YYYY-MM-DDTHH:MM:SSZ \
    --event-end   YYYY-MM-DDTHH:MM:SSZ \
    --stations N6RFM,-100.93,36.87 AA6BD,-94.70,38.29 W7LUX,-108.50,37.94 \
    --user-name "Your Name" \
    --user-email your@email.com \
    --user-affiliation "Your Institution" \
    --doa-lags AA6BD,N6RFM,1253 AA6BD,W7LUX,1481 N6RFM,W7LUX,228 \
    --doa-speed 304 --doa-azimuth-from 10 \
    --output-dir <event_dir>/runs/external_evaluations
```

`--stations` takes NAME,LON,LAT triples for each receiver station.
`--user-*` fields are required by the Madrigal API (free, no approval needed).

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

See `docs/EXTERNAL_EVALUATION.md` for full methodology and
`examples/ADVANCED_EVALUATION.md` for the Jan 2026 worked example.

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
    --doa-speed 304 --doa-azimuth-from 10 \
    --output-dir <event_dir>/runs/external_evaluations
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

See `docs/EXTERNAL_EVALUATION.md` for full tool reference
and `examples/ADVANCED_EVALUATION.md` for the Jan 2026 results.

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

### What does `.psws_station_id_cache.json` do?

The companion cache file used by `download_companions.py`. It maps
station nickname → public PSWS Station ID (e.g. `"S000028"`), which is
a different identifier than the internal numeric ID
`.psws_station_cache.json` uses. Also refreshed weekly; force a refresh
with `--no-cache`.

### How do I compare two DOA results side by side?

`tid_doa.py` already writes a self-contained, timestamped run log to
`<event_dir>/runs/<timestamp>_run.log` on every invocation (CLI or
GUI, since the dashboard's own pipeline calls `tid_doa.py` the same
way). Rather than re-reading old terminal output or opening two log
files by hand, use `tid_doa_compare.py`:

```bash
tid_doa_compare.py run1.log run2.log [run3.log ...]
tid_doa_compare.py --dir /path/to/event/runs          # 2 most recent
tid_doa_compare.py --dir /path/to/event/runs --all     # every run found
```

Shows speed/heading/diagnostics side by side, highlights differences
in yellow, and flags when the two runs used different station sets
(since a speed/heading difference there may just reflect a different
array geometry, not a change in extraction quality). Only ever reads
what `tid_doa.py` already wrote -- recomputes nothing.

### What about generated files? Should I commit them?

No. The `.gitignore` excludes `*.csv`, `*.png` (except in `docs/`),
`*.pdf` (except in `docs/` and `examples/`), `*.h5`, `OBS*`
directories, `download_manifest.json`, and `.downloads/`. Only source
code, example configs, and example data should be committed.

---

## Quick gotchas reference

| Symptom | Cause | Fix |
|---|---|---|
| Doppler trace looks like a square wave | Wrong `--channel-num` | Re-run `drf_inspect.py`; use the right index |
| `--ylim -2,2` rejected by argparse | Negative value treated as flag | Use `--ylim=-2,2` |
| `find_event_stations.py` first run is slow | Building station cache | Wait 3–5 min; subsequent runs fast |
| Multi-channel-num station has no `*** YES ***` | Frequency not recorded | Check `drf_inspect.py` table; pick nearest |
| `tid_doa.py` correlations < 0.4 across all pairs | Wrong analysis window | Look at spectrograms; pick a cleaner window |
| `tid_doa.py` one lag at the edge of max_lag_s | Pair too noisy or wrong cycle | Reduce `max_lag_seconds` or `--drop` that station |
| `tid_map.py` says "install cartopy" | Optional dep missing | `pip install cartopy` for nicer maps |
| `download_companions.py` reports "no matching observations" for a station that has data on the PSWS site | `--frequency` exact-string-matches; multi-channel-num rx888/WSPRDaemon stations store frequency as a list | Omit `--frequency` from the download step; use `drf_inspect.py --frequency` afterward |
| `download_companions.py` returns an unexpected extra day of data | PSWS download API's date matching is inconsistent across station types | Default behavior already discards out-of-range days; pass `--keep-extra-days` only if you want them |
| Multi-word station nickname only partly resolves | Shell splits unquoted `--stations` on spaces | Quote it (`--stations "KE9SA Grape DRF S48"`) or use `--stations-file` |

## Recipe: drop a station from DOA

When running `tid_doa.py` directly, use `--drop` to exclude a station
by name. When using `tid_workflow.py`, the interactive drop-station
loop activates automatically after the DOA result. The browser
dashboard has the same capability built in for events with more than 3
stations -- see [How do I drop a station and re-run in the
dashboard?](#how-do-i-drop-a-station-and-re-run-in-the-dashboard)
above.

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
