# Guided Doppler Extraction — Step-by-Step Tutorial

This tutorial walks through the complete workflow for extracting
Doppler phase from a new TID event using the interactive spectrogram
click tool. The result is a human-verified Doppler CSV that can be
fed directly into tid_doa.py for direction-of-arrival analysis.

## Prerequisites

- DRF data directories for each station (e.g. ./w7lux, ./ac0g_nd)
- psws-drf-tid-tools checked out on the research_gui branch
- Python packages: pandas, numpy, pyqtgraph, PyQt5, Pillow, scipy

## Overview

    DRF data → CSV (automated) → spectrogram PNG + sidecar
                                        ↓
                              tid_spect_click.py (GUI)
                                        ↓
                              *_guided.csv (human-verified)
                                        ↓
                              tid_doa.py → speed + direction

---

## Step 1 — Extract automated Doppler CSV

Run drf_to_doppler.py for each station. Use --subchannel to select
the 10 MHz WWV channel (see subchannel notes below).

    python3 drf_to_doppler.py ./w7lux \
        --subchannel 0 \
        --start 2024-05-17T16:00:00 \
        --end 2024-05-17T22:00:00 \
        --decim-seconds 60 \
        --method fft \
        --output w7lux_fft.csv

Repeat for each station, adjusting --subchannel, directory, and
--output as needed.

## Step 2 — Generate spectrogram with sidecar

Run drf_spectrogram.py with the --overlay flag to superimpose the
automated Doppler trace on the spectrogram. This writes both a PNG
and an _axes.json sidecar file that the click tool uses for coordinate
mapping.

    python3 drf_spectrogram.py ./w7lux \
        --subchannel 0 \
        --output w7lux_spect.png \
        --start 16:00 --end 22:00 \
        --ylim="-5,5" --dpi 150 \
        --overlay w7lux_fft.csv:FFT

Open w7lux_spect.png and identify:
- The analysis window (where the TID is active)
- The carrier track (wavy red/orange line near 0 Hz)
- The start/end time in decimal UTC hours (e.g. 18.0 to 20.0)

Repeat for each station.

## Step 3 — Launch the click tool

    python3 tid_spect_click.py \
        --spectrogram w7lux_spect.png \
        --csv w7lux_fft.csv \
        --name W7LUX \
        --seg-start 18 --seg-end 20 \
        --period-hint 3600

Arguments:
  --spectrogram   PNG file from Step 2
  --csv           automated CSV from Step 1
  --name          station label shown in title bar
  --seg-start     analysis window start (decimal UTC hours)
  --seg-end       analysis window end (decimal UTC hours)
  --period-hint   expected TID period in seconds (use 3600 for LSTID,
                  1800 for MSTID); required if clicks do not span a
                  full wave cycle

The sidecar (_axes.json) is auto-detected — no --tlim or --ylim needed.

## Step 4 — Click phase samples in the GUI

The spectrogram opens with:
- Grey automated Doppler trace overlaid on the carrier
- Yellow shaded region = analysis segment (drag edges to adjust)
- Status bar showing click count and segment bounds

Click 5-7 points along the carrier track inside the yellow segment.
Aim to sample the full wave shape:
- One point near a crest (carrier above 0 Hz)
- One point near a trough (carrier below 0 Hz)
- Points at zero-crossings
- Points spread across the segment time span

Red dots appear at each click. If you misclick, press R to reset
and start over for this station.

## Step 5 — Fit and write

Press F — a sinusoid is fitted through your clicks and overlaid in
blue. Check the status bar:

    Fit: A=0.81 Hz  T=3600 s  phi=-54.6 deg  — press W to write CSV

- A (amplitude) should match the visible carrier excursion (~0.3-1.5 Hz)
- T (period) should match the TID period you expect
- If T looks wrong, press R, re-click more carefully, and press F again

Press W to write the guided CSV (e.g. w7lux_fft_guided.csv).
Press Q to quit and move to the next station.

## Step 6 — Repeat for each station

If a station's spectrogram shows no coherent carrier (heavy
contamination, no visible TID), skip the guided step and use
the automated CSV directly in the event config.

