# Tutorial: a complete TID analysis from start to finish

This tutorial walks through every step of analyzing a Traveling Ionospheric
Disturbance (TID) using the **psws-drf-tid-tools** pipeline, using the
**19 January 2026 LSTID** event as a concrete worked example.

By the end you will have:

- identified the time window of a candidate TID at your own station
  or other chosen reference station by visual inspection of its
  24-hour Doppler spectrogram
- found which other HamSCI stations recorded usable data for the same
  event
- downloaded and verified their raw Digital RF (DRF) I/Q recordings
- extracted Doppler-vs-time CSVs from each recording
- run a two-station cross-correlation as a sanity check
- run the full multi-station direction-of-arrival inversion
- produced publication figures (spectrograms, stacked Doppler,
  geometry map)

The same process applies to any event you want to analyze; just substitute
your event date, your station, and your event window.

---

## The event we will analyze

On **18 January 2026** at 18:09 UTC, the Sun produced a long-duration
X1.9 flare from AR4341. A few hours later, a Large-Scale TID was
observed by four HamSCI Grape DRF stations across the central United States
between roughly 22:30 UTC Jan 18 and 01:45 UTC Jan 19.

We want to determine:

- The direction the TID was propagating (in degrees true)
- The horizontal phase speed (in m/s)
- Whether the result is internally consistent (so we believe it)

The reference operator is **N6RFM/5** at Keller TX (EM12jw, 32.94°N
-97.21°W). You can substitute your own station details throughout.

---

## Before you start

Make sure the toolkit is set up:

```
git clone https://github.com/N6RFM/psws-drf-tid-tools.git
cd psws-drf-tid-tools
pip install -r requirements.txt
pip install -r requirements-optional.txt   # cartopy for nicer maps
```

All scripts respond to `--help` and `--version`. The
[full cookbook](COOKBOOK.md) is a task-oriented reference; the
[troubleshooting guide](TROUBLESHOOTING.md) covers common problems.

We will work in a fresh directory:

```
mkdir tid_event_20260119 && cd tid_event_20260119
# Copy or symlink the scripts in. (We assume they are on your PATH or in
# this folder for the commands below.)
```

---

## Step 1: identify the TID region of interest at your reference station

**Before this step**, you should already have noticed some sign of
an event in your own PSWS spectrogram (or someone else's) — for
example, a Short-Wave Fadeout following a solar flare, a known
geomagnetic storm, an eclipse, or simply slow oscillations in the
WWV carrier track that suggest a TID. The pipeline starts from
that prior observation: you know roughly *when* something
happened, and Step 1 nails down *exactly when* by inspecting
the reference station's full-day spectrogram.

If you have no candidate event in mind yet, run
`drf_spectrogram.py` on a day of your reference station's data
and look for unusual features. Or use `tid_window_detector.py`
to scan a 24-hour CSV for wave-like activity.

Every other step in this pipeline starts from a specific UTC time
window in which you suspect a TID is present at a chosen reference
station. **That window is identified first, by looking at the
reference station's full-day Doppler spectrogram by eye.** Companion-
station selection, data download, Doppler extraction, and DOA
inversion all flow from this choice.

The reference station is usually your own, but it doesn't have to be —
any station with a clean recording across the event window will do.
We use N6RFM/5 throughout this tutorial.

For our event we knew an X1.9 flare had occurred on 18 January and
that LSTID activity often follows such events by a few hours, so we
naturally looked at the post-flare evening of 18 January and into the
UTC morning of 19 January. But the actual analysis window is something
you commit to only after looking at the spectrogram.

### Generate the full-day spectrogram

Assuming your reference station's DRF recording for the event date
is in `./n6rfm/`, render a 24-hour Doppler spectrogram:

```
python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_survey.png \
    --ylim=-2,2 \
    --callsign "N6RFM/5" --grid "EM12jw"
```

Open the resulting PNG and look for **slow, wavy modulation of the
carrier track**. A TID at this scale looks like the carrier wandering
smoothly up and down over tens of minutes to a couple of hours, often
with several visible oscillation cycles. The amplitude is typically a
few tenths of a hertz to a few hertz of Doppler. Random RFI spikes,
sharp single-sample glitches, and the slow diurnal drift of the carrier
are *not* what you are looking for.

For the 19 January 2026 spectrogram, the first ~90 minutes of the UTC
day showed an unmistakable slow oscillation in N6RFM/5's WWV 10 MHz
carrier track:

- A pronounced negative excursion down to about -0.8 Hz around 00:40 UTC
- A return through zero around 01:00 UTC
- A positive peak near +0.6 Hz around 01:13 UTC
- A return to near-zero by ~01:30 UTC

That is approximately one full cycle of an ~80–100 minute wave — a
textbook TID signature. The rest of the day showed unrelated
storm-driven activity beginning in the local afternoon, but the early
morning UTC hours were clean.

### Choosing the window edges

Two practical considerations decide where the window's edges go:

1. **Include enough of the wave to be useful.** At minimum one
   half-cycle (so a clear lead/lag can be measured between stations);
   ideally one full cycle so the cross-correlation has both rising and
   falling content to lock onto. Going beyond one cycle is fine if the
   signal stays clean, but doesn't usually improve the result.
2. **End the window before the carrier degrades.** If your reference
   station's SNR drops sharply (nighttime fade, terminator, storm-
   driven absorption) inside the window, the Doppler tracker becomes
   unreliable and the correlation result is meaningless. Pick the
   cleanest contiguous block you can.

