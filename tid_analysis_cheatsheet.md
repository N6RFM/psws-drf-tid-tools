# TID Analysis Cheatsheet — reference event: 2026-01-19

**Current release: v4.9.3** · Repo: `github.com/N6RFM/psws-drf-tid-tools`

**Stations:** N6RFM (keystone), AA6BD, AC0G_ND, W7LUX
**Known-good result:** N6RFM, AA6BD, AC0G_ND → **682 m/s from 63° true
bearing**, all 5 diagnostics pass. **Independently confirmed** by real
GNSS TEC data (§7) — 0.0 min triangle-closure residual across all
three station pairs. (Adding W7LUX back reintroduces a weak
N6RFM↔W7LUX correlation and pulls in more flags — see §5.)

---

## 0. Which machine, which path

This repo lives at a **different path on each machine** — worth
double-checking before pasting any command below:

| Machine | Repo path |
|---|---|
| bob-B360M-DS3H | `~/psws-tools-pr` |
| Go-2 | `~/psws-drf-tid-tools` |

Everything below uses `~/psws-drf-tid-tools` — substitute
`~/psws-tools-pr` if you're on bob-B360M-DS3H.

---

## 1. Viewing this cheatsheet in VS Code

```
code ~/Downloads/tid_analysis_cheatsheet.md
```
This opens the file as **raw text** — you'll see the actual `#`,
`` ` ``, and `**` markdown characters, in a tab at the top labeled
`tid_analysis_cheatsheet.md`.

**To switch to the rendered view:** press **`Ctrl+Shift+V`**. A
**second tab** opens next to the first one, usually labeled
`Preview tid_analysis_cheatsheet.md` with a small magnifying-glass
icon. That second tab is the one showing headers, bold text, and
formatted code blocks — the raw-text tab doesn't change, it's still
sitting there underneath/behind it.

**To switch back and forth between the two:** just click whichever
tab you want at the top of the window — the plain-file tab for raw
text, the "Preview" tab for the rendered view.

**To copy a command:** make sure you're on the **Preview** tab (not
the raw-text tab), then hover directly over the code block you want —
a small copy icon appears in its top-right corner. Click it.

`Ctrl+K V` (press `Ctrl+K`, release, then press `V`) opens the preview
pinned to the right side instead, so both views are visible at once.

---

## 2. Start a session

```
cd ~/psws-drf-tid-tools
source .venv/bin/activate
git pull origin main
git fetch --tags          # tags don't always come down with a plain pull
python3 check_install.py
```

If `check_install.py` shows the six `hamsci_LSTID_detection`-specific
packages (`dask`/`h5py`/`polars`/`pyarrow`/`pysolar`/`statsmodels`) as
missing and you don't plan to use the LSTID checkbox this session,
that's fine — they're intentionally not part of this repo's own
requirements. See §7 if you do want them.

---

## 3. No live data, or PSWS down? Test against the mock server instead

```
# Terminal 1 — leave running
python3 mock_psws_server.py

# Terminal 2
export PSWS_BASE_URL=http://127.0.0.1:8765
curl -s http://127.0.0.1:8765/stations/stations/ | head -3   # sanity check
python3 download_companions.py --date 2099-01-01 \
    --stations TESTKEY TESTA TESTB TESTC \
    --out-dir ~/Downloads/tid_event_20990101
python3 tid_workflow.py --event-dir ~/Downloads/tid_event_20990101 \
    --stations TESTKEY,TESTA,TESTB,TESTC --my-station TESTKEY --max-lag 30
```
Fake stations have a known ground truth (400 m/s from 270°, 60-min
period) baked in — a real answer to check `tid_doa.py`'s result
against. `PSWS_BASE_URL` only lasts the terminal session it's exported
in. Full details: `docs/TESTING_WITHOUT_LIVE_DATA.md`.

**GUI alternative for discovery/download:** `python3 tid_intake_helper.py`
walks through discover → download → generates the `tid_workflow.py`
command for you, real or mock data either way.

---

## 4. Get data for a NEW event (not needed for 2026-01-19 — already downloaded)

```
mkdir -p ~/Downloads/tid_event_YYYYMMDD

python3 download_companions.py --date YYYY-MM-DD \
    --stations YOURCALL \
    --out-dir ~/Downloads/tid_event_YYYYMMDD

python3 drf_inspect.py ~/Downloads/tid_event_YYYYMMDD/yourcall

python3 find_event_stations.py \
    --date YYYY-MM-DD \
    --my-lat LAT --my-lon LON --my-call YOURCALL

python3 download_companions.py --date YYYY-MM-DD \
    --stations STN1 STN2 STN3 \
    --out-dir ~/Downloads/tid_event_YYYYMMDD
```

---

## 5. Run the guided workflow on the reference event

```
python3 tid_workflow.py \
    --event-dir ~/Downloads/tid_event_20260119 \
    --stations N6RFM,AA6BD,W7LUX,AC0G_ND \
    --my-station N6RFM \
    --max-lag 30 \
    --resume
