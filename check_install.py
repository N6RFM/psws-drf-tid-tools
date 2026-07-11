#!/usr/bin/env python3
r"""
check_install.py — verify psws-drf-tid-tools' dependencies are installed

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.1.0  Updated for the requirements.txt/requirements-optional.txt
          consolidation into a single requirements.txt -- the missing-
          optional-dependency fix message now points to the one file
          rather than the removed second one. Also removed "(the
          recommended interactive method)" from prophet's own
          description -- cwt-prophet is one of several extraction
          methods, not a recommended default.
  v1.0.0  Initial release, written directly in response to hitting the
          same missing-dependency problem twice in one session: a
          venv rebuilt after a segfault (see PROJECT_STATE, this
          project's own research-branch history) only had
          requirements.txt reinstalled, not requirements-optional.txt
          -- so prophet went missing silently, only surfacing later
          as a confusing mid-run failure deep inside cwt-prophet
          extraction ("no output CSV found", with the actual
          ModuleNotFoundError buried in captured subprocess output
          that wasn't being surfaced anywhere). This script exists so
          that gap shows up immediately, in one place, with a clear
          fix -- rather than being rediscovered piecemeal every time
          a different optional feature happens to get exercised.
          Also suppresses a harmless but persistent "Importing plotly
          failed" warning that prophet's own plot submodule logs on
          every import regardless of whether plotting is ever used --
          this project never uses prophet's interactive plotting at
          all, and it was noisy enough during this script's own direct
          use to be worth fixing before the first release.

Checks every package this toolkit actually imports (cross-checked
directly against every .py file in the repo, not just requirements.txt
by hand) and reports which are missing, split into:
  - REQUIRED: the toolkit's core scripts won't run at all without these
  - OPTIONAL: specific features degrade or fail without these, but the
    rest of the toolkit still works fine

Usage:
    python3 check_install.py
"""

import importlib
import shutil
import sys

# (import name, pip package name, what breaks without it)
REQUIRED = [
    ("numpy", "numpy", "everything -- core numerical operations"),
    ("scipy", "scipy", "everything -- signal processing throughout"),
    ("pandas", "pandas", "everything -- data handling throughout"),
    ("matplotlib", "matplotlib", "every plot/spectrogram this toolkit produces"),
    ("digital_rf", "digital_rf", "reading any DRF recording at all"),
    ("requests", "requests", "any HTTP-based data fetching script"),
    ("bs4", "beautifulsoup4", "HTML-scraping data fetchers"),
    ("PyQt5", "PyQt5", "tid_spect_click.py, tid_quicklook.py"),
    ("pyqtgraph", "pyqtgraph", "tid_spect_click.py, tid_quicklook.py"),
    ("PIL", "Pillow", "image handling in the interactive GUI tools"),
]

OPTIONAL = [
    ("prophet", "prophet",
     "cwt-prophet extraction, one of several interactive extraction "
     "methods -- falls back to cwt-only without it"),
    ("streamlit", "streamlit",
     "tid_dashboard.py (the entire browser-based GUI) -- CLI tools "
     "still work fine without it"),
    ("cartopy", "cartopy",
     "tid_map.py's nicer maps -- falls back to a plain lat/lon plot "
     "without it"),
    ("astropy", "astropy",
     "hf_int.py's proper Lomb-Scargle significance test -- falls back "
     "to an approximate heuristic without it"),
    ("madrigalWeb", "madrigalWeb",
     "fetch_madrigal_tec.py specifically -- hard requirement for that "
     "one script, not needed elsewhere"),
]


def check(name):
    try:
        if name == "prophet":
            # prophet.plot logs a harmless "Importing plotly failed"
            # warning on every import regardless of whether plotting
            # is ever used -- this project never uses prophet's
            # interactive plotting, so it's pure cosmetic noise here.
            # Suppressed at this specific logger only, not globally.
            import logging
            logging.getLogger("prophet.plot").setLevel(logging.CRITICAL)
        importlib.import_module(name)
        return True
    except Exception:
        return False


def main():
    print("=== psws-drf-tid-tools dependency check ===\n")

    missing_required = []
    print("REQUIRED (core toolkit needs these to run at all):")
    for mod, pip_name, breaks in REQUIRED:
        ok = check(mod)
        status = "OK  " if ok else "MISSING"
        print(f"  [{status}] {mod}")
        if not ok:
            missing_required.append((pip_name, breaks))

    print()
    missing_optional = []
    print("OPTIONAL (specific features only):")
    for mod, pip_name, breaks in OPTIONAL:
        ok = check(mod)
        status = "OK  " if ok else "missing"
        print(f"  [{status}] {mod}")
        if not ok:
            missing_optional.append((pip_name, breaks))

    # tkinter is stdlib but a separate OS package on some systems, and
    # tid_dashboard.py's folder-browse button specifically needs it --
    # worth checking since "pip install" can't fix this one.
    print()
    tk_ok = check("tkinter")
    print(f"  [{'OK  ' if tk_ok else 'missing'}] tkinter (system package, "
          "not pip-installable)")
    if not tk_ok:
        print("      Affects: tid_dashboard.py's folder-browse button only "
              "-- falls back to manual path entry without it.")
        print("      Fix (Debian/Ubuntu): sudo apt install python3-tk")

    print()
    if missing_required:
        print("=== MISSING REQUIRED DEPENDENCIES ===")
        for pip_name, breaks in missing_required:
            print(f"  {pip_name}: breaks {breaks}")
        print(f"\n  Fix: pip install -r requirements.txt")

    if missing_optional:
        print("\n=== MISSING OPTIONAL DEPENDENCIES ===")
        for pip_name, breaks in missing_optional:
            print(f"  {pip_name}: breaks {breaks}")
        print(f"\n  Fix: pip install -r requirements.txt")
        print("  (These are listed alongside the required packages in "
              "the same file -- a partial reinstall of just some lines "
              "can leave specific features, like this one, silently "
              "broken.)")

    if not missing_required and not missing_optional:
        print("All dependencies present.")

    return 1 if missing_required else 0


if __name__ == "__main__":
    sys.exit(main())
