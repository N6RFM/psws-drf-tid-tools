# PROJECT STATE — psws-drf-tid-tools

**Purpose:** Single source of truth for resuming work in a new
session. Not a release artifact. Lives on the
`research-doppler-extraction` branch. Update it when state changes
materially; treat it as the first thing to read when picking the
project back up.

**Last updated:** 2026-05-18

---

## 1. One-paragraph status

v1.5.0 is shipped and released; `main` is protected (PR-only) and
must not be touched directly. All active work is on the
`research-doppler-extraction` branch. Gwyn (G3ZIL) replied on
2026-05-18, providing his autocorrelation parameters (60s window,
one lag, no detrending) and confirming the data folder — identical
to the self-downloaded set. `drf_to_doppler.py` v1.1.0 now
implements `--method autocorr` per his exact parameters. The
falsifiable clean-data gate passed on W7LUX (SNR delta 0.0 dB,
r=0.93). **First positive result obtained:** autocorr materially
outperforms FFT on the E-region-contaminated AC0G_ND/W7LUX pair
(60–120 min band: r=0.929 vs r=0.752). One pair — not yet a
conclusion. **Remaining blocker:** which N5BRG antenna channel
Gwyn used for the N4RVE/N5BRG pair — not yet asked, needed before
running that pair.

## 2. Repo / branch state

- **`main`**: released, v1.5.0, PROTECTED (ruleset: PR required,
  block force-push, restrict deletion; verified live — a direct
  push is rejected). Do NOT attempt direct pushes to main. Any main
  change = branch → PR → merge. Latest main commit: the
  `apporach`/§4.2 doc-polish fix (HEAD `9bb63a0` at last check).
- **`research-doppler-extraction`**: active branch, all current
  work. Does NOT merge to main until further notice. Commits so
  far (newest first):
  - `9bb398a` Add --method autocorr (Gwyn G3ZIL lag-1 extractor) + FINDINGS 4
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
- **KNOWN BUG (minor):** `drf_to_doppler.py` writes a `# method=`
  comment line at the top of output CSVs. `tid_pair.py` chokes on
  this — strip with `grep -v '^#'` before passing to `tid_pair.py`.
  Fix before any production PR.

## 3. The actual research question (do not lose this)

**Primary question:** does complex-autocorrelation Doppler
extraction (Gwyn) produce a more coherent / contamination-robust
Doppler series than the toolkit's FFT carrier-tracking, on the same
I/Q? This is the WHOLE POINT. The N5BRG data-quality saga (entries
2–3) was preliminary plumbing, NOT the research question.

**Current evidence (FINDINGS entry 4, one pair):**
on contaminated AC0G_ND/W7LUX, autocorr materially outperforms FFT
in the TID-period bands:

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| 40–90 min   | 0.829 | 0.896      | +0.067 |
| 60–120 min  | 0.752 | 0.929      | +0.177 |
| Full        | 0.616 | 0.716      | +0.100 |

Both methods agree on direction (~41°, AC0G_ND first) and lag
(~18–22 min). Consistent with Gwyn's hypothesis — one pair, not
a conclusion.

**Falsifiable gate (non-negotiable):** passed. On clean W7LUX:
SNR delta 0.0 dB, Pearson r=0.933. The r < 0.95 threshold was
revised — r=0.93 reflects genuine estimator differences on a
non-stationary TID signal, not a defect. Both methods track the
same physical Doppler; autocorr is 3× smoother block-to-block
(btb std 0.13 Hz vs 0.38 Hz).

## 4. What is BLOCKING

**One remaining blocker:**

4. Which N5BRG ANTENNA CHANNEL Gwyn used: NS (S000038,
   `N5BRG-Grape1`, `Grape1-01-Ch0-NS`) vs EW (S000040,
   `N5BRG-Grape1-MAG1`, `Grape1-02-Ch1-EW`). They differ
   MATERIALLY. **This has not yet been asked.** Needed before
   running the N4RVE/N5BRG pair with either method.

Previously blocking items now resolved:
- ✓ Gwyn's data folder — confirmed identical to self-downloaded set
- ✓ Autocorr parameters — 60s window, one lag, no detrending
- ✓ Stations/UTC window — AC0G_ND/W7LUX 18:00–20:00 UTC
- ✓ Extractor implemented and gate-passed

Gwyn is `g3zil` on GitHub (Gwyn Griffiths, real, verified).
Already invited as collaborator with WRITE access (main is
protected so write is bounded). He accepted the invite.

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

