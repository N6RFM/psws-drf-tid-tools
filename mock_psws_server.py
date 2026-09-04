#!/usr/bin/env python3
"""
mock_psws_server.py -- local stand-in for the PSWS observation portal,
for testing find_event_stations.py / download_companions.py /
tid_intake_helper.py while the real API (pswsnetwork.eng.ua.edu) is
offline.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.4.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.4.0  Added --scenario NAME and --list-scenarios, serving any of
          synthetic_tests/'s 29 real test conditions (real station
          arrays, known ground truth, optional noise/enhancement
          effects -- two superimposed waves, period chirp, E-region
          spikes, coloured noise, fading SNR, carrier offset) instead
          of just the single classic 4-station default. Deliberately
          calls synthetic_drf.generate_event() directly rather than
          re-implementing test_conditions.py's own per-test special-
          casing a second time here -- any condition added to that
          file in the future works through this server automatically.
          Verified end-to-end against two different scenarios (a
          3-station and a 4-station array): downloaded, extracted, and
          ran real DOA, landing within each scenario's own stated
          pass criteria both times (nominal: 526.7 m/s from 29.2 true
          vs. 500 m/s from 30 true; mixed_4stn: 542.0 m/s from 137.4
          true vs. 509 m/s from 137 true).

          Found and fixed a real (harmless) bug in synthetic_drf.py
          while checking this precisely rather than trusting it:
          EVENT_START_UTC's own inline comment claimed 2026-01-19, but
          the actual timestamp resolves to 2025-01-19 -- a full year
          off. No functional impact anywhere (every use of the
          constant reads the numeric value directly, never the
          comment), but worth being accurate, especially since
          2026-01-19 is this project's own real reference event date
          and an incorrect comment here could otherwise cause genuine
          confusion. Confirmed there is no actual date collision risk
          with real downloaded data as a result.

          Curated a 6-scenario RECOMMENDED_SCENARIOS list as the
          --list-scenarios default (30 is too many for a hands-on
          demo where the point is showing a few clearly different
          kinds of behaviour, not exhaustively sweeping every
          parameter) -- --list-scenarios --all still shows the
          complete list. Added a 30th condition, conus_5stn, since no
          5-station option existed at all (max was 4, used by exactly
          one condition) -- see synthetic_tests/test_conditions.py's
          own v1.2.0 changelog entry for the details, including a
          real alias-safety bug caught before shipping it (an initial
          60-min period was NOT alias-safe for this specific 5-station
          geometry, checked directly rather than assumed). Verified
          this scenario too, same as the other two: recovered 727.4
          m/s from 62.7 true vs. a ground truth of 682 m/s from 63
          true -- deliberately matching this project's own real 19
          January 2026 reference event exactly, for direct comparison.

          Also found live: killing scenario generation partway through
          (e.g. an impatient Ctrl+C, or a test script that connects
          before generation finishes) leaves a broken, partially-
          written cache under synthetic_tests/events/ that fails every
          future attempt to regenerate that same scenario, since
          generate_event()'s own caching only checks whether
          ground_truth.json exists -- written only at the very end --
          not whether a partial previous attempt left conflicting
          files behind. Not fixed at the generate_event() level itself
          (out of scope here, and used by the real automated test
          suite too) -- instead, a clear warning now prints before
          generation starts, since larger scenarios can take over a
          minute and there was previously no indication of that.

  v1.3.0  Fixed a real error in v1.2.0's own ground truth: it used
          tid_workflow.py's plain arithmetic-average midpoint()
          function -- the one used only for a quick preview print
          during Step 1's channel-num confirmation -- not what
          actually feeds the DOA math. Found only because asked to
          check this carefully rather than trust an earlier quick
          grep: tid_workflow.py's own menu text says "use great-circle
          midpoint between station and WWV as the DOA coord" for a
          reason -- a *second*, separate function (tid_workflow.py's
          own _gc_mid, explicitly commented "matches
          tid_doa.great_circle_midpoint") is what's actually used.
          Beyond the midpoint itself, tid_doa.py's own DOA fit also
          doesn't project station positions with a flat equirectangular
          approximation (what v1.2.0 used) -- it centers on the *array
          centroid* (mean of all stations' own IPP midpoints, not WWV)
          and projects with an azimuthal-equidistant transform whose
          own docstring explicitly says this exists because the
          equirectangular approximation is NOT accurate enough at
          CONUS scale (~1000-2000 km baselines) -- exactly the scale
          this fake array spans. Now imports and reuses tid_doa.py's
          own great_circle_midpoint() and latlon_to_local_xy()
          directly rather than a second approximation of them, so the
          ground truth this file generates is genuinely self-
          consistent with what the real solver solves, not merely
          close. Confirmed the corrected IPP coordinates now differ
          measurably from v1.2.0's (e.g. TESTKEY: 37.84,-100.02 ->
          37.95,-99.83) -- this was a real, substantive correction,
          not a cosmetic one.

Change log:
  v1.2.0  Added a real, known propagation delay between fake stations
          instead of generating the identical undelayed waveform for
          all of them. Found live: a full real-data-shaped run through
          tid_workflow.py -> tid_doa.py against the old data gave
          pairwise lags of ~0.0s between every station pair despite
          real geographic separation, which correctly produced a
          phase-speed result in the tens of millions of m/s (near-zero
          lag over real distance implies near-infinite speed) --
          tid_doa.py's own diagnostics correctly flagged this as
          unphysical, but the mock data was never actually testing the
          DOA math against a known answer, only exercising the
          pipeline mechanics. Now assumes a plane wave at
          TRUE_SPEED_MPS / TRUE_BEARING_FROM_DEG and computes each
          station's real delay from its IPP midpoint -- calculated
          with tid_workflow.py's own plain arithmetic-average
          midpoint() formula, confirmed by matching real printed
          output exactly, not a fancier great-circle formula that
          would silently use different coordinates than what
          tid_doa.py itself solves in. A full run should now recover a
          phase speed and bearing close to the assumed ground truth.

Change log:
  v1.1.0  Fixed synthetic recordings only containing 10 real minutes
          of samples inside a DRF block whose declared bounds still
          span a full hour (write_station_drf's own subdir cadence is
          a fixed 3600s, independent of how many samples are actually
          written). A full-day spectrogram read across that "declared
          but empty" 50-minute remainder, which dominated the plot's
          automatic color-scale normalization and produced a
          degenerate near-zero-range colorbar with a solid black/
          white split at the 10-minute mark -- confirmed live, then
          confirmed fixed, by generating a full real hour instead and
          comparing the two spectrograms directly. See
          _build_fake_drf_zip()'s own docstring for the full
          before/after story.
WHY THIS EXISTS
================
find_event_stations.py and download_companions.py don't talk to a
clean JSON API -- they scrape actual PSWS web pages with BeautifulSoup
(a station-dropdown <select>, an HTML observations table, an HTML
station directory table) and download a real ZIP of Digital RF data.
Confirmed directly by reading both scripts' parsing code rather than
guessing at the page shapes. This server reproduces exactly those
page shapes (matching td-index/regex assumptions verbatim) so the two
real scripts -- unmodified except for one line each, a PSWS_BASE_URL
environment-variable override -- can run against it with no other
changes.

The downloadapi endpoint doesn't return placeholder bytes: it
generates real Digital RF data on the fly using
synthetic_tests/synthetic_drf.py's own write_station_drf(), the same
function the project's real end-to-end test suite uses. That means
data downloaded through this mock is a genuinely valid DRF dataset --
tid_workflow.py can run its full pipeline against it, not just the
intake helper's download step.

FAKE TEST DATA
==============
4 fake stations, only "observed" on 2099-01-01 (deliberately a date
nothing real could ever collide with):
  TESTKEY  (35.00, -95.00)  EM45aa  -- intended as "my station"
  TESTA    (37.00, -90.00)  EM57aa
  TESTB    (40.00, -100.00) EN00aa
  TESTC    (33.00, -105.00) DM63aa

USAGE
=====
    python3 mock_psws_server.py                  # serves on :8765
    python3 mock_psws_server.py --port 9000

In another terminal:
    export PSWS_BASE_URL=http://127.0.0.1:8765
    python3 find_event_stations.py --date 2099-01-01 \\
        --my-lat 35.00 --my-lon -95.00 --my-call TESTKEY
    python3 download_companions.py --date 2099-01-01 \\
        --stations TESTKEY TESTA TESTB TESTC \\
        --out-dir ~/Downloads/tid_event_20990101
    # or via the GUI:
    python3 tid_intake_helper.py   (same PSWS_BASE_URL env var applies)
"""

