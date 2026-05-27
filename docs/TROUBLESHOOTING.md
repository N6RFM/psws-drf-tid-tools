# Troubleshooting

Failure modes you may encounter and how to fix them. The first section
covers things that go wrong at each pipeline stage; the second section
covers the broader "the result looks wrong" problem.

---

## Stage-by-stage failures

### `find_event_stations.py` returns no stations

**Cause 1**: The PSWS cache is stale or corrupt.

```bash
rm .psws_station_cache.json
python3 find_event_stations.py --date YYYY-MM-DD ...
```

**Cause 2**: Your geometry constraints exclude everything. Try widening:

```bash
--min-path-km 200 --max-path-km 5000 --max-mid-dist-km 5000
```

**Cause 3**: No stations actually uploaded data for that date. Check the
PSWS Central Control System directly:
https://pswsnetwork.eng.ua.edu/observations/

**Cause 4**: Network problem reaching PSWS. The script will normally
print a clear error; if not, test connectivity:

```bash
curl -I https://pswsnetwork.eng.ua.edu/
```

### `find_event_stations.py` misses a station I know was on the air

The PSWS observation portal has several known quirks worked around by
the script:

- **Multi-subchannel WSPRdaemon stations** report frequency as
  `"10.000 MHz, 5.000 MHz, ..."` (comma-separated). PSWS exact-string
  filters reject these; the script handles them client-side.
- **Stations with empty frequency metadata** are still valid DRF
  recordings. The script accepts them and you verify the frequency
  with `drf_inspect.py` after download.
- **One operator can have multiple PSWS registrations** (different
  receivers at different locations). The script queries each ID
  individually.

If a station you expect is still missing, run with `--verbose` (if
available) to see which stations were filtered out and why.

### `drf_inspect.py` errors on a DRF directory

**"ERROR: not a directory"**: You passed a file path or a non-existent
path. Check with `ls`.

**"ERROR opening DRF: ..."**: The DRF tarball may not be fully extracted,
or `ch0/` may be missing. Check:

```bash
ls station_dir/
ls station_dir/ch0/
```

You should see `ch0/` containing per-hour subdirectories
(`2026-01-19T00-00-00/`, etc.) and `drf_properties.h5`.

**"metadata not found"**: Some older Grape v1.x DRFs have a
`ch0/metadata/` directory but no actual metadata files, or have
incomplete metadata (no callsign, no grid). The script handles this
gracefully and you supply missing fields manually:

```bash
# When running drf_spectrogram.py:
--callsign "N6RFM/5" --grid "EM12jw"
```

### `drf_inspect.py` shows no `*** YES ***` row

The station does not have a recording at your target frequency. Check
the subchannel-to-frequency table; pick the nearest WWV frequency
(2.5, 5, 10, 15, 20, 25 MHz). For WWVB-recording stations (60 kHz),
this analysis pipeline does not apply.

### `drf_to_doppler.py` produces a noisy or empty trace

**Cause 1**: Wrong `--subchannel` for a multi-subchannel station. The
trace often looks like a square wave bouncing between ±5 Hz (the
search-band edges). **Fix**: re-run `drf_inspect.py` and use the index
it reports.

**Cause 2**: Time window outside the recording. Check the recording
bounds with `drf_inspect.py` and ensure `--start` and `--end` fall
inside them.

**Cause 3**: Signal genuinely too weak. Look at the SNR panel of the
output PNG. If most of the analysis window is sub-25 dB, the carrier is
not reliably trackable and Doppler estimates are noise.

**Cause 4**: Carrier outside `--search-band-hz`. Widen with
`--search-band-hz 10` and try again.

### `drf_spectrogram.py` shows the wrong y-axis (or rejects `--ylim`)

```
error: argument --ylim: expected one argument
```

This is an argparse quirk with negative numbers. Use `=` syntax:

```bash
--ylim=-2,2   # correct
--ylim "-2,2" # also works (note leading space inside quotes)
--ylim -2,2   # FAILS — argparse thinks -2,2 is a flag
```

### `tid_pair.py` reports correlation near zero

The two stations are not seeing the same wave, or the analysis window
is wrong. Look at the two stations' Doppler PNGs and compare visually:

- If both show a clear wave but the shapes differ → maybe two different
  TIDs in different parts of the array.
- If one shows a wave and the other is flat → one station's data is
  bad, or the wave hasn't arrived there yet (try a later window).
- If both look noisy → SNR is too low; try a different time window.

---

## "The DOA result looks wrong"

