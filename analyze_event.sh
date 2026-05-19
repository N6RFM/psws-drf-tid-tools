#!/usr/bin/env bash
# analyze_event.sh — interactive driver for the psws-drf-tid-tools pipeline
#
# Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
# Created by N6RFM with help from Claude AI.
# Version: 1.5.0
# License: MIT (do whatever you want, no warranty).
#
# OVERVIEW
# ========
# This script walks the operator through a complete TID analysis,
# pausing at the four points that require human judgment:
#
#   PAUSE 1: confirm or override the auto-proposed time window
#   PAUSE 2: pick which companion stations to download
#   PAUSE 3: confirm tarballs are downloaded and extracted
#   PAUSE 4: quality-check the per-station Doppler PNGs
#
# In Stage 1, the script automatically:
#   - Renders the reference-station 24-hour spectrogram
#   - Extracts a low-resolution survey CSV and runs tid_window_detector.py
#     to find the day's top-scoring TID candidate window
#   - Pads the candidate by 15 min, snaps to 15-min boundaries
#   - Re-renders the spectrogram with the proposal highlighted
# At Pause 1, you press Enter to accept the proposal or type your own
# start time to override.
#
# Between pauses everything is automatic. The script is resumable —
# state is written to .analyze_event_state in the working directory
# after each pause, and the script can be re-run to continue from
# where it left off.
#
# USAGE
# =====
#   ./analyze_event.sh \
#       --date 2026-01-19 \
#       --my-call "N6RFM/5" \
#       --my-grid "EM12jw" \
#       --my-lat 32.94 --my-lon -97.21 \
#       --my-station ./n6rfm
#
# All arguments are required on first run. On resume runs, they're read
# from the state file and don't need to be repeated.
#
# OPTIONAL FLAGS
# ==============
#   --workdir DIR           Working directory (default: current dir)
#   --reset                 Discard state and start fresh
#   --resume                Force resume from saved state (skips arg validation)
#   --tools-dir DIR         Where the Python scripts live (default: same
#                           directory as this script)
#   --decim-seconds N       Doppler extraction cadence (default: 10)
#   --image-viewer CMD      Command to open PNG files (default: xdg-open
#                           on Linux, open on macOS; set to "none" to skip)
#   --skip-flare            Don't try to find/render the prior-day flare
#                           spectrogram (some events don't have one)
#
# REQUIREMENTS
# ============
# All the tools the rest of the pipeline needs (digital_rf, numpy,
# scipy, pandas, matplotlib, requests, beautifulsoup4), plus a POSIX
# shell. cartopy optional for the geometry map.

set -e
set -u

# -----------------------------------------------------------------------------
# Defaults and CLI parsing
# -----------------------------------------------------------------------------
WORKDIR="$PWD"
TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
EVENT_DATE=""
MY_CALL=""
MY_GRID=""
MY_LAT=""
MY_LON=""
MY_STATION=""
DECIM_SECONDS=10
SKIP_FLARE=0
RESET=0
RESUME=0

# Image viewer: default by platform
if [[ "$(uname)" == "Darwin" ]]; then
    IMAGE_VIEWER="open"
else
    IMAGE_VIEWER="xdg-open"
fi

usage() {
    sed -n '2,55p' "$0"   # print the docstring header
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)            EVENT_DATE="$2"; shift 2 ;;
        --my-call)         MY_CALL="$2"; shift 2 ;;
        --my-grid)         MY_GRID="$2"; shift 2 ;;
        --my-lat)          MY_LAT="$2"; shift 2 ;;
        --my-lon)          MY_LON="$2"; shift 2 ;;
        --my-station)      MY_STATION="$2"; shift 2 ;;
        --workdir)         WORKDIR="$2"; shift 2 ;;
        --tools-dir)       TOOLS_DIR="$2"; shift 2 ;;
        --decim-seconds)   DECIM_SECONDS="$2"; shift 2 ;;
        --image-viewer)    IMAGE_VIEWER="$2"; shift 2 ;;
        --skip-flare)      SKIP_FLARE=1; shift ;;
        --reset)           RESET=1; shift ;;
        --resume)          RESUME=1; shift ;;
        -h|--help)         usage ;;
        --version)         echo "analyze_event.sh 1.5.0"; exit 0 ;;
        *)
            echo "Unknown argument: $1"
            echo "Try --help"
            exit 2
            ;;
    esac
done

cd "$WORKDIR"
STATE_FILE="$WORKDIR/.analyze_event_state"

# -----------------------------------------------------------------------------
# Resume / reset handling
# -----------------------------------------------------------------------------
if [[ $RESET -eq 1 ]]; then
    rm -f "$STATE_FILE"
    echo "State file removed. Starting fresh."
fi

# Load state if present
LAST_STAGE=0
WINDOW_START=""
WINDOW_END=""
COMPANIONS=""
if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    if [[ $RESUME -eq 0 ]]; then
        echo "Found existing state file from stage $LAST_STAGE. Resuming."
        echo "(Use --reset to discard and start fresh.)"
    fi
fi

# If we don't have required args (and aren't resuming with them saved), bail
if [[ -z "$EVENT_DATE" || -z "$MY_CALL" || -z "$MY_GRID" || \
      -z "$MY_LAT"   || -z "$MY_LON"  || -z "$MY_STATION" ]]; then
    echo "Missing required arguments. Need:"
    echo "  --date YYYY-MM-DD"
    echo "  --my-call CALL"
    echo "  --my-grid GRID"
    echo "  --my-lat LAT --my-lon LON"
    echo "  --my-station ./path/to/your/drf"
    echo "Run with --help for full usage."
    exit 2
fi

if [[ ! -d "$MY_STATION" ]]; then
    echo "Error: --my-station path does not exist: $MY_STATION"
    exit 2
fi

