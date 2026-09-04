#!/usr/bin/env python3
r"""
check_install.py — verify psws-drf-tid-tools' dependencies are installed

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.4.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.4.0  Added mock_server_gui.py as a fourth tool affected by a
          missing tkinter, alongside the three already listed.

  v1.3.0  Added tid_workflow_launcher.py (new) to the tkinter-affects
          message -- and, while there, fixed a real gap: this same
          message never actually mentioned tid_external_helper.py
          either, even though it's also a Tkinter app. Only
          tid_intake_helper.py was ever added here.

  v1.2.0  Two changes, neither previously given its own entry here:
          removed the `streamlit` optional-dependency check (v4.8.0
          retired `tid_dashboard.py`, the only thing that used it);
          added an informational (not required) check for `polars`,
          which belongs to the separate `hamsci_LSTID_detection` repo,
          not to anything in this one -- surfaced here so a real run
          against `tid_external_helper.py`'s LSTID checkbox doesn't
          get most of the way through a genuinely slow (but working)
          GNSS TEC step before failing on a missing dependency it
          could have known about up front.

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

    # tkinter is stdlib but a separate OS package on some systems.
    # tid_intake_helper.py is a Tkinter app -- without this, it won't
    # launch at all (not a graceful degradation, unlike the optional
    # dependencies above) -- worth checking since "pip install" can't
    # fix this one.
    print()
    tk_ok = check("tkinter")
    print(f"  [{'OK  ' if tk_ok else 'missing'}] tkinter (system package, "
          "not pip-installable)")
    if not tk_ok:
        print("      Affects: tid_intake_helper.py, tid_external_helper.py, "
              "tid_workflow_launcher.py, and mock_server_gui.py -- none of "
              "these four will launch without it. All CLI tools, including "
              "tid_workflow.py itself, are unaffected.")
        print("      Fix (Debian/Ubuntu): sudo apt install python3-tk")

    # None of these are dependencies of anything in this repo -- they
    # belong to hamsci_LSTID_detection, a separate GitHub repo this
    # project only shells out to (see docs/EXTERNAL_EVALUATION.md §3).
    # Checked here anyway, informationally, because tid_external_helper
    # .py's LSTID checkbox needs them, and checking only "polars" here
    # (an earlier version of this) genuinely wasn't enough: a real run
    # got most of the way through a working GNSS TEC step, past the
    # polars check, and then failed on a *second*, different missing
    # dependency (pyarrow) partway into the LSTID step. This list is
    # the complete one, taken directly from that repo's own README
    # ("Requirements" section) rather than adding packages here one at
    # a time as each one surfaces -- cartopy/matplotlib/numpy/pandas/
    # pillow/scipy are already required above and aren't repeated here.
    print()
    lstid_specific_deps = ["dask", "h5py", "polars", "pyarrow",
                           "pysolar", "statsmodels"]
    missing_lstid = [d for d in lstid_specific_deps if not check(d)]
    for dep in lstid_specific_deps:
        ok = dep not in missing_lstid
        print(f"  [{'OK  ' if ok else 'missing'}] {dep} (NOT required by "
              f"this repo -- only by the separate hamsci_LSTID_detection "
              f"toolkit)")
    if missing_lstid:
        print(f"      Affects: tid_external_helper.py's HamSCI LSTID "
              f"Detection checkbox only, and only if you've already "
              f"cloned that separate repo -- irrelevant otherwise.")
        fix = f"pip install {' '.join(missing_lstid)}"
        if "polars" in missing_lstid:
            fix = fix.replace("polars", "'polars[rtcompat]'")
        print(f"      Fix: {fix}" +
              (" -- see docs/EXTERNAL_EVALUATION.md \u00a73 for why "
               "the [rtcompat] variant specifically, on some CPUs."
               if "polars" in missing_lstid else "."))

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