*See also: [QUALITY_SUMMARY_WORKED_EXAMPLE.md](QUALITY_SUMMARY_WORKED_EXAMPLE.md) for a complete worked example of how a degraded analysis window produces an unphysical DOA result, and how `quality_summary.py` flags the problem.*


This is the most common and most subtle problem. Here's how to diagnose
it systematically.

### Step 1: Are the pairwise lags physically sensible?

Look at the lag table `tid_doa.py` prints. For each pair:

- Lag magnitude should be **comfortably within max_lag_seconds**.
  If a lag is at or near ±max_lag_seconds, the cross-correlation
  hit the edge of the search window and gave up. That station may
  not be seeing the same wave.
- Correlation should be **> 0.4**. Lower means weak or wrong wave.
- Sign should match what you see in the spectrograms — a station
  to your east should lead/lag you in a way consistent with a
  spatially-coherent wave.

### Step 2: Does the triangle closure check pass?

Pick any three stations A, B, C. The lag sum `lag(A→B) + lag(B→C)`
should approximately equal `lag(A→C)`. The script doesn't print
this explicitly, but you can compute it from the lag table. If the
sums disagree by more than ~5-10 minutes for any triangle, the
wave is non-planar or one station's lag is wrong.

### Step 3: Is `use_bandpass: true` doing the wrong thing?

If you changed `use_bandpass` to `true`, you may have re-introduced the
classic failure mode: bandpassing slow TID signals produces
nearly-sinusoidal traces whose autocorrelation has multiple lobes
one period apart. The lag-finder grabs a secondary peak, gives a
deceptively high correlation, and returns the wrong lag.

**Fix**: set `use_bandpass: false` in your config (this is the default).

To confirm bandpass is the problem, run the analysis once with bandpass
disabled and once with it enabled. If the lags or directions differ
dramatically, bandpass is the culprit.

### Step 4: Did one station drag down the fit?

If 5 of 6 pairwise correlations are 0.6–0.8 but one is 0.1, that pair
is noise. The least-squares solution will still try to fit it,
distorting the answer. Options:

- Drop the offending station and re-run with 3 stations (still valid
  if the geometry allows).
- Tighten the time window to avoid noisy parts of that station's
  signal.

### Step 5: Is the wave really planar across the array?

The slowness-vector inversion assumes a single planar wave with one
phase speed and one direction. Real ionospheric disturbances often
violate this — different parts of the wavefront move at different
speeds, or there are multiple overlapping waves.

Indicators:

- Adding/removing one station changes the direction by > 15° or
  speed by > 30%. Indicates the array isn't well-conditioned for the
  wave.
- Correlations all 0.4–0.6 (mediocre but not bad). The wave is
  partially planar.
- Different filter bands give different answers. Multiple waves at
  different periods.

If your event has structure beyond a single planar wave, the toolkit
will still report a "best-fit" plane wave, but you should report the
result with explicit caveats about non-planarity.

### Step 6: Is the speed in a physical range?

The script flags out-of-range speeds. Typical ranges:

- 100–300 m/s: MSTID (acoustic-gravity wave at thermospheric heights)
- 300–1000 m/s: LSTID (large-scale, often auroral-driven)
- > 1500 m/s: probably not a real TID; check for the bandpass-secondary-
  peak issue
- < 100 m/s: unphysical for a TID propagating in the F-region

If the speed is outside these ranges, suspect a methodological problem
before reporting it.

---

## Common cosmetic issues

### Map labels overlap

`tid_map.py` v1.0.0 uses quadrant-based label offsets to avoid most
collisions. If labels still overlap, edit the script's
`label_offsets_by_quadrant` dict at the top of the file.

### Spectrogram annotations clash with the carrier track

The default uses translucent colored regions and brackets to delimit
the annotation. If the colors clash with the spectrogram's content,
you can change them by editing the `callout_colors` list in
`drf_spectrogram.py`.

### Title shows `?` instead of callsign

The Grape v1.x metadata didn't include callsign/grid. Use:

```bash
--callsign "N6RFM/5" --grid "EM12jw"
```

---

## Getting more help

- **The script's `--help` output** is the first line of defense; each
  script's docstring is extensive.
- **The full [workflow tutorial](../WORKFLOW_TUTORIAL.md)** walks through a complete event
  with explanations of each step's purpose.
- **The [cookbook](COOKBOOK.md)** has task-oriented recipes.
- **GitHub issues**: https://github.com/N6RFM/psws-drf-tid-tools/issues
- **The HamSCI / PSWS community**: hamsci-psws Google Group