save_state() {
    cat > "$STATE_FILE" <<EOF
# psws-drf-tid-tools analyze_event.sh state file
# Auto-generated; safe to delete to start over.
LAST_STAGE=$1
EVENT_DATE="$EVENT_DATE"
MY_CALL="$MY_CALL"
MY_GRID="$MY_GRID"
MY_LAT="$MY_LAT"
MY_LON="$MY_LON"
MY_STATION="$MY_STATION"
WINDOW_START="$WINDOW_START"
WINDOW_END="$WINDOW_END"
COMPANIONS="$COMPANIONS"
DECIM_SECONDS=$DECIM_SECONDS
EOF
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
banner() {
    echo
    echo "=================================================================="
    echo "  $1"
    echo "=================================================================="
}

pause_block() {
    local title="$1"
    echo
    echo "------------------------------------------------------------------"
    echo "  >> HUMAN INPUT NEEDED: $title"
    echo "------------------------------------------------------------------"
}

# Print a one-line hint about an upcoming long stage so the user knows
# the silence is expected.
hint() {
    echo "  -- $1"
}

# Run a command with a rotating spinner and elapsed-time counter on
# stderr while it works. Stdout and stderr of the command are captured
# to a log file and dumped at the end so the user sees clean output.
#
# Usage: run_with_spinner LABEL CMD [ARGS...]
# Returns the exit status of the underlying command.
run_with_spinner() {
    local label="$1"
    shift
    # Disable set -e for the inner block so we can capture exit code.
    set +e
    local logfile
    logfile=$(mktemp)
    # Run the command in background, redirecting all output to the log.
    "$@" > "$logfile" 2>&1 &
    local cmd_pid=$!

    # Spinner loop in foreground.
    local spin_chars='|/-\'
    local i=0
    local start_time
    start_time=$(date +%s)
    while kill -0 "$cmd_pid" 2>/dev/null; do
        local elapsed=$(( $(date +%s) - start_time ))
        local min=$(( elapsed / 60 ))
        local sec=$(( elapsed % 60 ))
        # \r returns cursor to start of line so we overwrite in place.
        printf "\r  %s %s   [%dm %02ds]   " \
               "${spin_chars:$i:1}" "$label" "$min" "$sec" >&2
        i=$(( (i + 1) % 4 ))
        sleep 0.5
    done
    # Wait for the command to actually exit and grab its status.
    wait "$cmd_pid"
    local status=$?
    set -e

    # Clear spinner line and replace with final status.
    local total=$(( $(date +%s) - start_time ))
    local min=$(( total / 60 ))
    local sec=$(( total % 60 ))
    printf "\r  %s %s   [done in %dm %02ds]   \n" \
           "✓" "$label" "$min" "$sec" >&2

    # Replay captured output.
    if [[ -s "$logfile" ]]; then
        cat "$logfile"
    fi
    rm -f "$logfile"

    return $status
}

open_image() {
    local img="$1"
    if [[ "$IMAGE_VIEWER" == "none" ]]; then
        echo "  (image viewer disabled; open manually: $img)"
        return
    fi
    # IMAGE_VIEWER may contain extra args (e.g. "feh --geometry 1400x900").
    # Split on whitespace so the first token is the actual binary to
    # verify exists.
    local viewer_argv viewer_bin
    # shellcheck disable=SC2206
    viewer_argv=( $IMAGE_VIEWER )
    viewer_bin="${viewer_argv[0]}"
    if command -v "$viewer_bin" > /dev/null 2>&1; then
        # Kill any prior viewer instance showing this same file. Without
        # this, repeated re-renders (e.g. Pause 1's "e" to change end
        # time) stack new feh windows behind old ones — the file content
        # updates but the user sees the stale older window on top and
        # assumes nothing happened. Best-effort: pkill may fail silently
        # if no matching process exists, which is fine.
        local img_basename
        img_basename=$(basename "$img")
        pkill -f "${viewer_bin}.*${img_basename}" 2>/dev/null || true
        # Brief pause so the old process exits before launching the new one.
        sleep 0.15
        # Redirect viewer output to a log file rather than /dev/null —
        # some viewers (notably feh) detect /dev/null as stdout and exit
        # immediately without displaying a window. Redirecting to a real
        # file avoids that quirk. The log accumulates across launches; it
        # is removed when the analysis starts (see --reset) or can be
        # ignored.
        local viewer_log="${WORKDIR:-.}/.viewer.log"
        # shellcheck disable=SC2068
        ${viewer_argv[@]} "$img" >> "$viewer_log" 2>&1 &
        # Tiny settle delay so the viewer has time to launch before the
        # next prompt — otherwise the prompt's keystrokes can be eaten by
        # the briefly-focused viewer window.
        sleep 0.3
    else
        echo "  (image viewer '$viewer_bin' not found; open manually: $img)"
    fi
}

# Compute the day before event date (for flare-evening spectrogram).
day_before() {
    python3 -c "
from datetime import datetime, timedelta
d = datetime.strptime('$1', '%Y-%m-%d')
print((d - timedelta(days=1)).strftime('%Y-%m-%d'))
"
}

# -----------------------------------------------------------------------------
# STAGE 1: render reference station spectrogram(s)
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 1 ]]; then
    banner "STAGE 1 — render reference-station spectrogram(s)"
    hint "Reading 24 hours of raw I/Q from your reference DRF (~30 seconds)."
    REF_SPEC="ref_${EVENT_DATE}_spectrogram.png"
    python3 "$TOOLS_DIR/drf_spectrogram.py" "$MY_STATION" \
        --output "$REF_SPEC" \
        --ylim=-2,2 \
        --callsign "$MY_CALL" --grid "$MY_GRID"
    echo "Wrote $REF_SPEC"
    open_image "$REF_SPEC"

    # Optional: flare-evening spectrogram from the day before
    if [[ $SKIP_FLARE -eq 0 ]]; then
        FLARE_DATE=$(day_before "$EVENT_DATE")
        # Check whether the day-before recording is in the same DRF dir
        # (sometimes operators put one folder per day).
        FLARE_DRF=""
        if python3 -c "
import digital_rf as drf
from datetime import datetime, timezone, timedelta
r = drf.DigitalRFReader('$MY_STATION')
b, e = r.get_bounds('ch0')
sr_num, sr_den = r.get_properties('ch0')['samples_per_second'].as_integer_ratio()
sps = sr_num / sr_den
start = datetime.fromtimestamp(b * sr_den / sr_num, tz=timezone.utc)
target = datetime.strptime('$FLARE_DATE', '%Y-%m-%d').replace(tzinfo=timezone.utc)
exit(0 if start.date() <= target.date() else 1)
"; then
            FLARE_DRF="$MY_STATION"
        fi

        if [[ -n "$FLARE_DRF" ]]; then
            FLARE_SPEC="ref_${FLARE_DATE}_spectrogram.png"
            # Render 16:00–23:59 UTC of the prior day for typical flare events
            python3 "$TOOLS_DIR/drf_spectrogram.py" "$FLARE_DRF" \
                --output "$FLARE_SPEC" \
                --start "16:00" --end "23:59" \
                --ylim=-2,4 \
                --callsign "$MY_CALL" --grid "$MY_GRID" || true
            if [[ -f "$FLARE_SPEC" ]]; then
                echo "Wrote $FLARE_SPEC (prior-day flare evening)"
                open_image "$FLARE_SPEC"
            fi
        else
            echo "(Prior-day recording not present in $MY_STATION; skipping flare spectrogram)"
        fi
    fi
    save_state 1