import argparse
import io
import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

TOOLS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOLS_DIR / "synthetic_tests"))

try:
    from synthetic_drf import write_station_drf, generate_event
    _HAVE_SYNTH = True
except Exception as e:
    _HAVE_SYNTH = False
    _SYNTH_IMPORT_ERROR = e

try:
    from test_conditions import TEST_CONDITIONS, ARRAYS
    _HAVE_TEST_CONDITIONS = True
except Exception as e:
    _HAVE_TEST_CONDITIONS = False
    _TEST_CONDITIONS_IMPORT_ERROR = e

TEST_DATE = "2099-01-01"

# form_id -> (nickname, public_sid, grid, lat, lon)
FAKE_STATIONS = {
    "9001": ("TESTKEY", "S900001", "EM45aa", 35.00, -95.00),
    "9002": ("TESTA",   "S900002", "EM57aa", 37.00, -90.00),
    "9003": ("TESTB",   "S900003", "EN00aa", 40.00, -100.00),
    "9004": ("TESTC",   "S900004", "DM63aa", 33.00, -105.00),
}
NICK_TO_FORM_ID = {v[0]: k for k, v in FAKE_STATIONS.items()}
SID_TO_FORM_ID = {v[1]: k for k, v in FAKE_STATIONS.items()}

# Ground truth for the synthetic wave, so a full pipeline run against
# this mock data has a known answer to check tid_doa.py's result
# against -- not just "did it run without crashing."
#
# WWV_LAT/WWV_LON and the IPP formula below deliberately match
# tid_workflow.py's own defaults and its own midpoint() function
# EXACTLY (confirmed directly against real printed output: a TESTKEY
# station at 35.00,-95.00 prints "IPP midpoint: 37.8400N, 100.0200W",
# which is the plain arithmetic average (lat+tx_lat)/2, (lon+tx_lon)/2
# -- not a true great-circle midpoint, which find_event_stations.py
# uses for a different purpose and would have given a slightly
# different answer here). Using any other midpoint definition would
# silently bias the "true" bearing/speed this data is built around.
WWV_LAT, WWV_LON = 40.68, -105.04
TRUE_SPEED_MPS = 400.0        # LSTID-range ground truth
TRUE_BEARING_FROM_DEG = 270.0  # wave arriving FROM the west, i.e.
                                # travelling toward true bearing 90
