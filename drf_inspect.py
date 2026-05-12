r"""
drf_inspect.py — inspect a Digital RF station directory and identify the
correct subchannel for a target WWV frequency

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial public release.

OVERVIEW
========
Before extracting Doppler data from a HamSCI Grape station, you need to
verify:

  1. The DRF data is readable (paths, properties, time bounds).
  2. The recorded callsign and location actually match what you expect.
  3. For multi-subchannel WSPRdaemon stations, WHICH subchannel index
     corresponds to your target WWV frequency.

This tool reads the DRF metadata and prints all of the above. It is
strongly recommended as STEP 2 of the analysis pipeline, after you
download the DRF tarball from PSWS but BEFORE running drf_to_doppler.py.

It is especially important for multi-subchannel KA9Q-radio /
WSPRdaemon recordings, where the mapping from subchannel index to
center frequency varies between stations. Selecting the wrong
subchannel gives a noisy trace that may superficially look like weak
signal -- a real failure mode we encountered during the Jan 19 2026
event analysis.

WHY THIS IS A SEPARATE STEP
===========================
The DRF "center_frequencies" array in the metadata is the only
authoritative way to know which subchannel index corresponds to which
WWV frequency. Each station configures this independently:

  - N5TNL frequencies: [2.5, 3.33, 5.0, 7.85, 10.0, 14.67, 15.0, 20.0, 25.0]
                       -> 10 MHz is at INDEX 4 (zero-indexed)
  - KD7EFG frequencies: [0.06, 2.5, 3.33, 5.0, 7.85, 10.0, 14.67, 15.0, 20.0, 25.0]
                        -> 10 MHz is at INDEX 5 (the extra 0.06 MHz
                           WWVB entry shifts everything by one)
  - Single-channel Grape: only one subchannel, always index 0

Without inspecting the metadata first, you'd have to either guess the
index (often wrong) or run a slow subchannel sweep (we did both during
development; this tool is the right answer).

USAGE
=====
Inspect one DRF directory:

    python drf_inspect.py /path/to/station_drf_dir

Inspect a directory and look for a specific frequency:

    python drf_inspect.py ./n5tnl --frequency 10

Inspect every station folder in the current directory:

    python drf_inspect.py --all .

OUTPUT
======
For each DRF directory, the script reports:

    Station metadata:
      - Callsign as recorded by the receiver (may differ from PSWS
        nickname; e.g. PSWS "KA7OEI" actually has metadata callsign
        "KD7EFG")
      - Grid square and lat/lon
      - Receiver type (e.g. "KA9Q_0_WWV", "Grape v1.12")
      - UUID

    Channel info:
      - Sample rate (typically 10 Hz for narrowband Grape, higher for
        rx888)
      - Number of subchannels
      - Time bounds (UTC start and end of recording)
      - Total duration

    Subchannel table (for multi-subchannel data only):
      - Index, frequency in MHz, and a flag for the target frequency

    Sanity check:
      - For each subchannel, reads a few seconds of I/Q and reports the
        signal level. Empty subchannels show much lower power than
        active ones; this is a sanity check that the station was
        actually receiving on all listed frequencies.

PIPELINE POSITION
=================
This script slots into the analysis pipeline between data download and
Doppler extraction:

  1. find_event_stations.py     -> identify candidates
  2. Download DRF tarball from PSWS
  3. drf_inspect.py             -> verify metadata, find subchannel    <-- THIS
  4. drf_to_doppler.py          -> extract Doppler CSV
  5. tid_window_detector.py     -> (optional) find TID windows
  6. tid_pair.py / tid_doa.py   -> direction-of-arrival analysis

REQUIREMENTS
============
    pip install digital_rf numpy

SEE ALSO
========
    drf_to_doppler.py     consumer of the subchannel index this finds
    find_event_stations.py  upstream candidate finder
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import numpy as np

__version__ = "1.0.0"

# Lazy import: digital_rf is only needed at runtime, not for --help.
try:
    import digital_rf as drf
    _HAVE_DRF = True
except ImportError:
    drf = None
    _HAVE_DRF = False


def fmt_utc(sample_idx, sr_num, sr_den):
    """Convert a DRF sample index to a UTC datetime string."""
    sec = sample_idx * sr_den / sr_num
    return datetime.fromtimestamp(sec, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC")


def find_subchannel_index(freqs, target_mhz, tol_mhz=0.05):
    """Return the index of the subchannel matching target_mhz, or None."""
    if freqs is None:
        return None
    for i, f in enumerate(freqs):
        if abs(float(f) - target_mhz) <= tol_mhz:
            return i
    return None


def inspect_one(drf_dir, target_freq_mhz=None, channel="ch0"):
    """Inspect a single DRF directory and print its info."""
    print(f"\n=== {drf_dir} ===")

    if not os.path.isdir(drf_dir):
        print(f"  ERROR: not a directory")
        return None

    if not _HAVE_DRF:
        print("  ERROR: digital_rf not installed. Run: pip install digital_rf")
        return None

    try:
        reader = drf.DigitalRFReader(drf_dir)
    except Exception as e:
        print(f"  ERROR opening DRF: {e}")
        return None

    channels = reader.get_channels()
    if not channels:
        print("  ERROR: no channels found in this directory")
        return None
    if channel not in channels:
        print(f"  Channel '{channel}' not found. Available: {channels}")
        if len(channels) == 1:
            channel = channels[0]
            print(f"  Using channel '{channel}' instead.")
        else:
            return None

    # ---- Channel properties -----------------------------------------------
    props = reader.get_properties(channel)
    sr_num, sr_den = props["samples_per_second"].as_integer_ratio()
    sps = sr_num / sr_den
    n_sub = props.get("num_subchannels", 1)
    is_complex = props.get("is_complex", 1)

    try:
        b_start, b_end = reader.get_bounds(channel)
        start_str = fmt_utc(b_start, sr_num, sr_den)
        end_str = fmt_utc(b_end, sr_num, sr_den)
        dur_hr = (b_end - b_start) * sr_den / sr_num / 3600.0
    except Exception:
        b_start = b_end = None
        start_str = end_str = "?"
        dur_hr = 0

    print(f"  Channel:               {channel}")
    print(f"  Sample rate:           {sps:.3f} samples/sec  "
          f"({'complex' if is_complex else 'real'})")
    print(f"  Subchannels:           {n_sub}")
    print(f"  Recording start:       {start_str}")
    print(f"  Recording end:         {end_str}")
    print(f"  Total duration:        {dur_hr:.2f} hours")

    # ---- Station metadata -------------------------------------------------
    metadata_dir = os.path.join(drf_dir, channel, "metadata")
    station_info = {}
    if os.path.isdir(metadata_dir):
        try:
            mreader = drf.DigitalMetadataReader(metadata_dir)
            mb = mreader.get_bounds()
            sample = mreader.read(mb[0], mb[0] + 1)
            if sample:
                meta_dict = list(sample.values())[0]
                station_info = meta_dict
        except Exception as e:
            print(f"  (metadata read failed: {e})")

    if station_info:
        print(f"\n  Station metadata:")
        for key in ("callsign", "grid_square", "lat", "long", "receiver_name",
                    "uuid_str"):
            v = station_info.get(key)
            if v is not None:
                print(f"    {key:<16} {v}")

    # ---- Subchannel table -------------------------------------------------
    freqs = station_info.get("center_frequencies")
    target_idx = None
    if freqs is not None:
        freqs_list = list(freqs)
        print(f"\n  Subchannels and their center frequencies:")
        print(f"    {'Index':<6} {'Freq (MHz)':<12} {'WWV?':<6} {'Target?':<8}")
        wwv_freqs = {2.5, 5.0, 10.0, 15.0, 20.0, 25.0}
        for i, f in enumerate(freqs_list):
            is_wwv = "WWV" if float(f) in wwv_freqs else ""
            mark = ""
            if target_freq_mhz is not None and abs(float(f) - target_freq_mhz) <= 0.05:
                mark = "*** YES ***"
                target_idx = i
            print(f"    {i:<6} {float(f):<12.3f} {is_wwv:<6} {mark}")

        if target_freq_mhz is not None:
            print()
            if target_idx is not None:
                print(f"  >>> For {target_freq_mhz} MHz, USE: --subchannel {target_idx}")
            else:
                print(f"  >>> {target_freq_mhz} MHz NOT FOUND in this station's "
                      f"subchannels. Available: {[float(x) for x in freqs_list]}")

    elif n_sub > 1:
        print(f"\n  WARNING: {n_sub} subchannels present but no "
              f"center_frequencies metadata. Cannot identify which is which.")
        print(f"  Try running drf_to_doppler.py with --subchannel 0..{n_sub-1} "
              f"to find the right one empirically.")
    else:
        # Single-channel: nothing to choose
        if target_freq_mhz is not None:
            print(f"\n  Single-channel DRF: --subchannel 0 (the only option)")

    # ---- Signal-level sanity check ----------------------------------------
    if b_start is not None and n_sub > 1:
        print(f"\n  Signal level per subchannel (1-second sample at start):")
        try:
            n_samples = max(10, int(sps))
            block = reader.read_vector(b_start, n_samples, channel)
            if block.ndim == 2:
                print(f"    {'Index':<6} {'RMS magnitude':<18} {'Status':<14}")
                rms_vals = []
                for i in range(min(n_sub, block.shape[1])):
                    rms = float(np.sqrt(np.mean(np.abs(block[:, i])**2)))
                    rms_vals.append(rms)
                med = float(np.median(rms_vals))
                for i, rms in enumerate(rms_vals):
                    if med > 0 and rms < med / 10:
                        status = "EMPTY?"
                    elif med > 0 and rms > med * 3:
                        status = "ACTIVE"
                    else:
                        status = "normal"
                    print(f"    {i:<6} {rms:<18.3e} {status:<14}")
            else:
                rms = float(np.sqrt(np.mean(np.abs(block)**2)))
                print(f"    single subchannel  RMS = {rms:.3e}")
        except Exception as e:
            print(f"    (could not read sample I/Q: {e})")

    print()
    return target_idx


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.split("USAGE", 1)[0],
        epilog="See the docstring at the top of the script for full details.",
    )
    ap.add_argument("path", nargs="?", default=".",
                    help="Path to a DRF station directory (the one CONTAINING "
                         "'ch0/'), or a folder containing multiple station "
                         "directories if --all is used. Default: current dir")
    ap.add_argument("--all", action="store_true",
                    help="Treat 'path' as a parent directory and inspect "
                         "every DRF station folder inside it")
    ap.add_argument("--frequency", type=float, default=None,
                    help="Target WWV frequency in MHz. If specified, the "
                         "tool will identify which subchannel index "
                         "corresponds to this frequency and print a "
                         "ready-to-use --subchannel value.")
    ap.add_argument("--channel", default="ch0",
                    help="DRF channel name (default: ch0)")
    ap.add_argument("--version", action="version",
                    version="%(prog)s 1.0.0")
    args = ap.parse_args()

    if not _HAVE_DRF:
        sys.exit("digital_rf not installed. Run: pip install digital_rf")

    if args.all:
        if not os.path.isdir(args.path):
            sys.exit(f"--all requires a directory, got {args.path!r}")
        # Find each subdir that contains a 'ch0' (the DRF channel marker)
        candidates = []
        for entry in sorted(os.listdir(args.path)):
            full = os.path.join(args.path, entry)
            if os.path.isdir(os.path.join(full, args.channel)):
                candidates.append(full)
        if not candidates:
            sys.exit(f"No DRF station directories (containing '{args.channel}/') "
                     f"found in {args.path}")
        print(f"Found {len(candidates)} DRF station directories in {args.path}")
        for c in candidates:
            inspect_one(c, target_freq_mhz=args.frequency, channel=args.channel)
    else:
        inspect_one(args.path, target_freq_mhz=args.frequency,
                    channel=args.channel)


if __name__ == "__main__":
    main()
