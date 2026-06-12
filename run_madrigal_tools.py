#!/usr/bin/env python3
"""
run_madrigal_tools.py — Combined wrapper for PSWS Madrigal-based tools.

Two tools share Madrigal as a data source but analyze different things:

  - GNSS TEC tool   (fetch_madrigal_tec.py)         -> GPS TEC verification
  - HF LSTID tool   (hamsci_LSTID_detection)         -> HF spot-based LSTID detection

This script:
  1. Provides ONE setup step for shared Madrigal account info
     (~/.config/psws/madrigal_user.json), used by both tools.
  2. Reads the event date (and optionally stations/window) from a
     tid_workflow_event.json in the given event directory.
  3. Runs one or both tools (--tool gnss|lstid|both).
  4. Saves each tool's output under the event directory, e.g.:
       <event_dir>/gnss_tec/
       <event_dir>/lstid/

Setup (one time)
----------------
  python run_madrigal_tools.py --setup

Usage
-----
  # Run both tools for an event, saving results into the event directory
  python run_madrigal_tools.py --event ~/Downloads/tid_event_20260606 --tool both

  # Just the GNSS TEC check
  python run_madrigal_tools.py --event ~/Downloads/tid_event_20260606 --tool gnss

  # Just HF LSTID detection, downloading Madrigal HF spot data if needed
  python run_madrigal_tools.py --event ~/Downloads/tid_event_20260606 --tool lstid --download

Paths to the underlying tools/repos can be overridden with flags or env vars
(GNSS_TEC_SCRIPT, LSTID_REPO) — see --help for defaults.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MADRIGAL_USER_FILE = Path.home() / ".config" / "psws" / "madrigal_user.json"


# ---------------------------------------------------------------------------
# Shared Madrigal user setup
# ---------------------------------------------------------------------------

def setup_madrigal_user():
    MADRIGAL_USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if MADRIGAL_USER_FILE.exists():
        existing = json.loads(MADRIGAL_USER_FILE.read_text())
        print(f"Existing Madrigal user info found at {MADRIGAL_USER_FILE}:")
        print(json.dumps(existing, indent=2))

    fullname = input(f"Full name [{existing.get('user_fullname', '')}]: ").strip() \
        or existing.get("user_fullname", "")
    email = input(f"Email [{existing.get('user_email', '')}]: ").strip() \
        or existing.get("user_email", "")
    affiliation = input(f"Affiliation [{existing.get('user_affiliation', '')}]: ").strip() \
        or existing.get("user_affiliation", "")

    info = {"user_fullname": fullname, "user_email": email, "user_affiliation": affiliation}
    MADRIGAL_USER_FILE.write_text(json.dumps(info, indent=2))
    print(f"Saved to {MADRIGAL_USER_FILE}")
    return info


def load_madrigal_user():
    if not MADRIGAL_USER_FILE.exists():
        print("[run_madrigal_tools] No Madrigal user info saved yet. Running setup...")
        return setup_madrigal_user()
    return json.loads(MADRIGAL_USER_FILE.read_text())


# ---------------------------------------------------------------------------
# Event info
# ---------------------------------------------------------------------------

def load_event_json(event_dir: Path) -> dict:
    ev_path = event_dir / "tid_workflow_event.json"
    if not ev_path.exists():
        print(f"[run_madrigal_tools] ERROR: {ev_path} not found")
        sys.exit(1)
    with open(ev_path) as f:
        return json.load(f), ev_path


def get_event_date(ev: dict) -> datetime:
    if "date" in ev:
        return datetime.fromisoformat(ev["date"])
    if "start" in ev:
        return datetime.fromisoformat(ev["start"])
    raise KeyError('tid_workflow_event.json must contain "date" or "start"')


# ---------------------------------------------------------------------------
# GNSS TEC tool
# ---------------------------------------------------------------------------

def run_gnss_tec(args, event_dir: Path, ev_path: Path, user: dict):
    out_dir = event_dir / "gnss_tec"
    out_dir.mkdir(parents=True, exist_ok=True)

    script = Path(args.gnss_tec_script).expanduser().resolve()
    if not script.exists():
        print(f"[run_madrigal_tools] ERROR: GNSS TEC script not found at {script}")
        print("            Set --gnss-tec-script or GNSS_TEC_SCRIPT to its location.")
        sys.exit(1)

    cmd = [
        sys.executable, str(script),
        "--config", str(ev_path),
        "--output-dir", str(out_dir),
        "--user-fullname", user["user_fullname"],
        "--user-email", user["user_email"],
        "--user-affiliation", user["user_affiliation"],
    ]
    print(f"[run_madrigal_tools] Running GNSS TEC tool -> {out_dir}")
    print(f"[run_madrigal_tools]   {' '.join(cmd)}")
    if not args.dry_run:
        subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# HF LSTID tool
# ---------------------------------------------------------------------------

def download_hf_day(date_dt: datetime, data_dir: Path, user: dict):
    data_dir.mkdir(parents=True, exist_ok=True)
    fname = data_dir / f"rsd{date_dt:%Y-%m-%d}.01.hdf5"
    if fname.exists():
        print(f"[run_madrigal_tools] Already have {fname.name}")
        return

    if not shutil.which("globalDownload.py"):
        print("[run_madrigal_tools] ERROR: globalDownload.py not found. "
              "Install with: pip install madrigalWeb")
        sys.exit(1)

    mdy = date_dt.strftime("%m/%d/%Y")
    cmd = [
        "globalDownload.py", "--verbose",
        "--url=http://cedar.openmadrigal.org",
        f"--outputDir={data_dir}",
        f"--user_fullname={user['user_fullname']}",
        f"--user_email={user['user_email']}",
        f"--user_affiliation={user['user_affiliation']}",
        "--format=hdf5",
        f"--startDate={mdy}",
        f"--endDate={mdy}",
        "--inst=8308",
    ]
    print(f"[run_madrigal_tools] Downloading HF spot data for {date_dt:%Y-%m-%d} ...")
    subprocess.run(cmd, check=True)


def run_lstid(args, event_dir: Path, date_dt: datetime, user: dict):
    lstid_repo = Path(args.lstid_repo).expanduser().resolve()
    if not lstid_repo.exists():
        print(f"[run_madrigal_tools] ERROR: LSTID repo not found at {lstid_repo}")
        print("            git clone https://github.com/HamSCI/hamsci_LSTID_detection.git")
        sys.exit(1)

    cfg_path = lstid_repo / args.lstid_config
    with open(cfg_path) as f:
        cfg = json.load(f)

    cfg["start"] = date_dt.strftime("%Y-%m-%dT00:00:00")
    cfg["end"] = date_dt.strftime("%Y-%m-%dT23:59:59")

    out_dir = (event_dir / "lstid").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg["plotting"]["output_dir"] = str(out_dir / "daily_plots")

    if args.download:
        data_dir = (lstid_repo / cfg["data_dir"]).resolve()
        download_hf_day(date_dt, data_dir, user)

    run_cfg_path = lstid_repo / "config" / f"{date_dt:%Y%m%d}_event.json"
    with open(run_cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[run_madrigal_tools] Wrote LSTID config: {run_cfg_path}")
    print(f"[run_madrigal_tools] LSTID plots -> {out_dir / 'daily_plots'}")

    if args.dry_run:
        return

    cmd = [sys.executable, "run_LSTID_detection.py", "-p", str(run_cfg_path)]
    print(f"[run_madrigal_tools] Running: {' '.join(cmd)} (cwd={lstid_repo})")
    subprocess.run(cmd, cwd=lstid_repo, check=True)

    # Copy CSV summary into event dir for convenience
    csv_dir = lstid_repo / "output" / "summary_csv"
    if csv_dir.exists():
        for f in csv_dir.glob(f"{date_dt:%Y%m%d}-{date_dt:%Y%m%d}_*sinfit.csv"):
            dest = out_dir / f.name
            shutil.copy2(f, dest)
            print(f"[run_madrigal_tools] Copied summary -> {dest}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--setup", action="store_true",
                    help="Save/update shared Madrigal user info and exit")
    ap.add_argument("--event", help="Path to TID event directory (contains tid_workflow_event.json)")
    ap.add_argument("--tool", choices=["gnss", "lstid", "both"], default="both",
                    help="Which tool(s) to run (default: both)")
    ap.add_argument("--download", action="store_true",
                    help="Download missing Madrigal HF spot data for the LSTID tool")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would run without executing")

    # Tool locations
    ap.add_argument("--gnss-tec-script",
                    default=os.environ.get("GNSS_TEC_SCRIPT", "~/psws-tools-pr/fetch_madrigal_tec.py"),
                    help="Path to fetch_madrigal_tec.py")
    ap.add_argument("--lstid-repo",
                    default=os.environ.get("LSTID_REPO", "~/hamsci_LSTID_detection"),
                    help="Path to cloned hamsci_LSTID_detection repo")
    ap.add_argument("--lstid-config", default="config/config_test.json",
                    help="LSTID base config, relative to LSTID repo")

    args = ap.parse_args()

    if args.setup:
        setup_madrigal_user()
        return

    if not args.event:
        ap.error("Provide --event <event_dir> or --setup")

    event_dir = Path(args.event).expanduser().resolve()
    ev, ev_path = load_event_json(event_dir)
    date_dt = get_event_date(ev)
    user = load_madrigal_user()

    print(f"[run_madrigal_tools] Event dir : {event_dir}")
    print(f"[run_madrigal_tools] Event date: {date_dt:%Y-%m-%d}")
    print(f"[run_madrigal_tools] Tool(s)   : {args.tool}")

    if args.tool in ("gnss", "both"):
        run_gnss_tec(args, event_dir, ev_path, user)

    if args.tool in ("lstid", "both"):
        run_lstid(args, event_dir, date_dt, user)


if __name__ == "__main__":
    main()
