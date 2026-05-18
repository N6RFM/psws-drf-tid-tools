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
to the self-downloaded set. `drf_to_doppler.py` v1.1.1 now
implements `--method autocorr` per his exact parameters; the
clean-data gate passed on W7LUX. **Results obtained on both pairs:**
autocorr outperforms FFT in the TID-period bands (40–120 min) on
both AC0G_ND/W7LUX (r=0.929 vs 0.752) and N4RVE/N5BRG (r=0.894
vs 0.740). N4RVE/N5BRG lag matches Gwyn's 27 min exactly. One open
discrepancy: our AC0G_ND/W7LUX lag is +22 min vs Gwyn's +35 min —
stable across window widths, likely a pipeline difference.
Clarification email sent to Gwyn 2026-05-18. **Two open questions
pending his reply:** (1) any extraction steps beyond lag-1 with no
detrending? (2) which N5BRG antenna channel did he use?

## 2. Repo / branch state

- **`main`**: released, v1.5.0, PROTECTED (ruleset: PR required,
  block force-push, restrict deletion; verified live — a direct
  push is rejected). Do NOT attempt direct pushes to main. Any main
  change = branch → PR → merge. Latest main commit: the
  `apporach`/§4.2 doc-polish fix (HEAD `9bb63a0` at last check).
- **`research-doppler-extraction`**: active branch, all current
  work. Does NOT merge to main until further notice. Commits so
  far (newest first):
  - `latest`   FINDINGS: entries 4, 5, 6 + PROJECT_STATE update
  - `5d6e109`  Fix: remove # method= comment header from CSV output
  - `2bdef0a`  PROJECT_STATE: update to reflect first positive result
  - `9bb398a`  Add --method autocorr (Gwyn G3ZIL lag-1 extractor)
  - `9eec751`  N5BRG dual-channel resolved; self-download closed
  - `f73279b`  N4RVE/N5BRG self-download is noise
  - `fd0fb9e`  first run on self-downloaded 17 May data + plotter fix
  - `c87d3cc`  branch scaffold (FINDINGS, plotter, methodology subsection)
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
I/Q? This is the WHOLE POINT.

**Current evidence — two pairs, same directional result:**

AC0G_ND / W7LUX (E-region contaminated, Gwyn Path 2):

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| 40–90 min   | 0.829 | 0.896      | +0.067 |
| 60–120 min  | 0.752 | 0.929      | +0.177 |
| Raw curve   | 0.576 | 0.705      | +0.129 |

N4RVE / N5BRG (NS channel S000038, Gwyn Path 1):

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| 40–90 min   | 0.772 | 0.823      | +0.051 |
| 60–120 min  | 0.740 | 0.894      | +0.154 |
| Raw curve   | 0.556 | 0.485      | −0.071 |

Both pairs: autocorr materially better in TID-period bands.
Shorter periods and full window slightly favour FFT — consistent
with autocorr's smoother output (3× lower block-to-block std).
Two pairs, same pattern. Consistent with Gwyn's hypothesis.
Not yet a conclusion: lag discrepancy and N5BRG channel unresolved.

**Falsifiable gate: PASSED.** Clean W7LUX: SNR delta 0.0 dB,
r=0.933 between methods. 3× smoother block-to-block with autocorr.

## 4. What is BLOCKING

Two open questions, both pending Gwyn's reply to 2026-05-18 email:

1. **AC0G_ND/W7LUX lag discrepancy** — our peak +22 min vs his
   +35 min. Stable across window widths. Does his extraction apply
   any phase unwrapping, carrier drift removal, or smoothing beyond
   lag-1 with no detrending? Most likely explanation for the gap.

2. **N5BRG antenna channel** — the data folder contains S000038
   (NS antenna). Our earlier work showed S000040 (EW antenna) is
   materially different. Which channel did Gwyn use? Affects
   like-for-like validity of N4RVE/N5BRG result.

Previously blocking, now resolved:
- ✓ Gwyn's data folder (identical to self-downloaded set)
- ✓ Autocorr parameters (60s, lag-1, no detrending)
- ✓ Stations/UTC window (both pairs, 18:00–20:00 UTC)
- ✓ Extractor implemented and gate passed
- ✓ `# method=` CSV comment bug fixed (v1.1.1)
- ✓ Geometry discrepancy — Gwyn uses midpoint-to-midpoint baselines;
  our tid_pair.py uses station-to-station. Lags unaffected; speeds
  differ ~8%. Do not compare speeds until reconciled.

Gwyn is `g3zil` on GitHub. Collaborator with WRITE access (main
protected). Accepted invite 2026-05-18.

