# quality_summary.py — a worked example

This document shows why per-station quality scoring matters in TID
analysis, using a real failure mode encountered during pipeline
development on the **19 January 2026 LSTID** event. The pattern
illustrated here applies to any TID analysis where one or more
stations have degraded signal inside the chosen analysis window.

For the analysis pipeline overview, see the [tutorial](TUTORIAL.md).
For the methodology behind the slowness-vector inversion, see
[methodology](METHODOLOGY.md).

---

## The setup

On 18 January 2026 at 18:09 UTC the Sun produced an X1.9 flare; a
Large-Scale TID arrived over the central US several hours later.
Four HamSCI Grape stations recorded the event:

- **N6RFM/5** (EM12jw, reference station)
- **AA6BD** (EM75kb)
- **W7LUX** (DM45dc)
- **AC0G/ND** (EN16ov)

Visual inspection of N6RFM/5's spectrogram showed a clear wave
between roughly 00:00 and 01:30 UTC on 19 January. The
`tid_window_detector.py` auto-detector flagged the same band, and
the driver script proposed an analysis window of **00:00 to 01:45
UTC**.

The four stations had been verified, their DRF subchannels mapped
correctly, and each station's quick-look Doppler PNG looked
reasonable. The operator pressed Enter at every pause. The result
was wrong.

---

## What went wrong: the wider window (00:00 - 01:45 UTC)

The slowness-vector inversion produced a non-physical result:

- **Phase speed**: 1973 m/s (7104 km/h)
- **Wave heading**: 1.9° true (due north)
- **Wave source**: 181.9° true (due south)
- **Classification**: speed outside typical TID range

The pairwise lag matrix reveals the cause:

| Pair | Lag (s) | Correlation |
|---|---:|---:|
| N6RFM/5 → AA6BD | -1590 | 0.686 |
| N6RFM/5 → W7LUX | -210 | 0.632 |
| N6RFM/5 → AC0G/ND | -1670 | 0.481 |
| AA6BD → W7LUX | +1360 | 0.781 |
| AA6BD → AC0G/ND | -110 | 0.444 |
| **W7LUX → AC0G/ND** | **+3700** | **0.410** |

Three things stand out. First, the three pairs involving AC0G/ND
have markedly lower correlations (0.41 to 0.48) than the three pairs
not involving AC0G/ND (0.63 to 0.78). Second, the W7LUX → AC0G/ND
lag of +3700 seconds is unphysical: it implies the wave took 61
minutes to traverse a 1207 km baseline, a phase speed below 350 m/s
along a direction that the other pairs strongly disagree with.
Third, the least-squares slowness-vector fit, asked to satisfy all
six pairs simultaneously, has no consistent solution and produces
the non-physical north-south result.

The root cause: **AC0G/ND's signal begins to fade after
approximately 01:18 UTC**. The 27 minutes of degraded signal between
01:18 and 01:45 corrupts every cross-correlation that involves
AC0G/ND. The W7LUX → AC0G/ND pair is hit hardest because that pair
is on the longest baseline (1207 km) and is correlating one clean
trace against one increasingly noisy one across that distance.

---

## What's right: the narrower window (00:00 - 01:15 UTC)

Trimming the window to end at 01:15 UTC, before AC0G/ND's fade:

- **Phase speed**: 660.9 m/s (2379 km/h)
- **Wave heading**: 215.1° true (SW)
- **Wave source**: 35.1° true (NE)
- **Classification**: LSTID

The pairwise lag matrix is now internally consistent:

| Pair | Lag (s) | Correlation |
|---|---:|---:|
| N6RFM/5 → AA6BD | -1000 | 0.578 |
| N6RFM/5 → W7LUX | -70 | 0.561 |
| N6RFM/5 → AC0G/ND | -1340 | 0.696 |
| AA6BD → W7LUX | +1280 | 0.686 |
| AA6BD → AC0G/ND | 0 | 0.774 |
| W7LUX → AC0G/ND | -980 | 0.737 |

All six correlations cluster between 0.56 and 0.77. No lag sits at
the edge of the max_lag_seconds search window. The three
independent triangles close to within 7 minutes on lag sums. This
is the result that matches independent observations and that the
case study at https://spectrogram-docs.readthedocs.io reports.

---

## What `quality_summary.py` shows you

The toolkit's `quality_summary.py` was added precisely to catch
this kind of problem before the DOA inversion runs. Run on the
wider-window extractions, it produces:

