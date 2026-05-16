r"""
find_event_stations.py — locate companion HamSCI Grape DRF stations for a TID event


Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial public release covering the 19 Jan 2026 event analysis.

OVERVIEW
========
Given a UTC event date and your station's coordinates, this tool produces a
ranked shortlist of other HamSCI PSWS stations whose Digital RF (DRF) I/Q
observations on that date have useful midpoint geometry for cross-correlation
analysis of traveling ionospheric disturbances (TIDs).

WHY THIS IS NON-TRIVIAL
=======================
The PSWS observation portal (https://pswsnetwork.eng.ua.edu/) has several
quirks that prevent a simple date+frequency query from working:

  1. The global sort=-startDate ordering appears to use *upload* timestamp,
     not the observation's start_date. Late-uploaded data scatters across
     pages and cannot be found by scanning the date-sorted list.
     -> Workaround: query each station ID individually.

  2. The centerFrequency form filter does an exact-string match against the
     observation's center_freq field. Multi-subchannel WSPRdaemon stations
     record this as a comma-separated list ("10.000 MHz, 5.000 MHz, ...")
     which never matches "10.000".  Many older DRF observations leave the
     field blank entirely.
     -> Workaround: don't filter by frequency server-side; match
        client-side allowing "contains" and empty.

  3. The instrument field is free-text. The same hardware appears as
     "Grape 1 DRF", "Grape1", "Grape v1.12", "Grape55", "Grape66",
     "GRAPE1", "Node_56_Grape_DRF", "gnuGrape", "rx888", "RX888",
     "NW RX888", "WD-GRAPE" etc. Filtering by instrument name misses most
     stations.
     -> Workaround: classify by FILENAME pattern. DRF I/Q observations use
        OBS<date>T<time> (sometimes with .zip extension); Grape 1 Legacy
        CSVs use <date>Z_<node>_G1_<grid>_FRQ_WWV<freq>.csv.

  4. A single physical station may appear under multiple "station"
     dropdown entries (e.g. AB4EJ has 7: G1DRF, Grape2, G1test, -m, -rx888,
     -T1, etc.). Each registration uploads under one format.
     -> Workaround: dedupe candidates by grid square at the end.

  5. The per-station view is paginated 8 observations per page, with gaps
     for days the station didn't upload. To find Jan 19 from May, you may
     need 15-20 pages of history.
     -> --max-pages-per-station controls this; default 20.

  6. KA7OEI's actual callsign in metadata is KD7EFG. PSWS station nickname
     vs. callsign vs. DRF metadata are independent fields.
     -> The tool uses station ID consistently throughout.

OUTPUT
======
For each candidate companion, the tool reports:
  - Station nickname and grid square
  - Instrument label (informational only - actual format determined by
    filename pattern)
  - Path length WWV->receiver (paths under --min-path-km excluded;
    midpoints too close to WWV reflect at near-vertical incidence and
    aren't useful for TID work)
  - Midpoint separation from your station's midpoint
  - Bearing from your midpoint
  - Score (peak at ~500 km separation, falls off outside 100-1500 km)
  - PSWS observation ID for downloading

A bearing-gap analysis warns if the candidate spread leaves a wedge of
sky poorly observed.

RANKING
=======
Each candidate is scored on a single number between 0 and 1, computed
purely from the great-circle distance between the candidate's WWV-path
midpoint and YOUR WWV-path midpoint.

  score
   1.0 +              ___
       |             /   \___
       |            /        \____
       |           /              \____
       |          /                    \____
   0.0 +________ /                          \________
       +-------+----+----+----+----+----+----+----
      0      100   300  500  700  900 1100 1300 1500  km

  Below  100 km: score = 0   (too close; lag unmeasurable)
  100 to 500 km: rising      (sweet spot for typical MSTIDs)
       500 km:  score = 1.0  (peak)
  500 to 1500 km: falling    (wave may not be coherent over this distance)
  Above 1500 km: score = 0   (different ionosphere)

WHY DISTANCE MATTERS FOR TID TYPE
---------------------------------
The "best" baseline separation depends on the wave you're chasing.

  Type    Period       Speed       One wavelength    Best baseline
  ----    ------       -----       ---------------   -------------
  MSTID   15-60 min    150-300 m/s  150-1100 km     300-700 km
  LSTID   60-180 min   300-1000 m/s 1100-10800 km   700-1500 km
  Acoustic   3-10 min  500-1000 m/s  90-600 km        50-300 km
  gravity

You want baselines comparable to or somewhat smaller than the wave's
horizontal wavelength. Too short = lag is too small to measure. Too long
= the same wave is no longer recognizable at both stations (different
amplitude, phase, sometimes different period as it disperses).

The default score curve PEAKS AT 500 km, which is optimal for typical
medium-scale TIDs at mid-latitudes. This means:

  - MSTID hunts: trust the score; top candidates are well chosen
  - LSTID hunts: the score under-weights stations 700-1500 km away; you
    may want to lower --min-path-km or weigh longer baselines higher
  - Short-period acoustic-gravity wave studies: the score over-weights
    distant stations; you actually want very close pairs (100-300 km
    apart) which currently get low-to-mid scores

The "100 km minimum" is also period-dependent: for a 60-min wave at
200 m/s, even 100 km gives only a 30-second lag, which is hard to extract
from typical Doppler noise. For fast LSTIDs at 800 m/s, that same 100 km
baseline gives 2 minutes lag, which IS measurable.

WHAT THE SCORE DOES NOT CONSIDER
--------------------------------
  - Bearing. Direction is reported in a separate column. When picking
    3+ stations for direction-of-arrival, USE the bearing column to
    spread your array; don't just take top-N by score.
  - Path length to WWV (already filtered upstream).
  - Data quality (SNR, fading, RFI - check this AFTER downloading).
  - Latitude. High-latitude stations on 10 MHz fade at night.
  - Cross-station correlation (only knowable after analysis).

PRACTICAL WORKFLOW
------------------
  1. Look at the top 5-10 candidates by score.
  2. Check bearing distribution. If they're all in one quadrant,
     deliberately add lower-score candidates from underrepresented
     azimuths.
  3. Download and verify SNR / continuity for your event window.
  4. Drop bad stations; re-run cross-correlation with what remains.

For non-MSTID work, consider customizing --min-path-km:
  --min-path-km 500   for low-frequency acoustic-gravity waves
  --min-path-km 900   for LSTID studies (move the inner cutoff outward)

USAGE
=====
    python find_event_stations.py --date 2026-01-19 \\
        --my-lat 32.94 --my-lon -97.21 --my-call N6RFM/5

OPTIONS
=======
    --frequency 10.000           Default 10.000.  Used for client-side
                                 contains-match against the freq column.
                                 Observations with empty freq column are
                                 kept (older DRF uploads omitted this).
    --min-path-km 700            Minimum WWV->receiver distance.  Stations
                                 closer than this have midpoints too near
                                 WWV for clean F-region reflection.
    --max-pages-per-station 20   How many pages of history to scan per
                                 station.  Each page is 8 observations.
                                 Increase if the target date is many
                                 months old.
    --include-non-target-freq    By default we keep observations where
                                 freq matches OR is empty.  This flag
                                 *also* keeps observations whose instrument
                                 string suggests a different frequency
                                 (e.g. instrument="DRF_5_MHz"); they will
                                 be flagged in the output but not removed.
    --no-cache                   Bypass the .psws_station_cache.json
                                 cache and refresh the station directory.
    --top 25                     How many candidates to show.

The tool caches the PSWS station ID -> nickname mapping in
.psws_station_cache.json (one-week TTL).
"""

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
PSWS_BASE = "https://pswsnetwork.eng.ua.edu"
OBS_PATH  = "/observations/observation_list/"
STN_PATH  = "/stations/stations/"