fi

# -----------------------------------------------------------------------------
# STAGE 1b: auto-detect candidate TID windows
# -----------------------------------------------------------------------------
PROPOSED_START=""
PROPOSED_END=""
if [[ $LAST_STAGE -lt 2 ]]; then
    banner "STAGE 1b — auto-detect candidate TID windows"
    hint "Building 24-hour survey CSV at 60s cadence, then scoring for"
    hint "wave-like activity (typically ~30-60 seconds total)."

    # Extract a low-resolution full-day Doppler CSV for window detection.
    # 60-second cadence is cheap (~30 seconds) and plenty for detector.
    SURVEY_CSV="ref_${EVENT_DATE}_survey.csv"
    SURVEY_PNG="ref_${EVENT_DATE}_survey.png"
    DAY_START="${EVENT_DATE}T00:00:00"
    DAY_END="${EVENT_DATE}T23:59:00"
    if [[ ! -f "$SURVEY_CSV" ]]; then
        hint "Extracting 24-hour reference-station survey CSV at 60s cadence"
        hint "(takes ~20-40 seconds — drf_to_doppler.py output below is normal):"
        python3 "$TOOLS_DIR/drf_to_doppler.py" "$MY_STATION" \
            --start "$DAY_START" --end "$DAY_END" \
            --decim-seconds 60 --subchannel 0 \
            --output "$SURVEY_CSV" --plot "$SURVEY_PNG" \
            || true
    fi

    # Run the window detector. It scores 24-hour spectrograms for wave-like
    # activity and returns the top N candidates.
    DETECTOR_OUT="ref_${EVENT_DATE}_windows.txt"
    if [[ -f "$SURVEY_CSV" ]]; then
        python3 "$TOOLS_DIR/tid_window_detector.py" "$SURVEY_CSV" \
            --lat "$MY_LAT" --lon "$MY_LON" \
            --top 3 2>/dev/null | tee "$DETECTOR_OUT" || true
    else
        echo "(Could not produce survey CSV; skipping auto-detection.)"
    fi

    # Parse the detector output to extract the #1 candidate window (start,
    # end times). The detector prints lines like:
    #   1 2026-01-19 00:00:14  2026-01-19 01:59:14   60.0m  15.3  0.27  0.227
    # We do NOT add padding (it tends to grab dirty signal); we snap
    # inward to 15-min boundaries to keep the window clean.
    if [[ -f "$DETECTOR_OUT" ]]; then
        # shellcheck disable=SC2016
        PROPOSAL=$(python3 - "$DETECTOR_OUT" "$EVENT_DATE" <<'PYEOF'
import re, sys
from datetime import datetime, timedelta
text = open(sys.argv[1]).read()
event_date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
event_day_start = event_date.replace(hour=0, minute=0, second=0)
event_day_end   = event_date.replace(hour=23, minute=45, second=0)

# Match tid_window_detector.py output format:
#   1 2026-01-19 00:00:14  2026-01-19 01:59:14  60.0m  15.3  0.27  0.227
m = re.search(
    r'^\s*1\s+'
    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)'
    r'\s+'
    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)',
    text, re.MULTILINE)
# Fallback for older "1. ... to ..." formats
if not m:
    m = re.search(
        r'^\s*1\.?\s*'
        r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)\s*'
        r'(?:to|-->|->|-)\s*'
        r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)',
        text, re.MULTILINE)
if not m:
    sys.exit(0)

def parse(s):
    s = s.replace(' ', 'T')
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    sys.exit(0)