```
Quality summary:
  Station         SNR floor   Jitter   Excur.   End fade   Score   Status
  --------------- ---------- -------- -------- ---------- ------- --------
  N6RFM/5                0%     0.11        0       +6.6    77.8   OK
  AA6BD                  1%     0.26        0       -1.3    78.4   OK
  W7LUX                  0%     0.04        0       -0.5   100.0   GOOD
  AC0G/ND                1%     0.04        0       +2.1    94.4   GOOD

End-fade suggestions:
  N6RFM/5: SNR drops +6.6 dB in the last 10% of the window.
    Consider shortening the analysis window to end at or before
    2026-01-19T01:07:24.
```

Each station's score is a 0–100 composite of SNR floor, Doppler
jitter, out-of-band excursions, and end-fade. Stations rated POOR
(below 60) or BAD (below 40) almost always produce a degraded
contribution to the DOA inversion.

In this case, no station scored POOR, but the **end-fade flag on
N6RFM/5** caught the problem with a concrete suggestion. The
recommended end time of 01:07:24 cuts before the noise spikes that
appear in N6RFM/5 after about 01:13 UTC. Acting on that
suggestion — or any similar tightening of the window — yields the
correct LSTID result.

(Note: in this event the underlying problem was the *companion
station* AC0G/ND's fade, but the symptom that surfaces in the
quality summary appears on the *reference station* N6RFM/5's
trace, because the reference station's extracted Doppler also
degrades near the end of the window for unrelated tracker reasons.
Both effects together push the operator toward the same correct
remedy: a shorter window.)

---

## Running `quality_summary.py` yourself

The script is called automatically by `analyze_event.sh` at Pause 4,
but you can also run it standalone:

```bash
# Score every CSV in the current directory (skips survey/quicklook files)
python3 quality_summary.py *.csv

# Verbose per-station diagnostics
python3 quality_summary.py --verbose n6rfm.csv aa6bd.csv

# Pull station list from a DOA event config
python3 quality_summary.py --config event.json

# Include the window-shortening suggestion
python3 quality_summary.py --suggest-shorten *.csv

# Include scratch/survey CSVs you'd normally skip
python3 quality_summary.py --include-scratch *.csv
```

The script does not modify any files. It reads CSVs and writes the
table to stdout, with notes about skipped/scratch files going to
stderr.

---

## Two general lessons

### 1. The reference station's spectrogram cannot reveal companion-station data quality

N6RFM/5's spectrogram showed a clean wave between 00:00 and ~01:13
UTC. Based on that alone, a window of 00:00 to 01:45 UTC seemed
defensible. But the reference station's spectrogram says **nothing**
about whether AC0G/ND, W7LUX, or AA6BD were clean during the same
period.

The pipeline's design — propose a window from the reference
station, then refine after companion data is in hand — exists
precisely because the right window depends on conditions across all
stations. Use the reference-station spectrogram to identify a
*candidate* window, then refine after Stage 8 when you have the
companion data extracted and `quality_summary.py` can score every
station together.

### 2. A nominal correlation above 0.4 is not sufficient evidence of clean data

Even degraded cross-correlations can hit the 0.40–0.48 range when
the underlying signals have any shared structure at all (the trend
of a TID wave is broad enough that some correlation persists even
under noisy conditions). Operators should:

- Look at the whole lag matrix together, not individual pairs in
  isolation
- Prefer pairwise correlations **above 0.5**, with most pairs at
  0.6 or higher
- View a single low correlation in the context of whether its lag
  is physically plausible
- Check whether lags are at the edge of `max_lag_seconds` (a sign
  the cross-correlation hit the search-window boundary without
  finding a clean peak)

`quality_summary.py` surfaces SNR, jitter, and end-fade — proxies
for the underlying data quality — so the operator doesn't have to
deduce them from the post-correlation lag matrix.

---

## When to use this in your own analyses

- **If you're running the driver**: `quality_summary.py` runs
  automatically at Pause 4 and surfaces the table and any end-fade
  suggestions. Pay attention to stations rated POOR or BAD, and
  consider any window-shortening suggestion.
- **If you're running stages manually**: run
  `quality_summary.py --suggest-shorten *.csv` after extracting
  Doppler with `drf_to_doppler.py` and before building the DOA
  config. If the table shows poor scores, fix the window or drop
  the bad stations before running `tid_doa.py`.
- **If your DOA result looks unphysical** (speeds above 1500 m/s,
  directions suspiciously aligned with cardinal axes, or
  significantly different from what you expect): run
  `quality_summary.py` on the CSVs you used. End-fade or high
  jitter on any one station is a strong signal that the result is
  contaminated. See also [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Related documentation

- [TUTORIAL.md](TUTORIAL.md) — full pipeline walkthrough
- [AUTOMATION.md](AUTOMATION.md) — `analyze_event.sh` driver reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — diagnosing common failures
- [METHODOLOGY.md](METHODOLOGY.md) — math behind the slowness inversion
- The case study at https://spectrogram-docs.readthedocs.io
