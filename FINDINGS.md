# Research: Doppler extraction — FFT vs complex autocorrelation

**Status:** OPEN — investigation not started. No conclusion. No code
on this branch is verified or eligible for `main`.

**This branch does not merge to `main` until further notice.** Its
deliverable is knowledge: a documented finding, and *possibly* a
verified change if — and only if — the investigation earns one
through the gate below.

---

## The question

The toolkit extracts Doppler-vs-time from raw I/Q using an
FFT-based carrier track (`drf_to_doppler.py`, see
`docs/METHODOLOGY.md` Step 1). G3ZIL (Gwyn Griffiths), whose
independent analysis of a separate event (17 May 2024) is the first
external test of this toolkit, uses a **complex-autocorrelation**
approach instead, and observed that on a pair affected by E-region
propagation (AC0G_ND / W7LUX) the FFT-extracted Doppler produced
band-dependent, internally-inconsistent lags where his digital
analysis did not.

The question this branch exists to answer:

> On identical I/Q input, do FFT and complex-autocorrelation Doppler
> extraction agree on clean signal, and how does each behave on a
> known E-region-contaminated pair?

This is **not** "is FFT wrong." Nothing observed shows the inversion
math is wrong. The observed effect is upstream of the inversion, on
a pair with a known physical contamination, and it is consistent
with a limitation the toolkit *already documents*
(`docs/ASSESSING_RESULTS.md` §1 assumption 3, §7: single-hop
midpoint geometry; multi-hop not auto-detected).

## The gate (falsifiable, decided before any result)

A complex-autocorrelation extractor is only credible if it
**reproduces the FFT extractor on uncontaminated signal**. If the
two methods disagree on a clean pair, the new extractor is wrong —
that conclusion is not negotiable by "but it looks closer to Gwyn
on the bad pair." Clean-data agreement is this branch's equivalent
of the additive-only proof used for the v1.5.0 diagnostics: the
verification that makes any comparison trustworthy rather than just
two numbers.

Concretely, to graduate ANY extraction change to a `main` PR:

1. New extractor reproduces FFT lag on ≥1 clean pair within a
   stated, defensible tolerance. (FAIL ⇒ extractor is wrong; stop.)
2. Behaviour on the contaminated AC0G_ND/W7LUX pair characterised
   for BOTH methods, with the v1.5.0 diagnostics run on each.
3. A written finding stating what was learned, including the
   negative case ("FFT is adequate / autocorrelation not worth it"
   is a valid and publishable outcome).
4. Only then, if earned: a normal verified PR with the same bar as
   every prior substantive change.

## Open dependencies (blockers)

- [ ] **Gwyn's 17 May 2024 folder** — DRF dirs, CSVs, and any DOA
      config. Determines whether the gating run is multi-station
      DOA or pair-only. (User obtaining a copy.)
- [ ] **Gwyn's complex-autocorrelation parameters** — window
      length, lag range, detrending/preprocessing. The comparison
      is uninterpretable without matching his actual method, not
      *a* autocorrelation. (To request from Gwyn.)
- [ ] **Gwyn's exact stations / pairs / date-time window** — so the
      comparison is like-for-like, not toolkit-window-A vs
      Gwyn-window-B (the confound that caused the tid_pair
      confusion earlier).
- [ ] **Gating run** (blocked on folder): `tid_doa.py` v1.5.0
      diagnostics + run log on Gwyn's data. Result determines
      whether autocorrelation is "enhancement" or "urgent
      foundation issue" and what the comparison harness must show.

## Work log

(Empty. Entries appended as investigation proceeds. Each entry:
date, what was done, what was found, what it changed about the
plan. Negative results recorded with equal weight.)

### 2026-05-17 — First run on a self-downloaded copy of the 17 May 2024 event

