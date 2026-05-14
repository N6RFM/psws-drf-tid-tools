# Automation: `analyze_event.sh`

The `analyze_event.sh` script in the repo root is an **interactive
driver** that runs the entire TID analysis pipeline for you, pausing
only at the points that require human judgment. Most of the
typing-the-same-commands-with-different-arguments work that the
manual workflow involves is handled automatically.

For users new to the pipeline, the
[full tutorial](TUTORIAL.md) remains the better starting point — it
explains *why* each step exists. Once you've done one or two events by
hand, `analyze_event.sh` is the natural next step for everyday use.

---

## What it does

The script runs eleven stages with **four human-input pauses**:

| Stage | What happens | Pause? |
|---|---|---|
| 1   | Render reference-station 24-hour spectrogram (+ prior-day flare spectrogram if available) | — |
| 1b  | Auto-detect candidate TID windows: extract a 24-hr survey CSV at 60s, run `tid_window_detector.py`, pad and snap the top-ranked window, re-render the spectrogram with the proposal highlighted | — |
| 2   | Confirm or override the auto-proposed analysis window | ⏸ Pause 1 |
| 3   | Sanity-check extraction on reference station, open the PNG for the user to confirm | — |
| 4   | Run `find_event_stations.py`, display ranked candidates | — |
| 5   | Ask user which companion stations to use | ⏸ Pause 2 |
| 6   | Show download URLs; wait for the user to extract tarballs | ⏸ Pause 3 |
| 7   | Run `drf_inspect.py` on all stations; auto-detect 10 MHz subchannel | — |
| 8   | Extract Doppler CSV for every station with detected subchannels | — |
| 9   | Run `quality_summary.py` to score each station; open every Doppler PNG; ask if any station should be dropped | ⏸ Pause 4 |
| 10  | Build DOA config (with `tid_doa_config.py --auto`) and run `tid_doa.py` | — |
| 11  | Generate annotated spectrogram, stacked Doppler plot, and array-geometry map | — |

Between pauses everything is automatic. The script is also
**resumable** — state is saved to `.analyze_event_state` after each
stage. If you Ctrl-C partway through or hit an error, re-running picks
up from the last completed stage. Use `--reset` to discard the state
and start over.

---

## Quickstart

```bash
# One-time setup
chmod +x analyze_event.sh

# Run for the 19 Jan 2026 event
./analyze_event.sh \
    --date 2026-01-19 \
    --my-call "N6RFM/5" \
    --my-grid "EM12jw" \
    --my-lat 32.94 --my-lon -97.21 \
    --my-station ./n6rfm
```

All six flags above are required on the first run. On subsequent
(resume) runs, they're read from the state file and don't need to be
re-supplied.

---

## How the auto-proposed window is computed

The script's most useful automation is the proposed analysis window
shown at Pause 1. Here is what happens behind the scenes during
Stage 1b:

1. The reference station's full 24 UTC hours are extracted to a
   coarse Doppler CSV (60-second cadence — fast, takes ~30 seconds).
2. `tid_window_detector.py` scores the CSV at multiple sliding
   windows for wave-like activity using spectral power, spectral
   concentration, and stationarity heuristics.
3. The top three candidate windows are reported with scores and
   dominant periods.