## Step 7 — Create event config

    cat > event_guided.json << 'EOF'
    {
      "event_start_utc": "2024-05-17T18:00:00Z",
      "event_end_utc": "2024-05-17T20:00:00Z",
      "resample_seconds": 60,
      "use_bandpass": false,
      "min_expected_speed_m_s": 100,
      "stations": [
        {"name": "W7LUX",   "file": "w7lux_fft_guided.csv",
         "method": "fft", "lat": 35.1042, "lon": -111.7083},
        {"name": "AC0G_ND", "file": "ac0g_nd_fft_guided.csv",
         "method": "fft", "lat": 46.875,  "lon": -96.8333},
        {"name": "N4RVE",   "file": "n4rve_fft_guided.csv",
         "method": "fft", "lat": 48.5417, "lon": -123.1667}
      ]
    }
    EOF

Use the automated CSV for any station where the guided step was skipped.

## Step 8 — Run DOA analysis

    python3 tid_doa.py event_guided.json

## Step 9 — Compare with automated baseline

Run tid_doa.py on both configs and compare:

    echo "=== Guided ==="
    python3 tid_doa.py event_guided.json 2>/dev/null | \
        grep "Phase speed\|heading\|coming\|Triangle closure\|>> All"

    echo "=== Automated ==="
    python3 tid_doa.py event_automated.json 2>/dev/null | \
        grep "Phase speed\|heading\|coming\|Triangle closure\|>> All"

If results agree (speed within ~10%, direction within ~10 deg) the
automated extraction is reliable. If they disagree, the guided result
is more trustworthy for stations where the carrier was clearly visible.

---

## Subchannel reference (May 2024 LSTID event)

| Station  | Subchannel | Freq    | SNR     | Notes |
|----------|-----------|---------|---------|-------|
| W7LUX    | 0         | 10 MHz  | 51.6 dB | Clean |
| AC0G_ND  | 4         | 10 MHz  | 42.0 dB | E-region contamination in 18-20h window |
| N4RVE    | 4         | 10 MHz  | 42.3 dB | Usable |

Note: subchannel 0 on AC0G_ND gives 2.5 MHz — wrong frequency,
no visible carrier.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| F   | Fit sinusoid from clicks |
| W   | Write guided CSV |
| R   | Reset clicks for this station (keeps calibration) |
| C   | Clear all clicks and calibration |
| Q   | Quit |

---

## Troubleshooting

**Window closes immediately on launch**
A stray keypress from the shell is triggering Q. Launch with a
trailing space or from a fresh terminal.

**Period looks wrong after F (e.g. T=7000s)**
Your clicks do not span a full TID cycle. Add --period-hint 3600
(or appropriate period) to the launch command.

**Carrier not visible in spectrogram**
Try a different subchannel. Check the station subchannel table above.
If still no carrier, the station is too contaminated — use the
automated CSV directly.

**Sidecar not auto-detected**
Ensure the _axes.json file is in the same directory as the PNG and
has the same stem name (w7lux_spect.png → w7lux_spect_axes.json).
Regenerate with drf_spectrogram.py if missing.

---

## Clicking guidelines — how to place phase samples correctly

The goal is to trace the **smooth F-region TID carrier**, not the brightest
feature in the spectrogram at each moment.

**DO:**
- Click on the centre of the smooth, slowly-varying bright line near 0 Hz
- Aim for points where the carrier is clearly isolated with no competing
  features nearby
- Space clicks evenly across the segment — aim for one click every
  15-20 minutes
- Include at least one clear crest and one clear trough if visible
- If the carrier is temporarily obscured by interference, skip that region
  and place clicks where it re-emerges clearly

**DO NOT:**
- Click on sharp vertical spikes — these are E-region hops, not TID
- Click where multiple bright lines are present — pick the smoothest one
- Click on the brightest feature if it is clearly jumping erratically
- Click only in one part of the segment — spread clicks across the full window

**Verifying your clicks are correct:**
After pressing F, the fitted sinusoid (blue) should:
- Pass smoothly through all your red dots
- Have a period matching the visible TID oscillation (~3600s for LSTID)
- Have an amplitude matching the visible carrier excursion (~0.3-1.5 Hz)

If the fit looks wrong (wrong period, huge amplitude, flat line):
- Press R to reset and re-click more carefully
- Try --period-hint 3600 if not already set
- Zoom in with scroll wheel to see the carrier more clearly before clicking

**The critical test:**
After pressing X to export the corridor JSON, check that the corridor
centre values track the same oscillation as the automated FFT CSV.
Large systematic offsets (>0.3 Hz sustained over many minutes) indicate
the clicks are on a different feature than the automated extractor.
Run the comparison script in the troubleshooting section to verify.
