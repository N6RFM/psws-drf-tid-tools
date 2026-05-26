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
  Step 6:  sgolay-ridge: corridor clicking  |  fft/autocorr/cwt: automated extraction
  Step 7:  sgolay-ridge: sgolay extraction  |  fft: overlay spectrogram  |  autocorr/cwt: (none)
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
KNOWN_STATIONS = {
    "W7LUX":   (35.1042, -111.7083),
    "AC0G_ND": (46.8750,  -96.8333),
    "N4RVE":   (44.9700, -123.4800),
    "N5BRG":   (35.6500,  -97.4800),
    "N6RFM":   (32.9400,  -97.2100),
    "AA6BD":   (35.0600,  -85.1300),
    "K0LO":    (39.9500, -105.1500),
    "W3HH":    (39.9500,  -75.1500),
    "WA2HXB":  (41.0500,  -74.1300),
    "KD9UKK":  (41.7000,  -86.2300),
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


def get_station_coords(name, drf_dir):
    """Get receiver lat/lon: DRF metadata → callsign DB → user input."""
    # 1. Try DRF metadata
    lat, lon = read_drf_metadata(drf_dir)
    if lat is not None:
        print(f"    Coords from DRF metadata: {lat:.4f}N, {lon:.4f}E")
        return lat, lon

    # 2. Try callsign database
    key = name.upper().replace("-", "_")
    for k, (la, lo) in KNOWN_STATIONS.items():
        if k in key or key in k:
            print(f"    Coords from callsign DB ({k}): {la:.4f}N, {lo:.4f}E")
            return la, lo

    # 3. User input
    print(f"    Coords not found for {name}.")
    while True:
        try:
            lat = float(input(f"    Enter latitude for {name} (decimal degrees N): "))
            lon = float(input(f"    Enter longitude for {name} (decimal degrees E, negative=W): "))
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


def load_state(state_file):
    if Path(state_file).exists():
        with open(state_file) as f:
            return json.load(f)
    return {}


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    print(f"  State saved: {state_file}")


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
        for d in drf_dirs:
            print(f"    {d.name}")

        # Get date from first station
        date_str = get_date_from_drf(drf_dirs[0])
        if not date_str:
            date_str = input("  Enter event date (YYYY-MM-DD): ").strip()
        print(f"  Event date: {date_str}")

        # Probe subchannels and get coords for each station
        stations = []
        for drf_dir_s in drf_dirs:
            name = drf_dir_s.name.upper()
            print(f"\n  Station: {name}")

            # Probe subchannels
            print(f"    Probing subchannels...")
            subs = probe_subchannels(drf_dir_s, date_str, args.tx_freq_mhz)
            print(f"    Top subchannels by SNR:")
            for sub, snr, freq in subs[:5]:
                freq_str = f" — {freq/1e6:.3f} MHz" if freq else ""
                marker = " ← WWV 10 MHz" if freq and abs(freq/1e6 - 10.0) < 0.01 else ""
                print(f"      subchannel {sub}: {snr:.1f} dB{freq_str}{marker}")

            # Generate thumbnails for ALL stations — user always visually confirms
            if True:  # always generate, even single-channel
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
                            '--start', '17:00', '--end', '21:00',
                            '--ylim=-5,5', '--dpi', '60',
                            '--callsign', name,
                        ], capture_output=True)
                    freq_str = f' {freq_i/1e6:.3f} MHz' if freq_i else ''
                    print(f'      sub{sub_i:02d}.png — subchannel {sub_i}{freq_str} SNR={snr_i:.1f} dB')
                print(f'    Open thumbnails in: {thumb_dir}')
                print(f'    Look for clear carrier near 0 Hz = WWV 10 MHz')
            # Auto-suggest based on freq metadata if available
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
            # Get coords
            rx_lat, rx_lon = get_station_coords(name, drf_dir_s)

            # Compute IPP midpoint
            ipp_lat, ipp_lon = midpoint(
                rx_lat, rx_lon, args.tx_lat, args.tx_lon
            )
            print(f"    IPP midpoint: {ipp_lat:.4f}N, {ipp_lon:.4f}E")

            stations.append({
                "name": name,
                "drf_dir": str(drf_dir_s),
                "subchannel": subchannel,
                "receiver_lat": rx_lat,
                "receiver_lon": rx_lon,
                "ipp_lat": ipp_lat,
                "ipp_lon": ipp_lon,
                "date_str": date_str,
            })

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
        print("  1. sgolay-ridge  (corridor GUI — recommended)")
        print("  2. fft           (automated)")
        print("  3. autocorr      (automated, Gwyn G3ZIL method)")
        print("  4. cwt           (automated, CWT multi-peak tracker)")
        choice = input("Choose [1]: ").strip() or "1"
        method = {"1": "sgolay-ridge", "2": "fft",
                  "3": "autocorr", "4": "cwt"}.get(choice, "sgolay-ridge")
        state["extraction_method"] = method
        save_state(state_file, state)
    else:
        method = state["extraction_method"]
    print(f"  Extraction method: {method}")

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
        if method == "sgolay-ridge":
            # Step 6: Corridor clicking (zoom_clean_png already generated in Step 4)
            state[f"{stn_key}_zoom_overlay"] = True
            save_state(state_file, state)
            # Step 6/7: User clicks corridor
            if f"{stn_key}_corridor" not in state:
                print(f"\n[Step 6] Click corridor for {name}...")
                print(f"  → Open {zoom_png.name} for visual reference")
                print(f"  → Click corridor on clean PNG: {zoom_clean_png.name}")
                print("  → Click ~6 points bracketing the carrier")
                print("  → Press X to export corridor + preview, Q to accept")
                run([
                    "python3", tool("tid_spect_click.py"),
                    "--spectrogram", str(zoom_clean_png),
                    "--name", name,
                    "--drf-dir", drf_dir_s,
                    "--subchannel", str(sub),
                    "--sgolay-window", str(args.sgolay_window),
                ])
                if not corridor_json.exists():
                    print(f"  WARNING: No corridor saved for {name} — skipping")
                    continue
                state[f"{stn_key}_corridor"] = str(corridor_json)
                save_state(state_file, state)

            # Step 7: sgolay-ridge extraction
            if f"{stn_key}_sgolay" not in state:
                print(f"\n[Step 7] sgolay-ridge extraction for {name}...")
                r = run([
                    "python3", tool("drf_to_doppler.py"),
                    drf_dir_s,
                    "--subchannel", str(sub),
                    "--start", h_to_iso(date_str, t0_h),
                    "--end",   h_to_iso(date_str, t1_h),
                    "--decim-seconds", "60",
                    "--method", "sgolay-ridge",
                    "--corridor", str(corridor_json),
                    "--sgolay-window", str(args.sgolay_window),
                    "--output", str(sgolay_csv),
                ])
                if r.returncode != 0:
                    print(f"  ERROR: sgolay-ridge failed for {name}")
                    continue
                state[f"{stn_key}_sgolay"] = str(sgolay_csv)
                save_state(state_file, state)
            else:
                print(f"  sgolay CSV: {sgolay_csv.name} (already done)")

        else:  # method in (fft, autocorr, cwt)
            # Step 6: Automated extraction
            csv_key = f"{stn_key}_{method.replace('-', '_')}"
            out_csv = event_dir / f"{stn_key}_{method}_tid.csv"
            if csv_key not in state:
                print(f"\n[Step 6] {method} extraction for {name}...")
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
        ])
        state[f"{stn_key}_zoom"] = str(zoom_clean_png)
        save_state(state_file, state)

    # ── Step 10: Check overlap and run DOA ────────────────────────────────
    print(f"\n{'─'*60}")
    print("[Step 8] DOA")
    print(f"{'─'*60}")

    # Collect completed stations — prefer sgolay, then current method CSV
    completed = []
    for stn in stations:
        stn_key = stn["name"].lower()
        sgolay_csv   = event_dir / f"{stn_key}_sgolay_tid.csv"
        fft_csv      = event_dir / f"{stn_key}_fft_tid.csv"
        autocorr_csv = event_dir / f"{stn_key}_autocorr_tid.csv"
        cwt_csv      = event_dir / f"{stn_key}_cwt_tid.csv"
        # Priority: sgolay > current method > fft > autocorr > cwt
        candidates = [
            (sgolay_csv,   "sgolay-ridge"),
            (event_dir / f"{stn_key}_{method}_tid.csv", method),
            (fft_csv,      "fft"),
            (autocorr_csv, "autocorr"),
            (cwt_csv,      "cwt"),
        ]
        for csv, meth in candidates:
            if csv.exists():
                completed.append({
                    "name": stn["name"],
                    "file": str(csv),
                    "method": meth,
                    "lat": stn["ipp_lat"],
                    "lon": stn["ipp_lon"],
                })
                break

    if len(completed) < 3:
        print(f"  Only {len(completed)} station(s) completed — need ≥3 for DOA")
        return

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
        "min_expected_speed_m_s": 100,
        "stations": completed,
    }
    if args.max_lag is not None:
        event_config["max_lag_seconds"] = args.max_lag * 60
        print(f"  max_lag_seconds: {args.max_lag * 60:.0f} s ({args.max_lag:.0f} min)")
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

# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="Guided TID direction-of-arrival workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--stations", default=None, metavar="A,B,C",
                   help="Comma-separated station names to use (default: all found)")
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