WWV_LAT, WWV_LON = 40.6776, -105.0405   # WWV transmitter, Fort Collins CO
EARTH_R_KM = 6371.0

UA = "Mozilla/5.0"

CACHE_FILE = ".psws_station_cache.json"
CACHE_MAX_AGE_DAYS = 7


# ----------------------------------------------------------------------------
# Geometry: spherical-Earth helpers
# ----------------------------------------------------------------------------
def to_rad(d): return d * math.pi / 180.0
def to_deg(r): return r * 180.0 / math.pi


def grid_to_latlon(grid):
    """Maidenhead grid square -> (lat, lon) at center of the square."""
    g = grid.strip()
    if len(g) < 4:
        return None
    try:
        A = ord(g[0].upper()) - ord('A')
        B = ord(g[1].upper()) - ord('A')
        C = int(g[2]); D = int(g[3])
        lon = -180 + A*20 + C*2
        lat = -90 + B*10 + D*1
        if len(g) >= 6:
            E = ord(g[4].lower()) - ord('a')
            F = ord(g[5].lower()) - ord('a')
            lon += E*(2/24) + (1/24)
            lat += F*(1/24) + (0.5/24)
        else:
            lon += 1.0; lat += 0.5
        return lat, lon
    except Exception:
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km."""
    f1, f2 = to_rad(lat1), to_rad(lat2)
    df = to_rad(lat2 - lat1)
    dl = to_rad(lon2 - lon1)
    a = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def great_circle_midpoint(lat1, lon1, lat2, lon2):
    """Geographic midpoint along the great-circle arc."""
    f1, l1 = to_rad(lat1), to_rad(lon1)
    f2, l2 = to_rad(lat2), to_rad(lon2)
    dl = l2 - l1
    bx = math.cos(f2)*math.cos(dl)
    by = math.cos(f2)*math.sin(dl)
    f3 = math.atan2(math.sin(f1)+math.sin(f2),
                    math.sqrt((math.cos(f1)+bx)**2 + by**2))
    l3 = l1 + math.atan2(by, math.cos(f1)+bx)
    return to_deg(f3), (to_deg(l3) + 540) % 360 - 180


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, in degrees true."""
    f1, f2 = to_rad(lat1), to_rad(lat2)
    dl = to_rad(lon2 - lon1)
    y = math.sin(dl)*math.cos(f2)
    x = math.cos(f1)*math.sin(f2) - math.sin(f1)*math.cos(f2)*math.cos(dl)
    return (to_deg(math.atan2(y, x)) + 360) % 360


