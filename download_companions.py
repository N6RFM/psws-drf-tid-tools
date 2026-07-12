#!/usr/bin/env python3
r"""
download_companions.py — download and organize companion HamSCI Grape DRF
station data from the PSWS network for psws-drf-tid-tools

Community add-on for psws-drf-tid-tools
(https://github.com/N6RFM/psws-drf-tid-tools)

Created by N6RFM with help from Claude AI.
Version: 1.2.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.2.0  A station hitting "no matching observations" with a
          --frequency filter applied (the expected, common case for
          multi-channel-num rx888/WSPRdaemon stations, whose
          comma-separated frequency field can never exact-match a bare
          value) used to just print a suggestion to manually re-run
          that one station without --frequency -- requiring the user
          to notice the failure and run a second command by hand.
          Raised directly: "the whole point of this workflow was to
          make this very easy and almost seamless." Now auto-retries
          automatically, in the same run, the moment this specific
          case is detected -- download_one() returns a new
          "NO_MATCH_WITH_FREQ" sentinel (distinct from a genuine
          failure) specifically so the caller can tell the difference
          and retry only when it's actually likely to help. Verified
          directly: mocked the API to return 404 for a
          frequency-filtered request and 200 for the same request
          without one, confirmed the sentinel is returned correctly
          and the retry succeeds.
  v1.1.0  Reworded "subchannel" references to "channel-num" (and fixed
          an internal inconsistency where the same warning message
          mixed "multi-subchannel" and "multi-channel" for the same
          concept). "Subchannel" incorrectly implied a single combined
          signal demultiplexed into related sub-streams; what's
          actually happening is several independent, unrelated
          frequencies packed into one DRF directory's data columns.
          No functional change.
  v1.0.0  Initial release.

OVERVIEW
========
find_event_stations.py gives you a ranked shortlist of companion station
nicknames. The README's next step is manual: log into the PSWS web portal,
find each station's observation, download the tarball, unzip it, and
rename the result so it matches what drf_inspect.py / drf_to_doppler.py
expect:

    ./<station_slug>/ch0/...

This script automates that using the PSWS network's documented public
download API (no login required):

    https://pswsnetwork.eng.ua.edu/observations/downloadapi/

For each station nickname you give it, the script:

  1. Resolves the nickname -> public PSWS Station ID (e.g. "S000028") by
     scraping the station directory table (cached for a week, same
     pattern as find_event_stations.py's .psws_station_cache.json).
  2. Calls the download API for your date range (+ optional frequency
     filter) and saves the returned ZIP.
  3. Extracts it into a scratch directory and locates the actual DRF
     channel directory inside (searches for a "ch0" subdirectory rather
     than assuming a fixed layout, since the zip's internal structure can
     vary between single-station and multi-station downloads).
  4. Moves it into ./<station_slug>/ in your output directory, where
     station_slug is the lowercased nickname with "/" -> "_" (matching
     the convention used throughout the upstream repo, e.g. "AC0G_ND" or
     "n6rfm" for "N6RFM/5").
  5. Writes a download_manifest.json recording what was pulled, from
     where, and when (useful for citing data provenance later).

After this script finishes, the folder is ready for:

    python3 drf_inspect.py --all . --frequency 10

WHY NOT JUST USE THE select_download_range/<ObsID> LINKS PRINTED BY
find_event_stations.py?
=====================================================================
Those are PSWS *web UI* pages (a date-range picker, then a form submit),
not stable direct-download URLs, and scraping them is fragile. The
station_id + date-range REST API documented at
https://pswsnetwork.caps.ua.edu/about/ is the supported, stable way to
fetch the same data programmatically, so that's what this script uses.
You still typically want to run find_event_stations.py FIRST to decide
*which* station nicknames are worth downloading.

RATE LIMITS
===========
The PSWS download API is public and unauthenticated but rate-limited to
100 requests/day per the published docs. This script sleeps
--sleep-seconds (default 2.0) between requests and stops immediately on
an HTTP 429 response rather than burning through remaining stations.

USAGE
=====
Download a handful of specific stations for one UTC date:

    python3 download_companions.py --date 2026-01-19 \
        --stations AA6BD W7LUX AC0G_ND --frequency 10

Read the station list from a file (one nickname per line, '#' comments
and blank lines ignored) -- handy for pasting the "Station" column
straight out of find_event_stations.py's output:

    python3 download_companions.py --date 2026-01-19 \
        --stations-file companions.txt --frequency 10

Multi-day span:

    python3 download_companions.py --start-date 2026-01-18 \
        --end-date 2026-01-20 --stations AA6BD --frequency 10

Dry run (show what would happen, make no network requests for data,
only resolve station IDs):

    python3 download_companions.py --date 2026-01-19 \
        --stations AA6BD W7LUX --dry-run

OPTIONS
=======
--date YYYY-MM-DD       Shorthand for --start-date == --end-date == DATE.
--start-date / --end-date
                         Explicit date range (UTC, inclusive), YYYY-MM-DD.
--stations NICK [NICK ...]
                         One or more PSWS station nicknames (as shown by
                         find_event_stations.py / the PSWS site).
--stations-file FILE     Text file with one nickname per line.
--frequency MHZ          Optional center-frequency filter passed to the
                          API (e.g. 10 or 10.000). Omit to fetch all
                          frequencies for that station/date.
--out-dir DIR            Where station folders get created. Default: '.'
--channel ch0            DRF channel directory name to look for inside
                          the download. Default: ch0 (matches
                          drf_inspect.py's default).
--overwrite               Replace an existing ./<station_slug>/ folder
                          instead of skipping it.
--keep-extra-days         By default, any day the API returns outside
                          your requested date range is discarded. Pass
                          this to keep every day instead (each saved as
                          <slug>_<YYYYMMDD>/).
--keep-zip                Don't delete the downloaded ZIP after
                          extraction (saved into <out-dir>/.downloads/).
--sleep-seconds 2.0       Delay between API requests.
--no-cache                 Bypass the station-ID cache and re-scrape the
                          PSWS station directory.
--dry-run                 Resolve station IDs and print the planned
                          downloads, but don't call the download API or
                          write any station folders.

REQUIREMENTS
============
pip install requests beautifulsoup4
(same as find_event_stations.py)

SEE ALSO
========
find_event_stations.py   upstream candidate finder (run this first)
drf_inspect.py            run this on the output of this script next
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

__version__ = "1.0.0"

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

PSWS_BASE = "https://pswsnetwork.eng.ua.edu"
STN_PATH = "/stations/stations/"
DOWNLOAD_API_PATH = "/observations/downloadapi/"
UA = "Mozilla/5.0 (download_companions.py for psws-drf-tid-tools)"

STATION_ID_CACHE_FILE = ".psws_station_id_cache.json"
CACHE_MAX_AGE_DAYS = 7

DAILY_RATE_LIMIT = 100  # published limit; we just warn as we approach it


# ----------------------------------------------------------------------------
# Station nickname -> public Station ID ("S000028") resolution
# ----------------------------------------------------------------------------

def build_station_id_table(session):
    """Scrape /stations/stations/ and return {nickname: public_id}.

    The public ID is the S/N-prefixed identifier shown in the PSWS UI
    (e.g. "S000028"), which is what the download API's station_id
    parameter expects. This is a *different* identifier than the numeric
    internal form value find_event_stations.py uses for its own
    .psws_station_cache.json, so we keep a separate cache file.
    """
    table = {}
    for page in range(1, 80):
        try:
            r = session.get(PSWS_BASE + STN_PATH, params={"page": page},
                             timeout=30)
        except requests.RequestException as e:
            print(f"  warning: request failed on page {page}: {e}")
            break
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        tbl = soup.find("table")
        if not tbl:
            break
        rows = 0
        for tr in tbl.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) < 6:
                continue
            sid_str, user, nick, grid, elev, status = tds[:6]
            if not re.match(r"^[NS]\d+$", sid_str):
                continue
            table[nick] = sid_str
            rows += 1
        if rows == 0:
            break
        if not soup.find("a", string=re.compile(r"next", re.I)):
            break
        time.sleep(0.15)
    return table


def get_station_id_table(session, use_cache=True):
    if use_cache and os.path.exists(STATION_ID_CACHE_FILE):
        try:
            age_days = ((time.time() - os.path.getmtime(STATION_ID_CACHE_FILE))
                        / 86400)
            if age_days < CACHE_MAX_AGE_DAYS:
                with open(STATION_ID_CACHE_FILE) as f:
                    data = json.load(f)
                print(f"Using cached station-ID table "
                      f"({age_days:.1f} days old, {len(data)} stations)")
                return data
        except Exception:
            pass
    print("Fetching PSWS station directory (nickname -> Station ID)...")
    table = build_station_id_table(session)
    with open(STATION_ID_CACHE_FILE, "w") as f:
        json.dump(table, f, indent=2)
    print(f"  cached {len(table)} stations to {STATION_ID_CACHE_FILE}")
    return table


def resolve_station_id(nickname, table):
    """Case-insensitive, whitespace-tolerant lookup with a couple of
    fallbacks for nicknames PSWS often renders inconsistently."""
    if nickname in table:
        return table[nickname]
    target = nickname.strip().lower()
    for nick, sid in table.items():
        if nick.strip().lower() == target:
            return sid
    return None


# ----------------------------------------------------------------------------
# Folder naming
# ----------------------------------------------------------------------------

def slugify_station(nickname):
    """Match the lowercase, underscore-joined folder naming convention
    used throughout psws-drf-tid-tools' docs and examples (e.g.
    "AC0G_ND" -> "ac0g_nd", "N6RFM/5" -> "n6rfm_5")."""
    s = nickname.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# ----------------------------------------------------------------------------
# Download + extract + organize
# ----------------------------------------------------------------------------

def api_exclusive_end_date(end_date_str):
    """PSWS observation files span a full UTC day, 00:00:00 to the NEXT
    day's 00:00:00 (visible in the PSWS observation list: an obs dated
    2026-06-25 has Start=2026-06-25 00:00:00, End=2026-06-26 00:00:00).
    The download API's own documented examples request a single day as
    start_date=D, end_date=D+1 (e.g. 2022-12-09 .. 2022-12-10) -- NOT the
    same date twice. Passing the same date for both silently matches
    nothing, because the observation's end timestamp falls on the day
    *after* end_date when end_date is parsed as that day's midnight.

    This adds one calendar day to the user-facing end_date so a request
    for "give me DATE" actually captures DATE's observation file."""
    d = datetime.strptime(end_date_str, "%Y-%m-%d")
    d = d.replace(tzinfo=timezone.utc)
    return (d + timedelta(days=1)).strftime("%Y-%m-%d")


