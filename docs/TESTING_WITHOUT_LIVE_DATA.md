# Testing Without Live Data

`mock_psws_server.py` is a local stand-in for the real PSWS network
portal (`pswsnetwork.eng.ua.edu`). It lets you run the **actual,
interactive** guided workflow — `tid_workflow.py`, `tid_intake_helper.py`,
`find_event_stations.py`, `download_companions.py` — against realistic
fake data, entirely offline.

**This is not the same thing as `synthetic_tests/`.** That suite runs
automated batch validation across 29 ground-truth scenarios with no
human interaction (see `synthetic_tests/README.md`). This document
covers the mock server, which is for exercising the real, interactive
pipeline itself — channel-num confirmation, window selection, the
redraw prompt, wave-fit clicking, the DOA explore loop — the same
things a human operator actually does with real data.

Use the mock server when:

- **The real PSWS server is down or unreachable** and you still need
  to test a workflow change, learn the tool, or verify a bug fix.
- You're developing or debugging any part of the pipeline and don't
  want to wait on network calls to real infrastructure, or don't want
  to risk confusing real event data with test runs.
- You want a **known ground truth** to check `tid_doa.py`'s result
  against, which no real event can give you.

---

## Quick start

**Terminal 1 — start the mock server, leave it running:**

```bash
cd psws-drf-tid-tools
source .venv/bin/activate
python3 mock_psws_server.py
```

You should see:

```
Mock PSWS server -- serving fake data for test date 2099-01-01
Ground truth: 400 m/s, arriving from 270° true bearing -- tid_doa.py's result should land close to this.
Fake stations: TESTKEY, TESTA, TESTB, TESTC
Listening on http://127.0.0.1:8765 -- Ctrl+C to stop
```

Use `--port N` to run on a different port if 8765 is already in use.

**Terminal 2 — point every tool at it, then use the pipeline normally:**

```bash
cd psws-drf-tid-tools
source .venv/bin/activate
export PSWS_BASE_URL=http://127.0.0.1:8765
```

Verify it's actually reachable before doing anything else — a silent,
unset environment variable is the most common way this goes wrong:

```bash
curl -s http://127.0.0.1:8765/stations/stations/ | head -3
```

This must show `TESTKEY`, `TESTA`, `TESTB`, `TESTC` in the output. If
it hangs or errors, the server in Terminal 1 isn't running or isn't
reachable — fix that before continuing.

Download and run:

```bash
python3 download_companions.py --date 2099-01-01 \
    --stations TESTKEY TESTA TESTB TESTC \
    --out-dir ~/Downloads/tid_event_20990101

python3 tid_workflow.py \
    --event-dir ~/Downloads/tid_event_20990101 \
    --stations TESTKEY,TESTA,TESTB,TESTC \
    --my-station TESTKEY \
    --max-lag 30
```

**`PSWS_BASE_URL` only lasts for the terminal session it's exported
in.** Opening a new terminal tab or window means it's unset again —
re-export it there too, or every download will silently fall through
to the real (and possibly down) PSWS server instead of the mock one.

---

## The fake stations

| Callsign | Lat | Lon | Grid | Public station ID |
|----------|-----|-----|------|--------------------|
| TESTKEY  | 35.00 | -95.00 | EM45aa | S900001 |
| TESTA    | 37.00 | -90.00 | EM57aa | S900002 |
| TESTB    | 40.00 | -100.00 | EN00aa | S900003 |
| TESTC    | 33.00 | -105.00 | DM63aa | S900004 |

All four:

- Are single-channel, 10 sps, transmit on 10.000 MHz WWV (channel-num
  is always 0).
- Have exactly **one hour** of real recorded data, starting at
  `2099-01-01 00:00:00 UTC`. Any window you select — in
  `tid_quicklook.py`'s drag-select, or the `--start`/`--end` of a
  manual `drf_spectrogram.py` call — must fall inside that hour.
  Selecting anything outside it (e.g. `01:00`–`02:00`) fails cleanly
  with an explicit error rather than a crash (see
  [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)), but it still won't
  produce usable data — pick a window inside 00:00–00:59 UTC.