TRUE_PERIOD_S = 3600.0  # 60 min -- must be long enough that half the
    # period exceeds the max delay spread across the fake array
    # (~1583 s here) or cross-correlation can lock onto the wrong
    # period's peak -- confirmed live: a 1800 s period was too short
    # for the real ~1583 s delay spread this station geometry
    # produces, at ~400 m/s (verified with a direct extract-and-
    # correlate test against the raw synthetic IQ, independent of the
    # interactive pipeline: recovered lags disagreed with the intended
    # ground truth, including one station off in *sign*, both
    # symptoms of a wrong-period lock rather than a bug in the delay
    # calculation itself).

# IMPORTANT correction (found only after being asked to check this
# carefully -- an earlier version of this file used tid_workflow.py's
# *quick-preview* midpoint() function, a plain arithmetic average
# shown to the user during Step 1's channel-num confirmation only.
# That is NOT what actually feeds the DOA math. The real solver
# (tid_doa.py) uses a proper spherical great-circle midpoint for each
# station's IPP, then projects all of them with an azimuthal-
# equidistant transform centred on the *array centroid* (the mean of
# all stations' own IPP midpoints, not WWV) -- its own docstring
# explicitly says this exists because an equirectangular approximation
# is NOT accurate enough at CONUS scale (~1000-2000 km baselines),
# which is exactly the scale this fake array spans. Reusing tid_doa's
# actual functions directly here, rather than a second approximation
# of them, is the only way to guarantee the "ground truth" this file
# generates is truly self-consistent with what the real solver solves.
from tid_doa import great_circle_midpoint, latlon_to_local_xy