def download_one(session, nickname, station_id, start_date, end_date,
                  frequency, scratch_dir):
    """Download the ZIP for one station/date-range. Returns the local zip
    path, "RATE_LIMITED" (HTTP 429 -- caller should stop entirely),
    "NO_MATCH_WITH_FREQ" (HTTP 404 with a frequency filter applied --
    caller should auto-retry without one, since this usually means a
    multi-channel-num station whose comma-separated frequency field
    can't exact-match), or None (any other failure, already printed).

    start_date/end_date here are the user-facing INCLUSIVE range (e.g.
    both "2026-06-25" for a single day). The actual API call uses
    end_date + 1 day -- see api_exclusive_end_date() above."""
    api_end_date = api_exclusive_end_date(end_date)
    params = {"station_id": station_id,
              "start_date": start_date,
              "end_date": api_end_date}
    if frequency:
        params["frequency"] = frequency

    url = PSWS_BASE + DOWNLOAD_API_PATH
    print(f"  GET {url} params={params}")
    try:
        r = session.get(url, params=params, timeout=180, stream=True)
    except requests.RequestException as e:
        print(f"  ERROR: request failed: {e}")
        return None

    if r.status_code == 429:
        print("  RATE LIMITED (HTTP 429). Stopping further downloads "
              "this run -- the PSWS API allows 100 requests/day.")
        return "RATE_LIMITED"
    if r.status_code == 404:
        print(f"  No matching observations for {nickname} "
              f"({start_date}..{end_date}"
              f"{', '+str(frequency)+' MHz' if frequency else ''}).")
        if frequency:
            return "NO_MATCH_WITH_FREQ"
        return None
    if r.status_code == 400:
        print(f"  ERROR: bad request (400): {r.text[:300]}")
        return None
    if r.status_code != 200:
        print(f"  ERROR: unexpected status {r.status_code}: {r.text[:300]}")
        return None

    zip_path = os.path.join(scratch_dir, f"{slugify_station(nickname)}.zip")
    total = 0
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            if chunk:
                f.write(chunk)
                total += len(chunk)
    if total == 0:
        print("  ERROR: downloaded file is empty.")
        return None
    print(f"  saved {total/1e6:.1f} MB -> {zip_path}")
    return zip_path