- Coordinates auto-resolve in both `tid_workflow.py` and
  `tid_intake_helper.py` without prompting, the same as a real
  callsign would — the fake stations are merged into the same
  `KNOWN_STATIONS` lookup both tools already use.

**The test date is fixed:** `2099-01-01`. Using today's date (or any
other date) against the mock server will find nothing, since it only
knows about that one fabricated day.

---

## The ground truth

Every fake station's synthetic signal has a **real, physically
computed propagation delay** baked in, corresponding to an assumed
plane wave:

- **Speed: 400 m/s** (solidly in the LSTID range)
- **Arriving from: 270° true bearing** (i.e. travelling east)
- **Period: 60 minutes**

Each station's delay is computed from its actual IPP midpoint (station
↔ WWV, at 40.68°N, 105.04°W), using the exact same great-circle
midpoint formula and azimuthal-equidistant local projection that
`tid_doa.py` itself uses to solve for direction — not an approximation
of it. That self-consistency is what makes the ground truth meaningful:
a full workflow run's recovered speed and bearing should land in the
neighborhood of 400 m/s / 270°, not merely "some plausible LSTID
number."

In practice, expect the recovered result to be close but not exact —
typically within 10–20% on speed and a few degrees on bearing,
depending on extraction method and how precisely the same window is
selected across all four stations. Two things noticeably improve
precision:

- **Apply the same window to every station** (answer `y` when
  `tid_workflow.py` asks "Apply \<window\> to all remaining stations?").
  Independent, slightly-misaligned windows per station inject real
  timing noise directly into the cross-correlation lags.
- **Prefer `wave-fit` or `cwt-prophet`** over `autocorr` for the
  tightest match — the period-hint seeding (once the keystone's own
  period is measured, every other station's fit is seeded with it)
  tends to converge all four stations on the same period, which
  `autocorr` doesn't benefit from.

A result that's *wildly* off (orders of magnitude on speed, or a
diagnostic reporting near-zero lags across every pair) usually means
either mismatched windows, or something in a code change under test
broke the propagation-delay logic itself — not normal synthetic-data
noise.

---

## Using `tid_intake_helper.py` against the mock server

The GUI intake tool works the same way — set `PSWS_BASE_URL` in the
same terminal before launching it:

```bash
export PSWS_BASE_URL=http://127.0.0.1:8765
python3 tid_intake_helper.py
```

Enter callsign `TESTKEY`, date `2099-01-01`. Coordinates auto-fill the
same as a real station. "Find Companion Stations" should list TESTA,
TESTB, TESTC. Download organizes all four into an event directory and
generates the `tid_workflow.py` command to continue with.

---

## What's actually being tested

Running the guided workflow against the mock server exercises the real
code paths for:

- Station discovery and channel-num confirmation
- Full-day spectrogram generation, including the redraw-on-demand
  prompt (every station, every time — see `WORKFLOW_TUTORIAL.md`)
- Window selection via `tid_quicklook.py`, including the
  apply-to-all-stations convenience
- All four extraction methods (`cwt-prophet`, `autocorr`, `cwt`,
  `wave-fit`)
- The DOA explore loop (`drop` / `add` / `all`)
- Every diagnostic in `tid_doa.py`'s output

It does **not** meaningfully exercise: real-world signal artifacts
(mode jumps, sporadic-E, genuine noise floors), the Madrigal TEC
cross-check tools (`fetch_madrigal_tec.py`, `evaluate_external.py` —
these need real GNSS-TEC data for the actual event date), or anything
date-specific about a real event. For those, `synthetic_tests/`'s
noise-injection scenarios or a real event are the right tool instead.

---

## Cleanup

```bash
rm -rf ~/Downloads/tid_event_20990101
```

Then `Ctrl+C` in the terminal running `mock_psws_server.py`.

---

## Troubleshooting

See the "Testing when the PSWS server is down" section of
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for the specific failure
modes this setup produces (wrong terminal, server not running, stale
station-ID cache, out-of-bounds window selection) and how to fix each.
