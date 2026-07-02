#!/usr/bin/env python3
r"""
tid_workflow.py — guided TID direction-of-arrival workflow

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Version: 0.1.0

OVERVIEW
========
Automates the 10-step guided extraction workflow:

  Step 1:  Discover stations in event directory
  Step 2:  Full-day spectrogram for each station
  Step 3:  User selects TID window (tid_quicklook.py)
  Step 4:  Zoomed spectrogram
  Step 5:  Optionally refine TID window (opt-in)
  Step 6:  cwt-prophet: anchor-guided extraction (Pass 0 auto + P to re-run with anchors)
           autocorr/cwt: fully automated extraction
           wave-fit: sine fit to user-clicked cycle points
  Step 7:  overlay spectrogram for visual assessment
  Step 8:  DOA (tid_doa.py)

State is saved after each interactive step so the workflow can be
resumed if interrupted.

USAGE
=====
    # Run full workflow
    python3 tid_workflow.py --event-dir ~/Downloads/gwyn_tid_event_20240517

    # Resume from saved state
    python3 tid_workflow.py --event-dir ~/Downloads/gwyn_tid_event_20240517 --resume

    # With WWV transmitter (default)
    python3 tid_workflow.py --event-dir ~/Downloads/gwyn_tid_event_20240517 \
        --tx-lat 40.68 --tx-lon -105.04 --tx-name WWV

REQUIREMENTS
============
    pip install digital_rf numpy pandas scipy matplotlib pyqtgraph PyQt5 Pillow

KNOWN PSWS STATIONS (built-in callsign database)
=================================================
Coordinates used for IPP midpoint calculation if not in DRF metadata.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

# ── Built-in callsign database ──────────────────────────────────────────────
# (lat, lon, grid)
KNOWN_STATIONS = {
    "W7LUX":   (35.1042, -111.7083, "DM45dc"),
    "AC0G_ND": (46.8750,  -96.8333, "EN16ov"),
    "N4RVE":   (48.5417, -123.1667, "CN84xx"),
    "N5BRG":   (35.6500,  -97.4800, "EM15xq"),
    "N6RFM":   (32.9400,  -97.2100, "EM12jw"),
    "AA6BD":   (35.0600,  -85.1300, "EM75kb"),
    "K0LO":    (39.9500, -105.1500, "DM79xx"),
    "W3HH":    (39.9500,  -75.1500, "FM29xx"),
    "WA2HXB":  (41.0500,  -74.1300, "FN21xx"),
    "KD9UKK":  (41.7000,  -86.2300, "EN61xx"),
}

# ── Helpers ──────────────────────────────────────────────────────────────────

TOOLS_DIR = Path(__file__).parent.resolve()


def run(cmd, **kwargs):
    """Run a command, print it, return CompletedProcess."""
    print(f"\n  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, **kwargs)


def tool(name):
    """Return full path to a tool in the same directory as this script."""
    return str(TOOLS_DIR / name)


def h_to_hhmm(h):
    h = max(0.0, h)  # clamp negative to midnight
    total_min = int(round(h * 60))
    hh, mm = divmod(total_min, 60)
    return f"{hh:02d}:{mm:02d}"


def h_to_iso(date_str, h):
    h = max(0.0, h)  # clamp negative hours to midnight
    hh = int(h); rem = (h - hh) * 60; mm = int(rem); ss = int((rem - mm) * 60)
    return f"{date_str}T{hh:02d}:{mm:02d}:{ss:02d}"


def midpoint(rx_lat, rx_lon, tx_lat, tx_lon):
    """Simple geographic midpoint."""
    return (rx_lat + tx_lat) / 2, (rx_lon + tx_lon) / 2


def read_drf_metadata(drf_dir):
    """Try to read lat/lon from DRF metadata."""
    try:
        import digital_rf as drf
        r = drf.DigitalRFReader(str(drf_dir))
        ch = r.get_channels()[0]
        props = r.get_properties(ch)
        lat = props.get("latitude", None)
        lon = props.get("longitude", None)
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    except Exception:
        pass
    return None, None


def _load_coords_cache(event_dir):
    """Load station coordinates cache from event directory."""
    cache_path = Path(event_dir) / "station_coords.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {}


def _save_coords_cache(event_dir, cache):
    """Save station coordinates cache to event directory."""
    cache_path = Path(event_dir) / "station_coords.json"
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def get_station_coords(name, drf_dir, event_dir=None):
    """Get receiver lat/lon: cache → DRF metadata → callsign DB → user input.

    If event_dir is provided, coordinates are cached in
    <event_dir>/station_coords.json and reused across runs.
    """
    # 0. Try persistent cache
    cache = {}
    if event_dir:
        cache = _load_coords_cache(event_dir)
        key_cache = name.upper()
        if key_cache in cache:
            lat, lon = cache[key_cache]["lat"], cache[key_cache]["lon"]
            print(f"    Coords from cache: {lat:.4f}N, {abs(lon):.4f}{'W' if lon < 0 else 'E'}")
            return lat, lon

    # 1. Try DRF metadata
    lat, lon = read_drf_metadata(drf_dir)
    if lat is not None:
        print(f"    Coords from DRF metadata: {lat:.4f}N, {abs(lon):.4f}{'W' if lon < 0 else 'E'}")
        if event_dir:
            cache[name.upper()] = {"lat": lat, "lon": lon}
            _save_coords_cache(event_dir, cache)
        return lat, lon

    # 2. Try callsign database
    key = name.upper().replace("-", "_")
    for k, (la, lo, gr) in KNOWN_STATIONS.items():
        if k in key or key in k:
            print(f"    Coords from callsign DB ({k}): {la:.4f}N, {abs(lo):.4f}{'W' if lo < 0 else 'E'}  {gr}")
            if event_dir:
                cache[name.upper()] = {"lat": la, "lon": lo}
                _save_coords_cache(event_dir, cache)
            return la, lo

    # 3. User input
    print(f"    Coords not found for {name}.")
    while True:
        try:
            lat = float(input(f"    Enter latitude for {name} (decimal degrees N): "))
            lon = float(input(f"    Enter longitude for {name} (decimal degrees E, negative=W): "))
            if event_dir:
                cache[name.upper()] = {"lat": lat, "lon": lon}
                _save_coords_cache(event_dir, cache)
                print(f"    Saved to station_coords.json (will be reused on re-run)")
            return lat, lon
        except ValueError:
            print("    Invalid — enter decimal numbers e.g. 35.1042 and -111.7083")


def probe_subchannels(drf_dir, date_str, target_mhz=10.0):
    """
    Probe all subchannels. Returns list of (subchannel, snr_db, freq_hz).
    Priority: DRF metadata frequencies > SNR ranking.
    Auto-selects subchannel closest to target_mhz if frequency metadata available.
    """
    try:
        import digital_rf as drf_lib
        r = drf_lib.DigitalRFReader(str(drf_dir))
        ch = r.get_channels()[0]
        props = r.get_properties(ch)
        sr = float(props["samples_per_second"])
        b0, b1 = r.get_bounds(ch)

        # Read probe block from middle of recording
        mid = (b0 + b1) // 2
        block = int(sr * 60)
        try:
            iq = r.read_vector(mid, block, ch)
        except Exception:
            iq = r.read_vector(b0, min(block, b1-b0), ch)

        # Single channel
        if iq.ndim == 1:
            spec = np.abs(np.fft.rfft(iq.real))
            snr = 20 * np.log10(spec.max() / (np.median(spec) + 1e-12))
            # Try to get center frequency from metadata
            freq = None
            for key in ["center_frequencies", "center_frequency",
                        "rf_centerfreq", "centerfreq"]:
                val = props.get(key, None)
                if val is not None:
                    try:
                        freq = float(np.atleast_1d(val)[0])
                    except Exception:
                        pass
                    break
            return [(0, float(snr), freq)]

        # Multi-channel
        n_subs = iq.shape[1]
        results = []

        # Get frequency array from metadata - try multiple key names
        freqs = None
        for key in ["center_frequencies", "center_frequency",
                    "rf_centerfreq", "centerfreq", "subchannel_center_frequencies"]:
            val = props.get(key, None)
            if val is not None:
                try:
                    arr = np.atleast_1d(val)
                    if len(arr) == n_subs:
                        freqs = arr
                        break
                    elif len(arr) == 1:
                        # Single freq — same for all subchannels
                        freqs = np.full(n_subs, float(arr[0]))
                        break
                except Exception:
                    pass

        for sub in range(n_subs):
            col = iq[:, sub]
            # Handle complex data
            if np.iscomplexobj(col):
                spec = np.abs(np.fft.fftshift(np.fft.fft(col)))
            else:
                spec = np.abs(np.fft.rfft(col))
            snr = 20 * np.log10(spec.max() / (np.median(spec) + 1e-12))
            freq = float(freqs[sub]) if freqs is not None else None
            results.append((sub, float(snr), freq))

        return sorted(results, key=lambda x: -x[1])

    except Exception as e:
        print(f"    Subchannel probe failed: {e}")
        return [(0, 0.0, None)]


def best_subchannel(subs, target_mhz=10.0):
    """
    Select best subchannel:
    1. Subchannel with frequency closest to target_mhz (if freq metadata available)
    2. Subchannel with highest SNR (fallback)
    """
    # Try frequency match first
    freq_matches = [(sub, snr, freq) for sub, snr, freq in subs
                    if freq is not None]
    if freq_matches:
        closest = min(freq_matches, key=lambda x: abs(x[2]/1e6 - target_mhz))
        diff = abs(closest[2]/1e6 - target_mhz)
        if diff < 0.1:  # within 100 kHz
            return closest[0], f"frequency match ({closest[2]/1e6:.3f} MHz)"

    # Fall back to highest SNR
    best = subs[0]
    return best[0], f"highest SNR ({best[1]:.1f} dB)"


def discover_stations(event_dir):
    """Find all DRF station directories in event_dir."""
    stations = []
    for d in sorted(Path(event_dir).iterdir()):
        if not d.is_dir():
            continue
        # Check if it looks like a DRF directory
        try:
            import digital_rf as drf_lib
            r = drf_lib.DigitalRFReader(str(d))
            chs = r.get_channels()
            if chs:
                stations.append(d)
        except Exception:
            pass
    return stations


# ── Console output logger ────────────────────────────────────────────────────
# Captures all console output (including subprocess) via fd-level tee.
# Used to save a complete workflow log to the runs/ directory.

class ConsoleLogger:
    """Tee stdout+stderr to a log file at the file-descriptor level.

    Captures everything including subprocess output. Starts a reader
    thread that copies data from a pipe to both the original terminal
    and the log file.
    """

    def __init__(self, log_path):
        import os as _os, threading as _th
        self.log_path = log_path
        self.log_file = open(log_path, "w")
        # Save original stdout/stderr file descriptors
        self._orig_stdout_fd = _os.dup(1)
        self._orig_stderr_fd = _os.dup(2)
        # Create pipe: subprocess writes to w, reader reads from r
        r, w = _os.pipe()
        # Redirect stdout and stderr to the write end of the pipe
        _os.dup2(w, 1)
        _os.dup2(w, 2)
        _os.close(w)
        # Reader thread: reads from pipe, writes to terminal + log
        self._reader_fd = r
        self._stop = False
        self._thread = _th.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        import os as _os
        buf = b""
        while True:
            try:
                data = _os.read(self._reader_fd, 4096)
            except OSError:
                break
            if not data:
                break
            # Write to original terminal
            _os.write(self._orig_stdout_fd, data)
            # Write to log file
            try:
                self.log_file.write(data.decode("utf-8", errors="replace"))
                self.log_file.flush()
            except Exception:
                pass

    def close(self):
        import os as _os
        # Restore original stdout/stderr
        _os.dup2(self._orig_stdout_fd, 1)
        _os.dup2(self._orig_stderr_fd, 2)
        # Close the read end so the reader thread exits
        try:
            _os.close(self._reader_fd)
        except OSError:
            pass
        self._thread.join(timeout=3)
        self.log_file.close()
        _os.close(self._orig_stdout_fd)
        _os.close(self._orig_stderr_fd)


def load_state(state_file):
    if Path(state_file).exists():
        with open(state_file) as f:
            return json.load(f)
    return {}


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    print(f"  State saved: {state_file}")


def show_resume_menu(state, state_file):
    """Show interactive resume menu when state exists.

    Returns the (possibly modified) state dict.
    """
    stations = state.get("stations", [])
    method = state.get("extraction_method", "?")
    stn_names = [s["name"] for s in stations]

    print(f"\n  Saved state found ({len(stations)} stations, method={method}):")
    print()

    # Show per-station progress
    steps = {
        "fullday":  "Step 2 (spectrogram)",
        "window":   "Step 3 (window)",
        "zoom":     "Step 4 (zoom)",
        "spline":   "Step 6 (extraction)",
        "wave":     "Step 6 (wave-fit)",
        "capt":     "Step 6 (CAPT)",
        "capt_seed":"Step 6a (CAPT seed)",
        "fft":      "Step 6 (fft)",
        "autocorr": "Step 6 (autocorr)",
        "cwt":      "Step 6 (cwt)",
    }
    for stn in stations:
        name = stn["name"]
        key = name.lower()
        done = []
        for suffix, label in steps.items():
            if f"{key}_{suffix}" in state:
                done.append(label)
        if done:
            # Deduplicate
            done = list(dict.fromkeys(done))
            print(f"    {name:<14s} {', '.join(done)}")
        else:
            print(f"    {name:<14s} (not started)")

    print()
    print("  Resume options:")
    print("    1. Continue from where you left off (default)")
    print("    2. Redo extraction for a specific station")
    print("    3. Redo ALL extractions (keep spectrograms + windows)")
    print("    4. Redo from window selection (keep spectrograms only)")
    print("    5. Start completely fresh")
    choice = input("  Choose [1]: ").strip() or "1"

    if choice == "1":
        return state

    elif choice == "2":
        print(f"  Stations: {', '.join(stn_names)}")
        stn_name = input("  Which station to redo? ").strip()
        key = stn_name.lower()
        # Clear all extraction keys for that station
        extraction_suffixes = ["spline", "wave", "capt", "capt_seed",
                                "fft", "autocorr", "cwt"]
        removed = []
        for suffix in extraction_suffixes:
            k = f"{key}_{suffix}"
            if k in state:
                del state[k]
                removed.append(k)
        if removed:
            print(f"  Cleared: {', '.join(removed)}")
        else:
            print(f"  No extraction state found for {stn_name}")
        save_state(state_file, state)
        return state

    elif choice == "3":
        # Clear all extraction keys for all stations
        extraction_suffixes = ["spline", "wave", "capt", "capt_seed",
                                "fft", "autocorr", "cwt"]
        removed = []
        for stn in stations:
            key = stn["name"].lower()
            for suffix in extraction_suffixes:
                k = f"{key}_{suffix}"
                if k in state:
                    del state[k]
                    removed.append(k)
        # Also clear extraction method so user can re-choose
        state.pop("extraction_method", None)
        print(f"  Cleared {len(removed)} extraction key(s) — will re-extract all stations")
        save_state(state_file, state)
        return state

    elif choice == "4":
        # Clear window + extraction keys for all stations
        clear_suffixes = ["window", "zoom_window", "zoom",
                          "spline", "wave", "capt", "capt_seed",
                          "fft", "autocorr", "cwt"]
        removed = []
        for stn in stations:
            key = stn["name"].lower()
            for suffix in clear_suffixes:
                k = f"{key}_{suffix}"
                if k in state:
                    del state[k]
                    removed.append(k)
        state.pop("extraction_method", None)
        print(f"  Cleared {len(removed)} key(s) — will redo windows + extraction")
        save_state(state_file, state)
        return state

    elif choice == "5":
        state = {}
        save_state(state_file, state)
        print("  State cleared — starting fresh")
        return state

    return state


def get_date_from_drf(drf_dir):
    """Get recording date from DRF."""
    try:
        import digital_rf as drf_lib
        import pandas as pd
        r = drf_lib.DigitalRFReader(str(drf_dir))
        ch = r.get_channels()[0]
        props = r.get_properties(ch)
        sr = float(props["samples_per_second"])
        b0, _ = r.get_bounds(ch)
        t0 = pd.Timestamp(b0 / sr, unit="s", tz="UTC")
        return t0.strftime("%Y-%m-%d")
    except Exception:
        return None


# ── Main workflow ─────────────────────────────────────────────────────────────

def run_workflow(args):
    event_dir = Path(args.event_dir).resolve()
    state_file = event_dir / "tid_workflow_state.json"
    state = load_state(state_file) if args.resume else {}
    if state and args.resume:
        state = show_resume_menu(state, state_file)

    # Start console logging
    from datetime import datetime, timezone
    _log_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    _log_dir = event_dir / "runs"
    _log_dir.mkdir(exist_ok=True)
    _log_path = _log_dir / f"{_log_ts}_workflow_console.log"
    _console_logger = ConsoleLogger(str(_log_path))

    print(f"\n{'='*60}")
    print(f"TID Workflow — {event_dir.name}")
    print(f"{'='*60}")

    # ── Step 1: Discover stations ─────────────────────────────────────────
    print(f"\n[Step 1] Discovering stations in {event_dir}...")
    if "stations" not in state:
        drf_dirs = discover_stations(event_dir)
        if not drf_dirs:
            sys.exit("No DRF stations found in event directory.")
        if args.stations:
            wanted = [s.strip().lower() for s in args.stations.split(",")]
            drf_dirs = [d for d in drf_dirs if d.name.lower() in wanted]
            print(f"  Using {len(drf_dirs)} station(s) (filtered by --stations):")
        else:
            print(f"  Found {len(drf_dirs)} station(s):")

        # Put the user's own station first, if specified
        if args.my_station:
            my = args.my_station.strip().lower()
            drf_dirs.sort(key=lambda d: 0 if d.name.lower() == my else 1)
        for d in drf_dirs:
            print(f"    {d.name}")

        # Get date from first station
        date_str = get_date_from_drf(drf_dirs[0])
        if not date_str:
            date_str = input("  Enter event date (YYYY-MM-DD): ").strip()
        print(f"  Event date: {date_str}")

        def _confirm_subchannel(drf_dir_s):
            """Step 1 body for one station: probe subchannels, generate
            thumbnails, confirm subchannel, resolve coords. Returns a
            station dict (same shape stations[] has always used)."""
            name = drf_dir_s.name.upper()
            print(f"\n  Station: {name}")
            print(f"    [Step 1] Subchannel confirmation for {name}...")

            print(f"    Probing subchannels...")
            subs = probe_subchannels(drf_dir_s, date_str, args.tx_freq_mhz)
            print(f"    Top subchannels by SNR:")
            for sub, snr, freq in subs[:5]:
                freq_str = f" — {freq/1e6:.3f} MHz" if freq else ""
                marker = " ← WWV 10 MHz" if freq and abs(freq/1e6 - 10.0) < 0.01 else ""
                print(f"      subchannel {sub}: {snr:.1f} dB{freq_str}{marker}")

            if len(subs) > 1:
                thumb_dir = event_dir / f'{name.lower()}_subchannels'
                thumb_dir.mkdir(exist_ok=True)
                print(f'    Generating subchannel thumbnails...')
                for sub_i, snr_i, freq_i in subs:
                    thumb = thumb_dir / f'sub{sub_i:02d}.png'
                    if not thumb.exists():
                        run([
                            'python3', tool('drf_spectrogram.py'),
                            drf_dir_s,
                            '--subchannel', str(sub_i),
                            '--output', str(thumb),
                            '--start', '00:00', '--end', '24:00',
                            '--ylim=-5,5', '--dpi', '60',
                            '--callsign', name,
                        ])
                    freq_str = f' {freq_i/1e6:.3f} MHz' if freq_i else ''
                    print(f'      sub{sub_i:02d}.png — subchannel {sub_i}{freq_str} SNR={snr_i:.1f} dB')
                print(f'    Open thumbnails in: {thumb_dir}')
                print(f'    Look for clear carrier near 0 Hz = WWV 10 MHz')
            else:
                print(f'    Single subchannel — skipping thumbnail preview '
                      f'(Step 2\'s full-day spectrogram covers this)')

            best_sub, reason = best_subchannel(subs, args.tx_freq_mhz)
            if best_sub is not None:
                print(f'    Suggested: subchannel {best_sub} ({reason})')
            while True:
                try:
                    prompt = f'    Enter subchannel'
                    if best_sub is not None:
                        prompt += f' [{best_sub}]'
                    sub_input = input(prompt + ': ').strip()
                    subchannel = int(sub_input) if sub_input else (best_sub if best_sub is not None else None)
                    if subchannel is None:
                        print('    Please enter a number')
                        continue
                    break
                except ValueError:
                    print('    Please enter a number')

            rx_lat, rx_lon = get_station_coords(name, drf_dir_s, event_dir=event_dir)

            grid_sq = "?"
            for k, (la, lo, gr) in KNOWN_STATIONS.items():
                if k in name.upper() or name.upper() in k:
                    grid_sq = gr
                    break
            ipp_lat, ipp_lon = midpoint(rx_lat, rx_lon, args.tx_lat, args.tx_lon)
            print(f"    IPP midpoint: {ipp_lat:.4f}N, {abs(ipp_lon):.4f}{'W' if ipp_lon < 0 else 'E'}")

            return {
                "name": name,
                "drf_dir": str(drf_dir_s),
                "subchannel": subchannel,
                "receiver_lat": rx_lat,
                "receiver_lon": rx_lon,
                "ipp_lat": ipp_lat,
                "ipp_lon": ipp_lon,
                "grid": grid_sq,
                "date_str": date_str,
            }

        def _fullday_and_window(stn):
            """Step 2 (full-day spectrogram) + Step 3 (window selection,
            with the 'apply to remaining' propagation offer) for one
            already-subchannel-confirmed station. Mirrors the same state
            keys / file paths the Steps 2-9 loop later expects, so when
            that loop reaches this station it will find everything
            already done and just skip straight past it."""
            name = stn["name"]
            drf_dir_s = stn["drf_dir"]
            sub = stn["subchannel"]
            stn_key = name.lower()
            fullday_png = event_dir / f"{stn_key}_fullday.png"
            window_json = event_dir / f"{stn_key}_fullday_window.json"

            print(f"\n{'─'*60}")
            print(f"Station: {name}  (subchannel {sub})")
            print(f"{'─'*60}")

            if f"{stn_key}_fullday" not in state:
                print(f"\n[Step 2] Full-day spectrogram for {name}...")
                r = run([
                    "python3", tool("drf_spectrogram.py"),
                    drf_dir_s,
                    "--subchannel", str(sub),
                    "--output", str(fullday_png),
                    "--start", "00:00", "--end", "24:00",
                    "--ylim=-5,5", "--dpi", "100",
                    "--callsign", name,
                    "--grid", stn.get("grid", "?"),
                ])
                if r.returncode != 0:
                    print(f"  ERROR: spectrogram failed for {name}")
                    return
                state[f"{stn_key}_fullday"] = str(fullday_png)
                save_state(state_file, state)

            if f"{stn_key}_window" not in state:
                print(f"\n[Step 3] Select TID window for {name}...")
                print("  → Drag yellow region to bracket the TID, press S to save, Q to quit")
                run(["python3", tool("tid_quicklook.py"),
                     "--spectrogram", str(fullday_png)])
                if not window_json.exists():
                    print(f"  WARNING: No window saved for {name} — skipping")
                    return
                with open(window_json) as f:
                    wj = json.load(f)
                state[f"{stn_key}_window"] = wj
                state[f"{stn_key}_zoom_window"] = wj
                save_state(state_file, state)

                # Offer to apply this window to every OTHER requested
                # station up front, by name -- they don't need to have
                # gone through Step 1 yet for this to work, since we're
                # only pre-seeding state[] here, not full station dicts.
                other_names = [d.name.upper() for d in drf_dirs
                               if d.name.upper() != name]
                remaining = [n for n in other_names
                             if f"{n.lower()}_window" not in state]
                if remaining:
                    ans = input(f"  Apply {h_to_hhmm(wj['t_start_utc_hours'])}–"
                                f"{h_to_hhmm(wj['t_end_utc_hours'])} to all "
                                f"remaining stations? [y/N]: ").strip().lower()
                    if ans == "y":
                        for rn in remaining:
                            rk = rn.lower()
                            state[f"{rk}_window"] = wj
                            state[f"{rk}_zoom_window"] = wj
                            rk_win_json = event_dir / f"{rk}_fullday_window.json"
                            with open(rk_win_json, "w") as _f:
                                json.dump(wj, _f, indent=2)
                        save_state(state_file, state)
                        print(f"  Applied to: {remaining}")

        # Keystone fast-path: if --my-station is set, take that station
        # all the way through subchannel confirmation, full-day
        # spectrogram, AND window selection before any other station is
        # even probed for its subchannel. This is what makes the
        # keystone's own full-day view (not anyone else's) the thing
        # you're actually looking at when you pick the TID window.
        stations = []
        remaining_dirs = list(drf_dirs)
        if args.my_station:
            my = args.my_station.strip().lower()
            keystone_dir = next((d for d in remaining_dirs
                                  if d.name.lower() == my), None)
            if keystone_dir is not None:
                remaining_dirs.remove(keystone_dir)
                keystone_stn = _confirm_subchannel(keystone_dir)
                stations.append(keystone_stn)
                _fullday_and_window(keystone_stn)
            else:
                print(f"  WARNING: --my-station '{args.my_station}' not "
                      f"found among discovered stations — proceeding "
                      f"without a keystone fast-path.")

        # Remaining stations: subchannel confirmation only, same as
        # before. Their full-day spectrogram + window selection (or the
        # propagated window from the keystone, if you said yes above)
        # happens later in the Steps 2-9 loop, per station, in order.
        for drf_dir_s in remaining_dirs:
            stations.append(_confirm_subchannel(drf_dir_s))

        state["stations"] = stations
        state["date_str"] = date_str
        save_state(state_file, state)
    else:
        stations = state["stations"]
        date_str = state.get("date_str") or stations[0].get("date_str", "2024-01-01")
        print(f"  Resuming with {len(stations)} station(s): "
              f"{', '.join(s['name'] for s in stations)}")

    # ── Method selection ─────────────────────────────────────────────────
    if "extraction_method" not in state:
        print("\nExtraction method:")
        print("  1. cwt-prophet   (anchor-guided — recommended)")
        print("  2. autocorr      (automated, Gwyn G3ZIL method)")
        print("  3. cwt           (automated, CWT multi-peak tracker)")
        print("  4. wave-fit      (sine fit to clicked cycle points)")
        choice = input("Choose [1]: ").strip() or "1"
        method = {"1": "cwt-prophet", "2": "autocorr",
                  "3": "cwt", "4": "wave-fit"}.get(choice, "cwt-prophet")
        state["extraction_method"] = method
        save_state(state_file, state)
    else:
        method = state["extraction_method"]
    print(f"  Extraction method: {method}")

    # ── IPP midpoint selection ────────────────────────────────────────
    if "use_ipp" not in state:
        print("\nDOA coordinate system:")
        print("  1. IPP midpoints  (recommended — use great-circle midpoint")
        print("                     between station and WWV as the DOA coord)")
        print("  2. Station coords (use raw receiver coordinates — for")
        print("                     comparison or when IPP is pre-computed)")
        ipp_choice = input("Choose [1]: ").strip() or "1"
        state["use_ipp"] = (ipp_choice != "2")
        save_state(state_file, state)
    use_ipp = state["use_ipp"]
    print(f"  DOA coords: {'IPP midpoints' if use_ipp else 'station coords'}")

    # ── Steps 2-9: Per-station workflow ───────────────────────────────────
    for stn in stations:
        name = stn["name"]
        drf_dir_s = stn["drf_dir"]
        sub = stn["subchannel"]
        date_str = stn["date_str"]
        stn_key = name.lower()

        print(f"\n{'─'*60}")
        print(f"Station: {name}  (subchannel {sub})")
        print(f"{'─'*60}")

        fullday_png  = event_dir / f"{stn_key}_fullday.png"
        zoom_png       = event_dir / f"{stn_key}_tid_zoom.png"
        zoom_clean_png = event_dir / f"{stn_key}_tid_zoom_clean.png"
        fft_csv      = event_dir / f"{stn_key}_fft_tid.csv"
        corridor_json = event_dir / f"{stn_key}_tid_zoom_clean_corridor.json"
        sgolay_csv   = event_dir / f"{stn_key}_sgolay_tid.csv"
        window_json  = event_dir / f"{stn_key}_fullday_window.json"
        zoom_window  = event_dir / f"{stn_key}_tid_zoom_window.json"

        # Step 2: Full-day spectrogram
        if f"{stn_key}_fullday" not in state:
            print(f"\n[Step 2] Full-day spectrogram for {name}...")
            r = run([
                "python3", tool("drf_spectrogram.py"),
                drf_dir_s,
                "--subchannel", str(sub),
                "--output", str(fullday_png),
                "--start", "00:00", "--end", "24:00",
                "--ylim=-5,5", "--dpi", "100",
                "--callsign", name,
                "--grid", stn.get("grid", "?"),
            ])
            if r.returncode != 0:
                print(f"  ERROR: spectrogram failed for {name}")
                continue
            state[f"{stn_key}_fullday"] = str(fullday_png)
            save_state(state_file, state)

        # Step 3: User selects TID window
        if f"{stn_key}_window" not in state:
            print(f"\n[Step 3] Select TID window for {name}...")
            print("  → Drag yellow region to bracket the TID, press S to save, Q to quit")
            run(["python3", tool("tid_quicklook.py"),
                 "--spectrogram", str(fullday_png)])
            if not window_json.exists():
                print(f"  WARNING: No window saved for {name} — skipping")
                continue
            with open(window_json) as f:
                wj = json.load(f)
            state[f"{stn_key}_window"] = wj
            # Default zoom_window to window — Step 5 may refine it
            state[f"{stn_key}_zoom_window"] = wj
            save_state(state_file, state)
            # Offer to apply same window to all remaining stations
            remaining = [s for s in stations
                         if f"{s['name'].lower()}_window" not in state
                         and s["name"] != name]
            if remaining:
                ans = input(f"  Apply {h_to_hhmm(wj["t_start_utc_hours"])}–"
                            f"{h_to_hhmm(wj["t_end_utc_hours"])} to all "
                            f"remaining stations? [y/N]: ").strip().lower()
                if ans == "y":
                    for rs in remaining:
                        rk = rs["name"].lower()
                        state[f"{rk}_window"] = wj
                        state[f"{rk}_zoom_window"] = wj
                        rk_win_json = event_dir / f"{rk}_fullday_window.json"
                        with open(rk_win_json, "w") as _f:
                            json.dump(wj, _f, indent=2)
                    save_state(state_file, state)
                    print(f"  Applied to: {[s['name'] for s in remaining]}")
        else:
            wj = state[f"{stn_key}_window"]
            print(f"  Window: {h_to_hhmm(wj['t_start_utc_hours'])}"
                  f"–{h_to_hhmm(wj['t_end_utc_hours'])} UTC")

        # Step 4: Zoomed spectrogram (clean — no overlay, used for corridor clicking)
        if f"{stn_key}_zoom" not in state:
            print(f"\n[Step 4] Zoomed spectrogram for {name}...")
            r = run([
                "python3", tool("drf_spectrogram.py"),
                drf_dir_s,
                "--subchannel", str(sub),
                "--output", str(zoom_clean_png),
                "--window", str(window_json),
                "--ylim=-5,5", "--dpi", "150",
                "--callsign", name,
                "--grid", stn.get("grid", "?"),
            ])
            if r.returncode != 0:
                print(f"  ERROR: zoom spectrogram failed for {name}")
                continue
            state[f"{stn_key}_zoom"] = str(zoom_clean_png)
            save_state(state_file, state)

        # Step 5: Opt-in window refinement (skipped by default)
        if f"{stn_key}_zoom_window" not in state:
            ans = input(f"  Refine window for {name}? [y/N]: ").strip().lower()
            if ans == "y":
                print(f"\n[Step 5] Refine TID window for {name}...")
                print("  → Drag yellow region to refine, S to save, Q to keep")
                run(["python3", tool("tid_quicklook.py"),
                     "--spectrogram", str(zoom_clean_png),
                     "--seg-start", str(wj["t_start_utc_hours"]),
                     "--seg-end",   str(wj["t_end_utc_hours"])])
                if zoom_window.exists():
                    with open(zoom_window) as f:
                        zwj = json.load(f)
                    state[f"{stn_key}_zoom_window"] = zwj
            t0_h = state[f"{stn_key}_zoom_window"]["t_start_utc_hours"]
            t1_h = state[f"{stn_key}_zoom_window"]["t_end_utc_hours"]
            save_state(state_file, state)
        else:
            zwj = state[f"{stn_key}_zoom_window"]
            t0_h = zwj["t_start_utc_hours"]
            t1_h = zwj["t_end_utc_hours"]
        print(f"  Analysis window: {h_to_hhmm(t0_h)}–{h_to_hhmm(t1_h)} UTC")
        if method == "wave-fit":
            # Step 6: Wave-fit extraction via tid_spect_click --wave-only
            wave_csv = event_dir / f"{stn_key}_wave_tid.csv"
            wave_key = f"{stn_key}_wave"
            if wave_key not in state:
                while True:
                    print(f"")
                    print(f"  ┌───────────────────────────────────────────────────────┐")
                    print(f"  │  [Step 6] Wave-fit extraction for {name:<14s}      │")
                    print(f"  │                                                       │")
                    print(f"  │  1. Click 3+ points along the TID oscillation         │")
                    print(f"  │     (peaks and troughs of the wave)                   │")
                    print(f"  │  2. Press F to fit and save                           │")
                    print(f"  │  3. If fit looks good → press Q to close              │")
                    print(f"  │     If not → press W to redo, adjust clicks, F again  │")
                    print(f"  │                                                       │")
                    print(f"  │  Keys: F=fit+save  W=redo  Q=done (close window)      │")
                    print(f"  └───────────────────────────────────────────────────────┘")
                    run([
                        "python3", tool("tid_spect_click.py"),
                        "--spectrogram", str(zoom_clean_png),
                        "--name", name,
                        "--seg-start", str(max(0.0, t0_h)),
                        "--seg-end",   str(t1_h),
                        "--wave-only",
                    ])
                    if wave_csv.exists():
                        break
                    print(f"  ⚠️  No wave-fit CSV saved (did you press F to fit?)")
                    retry = input(f"  Retry wave-fit for {name}? [Y/n/skip]: ").strip().lower()
                    if retry == "n" or retry == "skip":
                        print(f"  Skipping {name}")
                        break
                if not wave_csv.exists():
                    continue
                state[wave_key] = str(wave_csv)
                save_state(state_file, state)
                print(f"  ✓ Wave-fit CSV: {wave_csv.name}")
            else:
                print(f"  ✓ Wave-fit CSV: {wave_csv.name} (already done)")

        elif method in ("sgolay-ridge", "cwt-prophet"):
            # Step 6: Anchor-guided cwt-prophet or sgolay-ridge via tid_spect_click
            # Pass 0: cwt-prophet auto-runs on open, user corrects with anchors
            # P=re-run Prophet, E=export prophet, X=export spline, R=reset, Q=quit
            spline_csv = event_dir / f"{stn_key}_spline_tid.csv"
            spline_key = f"{stn_key}_spline"
            prophet_csv = event_dir / f"{stn_key}_prophet_tid.csv"
            if spline_key not in state:
                while True:
                    if method == "cwt-prophet":
                        print(f"")
                        print(f"  ┌──────────────────────────────────────────────────────────┐")
                        print(f"  │  [Step 6] Doppler extraction for {name:<14s}          │")
                        print(f"  │                                                          │")
                        print(f"  │  Auto-trace shown (green/yellow).                        │")
                        print(f"  │                                                          │")
                        print(f"  │  If trace follows the carrier well:                      │")
                        print(f"  │    → Press E to accept and export                        │")
                        print(f"  │                                                          │")
                        print(f"  │  If trace does NOT follow the carrier:                   │")
                        print(f"  │    1. Click along the carrier from left to right          │")
                        print(f"  │    2. Press X to export your trace                       │")
                        print(f"  │                                                          │")
                        print(f"  │  Keys: E=accept auto-trace  X=export clicked trace       │")
                        print(f"  │        Z=undo last click  R=reset  Q=done (close window)                │")
                        print(f"  └──────────────────────────────────────────────────────────┘")
                    else:  # sgolay-ridge
                        print(f"")
                        print(f"  ┌──────────────────────────────────────────────────────┐")
                        print(f"  │  [Step 6] Sgolay-ridge extraction for {name:<12s}  │")
                        print(f"  │                                                      │")
                        print(f"  │  1. Click anchor points to define corridor            │")
                        print(f"  │  2. Press X to export spline CSV                     │")
                        print(f"  │  3. Press Q to close                                 │")
                        print(f"  │                                                      │")
                        print(f"  │  Keys: X=export  Z=undo  R=reset  Q=quit             │")
                        print(f"  └──────────────────────────────────────────────────────┘")
                    run([
                        "python3", tool("tid_spect_click.py"),
                        "--spectrogram", str(zoom_clean_png),
                        "--name", name,
                        "--drf-dir", drf_dir_s,
                        "--subchannel", str(sub),
                        "--corridor-width", "0.4",
                        "--seg-start", str(max(0.0, t0_h)),
                        "--seg-end",   str(t1_h),
                    ])
                    # Check for either prophet or spline CSV
                    if prophet_csv.exists() or spline_csv.exists():
                        break
                    print(f"  ⚠️  No CSV saved (did you press E or X before Q?)")
                    retry = input(f"  Retry for {name}? [Y/n/skip]: ").strip().lower()
                    if retry == "n" or retry == "skip":
                        print(f"  Skipping {name}")
                        break
                if not (prophet_csv.exists() or spline_csv.exists()):
                    continue
                # Prefer prophet CSV if it exists (E key export)
                if prophet_csv.exists():
                    state[spline_key] = str(prophet_csv)
                    print(f"  ✓ Prophet CSV: {prophet_csv.name}")
                else:
                    state[spline_key] = str(spline_csv)
                    print(f"  ✓ Spline CSV: {spline_csv.name}")
                save_state(state_file, state)
            else:
                csv_name = Path(state[spline_key]).name
                print(f"  ✓ {csv_name} (already done)")
        else:  # method in (fft, autocorr, cwt)
            # Step 6: Automated extraction
            csv_key = f"{stn_key}_{method.replace('-', '_')}"
            out_csv = event_dir / f"{stn_key}_{method}_tid.csv"
            if csv_key not in state:
                print(f"")
                print(f"  ┌──────────────────────────────────────────────────────┐")
                print(f"  │  [Step 6] Automated {method} extraction for {name:<8s}  │")
                print(f"  │                                                      │")
                print(f"  │  Fully automated — no interaction needed.             │")
                print(f"  │  Extracting Doppler from DRF...                       │")
                print(f"  └──────────────────────────────────────────────────────┘")
                r = run([
                    "python3", tool("drf_to_doppler.py"),
                    drf_dir_s,
                    "--subchannel", str(sub),
                    "--start", h_to_iso(date_str, t0_h),
                    "--end",   h_to_iso(date_str, t1_h),
                    "--decim-seconds", "60",
                    "--method", method,
                    "--output", str(out_csv),
                ])
                if r.returncode != 0:
                    print(f"  ERROR: {method} extraction failed for {name}")
                    continue
                state[csv_key] = str(out_csv)
                # Keep fft_csv alias for overlay step
                if method == "fft":
                    state[f"{stn_key}_fft"] = str(out_csv)
                save_state(state_file, state)
            else:
                out_csv = Path(state[csv_key])
                print(f"  {method} CSV: {out_csv.name} (already done)")
            fft_csv = out_csv  # used by overlay step

            # Step 7: Zoomed spectrogram with FFT overlay
            if f"{stn_key}_zoom_overlay" not in state:
                print(f"\n[Step 7] Zoomed spectrogram with FFT overlay for {name}...")
                r = run([
                    "python3", tool("drf_spectrogram.py"),
                    drf_dir_s,
                    "--subchannel", str(sub),
                    "--output", str(zoom_png),
                    "--window", str(window_json),
                    "--ylim=-5,5", "--dpi", "150",
                    "--callsign", name,
                    "--grid", stn.get("grid", "?"),
                    f"--overlay={fft_csv}:FFT",
                ])
                if r.returncode != 0:
                    print(f"  ERROR: overlay spectrogram failed for {name}")
                    continue
                state[f"{stn_key}_zoom_overlay"] = True
                save_state(state_file, state)

    # ── Window review before extraction ─────────────────────────────────
    while True:
        print(f"\n{'─'*60}")
        print("Window summary (before extraction):")
        all_windowed = True
        for stn in stations:
            stn_key = stn["name"].lower()
            zwj = state.get(f"{stn_key}_zoom_window")
            if zwj:
                t0 = zwj["t_start_utc_hours"]
                t1 = zwj["t_end_utc_hours"]
                print(f"  {stn['name']:<12} {h_to_hhmm(t0)}–{h_to_hhmm(t1)} UTC")
            else:
                print(f"  {stn['name']:<12} (no window)")
                all_windowed = False
        print()
        ans = input("Proceed with extraction? [Y] or station name to redo window: ").strip()
        if ans.upper() in ("", "Y", "YES"):
            break
        redo_name = ans.upper()
        redo_stn = next((s for s in stations if s["name"].upper() == redo_name), None)
        if redo_stn is None:
            print(f"  Unknown station '{ans}' — enter a station name or Y to proceed")
            continue
        # Clear window state for this station so Steps 3-5 re-run
        stn_key = redo_stn["name"].lower()
        for key in [f"{stn_key}_window", f"{stn_key}_zoom",
                    f"{stn_key}_zoom_window", f"{stn_key}_zoom_overlay",
                    f"{stn_key}_fft", f"{stn_key}_corridor", f"{stn_key}_sgolay"]:
            state.pop(key, None)
        save_state(state_file, state)
        print(f"  Cleared {redo_stn['name']} — re-running Steps 3-5...")
        # Re-run Steps 3-5 for this station only
        name = redo_stn["name"]
        drf_dir_s = redo_stn["drf_dir"]
        sub = redo_stn["subchannel"]
        date_str = redo_stn["date_str"]
        fullday_png    = event_dir / f"{stn_key}_fullday.png"
        zoom_clean_png = event_dir / f"{stn_key}_tid_zoom_clean.png"
        window_json    = event_dir / f"{stn_key}_fullday_window.json"
        zoom_window    = event_dir / f"{stn_key}_tid_zoom_window.json"
        # Step 3 redo
        print(f"\n[Step 3] Select TID window for {name}...")
        run(["python3", tool("tid_quicklook.py"),
             "--spectrogram", str(fullday_png)])
        if not window_json.exists():
            print(f"  WARNING: No window saved — skipping")
            continue
        with open(window_json) as _f:
            wj = json.load(_f)
        state[f"{stn_key}_window"] = wj
        save_state(state_file, state)
        # Step 4 redo — use fullday window for zoom extent
        print(f"\n[Step 4] Zoomed spectrogram for {name}...")
        run([
            "python3", tool("drf_spectrogram.py"),
            drf_dir_s, "--subchannel", str(sub),
            "--output", str(zoom_clean_png),
            "--window", str(window_json),
            "--ylim=-5,5", "--dpi", "150",
            "--callsign", name,
            "--grid", redo_stn.get("grid", "?"),
        ])
        state[f"{stn_key}_zoom"] = str(zoom_clean_png)
        save_state(state_file, state)
        # Step 5 redo — pre-position to Step 3 window
        print(f"\n[Step 5] Refine TID window for {name}...")
        run(["python3", tool("tid_quicklook.py"),
             "--spectrogram", str(zoom_clean_png),
             "--seg-start", str(wj["t_start_utc_hours"]),
             "--seg-end",   str(wj["t_end_utc_hours"])])
        if zoom_window.exists():
            with open(zoom_window) as _f:
                zwj = json.load(_f)
            state[f"{stn_key}_zoom_window"] = zwj
        else:
            state[f"{stn_key}_zoom_window"] = wj
            zwj = wj
        # Regenerate zoom PNG with refined window so corridor clicking
        # uses the correct time range
        print(f"  Regenerating zoom spectrogram with refined window...")
        run([
            "python3", tool("drf_spectrogram.py"),
            drf_dir_s, "--subchannel", str(sub),
            "--output", str(zoom_clean_png),
            "--window", str(zoom_window) if zoom_window.exists() else str(window_json),
            "--ylim=-5,5", "--dpi", "150",
            "--callsign", name,
            "--grid", redo_stn.get("grid", "?"),
        ])
        state[f"{stn_key}_zoom"] = str(zoom_clean_png)
        save_state(state_file, state)

    # ── Step 10: Check overlap and run DOA ────────────────────────────────
    print(f"\n{'─'*60}")
    print("[Step 8] DOA")
    print(f"{'─'*60}")

    # Collect completed stations — selected method first, then fallbacks
    completed = []
    for stn in stations:
        stn_key = stn["name"].lower()
        # Build candidate list with SELECTED METHOD FIRST
        prophet_path = event_dir / f"{stn_key}_prophet_tid.csv"
        spline_path = event_dir / f"{stn_key}_spline_tid.csv"
        all_csvs = {
            "spline":       spline_path,
            "sgolay-ridge": event_dir / f"{stn_key}_sgolay_tid.csv",
            "fft":          event_dir / f"{stn_key}_fft_tid.csv",
            "autocorr":     event_dir / f"{stn_key}_autocorr_tid.csv",
            "cwt":          event_dir / f"{stn_key}_cwt_tid.csv",
            "wave-fit":     event_dir / f"{stn_key}_wave_tid.csv",
            # E-key export (prophet_tid.csv) is the documented/preferred
            # action when the auto-trace looks good -- check for it
            # first, falling back to the X-key spline export.
            "cwt-prophet":  prophet_path if prophet_path.exists() else spline_path,
        }
        # Priority: selected method > spline > others
        candidates = [(all_csvs.get(method, ""), method)]
        for meth, csv in all_csvs.items():
            if meth != method:
                candidates.append((csv, meth))
        found = False
        for csv, meth in candidates:
            if csv and Path(csv).exists():
                completed.append({
                    "name": stn["name"],
                    "file": str(csv),
                    "method": meth,
                    "lat": stn["receiver_lat"],
                    "lon": stn["receiver_lon"],
                })
                found = True
                break
        if not found:
            print(f"  ⚠️  No extraction CSV found for {stn['name']} — excluded from DOA")

    if len(completed) < 3:
        print(f"  Only {len(completed)} station(s) completed — need ≥3 for DOA")
        return

    # Show which CSV and method will be used per station
    print(f"\n  Extraction files for DOA:")
    for s in completed:
        print(f"    {s['name']:<14s} method={s['method']:<12s} {Path(s['file']).name}")

    # Show which CSV and method will be used per station
    print(f"\n  Extraction files for DOA:")
    for s in completed:
        print(f"    {s['name']:<14s} method={s['method']:<12s} {Path(s['file']).name}")

    # Check time overlap
    import pandas as pd
    dfs = {}
    for stn in completed:
        df = pd.read_csv(stn["file"], parse_dates=["timestamp_utc"])
        dfs[stn["name"]] = df
        print(f"  {stn['name']}: {df.timestamp_utc.min()} to "
              f"{df.timestamp_utc.max()} ({len(df)} rows)")

    t_start = max(df.timestamp_utc.min() for df in dfs.values())
    t_end   = min(df.timestamp_utc.max() for df in dfs.values())
    overlap_min = (t_end - t_start).total_seconds() / 60
    print(f"\n  Overlap: {t_start} to {t_end} ({overlap_min:.0f} min)")

    if overlap_min < 60:
        print(f"\n  ⚠️ WARNING: only {overlap_min:.0f} min overlap (need ≥60 min for reliable DOA)")
        print("  Stations with misaligned windows:")
        for stn in completed:
            df = dfs[stn["name"]]
            print(f"    {stn['name']}: {df.timestamp_utc.min()} to {df.timestamp_utc.max()}")
        print("\n  Options:")
        print("  1. Continue anyway (result may be unreliable)")
        print("  2. Quit and re-run Steps 3-5 with better-aligned windows")
        choice = input("  Choose [1/2]: ").strip()
        if choice == "2":
            print("  Quitting. Delete tid_workflow_state.json entries for")
            print("  affected stations and re-run with --resume to redo windows.")
            return

    # Write event config
    event_config = {
        "event_start_utc": t_start.isoformat(),
        "event_end_utc":   t_end.isoformat(),
        "resample_seconds": 60,
        "use_bandpass": False,
        "use_ipp": use_ipp,
        "min_expected_speed_m_s": 100,
        "stations": completed,
    }
    # Always persist max_lag_seconds so re-running from the saved JSON
    # uses the same lag window as the interactive session. When --max-lag
    # is not given, the auto-computed value from tid_doa.py is used, but
    # that value is not yet available here -- so we store the auto-computed
    # bound: largest_baseline_km * 1000 / min_expected_speed_m_s.
    if args.max_lag is not None:
        event_config["max_lag_seconds"] = args.max_lag * 60
        print(f"  max_lag_seconds: {args.max_lag * 60:.0f} s ({args.max_lag:.0f} min)")
    else:
        # Reproduce tid_doa.py's auto-computation so the value is explicit
        import math as _math
        def _hav_km(la1, lo1, la2, lo2):
            R = 6371.0
            f1, f2 = _math.radians(la1), _math.radians(la2)
            df = _math.radians(la2 - la1)
            dl = _math.radians(lo2 - lo1)
            a = (_math.sin(df/2)**2 +
                 _math.cos(f1)*_math.cos(f2)*_math.sin(dl/2)**2)
            return 2 * R * _math.asin(_math.sqrt(a))
        WWV_LAT, WWV_LON = 40.6776, -105.0405
        mids = []
        for _s in completed:
            _lat, _lon = _s["lat"], _s["lon"]
            _mlat = (_lat + WWV_LAT) / 2
            _mlon = (_lon + WWV_LON) / 2
            mids.append((_mlat, _mlon))
        max_bl = 0.0
        for _i in range(len(mids)):
            for _j in range(_i+1, len(mids)):
                max_bl = max(max_bl, _hav_km(*mids[_i], *mids[_j]))
        min_spd = event_config.get("min_expected_speed_m_s", 100.0)
        auto_lag = max_bl * 1000.0 / min_spd
        event_config["max_lag_seconds"] = round(auto_lag)
        print(f"  max_lag_seconds: {auto_lag:.0f} s (auto, "
              f"largest baseline {max_bl:.0f} km / {min_spd:.0f} m/s)")
    config_path = event_dir / "tid_workflow_event.json"
    with open(config_path, "w") as f:
        json.dump(event_config, f, indent=2)
    print(f"\n  Event config: {config_path.name}")

    # Run DOA — with interactive drop-station loop
    active_stations = list(completed)
    doa_results = []
    while True:
        event_config["stations"] = active_stations
        with open(config_path, "w") as f:
            json.dump(event_config, f, indent=2)
        stn_names = [s["name"] for s in active_stations]
        print(f"\n  Running DOA with {len(active_stations)} stations: {stn_names}")
        r = run(["python3", tool("tid_doa.py"), str(config_path)])
        if r.returncode == 0:
            state["doa_done"] = True
            save_state(state_file, state)
        # Parse speed/direction from run log
        speed, from_deg, n_flags = None, None, 0
        log_files = sorted((event_dir / "runs").glob("*.log"))
        if log_files:
            log_txt = log_files[-1].read_text()
            for line in log_txt.splitlines():
                if line.startswith("Phase speed:"):
                    try: speed = float(line.split()[2])
                    except: pass
                if line.startswith("Coming from:"):
                    try: from_deg = float(line.split()[2])
                    except: pass
                if "diagnostic(s) outside" in line:
                    try: n_flags = int(line.strip().split()[1])
                    except: pass
        doa_results.append({
            "stations": list(stn_names),
            "speed": speed,
            "from": from_deg,
            "flags": n_flags,
        })
        if len(doa_results) > 1:
            print(f"\n  Comparison:")
            print(f"  {'Stations':<35} {'Speed':>8} {'From':>7} {'Flags':>6}")
            print(f"  {'-'*60}")
            for res in doa_results:
                sp = f"{res['speed']:.0f} m/s" if res["speed"] else "  ---  "
                fr = f"{res['from']:.0f} deg" if res["from"] else "  ---"
                stns = ",".join(res["stations"])
                print(f"  {stns:<35} {sp:>8} {fr:>7} {res['flags']:>6}")
            print(f"  {'-'*60}")
        if len(active_stations) <= 3:
            break
        ans = input("\n  Drop a station and re-run DOA? "
                    "[station name or Enter to finish]: ").strip().upper()
        if not ans:
            break
        match = [s for s in active_stations if s["name"].upper() == ans]
        if not match:
            print(f"  Unknown station '{ans}' — valid: {[s['name'] for s in active_stations]}")
            continue
        active_stations = [s for s in active_stations if s["name"].upper() != ans]
        print(f"  Dropped {ans}. Remaining: {[s['name'] for s in active_stations]}")
    print(f"\n{'='*60}")
    print("Workflow complete.")
    print(f"{'='*60}")

    # Save console log
    _console_logger.close()
    print(f"Console log saved: {_log_path}")

# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="Guided TID direction-of-arrival workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--stations", default=None, metavar="A,B,C",
                   help="Comma-separated station names to use (default: all found)")
    p.add_argument("--my-station", default=None, metavar="NAME",
                   help="Station to process first (e.g. your own callsign). "
                        "Useful for setting the TID window on a familiar trace first.")
    p.add_argument("--event-dir", required=True, metavar="DIR",
                   help="Directory containing DRF station subdirectories")
    p.add_argument("--resume", action="store_true",
                   help="Resume from saved state (tid_workflow_state.json)")
    p.add_argument("--tx-lat", type=float, default=40.68, metavar="DEG",
                   help="Transmitter latitude (default: WWV 40.68N)")
    p.add_argument("--tx-lon", type=float, default=-105.04, metavar="DEG",
                   help="Transmitter longitude (default: WWV -105.04E)")
    p.add_argument("--tx-name", default="WWV", metavar="NAME",
                   help="Transmitter name for labeling (default: WWV)")
    p.add_argument("--tx-freq-mhz", type=float, default=10.0, metavar="MHZ",
                   help="Transmitter frequency MHz for subchannel selection (default 10.0)")
    p.add_argument("--sgolay-window", type=float, default=21.0, metavar="MIN",
                   help="SGOLAY smoothing window in minutes (default 21)")
    p.add_argument("--max-lag", type=float, default=None, metavar="MIN",
                   help="Maximum xcorr lag in minutes (default: auto). Set to ~1/3 of TID period.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_workflow(args)