For the 19 January event, those two considerations told us the
analysis window should be approximately **00:00 – 01:15 UTC**. This
covers most of one full cycle of the wave at the reference station.
The 01:15 end was actually constrained by a companion station
(AC0G_ND's signal fades after ~01:18 UTC), but you only discover that
later, in Step 3, when you have downloaded the companion data. Step 1
gives you a candidate window from your reference station alone, which
you then refine if needed.

### Recording the window as numeric times

Once you've decided where the window starts and ends, write down the
two times in **UTC, ISO-8601 format**:

    start: 2026-01-19T00:00:00
    end:   2026-01-19T01:15:00

These two strings are what you pass to every later script. They appear
in three places downstream:

1. The `--start` and `--end` flags of `drf_to_doppler.py` when you
   extract Doppler for each station (Step 4).
2. The `--annotate "HH:MM,HH:MM,label"` flag of `drf_spectrogram.py`
   when you make the annotated spectrogram figure (the HH:MM form is
   abbreviated; it just takes hours and minutes within the displayed
   day).
3. The `event_start_utc` and `event_end_utc` fields in the JSON config
   file consumed by `tid_doa.py` (Step 5–6).

If you're using `tid_doa_config.py` to build the config interactively
(Step 5), the same two timestamps go in the prompt for event start and
end.

#### Reading times off the spectrogram

Spectrogram x-axis labels are in UTC hours. Wave features rarely fall
exactly on an hour-line — that's fine. **Round to whatever boundary is
convenient** (the nearest 5 minutes, 15 minutes, or hour), erring on
the side of including more of the wave rather than less. Cross-
correlation is not sensitive to exact alignment of the window edges;
the wave itself dominates.

For our event the wave was clearly visible from about 00:00 UTC
through about 01:15 UTC, with the carrier becoming choppy slightly
after that as AC0G_ND's signal began to fade. The natural round
choice was 00:00:00 to 01:15:00. We could have used 00:00 to 01:30 and
gotten a similar answer; we could not have used 00:00 to 04:00 because
the carrier degrades after ~01:18.

#### Quick sanity check on your window

Before propagating the window through the rest of the pipeline, run a
single extraction of *just the reference station* with these times
and look at the resulting Doppler-vs-time PNG:

```
python3 drf_to_doppler.py ./n6rfm \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 \
    --output n6rfm.csv --plot n6rfm.png
```

Open `n6rfm.png`. The Doppler trace should show **the wave you saw
in the spectrogram** — same shape, same number of cycles, same rough
amplitude. If the trace looks flat, noisy, or fundamentally different,
your window is wrong (likely too narrow, or includes a fade) and you
should pick a different one before continuing.

This sanity check costs about 5 seconds per station and saves
debugging hours later.

### Annotate the spectrogram to record your choice

Once you have committed to a window, regenerate the spectrogram with
the annotation in place — this is the figure you will use in any
writeup:

```
python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_jan19_annotated.png \
    --ylim=-2,2 \
    --callsign "N6RFM/5" --grid "EM12jw" \
    --annotate "00:00,01:15,4-station DOA window"
```

The cyan-bracketed region in the resulting figure is the "region of
interest" — the time window we will now propagate through every
remaining step.

### A note on automated detection

The toolkit does include an automated TID-window detector
(`tid_window_detector.py`) that scores 24-hour spectrograms for
wave-like activity. It is useful when you have long stretches of
continuous data and want to catalogue events from a station without
prior knowledge of when they happened.

For event-driven analysis like this one — where you already know
roughly when the disturbance occurred (a known flare, geomagnetic
storm, eclipse, etc.) — visual inspection is faster and more
reliable. The eye is excellent at picking coherent slow modulation
out of a noisy background; the automated detector exists as a
complement, not a replacement.

---

## Step 2: find companion stations

We need at least 3 stations (preferably 4+) with usable data for our
event. The first script polls PSWS Central Control System and reports
candidates ranked by geometric suitability:

```
python3 find_event_stations.py \
    --date 2026-01-19 \
    --my-lat 32.94 --my-lon -97.21 \
    --my-call "N6RFM/5"
```

The first run typically takes 3-10 minutes — the script has to walk all ~279
registered PSWS stations to build a directory. It caches the directory
in `.psws_station_cache.json`, so subsequent runs (refreshed weekly) are
fast.

You will see output like:

```
Stations with DRF I/Q recordings on 2026-01-19:
  Rank Station              Grid   Path  MidSep Brg  Score  Flag/Note
  -----------------------------------------------------------------------
  *    N6RFM/5              EM12kw 1111km    4km  90°   —    (your station)
  1    KC4LE_G1_Node60_DRF  EM63nh 1804km  483km  82°  0.96
  2    AA6BD                EM75kb 1851km  571km  72°  0.93
  3    K4BSE                EM73sj 1992km  595km  81°  0.90
  4    W7LUX                DM45dc  852km  679km 282°  0.82
  5    AC0G_ND              EN16ov  956km  777km 359°  0.72
  ...
```

*Note: the table above is an illustrative example. The actual rows,
rank ordering, path lengths, and bearings depend on PSWS's current
station metadata (which is updated continuously) and on the exact
scoring parameters used. The example shows the **format** you should
expect, not the **specific numbers** for any future query.*

The score combines path length (700–1400 km is ideal for clean
single-hop F-region work) with midpoint coverage relative to your
station. Look for **azimuthal spread** — ideally three stations
whose WWV-path midpoints sit roughly to the N, E, S, or W of your
own midpoint, so the array covers three cardinal directions besides
yours.

### A dead end worth knowing about

If you run `find_event_stations.py` against the raw PSWS observation
list with a `centerFrequency=10.000` filter, you will miss every
multi-subchannel WSPRdaemon station, because those report their
frequency as `"10.000 MHz, 5.000 MHz, ..."` (a comma-separated list)
which never matches the exact-string filter.

The script works around this by querying each station individually and
filtering client-side. If you have your own scripts that talk to PSWS,
expect this gotcha and handle it the same way.

### Picking our four

For this tutorial we chose:

- **N6RFM/5** (reference station, Keller TX) — single-channel Grape
- **AA6BD** (Tennessee/Georgia border) — single-channel
- **W7LUX** (northern Arizona) — single-channel
- **AC0G/ND** (northern North Dakota) — *multi-subchannel WSPRdaemon*

Coverage is roughly N, S, E, W around the array centroid in Kansas.

---

## Step 3: download and inspect the DRF data

For each chosen station, download the DRF tarball from PSWS. The
script's output includes direct download links. Extract each into a
folder named after the station, so your directory looks like:

```
tid_event_20260119/
├── n6rfm/
├── aa6bd/
├── w7lux/
└── ac0g_nd/
```

Now verify each station's metadata and (crucially) **identify the
correct subchannel index for 10 MHz**:

```
python3 drf_inspect.py --all . --frequency 10
```

The output for each station reports the recording bounds, callsign,
grid square, and a subchannel-to-frequency mapping. For single-channel
Grape stations, the answer is always `--subchannel 0`. For
multi-subchannel stations, it isn't.

Sample output for ac0g_nd:

```
=== ./ac0g_nd ===
  Sample rate:           10.000 samples/sec  (complex)
  Subchannels:           9
  Recording start:       2026-01-19 00:00:00 UTC
  Recording end:         2026-01-19 23:59:59 UTC

  Subchannels and their center frequencies:
    Index  Freq (MHz)   WWV?   Target?
    0      2.500        WWV
    1      3.330
    2      5.000        WWV
    3      7.850
    4      10.000       WWV    *** YES ***
    5      14.670
    ...
  >>> For 10.0 MHz, USE: --subchannel 4
```

This is also the right moment to **render a quick spectrogram of each
companion station** and confirm that the wave you identified in Step 1
at your own station is also visible (or at least plausibly present)
in their data, and that their SNR is good through your candidate
window. If one station has a fade across part of your window, you
either truncate the window or drop that station.

### Why this step matters

The mapping from subchannel index to frequency **varies between
stations**. N5TNL starts at 2.5 MHz (10 MHz is index 4). KD7EFG starts
at 60 kHz WWVB (10 MHz is index 5). If you guess wrong, you get a noisy
trace that looks like a weak signal — a subtle failure mode that wastes
hours of analysis time if you don't catch it.

`drf_inspect.py` also runs a signal-level check on each subchannel,
reporting whether each looks ACTIVE or EMPTY based on RMS magnitude.
This is a useful sanity check that the station was actually receiving
on the frequency you expect.

---

## Step 4: extract Doppler-vs-time CSVs

Now reduce each station's raw I/Q to a Doppler time series. For the
analysis window 00:00–01:15 UTC on 19 January (the early, clean part
of the event before AC0G_ND's signal fades):

```
# Single-channel stations
python3 drf_to_doppler.py ./n6rfm \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 \
    --output n6rfm.csv --plot n6rfm.png

python3 drf_to_doppler.py ./aa6bd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 \
    --output aa6bd.csv --plot aa6bd.png

python3 drf_to_doppler.py ./w7lux \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 0 \
    --output w7lux.csv --plot w7lux.png

# Multi-subchannel station — note --subchannel 4 from step 3
python3 drf_to_doppler.py ./ac0g_nd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 4 \
    --output ac0g_nd.csv --plot ac0g_nd.png
```

Each command takes a few seconds to a minute depending on disk speed.
You should now have four CSVs and four quick-look PNGs in the working
directory.

### Sanity-check each plot

Open each `*.png` and confirm:

- **SNR is mostly above 30 dB** for the analysis window. Sub-20 dB
  sections are unreliable.
- **Doppler values fall within ±2 Hz**. Excursions to ±5 Hz are search-
  band edge artifacts.
- **No sustained vertical spikes** (brief one-sample spikes are RFI
  and don't matter; sustained drift means the carrier is unstable).
- **For multi-subchannel data**: if the trace looks like square-wave
  noise jumping between ±5 Hz, you picked the wrong subchannel. Re-run
  `drf_inspect.py` and try the right one.

For our event, all four traces showed clean ~80-minute wave structure
with SNR mostly above 40 dB. AC0G_ND's SNR begins to fade after about
01:18 UTC, which is why we deliberately ended the window at 01:15.

---


### Step 4b: visual method validation with overlay spectrogram

The default extraction method is FFT. For most clean signals this is
the right choice. However, if a station path has E-region contamination
(a flat bright band near 0 Hz on the spectrogram alongside the TID
wave), the autocorr method may track the F-region TID carrier more
cleanly.

Extract both methods and overlay them on the spectrogram:

```bash
python3 drf_to_doppler.py ./ac0g_nd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 4 --method fft \
    --output ac0g_nd_fft.csv

python3 drf_to_doppler.py ./ac0g_nd \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00 \
    --decim-seconds 10 --subchannel 4 --method autocorr \
    --output ac0g_nd_autocorr.csv

python3 drf_spectrogram.py ./ac0g_nd \
    --output ac0g_nd_overlay.png --subchannel 4 \
    --start 00:00 --end 01:15 \
    --annotate "00:00,01:15,Analysis window" \
    --overlay "ac0g_nd_fft.csv:FFT" \
    --overlay "ac0g_nd_autocorr.csv:Autocorr:#FF9800"
```

The legend shows inter-method r and RMS diff. Decision guide:

- r > 0.95 and RMS < 0.10 Hz: both equivalent, use FFT (default)
- autocorr visually tracks TID better and lag < 0.3 * period: use autocorr
- otherwise: use FFT (safer for ambiguous lag/period ratios)

Full guidance with worked examples is in docs/METHODOLOGY.md Step 1b.
Record your choice as a "method" field per station in event.json
(see Step 6). If you use analyze_event.sh this step runs automatically.

---

## Step 5: cross-correlate one pair as a sanity check

Before running the full multi-station inversion, it is worth doing a
quick two-station cross-correlation to verify the wave is real and
coherent. This is the simplest possible TID analysis:

```
python3 tid_pair.py n6rfm.csv aa6bd.csv \
    --lat1 32.94 --lon1 -97.21 --name1 N6RFM \
    --lat2 35.06 --lon2 -85.13 --name2 AA6BD \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00
```

The rows in the output table (`Full (no filter)`, `30–60 min`,
`40–90 min`, ...) are **wave-period bandpass filters**, not
time-of-day windows. Each row filters both Doppler traces to the
stated period range and then cross-correlates. A genuine wave shows a
consistent lag across the bands that span its period; wildly varying
lag or sign flips across bands indicate noise or multiple
superimposed waves.

To analyse a **different pair**, you must change *three* things
together: the two CSV filenames, **and** the matching
`--lat/--lon/--name` flags for each station. Changing only the names
or coordinates while reusing the same two CSVs will re-analyse the
same data with relabelled output. For example, N6RFM vs W7LUX:

```
python3 tid_pair.py n6rfm.csv w7lux.csv \
    --lat1 32.94 --lon1 -97.21 --name1 N6RFM \
    --lat2 35.10 --lon2 -111.71 --name2 W7LUX \
    --start 2026-01-19T00:00:00 --end 2026-01-19T01:15:00
```

If in doubt about which files are actually being read, add `--debug`:
it prints the resolved CSV paths, row counts, and time spans so you
can confirm the two inputs really are different.

The output shows the cross-correlation lag, correlation peak, and
apparent along-baseline phase speed across multiple filter bands:

```
Pair N6RFM/AA6BD (baseline 1146 km, bearing N6RFM->AA6BD: 77°)
  Band              Lag(s)    Lag(min)  Corr     Apparent speed
  --------------------------------------------------------------
  Raw                -940      -15.7    0.58      1219 m/s
  15-60 min          -870      -14.5    0.61      1317 m/s
  30-90 min          -940      -15.7    0.59      1219 m/s
  40-120 min        -1030      -17.2    0.55      1113 m/s
```

What to look for:

- **Consistent lag across bands** (within ~10%). If raw says -940 s
  and 30-90 min says +1100 s, something is wrong (probably the
  bandpass-secondary-peak trap, see "Dead ends" sidebar below).
- **Correlation > 0.5**. Below 0.4 the wave is too weak or the
  stations are seeing different things.
- **Negative lag**: AA6BD's signal arrives 15.7 minutes *before*
  N6RFM's. The wave is moving from AA6BD toward N6RFM (NE to SW),
  consistent with what the spectrograms show.

The apparent speed (1219 m/s) is the wave's velocity *component
along the baseline*. If the wave is moving exactly along the baseline,
apparent speed equals the true speed; if it's oblique, apparent speed
overstates the true speed (apparent = true / cos(theta), where theta
is the angle between the wave direction and the baseline). We need
3+ stations to get the true vector velocity rather than a single
along-baseline component.

---

## Step 6: multi-station direction-of-arrival

Build the DOA config interactively (the script auto-discovers stations
and pulls their coordinates from the DRF metadata):

```
python3 tid_doa_config.py --output event.json --scan .
```

You will be prompted to confirm each station and the event window.
Accept the suggested defaults; the resulting `event.json` looks like:

```
{
  "event_start_utc": "2026-01-19T00:00:00Z",
  "event_end_utc":   "2026-01-19T01:15:00Z",
  "resample_seconds": 10,
  "use_bandpass": false,
  "min_expected_speed_m_s": 100,
  "stations": [
    {"name": "N6RFM",   "file": "n6rfm.csv",   "method": "fft", "lat": 32.94, "lon":  -97.21},
    {"name": "AA6BD",   "file": "aa6bd.csv",   "method": "fft", "lat": 35.06, "lon":  -85.13},
    {"name": "W7LUX",   "file": "w7lux.csv",   "method": "fft", "lat": 35.10, "lon": -111.71},
    {"name": "AC0G_ND", "file": "ac0g_nd.csv", "method": "fft", "lat": 46.88, "lon":  -96.83}
  ]
}
```

Now run the inversion:

```
python3 tid_doa.py event.json
```

You should see:

```
Auto max_lag_seconds = 12069 s (largest baseline 1207 km / 100 m/s minimum expected speed).
Bandpass disabled (default). Raw mean-subtracted signals will be cross-correlated.
Loaded 4 stations, window 2026-01-19 00:00:00 to 2026-01-19 01:15:00, dt=10s
  N6RFM        mid=(36.87,-100.93) N=449
  AA6BD        mid=(38.29,-94.70) N=449
  W7LUX        mid=(37.94,-108.50) N=449
  AC0G_ND      mid=(43.85,-101.15) N=451

Pairwise time lags (positive = second station lags first):
       N6RFM -> AA6BD      lag= -940.0 s  corr=+0.577
       N6RFM -> W7LUX      lag=  -70.0 s  corr=+0.564
       N6RFM -> AC0G_ND    lag=-1340.0 s  corr=+0.698
       AA6BD -> W7LUX      lag=+1280.0 s  corr=+0.688
       AA6BD -> AC0G_ND    lag=   +0.0 s  corr=+0.771
       W7LUX -> AC0G_ND    lag= -980.0 s  corr=+0.737

=== TID Direction-of-Arrival Result ===
  Phase speed:             666.1 m/s (2398 km/h)
  Wave heading toward:    214.9° (true bearing)
  Wave coming from:        34.9° (true bearing)
  -> Consistent with large-scale TID (LSTID).
```

**That is the answer**: the wave propagated SW at 666 m/s, coming from
the NE. Classification: LSTID (consistent with the 300–1000 m/s LSTID
range).

### Quality-checking the result

Look at the pairwise lag matrix:

- All six pairs show physically sensible lags (no edges at the
  ±max_lag_seconds boundary).
- Correlations are 0.56–0.77 — moderate but consistent.
- Triangle closure: the three independent triangles agree to within
  ~7 minutes on lag sums. Good.

If any of these fail, see the [troubleshooting guide](TROUBLESHOOTING.md).

### Dead end worth knowing about

An earlier version of this analysis applied a 40–90 minute bandpass
filter before cross-correlation. The result was nonsense: AA6BD
appeared to *lag* N6RFM by 2.7 minutes (instead of leading by 15.7),
with a deceptively high correlation of 0.93. The DOA solution claimed
the wave was moving at 1221 m/s heading 165° (south).

The problem: bandpassing produces a nearly-sinusoidal signal whose
autocorrelation has high-correlation lobes spaced one wave period
apart. The lag-finder grabbed a secondary lobe rather than the true
peak. Removing the bandpass (and just using mean-subtracted raw
Doppler) recovered the correct answer.

**Lesson**: bandpass filtering before cross-correlation is *bad* for
slow TID signals. The `tid_doa.py` default `use_bandpass: false` is
correct for almost every event.

---

## Step 7: make the publication figures

Four figures tell the complete story.

### Figure 1: the flare SWF

A spectrogram of the flare evening showing the short-wave fadeout:

```
# Run from the Jan 18 DRF folder, not the Jan 19 one
python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_jan18_annotated.png \
    --start "16:00" --end "23:59" \
    --ylim=-2,4 \
    --callsign "N6RFM/5" --grid "EM12jw" \
    --annotate "17:45,18:30,X1.9 flare SWF (carrier fadeout)"
```

The carrier track vanishes during the cyan-bracketed window, exactly
as expected from a major flare's prompt D-layer absorption.

### Figure 2: the TID window

You already made this in Step 1; it doubles as a publication figure:

```
python3 drf_spectrogram.py ./n6rfm \
    --output n6rfm_jan19_annotated.png \
    --ylim=-2,2 \
    --callsign "N6RFM/5" --grid "EM12jw" \
    --annotate "00:00,01:15,4-station DOA window"
```

Note: `--ylim=-2,2` uses the `=` syntax because the value starts with
a minus sign (argparse otherwise treats it as a flag).

### Figure 3: stacked four-station comparison

```
python3 tid_stack_plot.py \
    --config event.json \
    --output stack.png \
    --ylim=-2,2 \
    --title "Doppler vs UTC at four HamSCI Grape DRF stations, 19 Jan 2026"
```

The four panels show successive peak times: AC0G_ND first (00:50:40),
then AA6BD (00:57:38), then W7LUX (01:05:07), then N6RFM (01:13:14).
The wave's NE-to-SW motion is visible without any math.

### Figure 4: array geometry map

```
python3 tid_map.py \
    --config event.json \
    --output map.png \
    --azimuth-toward 215 \
    --speed 666
```

The wave arrow points SW, the WWV-path midpoints cluster in the central
US, and the geometric relationships are immediately visible.

---

## Summary of what we just did

1. Identified the TID region of interest at the reference station by
   visually inspecting its 24-hour Doppler spectrogram (00:00–01:15
   UTC on 19 January).
2. Found 4 well-distributed companion stations on the event date.
3. Verified each DRF, confirming the right subchannel for multi-
   subchannel data.
4. Extracted four Doppler CSVs over the chosen window.
5. Sanity-checked one pair with cross-correlation: AA6BD leads N6RFM
   by 15.7 min, consistent direction.
6. Ran full 4-station DOA: 666 m/s SW at azimuth 215°, classified as
   LSTID.
7. Produced four publication-quality figures.

Total elapsed time, after the first cache build: about 20 minutes of
shell commands plus a few minutes of human judgement looking at the
spectrogram.

## What to do for your own events

The pattern is the same:

1. Render your reference station's 24-hour spectrogram and pick a
   candidate TID window by eye.
2. Find 3+ companion stations from `find_event_stations.py` output,
   prioritizing azimuthal coverage.
3. Verify each DRF with `drf_inspect.py`; render their spectrograms
   and confirm the wave is plausibly visible at each.
4. Extract Doppler at 10-second cadence over your chosen window.
5. Run `tid_doa.py`.

For situations where you have your reference station's Doppler but
don't yet know *when* a TID was active — for instance scanning long
archives for events to catalogue — run `tid_window_detector.py`
on a 24-hour survey to find candidate windows automatically.

For everyday reference once you know the pipeline, see the
[full cookbook](COOKBOOK.md).