def separation_score(km):
    """Companion-quality score, peaks at 500 km midpoint separation.

    Below 100 km: too close to measure a meaningful time lag.
    Above 1500 km: probably not the same wave; ionosphere has changed.
    """
    if km < 100 or km > 1500:
        return 0.0
    if km <= 500:
        return (km - 100) / 400
    return max(0, (1500 - km) / 1000)


# ----------------------------------------------------------------------------
# Filename classification
# ----------------------------------------------------------------------------
# DRF I/Q observations use names like 'OBS2026-01-19T00-00' (no extension)
# or 'OBS2026-01-19T00:00.zip' (newer compressed packaging).
DRF_FILENAME_RE = re.compile(
    r"^OBS\d{4}-\d{2}-\d{2}T\d{2}[-:]\d{2}(\.zip)?$"
)

# Grape 1 Legacy uses CSV files of Doppler-vs-time only (no raw I/Q).
LEGACY_CSV_RE = re.compile(r"\.csv$", re.IGNORECASE)


def is_drf_iq_file(filename):
    """True if this filename represents a Digital RF I/Q observation."""
    return bool(DRF_FILENAME_RE.match(filename.strip()))


def is_legacy_csv_file(filename):
    """True if this filename is a Grape 1 Legacy CSV (Doppler+amp only)."""
    return bool(LEGACY_CSV_RE.search(filename.strip()))


# ----------------------------------------------------------------------------
# Frequency-related helpers
# ----------------------------------------------------------------------------
# Some operators name their instrument with a frequency hint (e.g.
# "DRF_5_MHz", "WWV15"). If that hint conflicts with the requested
# frequency we flag the observation as suspect rather than dropping it.
FREQ_IN_INSTRUMENT_RE = re.compile(r"(?<!\d)(\d{1,2})\s*MHz", re.IGNORECASE)