_ALL_IPPS = {
    nick: great_circle_midpoint(lat, lon, WWV_LAT, WWV_LON)
    for _fid, (nick, _sid, _grid, lat, lon) in FAKE_STATIONS.items()
}
_CENTROID_LAT = sum(la for la, lo in _ALL_IPPS.values()) / len(_ALL_IPPS)
_CENTROID_LON = sum(lo for la, lo in _ALL_IPPS.values()) / len(_ALL_IPPS)


def _ipp_midpoint(lat, lon):
    """The real IPP midpoint tid_doa.py itself uses -- see the
    correction note above."""
    return great_circle_midpoint(lat, lon, WWV_LAT, WWV_LON)


def _propagation_delay_s(lat, lon):
    """Time delay (seconds, can be negative) for this station's IPP
    midpoint under the TRUE_SPEED_MPS / TRUE_BEARING_FROM_DEG plane
    wave. Projects into local east/north metres exactly the way
    tid_doa.py's own DOA fit does -- centred on the array centroid,
    using its azimuthal-equidistant projection -- so the delays baked
    into this synthetic data are consistent with the same coordinate
    frame the real solver will use to recover them."""
    import math
    ipp_lat, ipp_lon = _ipp_midpoint(lat, lon)
    x_m, y_m = latlon_to_local_xy(ipp_lat, ipp_lon, _CENTROID_LAT, _CENTROID_LON)

    bearing_toward_deg = (TRUE_BEARING_FROM_DEG + 180.0) % 360.0
    dx = math.sin(math.radians(bearing_toward_deg))  # +east component
    dy = math.cos(math.radians(bearing_toward_deg))  # +north component

    dist_along_travel_m = x_m * dx + y_m * dy
    return dist_along_travel_m / TRUE_SPEED_MPS


def _html(body):
    return f"<html><body>{body}</body></html>".encode("utf-8")


