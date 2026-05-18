# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Lives on the
`research-doppler-extraction` branch. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-17

---

## 1. One-paragraph status

v1.5.0 is shipped and released; `main` is protected (PR-only) and
must not be touched directly. All active work is on the
`research-doppler-extraction` branch, investigating whether complex
autocorrelation (Gwyn's method) extracts cleaner Doppler than the
toolkit's FFT carrier-tracking, especially on E-region-contaminated
data. The investigation is **paused, blocked on Gwyn (G3ZIL)**
sending his actual extracted 17 May 2024 dataset and his
autocorrelation parameters. An email requesting this has been sent.
The self-download route has been exhausted and documented; do not
pursue more self-download extraction without Gwyn's input.

## 2. Repo / branch state

- **`main`**: released, v1.5.0, PROTECTED (ruleset: PR required,
  block force-push, restrict deletion; verified live — a direct
  push is rejected). Do NOT attempt direct pushes to main. Any main
  change = branch → PR → merge. Latest main commit: the
  `apporach`/§4.2 doc-polish fix (HEAD `9bb63a0` at last check).
- **`research-doppler-extraction`**: active branch, all current
  work. Does NOT merge to main until further notice. Commits so
  far (newest first):
  - `9eec751` N5BRG dual-channel resolved; self-download closed
  - `f73279b` N4RVE/N5BRG self-download is noise
  - `fd0fb9e` first run on self-downloaded 17 May data + plotter fix
  - `c87d3cc` branch scaffold (FINDINGS, plotter, methodology subsection)
- Repo lives at `~/psws-tools-pr/`. Tools are invoked BY PATH from
  inside data folders, e.g. `python3 ~/psws-tools-pr/tid_pair.py …`
  (single-source-of-truth model — data folders contain NO code).
- `research/xcorr_lag_plot.py` exists ONLY on the research branch.
  Running it requires `git checkout research-doppler-extraction`
  first, or it's "file not found". `tid_doa.py`, `tid_pair.py`,
  `drf_to_doppler.py`, `drf_inspect.py` exist on both branches.

## 3. The actual research question (do not lose this)

**Primary question:** does complex-autocorrelation Doppler
extraction (Gwyn) produce a more coherent / contamination-robust
Doppler series than the toolkit's FFT carrier-tracking, on the same
I/Q? This is the WHOLE POINT. The N5BRG data-quality saga (entries
2–3) was preliminary plumbing, NOT the research question.

**First suggestive evidence (one data point, NOT a conclusion):**
on contaminated AC0G_ND/W7LUX, Gwyn's correlation peaked ~0.5–0.6
(his Image 2) while the toolkit's raw cross-correlation peaked only
0.162 (FINDINGS entry 1). Consistent with his hypothesis that
autocorrelation is more robust to E-region contamination —
suggestive only.

**Falsifiable gate (non-negotiable):** any complex-autocorrelation
extractor MUST reproduce the FFT extractor on CLEAN signal within a
stated tolerance before its behaviour on contaminated data means
anything. Fail ⇒ extractor is wrong, full stop. "But it looks
better on the bad pair" does not rescue a failed clean-data check.
This is the research branch's equivalent of the v1.5.0
additive-only proof.

## 4. What is BLOCKING (all on Gwyn)

Email sent to Gwyn asking for:
1. His actual extracted 17 May 2024 folder (DRF/CSVs + any DOA
   config) — for a like-for-like run.
2. His complex-autocorrelation parameters: window length, lag
   range, detrending/preprocessing. **Without this, the comparison
   cannot be set up faithfully** — a generic autocorrelation is
   uninterpretable. This ask is as important as ask 1.
3. Exact stations / pairs / UTC window he used.

Not yet asked, needed at his reply (in FINDINGS entry 3 as open):
4. Which N5BRG ANTENNA CHANNEL: NS (S000038, `N5BRG-Grape1`,
   `Grape1-01-Ch0-NS`) vs EW (S000040, `N5BRG-Grape1-MAG1`,
   `Grape1-02-Ch1-EW`). They differ MATERIALLY — not a detail.

Gwyn is `g3zil` on GitHub (Gwyn Griffiths, real, verified from
profile). Already invited as collaborator with WRITE access
(appropriate — main is protected so write is bounded).

## 5. The event & the data (reference)

Gwyn's event: **17 May 2024, ~19:00 UTC**, a large-scale TID.
Common transmitter reference = **WWV 10 MHz**. His method = two
WWV-referenced pairs + vector decomposition (NOT a single-reference
N-station DOA). His two published analyses of it DIFFER:
- Graphical/provisional (Image 1): 885 m/s @ 174°
- Revised digital RF (Image 2): 979 m/s @ 157°
  (VERIFY these two numbers against his slides before quoting back
  to him — transcribed, unverified.)
His pairs: Path 1 = WWV→N4RVE(Turn Island) + WWV→N5BRG;
Path 2 = WWV→AC0G_ND + WWV→W7LUX (he flagged Path 2 as
E-region-contaminated).

Self-downloaded data at `~/Downloads/tid_event_20240517/`:
- `ac0g_nd/` 9-subchannel; **10 MHz = subchannel 4** (default 0 =
  2.5 MHz noise — silent trap). Good at event time with `--subchannel 4`.
- `w7lux/` single-channel, clean, 42.7 dB. Good.
- `n4rve/` (= Turn Island, 48.54/-123.17) 9-subch, **10 MHz =
  subchannel 4**. Clean, 40.8 dB. Good.
- `n5brg/` currently the EW pull (S000040): better than NS but
  decays to 10–25 dB and spiky through 18–21 UTC — NOT clean at
  event time.
- `n5brg_old/` preserved = the NS pull (S000038): noise, saturated.
- CSVs/PNGs: ac0g_nd, w7lux, n4rve, n5brg_ew; xcorr_ac0g_w7lux.png,
  xcorr_n4rve_n5brg.png.

**Hard data lesson, applied every station this session:** always
`drf_inspect` first → identify the 10 MHz subchannel → extract →
check **event-time (~19:00) SNR on the plot** → only then
correlate. A wrong-subchannel/weak extraction writes a
successful-looking CSV full of noise. Verified caught real problems
on AC0G_ND and N5BRG.

## 6. What the investigation HONESTLY established

- Toolkit, on correctly-extracted data, **independently reproduced
  Gwyn's E-region contamination diagnosis** on AC0G_ND/W7LUX:
  agreed with his lag to ~2 min on the strong 40–90 band
  (toolkit +20.0 min/r0.90 vs Gwyn +18.17 min/r0.92), across
  different extraction methods; flagged band-inconsistency rather
  than returning a confident wrong answer.
- Toolkit **correctly refused** noise (N4RVE/N5BRG-NS) and weak
  data (N5BRG-EW) — its own diagnostics fired. Three demonstrations
  this session of "fails recognisably, not silently"
  (ASSESSING_RESULTS.md §3.3): synthetic, contaminated, noise.
- Comparison to Gwyn's OVERALL result (979 m/s) is **demonstrably
  blocked** (proven by exhausting self-download), NOT done. Geometry
  also unreconciled (toolkit baseline 689 km@225° vs his slide
  900 km@221°) → **lags comparable, SPEEDS NOT**.
- NOT established / NOT claimed: that FFT is worse than
  autocorrelation. That's the open question, motivated by the
  0.162-vs-~0.55 single point, gated on Gwyn.

## 7. Next steps WHEN Gwyn replies (already scoped)

1. Run `tid_doa.py` v1.5.0 (diagnostics + run-log) on HIS data —
   the gating run. Determines if autocorrelation is "enhancement"
   or "urgent foundation issue".
2. Confirm which N5BRG channel he used (ask 4).
3. Implement complex-autocorrelation extractor MATCHING his
   parameters (ask 2). Apply the §3 falsifiable clean-data gate.
4. If it passes the gate: characterise both methods on
   AC0G_ND/W7LUX, run v1.5.0 diagnostics on each, write a finding
   (negative result — "FFT adequate" — is valid & publishable).
5. Production change to main ONLY if earned, via normal PR, same
   verification bar as every prior substantive change.

## 8. Other open / lower-priority threads

- METHODOLOGY.md "Interpreting the correlation curve" subsection is
  on the research branch (committed). Its clean-vs-contaminated
  FIGURE has only the contaminated half (AC0G_ND/W7LUX xcorr); the
  clean half is blocked on Gwyn's data. Do NOT manufacture it from
  weak data.
- `xcorr_lag_plot.py` is UNVERIFIED research code. Fixed this
  session: added `timestamp_utc` to TIME_CANDIDATES. Still
  outstanding: cross-check its peak lag vs `tid_pair.py` on a known
  pair before trusting its numbers (its curve SHAPE is the reliable
  signal; numbers provisional).
- Pre-existing minor items (not started, low priority): v1.4.0
  follow-up email to Gwyn; case-study v1.4.0 refinement note into
  the ReadTheDocs report; optional generic alias-free repo
  cheatsheet.
- The Gwyn reply email is SENT (the warm short version: 3 asks —
  folder, autocorr params, stations/window; mentions research
  branch + invite). Waiting on his response is the correct state.

## 9. Working discipline (why this project's results are trustworthy)

- Verify before acting. `drf_inspect` before extract; check
  event-time SNR before correlate; `git log -3` before any
  `reset --hard`; grep-verify file content before commit (heredoc
  terminal echo looks garbled but the FILE is correct — confirmed
  3×; trust grep, not the paste echo).
- Do not overclaim. Diagnosis reproduced ≠ numbers reproduced.
  Motivated ≠ concluded. Blocked ≠ partially done. Lags ≠ speeds
  (geometry). One data point ≠ a result.
- Negative/blocked results are recorded with equal weight; the
  blocker is documented as a finding, not hidden.
- Nothing reaches `main` without earning a verified PR.
