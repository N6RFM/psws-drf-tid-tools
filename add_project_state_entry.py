#!/usr/bin/env python3
"""
add_project_state_entry.py -- append a new numbered entry to
PROJECT_STATE.md without the manual cat/sed dance that has caused
real bugs twice already this project (a missing "---" separator before
the new entry, caught after the fact in two different sessions).

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

What it does automatically (the parts that kept getting done by hand
and getting it wrong):
  1. Finds the highest existing "## N." entry number and uses N+1 --
     no more manually tracking what the next number should be.
  2. Always inserts the "---" separator before the new entry, matching
     every other entry in the file -- no more forgetting it.
  3. Uses today's date automatically (UTC) unless overridden.
  4. Writes atomically (temp file + rename) so a crash mid-write can't
     leave PROJECT_STATE.md half-written.

USAGE
    # Body from a file:
    python3 add_project_state_entry.py \\
        --title "Fixed the frobnicator race condition" \\
        --body-file draft.md

    # Body from stdin (e.g. piped from another tool, or heredoc):
    python3 add_project_state_entry.py --title "Quick fix" <<'EOF'
    ### What changed
    One-line description of what happened.
    EOF

    # Preview without writing (prints what would be appended):
    python3 add_project_state_entry.py --title "..." --body-file draft.md --dry-run

    # Point at a different file (default: PROJECT_STATE.md in cwd):
    python3 add_project_state_entry.py --title "..." --body-file draft.md \\
        --project-state /path/to/PROJECT_STATE.md
"""

import argparse
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ENTRY_HEADER_RE = re.compile(r"^## (\d+)\.", re.MULTILINE)


def find_next_entry_number(text):
    """Highest existing '## N.' entry number, plus one. Starts at 1 if
    the file has no entries yet."""
    numbers = [int(m.group(1)) for m in ENTRY_HEADER_RE.finditer(text)]
    return (max(numbers) + 1) if numbers else 1


def build_entry(number, title, body, date_str):
    """Assemble one entry exactly matching the file's existing
    convention: a '---' separator, '## N. TITLE -- DATE' header, blank
    line, then the body verbatim."""
    header = f"## {number}. {title} -- {date_str}"
    body = body.rstrip("\n")
    return f"\n---\n{header}\n\n{body}\n"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True,
                     help="Entry title (goes after the auto-numbered '## N.')")
    ap.add_argument("--body-file", default=None,
                     help="File containing the entry body (markdown). "
                          "If omitted, reads body from stdin.")
    ap.add_argument("--date", default=None,
                     help="Date string for the entry (default: today, UTC, "
                          "YYYY-MM-DD)")
    ap.add_argument("--project-state", default="PROJECT_STATE.md",
                     help="Path to PROJECT_STATE.md (default: ./PROJECT_STATE.md)")
    ap.add_argument("--dry-run", action="store_true",
                     help="Print what would be appended, don't write anything")
    args = ap.parse_args()

    ps_path = Path(args.project_state)
    if not ps_path.exists():
        print(f"ERROR: {ps_path} not found. Run this from the repo root, "
              f"or pass --project-state /path/to/PROJECT_STATE.md.", file=sys.stderr)
        sys.exit(1)

    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.exists():
            print(f"ERROR: body file {body_path} not found.", file=sys.stderr)
            sys.exit(1)
        body = body_path.read_text()
    else:
        if sys.stdin.isatty():
            print("ERROR: no --body-file given and stdin is a terminal "
                  "(nothing piped in). Provide --body-file or pipe/heredoc "
                  "the body text.", file=sys.stderr)
            sys.exit(1)
        body = sys.stdin.read()

    if not body.strip():
        print("ERROR: entry body is empty.", file=sys.stderr)
        sys.exit(1)

    current_text = ps_path.read_text()
    number = find_next_entry_number(current_text)
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_entry = build_entry(number, args.title, body, date_str)

    if args.dry_run:
        print(f"Would append as entry #{number} to {ps_path}:")
        print(new_entry)
        return

    # Atomic write: build the full new content in a temp file, then
    # rename over the original -- a crash mid-write can't corrupt
    # PROJECT_STATE.md.
    updated_text = current_text.rstrip("\n") + "\n" + new_entry.lstrip("\n")
    fd, tmp_path = tempfile.mkstemp(
        dir=ps_path.parent, prefix=ps_path.name + ".", suffix=".tmp")
    try:
        with open(fd, "w") as f:
            f.write(updated_text)
        Path(tmp_path).replace(ps_path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    print(f"Appended entry #{number} to {ps_path} (dated {date_str}).")
    print(f"Title: {args.title}")
    print("Review with: git diff PROJECT_STATE.md")


if __name__ == "__main__":
    main()