EMPTY_FREQ_TOKENS = {"", "\u2014", "-", "--", "n/a", "none"}


def instrument_freq_hint_mhz(instrument):
    """Try to infer a frequency from the instrument name. Returns int MHz
    or None if no clear hint."""
    m = FREQ_IN_INSTRUMENT_RE.search(instrument)
    if not m:
        # Also handle bare-number patterns like "WWV15" or "DRF_5"
        m2 = re.search(r"\b(WWV|DRF[_\-]?)(\d{1,2})\b", instrument, re.IGNORECASE)
        if m2:
            return int(m2.group(2))
        return None
    return int(m.group(1))


def freq_compatible(observation, target_freq_str):
    """Returns ('match', 'empty', 'mismatch') describing how this
    observation's freq column relates to the requested frequency."""
    cf = observation.center_freq_text.strip().lower()
    if cf in EMPTY_FREQ_TOKENS:
        return "empty"
    if target_freq_str in cf:
        return "match"
    return "mismatch"


# ----------------------------------------------------------------------------
# Station directory: pull the ID -> nickname/grid mapping
# ----------------------------------------------------------------------------
def get_station_list(session, use_cache=True):
    """Build a dict mapping station_id -> {nickname, grid, lat, lon}.

    Combines two sources:
      - The 'station' dropdown on the observation form gives ID -> nickname.
      - The /stations/stations/ table gives nickname -> grid square.
    The result is cached to .psws_station_cache.json for one week.
    """
    if use_cache and os.path.exists(CACHE_FILE):
        try:
            age_days = (time.time() - os.path.getmtime(CACHE_FILE)) / 86400
            if age_days < CACHE_MAX_AGE_DAYS:
                with open(CACHE_FILE) as f:
                    data = json.load(f)
                print(f"  Using cached station list "
                      f"({age_days:.1f} days old, {len(data)} stations)")
                return data
        except Exception:
            pass

    print("  Fetching station dropdown from observation form...")
    r = session.get(PSWS_BASE + OBS_PATH, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    stations = {}
    for sel in soup.find_all("select"):
        if sel.get("name") == "station":
            for opt in sel.find_all("option"):
                val = opt.get("value", "").strip()
                txt = opt.get_text(strip=True)
                if val and val.isdigit():
                    stations[val] = txt
            break

    print("  Fetching station directory for grid squares...")
    grid_by_nick = {}
    for page in range(1, 80):
        r = session.get(PSWS_BASE + STN_PATH,
                        params={"page": page}, timeout=30)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table:
            break
        rows = 0
        for tr in table.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) < 6:
                continue
            sid_str, user, nick, grid, elev, status = tds[:6]
            if not re.match(r"^[NS]\d+$", sid_str):
                continue
            grid_by_nick[nick] = grid
            rows += 1
        if rows == 0:
            break
        if not soup.find("a", string=re.compile(r"next", re.I)):
            break
        time.sleep(0.15)

    out = {}
    for sid, nick in stations.items():
        grid = grid_by_nick.get(nick)
        ll = grid_to_latlon(grid) if grid else None
        out[sid] = {
            "id": sid,
            "nickname": nick,
            "grid": grid,
            "lat": ll[0] if ll else None,
            "lon": ll[1] if ll else None,
        }

    with open(CACHE_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  cached {len(out)} stations to {CACHE_FILE}")
    return out


# ----------------------------------------------------------------------------
# Find observations for one station on the target date
# ----------------------------------------------------------------------------
@dataclass
class Observation:
    obs_id: str
    station_id: str
    station_nickname: str
    instrument: str
    center_freq_text: str
    file_name: str
    size_mb: float
    start_utc: str
    end_utc: str


def find_obs_for_station(session, station_id, target_date_str, max_pages=20):
    """Return all observations for one station starting on target_date_str.

    Paginates the per-station observation list (sort=-startDate) and stops
    once we go past the target date. Returns possibly-empty list.
    """
    found = []
    for page in range(1, max_pages + 1):
        try:
            r = session.get(
                PSWS_BASE + OBS_PATH,
                params={"station": station_id,
                        "sort": "-startDate",
                        "page": page},
                timeout=20,
            )
        except Exception:
            return found
        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("tr")
        page_obs = 0
        oldest_on_page = None
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 9:
                continue
            page_obs += 1
            start_utc = tds[7].get_text(strip=True)
            if start_utc and (oldest_on_page is None
                              or start_utc < oldest_on_page):
                oldest_on_page = start_utc
            if start_utc.startswith(target_date_str):
                end_utc = tds[8].get_text(strip=True)
                inst = tds[3].get_text(strip=True)
                size_text = tds[4].get_text(strip=True).replace(",", "")
                try:
                    size_mb = float(size_text)
                except ValueError:
                    size_mb = 0.0
                cf_text = tds[1].get_text(strip=True)
                file_a = tds[5].find("a")
                fname = file_a.get_text(strip=True) if file_a else ""
                href = file_a.get("href", "") if file_a else ""
                m = re.search(r"/select_download_range/(\d+)", href)
                obs_id = m.group(1) if m else "?"
                station_a = tds[2].find("a")
                station_name = (station_a.get_text(strip=True)
                                if station_a else "")
                found.append(Observation(
                    obs_id=obs_id, station_id=station_id,
                    station_nickname=station_name,
                    instrument=inst, center_freq_text=cf_text,
                    file_name=fname, size_mb=size_mb,
                    start_utc=start_utc, end_utc=end_utc,
                ))
        if page_obs == 0:
            break
        # Stop once page contains dates older than the target
        if oldest_on_page and oldest_on_page < target_date_str:
            break
    return found


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring at the top of the script for full details.",
    )
    ap.add_argument("--date", required=True,
                    help="Event date in YYYY-MM-DD UTC, e.g. 2026-01-19")
    ap.add_argument("--my-lat", type=float, required=True,
                    help="Your station's latitude in decimal degrees")
    ap.add_argument("--my-lon", type=float, required=True,
                    help="Your station's longitude in decimal degrees")
    ap.add_argument("--my-call", required=True,
                    help="Your station's PSWS nickname (will be "
                         "excluded from the candidate list)")
    ap.add_argument("--frequency", default="10.000",
                    help="WWV frequency to match against the observation's "
                         "centerFrequency cell, e.g. '10.000' or '5.000'. "
                         "Default: 10.000")
    ap.add_argument("--min-path-km", type=float, default=700,
                    help="Minimum WWV-to-receiver path length. Stations "
                         "closer than this produce midpoints near the "
                         "transmitter, not useful for F-region TID work. "
                         "Default: 700")
    ap.add_argument("--max-pages-per-station", type=int, default=20,
                    help="How many pages of per-station history to scan. "
                         "Each page is 8 observations. Increase if the "
                         "target date is more than ~6 months ago. "
                         "Default: 20")
    ap.add_argument("--include-non-target-freq", action="store_true",
                    help="Also include observations whose instrument "
                         "name suggests a different frequency (these are "
                         "flagged with [!freq] in the output)")
    ap.add_argument("--no-cache", action="store_true",
                    help="Bypass the .psws_station_cache.json cache and "
                         "refresh the station directory from PSWS")
    ap.add_argument("--top", type=int, default=25,
                    help="Maximum number of candidates to display. "
                         "Default: 25")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    print(f"Looking for observations on {args.date} at {args.frequency} MHz\n")

    print(f"Step 1: gather station directory")
    stations = get_station_list(session, use_cache=not args.no_cache)
    print(f"  total registered stations: {len(stations)}")

    print(f"\nStep 2: query each station for {args.date} observations")
    all_obs = []
    n_with_obs = 0
    for i, (sid, info) in enumerate(stations.items(), 1):
        if i % 20 == 0:
            print(f"  ...checked {i}/{len(stations)} stations, "
                  f"{n_with_obs} have data on {args.date}")
        obs_list = find_obs_for_station(
            session, sid, args.date,
            max_pages=args.max_pages_per_station)
        if obs_list:
            n_with_obs += 1
            all_obs.extend(obs_list)
        time.sleep(0.05)

    print(f"\n=== {len(all_obs)} total observations from "
          f"{n_with_obs} stations on {args.date} ===")

    # ----- Frequency compatibility classification -----
    target_freq = args.frequency.strip()
    target_freq_mhz = int(float(target_freq))
    matched, empty, mismatched = [], [], []
    for o in all_obs:
        status = freq_compatible(o, target_freq)
        if status == "match":
            matched.append(o)
        elif status == "empty":
            empty.append(o)
        else:
            mismatched.append(o)
    print(f"  Freq column matches '{target_freq} MHz': {len(matched)}")
    print(f"  Freq column empty (older DRF):           {len(empty)}")
    print(f"  Freq column shows a different freq:      {len(mismatched)}")

    # Decide which observations to keep
    kept = matched + empty
    if args.include_non_target_freq:
        kept = kept + mismatched

    # ----- Filename classification -----
    drf_obs = [o for o in kept if is_drf_iq_file(o.file_name)]
    legacy_obs = [o for o in kept if is_legacy_csv_file(o.file_name)]
    other_obs = [o for o in kept
                 if not is_drf_iq_file(o.file_name)
                 and not is_legacy_csv_file(o.file_name)]

    print(f"\nClassified by filename:")
    print(f"  DRF I/Q (usable, OBS<date> or OBS<date>.zip): {len(drf_obs)}")
    print(f"  Grape 1 Legacy CSV (no raw I/Q):              {len(legacy_obs)}")
    if other_obs:
        print(f"  Unknown filename pattern:                     {len(other_obs)}")
        for o in other_obs[:3]:
            print(f"    e.g. {o.file_name!r}")

    if not drf_obs:
        print("\nNo DRF I/Q observations found. Cannot proceed.")
        return

    # ----- Geometric ranking -----
    my_mid = great_circle_midpoint(WWV_LAT, WWV_LON, args.my_lat, args.my_lon)
    print(f"\nYour station: {args.my_call}  "
          f"({args.my_lat:.3f}, {args.my_lon:.3f})")
    print(f"Your WWV-path midpoint: ({my_mid[0]:.2f}, {my_mid[1]:.2f})\n")

    candidates = []
    excluded_near_wwv = []
    for obs in drf_obs:
        info = stations.get(obs.station_id)
        if not info or info["lat"] is None:
            continue
        # Skip magnetometer-only stations — they record geomagnetic data,
        # not radio signals, so they cannot contribute to Doppler analysis.
        inst_lc = (obs.instrument or "").lower()
        if any(p in inst_lc for p in ("rm3100", "magnetome", "gmag")):
            continue
        # Reference station is included in the table (as a marked entry),
        # not silently dropped. The is_me flag is propagated through the
        # record so the output stage can format it specially.
        is_me = (obs.station_nickname == args.my_call)
        lat, lon = info["lat"], info["lon"]
        path_km = haversine_km(WWV_LAT, WWV_LON, lat, lon)
        mid = great_circle_midpoint(WWV_LAT, WWV_LON, lat, lon)
        sep_km = haversine_km(my_mid[0], my_mid[1], mid[0], mid[1])
        brg = bearing_deg(my_mid[0], my_mid[1], mid[0], mid[1])
        score = separation_score(sep_km)
        # Frequency-hint flag: does instrument name suggest non-target freq?
        hint = instrument_freq_hint_mhz(obs.instrument)
        freq_flag = ""
        if hint is not None and hint != target_freq_mhz:
            freq_flag = f"[!{hint}MHz]"
        record = {
            "obs": obs, "info": info,
            "path_km": path_km, "sep_km": sep_km,
            "bearing": brg, "score": score,
            "freq_flag": freq_flag,
            "is_me": is_me,
        }
        if path_km < args.min_path_km:
            excluded_near_wwv.append(record)
        else:
            candidates.append(record)

    # Hold the reference station aside so it always appears at the top of
    # the table — its midpoint separation from itself is zero, which would
    # otherwise put it at the bottom of the score ordering.
    me_records = [c for c in candidates if c["is_me"]]
    other_records = [c for c in candidates if not c["is_me"]]

    # Dedupe non-reference candidates by grid square (one operator can have
    # multiple registrations at the same physical location)
    by_grid = {}
    for c in other_records:
        g = c["info"]["grid"]
        if g not in by_grid or c["score"] > by_grid[g]["score"]:
            by_grid[g] = c
    other_records = list(by_grid.values())
    other_records.sort(key=lambda r: r["score"], reverse=True)

    # Reference station first (if it has DRF data on this date), then the
    # other candidates by score.
    candidates = me_records + other_records

    # ----- Output -----
    print(f"Candidate DRF I/Q companions on {args.date} "
          f"(path >= {args.min_path_km} km):")
    print(f"  Flags: [!NN MHz] = instrument name suggests a different "
          f"frequency than {target_freq_mhz} MHz")
    print()
    print(f"{'Rank':<4} {'Station':<24} {'Grid':<7} {'Instrument':<16} "
          f"{'Path':>5} {'MidSep':>6} {'Brg':>4} {'Score':>5}  "
          f"{'Flag/Note':<14} ObsID")
    print("-" * 109)
    rank_counter = 0
    for r in candidates[:args.top]:
        o = r["obs"]
        if r.get("is_me"):
            rank_str = "*"
            score_str = "  —  "
            tail_flag = "(your station)"
        else:
            rank_counter += 1
            rank_str = str(rank_counter)
            score_str = f"{r['score']:>5.2f}"
            tail_flag = r["freq_flag"]
        print(f"{rank_str:<4} {o.station_nickname[:24]:<24} "
              f"{r['info']['grid'] or '?':<7} "
              f"{o.instrument[:16]:<16} "
              f"{r['path_km']:>4.0f}km {r['sep_km']:>5.0f}km "
              f"{r['bearing']:>3.0f}° {score_str}  "
              f"{tail_flag:<14} {o.obs_id}")

    if excluded_near_wwv:
        print(f"\nExcluded (path < {args.min_path_km} km, midpoint too close "
              f"to WWV):")
        for r in excluded_near_wwv:
            o = r["obs"]
            print(f"   {o.station_nickname} ({r['info']['grid']}): "
                  f"path {r['path_km']:.0f} km   ObsID {o.obs_id}")

    if len(candidates) >= 2:
        top = candidates[:min(args.top, 6)]
        bs = sorted([r["bearing"] for r in top])
        bs_wrap = bs + [bs[0] + 360]
        gaps = [bs_wrap[i+1] - bs_wrap[i] for i in range(len(bs))]
        max_gap = max(gaps)
        # Find the center of the largest gap (azimuth that is
        # least-well-observed)
        gap_idx = gaps.index(max_gap)
        gap_center = (bs_wrap[gap_idx] + bs_wrap[gap_idx + 1]) / 2 % 360
        print(f"\nBearing coverage (top {len(top)}):")
        print(f"  Largest gap: {max_gap:.0f}° centered around "
              f"azimuth {gap_center:.0f}°")
        if max_gap > 180:
            print("  WARNING: gap > 180° — wave direction-of-arrival "
                  f"poorly constrained for azimuths near {gap_center:.0f}°")
        elif max_gap > 120:
            print(f"  Note: moderately uneven coverage; "
                  f"DOA errors will be larger for waves from "
                  f"~{gap_center:.0f}° azimuth")
        else:
            print("  Coverage is reasonably even across all azimuths.")

    print(f"\nDownload URL pattern:")
    print(f"  {PSWS_BASE}/observations/select_download_range/<ObsID>/")
    print("Notes:")
    print("  - Each download is roughly 30-50 MB (single-channel) or "
          "~3 GB (multi-subchannel WSPRdaemon)")
    print("  - Confirm the actual recording frequency by reading the DRF "
          "metadata after download (see drf_to_doppler.py docstring)")
    print("  - Flagged stations [!NN MHz] may have been recording a "
          "different frequency than expected")


if __name__ == "__main__":
    main()