def snap_inward(dt, direction):
    """Snap to 15-min boundary INWARD (i.e. shorten the window).
       direction='start' rounds UP to next 15-min boundary (later);
       direction='end'   rounds DOWN to prior 15-min boundary (earlier).
       This produces a conservative, fully-contained window with clean
       times like :00, :15, :30, :45 instead of the detector's raw
       sample timestamps."""
    base = dt.replace(second=0, microsecond=0)
    minute = base.minute
    if direction == 'start':
        # Round UP to next 15-min mark (or stay if already on one)
        next_mark = ((minute + 14) // 15) * 15
        if next_mark == minute:
            return base
        if next_mark >= 60:
            return base.replace(minute=0) + timedelta(hours=1)
        return base.replace(minute=next_mark)
    else:  # end
        # Round DOWN to prior 15-min mark
        prev_mark = (minute // 15) * 15
        return base.replace(minute=prev_mark)

raw_start = parse(m.group(1))
raw_end   = parse(m.group(2))

start = snap_inward(raw_start, 'start')
end   = snap_inward(raw_end,   'end')

# Clamp to event date
if start < event_day_start:
    start = event_day_start
if end > event_day_end:
    end = event_day_end

# If snapping inward made the window too short (< 30 min), fall back
# to using raw detector times rounded to nearest minute.
duration_minutes = (end - start).total_seconds() / 60.0
if duration_minutes < 30:
    start = raw_start.replace(second=0, microsecond=0)
    end   = raw_end.replace(second=0, microsecond=0)
    if start < event_day_start:
        start = event_day_start
    if end > event_day_end:
        end = event_day_end

print(start.strftime('%Y-%m-%dT%H:%M:%S'))
print(end.strftime('%Y-%m-%dT%H:%M:%S'))
PYEOF
)
        if [[ -n "$PROPOSAL" ]]; then
            PROPOSED_START=$(echo "$PROPOSAL" | sed -n '1p')
            PROPOSED_END=$(echo "$PROPOSAL"   | sed -n '2p')
        fi
    fi

    if [[ -n "$PROPOSED_START" && -n "$PROPOSED_END" ]]; then
        # Compute duration in minutes for the user-facing message
        DURATION_MIN=$(python3 -c "
from datetime import datetime
s = datetime.strptime('$PROPOSED_START', '%Y-%m-%dT%H:%M:%S')
e = datetime.strptime('$PROPOSED_END',   '%Y-%m-%dT%H:%M:%S')
print(int((e - s).total_seconds() / 60))")
        echo
        echo "Top candidate window (auto-detected, snapped inward to 15-min boundaries):"
        echo "    $PROPOSED_START  ->  $PROPOSED_END   (duration: ${DURATION_MIN} min)"

        # Re-render the spectrogram with the proposed window highlighted.
        PROPOSAL_PNG="ref_${EVENT_DATE}_with_proposal.png"
        ANN_START=$(echo "$PROPOSED_START" | grep -oE 'T[0-9]{2}:[0-9]{2}' | tr -d T)
        ANN_END=$(echo "$PROPOSED_END" | grep -oE 'T[0-9]{2}:[0-9]{2}' | tr -d T)
        hint "Rendering annotated spectrogram with proposed window highlighted"
        hint "(takes ~30-60 seconds — drf_spectrogram.py output below is normal):"
        python3 "$TOOLS_DIR/drf_spectrogram.py" "$MY_STATION" \
            --output "$PROPOSAL_PNG" \
            --ylim=-2,2 \
            --callsign "$MY_CALL" --grid "$MY_GRID" \
            --annotate "${ANN_START},${ANN_END},Proposed TID window" \
            || true
        if [[ -f "$PROPOSAL_PNG" ]]; then
            echo "Spectrogram with proposed window: $PROPOSAL_PNG"
            open_image "$PROPOSAL_PNG"
        fi
    else
        echo "(Auto-detector did not return a usable proposal; you'll enter the window manually.)"
    fi
fi

# -----------------------------------------------------------------------------
# PAUSE 1: ask for the analysis window
# -----------------------------------------------------------------------------

# Helper: re-render the spectrogram with a different proposed window,
# then open it. Used when the user edits the proposal.
# Re-extract a single station's Doppler CSV at the current WINDOW_START
# and WINDOW_END. Used by the Pause 4 tightening loop. The subchannel
# is read from station_subchannels.txt (built at Stage 8); falls back
# to 0 if the file is missing or the station is not listed.
#
# Args:
#   $1 = station name (matches directory name and CSV name)
#   $2 = "ref" (use $MY_STATION as data source) or "companion" (./$1)
reextract_one_station() {
    local s="$1"
    local kind="$2"
    local data_dir subch
    if [[ "$kind" == "ref" ]]; then
        data_dir="$MY_STATION"
        # Reference station: subchannel always 0 in this pipeline
        # (matches Stage 8's behavior at line 925-ish).
        subch=0
    else
        data_dir="./$s"
        subch=$(awk -F'\t' -v s="$s" '$1 == s {print $2; exit}' \
                station_subchannels.txt 2>/dev/null)
        subch="${subch:-0}"
    fi
    python3 "$TOOLS_DIR/drf_to_doppler.py" "$data_dir" \
        --start "$WINDOW_START" --end "$WINDOW_END" \
        --decim-seconds "$DECIM_SECONDS" --subchannel "$subch" \
        --output "${s}.csv" --plot "${s}.png"
}

# Re-extract reference + all companion stations at the current
# WINDOW_START / WINDOW_END. Used by the Pause 4 tightening loop.
# Returns 0 on success, non-zero on any failure.
reextract_all_stations() {
    echo ""
    echo "  Re-extracting Doppler CSVs at new window..."
    echo "    Window: $WINDOW_START -> $WINDOW_END"
    reextract_one_station "$REF_NAME" "ref" || return 1
    for s in "${COMPANION_LIST[@]}"; do
        reextract_one_station "$s" "companion" || return 1
    done
    echo "  Re-extraction complete."
    return 0
}

# Run quality_summary.py against the current Doppler CSVs (reference +
# all companions) and tee the output to .quality_summary_output so
# get_suggested_end_time and other downstream code can parse it.
# Used both at the initial Pause 4 entry and inside the tightening loop.
run_quality_summary() {
    local csvs=("${REF_NAME}.csv")
    for s in "${COMPANION_LIST[@]}"; do
        [[ -f "${s}.csv" ]] && csvs+=("${s}.csv")
    done
    python3 "$TOOLS_DIR/quality_summary.py" --suggest-shorten "${csvs[@]}" \
        | tee .quality_summary_output || true
}


# Parse .quality_summary_output and extract the EARLIEST (most-restrictive)
# end-time suggestion. Echoes the timestamp in YYYY-MM-DDTHH:MM:SS format,
# or empty string if no suggestions are present.
#
# Lines we care about look like:
#   Consider shortening the analysis window to end at or before 2026-01-19T01:07:24.
get_suggested_end_time() {
    if [[ ! -f .quality_summary_output ]]; then
        return
    fi
    grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' \
        .quality_summary_output 2>/dev/null | sort | head -1
}

# Pause 4 auto-window-tightening loop. Offers to tighten the analysis
# window when quality_summary.py has flagged end-fade. Loops up to 3
# iterations or until no more suggestions appear.
#
# Reads:  WINDOW_END (current), .quality_summary_output (suggestions)
# Writes: WINDOW_END (if tightened), all *.csv (if re-extracted),
#         .quality_summary_output (refreshed), stack_pause4.png (refreshed),
#         .analyze_event_state (persists new WINDOW_END)
pause4_tightening_loop() {
    local iteration=0
    local max_iterations=3
    while [[ $iteration -lt $max_iterations ]]; do
        local suggested
        suggested=$(get_suggested_end_time)
        if [[ -z "$suggested" ]]; then
            return 0
        fi
        if [[ "$suggested" == "$WINDOW_END" ]] \
           || [[ "$suggested" > "$WINDOW_END" ]]; then
            # Suggestion is not actually earlier than current — done
            return 0
        fi
        echo ""
        echo "End-fade suggestion: shorten the analysis window."
        echo "  Current end time:             $WINDOW_END"
        echo "  Suggested (most-restrictive): $suggested"
        echo ""
        read -p "Tighten window to $suggested? [y/N]: " TIGHTEN_ANSWER
        case "${TIGHTEN_ANSWER,,}" in
            y|yes)
                echo "  Updating WINDOW_END to $suggested..."
                WINDOW_END="$suggested"
                # Persist immediately so Stage 10 and resumes pick up
                # the new window even if the user Ctrl-Cs the
                # re-extraction.
                save_state 8
                if ! reextract_all_stations; then
                    echo "  Re-extraction failed; reverting WINDOW_END."
                    WINDOW_END=$(grep "^WINDOW_END=" \
                        .analyze_event_state | cut -d= -f2 \
                        | sed 's/^"//;s/"$//')
                    return 1
                fi
                # Re-run quality_summary with the tightened CSVs so the
                # next iteration's get_suggested_end_time sees updated
                # data.
                run_quality_summary || true
                # Refresh the stack PNG so the operator can see the
                # tightened view.
                render_pause4_stack
                iteration=$((iteration + 1))
                ;;
            *)
                # Default (Enter or 'n') = keep current window, exit loop
                echo "  Keeping current window: $WINDOW_END"
                return 0
                ;;
        esac
    done
    if [[ $iteration -ge $max_iterations ]]; then
        echo ""
        echo "  Reached maximum tightening iterations ($max_iterations);"
        echo "  proceeding with WINDOW_END=$WINDOW_END."
    fi
    return 0
}