4. The #1 window has 15 minutes of padding added on each side
   (because the detector tends to report tight bounds inside the
   wave's central cycle), and the result is snapped to the nearest
   15-minute boundary so the prompt isn't full of awkward times like
   `00:13:47`.
5. The spectrogram is re-rendered with this padded, snapped window
   highlighted in cyan so you can see it in context before deciding.

At Pause 1, **press Enter to accept the proposal** or type your own
start time to override (then you'll be prompted for the end time too).
If the auto-detector found nothing usable (a quiet day, a noisy
recording), the script falls back to fully manual entry.

The proposed window is conservative: small TIDs and partial cycles
sometimes don't make it through the detector's scoring. If you can
see a wave by eye that the detector missed, override.

---

## Flags

| Flag | Purpose |
|---|---|
| `--date YYYY-MM-DD` | UTC date of the event |
| `--my-call CALL` | Your operator callsign (e.g. `N6RFM/5`) |
| `--my-grid GRID` | Your Maidenhead grid (e.g. `EM12jw`) |
| `--my-lat LAT` | Your station latitude in decimal degrees |
| `--my-lon LON` | Your station longitude in decimal degrees |
| `--my-station PATH` | Path to your DRF directory for this event |
| `--workdir DIR` | Working directory (default: current) |
| `--tools-dir DIR` | Where the Python scripts live (default: same dir as this script) |
| `--decim-seconds N` | Doppler extraction cadence (default: 10) |
| `--image-viewer CMD` | Command to open PNGs (default: `xdg-open` on Linux, `open` on macOS, `none` to skip) |
| `--skip-flare` | Don't try to render the prior-day flare-evening spectrogram |
| `--reset` | Discard state file and start fresh |
| `--resume` | Force resume from saved state |
| `--version` | Print version and exit |
| `--help` | Print full usage and exit |

---

## Image viewer tips

The driver opens generated PNGs (spectrograms, per-station Doppler
quick-looks) in your default image viewer so you can review them
without leaving the terminal. The default viewer is `xdg-open` on
Linux and `open` on macOS.

**The viewer should run in the background** — the script continues
immediately and prompts you for input. You should *not* need to close
the viewer for the script to proceed. If your viewer pops to focus
when it opens, just click back into the terminal and answer the
prompt.

### Recommended on Linux: `feh`

The default `xdg-open` typically launches a heavyweight GUI app that
aggressively grabs focus. The lightweight viewer `feh` is much better
behaved for this workflow:

```bash
sudo apt install feh   # Ubuntu / Debian
```

Pick a geometry that matches your display:

| Display              | Suggested `--image-viewer` |
|----------------------|----------------------------|
| 1080p laptop         | `feh --scale-down --geometry 1400x900`  |
| 1080p desktop        | `feh --scale-down --geometry 1600x1000` |
| 1440p / 2K           | `feh --scale-down --geometry 1800x1100` |
| 4K                   | `feh --scale-down --geometry 2400x1500` |

`--scale-down` tells feh to shrink large images to fit the window
(never enlarge small ones). Without it, the window may open at the
image's full native dimensions and overflow the screen.

Example invocation:

```bash
./analyze_event.sh \
    --image-viewer "feh --scale-down --geometry 1800x1100" \
    --date 2026-01-19 \
    --my-call "N6RFM/5" \
    --my-grid "EM12jw" \
    --my-lat 32.94 --my-lon -97.21 \
    --my-station ./n6rfm
```

To make it permanent, add a shell alias:

```bash
# in ~/.bashrc:
alias analyze_event='~/path/to/analyze_event.sh --image-viewer "feh --scale-down --geometry 1800x1100"'
```

### Disable auto-opening entirely

If you'd rather review PNGs manually (e.g. when running over SSH or on
a headless machine):

```bash
--image-viewer none
```

The script will print the path of each generated PNG, but won't try to
open them. You can `scp` them to another machine or browse via VS Code's
file explorer or whatever else works for you.

---

## What each pause expects

### Pause 1: confirm or override the proposed window

The script shows you both the unannotated spectrogram and a second
copy with the auto-proposed window highlighted. When prompted:

```
Start time [Enter = accept proposal]: 
```

Just press Enter to accept the proposal. Or type a start time in
ISO-8601 UTC form (e.g. `2026-01-19T00:00:00`) to override. If you
override the start, the script will prompt you for the end time too.

See the [tutorial Step 1](TUTORIAL.md#step-1-identify-the-tid-region-of-interest-at-your-reference-station)
for guidance on how to choose times if the auto-proposal doesn't look
right.

### Pause 2: choose companion stations

The script runs `find_event_stations.py` and shows a ranked list of
candidates. You pick 2–6 companions to add to your reference station,
comma-separated:

```
Companion stations: aa6bd, w7lux, ac0g_nd
```

Aim for azimuthal spread (N/E/S/W of your station) over raw
correlation score. Use the lowercased short name from the ranked
list (the script converts slashes to underscores internally for path
purposes).

### Pause 3: download the DRF data

The script prints the PSWS download URLs for each companion. You:

1. Open each URL in a browser
2. Download the tarball for the event date
3. Extract each tarball into a directory in your working directory
   named after the station (e.g. `./aa6bd/`, `./w7lux/`, etc.)
4. Press Enter at the script's prompt

The script then verifies all expected directories exist before
continuing. If any are missing, it lists them and exits with code 3 —
fix the directories and re-run.

### Pause 4: quality-check the per-station Doppler

After Doppler extraction, the script runs `quality_summary.py` to score
each station's CSV. The summary table flags:

- **SNR floor** — percentage of samples below 30 dB
- **Jitter** — Doppler trace volatility (std-dev of consecutive sample
  differences). High jitter means the carrier tracker is bouncing.
- **Excursions** — samples with |Doppler| > 2 Hz (usually tracker
  failures)
- **End fade** — how much SNR drops in the last 10% of the window vs
  the middle (suggests the window extends past clean data)
- **Score** — 0-100 composite, with GOOD / OK / POOR / BAD status

If any station has notable end-fade, the script also suggests a
shorter analysis window.

The script then opens every station's quick-look PNG. You confirm:

- The wave is visible (same shape as the reference)
- SNR stays above ~30 dB through the window
- No sustained fades or RFI bursts

When prompted, you can drop any station that looks bad:

```
Stations to DROP (comma-separated, blank = keep all): aa6bd
```

The dropped stations are removed from the final DOA inversion. The
inversion still runs as long as at least 3 stations remain.

---

## Output files

After a complete run, the working directory contains:

```
.analyze_event_state                  resumable state (delete to start over)
event.json                            DOA config used by tid_doa.py
doa_output.txt                        DOA result (text)
ref_<DATE>_survey.csv                 24-hour reference-station Doppler at 60s
ref_<DATE>_spectrogram.png            reference-station 24-hour spectrogram
ref_<DATE>_with_proposal.png          same, with auto-proposed window box
ref_<DATE>_windows.txt                tid_window_detector top candidates
ref_<DATE>_annotated.png              final reference spectrogram (with annotation)
ref_<DATE-1>_spectrogram.png          prior-day flare evening (if applicable)
find_event_stations_<DATE>.txt        full candidate list
drf_inspect_output.txt                per-station metadata
station_subchannels.txt               station -> subchannel mapping
<station>.csv                         Doppler-vs-time CSV (one per station)
<station>.png                         per-station quick-look (one per station)
stack_<DATE>.png                      stacked multi-station Doppler comparison
array_map_<DATE>.png                  array geometry map with wave-direction arrow
```

The final three PNGs (`ref_<DATE>_annotated.png`, `stack_<DATE>.png`,
`array_map_<DATE>.png`) are the figures suitable for
a case-study writeup.

---

## Recovering from a mid-run error

If something goes wrong partway through (network failure during a
download URL fetch, a missing directory, an unexpected DRF format), the
script's `set -e` will cause it to exit at the first error. The state
file records which stage was last completed, so:

```bash
# Investigate and fix the underlying problem, then:
./analyze_event.sh
```

(with no arguments — they'll be read from the state file). The script
resumes at the next un-completed stage.

To force a restart from the beginning:

```bash
./analyze_event.sh --reset \
    --date ... --my-call ... --my-grid ... \
    --my-lat ... --my-lon ... --my-station ...
```

---

## When NOT to use the driver

Use the manual workflow ([tutorial](TUTORIAL.md)) instead when:

- You're learning the pipeline for the first time
- You want to experiment with non-default parameters (different
  bandpass settings, different period bands, etc.)
- You're analyzing an unusual event that doesn't fit the
  flare-then-TID pattern
- The auto-detector isn't finding the window you're interested in
  (small TIDs, partial cycles, weak events)
- You want to use only `tid_pair.py` (two-station) without going all
  the way to DOA inversion

The driver is optimized for the common case of a 3-6 station DOA
analysis using sensible defaults.

---

## Changelog

- **v1.4.0** — Added per-station quality scoring at Pause 4 via the
  new `quality_summary.py`. Reports SNR floor, jitter, excursions,
  end-fade, and a composite 0-100 score for each station, plus an
  optional suggestion to shorten the analysis window if end-fade is
  detected on any station.
- **v1.3.0** — Added `hint` messages under each stage banner explaining
  what's happening and roughly how long it'll take. Stage 4 (the slow
  PSWS-cache walk) now shows a live spinner with elapsed time.
- **v1.2.x** — Pause 1 became a menu-driven editor (view spectrogram,
  change start/end/duration/both); Pause 4 changed from blank-to-keep-
  all to explicit yes/no; Stage 3 sanity-check became y/n with default
  yes. Image viewer now correctly splits its arguments (so `--image-
  viewer "feh --scale-down --geometry ..."` works). Auto-window detection
  uses conservative inward snapping rather than outward padding.
- **v1.1.0** — added Stage 1b auto-detection: extracts a 24-hour
  survey CSV at 60s cadence, runs `tid_window_detector.py` for top
  candidate windows, and re-renders the spectrogram with the proposal
  highlighted. At Pause 1 you Enter to accept or use the menu to edit.
- **v1.0.0** — initial release: 11 stages, 4 human-input pauses,
  fully resumable.