def _latlon_to_grid(lat, lon):
    """Standard 6-character Maidenhead locator. Verified against the
    well-known ARRL HQ reference point (41.714775,-72.727260 ->
    FN31pr) before use -- two of the four hand-typed grids already in
    FAKE_STATIONS above don't actually match what this computes for
    their own coordinates (approximate/illustrative, not computed),
    confirmed harmless since grid squares here are cosmetic display
    only, never used in any actual physics."""
    lon2 = lon + 180
    lat2 = lat + 90
    field_lon = int(lon2 // 20)
    field_lat = int(lat2 // 10)
    square_lon = int((lon2 % 20) // 2)
    square_lat = int((lat2 % 10) // 1)
    subsq_lon = int(((lon2 % 20) % 2) / (2 / 24))
    subsq_lat = int(((lat2 % 10) % 1) / (1 / 24))
    return (chr(ord("A") + field_lon) + chr(ord("A") + field_lat) +
            str(square_lon) + str(square_lat) +
            chr(ord("a") + subsq_lon) + chr(ord("a") + subsq_lat))


SCENARIO_SCRATCH_ROOT = TOOLS_DIR / "synthetic_tests" / "events"
# Same output-root convention run_tests.py itself already uses (see
# its own --output-root default) -- means a scenario already generated
# by running the real test suite is reused here too, and vice versa,
# rather than each maintaining a separate cache of the same data.

SCENARIO_NAME = None
SCENARIO_EVENT_DIR = None
SCENARIO_GROUND_TRUTH = None

# Six scenarios curated out of test_conditions.py's full 30, chosen to
# cover distinct dimensions rather than exhaustively sweep every
# parameter (most of the other 24 are speed/azimuth/period/SNR sweeps
# around these same core ideas -- valuable for the real automated test
# suite's statistical coverage, redundant for a hands-on demo). Each
# one earns its place for a different reason:
RECOMMENDED_SCENARIOS = [
    "nominal",         # clean baseline -- success case, the reference point
    "slow_tid_alias",  # FAILURE mode 1: aliasing -- lag exceeds T/2
    "very_low_snr",    # FAILURE mode 2: weak signal -- a different kind
                       # of failure than aliasing, same expect_pass=False
    "mixed_4stn",      # 4-station array -- not hardcoded to always-3
    "conus_5stn",      # 5-station array, ground truth matches this
                       # project's own real 19 Jan 2026 reference event
    "two_wave",        # two genuinely superimposed TIDs -- the richest
                       # part of the signal model
]


def list_scenarios(show_all=False):
    """Print scenario names and a one-line description each. Shows
    just the 6 curated RECOMMENDED_SCENARIOS by default -- all 30 of
    test_conditions.py's conditions is too many for a hands-on demo
    where the point is showing a few clearly different *kinds* of
    behaviour, not exhaustively sweeping every parameter combination
    (most of the other 24 are speed/azimuth/period/SNR sweeps around
    the same core ideas). --list-scenarios --all shows the complete
    list for anyone who wants a specific one of the other 24."""
    if not _HAVE_TEST_CONDITIONS:
        print(f"Could not import test_conditions.py: "
              f"{_TEST_CONDITIONS_IMPORT_ERROR}")
        return
    by_name = {tc[0]: tc for tc in TEST_CONDITIONS}
    if show_all:
        names = [tc[0] for tc in TEST_CONDITIONS]
        print(f"All {len(names)} scenarios available "
              f"(--list-scenarios with no --all shows just the 6 "
              f"recommended for this purpose):\n")
    else:
        names = RECOMMENDED_SCENARIOS
        print(f"{len(names)} scenarios recommended for this purpose "
              f"(of {len(TEST_CONDITIONS)} total -- see --list-scenarios "
              f"--all for the rest):\n")
    print(f"{'Name':22s} {'Speed':>6s} {'Az':>4s} {'Per(m)':>7s} "
          f"{'Array':20s} {'Pass?':5s}  Notes")
    print("-" * 115)
    for name in names:
        _, speed, az, period, amp, snr, noise, array, expect_pass, notes = by_name[name]
        print(f"{name:22s} {speed:6d} {az:4d} {period:7d} "
              f"{array:20s} {str(expect_pass):5s}  {notes[:42]}")


def _load_scenario(name):
    """Generate (or reuse a cached) full synthetic_tests/ event for
    the named test condition, and build a FAKE_STATIONS-shaped dict
    from its real station array. Deliberately calls generate_event()
    itself rather than re-implementing test_conditions.py's own
    per-test special-casing (two_wave, period_chirp, eregion, etc.) a
    second time here -- any condition added to that file in the
    future works through this server automatically, with nothing to
    update in this file to match.

    Public station IDs and internal form IDs use a distinct 91xxx/91xx
    block (S991001+, matching the S900001-4 default block's own 7-
    character format) specifically so a scenario's stations can never
    collide with the classic 4-station default set, even though only
    one or the other is ever actually active in a given server run."""
    if not _HAVE_TEST_CONDITIONS:
        sys.exit(f"Could not import test_conditions.py: "
                 f"{_TEST_CONDITIONS_IMPORT_ERROR}")
    if not _HAVE_SYNTH:
        sys.exit(f"Could not import synthetic_drf.py: "
                 f"{_SYNTH_IMPORT_ERROR}")
    names = [tc[0] for tc in TEST_CONDITIONS]
    if name not in names:
        sys.exit(f"Unknown scenario {name!r}. Run with --list-scenarios "
                 f"to see all {len(names)} available.")

    SCENARIO_SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Generating synthetic scenario {name!r} "
          f"(reused from cache if already generated -- this can take "
          f"anywhere from a few seconds to over a minute the first "
          f"time, longer for scenarios with more stations or a longer "
          f"duration; please let it finish rather than interrupting -- "
          f"found live: killing this partway through leaves a broken, "
          f"partially-written cache that fails every future attempt to "
          f"generate the same scenario until the stale directory under "
          f"synthetic_tests/events/ is deleted by hand)...")
    event_dir, ground_truth = generate_event(name, str(SCENARIO_SCRATCH_ROOT))

    fake_stations = {}
    for i, stn in enumerate(ground_truth["stations"]):
        form_id = f"91{i:03d}"
        public_sid = f"S9{91001 + i:05d}"
        grid = _latlon_to_grid(stn["lat"], stn["lon"])
        fake_stations[form_id] = (stn["name"], public_sid, grid,
                                   stn["lat"], stn["lon"])
    return fake_stations, ground_truth, event_dir


def _zip_scenario_station_dir(nickname, event_dir):
    """Zip an already-generated (by generate_event(), at server
    startup) station directory for scenario mode, renaming its
    top-level folder to nickname.lower() when packed -- matches the
    lowercase-directory convention download_companions.py/
    tid_workflow.py expect everywhere else, the same rename
    _build_fake_drf_zip() already does for the classic default mode."""
    src = Path(event_dir) / nickname / "ch0"
    if not src.is_dir():
        raise FileNotFoundError(
            f"Scenario station directory not found: {src} -- was "
            f"generate_event() actually run for this scenario?")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in src.rglob("*"):
            if p.is_file():
                rel = Path(nickname.lower()) / "ch0" / p.relative_to(src)
                zf.write(p, rel)
    return buf.getvalue()


def _station_dropdown_html():
    opts = "".join(
        f'<option value="{fid}">{nick}</option>'
        for fid, (nick, sid, grid, lat, lon) in FAKE_STATIONS.items()
    )
    return _html(f'<form><select name="station">{opts}</select></form>')


def _stations_table_html():
    rows = "".join(
        f"<tr><td>{sid}</td><td>user</td><td>{nick}</td>"
        f"<td>{grid}</td><td>100</td><td>active</td></tr>"
        for fid, (nick, sid, grid, lat, lon) in FAKE_STATIONS.items()
    )
    # Deliberately no "next" link -- all 4 fake stations fit on one
    # page, so both scripts' pagination loops stop here on their own
    # (they check for an <a> containing "next", case-insensitive).
    return _html(f"<table>{rows}</table>")


def _obs_row_html(nick, obs_id):
    """One row matching find_obs_for_station's exact td-index reads:
    tds[1]=freq, tds[2]=<a>station</a>, tds[3]=instrument, tds[4]=size,
    tds[5]=<a href=.../select_download_range/ID>filename</a>,
    tds[7]=start_utc, tds[8]=end_utc. tds[0] and tds[6] are unused
    filler -- 9 <td> cells minimum, matching len(tds) < 9 check.

    Filename MUST match find_event_stations.py's own DRF_FILENAME_RE
    (r"^OBS\\d{4}-\\d{2}-\\d{2}T\\d{2}[-:]\\d{2}(\\.zip)?$") or it gets
    classified as "Unknown filename pattern" and silently excluded --
    caught by actually running the real script against this mock
    rather than assuming any 'OBS...zip'-shaped name would do."""
    start_utc = f"{TEST_DATE} 00:00:00"
    end_utc = f"{TEST_DATE} 23:59:59"
    filename = f"OBS{TEST_DATE}T00-00.zip"
    return (
        "<tr>"
        "<td>row</td>"
        "<td>10.000</td>"
        f"<td><a href='#'>{nick}</a></td>"
        "<td>GRAPE1</td>"
        "<td>12.3</td>"
        f"<td><a href='/observations/select_download_range/{obs_id}'>"
        f"{filename}</a></td>"
        "<td>-</td>"
        f"<td>{start_utc}</td>"
        f"<td>{end_utc}</td>"
        "</tr>"
    )


def _obs_list_html(form_id, page):
    if page != 1 or form_id not in FAKE_STATIONS:
        return _html("<table></table>")  # empty -> pagination stops
    nick = FAKE_STATIONS[form_id][0]
    obs_id = form_id  # reuse form_id as a stand-in observation id
    return _html(f"<table>{_obs_row_html(nick, obs_id)}</table>")


def _build_fake_drf_zip(nickname, lat, lon, start_date, end_date):
    """Generate a small, genuinely valid DRF dataset with
    write_station_drf() and zip it up. A full hour at 10 sps (36000
    complex samples) -- matches write_station_drf's own 1-hour
    subdir/file cadence exactly, so the declared DRF bounds and the
    actual written samples agree.

    Real bug found live: an earlier version of this used duration_s=600
    (10 minutes) inside a block whose *declared* bounds still span a
    full hour (write_station_drf's subdir_cadence_secs=3600 is fixed,
    independent of how many samples are actually written). Any read
    across the full declared hour -- exactly what tid_workflow.py's
    Step 2 full-day spectrogram does -- then spans 50 minutes of
    nothing. That's not a gap digital_rf raises an error on; it reads
    back as usable-looking but near-zero data, which dominates the
    plot's automatic color-scale normalization (50 real minutes of
    near-zero at 83% of the window vs. 10 minutes of real signal) and
    collapses the colorbar to a degenerate range -- confirmed directly:
    the resulting spectrogram showed a -0.1 to 0.1 dB colorbar and a
    solid black/white split at the 10-minute mark, both symptoms of
    this rather than a real drf_spectrogram.py bug (a separate, actual
    bug was also found and fixed in that file the same session -- see
    its own v1.5.0 changelog entry -- but fixing that alone did not
    resolve this, confirmed by testing them independently). Writing a
    full real hour eliminates the mismatch entirely."""
    import numpy as np

    sample_rate_hz = 10.0
    duration_s = 3600  # 1 hour -- matches write_station_drf's own cadence
    d = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_unix_s = d.timestamp()
    n = int(duration_s * sample_rate_hz)
    t = np.arange(n) / sample_rate_hz

    # Same waveform shape at every station, but time-shifted by this
    # station's real propagation delay under the assumed plane wave
    # (TRUE_SPEED_MPS / TRUE_BEARING_FROM_DEG) -- see the ground-truth
    # note above _ipp_midpoint(). A station further along the wave's
    # travel direction sees the same pattern later, exactly like a
    # real TID crossing the array; a naive earlier version of this
    # gave every station the identical, undelayed t, so cross-
    # correlation always found ~0 lag regardless of real separation --
    # confirmed live: that produced a phase-speed result in the tens
    # of millions of m/s (near-zero lag over real distance implies
    # near-infinite speed), correctly flagged by tid_doa.py's own
    # diagnostics as unphysical, but not actually testing the DOA math
    # against a known answer the way this does.
    delay_s = _propagation_delay_s(lat, lon)
    t_signal = t - delay_s

    doppler_hz = 0.3 * np.sin(2 * np.pi * t_signal / TRUE_PERIOD_S)
    phase = 2 * np.pi * np.cumsum(doppler_hz) / sample_rate_hz
    iq = (0.1 * np.exp(1j * phase)).astype(np.complex64)
    iq += (0.01 * (np.random.randn(n) + 1j * np.random.randn(n))).astype(np.complex64)

    with tempfile.TemporaryDirectory() as tmp:
        station = {"name": nickname.lower(), "lat": lat, "lon": lon}
        write_station_drf(
            tmp, station, iq, start_unix_s,
            sample_rate_hz=sample_rate_hz, f_carrier_hz=10_000_000.0,
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            root = Path(tmp)
            for p in root.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(root))
        return buf.getvalue()


class MockPSWSHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [mock-psws] {self.address_string()} - {fmt % args}")

    def _send(self, body, content_type="text/html", disposition=None):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path

        if path == "/observations/observation_list/":
            if "station" in qs:
                form_id = qs["station"][0]
                page = int(qs.get("page", ["1"])[0])
                self._send(_obs_list_html(form_id, page))
            else:
                self._send(_station_dropdown_html())
            return

        if path == "/stations/stations/":
            page = int(qs.get("page", ["1"])[0])
            if page == 1:
                self._send(_stations_table_html())
            else:
                self._send(_html("<table></table>"))
            return

        if path == "/observations/downloadapi/":
            if not _HAVE_SYNTH:
                self._send_error_json(
                    500,
                    f"synthetic_drf.py import failed: {_SYNTH_IMPORT_ERROR}\n"
                    f"(is digital_rf installed? see check_install.py)",
                )
                return
            sid = qs.get("station_id", [None])[0]
            start_date = qs.get("start_date", [None])[0]
            end_date = qs.get("end_date", [None])[0]
            form_id = SID_TO_FORM_ID.get(sid)
            if not form_id:
                self._send_error_json(404, f"Unknown station_id {sid!r}")
                return
            nick, real_sid, grid, lat, lon = FAKE_STATIONS[form_id]
            try:
                if SCENARIO_EVENT_DIR is not None:
                    zip_bytes = _zip_scenario_station_dir(nick, SCENARIO_EVENT_DIR)
                else:
                    zip_bytes = _build_fake_drf_zip(
                        nick, lat, lon, start_date or TEST_DATE,
                        end_date or TEST_DATE,
                    )
            except Exception as e:
                self._send_error_json(500, f"synthetic DRF generation failed: {e}")
                return
            self._send(
                zip_bytes, content_type="application/zip",
                disposition=f'attachment; filename="{nick}_OBS.zip"',
            )
            return

        self._send_error_json(404, f"mock server: no handler for {path}")


def main():
    global FAKE_STATIONS, NICK_TO_FORM_ID, SID_TO_FORM_ID, TEST_DATE
    global TRUE_SPEED_MPS, TRUE_BEARING_FROM_DEG, TRUE_PERIOD_S
    global SCENARIO_NAME, SCENARIO_EVENT_DIR, SCENARIO_GROUND_TRUTH

    ap = argparse.ArgumentParser(description=__doc__.split("USAGE")[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--scenario", metavar="NAME", default=None,
                     help="Serve one of synthetic_tests/'s 29 test "
                          "conditions (real station arrays, known ground "
                          "truth, optional noise/enhancement effects) "
                          "instead of the classic 4-station default. "
                          "See --list-scenarios.")
    ap.add_argument("--list-scenarios", action="store_true",
                     help="Print available --scenario names and exit. "
                          "Shows the 6 recommended by default -- see --all.")
    ap.add_argument("--all", action="store_true",
                     help="With --list-scenarios, show all 30 conditions "
                          "instead of just the 6 recommended.")
    args = ap.parse_args()

    if args.list_scenarios:
        list_scenarios(show_all=args.all)
        return

    if not _HAVE_SYNTH:
        print(f"WARNING: could not import synthetic_drf.py "
              f"({_SYNTH_IMPORT_ERROR}) -- discovery endpoints will work, "
              f"but the download endpoint will return HTTP 500 until "
              f"this is fixed (check digital_rf is installed).")

    if args.scenario:
        FAKE_STATIONS, SCENARIO_GROUND_TRUTH, SCENARIO_EVENT_DIR = \
            _load_scenario(args.scenario)
        NICK_TO_FORM_ID = {v[0]: k for k, v in FAKE_STATIONS.items()}
        SID_TO_FORM_ID = {v[1]: k for k, v in FAKE_STATIONS.items()}
        SCENARIO_NAME = args.scenario
        gt = SCENARIO_GROUND_TRUTH
        TEST_DATE = gt["event_start_utc"][:10]
        TRUE_SPEED_MPS = gt["true_speed_m_s"]
        TRUE_BEARING_FROM_DEG = gt["true_az_from_deg"]
        TRUE_PERIOD_S = gt["true_period_min"] * 60.0

        print(f"\nMock PSWS server -- serving synthetic_tests/ scenario "
              f"{args.scenario!r}")
        print(f"Ground truth: {TRUE_SPEED_MPS:.0f} m/s, arriving from "
              f"{TRUE_BEARING_FROM_DEG:.0f}\u00b0 true bearing, "
              f"{gt['true_period_min']:.0f} min period, "
              f"{gt['snr_db']:.0f} dB SNR ({gt['noise_type']} noise) "
              f"-- tid_doa.py's result should land close to the speed/"
              f"bearing (some scenarios are deliberately alias/stress "
              f"tests: expect_pass={gt['expect_pass']}).")
        print(f"Fake stations: {', '.join(v[0] for v in FAKE_STATIONS.values())}")
        print(f"Test date: {TEST_DATE} (synthetic_tests/'s own fixed "
              f"epoch, verified directly against the actual timestamp -- "
              f"not the same as this project's real 19 January 2026 "
              f"reference event, so no collision risk with real "
              f"downloaded data for that date).")
    else:
        print(f"Mock PSWS server -- serving fake data for test date {TEST_DATE}")
        print(f"Ground truth: {TRUE_SPEED_MPS:.0f} m/s, arriving from "
              f"{TRUE_BEARING_FROM_DEG:.0f}\u00b0 true bearing "
              f"-- tid_doa.py's result should land close to this.")
        print(f"Fake stations: {', '.join(v[0] for v in FAKE_STATIONS.values())}")

    print(f"\nIn another terminal:")
    print(f"  export PSWS_BASE_URL=http://127.0.0.1:{args.port}")
    print(f"  python3 find_event_stations.py --date {TEST_DATE} "
          f"--my-lat 35.00 --my-lon -95.00 --my-call TESTKEY")
    print(f"\nListening on http://127.0.0.1:{args.port} -- Ctrl+C to stop\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), MockPSWSHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