# Render the per-Pause-4 stack PNG so the operator sees the multi-station
# comparison BEFORE deciding whether all stations look good. Uses
# --smooth 120 for peak detection so noise spikes don't dominate the
# peak markers.
render_pause4_stack() {
    local stations=("${REF_NAME}:${REF_NAME}.csv")
    for s in "${COMPANION_LIST[@]}"; do
        stations+=("${s}:${s}.csv")
    done
    echo
    echo "  Rendering stacked Doppler plot for review..."
    python3 "$TOOLS_DIR/tid_stack_plot.py" \
        --stations "${stations[@]}" \
        --start "$WINDOW_START" --end "$WINDOW_END" \
        --smooth 120 \
        --title "Doppler comparison at chosen stations, ${EVENT_DATE}" \
        --output stack_pause4.png \
        2>&1 | grep -v "^$" || true
    if [[ -f stack_pause4.png ]]; then
        open_image stack_pause4.png
    fi
}

rerender_proposal() {
    local s="$1" e="$2"
    local png="ref_${EVENT_DATE}_with_proposal.png"
    local ann_s ann_e
    ann_s=$(echo "$s" | grep -oE 'T[0-9]{2}:[0-9]{2}' | tr -d T)
    ann_e=$(echo "$e" | grep -oE 'T[0-9]{2}:[0-9]{2}' | tr -d T)
    echo "  -- Re-rendering annotated spectrogram (~30-60 sec)..."
    python3 "$TOOLS_DIR/drf_spectrogram.py" "$MY_STATION" \
        --output "$png" \
        --ylim=-2,2 \
        --callsign "$MY_CALL" --grid "$MY_GRID" \
        --annotate "${ann_s},${ann_e},Proposed TID window" \
        || true
    if [[ -f "$png" ]]; then
        echo "Re-rendered: $png"
        open_image "$png"
    fi
}

# Validate ISO-8601 timestamp format
valid_iso() {
    [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]
}

# Read an ISO time with re-prompt on bad format
read_iso() {
    local prompt="$1" var
    while true; do
        read -p "$prompt: " var
        if valid_iso "$var"; then
            echo "$var"
            return
        fi
        echo "  (format must be YYYY-MM-DDTHH:MM:SS, try again)" >&2
    done
}

# Add N minutes to an ISO time
add_minutes() {
    local t="$1" mins="$2"
    python3 -c "
from datetime import datetime, timedelta
dt = datetime.strptime('$t', '%Y-%m-%dT%H:%M:%S')
print((dt + timedelta(minutes=$mins)).strftime('%Y-%m-%dT%H:%M:%S'))"
}

# Duration in minutes between two ISO times
duration_min() {
    local s="$1" e="$2"
    python3 -c "
from datetime import datetime
s = datetime.strptime('$s', '%Y-%m-%dT%H:%M:%S')
e = datetime.strptime('$e', '%Y-%m-%dT%H:%M:%S')
print(int((e - s).total_seconds() / 60))"
}

if [[ $LAST_STAGE -lt 2 ]]; then
    pause_block "PAUSE 1 of 4 — Choose the TID analysis window"
    cat <<EOF
The reference-station spectrogram (and the version annotated with the
proposed window, if auto-detection succeeded) have been opened. Look
for a contiguous block of time during which:
  - A slow oscillation of the carrier track is visible (typical TID)
  - The carrier SNR stays high (no fades)
  - At least one full wave cycle is included

Common window lengths are 60-180 minutes.

EOF

    # If no proposal, get a fully manual entry and skip the menu
    if [[ -z "$PROPOSED_START" || -z "$PROPOSED_END" ]]; then
        echo "(No auto-proposal was generated.)"
        echo "Example: 2026-01-19T00:00:00 to 2026-01-19T01:15:00"
        echo
        WINDOW_START=$(read_iso "Start time (UTC, YYYY-MM-DDTHH:MM:SS)")
        WINDOW_END=$(read_iso "End time   (UTC, YYYY-MM-DDTHH:MM:SS)")
    else
        # Menu-driven editor
        WINDOW_START="$PROPOSED_START"
        WINDOW_END="$PROPOSED_END"

        while true; do
            DUR=$(duration_min "$WINDOW_START" "$WINDOW_END")
            echo
            echo "Current proposed window:"
            echo "    $WINDOW_START  ->  $WINDOW_END   (duration: ${DUR} min)"
            echo
            cat <<EOF
What would you like to do?
  [Enter]   Accept this window and continue
  v         View the annotated spectrogram again
  s         Change START time only
  e         Change END time only
  d         Change DURATION (keeps start fixed)
  t         Change START TIME and DURATION
  b         Change BOTH start and end
EOF
            read -p "Choice [Enter = accept]: " CHOICE
            case "${CHOICE,,}" in
                "" )
                    echo "Accepted: $WINDOW_START -> $WINDOW_END"
                    break
                    ;;
                v )
                    rerender_proposal "$WINDOW_START" "$WINDOW_END"
                    ;;
                s )
                    NEW_START=$(read_iso "New START time (UTC, YYYY-MM-DDTHH:MM:SS)")
                    WINDOW_START="$NEW_START"
                    rerender_proposal "$WINDOW_START" "$WINDOW_END"
                    ;;
                e )
                    NEW_END=$(read_iso "New END time (UTC, YYYY-MM-DDTHH:MM:SS)")
                    WINDOW_END="$NEW_END"
                    rerender_proposal "$WINDOW_START" "$WINDOW_END"
                    ;;
                d )
                    read -p "New duration in minutes (e.g. 75): " NEW_DUR
                    if [[ "$NEW_DUR" =~ ^[0-9]+$ ]] && [[ "$NEW_DUR" -gt 0 ]]; then
                        WINDOW_END=$(add_minutes "$WINDOW_START" "$NEW_DUR")
                        rerender_proposal "$WINDOW_START" "$WINDOW_END"
                    else
                        echo "  (must be a positive integer)"
                    fi
                    ;;
                t )
                    NEW_START=$(read_iso "New START time (UTC, YYYY-MM-DDTHH:MM:SS)")
                    read -p "New duration in minutes (e.g. 75): " NEW_DUR
                    if [[ "$NEW_DUR" =~ ^[0-9]+$ ]] && [[ "$NEW_DUR" -gt 0 ]]; then
                        WINDOW_START="$NEW_START"
                        WINDOW_END=$(add_minutes "$WINDOW_START" "$NEW_DUR")
                        rerender_proposal "$WINDOW_START" "$WINDOW_END"
                    else
                        echo "  (duration must be a positive integer; nothing changed)"
                    fi
                    ;;
                b )
                    WINDOW_START=$(read_iso "New START time (UTC, YYYY-MM-DDTHH:MM:SS)")
                    WINDOW_END=$(read_iso "New END time   (UTC, YYYY-MM-DDTHH:MM:SS)")
                    rerender_proposal "$WINDOW_START" "$WINDOW_END"
                    ;;
                * )
                    echo "  (Unrecognized choice; type one of: Enter, v, s, e, d, t, b)"
                    ;;
            esac
        done
    fi

    echo
    echo "Final window: $WINDOW_START -> $WINDOW_END"
    save_state 2