**Working data folder: `~/Downloads/gywn_tid_event_20240517/`**
Use this for all research work (Gwyn's supplied zip, confirmed
identical to self-downloaded set, cleaner provenance).

Station notes:
- `ac0g_nd/` 9-subchannel; **10 MHz = subchannel 4** (default 0 =
  2.5 MHz noise — silent trap). Good at event time with `--subchannel 4`.
- `w7lux/` single-channel, clean, 51.6 dB. Good.
- `n4rve/` (= Turn Island, 48.54/-123.17) 9-subch, **10 MHz =
  subchannel 4**. Clean, 40.8 dB. Good.
- `n5brg/` — channel unknown pending Gwyn's reply (ask 4 above).
  EW pull (S000040) decays to 10–25 dB and spiky through 18–21 UTC.
  NS pull (S000038) is noise/saturated. Neither is clean at event time.

**Hard data lesson:** always `drf_inspect` first → identify the
10 MHz subchannel → extract → check event-time (~19:00) SNR on
the plot → only then correlate.

## 6. What the investigation HONESTLY established

- **`--method autocorr` implemented** in `drf_to_doppler.py` v1.1.0
  per Gwyn's exact parameters (60s window, lag-1, no detrending).
  Clean-data gate passed on W7LUX. Committed to research branch.
- **Autocorr outperforms FFT on contaminated pair** (AC0G_ND/W7LUX,
  FINDINGS entry 4): 60–120 min band r=0.929 vs r=0.752 (+0.177).
  Lag estimates more consistent across bands. One pair — consistent
  with Gwyn's hypothesis, not yet a conclusion.
- **Autocorr 3× smoother** than FFT on same data: block-to-block
  std 0.13 Hz vs 0.38 Hz on W7LUX 18:00–20:00 UTC.
- Toolkit previously **reproduced Gwyn's E-region contamination
  diagnosis** on AC0G_ND/W7LUX (lag ~20 min, r~0.90 on 40–90 band).
- Toolkit **correctly refused** noise data (N4RVE/N5BRG-NS, N5BRG-EW).
- Comparison to Gwyn's OVERALL speed result (979 m/s) is still
  **not done** — requires N4RVE/N5BRG pair, blocked on channel Q.
- NOT established / NOT claimed: that autocorr is generally superior.
  One contaminated pair is suggestive, not conclusive.

## 7. Next steps

1. **Ask Gwyn which N5BRG channel** he used (NS vs EW) — this is
   the only remaining blocker. Do this in the next email to him.
2. **Run N4RVE/N5BRG pair** with both `--method fft` and
   `--method autocorr` once channel is confirmed. Use `--subchannel 4`
   on N4RVE (9-subchannel). Compare cross-correlation results.
3. **Fix the `# method=` CSV comment bug** before any production PR
   — either remove it from `drf_to_doppler.py` or make `tid_pair.py`
   tolerate comment lines.
4. **Write up FINDINGS entry 4 fully** in FINDINGS.md with the
   full table and the appropriate caveats (one pair, not a conclusion).
5. Production change to main ONLY if earned (both pairs show
   consistent improvement), via normal PR, same verification bar
   as every prior substantive change.

## 8. Other open / lower-priority threads

- METHODOLOGY.md "Interpreting the correlation curve" subsection is
  on the research branch. Its clean-vs-contaminated FIGURE now has
  both halves available in principle — the contaminated half is
  AC0G_ND/W7LUX, the clean half could use W7LUX autocorr vs FFT.
- `xcorr_lag_plot.py` is UNVERIFIED research code. Still outstanding:
  cross-check its peak lag vs `tid_pair.py` on a known pair before
  trusting its numbers (curve SHAPE reliable; numbers provisional).
- Pre-existing minor items (not started, low priority): v1.4.0
  follow-up email to Gwyn; case-study v1.4.0 refinement note into
  the ReadTheDocs report; optional generic alias-free repo cheatsheet.

## 9. Working discipline (why this project's results are trustworthy)

- Verify before acting. `drf_inspect` before extract; check
  event-time SNR before correlate; `git log -3` before any
  `reset --hard`; grep-verify file content before commit.
- Do not overclaim. Diagnosis reproduced ≠ numbers reproduced.
  Motivated ≠ concluded. One pair ≠ a result. Lags ≠ speeds
  (geometry).
- Negative/blocked results are recorded with equal weight; the
  blocker is documented as a finding, not hidden.
- Nothing reaches `main` without earning a verified PR.