```

`--resume` picks up wherever `tid_workflow_state.json` left off — all
four stations already have completed wave-fit extractions from prior
sessions, so this will likely skip straight to the DOA step (§6).

**What happens automatically:**
- N6RFM (keystone) is processed first and is the reference for
  everything below.
- Immediately after each station's full-day spectrogram is generated,
  it opens automatically and you're asked whether to redraw it at a
  tighter Y-axis range — every station, every time, since the
  keystone can't benefit from auto-tuning on its own first pass.
- Later stations' zoomed spectrograms auto-tighten toward N6RFM's
  measured amplitude.
- Later stations' wave-fit clicks show N6RFM's measured period as a
  `--period-hint` sanity check.
- After a DOA result exists, you're offered a station map (§6) and
  pointed toward external cross-checks (§7).

**Useful extra flags, if re-extracting anything:**
```
--ylim-margin-pct 25        # 25% more headroom than the auto-tightened view
--ylim-margin-pct 50        # 50% more headroom (used for AA6BD/W7LUX redo below)
--ylim-half-range 2         # lock every station to ±2 Hz explicitly (disables auto-tune)
--no-keystone-auto-tune     # disable both y-axis tightening and period-hint seeding
```

**Extraction method for this event:** wave-fit (option 4).

---

## 5b. Wave-fit clicking notes specific to this event

- **AA6BD** has a sharp discontinuity around t≈0.65h (a near-vertical
  Doppler jump) — click only the smooth hump from ~0.65h to ~1.6h,
  aiming at the peak near t≈1.1h (matches N6RFM's own peak). Clicking
  across the jump previously produced a bad T=68.7 min fit; the
  corrected fit was T=36.9 min.
- **AC0G_ND** has 9 channel-nums available; WWV 10 MHz is channel-num
  **4** (the 56 dB SNR channel is 5 MHz on channel-num 2 — don't
  confuse the two; channel-num 4 is the one to pick).
- General reminders: click 6+ points; compare against the period hint
  before accepting; use the stack plot if unsure which cycle to click:
  ```
  python3 tid_stack_plot.py \
      --config ~/Downloads/tid_event_20260119/tid_workflow_event.json \
      --output ~/Downloads/tid_event_20260119/stack_plot.png
  ```

---

## 6. DOA step — reproducing the known-good result

At the explore-loop prompt, type:

```
all
```

This tests every combination that keeps N6RFM. Expected ranking
(fewest flags first):

```
#   Stations                          Speed     From  Flags
---------------------------------------------------------------
1   N6RFM,AA6BD,AC0G_ND              682 m/s   63 deg     0
2   N6RFM,AC0G_ND,W7LUX             1107 m/s  312 deg     2
3   N6RFM,AA6BD,W7LUX                254 m/s  194 deg     3
4   N6RFM,AA6BD,AC0G_ND,W7LUX        958 m/s   45 deg     3
```

Pick **`1`** to select N6RFM/AA6BD/AC0G_ND as the final result. Press
Enter at the next prompt to finish, then **`y`** when asked to
generate a station map.

**Other explore-loop commands:**
```
<name>          # drop a station
add <name>      # bring a dropped station back
```
(N6RFM can't be dropped — it's the keystone.)

### Direct `tid_doa.py` use (outside the guided workflow)

```
python3 tid_doa.py ~/Downloads/tid_event_20260119/tid_workflow_event.json --drop W7LUX
```

Every run now also writes `tid_doa_result.json` next to the config —
speed, bearing, station list, timestamp — which `tid_map.py` and
`tid_external_helper.py` (§7) both read automatically instead of
requiring the numbers to be retyped.

⚠️ **Trap:** the guided workflow's explore loop overwrites
`tid_workflow_event.json`'s station list every time you finish a
session — if a prior session ended with a station dropped, it's
genuinely gone from the file. Run `tid_workflow.py --resume` first if
you want the full 4-station set back in the config before using
`--drop` directly.

### Station map, directly (if you skipped the end-of-run prompt)

```
python3 tid_map.py \
    --config ~/Downloads/tid_event_20260119/tid_workflow_event.json \
    --output ~/Downloads/tid_event_20260119/tid_map.png \
    --azimuth-toward 243.2 \
    --speed 682.0