fi

# -----------------------------------------------------------------------------
# STAGE 3: quick sanity check on the reference station with this window
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 3 ]]; then
    banner "STAGE 3 — sanity-check the window on the reference station"
    hint "Extracting Doppler CSV for the chosen window (~10-30 seconds)."
    REF_CSV="${MY_CALL//\//_}.csv"
    REF_PNG="${MY_CALL//\//_}_quicklook.png"
    python3 "$TOOLS_DIR/drf_to_doppler.py" "$MY_STATION" \
        --start "$WINDOW_START" --end "$WINDOW_END" \
        --decim-seconds "$DECIM_SECONDS" \
        --subchannel 0 \
        --output "$REF_CSV" --plot "$REF_PNG"
    echo "Wrote $REF_PNG (sanity check)"
    open_image "$REF_PNG"
    echo
    echo "Does the Doppler trace match the wave you saw in the spectrogram?"
    while true; do
        read -p "Continue? [Y/n]: " ANS
        case "${ANS:-y}" in
            y|Y|yes|YES|Yes)
                break
                ;;
            n|N|no|NO|No)
                echo "Aborting — re-run with --reset to pick a different window."
                exit 1
                ;;
            *)
                echo "  (Please answer y or n.)"
                ;;
        esac
    done
    save_state 3
fi

# -----------------------------------------------------------------------------
# STAGE 4: find companion stations
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 4 ]]; then
    banner "STAGE 4 — find candidate companion stations"
    hint "Querying PSWS for all stations active on $EVENT_DATE."
    hint "First run on a fresh cache takes 3-5 minutes (queries ~280 stations);"
    hint "subsequent runs use the cached directory and are much faster."

    # Run with a spinner so the user can see we're still alive.
    # The script's own output (the candidate list) is captured and
    # printed at the end.
    run_with_spinner "find_event_stations.py" \
        python3 "$TOOLS_DIR/find_event_stations.py" \
            --date "$EVENT_DATE" \
            --my-lat "$MY_LAT" --my-lon "$MY_LON" \
            --my-call "$MY_CALL" \
        | tee "find_event_stations_${EVENT_DATE}.txt"

    save_state 4
fi

# -----------------------------------------------------------------------------
# PAUSE 2: pick companions
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 5 ]]; then
    pause_block "PAUSE 2 of 4 — Choose companion stations"
    cat <<EOF
From the list above, pick 2–6 companion stations (your reference station
is already in the analysis). Aim for AZIMUTHAL SPREAD — stations to your
N, E, S, and W if possible — over raw correlation score.

Enter the companion station shortnames (the leftmost column of the
ranked list), comma-separated. Example:
  aa6bd, w7lux, ac0g_nd

EOF
    read -p "Companion stations: " COMPANIONS_RAW
    # Normalize: strip whitespace, lowercase, hyphen-to-underscore for paths
    COMPANIONS=$(echo "$COMPANIONS_RAW" | tr ',' '\n' | \
        sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
        tr 'A-Z' 'a-z' | tr '/' '_' | paste -sd ',' -)
    echo "Companions chosen: $COMPANIONS"
    save_state 5
fi

# -----------------------------------------------------------------------------
# PAUSE 3: download tarballs
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 6 ]]; then
    pause_block "PAUSE 3 of 4 — Download companion DRF data"
    cat <<EOF
Now download the DRF tarballs for each companion station from PSWS:
  https://pswsnetwork.eng.ua.edu/observations/

The search list above includes direct download URLs for each station.

Extract each tarball into a directory named after the station, in this
working directory ($WORKDIR). The expected layout is:

EOF
    IFS=',' read -ra COMPANION_LIST <<< "$COMPANIONS"
    for s in "${COMPANION_LIST[@]}"; do
        echo "  $WORKDIR/$s/ch0/..."
    done
    echo
    read -p "Press Enter once all directories are in place: " _

    # Verify each companion exists
    MISSING=""
    for s in "${COMPANION_LIST[@]}"; do
        if [[ ! -d "$WORKDIR/$s/ch0" ]]; then
            MISSING="$MISSING $s"
        fi
    done
    if [[ -n "$MISSING" ]]; then
        echo "Missing or invalid DRF directories:$MISSING"
        echo "Place them under $WORKDIR/ and re-run analyze_event.sh"
        exit 3
    fi
    echo "All companion directories present."
    save_state 6
fi

# -----------------------------------------------------------------------------
# STAGE 7: verify each station and find correct subchannel for 10 MHz
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 7 ]]; then
    banner "STAGE 7 — inspect each DRF and identify 10 MHz subchannel"
    hint "Reading metadata + signal-level check from each companion DRF."
    hint "Typically a few seconds per station."
    python3 "$TOOLS_DIR/drf_inspect.py" --all . --frequency 10 \
        | tee drf_inspect_output.txt
    echo
    echo "Subchannel mapping has been recorded in drf_inspect_output.txt"
    save_state 7
fi

# -----------------------------------------------------------------------------
# STAGE 8: extract Doppler CSVs for all stations
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 8 ]]; then
    banner "STAGE 8 — extract Doppler CSV for each station"
    hint "Reducing raw I/Q to Doppler-vs-time for each station."
    hint "Typically 10-30 seconds per station."

    # Extract subchannel info from drf_inspect output. Parse lines like:
    #   >>> For 10.0 MHz, USE: --subchannel N
    # Map them to their preceding "=== ./station ===" line.
    python3 <<EOF > station_subchannels.txt
import re
sub_for = {}
current = None
for line in open('drf_inspect_output.txt'):
    m = re.match(r'^=== \./(.+?) ===\s*$', line)
    if m:
        current = m.group(1)
        sub_for[current] = 0
        continue
    m = re.search(r'USE:\s*--subchannel\s+(\d+)', line)
    if m and current:
        sub_for[current] = int(m.group(1))
