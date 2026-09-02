# Research archive

This directory preserves the research log from the `research_gui`
branch (and its collaboration counterpart, `gwyn-g3zil`), which was
retired on 2026-09-02.

## What this is

`research_gui` served as a working research log for validating
changes against real events before they were PR'd into `main`.
Per its own `FINDINGS.md` header:

> Code changes validated here are PR'd to `main` as they are
> confirmed. Research docs (this file, PROJECT_STATE.md,
> CHANGELOG.md) remain on research_gui and gwyn-g3zil only — never
> merged to main.

That is, the *code* changes described in these files have already
made their way into `main` over time through normal PRs — this
archive exists so the *narrative* (why a change was made, what was
tried and discarded, real bugs found during live testing against
actual station data) isn't lost once the branch itself is gone.

## Contents

- **`FINDINGS.md`** — 55+ dated research-log entries, chronicling
  real events analyzed (e.g. the 17 May 2024 and 19 January 2026
  LSTIDs), extraction issues found and resolved, and comparisons
  against independent analysis.
- **`PROJECT_STATE.md`** — a running project-state log reconstructed
  from git history and `FINDINGS.md`, covering the project's
  evolution from its v1.0.0 initial release onward.
- **`add_project_state_entry.py`** — the script `research_gui` used
  to append new dated sections to `PROJECT_STATE.md`. Kept for
  provenance; not wired into anything on `main` and not intended to
  be run against this archived copy.

## Provenance

Archived from `research_gui` at commit `c346d15` ("Sync research_gui
with main: CHANGELOG.md v4.4.0 entry"), dated 2026-07-13, the branch's
tip at the time of retirement. Content is preserved verbatim — no
edits were made during archival.

This is a historical snapshot, not an actively maintained document.
For current project history, see the top-level `CHANGELOG.md`.