```
(`--azimuth-toward` is the *heading*, not the bearing-from — 63.2°
from + 180° = 243.2° toward, for this event's result.)

---

## 7. External validation — Kp/AE, GNSS TEC, and LSTID detection

**GUI (recommended):**
```
python3 tid_external_helper.py
```
Load the event directory — auto-fills the DOA speed/bearing from
`tid_doa_result.json` — check the boxes for whichever sources you
want, click **Run Selected**. A moving progress bar and "Running:
\<step\>..." label confirm it's actually working; real network calls
can legitimately take a while.

**What's already been confirmed for this event:**
- **Kp/AE:** onset Kp=3.3, consistent with the event timing. AE
  sometimes times out fetching from WDC Kyoto (their server, not a
  bug here) — safe to retry.
- **GNSS TEC:** genuinely excellent independent corroboration —
  **0.0 min RMS triangle-closure residual** across N6RFM/AA6BD/AC0G_ND,
  confirming the same 682 m/s / 63° result via a completely
  independent MIT Haystack Madrigal dataset. Real network calls to
  `cedar.openmadrigal.org` occasionally time out (their server; a
  small academic service, not always up) — just retry later if so.
- **LSTID detection:** needs the separate `hamsci_LSTID_detection`
  repo (below) plus real amateur-radio HF spot data for the date,
  which can have several weeks of upload latency.

**Manual CLI equivalents**, if preferred:
```
python3 evaluate_external.py --date 2026-01-19 \
    --event-start 2026-01-19T00:15:00+00:00 \
    --event-end 2026-01-19T02:02:00+00:00 \
    --speed-m-s 682.0 --azimuth-from 63.2 \
    --output-dir ~/Downloads/tid_event_20260119/runs/external_evaluations

python3 fetch_madrigal_tec.py \
    --config ~/Downloads/tid_event_20260119/tid_workflow_event.json \
    --user-name 'Your Name' --user-email you@example.com \
    --user-affiliation amateur \
    --output-dir ~/Downloads/tid_event_20260119/gnss_tec \
    --doa-speed 682.0 --doa-azimuth-from 63.2
```

### Setting up HamSCI LSTID Detection (one time, separate repo)

```
git clone https://github.com/HamSCI/hamsci_LSTID_detection.git ~/hamsci_LSTID_detection
cd ~/hamsci_LSTID_detection
pip install -e .
```

⚠️ **This can silently downgrade shared packages** (numpy, scipy,
pandas, matplotlib, cartopy, pillow, h5py) if installed into the same
venv as `psws-drf-tid-tools`, since that repo pins exact versions
rather than minimums. **Harmless inside a venv** (confirmed — the
downgraded versions still satisfy this repo's own requirements), but
a real risk to *other* software (e.g. GNU Radio) if ever installed
without one. Full explanation: `docs/EXTERNAL_EVALUATION.md` §3.

```
python3 check_install.py    # confirm all 6 LSTID-specific deps show [OK]
python3 run_madrigal_tools.py --event ~/Downloads/tid_event_20260119 \
    --tool lstid --download
```

---

## 8. Cleanup

Safe to delete: `*_channel_nums/` thumbnail folders,
`*_wave_tid_candidate.csv` files, any empty `.downloads/` folder.

Keep: `runs/` (audit trail), `tid_workflow_state.json`,
`tid_workflow_event.json`, `tid_doa_result.json`, `station_coords.json`,
final `*_fullday.png` / `*_tid_zoom_clean.png` + sidecars, final
`*_wave_tid.csv` files, `gnss_tec/` and `lstid/` output folders.

---

## 9. Git workflow (branch → PR → merge → tag → release)

The pattern used for every change this project ships:

```
git checkout -b short-descriptive-branch-name
git add -A
git status                      # confirm staged list looks right BEFORE committing
git commit -m "One-line summary

Longer explanation of what and why. See CHANGELOG.md vX.Y.Z for
full details."
git push -u origin short-descriptive-branch-name
gh pr create --title "vX.Y.Z: short summary" --body "See CHANGELOG.md vX.Y.Z entry." --base main
gh pr merge --squash
git checkout main && git pull origin main
git tag -a vX.Y.Z -m "Short summary"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z -- Short summary" \
    --notes "$(sed -n '/^## vX.Y.Z/,/^## vPREV/p' CHANGELOG.md | sed '$d')"
git branch -d short-descriptive-branch-name    # local cleanup
```

If `gh` isn't authenticated on a machine yet:
```
gh auth login          # follow the browser prompt
gh auth setup-git       # wires gh's auth into plain git push/pull too
```

Syncing a second machine after a release:
```
git checkout main
git pull origin main
git fetch --tags
git tag --points-at HEAD   # should show the version just released
```

---

## 10. Reference docs (all current as of v4.9.3)

- `WORKFLOW_TUTORIAL.md` — full guided-workflow walkthrough
- `MANUAL_TUTORIAL.md` — step-by-step manual pipeline, tool by tool
- `docs/TESTING_WITHOUT_LIVE_DATA.md` — mock server, offline testing
- `docs/COOKBOOK.md` — task-oriented recipes
- `docs/ASSESSING_RESULTS.md` — how to read the 5 diagnostics
- `docs/EXTERNAL_EVALUATION.md` — Kp/AE, GNSS TEC, LSTID setup and
  the pinned-dependency venv gotcha
- `docs/TROUBLESHOOTING.md` — failure modes and fixes
- `CHANGELOG.md` — full version history, v4.6.0 through v4.9.3
- `docs/research-archive/` — archived research log from the retired
  `research_gui` branch