for k, v in sub_for.items():
    print(f"{k}\t{v}")
EOF

    # Reference station and companions — extract with both methods,
    # show overlay spectrogram, let operator choose FFT or autocorr.
    REF_NAME="${MY_STATION#./}"
    REF_NAME="${REF_NAME%/}"
    REF_CSV_FINAL="${REF_NAME}.csv"
    REF_PNG_FINAL="${REF_NAME}.png"
    rm -f station_methods.txt
    extract_with_overlay "$REF_NAME" "$MY_STATION" "0"
    [[ -f "${REF_NAME}.csv" ]] && cp "${REF_NAME}.csv" "$REF_CSV_FINAL"
    [[ -f "${REF_NAME}.png" ]] && cp "${REF_NAME}.png" "$REF_PNG_FINAL"
    # Each companion
    IFS=',' read -ra COMPANION_LIST <<< "$COMPANIONS"
    for s in "${COMPANION_LIST[@]}"; do
        SUB=$(awk -F'\t' -v s="$s" '$1 == s {print $2; exit}' station_subchannels.txt)
        SUB="${SUB:-0}"
        echo "  $s: --subchannel $SUB"
        extract_with_overlay "$s" "./$s" "$SUB"
    done
    save_state 8
fi

# -----------------------------------------------------------------------------
# PAUSE 4: visual sanity-check of each station
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 9 ]]; then
    pause_block "PAUSE 4 of 4 — Quality-check each station"

    REF_NAME="${MY_STATION#./}"
    REF_NAME="${REF_NAME%/}"
    IFS=',' read -ra COMPANION_LIST <<< "$COMPANIONS"

    # Run automated quality summary if quality_summary.py is available
    if [[ -x "$TOOLS_DIR/quality_summary.py" ]] || [[ -f "$TOOLS_DIR/quality_summary.py" ]]; then
        # Build list of CSVs to score
        QUALITY_CSVS=("${REF_NAME}.csv")
        for s in "${COMPANION_LIST[@]}"; do
            [[ -f "${s}.csv" ]] && QUALITY_CSVS+=("${s}.csv")
        done
        python3 "$TOOLS_DIR/quality_summary.py" --suggest-shorten "${QUALITY_CSVS[@]}" | tee .quality_summary_output || true

        # Render the multi-station stacked Doppler plot so the operator
        # can see the array view in one image before deciding whether
        # all stations look good.
        render_pause4_stack
    fi

    cat <<EOF
Per-station Doppler PNGs have been written. Open each one and confirm:
  - The wave is visible (same shape as your reference station)
  - SNR is mostly above 30 dB through the analysis window
  - No sustained fades or RFI bursts

The quality table above flags stations with high jitter, low SNR,
excursions, or end-fade. Use it as a guide alongside the visual
inspection. Stations rated POOR or BAD usually should be dropped.

EOF
    open_image "${REF_NAME}.png"
    for s in "${COMPANION_LIST[@]}"; do
        open_image "${s}.png"
    done

    while true; do
        read -p "Do all stations look good? [yes/no]: " ALLGOOD
        case "${ALLGOOD,,}" in
            y|yes)
                DROP_RAW=""
                break
                ;;
            n|no)
                read -p "Stations to DROP (comma-separated, or empty/n/none to proceed without drops): " DROP_RAW
                # Treat empty input, "n", "no", or "none" as "proceed
                # without any drops" — useful when the operator answered
                # "no" because they want to tighten the window (handled
                # below by pause4_tightening_loop), not because they want
                # to drop stations.
                case "${DROP_RAW,,}" in
                    ""|n|no|none)
                        DROP_RAW=""
                        break
                        ;;
                    *)
                        break
                        ;;
                esac
                ;;
            *)
                echo "  (Please answer 'yes' or 'no'.)"
                ;;
        esac
    done
    if [[ -n "$DROP_RAW" ]]; then
        DROP_NORMALIZED=$(echo "$DROP_RAW" | tr ',' '\n' | \
            sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
            tr 'A-Z' 'a-z' | tr '/' '_' | paste -sd ',' -)
        # Remove dropped stations from COMPANIONS
        NEW_LIST=()
        for s in "${COMPANION_LIST[@]}"; do
            if ! echo ",$DROP_NORMALIZED," | grep -q ",$s,"; then
                NEW_LIST+=("$s")
            fi
        done
        COMPANIONS=$(IFS=,; echo "${NEW_LIST[*]}")
        echo "After drops, companions are: $COMPANIONS"
    fi

    # PR-D: Offer to tighten the analysis window if quality_summary
    # flagged end-fade. Loops up to 3 iterations or until no more
    # suggestions appear; safe-by-default prompt (Enter = keep current).
    pause4_tightening_loop

    # New in v1.4.3: offer smoothing for stations with high jitter.
    # quality_summary.py's output (printed earlier in this stage) has a
    # column for jitter in Hz. Look for any line with a numeric jitter
    # value > 0.15 Hz; if found, offer to enable smoothing on the DOA run.
    SMOOTH_FOR_DOA=""
    if [[ -f .quality_summary_output ]]; then
        HIGH_JITTER_FOUND=$(awk '
            /^  [a-zA-Z0-9_]/ && NF >= 6 {
                # Field 3 is jitter — try to parse as float
                jitter = $3 + 0
                if (jitter > 0.15) print $1
            }
        ' .quality_summary_output 2>/dev/null | head -1)

        if [[ -n "$HIGH_JITTER_FOUND" ]]; then
            echo ""
            echo "One or more stations show high jitter (>0.15 Hz)."
            echo "Smoothing the Doppler series before cross-correlation can help"
            echo "the DOA inversion converge on the wave signal rather than noise."
            read -p "Enable smoothing (Savitzky-Golay 60s window) for DOA? [y/N]: " smyn
            case "${smyn,,}" in
                y|yes)
                    SMOOTH_FOR_DOA="60"
                    echo "  Smoothing will be applied (60s window)."
                    ;;
                *)
                    echo "  No smoothing — raw Doppler series will be used."
                    ;;
            esac
        fi
    fi

    save_state 9
fi