OBS_DATE_RE = re.compile(r"OBS(\d{4}-\d{2}-\d{2})T")


def root_date_stamp(root):
    """Try to pull a YYYY-MM-DD date out of a DRF root's path, e.g. a
    directory named 'OBS2026-06-25T00-00' somewhere on the path -- this
    is the naming convention PSWS uses for DRF I/Q observations (see
    find_event_stations.py's DRF_FILENAME_RE). Returns None if no such
    component is found anywhere in the path."""
    for part in root.split(os.sep):
        m = OBS_DATE_RE.search(part)
        if m:
            return m.group(1).replace("-", "")
    return None


def find_drf_roots(extract_dir, channel):
    """Walk extract_dir and return every directory whose immediate child
    is named `channel` (e.g. 'ch0'). That parent directory is a DRF
    station root in the sense drf_inspect.py expects."""
    roots = []
    for dirpath, dirnames, _filenames in os.walk(extract_dir):
        if channel in dirnames:
            roots.append(dirpath)
    return roots


def organize_one(zip_path, nickname, out_dir, channel, overwrite,
                  scratch_dir, user_start_date, user_end_date,
                  keep_extra_days=False):
    """Extract zip_path and move the DRF root(s) it contains into
    out_dir/<slug>/. The PSWS download API's date-range matching is not
    perfectly consistent across station/instrument types, and can return
    extra calendar days beyond what was actually requested (see
    api_exclusive_end_date()). By default, any extracted day outside
    [user_start_date, user_end_date] (inclusive, the dates the user
    actually asked for) is discarded rather than kept -- pass
    keep_extra_days=True to keep everything the API returned, each
    labeled out_dir/<slug>_<YYYYMMDD>/. Returns a list of destination
    folder paths."""
    slug = slugify_station(nickname)
    extract_dir = os.path.join(scratch_dir, f"{slug}_extract")
    if os.path.isdir(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        print(f"  ERROR: {zip_path} is not a valid zip "
              f"(API may have returned an error page).")
        return []

    roots = find_drf_roots(extract_dir, channel)
    if not roots:
        print(f"  WARNING: no '{channel}/' directory found anywhere in "
              f"the download for {nickname}. Leaving raw contents in "
              f"{extract_dir} for manual inspection.")
        return []

    if not keep_extra_days and len(roots) > 1:
        lo = user_start_date.replace("-", "")
        hi = user_end_date.replace("-", "")
        kept_roots, dropped = [], []
        for root in roots:
            stamp = root_date_stamp(root)
            if stamp is None or lo <= stamp <= hi:
                kept_roots.append(root)
            else:
                dropped.append((root, stamp))
        if dropped:
            print(f"  NOTE: download contained {len(roots)} calendar "
                  f"day(s) for {nickname}; keeping {len(kept_roots)} "
                  f"within your requested {user_start_date}..{user_end_date} "
                  f"range and discarding {len(dropped)} outside it "
                  f"({', '.join(s for _, s in dropped)}). "
                  f"Pass --keep-extra-days to keep everything instead.")
            for root, _stamp in dropped:
                shutil.rmtree(root, ignore_errors=True)
        roots = kept_roots
    elif len(roots) > 1:
        print(f"  NOTE: this download contained {len(roots)} separate "
              f"calendar days for {nickname}. --keep-extra-days is set, "
              f"so each is being saved as its own date-stamped folder.")

    if not roots:
        print(f"  Nothing left to organize for {nickname} after date "
              f"filtering.")
        shutil.rmtree(extract_dir, ignore_errors=True)
        return []

    dests = []
    for i, root in enumerate(roots):
        if len(roots) == 1:
            dest_slug = slug
        else:
            stamp = root_date_stamp(root)
            dest_slug = f"{slug}_{stamp}" if stamp else f"{slug}_{i+1}"
        dest = os.path.join(out_dir, dest_slug)
        if os.path.exists(dest):
            if overwrite:
                shutil.rmtree(dest)
            else:
                print(f"  SKIP: {dest} already exists "
                      f"(use --overwrite to replace).")
                continue
        shutil.move(root, dest)
        print(f"  organized -> {dest}/{channel}/")
        dests.append(dest)

    shutil.rmtree(extract_dir, ignore_errors=True)
    return dests


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def load_stations_file(path):
    """One station nickname per line. Nicknames may themselves contain
    spaces (e.g. "KE9SA Grape DRF S48"), so we only strip a trailing
    " # comment" rather than truncating to the first whitespace token."""
    out = []
    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if " #" in line:
                line = line.split(" #", 1)[0].rstrip()
            if line:
                out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring at the top of the script for full details.",
    )
    ap.add_argument("--date", help="Shorthand: sets both --start-date and "
                                    "--end-date to this UTC date.")
    ap.add_argument("--start-date", help="Start date YYYY-MM-DD (UTC).")
    ap.add_argument("--end-date", help="End date YYYY-MM-DD (UTC).")
    ap.add_argument("--stations", nargs="+", default=[],
                     help="One or more PSWS station nicknames.")
    ap.add_argument("--stations-file",
                     help="Text file, one station nickname per line.")
    ap.add_argument("--frequency", default=None,
                     help="Optional center-frequency filter in MHz, "
                          "e.g. 10 or 10.000.")
    ap.add_argument("--out-dir", default=".",
                     help="Directory to create station folders in. "
                          "Default: current directory.")
    ap.add_argument("--channel", default="ch0",
                     help="DRF channel directory name to look for. "
                          "Default: ch0.")
    ap.add_argument("--overwrite", action="store_true",
                     help="Replace an existing station folder instead of "
                          "skipping it.")
    ap.add_argument("--keep-extra-days", action="store_true",
                     help="By default, any calendar day the PSWS API "
                          "returns outside your requested --date / "
                          "--start-date..--end-date range is discarded "
                          "(this can happen because the API's date "
                          "matching isn't perfectly consistent across "
                          "station types). Pass this flag to keep every "
                          "day the API returns instead, each saved as "
                          "<slug>_<YYYYMMDD>/.")
    ap.add_argument("--keep-zip", action="store_true",
                     help="Keep downloaded ZIPs in <out-dir>/.downloads/ "
                          "instead of deleting them after extraction.")
    ap.add_argument("--sleep-seconds", type=float, default=2.0,
                     help="Delay between download API requests. "
                          "Default: 2.0")
    ap.add_argument("--no-cache", action="store_true",
                     help="Bypass the station-ID cache and re-scrape the "
                          "PSWS station directory.")
    ap.add_argument("--dry-run", action="store_true",
                     help="Resolve station IDs and print the plan; make "
                          "no download requests.")
    ap.add_argument("--version", action="version",
                     version=f"%(prog)s {__version__}")
    args = ap.parse_args()

    start_date = args.start_date or args.date
    end_date = args.end_date or args.date
    if not start_date or not end_date:
        sys.exit("Specify --date, or both --start-date and --end-date.")

    stations = list(args.stations)
    if args.stations_file:
        stations.extend(load_stations_file(args.stations_file))
    # de-dupe, preserve order
    seen = set()
    stations = [s for s in stations if not (s in seen or seen.add(s))]
    if not stations:
        sys.exit("No stations given. Use --stations or --stations-file.")

    os.makedirs(args.out_dir, exist_ok=True)
    scratch_dir = os.path.join(args.out_dir, ".downloads", "_scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    zip_keep_dir = os.path.join(args.out_dir, ".downloads")

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    print(f"Stations requested: {', '.join(stations)}")
    print(f"Date range: {start_date} .. {end_date}"
          f"{f' @ {args.frequency} MHz' if args.frequency else ''}\n")

    if args.frequency:
        print("NOTE: --frequency does an exact-string match against "
              "the API's center-frequency field. Multi-channel-num "
              "rx888/WSPRdaemon stations store this as a comma-separated "
              "list (e.g. \"10.000 MHz, 5.000 MHz, ...\") which will NOT "
              "match a bare value like '10', so the API may silently "
              "report \"no matching observations\" for a station that "
              "actually does have your target frequency. This script "
              "auto-retries any such station without --frequency in "
              "the same run (downloading the full multi-channel-num "
              "file, often ~3 GB instead of ~30-50 MB, since that's the "
              "only filter-safe option for those stations), so no "
              "manual re-run is needed. Use drf_inspect.py --frequency "
              "<MHz> afterward to find the right --channel-num index.\n")

    id_table = get_station_id_table(session, use_cache=not args.no_cache)

    plan = []
    for nick in stations:
        sid = resolve_station_id(nick, id_table)
        if sid is None:
            print(f"  COULD NOT RESOLVE station ID for '{nick}' "
                  f"-- check spelling against the PSWS station directory, "
                  f"or run with --no-cache to refresh.")
        plan.append((nick, sid))

    print("\nPlan:")
    for nick, sid in plan:
        print(f"  {nick:<20} -> {sid or '??? (will be skipped)'}")

    if args.dry_run:
        print("\n--dry-run set: stopping before any download requests.")
        shutil.rmtree(scratch_dir, ignore_errors=True)
        return

    manifest_path = os.path.join(args.out_dir, "download_manifest.json")
    manifest = []
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception:
            manifest = []

    n_requests = 0
    n_ok = 0
    print()
    for nick, sid in plan:
        if sid is None:
            continue
        print(f"=== {nick} ({sid}) ===")
        if n_requests > 0:
            time.sleep(args.sleep_seconds)
        n_requests += 1
        if n_requests > DAILY_RATE_LIMIT:
            print("  Reached the published 100 requests/day limit for "
                  "this run. Stopping; re-run tomorrow for the rest.")
            break

        zip_path = download_one(session, nick, sid, start_date, end_date,
                                 args.frequency, scratch_dir)
        if zip_path == "RATE_LIMITED":
            break
        if zip_path == "NO_MATCH_WITH_FREQ":
            # REAL UX GAP FOUND live, raised directly: this used to just
            # print a suggestion ("retry just this one without
            # --frequency") and require the user to notice the failure,
            # then manually run a second command for the affected
            # station(s) -- exactly the opposite of "very easy and
            # almost seamless" this whole workflow exists for.
            # Multi-channel-num rx888/WSPRdaemon stations store their
            # center-frequency as a comma-separated list that the API's
            # exact-string --frequency filter can never match, so this
            # case is expected/common, not exceptional -- auto-retrying
            # immediately, in the same run, is the right default rather
            # than a manual escape hatch.
            print(f"    Retrying {nick} without --frequency "
                  f"(likely a multi-channel-num station whose "
                  f"comma-separated frequency list can't exact-match "
                  f"'{args.frequency}')...")
            time.sleep(args.sleep_seconds)
            n_requests += 1
            if n_requests > DAILY_RATE_LIMIT:
                print("  Reached the published 100 requests/day limit "
                      "for this run. Stopping; re-run tomorrow for the "
                      "rest.")
                break
            zip_path = download_one(session, nick, sid, start_date, end_date,
                                     None, scratch_dir)
            if zip_path == "RATE_LIMITED":
                break
        if zip_path is None or zip_path == "NO_MATCH_WITH_FREQ":
            continue

        dests = organize_one(zip_path, nick, args.out_dir, args.channel,
                              args.overwrite, scratch_dir,
                              start_date, end_date,
                              keep_extra_days=args.keep_extra_days)

        if args.keep_zip:
            os.makedirs(zip_keep_dir, exist_ok=True)
            kept = os.path.join(zip_keep_dir, os.path.basename(zip_path))
            shutil.move(zip_path, kept)
        else:
            os.remove(zip_path)

        for dest in dests:
            n_ok += 1
            manifest.append({
                "nickname": nick,
                "station_id": sid,
                "folder": os.path.relpath(dest, args.out_dir),
                "start_date": start_date,
                "end_date": end_date,
                "frequency_mhz": args.frequency,
                "downloaded_at": datetime.now(timezone.utc)
                                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": PSWS_BASE + DOWNLOAD_API_PATH,
            })
        print()

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    shutil.rmtree(scratch_dir, ignore_errors=True)

    print(f"Done. {n_ok} station folder(s) organized in "
          f"{os.path.abspath(args.out_dir)}")
    print(f"Manifest written to {manifest_path}")
    print()
    print("Next steps:")
    freq_flag = f" --frequency {args.frequency}" if args.frequency else ""
    print(f"  python3 drf_inspect.py --all {args.out_dir}{freq_flag}")
    print(f"  (read the '--channel-num N' it prints for EACH station -- "
          f"single-channel Grapes are always 0, but rx888/WSPRdaemon "
          f"stations vary per station, e.g. N5TNL=4, KD7EFG=5, then "
          f"run drf_to_doppler.py per station with its own --channel-num)")


if __name__ == "__main__":
    main()