## 5. The event & the data (reference)

Gwyn's event: **17 May 2024, ~19:00 UTC**, a large-scale TID.
Common transmitter = **WWV 10 MHz**. His method = two WWV-referenced
pairs + vector decomposition. His V1.2 slide (confirmed from image):
- Path 1 (N4RVE/N5BRG): 1360 km @ 126°, lag 27 min, 840 ±60 m/s
- Path 2 (AC0G_ND/W7LUX): 900 km @ 221°, lag 35 min, 429 ±60 m/s
- Combined: 979 ±80 m/s @ 157° ±6°; period ~58 min; wavelength ~3406 km
- His cross-correlation peaks: N4RVE/N5BRG ~0.6, AC0G_ND/W7LUX ~0.5

**Working data folder: `~/Downloads/gywn_tid_event_20240517/`**
Use this for all research work. Confirmed identical to self-download.

Station notes:
- `ac0g_nd/` 9-subchannel; **10 MHz = subchannel 4**. 42.0 dB. Good.
- `w7lux/` single-channel. 51.6 dB. Good. Used for gate check.
- `n4rve/` 9-subchannel; **10 MHz = subchannel 4**. 42.3 dB. Good.
- `n5brg/` S000038 (NS antenna), single channel, 10.000 MHz.
  Median SNR 26.4 dB at event time; drops to 17 dB at 18:45–19:00
  UTC. Marginal. Which channel Gwyn used is unconfirmed (ask 2 above).

**Hard data lesson:** always `drf_inspect` first → identify the
10 MHz subchannel → extract → check event-time (~19:00) SNR on
the plot → only then correlate.

## 6. What the investigation HONESTLY established

- **`--method autocorr` implemented** in `drf_to_doppler.py` v1.1.1
  per Gwyn's exact parameters. Clean-data gate passed. Committed.
- **Autocorr outperforms FFT in TID-period bands on both pairs.**
  AC0G_ND/W7LUX 60–120 min: r=0.929 vs 0.752 (+0.177).
  N4RVE/N5BRG 60–120 min: r=0.894 vs 0.740 (+0.154).
- **N4RVE/N5BRG lag matches Gwyn's 27 min exactly** (autocorr
  −27 min, FFT −29 min). Raw curve shape matches his slide.
- **AC0G_ND/W7LUX lag discrepancy:** our +22 min vs his +35 min.
  Stable across window widths. Not a physical disagreement (same
  broad peak, same direction) but unexplained. Awaiting Gwyn.
- **Autocorr 3× smoother** than FFT: block-to-block std 0.13 Hz
  vs 0.38 Hz on W7LUX.
- **Curve shapes reproduce Gwyn's slide** — same sinusoidal form,
  same trough near zero, peaks in the correct region.
- NOT established: that autocorr is generally superior. Two pairs
  on one event. FFT slightly better at shorter periods and full
  window. More data needed.
- NOT done: speed comparison (geometry unreconciled).
- NOT done: v1.5.0 diagnostics run on autocorr extractions.

## 7. Next steps (when Gwyn replies)

1. **Resolve lag discrepancy** — if he confirms no additional
   extraction steps, the +13 min difference is a genuine method
   difference worth characterising. If he reveals additional steps,
   implement and re-run.
2. **Confirm N5BRG channel** — re-run N4RVE/N5BRG with the correct
   channel if it differs from S000038.
3. **Run v1.5.0 diagnostics** (`tid_doa.py`) on autocorr
   extractions for both pairs.
4. **Write up formal finding** — two pairs, full table, honest
   caveats, including what autocorr does NOT improve.
5. **Production PR only if earned** — both pairs consistent,
   diagnostics clean, gate passed, written finding complete.

## 8. Other open / lower-priority threads

- METHODOLOGY.md clean-vs-contaminated figure: both halves now
  have data. Can be completed once lag discrepancy resolved.
- `xcorr_lag_plot.py` peak-lag vs `tid_pair.py` cross-check still
  outstanding (curve shape reliable; numbers provisional).
- Pre-existing minor items: v1.4.0 follow-up email; case-study
  refinement; alias-free repo cheatsheet.

## 9. Working discipline (why this project's results are trustworthy)

- Verify before acting. `drf_inspect` before extract; check
  event-time SNR before correlate; `git log -3` before any
  `reset --hard`.
- Do not overclaim. Two pairs ≠ a conclusion. Lag discrepancy
  unresolved ≠ results invalid. Smoother ≠ more accurate.
- Negative/blocked results recorded with equal weight.
- Nothing reaches `main` without earning a verified PR.