# -----------------------------------------------------------------------------
# STAGE 10: build DOA config and run inversion
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 10 ]]; then
    banner "STAGE 10 — build DOA config and run inversion"
    hint "Cross-correlating all station pairs and solving for the wave"
    hint "direction and speed (~5-15 seconds)."

    # We know exactly which stations should be in the DOA: the reference
    # station plus whatever's left in COMPANIONS after Pause 4's drops.
    # Build event.json directly rather than letting tid_doa_config.py scan
    # the directory (which would pick up the survey CSV and any other
    # stray files).
    REF_NAME="${MY_STATION#./}"
    REF_NAME="${REF_NAME%/}"
    REF_CSV_PATH="${REF_NAME}.csv"

    python3 - "$WINDOW_START" "$WINDOW_END" "$DECIM_SECONDS" \
            "$MY_CALL" "$REF_CSV_PATH" "$MY_LAT" "$MY_LON" \
            "$COMPANIONS" <<'PYEOF' > event.json
import json, sys, os, re

window_start = sys.argv[1]
window_end   = sys.argv[2]
decim        = int(sys.argv[3])
my_call      = sys.argv[4]
ref_csv      = sys.argv[5]
ref_lat      = float(sys.argv[6])
ref_lon      = float(sys.argv[7])
companions   = [s.strip() for s in sys.argv[8].split(',') if s.strip()]

# Sanitize callsign for use as a station name in the config
def sanitize(name):
    return re.sub(r'[^A-Za-z0-9_]+', '_', name)

stations = [{
    "name": sanitize(my_call),
    "file": ref_csv,
    "lat":  round(ref_lat, 4),
    "lon":  round(ref_lon, 4),
}]

# For each companion, look up its lat/lon by reading the DRF metadata
# directly. This is robust against the CSV not having lat/lon columns.
try:
    import digital_rf as drf
    have_drf = True
except ImportError:
    have_drf = False

def latlon_from_drf(station_dir):
    if not have_drf:
        return None, None
    metadata_dir = os.path.join(station_dir, "ch0", "metadata")
    if not os.path.isdir(metadata_dir):
        return None, None
    try:
        mr = drf.DigitalMetadataReader(metadata_dir)
        b = mr.get_bounds()
        sample = mr.read(b[0], b[0] + 1)
        if not sample:
            return None, None
        meta = list(sample.values())[0]
        lat = meta.get('lat')
        lon = meta.get('long')
        if lat is None or lon is None:
            return None, None
        return float(lat), float(lon)
    except Exception:
        return None, None

missing = []
for s in companions:
    lat, lon = latlon_from_drf("./" + s)
    if lat is None or lon is None:
        missing.append(s)
        continue
    stations.append({
        "name": sanitize(s),
        "file": f"{s}.csv",
        "lat": round(lat, 4),
        "lon": round(lon, 4),
    })

if missing:
    sys.stderr.write(
        f"ERROR: could not read lat/lon from DRF metadata for: {', '.join(missing)}\n"
        f"  Add them manually to event.json before running tid_doa.py.\n")

if len(stations) < 3:
    sys.stderr.write(
        f"WARNING: only {len(stations)} station(s) ready; tid_doa.py needs at least 3.\n")

cfg = {
    "_comment": f"Generated by analyze_event.sh from reference station {my_call} plus companions.",
    "event_start_utc": window_start.replace('T', 'T') + 'Z' if not window_start.endswith('Z') else window_start,
    "event_end_utc":   window_end.replace('T', 'T') + 'Z' if not window_end.endswith('Z') else window_end,
    "resample_seconds": decim,
    "use_bandpass": False,
    "min_expected_speed_m_s": 100,
    "stations": stations,
}
print(json.dumps(cfg, indent=2))
PYEOF

    echo "Wrote event.json with $(python3 -c "import json; print(len(json.load(open('event.json'))['stations']))") stations."

    # Run the inversion
    SMOOTH_FLAG=""
    if [[ -n "$SMOOTH_FOR_DOA" ]]; then
        SMOOTH_FLAG="--smooth $SMOOTH_FOR_DOA"
    fi
    python3 "$TOOLS_DIR/tid_doa.py" event.json $SMOOTH_FLAG | tee doa_output.txt
    save_state 10
fi

# -----------------------------------------------------------------------------
# STAGE 11: generate figures
# -----------------------------------------------------------------------------
if [[ $LAST_STAGE -lt 11 ]]; then
    banner "STAGE 11 — generate figures"
    hint "Rendering annotated spectrogram, stacked Doppler plot, and"
    hint "array-geometry map (~30 seconds total)."

    # Extract heading and speed from the DOA output
    AZIM=$(grep "heading toward" doa_output.txt | grep -oE '[0-9]+\.[0-9]+°' | head -1 | tr -d '°' || true)
    SPEED=$(grep "Phase speed" doa_output.txt | grep -oE '[0-9]+\.[0-9]+ m/s' | head -1 | grep -oE '[0-9]+\.[0-9]+' || true)
    AZIM=${AZIM:-215}
    SPEED=${SPEED:-666}

    # Annotated spectrogram (window highlighted)
    ANNO_START=$(echo "$WINDOW_START" | grep -oE 'T[0-9]{2}:[0-9]{2}' | tr -d T)
    ANNO_END=$(echo "$WINDOW_END" | grep -oE 'T[0-9]{2}:[0-9]{2}' | tr -d T)
    python3 "$TOOLS_DIR/drf_spectrogram.py" "$MY_STATION" \
        --output "ref_${EVENT_DATE}_annotated.png" \
        --ylim=-2,2 \
        --callsign "$MY_CALL" --grid "$MY_GRID" \
        --annotate "${ANNO_START},${ANNO_END},Analysis window"

    # Stacked multi-station plot
    python3 "$TOOLS_DIR/tid_stack_plot.py" \
        --config event.json \
        --output "stack_${EVENT_DATE}.png" \
        --ylim=-2,2

    # Array geometry map with wave arrow
    python3 "$TOOLS_DIR/tid_map.py" \
        --config event.json \
        --output "array_map_${EVENT_DATE}.png" \
        --azimuth-toward "$AZIM" --speed "$SPEED"

    save_state 11
fi

# -----------------------------------------------------------------------------
# DONE
# -----------------------------------------------------------------------------
banner "DONE"
cat <<EOF
Outputs in $WORKDIR:

  Per-station Doppler:
    ${MY_STATION#./}.csv, ${MY_STATION#./}.png
    <station>.csv and <station>.png for each companion

  DOA event config:           event.json
  DOA result (text):          doa_output.txt

  Figures:
    ref_${EVENT_DATE}_annotated.png   (reference-station spectrogram + window)
    stack_${EVENT_DATE}.png           (stacked multi-station Doppler)
    array_map_${EVENT_DATE}.png       (array geometry + wave-direction arrow)

State file: $STATE_FILE (delete or use --reset to start over)

Next steps:
  - Inspect the final figures
  - If satisfied, copy the case-study template and fill it in
  - Push to your repo / docs site

EOF