**Inputs.** Self-downloaded PSWS DRF for AC0G_ND, W7LUX (also N4RVE,
N5BRG, not yet processed). NOT Gwyn's extracted folder — an
independent pull by callsign+date. Window 16:00–22:00 UTC (brackets
the ~19:00 event; Gwyn's exact analysis window still unconfirmed).

**Extraction issues found and resolved.**
- AC0G_ND is a 9-subchannel DRF. WWV 10 MHz is **subchannel 4**
  (confirmed via `drf_inspect`: index 4 = 10.000 MHz, ACTIVE,
  RMS 287 — strongest). Default extraction took subchannel 0
  (2.5 MHz, ~noise floor, 11.5 dB SNR) and produced a noise CSV
  that looked successful (exit 0, 8280 rows). Re-extracted with
  `--subchannel 4`: SNR 30–60 dB across the day incl. event window.
- W7LUX single-channel; correct as-is, 42.7 dB median SNR.
- Lesson: wrong-subchannel extraction is silent — only SNR/plot
  reveals it. Inspect subchannels + check event-time SNR before
  trusting a CSV.

**tid_pair.py band table (AC0G_ND vs W7LUX, 16–22 UTC):**

| Band | Toolkit lag / r | Gwyn (digital RF) |
|---|---|---|
| Full | +19.0 min / 0.380 | +18.5 min / 0.565 |
| 40–90 min | +20.0 min / 0.903 | +18.17 min / 0.918 |
| 60–120 min | +21.3 min / 0.526 | +12.33 min / 0.972 |
| 30–60 / 30–120 | +15.0 min / ~0.60 | — |

**Raw cross-correlation curve (xcorr_lag_plot.py):** peak r =
**0.162** at +18.8 min. Broad, low, quasi-sinusoidal; no isolated
dominant peak (comparable bump near −40 min). The broad/multi-peak
curve-shape failure described in METHODOLOGY.md "Interpreting the
correlation curve": lag not robustly determined; coefficient
(0.162, below 0.4) and shape agree — distrust this lag.

**Reading (honest bounds).**
1. Strong band (40–90 min): toolkit (+20.0 min, r 0.903) vs Gwyn
   (+18.17 min, r 0.918) — agree to ~2 min, near-identical r,
   across different extraction methods. Where data supports a
   confident lag, FFT and complex-autocorrelation converge.
2. Both analyses independently show band-inconsistent lags and a
   weak/broad raw correlation — the contamination signature. The
   toolkit reaches Gwyn's hand-derived diagnosis ("don't trust this
   pair", E-region) via its own diagnostics + curve shape. The
   "fails recognisably, not silently" property (ASSESSING_RESULTS
   §3.3) on a real, independent, expert-vetted event.
3. NOT yet an FFT-vs-autocorrelation conclusion. Gwyn's Image-2
   correlation peaked higher (~0.5–0.6, broad ~35 min); toolkit raw
   peak 0.162. Suggestive that complex autocorrelation pulled a
   more coherent signal from the contaminated pair — his hypothesis
   — but one pair, one event, different window, self-download not
   his folder. Motivates the investigation; not a result.

**Open / next.**
- [ ] Clean-pair contrast not done. N5BRG/N4RVE (Gwyn Path 1,
      cleaner) is the control — needs same subchannel-inspect +
      event-time-SNR verification (N4RVE also multi-subchannel).
- [ ] Geometry discrepancy: toolkit baseline 689 km @ 225° vs
      Gwyn's slide 900 km @ 221°. Lags geometry-independent and
      comparable; speeds NOT until midpoint/transmitter assumptions
      reconciled. Do not compare speeds yet.
- [ ] Pending Gwyn: his folder, complex-autocorrelation parameters
      (window, lag range, detrending), exact stations/pairs/window.
      Stays "toolkit independently shows same signature", not
      "reproduces Gwyn", until these.
- [ ] Plotter fix this session: timestamp_utc added to
      TIME_CANDIDATES. Otherwise still unverified — peak-lag vs
      tid_pair.py cross-check still outstanding.

### 2026-05-17 — N4RVE/N5BRG (Gwyn Path 1) on self-download: noise; clean control NOT obtainable

**Goal.** Clean-pair control (Gwyn treated N4RVE/N5BRG, Path 1, as
cleaner) to contrast vs contaminated AC0G_ND/W7LUX, for the
METHODOLOGY clean-vs-contaminated figure.

**Extraction.** N4RVE 9-subchannel; 10 MHz = subchannel 4 (same as
AC0G_ND). Extracted --subchannel 4: SNR 40.8 dB, clean through
event — N4RVE good. N5BRG single-channel but poor download:
full-day saturation bands; median SNR 18.8 dB (vs 40+ all others).
Event window 16-22 UTC: SNR median 21.3, 10.6% < 15 dB, 4.2%
saturated. N5BRG is the weakest station 2x over — opposite of a
clean control.

**tid_pair.py N4RVE/N5BRG 16-22 UTC:** corr 0.112/0.259/0.325/
0.734/0.136 (almost all sub-0.4). Lag SIGN FLIPS across bands
(Full +1550s N4RVE-first; 30-60/40-90/60-120 negative N5BRG-first).
Toolkit's own hint fired: "Sign flips between period bands indicate
the lag is dominated by noise, not a coherent wave." The lone 0.734
(60-120) is the documented bandpass artifact: var(y_f)=0.010,
filtering near-noise to a narrow band (METHODOLOGY "bandpass
problem").

**Raw xcorr curve:** peak r = -0.037 @ +27.7 min. Flat,
structureless, no peak — noise. Flatter/lower than even the
contaminated AC0G_ND/W7LUX curve.

**Reading (honest).**
1. DATA failure, not method/toolkit failure. N4RVE fine;
   self-downloaded N5BRG too poor (~21 dB, saturated) for any
   common wave. Says nothing about Gwyn's Path 1 or his method.
2. Toolkit behaved CORRECTLY: noise-dominated pair -> no confident
   answer, sub-threshold sign-flipping corr, own "noise" hint
   fired, flat curve. Third demo this session of "fails
   recognisably, not silently" (ASSESSING_RESULTS §3.3): synthetic,
   contaminated AC0G_ND/W7LUX, now noise pair. Pair is a bust; tool
   is not.
3. POSSIBLE WRONG N5BRG. Metadata anomalous vs others: uuid_str
   S000038, lat 33.396 lon -87.542, NO callsign, no KA9Q receiver
   name. The N5BRG pulled by callsign+date may not be Gwyn's N5BRG.
   Another reason self-download comparison to his numbers is unsafe.

**Conclusion: clean control NOT obtainable from self-download.**
Both Gwyn pairs via independent pull unusable: AC0G_ND/W7LUX
genuinely contaminated (matches him), N4RVE/N5BRG killed by N5BRG
download quality. Clean-vs-contaminated METHODOLOGY contrast does
not exist from this data. Any comparison to Gwyn's Path 1 / his
vector-sum overall (979 m/s @ 157°) / his method is BLOCKED on his
extracted folder — now demonstrated by two failed pairs, not
asserted.

**Open / next (reinforced).**
- [ ] Gwyn's folder now the demonstrated prerequisite. Two
      self-download pairs failed.
- [ ] Reply to Gwyn still the unblock: folder, autocorrelation
      params, exact stations/pairs/window, + clarify N5BRG identity
      (uuid S000038?).
- [ ] No speeds compared (geometry unreconciled; pairs are
      noise/contaminated regardless).
- [ ] METHODOLOGY clean-vs-contaminated figure: only contaminated
      half exists. Clean half blocked on Gwyn's data. Do NOT
      manufacture from weak data.

### 2026-05-17 — N5BRG re-investigated: dual-channel; self-download thread closed

PSWS shows N5BRG as a dual-channel Grape-1 installation, archived
as two separate observations, both 10 MHz / ~31 MB / 24 h:
- NS: S000038, station N5BRG-Grape1, instrument Grape1-01-Ch0-NS
  (the original "suspect" pull, FINDINGS entry 2).
- EW: S000040, station N5BRG-Grape1-MAG1, instrument
  Grape1-02-Ch1-EW (re-download).

Both have the same sparse metadata schema (uuid S0000xx, lat/lon
only, no callsign, no KA9Q_* receiver_name) - different from
W7LUX/N4RVE/AC0G_ND which carry full KA9Q/callsign metadata. The
earlier "possible wrong N5BRG" flag is resolved: it is the SAME
station, two antenna channels, not a wrong/different station. The
metadata-schema difference is a PSWS archiving difference, not a
station mismatch.

Extraction quality at the event (18-21 UTC), the only window that
matters:
- NS (S000038): median ~19 dB, heavy full-day saturation, noise at
  event time (pair result: sign-flipping, raw r = -0.037, entry 2).
- EW (S000040): better overall (30-45 dB much of the day) but
  decays to ~10-25 dB and is disturbed/spiky through 18-21 UTC;
  worst point ~7 dB near 21:00. Still NOT a clean event-time signal.

Finding. The two N5BRG antenna channels differ materially and
NEITHER provides a clean event-time signal from the self-download.
The N5BRG result is antenna-channel-dependent and both channels
fail in the 18-21 UTC window specifically. EW not run through
tid_pair.py - outcome (weak/uninterpretable) already determined
from the SNR/Doppler plot; a third low-confidence pair number would
add nothing.

Conclusion (reinforced, not changed). Clean-pair control remains
unobtainable from the self-download - now demonstrated three ways
(NS noise; EW weak-at-event; channel-dependence itself). Any
comparison to Gwyn's Path 1 / vector-sum overall (979 m/s @ 157) /
his method is blocked on BOTH (a) his actual extracted N5BRG data,
and (b) which antenna channel (NS S000038 vs EW S000040) he used -
they differ materially, so this is not a detail. Toolkit not
implicated anywhere in the N5BRG line: every failure is
data-quality / propagation at event time, and the toolkit correctly
refused a confident answer each time.

N5BRG self-download thread CLOSED. Do not pursue further N5BRG
variants without Gwyn's input. Productive next action is Gwyn's
reply with the full dataset he used (requested) and the NS-vs-EW
clarification, not more extraction.
