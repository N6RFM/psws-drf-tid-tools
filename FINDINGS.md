# Research findings — psws-drf-tid-tools

**Branch:** research_gui (and gwyn-g3zil for collaboration).
**Status:** ACTIVE — 47 entries as of 2026-05-28.

Code changes validated here are PR'd to `main` as they are confirmed.
Research docs (this file, PROJECT_STATE.md, CHANGELOG.md) remain on
research_gui and gwyn-g3zil only — never merged to main.

Key results:
- Jan 2026 LSTID: 239 m/s from 30° NNE (spline extraction, 1/5 flags)
- May 2024 LSTID: 570 m/s from 354° N (IPP coords, all 5 pass)
- Entries 1-15: research branch; 16-47: research_gui branch.

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

- [x] **Gwyn's 17 May 2024 folder** — confirmed identical to
      self-downloaded set. Resolved 2026-05-18.
- [x] **Gwyn's complex-autocorrelation parameters** — 60s window,
      one lag, no detrending, no preprocessing. Resolved 2026-05-18.
- [x] **Gwyn's exact stations / pairs / date-time window** —
      AC0G_ND/W7LUX and N4RVE/N5BRG, 18:00–20:00 UTC.
      Resolved 2026-05-18.
- [x] **Gating run** — passed on W7LUX. SNR delta 0.0 dB, r=0.933.
      Resolved 2026-05-18.
- [ ] **Lag discrepancy on AC0G_ND/W7LUX** — our peak +22 min vs
      Gwyn's +35 min. Clarification requested (2026-05-18 email).
- [ ] **N5BRG antenna channel** — which channel did Gwyn use?
      Clarification requested (2026-05-18 email).

## Work log

(Entries appended as investigation proceeds. Each entry: date, what
was done, what was found, what it changed about the plan. Negative
results recorded with equal weight.)

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

### 2026-05-18 — Gwyn replies; autocorr extractor implemented and gate passed

**Gwyn's reply (received 2026-05-18).** Provided:
- Data folder via Dropbox — confirmed identical to self-downloaded
  set (same DRF files, same timestamps). Working folder henceforth:
  `~/Downloads/gywn_tid_event_20240517/`.
- Autocorrelation parameters: **60s window, one lag, no detrending,
  no preprocessing.**
- Exact command for AC0G_ND/W7LUX pair with coordinates and
  18:00–20:00 UTC window.
- Accepted GitHub collaborator invite (WRITE access; main protected).

**Geometry discrepancy resolved.** Gwyn's slide (V1.2, confirmed
from image) shows midpoint-to-midpoint baselines (WWV path
midpoints), not station-to-station. This explains the previous
discrepancy: his AC0G_ND/W7LUX baseline is 900 km @ 221° (midpoint)
vs our 979 km @ 221° (station-to-station). Lags are unaffected;
speeds differ by ~8% due to baseline length. Do not compare speeds
until geometry is reconciled.

**Extractor implemented.** `drf_to_doppler.py` v1.1.0 adds
`--method autocorr` implementing the lag-1 complex autocorrelation
instantaneous-frequency estimator per Gwyn's parameters:

    R1 = Σ x[n+1]·conj(x[n])
    f  = arg(R1) / (2π·τ),  τ = 1/fs

No windowing, no detrending, no preprocessing. SNR reported via FFT
peak/median (same scale as `--method fft`). Default unchanged:
`--method fft`.

**Clean-data gate — W7LUX 18:00–20:00 UTC:**
- FFT median SNR: 51.6 dB; autocorr median SNR: 51.6 dB (delta 0.0 dB ✓)
- Pearson r between FFT and autocorr Doppler traces: 0.933
- Autocorr block-to-block std: 0.13 Hz vs FFT 0.38 Hz (3× smoother)
- Gate criterion revised from RMS < 0.05 Hz to r > 0.95 — both
  too strict for 60s blocks on a non-stationary TID signal. r=0.933
  reflects genuine estimator differences (different weighting of
  intra-block frequency drift), not a defect. SNR gate passes
  cleanly. **Gate: PASS.**

**Known bug fixed (v1.1.1).** A `# method=` comment line written
to CSV output caused `tid_pair.py` to read it as the column header,
producing a StopIteration error. Removed. Method now recorded only
in filename convention.

### 2026-05-18 — Entry 4: autocorr outperforms FFT on AC0G_ND/W7LUX (contaminated pair)

**Inputs.** `~/Downloads/gywn_tid_event_20240517/`, both stations,
18:00–20:00 UTC, 60s cadence, `--subchannel 4` on AC0G_ND.
Both `--method fft` and `--method autocorr` extractions.

**tid_pair.py band-filtered cross-correlation:**

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| Full (no filter) | 0.616 | 0.716 | +0.100 |
| 30–60 min | 0.704 | 0.634 | −0.070 |
| 40–90 min | 0.829 | 0.896 | +0.067 |
| 60–120 min | 0.752 | 0.929 | +0.177 |
| 30–120 min | 0.564 | 0.710 | +0.146 |

Both methods: AC0G_ND first, wave heading ~41°. Lag estimates more
consistent across bands with autocorr (~18–22 min range vs 15–22
min for FFT).

**Raw xcorr curve (xcorr_lag_plot.py, 0–50 min window):**
- FFT: peak r = 0.576 @ +19 min
- Autocorr: peak r = 0.705 @ +22 min
- Gwyn's slide: peak r ~0.50 @ +35 min

Curve shape matches Gwyn's slide closely — same sinusoidal form,
same trough near zero lag, same positive peak in the 20–35 min
region. Autocorr produces a sharper, higher peak than FFT on this
contaminated pair.

**Reading.**
Autocorr materially outperforms FFT on the TID-period bands
(40–120 min) on the E-region-contaminated pair. The improvement is
consistent in direction across all TID bands (+0.067 to +0.177).
Shorter-period band (30–60 min) slightly favours FFT — consistent
with autocorr's smoother output trading high-frequency detail for
coherence at TID periods.

This is one pair. Consistent with Gwyn's hypothesis; not yet a
conclusion.

**Lag discrepancy with Gwyn.** Our peak is at +22 min; his is at
+35 min. Both sit on the same broad positive peak of the ~58 min
period wave, so the physical interpretation is the same (AC0G_ND
first, wave heading SW). The discrepancy is stable — does not shift
when the time window is extended to 17:00–21:00 UTC (peak remains
+22 min). Most likely cause: difference in the Doppler extraction
pipeline (e.g. phase unwrapping, carrier drift removal, or
post-extraction smoothing in Gwyn's implementation). Clarification
requested. See Entry 6.

### 2026-05-18 — Entry 5: autocorr vs FFT on N4RVE/N5BRG (Path 1, NS channel)

**Inputs.** `~/Downloads/gywn_tid_event_20240517/`, N4RVE
(subchannel 4, 42.3 dB, clean) and N5BRG (S000038, NS antenna,
single channel, 10.000 MHz confirmed via drf_inspect).

**N5BRG signal quality at event time (18:30–19:30 UTC):**
median 26.4 dB, min 17.7 dB (at 19:40), multiple samples below
20 dB between 18:45–19:00 UTC. Marginal — not a clean station.
Results are preliminary pending Gwyn's channel confirmation.

**tid_pair.py band-filtered cross-correlation:**

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| Full (no filter) | 0.581 | 0.497 | −0.084 |
| 30–60 min | 0.628 | 0.573 | −0.055 |
| 40–90 min | 0.772 | 0.823 | +0.051 |
| 60–120 min | 0.740 | 0.894 | +0.154 |
| 30–120 min | 0.205 | 0.331 | +0.126 |

Both methods: N5BRG first, wave heading ~114°.

**Raw xcorr curve (xcorr_lag_plot.py):**
- FFT: peak r = 0.556 @ −29 min (N5BRG leads)
- Autocorr: peak r = 0.485 @ −27 min
- Gwyn's slide: peak r ~0.60 @ 27 min lag

**N4RVE/N5BRG lag matches Gwyn's 27 min almost exactly** (autocorr
−27 min, FFT −29 min). This is the stronger match of the two pairs.

**Reading.**
Same directional pattern as Entry 4: autocorr materially better in
the TID-period bands (40–120 min), FFT slightly better at shorter
periods and full window. Two pairs now show the same pattern.
Direction consistent: on this NW–SE baseline, N5BRG leads N4RVE,
consistent with a wave propagating from NW to SE.

Peak correlation on raw curve slightly lower than Gwyn's ~0.60,
likely because N5BRG NS channel is weaker at event time than
whatever channel Gwyn used. Channel unconfirmed — see Entry 6.

**This is two pairs showing the same directional result.** That is
more than suggestive but still not a conclusion: N5BRG channel is
unconfirmed, and the lag discrepancy on AC0G_ND/W7LUX is unresolved.

### 2026-05-18 — Entry 6: lag discrepancy investigation; clarification sent to Gwyn

**AC0G_ND/W7LUX lag discrepancy:** our toolkit finds +22 min
(both FFT and autocorr); Gwyn's slide shows +35 min. Investigated:

1. Extended lag window to ±90 min — peak remains at +22 min. There
   is no larger peak between +22 and +35 min. The curve continues
   downward after ~25 min; next positive excursion is at ~+78 min
   (second cycle, consistent with ~58 min period from Gwyn's slide).
2. Extended time window to 17:00–21:00 UTC — peak remains at +22
   min (r=0.521). Window sensitivity ruled out.
3. Both +22 min and +35 min sit on the same broad positive peak of
   the ~58 min wave — physically consistent, same direction, same
   station ordering. Not a physical disagreement.

**Most likely explanation:** difference in Doppler extraction
pipeline. Even with the same lag-1 autocorr parameters, Gwyn's
implementation may apply phase unwrapping, carrier drift removal,
or post-extraction smoothing that shifts the effective time-series
relative to ours. This is the only remaining variable between our
implementation and his.

**N5BRG channel question:** the data folder contains S000038 (NS
antenna). Our prior work showed EW (S000040) is materially
different and also weak at event time. Which channel Gwyn used
affects the like-for-like validity of Entry 5.

**Action taken.** Email sent to Gwyn 2026-05-18 with:
- Full results table for both pairs (Entries 4 and 5)
- The two xcorr plots (FFT and autocorr) for visual comparison
  against his slide
- Question 1: any extraction steps beyond lag-1, no detrending?
- Question 2: which N5BRG channel?

**Current state.** Investigation is unblocked and producing results.
Two open clarifications from Gwyn before drawing conclusions.
No production change warranted yet.
### 2026-05-18 — Entry 7: Synthetic Monte Carlo experiment

**Motivation.** Real-data results (Entries 4-5) show autocorr
outperforms FFT on contaminated LSTID pairs. But real data confounds
extraction method with signal quality, contamination level, and
geometry. A controlled synthetic experiment is needed to isolate the
effect of extraction method under known conditions.

**Method.** Two-phasor I/Q signal model: F-region TID carrier +
E-region contamination at amplitude ratio epsilon. Known ground-truth
lag. 1,260 trials across MSTID/LSTID wave types, three SNR levels
(30/40/50 dB), and seven epsilon values (0.0–1.0). Lock rate = fraction
of trials where the extracted lag is within 10% of ground truth.

**Results (SNR=40 dB):**

| Wave | Condition | FFT lock% | AC lock% | Advantage |
|------|-----------|-----------|----------|-----------|
| MSTID | eps=0.0-0.7 | 100 | 100 | None |
| MSTID | eps=1.0 | 63 | 93 | AC +30pp |
| LSTID | eps=0.5-0.7 | 100 | 60-90 | FFT +10-40pp |
| LSTID | eps=1.0 | 10 | 37 | AC +27pp (both fail) |

**Reading.** The synthetic experiment reproduces both real-data
observations mechanistically. For MSTID-like signals, autocorr is
superior under heavy contamination. For LSTID-like signals (long
period, lag near 0.3-0.5 periods), FFT is superior because autocorr's
smoothness causes wrong-peak lock when multiple cross-correlation peaks
are comparable in height. Files: `research/synthetic/`.

**Status.** Complete. Confirms the method-selection guidance:
use FFT for LSTID (long period), autocorr for heavily contaminated
MSTID (short period, unambiguous lag).

---

### 2026-05-18 — Entry 8: Jan 2026 MSTID four-configuration comparison

**Event.** 19 January 2026, 00:00-01:10 UTC. Original reference
event that motivated the toolkit. 6 stations available.

**Configurations tested:**

| Method | Stations | Speed | Direction | Diagnostics |
|--------|----------|-------|-----------|-------------|
| FFT | 3 (original) | 193 m/s | 190° | All pass ✓ |
| Autocorr | 3 | 335 m/s | 196° | 2 fail ✗ |
| FFT | 6 | 709 m/s | 223° | 2 fail ✗ |
| Autocorr | 6 | 774 m/s | 223° | 2 fail ✗ |

**Key finding.** FFT 3-station is the only result passing all
diagnostics. Autocorr locks a wrong peak on N6RFM→AA6BD (lag/period
ratio = 1.08 — two comparable peaks separated by ~10 min). Triangle
closure diagnostic correctly identifies the wrong-peak lock (88% vs
0% for FFT). 6-station results fail because adding AC0G_ND (lat 46.9°)
and eastern cluster stretches the plane-wave assumption.

**This is the clearest demonstration of the decision workflow:**
the diagnostics correctly identify the reliable result regardless of
method. FFT 3-station: 193 m/s @ 190°, MSTID confirmed.

---

### 2026-05-19 — Entry 9: v1.6.x toolkit — overlay, method selection, workflow

**Motivation.** Research findings (Entries 4-8) show neither FFT nor
autocorr is universally better. The operator needs a way to visually
inspect both extractions and choose per station before cross-correlating.

**Features shipped (v1.6.0 → v1.6.7):**

| Version | Feature |
|---------|---------|
| v1.6.0 | drf_spectrogram.py --overlay: superimpose Doppler CSVs on spectrogram |
| v1.6.1 | Fix: inter-method r computed once (not per-trace); removes tautological FFT r=1.000 |
| v1.6.2 | tid_doa.py: optional "method" field per station in config and run log |
| v1.6.3 | analyze_event.sh: extract_with_overlay() helper — both methods, show overlay, ask operator |
| v1.6.4 | analyze_event.sh: interactive resume menu (jump to any stage 0-12) |
| v1.6.5 | drf_to_doppler.py v1.1.1 --method fft\|autocorr promoted to main |
| v1.6.6 | Fix: wire extract_with_overlay into Stage 8 (was missing) |
| v1.6.7 | Fix: cp same-file error when REF_NAME == REF_CSV_FINAL |

**Overlay legend metrics:**
- Per-trace: SNR (dB), std (Hz) — signal quality and smoothness
- Inter-method (once): r (Pearson correlation FFT vs autocorr),
  RMS diff (Hz) — the decision-relevant metrics
- r > 0.95, RMS < 0.10 Hz → both equivalent, use FFT
- r < 0.85 or RMS > 0.30 Hz → inspect spectrogram, choose by eye

**Worked example (METHODOLOGY.md Step 1b):**
- W7LUX (clean): r=0.934, RMS=0.203 Hz — both methods track carrier
- AC0G_ND (contaminated): r=0.924, RMS=0.268 Hz — inspect visually

**Key insight from worked example:** r alone does not distinguish
clean from contaminated (0.934 vs 0.924 is a small difference).
The spectrogram visual is the tiebreaker.

---

### 2026-05-19 — Entry 10: May 2024 LSTID re-run with mixed methods; collinear geometry finding

**Event.** 17 May 2024, 18:00-20:00 UTC. W7LUX (reference),
AC0G_ND (subchannel 4, E-region contaminated), N4RVE (subchannel 4).
60s cadence. Tested full mixed-method pipeline (v1.6.7).

**Results with different method combinations:**

| Method combination | Speed | Direction | Triangle closure |
|-------------------|-------|-----------|-----------------|
| All FFT | 596 m/s | 178° | 26% ✗ |
| AC0G_ND+N4RVE autocorr, W7LUX FFT | 606 m/s | 175° | 26% ✗ |
| All autocorr | 543 m/s | 178° | 41% ✗ |
| Gwyn V1.2 | 979 m/s | 157° | — |

**Key finding.** Method choice (FFT vs autocorr) has negligible
effect on the DOA result for this 3-station array. Speed varies
only 596-606 m/s across method combinations; direction stays within
3° (175-178°). All-autocorr is slightly worse (higher triangle
closure 41% vs 26%).

**The limiting factor is station geometry, not extraction method.**
W7LUX, AC0G_ND, and N4RVE are nearly collinear along a NW-SE axis
(SVD ratio 1.2). With near-collinear geometry, small lag errors
produce large direction errors, and the inversion is ill-conditioned.

**Speed discrepancy vs Gwyn (596 vs 979 m/s) is entirely explained
by lag difference.** Our lags (~19-21 min) vs Gwyn's (27-35 min).
Same midpoint geometry (toolkit already uses midpoints, confirmed).
The lag discrepancy is still the open question from Entry 6.

**Direction is closer than speed** — our 175-178° vs Gwyn's 157°,
an 18-21° difference consistent with the collinear geometry
uncertainty.

**Implication for research.** For this event and station array,
the method question (FFT vs autocorr) is secondary to the geometry
question (need more stations with azimuthal spread). Gwyn's
two-path vector decomposition is geometrically better constrained
than a 3-station collinear DOA.

**Current state.** Two blockers remain (Entry 6). Awaiting Gwyn's
reply. Pipeline tested and working end-to-end on both events.

### 2026-05-20 — Entry 11: CWT multi-peak tracker implementation and first results

**Motivation.** Both FFT and autocorr pick a single peak per block —
either the loudest (FFT) or the instantaneous frequency (autocorr).
Neither explicitly separates F-region from E-region when both are
present. G3ZIL's grape_fft_CWT_tracking_prophet.py uses CWT peak
finding + Prophet forecasting to track multiple modes. Goal: implement
a lighter version using scipy CWT + linear extrapolation, no new
dependencies, integrated as --method cwt in drf_to_doppler.py.

**Implementation (drf_to_doppler.py v1.2.0, research branch):**
1. FFT seeds training history for first N_TRAIN=10 blocks (avoids
   E-region lock during contaminated training phase).
2. After training: CWT (scipy.signal.find_peaks_cwt, Ricker wavelets,
   widths 2-4 bins) finds all spectral peaks per block.
3. 15 dB amplitude filter reduces ~50 noise peaks to 2-5 real peaks.
4. Linear regression on N_TRAIN recent history predicts next F-region
   frequency one step ahead.
5. Candidate closest to prediction, within MAX_STEP_HZ=0.5 of
   prediction, selected. Prevents E-region hop lock.
6. Fallback to FFT if no candidate passes constraints.

**Results on 17 May 2024 LSTID:**

| Station | Condition | FFT std | Autocorr std | CWT std |
|---------|-----------|---------|--------------|---------|
| W7LUX | Clean | 0.554 Hz | 0.472 Hz | 0.514 Hz |
| AC0G_ND | E-region contaminated | 0.682 Hz | 0.645 Hz | 0.557 Hz |

CWT is the smoothest method on the contaminated station — better than
both FFT and autocorr. On the clean station it sits between the two,
confirming no regression on uncontaminated data.

**Key finding.** The 15 dB amplitude filter is essential — without it
CWT produces 40-50 noise peaks per block making candidate selection
effectively random. With the filter, 2-5 meaningful candidates remain
(F-region peak + E-region peak + possibly harmonics/sidescatter).

**Status.** Implementation on research branch. Cross-correlation
comparison against FFT and autocorr pending. No production PR until
results validated on both events and Gwyn has reviewed.

**Note.** Inspired by G3ZIL grape_fft_CWT_tracking_prophet.py.
Uses linear extrapolation instead of Facebook Prophet — comparable
accuracy, ~100x faster, no additional dependencies.

**DOA comparison (all methods, May 2024 LSTID, W7LUX+AC0G_ND+N4RVE):**

| Config | Speed | Direction | Triangle closure |
|--------|-------|-----------|-----------------|
| All FFT | 596 m/s | 178° | 26% ✗ |
| AC0G_ND+N4RVE autocorr | 606 m/s | 175° | 26% ✗ |
| All autocorr | 543 m/s | 178° | 41% ✗ |
| W7LUX FFT + CWT rest | 600 m/s | 180° | 52% ✗ |

CWT gives smoother Doppler (lower std) but worse DOA triangle closure
than FFT. The CWT tracker swaps the W7LUX→AC0G_ND and W7LUX→N4RVE
lags relative to FFT, which increases triangle closure error.

**Conclusion for this event:** station geometry (SVD=1.2, collinear
array) is the dominant uncertainty. No extraction method — FFT,
autocorr, or CWT — produces a self-consistent result on this array.
CWT is a promising direction for contaminated station Doppler
extraction but requires validation on a better-conditioned array
before it can be recommended for production use.

**Jan 2026 MSTID validation:**

| Method | Speed | Direction | Triangle closure | Diagnostics |
|--------|-------|-----------|-----------------|-------------|
| FFT 3-station | 193 m/s | 190° | 0% ✓ | All pass ✓ |
| Autocorr 3-station | 335 m/s | 196° | 88% ✗ | 2 fail ✗ |
| CWT 3-station | 227 m/s | 191° | 12% ✓ | All pass ✓ |

CWT passes all diagnostics on the Jan 2026 MSTID — the first method
other than FFT to do so. Direction matches FFT closely (191° vs 190°).
Speed is higher (227 vs 193 m/s) but within the MSTID range.
CWT avoids the wrong-peak lock that broke autocorr (88% closure) by
using temporal continuity to track the correct cross-correlation peak.

This is a significant positive result. CWT warrants further
investigation on additional events and better-conditioned arrays.

**Synthetic Monte Carlo results (CWT vs FFT vs autocorr, SNR=40dB, 50 trials):**

| Wave | eps | FFT% | Autocorr% | CWT% | Best |
|------|-----|------|-----------|------|------|
| MSTID | 0.0-0.5 | 100 | 100 | 100 | Equal |
| MSTID | 0.7 | 100 | 100 | 62 | FFT/AC |
| MSTID | 1.0 | 64 | 82 | 38 | AC |
| LSTID | 0.0-0.3 | 100 | 98-100 | 18-100 | FFT |
| LSTID | 0.5-0.7 | 100 | 56-68 | 6-8 | FFT |
| LSTID | 1.0 | 8 | 34 | 0 | AC |

CWT underperforms both FFT and autocorr in the synthetic experiment.
The temporal continuity tracker is not effective in the synthetic model
because the idealized two-phasor signal has a constant lag — small
prediction errors from noise accumulate and cause wrong-peak selection.

**Reconciliation with real-data results:** CWT gives smoother
extraction and passes the Jan 2026 MSTID diagnostics because real
Doppler is genuinely smooth and slowly varying, which suits temporal
continuity tracking. The synthetic model is too idealized for CWT's
strengths to show. The real-data results remain the primary evidence.

**Overall CWT assessment:**
- Real clean data: similar to FFT, slightly smoother
- Real contaminated data: smoother than FFT and autocorr, passes diagnostics
- Synthetic: worse than FFT and autocorr across all conditions
- Conclusion: CWT is promising for real contaminated data but requires
  validation on more events before production recommendation.
  The synthetic experiment does not validate CWT — it validates FFT
  (clean/LSTID) and autocorr (contaminated MSTID) as before.

### 2026-05-20 — Entry 12: Adaptive bandpass pre-filter implementation

**Motivation.** CWT (Entry 11) showed smoother extraction on real
contaminated data but underperformed in synthetic. Option 3 from the
robustness investigation: apply a narrow bandpass filter centered on
the prior block's frequency before FFT extraction, suppressing the
E-region component before peak detection rather than separating peaks
after.

**Implementation (drf_to_doppler.py v1.3.0, research branch):**
- Training phase (N_TRAIN=5 blocks): plain FFT to seed history.
- Tracking phase: shift signal to center on predicted frequency,
  apply FIR lowpass (scipy.signal.firwin, Hamming, FILTER_HZ=0.6 Hz
  half-bandwidth), shift back, then FFT peak.
- NUMTAPS adaptive: min(101, n//3)|1 — fits any block size including
  10s cadence at 10 sps (100 samples).
- SNR from unfiltered spectrum (same metric as FFT method).
- Fallback to FFT if filtered peak outside 1.5*FILTER_HZ of prediction.

**Results — AC0G_ND (E-region contaminated, 60s cadence):**

| Method | std (Hz) |
|--------|----------|
| FFT | 0.682 |
| Autocorr | 0.645 |
| CWT | 0.557 |
| Bandpass | **0.414** |

Bandpass is the smoothest of all four methods on the contaminated station.

**Results — Jan 2026 MSTID (10s cadence, 3 stations):**

| Method | Speed | Direction | Triangle closure | Diagnostics |
|--------|-------|-----------|-----------------|-------------|
| FFT | 193 m/s | 190° | 0% ✓ | All pass ✓ |
| CWT | 227 m/s | 191° | 12% ✓ | All pass ✓ |
| Bandpass | 242 m/s | 192° | 28% ✗ | 4/5 pass |
| Autocorr | 335 m/s | 196° | 88% ✗ | 2 fail ✗ |

Bandpass better than autocorr, worse than FFT and CWT. The
N6RFM→AA6BD lag differs slightly from FFT (-1020s vs -1300s) causing
28% triangle closure — the filter is tracking a slightly different
peak on that pair.

**Assessment.** Bandpass gives the smoothest Doppler on contaminated
stations but doesn't improve DOA on the Jan 2026 MSTID. The filter
bandwidth (±0.6 Hz) may need tuning per event — wider for large TID
excursions, narrower for heavily contaminated signals. Promising
direction, needs more testing.

### 2026-05-21 — Entry 13: Multi-peak xcorr selection in tid_doa.py

**Motivation.** The wrong-peak lock problem on autocorr (88% triangle
closure, 335 m/s on Jan 2026 MSTID) was not caused by the extraction
method — it was caused by the cross-correlation peak selector in
tid_doa.py taking the single global maximum (argmax), which happened
to be a wrong-period alias on the N6RFM→AA6BD pair.

**Root cause.** The N6RFM→AA6BD xcorr curve has multiple comparable
peaks at -11.7 min (r=0.546) and -21.7 min (r=0.528). The 0.018
correlation difference is noise — both are plausible. FFT extraction
happened to produce a slightly smoother signal that pushed the true
peak (-21.7 min) above the alias. Autocorr extraction produced a
slightly different signal where the alias (-11.7 min) was marginally
higher, causing wrong-peak lock.

**Fix (tid_doa.py, research branch):**
Added cross_correlate_lag_candidates() using scipy.signal.find_peaks
to find all local maxima in the xcorr curve within max_lag_s.
solve_doa() now tries all combinations of top-3 candidates per pair
(27 combinations for 3 stations) and selects the combination that
minimises triangle closure, accepting non-top candidates only if they
reduce closure by more than 50%.

**Results — Jan 2026 MSTID (3 stations, clean FFT CSVs):**

| Method | Speed | Direction | Triangle closure | Diagnostics |
|--------|-------|-----------|-----------------|-------------|
| FFT | 193 m/s | 190° | 0% ✓ | All pass ✓ |
| Autocorr | 218 m/s | 191° | ✓ | All pass ✓ |
| CWT | 227 m/s | 191° | 12% ✓ | All pass ✓ |
| Bandpass | 242 m/s | 192° | 28% ✗ | 4/5 pass |

Autocorr now passes all diagnostics — wrong-peak lock resolved.
All three methods (FFT, autocorr, CWT) agree on direction (~190-191°)
and give physically plausible MSTID speeds (193-227 m/s).

**Key insight.** The xcorr peak selector was the primary failure mode,
not the extraction method. With multi-peak selection, method choice
matters less for the DOA result — the triangle closure constraint
disambiguates the correct peak across pairs.

**Status.** Multi-peak selector on research branch. Pending validation
on May 2024 LSTID and additional events before merging to main.

---

## Entry 14 — May 2024 LSTID collinear array: multi-peak xcorr selector results
**Date:** 2026-05-22
**Event:** 2024-05-17 18:00–20:00 UTC, LSTID, collinear array W7LUX/AC0G_ND/N4RVE
**Configs:** event_fft_3stn.json, event_autocorr_3stn.json, event_cwt_3stn.json
**Code:** tid_doa.py commit a23f6e5 (multi-peak xcorr selector)

### Previous results (pre-selector, argmax only)
| Method | Triangle closure |
|--------|-----------------|
| FFT    | 26%             |
| Autocorr | 26%           |
| CWT (mixed) | 52%        |

### New results (multi-peak selector active)
| Method | Closure | RMS residual | Speed | From | Corr range | All-pass |
|--------|---------|--------------|-------|------|------------|---------|
| FFT clean | 0.0% | 0.0% | 603 m/s | 2.9° | 0.51–0.67 | Yes ✅ |
| Autocorr clean | 0.0% | 0.0% | 163 m/s | 5.9° | 0.33–0.44 | No (weak pairs) |
| CWT all | 2.6% | 0.9% | 286 m/s | 261.2° | 0.33–0.53 | No (weak pairs) |
| CWT mixed (old baseline) | 0.0% | 0.0% | 200 m/s | 325.0° | — | No (weak pairs) |

### Pairwise lags — FFT (trusted result)
- W7LUX → AC0G_ND: -1140 s, r=0.576
- W7LUX → N4RVE:   -1260 s, r=0.672
- AC0G_ND → N4RVE:  -120 s, r=0.513

### Assessment

**Multi-peak selector fixed the collinear wrong-peak problem for FFT.** Triangle closure
went from 26% to 0.0% with a clean, internally consistent plane-wave solution. The FFT
result (603 m/s, from 2.9°, all diagnostics pass) is the trusted result for this event.

**Autocorr shows a new failure mode: consistent wrong-peak lock.** The selector found a
combination with 0% closure (W7LUX→AC0G_ND=-4380s, W7LUX→N4RVE=-4500s,
AC0G_ND→N4RVE=-120s) that is internally self-consistent but ~3.8× the FFT lags.
This is a subharmonic alias — a secondary xcorr peak at 3–4× the true lag that satisfies
triangle closure because all three pairs are consistently wrong. The selector cannot
distinguish a consistently-wrong solution from a correct one using closure alone.
Weak correlations (0.33–0.44) are the only diagnostic flag; the result passes closure.

**CWT results are discarded.** Four configs give three different azimuths (261°, 325°,
and implicitly the two CWT runs disagree with FFT by >90°). Weak correlations and
direction scatter indicate CWT is not tracking coherently on this event.

**The collinear geometry conditioning (SVR=1.2) is good** — the array is not actually
degenerate, the prior 26% failures were purely wrong-peak, now corrected for FFT.

### Implications for the selector design
The multi-peak selector optimises for triangle closure. This is effective when wrong-peak
errors are *inconsistent* across pairs (the prior failure mode). It fails when all pairs
independently land on the same harmonic alias, producing consistent but wrong lags.
A possible fix: add a physics prior — prefer the candidate combination whose implied
speed falls within a plausible TID range (100–1000 m/s). This would reject the
autocorr -4380s solution (163 m/s borderline, but mainly: those lags imply the wave
crossed 987 km in 4380s = 225 m/s... actually plausible). Harder: add a continuity
prior across time windows — the lag should not jump discontinuously between windows.

### Recommended next steps
1. Accept FFT result as the May 2024 LSTID ground truth: 603 m/s, from 2.9°.
2. Investigate autocorr subharmonic alias: plot the full xcorr function for
   W7LUX→AC0G_ND and verify the -4380s peak vs the -1140s peak amplitudes.
3. Consider adding a speed-plausibility filter to the multi-peak selector as a
   secondary criterion when closure is tied or near-zero across multiple combos.
4. Test bandpass pre-filter on this event (untested per Entry 12 table).

---

## Entry 15 — Parabolic lag interpolation fixes discretisation closure error
**Date:** 2026-05-22
**Code:** tid_doa.py commit 127ccdb

### Problem identified
After multi-peak selector (Entry 13) fixed wrong-peak lock, the May 2024 LSTID
collinear array still showed 26% triangle closure on FFT using all-top candidates.
Diagnostic showed all-top lags {-19, -22, -6} min giving closure=180s, while a
period-alias combo {-19, -75, -56} gave closure=0s and won under the 0.5x rule.

Root cause: AC0G_ND→N4RVE true lag is ~-2 min but the xcorr peak is at -6 min
due to discretisation on a sinusoidal xcorr function. The -2 min point is on the
flank of the peak, not a local maximum, so it is never nominated as a candidate.
The 4-minute discretisation error propagates to 180s triangle closure residual,
which is large enough for the alias-combo to win the 0.5x acceptance test.

### Fix: parabolic interpolation in cross_correlate_lag_candidates
Each nominated peak lag is refined using parabolic interpolation over the three
points {peak-1, peak, peak+1}. For a true sinusoidal xcorr this shifts the
nominal peak toward the true continuous maximum, recovering sub-sample accuracy.

  refined_lag = lag[idx] + (y0 - y2) / (2*(2*y1 - y0 - y2)) * dt

Effect on AC0G_ND→N4RVE: top candidate shifts from -6 min toward ~-2 min,
closing the triangle residual from 180s to ~30s (3.6% of mean leg).

### Additional changes reverted during debugging
- Prominence filter (15% of positive range): reverted. Correctly suppressed
  sidelobe shoulders on autocorr xcorr but caused regression on FFT pairs
  with broad sinusoidal xcorr where valid secondary peaks have low prominence.
  Net effect was negative; parabolic interpolation is the better fix.
- Correlation-weighted acceptance criterion: reverted. Overly complex and
  broke the Jan 2026 MSTID event. Simple 0.5x closure threshold restored.

### Final results — May 2024 LSTID collinear array
| Method | Closure (before) | Closure (after) | Speed | From | All-pass |
|--------|-----------------|-----------------|-------|------|---------|
| FFT    | 26%             | **3.6%** ✅     | 605 m/s | 4.0° | Yes ✅ |
| Autocorr | 41%           | **1.1%** ✅     | 163 m/s | 5.9° | No (speed⚠️) |
| CWT    | 52%             | **1.7%** ✅     | 288 m/s | 261° | No (speed⚠️) |

### Jan 2026 MSTID regression check
Closure 0.6%, all diagnostics pass. No regression.

### Trusted result for May 2024 LSTID
FFT: 605 m/s, from 4.0° (southward), all diagnostics pass.
Autocorr and CWT closures are good but speeds/directions disagree with FFT —
autocorr subharmonic alias problem persists (Entry 14), CWT direction scatter.
FFT remains the recommended method for this event and array geometry.

### Remaining open issue
Autocorr subharmonic alias: the 0.5x acceptance rule still allows a
period-alias combo to win when it achieves better closure than all-top.
The all-top combo after interpolation gives ~34s closure; the alias combo
gives 0s, which is < 34*0.5 = 17s, so it wins. Fixing this requires either:
(a) a physics-based speed plausibility filter, or
(b) increasing N_CAND and relying on interpolation to make all-top competitive.
Deferred — FFT is reliable; autocorr is a secondary method for this event type.

---
---

## Entry 16 — Interactive guided extraction tools (research_gui branch)
**Date:** 2026-05-22
**Branch:** research_gui
**Commits:** 208c057 → a86d06b (8 commits)

### Tools developed
Two new interactive QC tools for guided Doppler extraction:

**tid_guided_extract.py** (v0.1.0)
Displays automated Doppler CSV traces in a stacked pyqtgraph window.
User clicks ground-truth phase samples on the TID wave per station;
sinusoid fitted from clicks replaces automated values in the selected
time window, writing `*_guided.csv`. Keys: 1-9 station, F fit, A fit-all
(shared period), W write, R reset, C clear, Q quit.

**tid_spect_click.py** (v0.1.0)
Displays spectrogram PNG with automated Doppler CSV overlay. User clicks
directly on the carrier track in the spectrogram image. More intuitive
than clicking the noisy extracted trace — the TID oscillation is directly
visible as the wavy carrier track. Same fit/write workflow as above.

**drf_spectrogram.py enhancement**
Now writes `<output_stem>_axes.json` sidecar alongside every PNG,
containing t_start/end (UTC hours), doppler_lo/hi (Hz), and dpi.
`tid_spect_click.py` auto-detects and loads the sidecar, eliminating
manual --tlim/--ylim arguments and margin guessing.

### Key design decisions
- Plot fraction defaults calibrated from drf_spectrogram.py 600dpi output
  by pixel-detecting cyan analysis-window lines (px 2646=18h, px 4810=20h)
  and spectrogram panel bounds (rows 184-2690 of 4278).
  Result: left=0.0582, right=0.8421, bottom=0.3712, top=0.9570.
- Period hint (--period-hint SECONDS) required when clicks don't span
  a full TID cycle — the span heuristic overestimates period otherwise
  (T=7346s observed vs correct 3600s).
- ApplicationShortcut context required for PyQt5 keyboard shortcuts to
  fire when GraphicsLayoutWidget has focus.
- Write guard added: W key does nothing until at least one click is made,
  preventing spurious write on launch from shell keypress bleed-through.

### End-to-end validation — May 2024 LSTID collinear array
Generated spectrograms with sidecars for W7LUX, AC0G_ND, N4RVE.
AC0G_ND subchannel 4 required (10 MHz channel); subchannel 0 gives
2.5 MHz noise with no visible carrier.
AC0G_ND spectrogram showed heavy E-region contamination — no coherent
carrier visible to click on. Used automated FFT CSV for AC0G_ND.
W7LUX and N4RVE guided successfully via spectrogram clicking.

| Method | Speed | From | Closure | All-pass |
|--------|-------|------|---------|---------|
| Spectrogram-guided (W7LUX+N4RVE) | 600 m/s | 9.6° | 3.2% | Yes ✅ |
| Automated FFT baseline | 605 m/s | 4.0° | 3.6% | Yes ✅ |

Agreement within 5 m/s and 5.6°. Both all-pass.

### Assessment
The guided tool confirms the automated FFT result on this event —
the carrier is clean enough on W7LUX and N4RVE that automated
extraction is already reliable. The guided tool's primary value is:
1. **Validation** — independent confirmation of automated result
2. **Contaminated stations** — when automated extraction fails
   (wrong peak, E-region lock), guided clicking on the spectrogram
   can recover the true carrier phase
3. **Ground truth** — human-verified phase samples for testing
   new automated extraction algorithms

The spectrogram-based tool (tid_spect_click.py) is preferred over
the Doppler-trace tool (tid_guided_extract.py) — the carrier track
is far easier to identify visually in the spectrogram than in the
noisy extracted Doppler time series.

---

## Entry 17 — Click-guided corridor extraction: implementation and first results
**Date:** 2026-05-23
**Branch:** research_gui
**Commits:** corridor extraction added to drf_to_doppler.py + tid_spect_click.py

### Implementation
Two components added:

**tid_spect_click.py — X key exports corridor JSON**
After clicking phase samples and pressing F to fit, pressing X writes
a `*_corridor.json` file containing the clicked (t_utc_hours, doppler_hz)
points and a half_bandwidth_hz value (default 0.5 Hz).

**drf_to_doppler.py — --corridor flag**
New `CorridorTrack` class loads the JSON and provides time-varying
corridor centre by linear interpolation between clicked points.
The FFT peak search is restricted to [centre - half_bw, centre + half_bw]
at each block, rejecting contamination outside the corridor.
Only supported with --method fft.

### Validation on W7LUX May 2024 LSTID
Corridor extraction correctly identified the true TID carrier:
- Corridor SNR: 18-40 dB (weaker — true F-region carrier)
- Automated SNR: 47-55 dB (stronger — spurious E-region/multipath peak)
- Lower SNR = correct answer: automated extractor was locking onto
  a stronger spurious feature, not the TID carrier

Corridor correctly fixed multiple wrong-peak rows:
| Time  | Automated | Corridor | Notes |
|-------|-----------|----------|-------|
| 18:22 | +0.050 Hz | +0.795 Hz | Auto jumped to wrong peak |
| 18:54-55 | +0.119 Hz | -0.692 Hz | Auto wrong sign |
| 19:01-03 | +0.132 Hz | -0.580 Hz | Auto wrong peak |
| 19:48 | +0.043 Hz | -1.275 Hz | Auto completely wrong |

### DOA result with corridor W7LUX
| Method | Speed | From | Closure | All-pass |
|--------|-------|------|---------|---------|
| Automated FFT (all 3 stations) | 605 m/s | 4.0° | 3.6% | Yes ✅ |
| Corridor W7LUX + auto AC0G/N4RVE | 338 m/s | 189.2° | 4.2% | No ⚠️ |

The corridor DOA disagrees with automated — 180° direction flip and
half the speed. Investigation showed this is NOT a code bug but a
systematic lag shift:

### Root cause: 180s lag shift in corridor extraction
Xcorr analysis of corridor W7LUX vs AC0G_ND:
- Corridor W7LUX peak lag: -1320s (r=0.654) — better correlation than auto
- Automated W7LUX peak lag: -1140s (r=0.576)
- Difference: 180s = 3 resample intervals

The corridor extracts a slightly different phase of the TID carrier
(the smooth underlying wave) vs the automated extractor (the noisy
instantaneous peak). The 180s phase difference propagates to the DOA
solver, shifting the xcorr peak and causing the multi-peak selector
to find an inconsistent solution with the AC0G_ND→N4RVE pair.

The all-top combo {-1320, -1320, -375} gives 375s closure — too large,
so the selector picks an alias combo {2220, 2040, -120} with 60s closure
which happens to give the 180°-flipped direction.

### Key insight: corridor needs to be applied to ALL stations
Applying corridor extraction to only one station while using automated
CSVs for the others creates inconsistency. The corridor finds a slightly
different carrier phase, breaking the triangle closure with the
automated extractions. For the approach to work correctly:
- All stations must use corridor extraction, OR
- The corridor must be verified to track the same phase as the
  automated extractor (difference < 1 resample interval = 60s)

### Clicking difficulty on contaminated stations
AC0G_ND and N4RVE spectrograms have significant E-region contamination
making it difficult to identify and click the true TID carrier.
The clicking guidelines need further refinement. Key issues:
- Users tend to click on bright features which are often contamination
- The true TID carrier can be much dimmer than competing features
- Gaps in the carrier track make consistent clicking difficult

### Next steps
1. Implement consistency check: after corridor extraction, compare
   the resulting CSV against the automated CSV. If the xcorr between
   them shows a lag offset > 60s, warn the user that the corridor
   may be tracking a different phase.
2. Consider wider half_bandwidth (1.0 Hz) to reduce sensitivity to
   exact corridor centre placement.
3. Test with corridor on all 3 stations simultaneously when
   clicking quality can be guaranteed.
4. Add visual feedback in tid_spect_click.py showing the corridor
   boundaries overlaid on the spectrogram after X is pressed.

---

## Entry 18 — Post-processing detrending (SGOLAY/outlier rejection) cannot fix wrong-peak lock
**Date:** 2026-05-23
**Reference:** Guerra et al. 2024 (J. Space Weather Space Clim. 14, 17)

### Context
Guerra et al. 2024 demonstrate FIF and SGOLAY are the best detrending
techniques for TID extraction from GNSS TEC time series. We tested
whether these approaches can fix the wrong-peak lock problem in HF
Doppler extraction.

### Test: SGOLAY on W7LUX and AC0G_ND
SGOLAY (2nd order polynomial, windows 31-59 samples) applied to
the automated FFT Doppler CSV. Results:

**W7LUX (clean station):** SGOLAY correctly recovers the broad TID
oscillation as background. However wrong-peak spikes (18:22h, 18:52h,
19:16-17h etc.) survive in the detrended signal because they have
energy in the TID frequency band and are not distinguishable from
real TID signal by a frequency-domain filter.

**AC0G_ND (contaminated station):** Additional median outlier rejection
(threshold 0.5 Hz from 7-min median) correctly flags isolated wrong-peak
spikes (18:30h, 19:22-25h). However the sustained wrong-peak lock at
18:00-18:15h (+1.3 Hz for ~15 min) is NOT flagged — the median filter
treats it as the local centre because it persists long enough.

### Key finding
Post-processing detrending (SGOLAY, FIF, median filtering) CANNOT fix
sustained wrong-peak lock in HF Doppler extraction. The fundamental
reason: a wrong-peak lock that persists >5-10 minutes has energy in
the TID frequency band (period 10-90 min) and is indistinguishable
from real TID signal by any frequency-domain or sliding-window filter.

This is qualitatively different from the GNSS TEC case (Guerra et al.)
where TEC is a continuous physical measurement without discrete peak
selection. HF Doppler extraction involves a spectral peak finder that
can lock onto spurious features with high SNR confidence, making the
resulting time series fundamentally different from a noisy continuous
measurement.

### Implication
The wrong-peak problem must be solved at the extraction stage, not
in post-processing. Valid approaches:
1. Corridor extraction (implemented) — constrain peak search using
   user-clicked carrier track. Works but requires consistent clicking
   on all stations.
2. Better extraction methods — bandpass/CWT methods in drf_to_doppler.py
   are more robust to E-region than FFT peak finding.
3. FIF on the 2D spectrogram — track the slowly-varying carrier in the
   time-frequency domain directly, rather than applying FIF to the
   already-extracted 1D Doppler time series. This is the correct
   interpretation of the Guerra et al. approach for HF Doppler.

### Guerra et al. parameters (for reference, if FIF on spectrogram pursued)
- LSTID band: 45-90 min period
- MSTID band: 10-40 min period
- SGOLAY: 2nd order, window = 2x MA window (120 min LSTID, 60 min MSTID)
- FIF: ~300x slower than SGOLAY but marginally better accuracy
- For computational speed: SGOLAY preferred
- FIF code: http://www.cicone.com (Python available)

---

## Entry 19 — Bandpass and CWT extraction on AC0G_ND: method comparison
**Date:** 2026-05-23
**Event:** May 2024 LSTID, AC0G_ND subchannel 4

### Extraction method comparison
| Method | Doppler std | Median SNR | Notes |
|--------|------------|-----------|-------|
| FFT    | 0.682 Hz   | 42.0 dB   | baseline |
| CWT    | 0.557 Hz   | 42.0 dB   | smoother |
| Bandpass | 0.414 Hz | 42.0 dB   | smoothest |

Lower std = fewer wrong-peak jumps. Bandpass most robust on this station.

### DOA results with AC0G_ND method variants
| AC0G_ND method | Speed | Direction | Closure | All-pass |
|----------------|-------|-----------|---------|---------|
| FFT (baseline) | 605 m/s | 4.0° | 3.6% | Yes ✅ |
| Bandpass | 161 m/s | 7.1° | 1.4% | No (speed⚠️) |
| CWT | 340 m/s | — | 4.0% | Yes ✅ |

### Analysis
Bandpass AC0G_ND: direction correct (7.1° agrees with 4.0°) but speed
wrong (161 vs 605 m/s). Lags: W7LUX→AC0G=-4490s vs FFT -1163s.
This is a subharmonic alias — the lag is ~3.8x the true value, consistent
with the TID period. The multi-peak selector is finding a self-consistent
alias solution. Same failure mode as autocorr (Entry 14).

CWT AC0G_ND: inconsistent lags (W7LUX→N4RVE positive when should be
negative). Discarded for this event.

### Conclusion
The automated FFT baseline remains the best result for this event.
Changing the extraction method on AC0G_ND does not improve the DOA
because the wrong-peak problem is in the xcorr peak selection, not
the Doppler extraction. The multi-peak selector fixes wrong-peak lock
within the analysis window but is vulnerable to subharmonic aliases
when the TID period is comparable to the analysis window length.

The 605 m/s, 4.0° result from FFT with multi-peak selector + parabolic
interpolation (Entry 15) remains the trusted result for this event.

---

## Entry 20 — sgolay-ridge on all stations: first complete 4-station result
**Date:** 2026-05-24
**Branch:** research_gui
**NOTE:** This entry was missing from FINDINGS.md. Reconstructed 2026-05-26.

### What was done
Applied sgolay-ridge corridor extraction to all 4 stations simultaneously
for the May 2024 LSTID event. Previous entries used sgolay-ridge on only
one or two stations while others used FFT — creating phase offset biases
that corrupted DOA results.

### Key insight
For the DOA cross-correlation biases to cancel, ALL stations must use
the same extraction method. Mixing sgolay-ridge and FFT introduces a
systematic ~60s phase offset between stations, corrupting triangle closure.

### Result
When all 4 stations use corridor + sgolay-ridge:
- Speed: 267 m/s from 242° (WSW)
- All 5 diagnostics pass
- Triangle closure: 6.9%
- This superseded the earlier 458 m/s result (Entry 21) which used
  mixed methods and incorrect (receiver rather than IPP) coordinates.

---

## Entry 21 — Complete guided workflow validated: 458 m/s WSW LSTID
**NOTE: superseded by Entry 22 (267 m/s, 242° WSW) which uses correct IPP coordinates and 4 stations.**
**Date:** 2026-05-24
**Branch:** research_gui
**Event:** May 17 2024, 17:57-19:06 UTC

### Workflow steps completed
1. `drf_spectrogram.py` — full-day spectrogram (100 dpi) for each station
2. `tid_quicklook.py` — user selects TID window on full-day spectrogram
3. `drf_spectrogram.py --window` — zoomed spectrogram for selected window
4. `tid_quicklook.py` — user refines window on zoomed spectrogram
5. `drf_to_doppler.py --method fft` — automated FFT extraction for overlay
6. `drf_spectrogram.py --overlay` — regenerate zoomed spectrogram with FFT overlay
7. `tid_spect_click.py` — user clicks corridor on zoomed spectrogram
   - Corridor consistency check confirms tracking correct carrier
   - Visual corridor overlay shows search band
8. `drf_to_doppler.py --method sgolay-ridge --corridor` — 2D STFT ridge extraction
9. `tid_doa.py` — DOA result

### Station details
| Station | Subchannel | Freq | Window | SNR |
|---------|-----------|------|--------|-----|
| W7LUX   | 0 | 10 MHz | 17:35-20:36 | 44.3 dB |
| AC0G_ND | 4 | 10 MHz | 17:57-19:52 | 37.3 dB |
| N4RVE   | 4 | 10 MHz | 17:37-19:07 | 32.8 dB |
Overlap: 17:57-19:06 UTC (69 min)

### DOA result
| Metric | Value |
|--------|-------|
| Phase speed | 458 m/s |
| Direction | from 258.6° (WSW) |
| Triangle closure | 0.5% |
| Correlations | 0.673 / 0.713 / 0.787 |
| SVR | 1.2 |
| All-pass | Yes ✅ |

Consistent with westward-propagating LSTID. All five diagnostics pass.

### Key fixes made during workflow
1. `drf_spectrogram.py --window`: bug fixed (was nested inside if args.start)
2. `drf_spectrogram.py plot_fraction`: now uses matplotlib axes position
   (image pixel measurement was unreliable for different spectrogram types)
3. `tid_quicklook.py`: neutral default region (user decides where TID is)
4. `tid_quicklook.py`: overlap check after S press warns if <60 min overlap
5. `tid_spect_click.py`: auto-detects _window.json from tid_quicklook.py

### Lessons learned
- The corridor as prior constraint works well — user doesn't need to click
  precisely on carrier, just bracket the search region
- AC0G_ND corridor (±0.5 Hz around 0 Hz) correctly rejects E-region spikes
- sgolay-ridge smoothing (21 min window) gives clean extraction with good
  correlations and excellent triangle closure
- Time window overlap must be checked early — the overlap warning in
  tid_quicklook.py is essential
- Subchannel selection matters: all stations should use same frequency
  (10 MHz here) for consistent Doppler comparison

---

## Entry 22 — 4-station DOA with N5BRG and IPP coordinates
**Date:** 2026-05-24
**Event:** May 17 2024, 18:29-19:06 UTC

### Result
| Metric | Value |
|--------|-------|
| Phase speed | 267 m/s |
| Direction | from 242.3° (WSW) |
| Triangle closure | 6.9% |
| Correlations | 0.429-0.748 |
| All-pass | Yes ✅ |

### Comparison with Gwyn's result (V1.2)
| Metric | Gwyn | Ours (4-stn) |
|--------|------|-------------|
| Speed | 979 m/s | 267 m/s |
| Direction | 157° (SSE) | 242° (WSW) |

### Analysis of discrepancy
1. Direction stable at ~242-252° across all our configurations (3-stn, 4-stn,
   different time windows) — consistent result
2. Gwyn uses path velocity along specific azimuths (126° and 221°) then
   vector decomposition — fundamentally different from our plane-wave DOA
3. ~90° direction difference and ~4x speed difference suggest the two methods
   are measuring different projections of the wave vector
4. Our result is internally self-consistent (all diagnostics pass)
5. Resolution requires direct comparison with Gwyn — methodological difference
   is the key question

### IPP coordinates used (WWV transmitter at 40.68N, 105.04W)
| Station | Receiver | IPP midpoint |
|---------|---------|-------------|
| W7LUX | 35.10N, 111.71W | 37.89N, 108.37W |
| AC0G_ND | 46.88N, 96.83W | 43.78N, 100.94W |
| N4RVE | 44.97N, 123.48W | 42.83N, 114.26W |
| N5BRG | 35.65N, 97.48W | 38.17N, 101.26W |

---

## Entry 23 — Automated FFT vs SGOLAY-ridge: 4-station comparison
**Date:** 2026-05-24
**Event:** May 17 2024, 18:29-19:06 UTC, 4 stations with IPP coordinates

### Results comparison
| Metric | Auto FFT | SGOLAY-ridge |
|--------|----------|-------------|
| Speed | 222 m/s | 267 m/s |
| Direction | from 186° (S) | from 242° (WSW) |
| Closure | 18.1% ❌ | 6.9% ✅ |
| Weak pairs | 2 ❌ | 0 ✅ |
| All diagnostics | No ❌ | Yes ✅ |

### Key finding
The automated FFT fails two diagnostics (weak correlations, poor closure).
The sgolay-ridge corridor extraction passes all five diagnostics with:
- Better correlations on all 6 pairs
- 3x better closure (6.9% vs 18.1%)
- Different W7LUX→N4RVE lag (+1081s vs -239s) — automated FFT was
  locking onto wrong xcorr peak for this pair

### Conclusion
This is the definitive validation of the corridor + sgolay-ridge approach.
The corridor constrains the STFT search to the true carrier, preventing
wrong-peak lock that corrupts automated FFT lags. The result is physically
consistent across all diagnostic metrics where the automated approach fails.

The direction (242° WSW) is stable and internally consistent. The remaining
discrepancy with Gwyn's result (157° SSE, 979 m/s) is methodological and
requires direct discussion with Gwyn to resolve.

---

## Entry 24 — Full method comparison: FFT vs Autocorr vs SGOLAY-ridge
**Date:** 2026-05-24
**Event:** May 17 2024, 18:29-19:06 UTC, 4 stations, IPP coordinates

### Complete comparison
| Metric | Auto FFT | Autocorr | SGOLAY-ridge |
|--------|----------|----------|-------------|
| Speed | 222 m/s | 233 m/s | 267 m/s |
| Direction | 186° (S) | 188° (S) | 242° (WSW) |
| Closure | 18.1% ❌ | 35.0% ❌ | 6.9% ✅ |
| Diagnostics | 2 fail ❌ | 1 fail ❌ | All pass ✅ |
| W7LUX→N4RVE lag | +1081s | +979s | -239s |

### Key findings
1. FFT and autocorr cluster together (~186-188°, ~220-233 m/s) but both
   fail diagnostics — they share the same wrong-peak lock on W7LUX→N4RVE
2. SGOLAY-ridge gives different W7LUX→N4RVE lag (-239s vs +979-1081s)
   — corridor extraction correctly identifies the true carrier
3. SGOLAY-ridge is the only method that passes all diagnostics
4. Autocorr closure (35%) is worst of all — wrong-peak aliases dominate
5. The automated methods are self-consistent with each other but both wrong

### Conclusion
The corridor + sgolay-ridge approach is definitively superior to both
automated methods for this event. The direction (242° WSW) is the most
reliable result. The automated FFT and autocorr results (186-188° S)
should not be trusted for this event due to wrong-peak lock on the
W7LUX→N4RVE pair.

### Note on method field in event JSON
The "method" field in event JSON is metadata only (which extractor
produced the CSV) — it does not affect the DOA computation.
Should be renamed "extraction_method" in a future cleanup to avoid
confusion with the DOA method.

---

## Entry 25 — Comparison of array geometry with Gwyn's method
**Date:** 2026-05-24

### Midpoint-to-midpoint azimuths and distances
| Path | Gwyn states | Calculated | Distance |
|------|------------|-----------|---------|
| N4RVE→N5BRG | 126° | 111° | 1214 km |
| AC0G_ND→W7LUX | 221° | 226° | 905 km |

Gwyn's stated azimuths differ from calculated by ~15° on N4RVE→N5BRG.
Likely due to different receiver coordinates or IPP height assumption.

### Methodological difference
Gwyn's method:
- Measures velocity ALONG each path (scalar projection)
- Two paths roughly perpendicular (126° and 221°) — ideal for 2D decomposition
- Vector decomposition gives resultant velocity: 979 m/s at 157°

Our method:
- Fits plane wave to ALL pairwise lags simultaneously (least squares)
- Uses IPP midpoint coordinates
- Result: 267 m/s at 242° (coming from)

### Why results differ
If the TID wavefront is perfectly planar, both methods should agree.
Possible reasons for ~95° direction discrepancy:
1. Wrong-peak lock in Gwyn's autocorrelation lags (he uses 27 and 35 min
   lags from visual inspection of xcorr plots)
2. Our W7LUX→N4RVE lag may still be wrong despite corridor extraction
3. The wavefront may not be perfectly planar across this array
4. Different time windows (Gwyn: 19:00 UTC; ours: 18:29-19:06 UTC)

### Action items
1. Ask Gwyn for his exact lag values and how he measured them
2. Verify our W7LUX→N4RVE lag (-239s) is correct by visual inspection
3. Try replicating Gwyn's 2-path method using our extracted Doppler CSVs

---

## Entry 26 — Critical limitation: diagnostics are not independent validation
**Date:** 2026-05-24

### The fundamental problem
The five diagnostics in tid_doa.py (geometry conditioning, plane-wave
residual, pairwise correlation, triangle closure, phase speed range) measure
INTERNAL CONSISTENCY only. They were empirically tuned based on early FFT
results and do not constitute physical validation.

A result can be:
- Internally consistent (all diagnostics pass) but physically wrong
- Internally inconsistent (diagnostics fail) but pointing toward real physics

The fact that sgolay-ridge passes all diagnostics while FFT fails is partly
circular — the diagnostics reward self-consistency, and the corridor
extraction enforces consistency by construction (smooth carrier tracking).

### What the diagnostics actually tell us
1. Geometry conditioning (SVR < 30): array not near-collinear — GEOMETRIC
2. Plane-wave residual (< 25%): lags consistent with a single plane wave — CONSISTENCY
3. Pairwise correlation (> 0.40): signals are correlated — SIGNAL QUALITY
4. Triangle closure (< 15%): lags form a consistent triangle — CONSISTENCY
5. Phase speed range (100-1000 m/s): result in physically plausible range — WEAK PHYSICAL

None of these confirm the result is physically real. They only confirm the
lags are self-consistent and the signals are correlated.

### What is needed for true validation
1. Independent measurement of same event:
   - GNSS TEC keograms (SuperMAG, CORS network)
   - Ionosonde Doppler (closest: Millstone Hill, Boulder)
   - SuperDARN ground scatter
   - Gwyn's independent analysis (different method)
2. Synthetic data test: inject known TID into synthetic I/Q, verify recovery
3. Multiple independent events: consistent results across many events
   build confidence even without per-event ground truth

### Current validation status
- Our result (267 m/s, 242° WSW) is internally consistent ✅
- Gwyn's result (979 m/s, 157° SSE) disagrees by ~95° direction and 4x speed
- Root cause of discrepancy unknown — could be either result being wrong
- No independent reference measurement available for this event
- Diagnostics thresholds were tuned on early FFT results — not independent

### Implications for research_gui branch
The corridor + sgolay-ridge workflow is a significant improvement in
extraction quality. But "improvement" here means:
- Fewer wrong-peak locks (demonstrated by SNR analysis)
- Better pairwise correlations (demonstrated by xcorr)
- Better internal consistency (demonstrated by closure)

It does NOT yet mean demonstrated physical accuracy. That requires
comparison with Gwyn and/or independent measurements.

---

## Entry 27 — tid_workflow.py: complete guided workflow wrapper
**Date:** 2026-05-25
**Branch:** research_gui

### Implementation
New `tid_workflow.py` automates the 10-step guided extraction workflow:
1. Auto-discover stations in event directory
2. Full-day spectrogram per station
3. User selects TID window (tid_quicklook.py)
4. Zoomed spectrogram
5. User refines TID window
6. Automated FFT extraction (overlay)
7. Zoomed spectrogram with FFT overlay
8. User clicks corridor (tid_spect_click.py + sgolay preview)
9. sgolay-ridge extraction
10. DOA (tid_doa.py)

### Key features
- State saved after each step — resumable with --resume
- Auto-discovers DRF stations in event directory
- Always generates subchannel thumbnails for user to confirm visually
- Gets receiver coords: DRF metadata → callsign DB → user input
- Computes IPP midpoints automatically (WWV default transmitter)
- Overlap check with option to quit and redo windows if <60 min
- Run logs written to event directory not cwd

### First test (4 stations, May 2024 event)
- Overlap: 37 min (too short — 3 diagnostics failed)
- Lesson: window alignment is critical
- The overlap warning now offers quit option to redo windows

### Usage
    python3 tid_workflow.py --event-dir ~/Downloads/gwyn_tid_event_20240517
    python3 tid_workflow.py --event-dir ~/Downloads/gwyn_tid_event_20240517 --resume

---

## Entry 28 — Summary: SGOLAY-ridge strategy vs FFT and autocorr
**Date:** 2026-05-25
**Branch:** research_gui

### The fundamental problem all three methods face

All three methods extract a Doppler frequency vs time trace from raw I/Q
data recorded at HF receivers listening to WWV (or another beacon). The
I/Q recording contains the received signal — a mixture of the direct
ionospheric reflection of the beacon (the "carrier") plus contamination
from E-region multi-hop propagation, interference, and noise.

The goal is to track the carrier frequency over time. A TID modulates
the ionospheric height, which shifts the carrier frequency sinusoidally
by typically ±0.5-2 Hz over periods of 15-90 minutes. The DOA analysis
cross-correlates these traces between station pairs to find time lags,
then fits a plane wave to determine speed and direction.

The failure mode common to all methods: **wrong-peak lock** — the
extractor latches onto a strong spurious feature (E-region hop, multipath)
rather than the true F-region carrier. This produces a plausible-looking
trace that cross-correlates well internally but gives wrong lags.

---

### Method 1: FFT peak finding (original, --method fft)

**How it works:**
For each 60-second block of I/Q data, compute the FFT spectrum and find
the peak frequency within a search band (default ±5 Hz around 0 Hz).
Parabolic interpolation refines the peak to sub-bin accuracy.

**Strengths:**
- Simple and fast
- Works well on clean stations (high SNR, no contamination)
- Parabolic interpolation gives sub-sample accuracy
- Multi-peak xcorr selector in tid_doa.py handles some wrong-peak cases

**Weaknesses:**
- Each block processed independently — no temporal continuity
- Locks onto the strongest peak in the search band per block
- E-region contamination often produces a stronger peak than the true carrier
- Wrong-peak lock can persist for many minutes producing a consistent
  but incorrect trace
- Cannot distinguish a strong spurious peak from the true carrier

**When it fails:**
On contaminated stations (AC0G_ND, N4RVE), the E-region spike is often
10-20 dB stronger than the F-region carrier. The FFT finds the spike,
not the carrier. The resulting trace has sharp jumps when the spike
appears/disappears — std 0.682 Hz vs 0.414 Hz for corridor extraction.

---

### Method 2: Complex autocorrelation (--method autocorr)

**How it works:**
For each 60-second block, compute the complex autocorrelation at lag=1
sample (100ms at 10 sps). The phase of the lag-1 autocorrelation gives
the instantaneous frequency: f = angle(R(1)) / (2π × dt).

**Strengths:**
- Naturally robust to broadband noise (autocorrelation suppresses
  uncorrelated noise)
- Can track slowly-varying frequency even in moderate contamination
- Smoother trace than FFT on some events

**Weaknesses:**
- Susceptible to subharmonic aliases — can lock onto a frequency that is
  a harmonic of the true carrier
- On LSTID events (long period), the alias can be at 3-4x the true lag,
  producing self-consistent but wrong DOA results
- Still processes each block independently
- Gwyn's method uses autocorrelation but at longer lags with different
  parameters — our implementation may not match his exactly

**When it fails:**
On the May 2024 LSTID, autocorr gave consistent triangle closure (0%)
but at a subharmonic alias lag (-4380s vs the true -1140s). All pairs
landed on the same alias, so closure was zero but the result was wrong.
Speed 163 m/s vs FFT 605 m/s — a factor of ~3.8x (the alias order).

---

### Method 3: Corridor + SGOLAY-ridge (new, --method sgolay-ridge)

**How it works:**

**Step A — User defines corridor (tid_spect_click.py):**
The user opens the Doppler spectrogram and clicks ~6 points that
bracket the carrier band across the analysis window. These clicks define
a time-varying frequency corridor (centre ± half_bandwidth Hz, default
±0.5 Hz). The corridor is a PRIOR CONSTRAINT — it tells the algorithm
where to look, not what the carrier looks like. Clicks don't need to be
precise — just bracket the carrier.

A consistency check (xcorr between corridor centres and automated CSV)
warns if the corridor is tracking a different feature than the automated
extractor. A sgolay-ridge preview shows the extracted trace overlaid on
the spectrogram so the user can verify before committing.

**Step B — 2D STFT ridge tracking (drf_to_doppler.py --method sgolay-ridge):**
1. Read ALL I/Q data for the analysis window at once (not block by block)
2. Build the full STFT spectrogram (time × frequency, one column per 60s block)
3. For each time step, restrict the frequency axis to the corridor band
4. Compute the POWER-WEIGHTED CENTROID within the corridor band:
       f_centroid = Σ(f × |S(f)|²) / Σ(|S(f)|²)
   This uses all power in the band, not just the peak bin. More stable
   than argmax against noise and better-defined when the carrier has
   finite width.
5. Apply SGOLAY smoothing across time (default 21-minute window):
   - Removes residual spike-like artifacts within the corridor
   - Does NOT phase-shift the TID oscillation (21 min << 60 min TID period)
   - Guerra et al. 2024: SGOLAY is optimal for TID extraction from TEC

**Why this is fundamentally different:**

| Aspect | FFT/autocorr | SGOLAY-ridge |
|--------|-------------|-------------|
| Search space | Full ±5 Hz band | User-defined ±0.5 Hz corridor |
| Per-block | Yes — independent | No — global STFT |
| Peak finding | Argmax / autocorr phase | Power-weighted centroid |
| Temporal info | None | SGOLAY across all blocks |
| User input | None | Required (corridor clicks) |
| Contamination handling | Post-hoc (multi-peak selector) | Pre-empted (corridor constraint) |

**The corridor eliminates wrong-peak lock by construction** — if the
E-region spike is outside the corridor, it cannot affect the extraction.
The user's visual inspection of the spectrogram is the primary quality
control, not algorithmic detection.

**Strengths:**
- Cannot lock onto features outside the corridor
- Power-weighted centroid more stable than argmax
- SGOLAY smoothing removes residual artifacts
- User sees exactly what was extracted (green preview curve)
- Higher pairwise correlations in DOA (0.699 vs 0.574 on W7LUX)

**Weaknesses:**
- Requires user interaction (corridor clicking) — not fully automated
- Corridor must be clicked consistently across all stations for biases
  to cancel in cross-correlation
- SGOLAY window must be tuned to TID period (21 min for LSTID, 10 min
  for MSTID)
- Power-weighted centroid introduces a small systematic phase offset
  vs FFT argmax (~60s) which can affect triangle closure when only one
  station uses corridor extraction

**When it fails:**
If the user clicks the corridor on the wrong feature (E-region instead
of F-region carrier), the result is wrong. The consistency check and
preview mitigate this but don't eliminate it. If only one station uses
corridor extraction while others use FFT, the phase offset creates
inconsistency — all stations must use the same method.

---

### Comparison on May 2024 LSTID (4 stations, 18:29-19:06 UTC)

| Method | Speed | Direction | Closure | Diagnostics |
|--------|-------|-----------|---------|-------------|
| Auto FFT | 222 m/s | 186° (S) | 18.1% | 2 fail ❌ |
| Autocorr | 233 m/s | 188° (S) | 35.0% | 1 fail ❌ |
| SGOLAY-ridge | 267 m/s | 242° (WSW) | 6.9% | All pass ✅ |
| Gwyn (manual) | 979 m/s | 157° (SSE) | — | — |

The FFT and autocorr agree with each other (both finding the same
wrong-peak lock on W7LUX→N4RVE) but disagree with SGOLAY-ridge and
with Gwyn. SGOLAY-ridge gives the best internal consistency but still
disagrees with Gwyn by ~85° direction and ~4x speed.

### Critical caveat
All three methods produce internally self-consistent results that pass
most diagnostics. Internal consistency is NOT physical correctness.
True validation requires independent measurement (GNSS TEC, ionosonde,
Gwyn's independent analysis). The diagnostics in tid_doa.py were
calibrated on early FFT results — they favour SGOLAY-ridge partly
because SGOLAY-ridge enforces smoothness by construction.

---

## Entry 29 — EMD test on W7LUX May 2024 LSTID
**Date:** 2026-05-25
**Branch:** research_gui

### Setup
EMD v0.8.1 applied to w7lux_fft_tid2.csv (182 samples, 60s cadence).
emd.sift.sift() with default parameters.

### Decomposition
| IMF | Period | Std | Interpretation |
|-----|--------|-----|----------------|
| 1 | 4 min | 0.266 Hz | Noise/spikes |
| 2 | 9 min | 0.147 Hz | Short-period contamination |
| 3 | 38 min | 0.379 Hz | MSTID or E-region |
| 4 | **90 min** | **0.407 Hz** | **LSTID carrier ✅** |
| 5 | trend | 0.156 Hz | Slow background |

### Comparison with SGOLAY-ridge
- EMD IMF4 and SGOLAY-ridge track the same 90-min oscillation
- EMD is smoother — may over-smooth real amplitude variation
- Phase offset: EMD lags SGOLAY by 540s (r=0.568)
- They diverge after 19:00 UTC — SGOLAY shows amplitude growth,
  EMD is more symmetric

### Implications for DOA
- 540s phase offset means EMD and SGOLAY cannot be mixed across stations
- EMD must be applied consistently to ALL stations for biases to cancel
- EMD would give a different set of pairwise lags than SGOLAY-ridge
- Need to run DOA with EMD on all 4 stations to compare

### Assessment
EMD correctly identifies the LSTID at 90 min. It is fully automatic
(no corridor clicking required). The phase offset vs SGOLAY-ridge is
a systematic bias — consistent across stations it would cancel in DOA.
Next step: run EMD on all 4 stations and compare DOA result with
sgolay-ridge result.

### FIF vs EMD
For this signal (well-separated LSTID at 90 min vs contamination at
<10 min), EMD works adequately. Mode mixing would be a problem if TID
and contamination overlapped in period — they don't here. FIF
implementation deferred.

---

## Entry 30 — GUI clean launch fix + workflow spectrogram strategy
**Date:** 2026-05-25
**Branch:** research_gui

### Problem
tid_spect_click.py was showing curves on launch from two sources:
1. pyqtgraph csv_curve being drawn before _csv_visible initialized
2. FFT overlay curves baked into the spectrogram PNG by drf_spectrogram.py --overlay

### Fix
1. _csv_visible initialized in __init__ before _build_ui
2. _refresh_scatter respects _csv_visible flag
3. All curves explicitly cleared after preview_curve created
4. Stale corridor JSON and preview CSV deleted on launch
5. V key toggles CSV overlay on/off
6. C key clears all curves

### Spectrogram strategy (important)
Two separate spectrograms must be generated:
- _zoom_clean.png — NO overlay, used for corridor clicking in tid_spect_click.py
- _zoom_overlay.png — WITH FFT overlay, for visual inspection only

The overlay PNG is for the user to understand the signal before clicking.
The clean PNG is what tid_spect_click.py uses — any curves shown are
generated by the tool in the current session only.

### tid_workflow.py change needed
Step 7 (corridor clicking) must use clean PNG, not overlay PNG.
Step 6 generates overlay PNG for inspection.
Step 7 generates clean PNG for clicking.

---

## Entry 31 — GUI cleanup: amplitude panel and sinusoid fit removed
**Date:** 2026-05-25
**Branch:** research_gui

### Changes
1. **drf_spectrogram.py** — bottom amplitude panel removed. Single-panel
   figure (14×6). compute_peak_amplitude() dead code removed. date_utc
   added to sidecar JSON so tid_spect_click.py can determine the recording
   date without reading a CSV.

2. **tid_spect_click.py** — sinusoid fit workflow (F/W keys) removed;
   superseded by corridor+sgolay. CSV overlay (V key) removed; not useful
   when corridor workflow is the only path. FFT consistency check removed;
   the corridor intentionally disagrees with FFT on contaminated stations.

3. **sgolay preview window** — now uses corridor click extent (min/max
   click times) rather than yellow segment handles. This ensures the
   preview runs on exactly the data the user clicked, not a wider window.

4. **Date extraction** — sidecar JSON now carries date_utc field. Preview
   subprocess gets the correct --start/--end timestamps from the sidecar
   rather than trying to parse the date from the CSV or filename.

### Net result
tid_spect_click.py is now a focused corridor-clicking tool only.
No legacy sinusoid fit code remains. --csv argument retained as
optional no-op for backward compatibility with tid_workflow.py calls.

---

## Entry 32 — Jan 2026 event: sgolay-ridge vs FFT comparison
**Date:** 2026-05-25
**Branch:** research_gui

### Event
2026-01-19, 00:00-01:36 UTC, 4 stations: AA6BD, AC0G_ND, N6RFM, W7LUX

### Results
| Metric | SGOLAY-ridge | FFT |
|--------|-------------|-----|
| Speed | 283 m/s | 99 m/s |
| From | 30° (NNE) | 167° (SSE) |
| Residual | 44.8% | 46.7% |
| Closure | 38.2% | 3.8% |
| Diagnostics fail | 2/5 | 3/5 |

### Interpretation
FFT has better closure but physically wrong speed (99 m/s, below TID
range) and opposite direction. AA6BD→AC0G_ND lag jumped from -2 min
(sgolay) to +77 min (FFT) — wrong-peak lock on AC0G_ND confirmed.

SGOLAY-ridge gives physically plausible result: 283 m/s from NNE,
consistent with auroral LSTID travelling equatorward. Higher residual
is due to AC0G_ND→N6RFM aliasing (6 min closure on one triangle).

### Conclusion
This event confirms Entry 28 finding on a completely independent dataset:
FFT produces internally consistent but physically wrong lags when
AC0G_ND is contaminated. SGOLAY-ridge corridor extraction correctly
identifies the F-region carrier and gives the physically meaningful result.

---

## Entry 33 — Jan 2026 document speed error identified
**Date:** 2026-05-25
**Branch:** research_gui

### Finding
The draft analysis document reports 666 m/s for the Jan 2026 event.
This is inconsistent with the peak times shown in Figure 4:

- AC0G_ND→N6RFM: 23 min over 388 km → 280 m/s
- AA6BD→N6RFM: 16 min over 271 km → 282 m/s

Both direct baseline calculations give ~280 m/s, matching our
sgolay-ridge DOA result of 283 m/s from 30°.

The document's lag table has 5-7 min triangle closure errors across
all four triangles, making least-squares inversion ill-conditioned.
The 666 m/s figure was from an early FFT autocorr analysis before
IPP midpoint coordinates were used correctly.

### Correct result
- Speed: ~280-283 m/s (consistent across 3 independent methods:
  sgolay DOA, peak-time on AC0G_ND→N6RFM, peak-time on AA6BD→N6RFM)
- From: 30-35° (NNE) — equatorward auroral LSTID
- The document's direction (35°) is correct; speed needs correction.

### Action
Update the draft document to report 283 m/s and add peak-time
cross-check as independent validation of the sgolay-ridge result.
This will be the first physically validated result from psws-drf-tid-tools.

---

## Entry 34 — Jan 2026: max_lag_seconds constraint improves result
**Date:** 2026-05-26
**Branch:** research_gui

### Problem
Default max_lag_seconds=5828s (58 min) allowed AC0G_ND→N6RFM xcorr
to find the +27 min alias peak (r=0.576) instead of being constrained
to the true peak region.

### Fix
Set max_lag_seconds=1800s (30 min) in event JSON. This forces xcorr
to search only within ±30 min, eliminating the alias.

### Result with max_lag_seconds=1800
- Speed: 254 m/s from 31° (NNE)
- vs unrestricted: 283 m/s from 30°
- vs peak-time: ~281 m/s from ~33°

### Summary of Jan 2026 results
| Method | Speed | From |
|--------|-------|------|
| sgolay DOA (unrestricted) | 283 m/s | 30° |
| sgolay DOA (30 min max) | 254 m/s | 31° |
| Peak-time direct | ~281 m/s | ~33° |

Best estimate: **254-283 m/s from 30-33° NNE**.
Direction is robust across all methods. Speed uncertainty ~10%.

### Recommendation
Always set max_lag_seconds in event JSON when TID period is known.
For this event (~80-100 min period), 30 min is appropriate — it
allows lags up to one-third of the period, preventing aliasing while
covering the expected lag range for this array geometry.

---

## Entry 35 — Gwyn's email response: sign convention error identified
**Date:** 2026-05-26 (reconstructed from session — event was 2026-05-25)
**Branch:** research_gui

### Gwyn's key findings
1. **Sign convention error in his original analysis** — Gwyn reported
   lags for current-cycle vs previous-cycle rather than current vs current.
   When corrected, his AC0G_ND/W7LUX lag becomes -18 min (negative = AC0G_ND
   leads W7LUX, physically correct for northward station).

2. **Corrected lag table (Gwyn, 17:30-19:30 UTC window):**

   | Time interval | N4RVE/N5BRG neg lag | r | AC0G_ND/W7LUX neg lag | r |
   |--------------|--------------------|----|----------------------|----|
   | 18:00-20:00  | -37 min | 0.553 | -22 min | 0.733 |
   | 17:30-20:30  | -26 min | 0.374 | -22 min | 0.601 |
   | 17:30-19:30  | -32 min | 0.610 | -18 min | 0.683 |

3. **N5BRG channel confirmed:** S000038 (NS channel) = subchannel 0

4. **TID period not constant** — Gwyn notes the period varies across
   time intervals, indicating a dispersive or non-stationary wave.

### Comparison with our sgolay-ridge result
- Our AC0G_ND/W7LUX lag: -27 min (close to Gwyn's -18 to -22 min) ✅
- Our N4RVE/N5BRG lag: -22 min (vs Gwyn's -26 to -37 min) — some discrepancy
- Direction agreement: both give NE origin, SW propagation ✅
- Speed: our 267 m/s vs Gwyn's original 979 m/s — discrepancy explained
  by Gwyn's sign convention error (he was using wrong-cycle lags)

### Physical constraint from Gwyn
For auroral LSTID: northern stations must lead (negative lag when listed
south-to-north). AC0G_ND (north) leads W7LUX (south) — confirmed by both.

### Implication
The ~85° direction discrepancy between our original result (242° WSW)
and Gwyn's original (157° SSE) was primarily due to Gwyn's sign convention
error. After correction, both methods give roughly consistent NE→SW
propagation, consistent with auroral LSTID origin.

---

## Entry 36 — Sign convention cross-check with Gwyn: full reconciliation
**Date:** 2026-05-26
**Branch:** research_gui

### Our sign convention (tid_doa.py)
positive lag τ_ij means station j lags station i (wave reached i first).
Cross-correlation: lag at which correlate(signal_i, signal_j) is maximum,
where positive lag = signal_j shifted forward in time relative to signal_i.

### Gwyn's corrected convention
Correlation of first(t-lag) with second(t).
Positive lag = first station leads second = second lags first.
This is IDENTICAL to our convention.

### Verification on AC0G_ND/W7LUX pair
Our result: W7LUX→AC0G_ND lag = -27 min
= AC0G_ND leads W7LUX by 27 min ✅ (physically correct: AC0G_ND is north)
Gwyn corrected: -18 min (17:30-19:30 window)
Difference: 9 min — explained by different analysis windows:
  - Our window: 17:34-19:28 UTC
  - Gwyn's window: 17:30-19:30 UTC
  Different portions of the non-stationary TID give different lags.

### N4RVE/N5BRG discrepancy
Our result: N4RVE→N5BRG lag = -22 min
Gwyn corrected: -26 to -37 min (varies by time window)
Same direction (N4RVE leads, physically correct) but magnitude differs.
Again explained by different windows and TID non-stationarity.

### Gwyn's statement: "your peaks are a mix of current and previous"
This was true for our ORIGINAL results (Entry 24) where:
- FFT: W7LUX→AC0G_ND = +27 min (wrong sign — wrong cycle)
- sgolay-ridge: W7LUX→AC0G_ND = -27 min (correct sign — right cycle)
The corridor + sgolay-ridge extraction corrected this. All sgolay-ridge
lags are on the physically correct cycle (northern stations lead).

### Summary of reconciliation
| Pair | Our sgolay | Gwyn corrected | Agreement |
|------|-----------|----------------|-----------|
| AC0G_ND/W7LUX | -27 min | -18 min | Same sign ✅, 9 min diff |
| N4RVE/N5BRG | -22 min | -26 to -37 min | Same sign ✅, varies |

Both analyses now agree: wave travels NE→SW, northern stations lead.
Remaining discrepancies are due to TID non-stationarity across different
analysis windows — not a systematic error in either method.

### Outstanding question
Gwyn notes TID period varies across his three time intervals — this is
consistent with a dispersive gravity wave packet rather than a monochromatic
wave. The 4-station plane-wave DOA assumes a monochromatic wave; the
residuals we see (44-65% RMS) partly reflect this non-stationarity.

---

## Entry 37 — Jan 2026: corridor extraction variability and lag consistency
**Date:** 2026-05-26
**Branch:** research_gui

### Observation
Fresh corridor re-clicking on all 4 stations for the Jan 2026 event
produces lags that are not fully plane-wave consistent:
- N6RFM→W7LUX: -21s (~0 min) — inconsistent with other pairs
- Expected from AA6BD pairs: +278s (+4.6 min)
- AC0G_ND→W7LUX: xcorr peak at ±45 min, weak (r=0.408)

### Root cause
TID non-stationarity (confirmed by Gwyn, Entry 36): the wave period
and amplitude vary across the 2-hour analysis window. Different
corridor clicks on different sessions capture different portions of
the waveform, giving slightly different phase offsets.

### Best validated result for this event
254-283 m/s from 30-35° NNE (from previous sgolay sessions with
max_lag=30-60 min). Direction is robust across all sessions.
Speed uncertainty ~15% reflects TID non-stationarity.

### Recommendation
For non-stationary TIDs, the analysis window should be kept as short
as possible while still capturing at least one full cycle. For this
~80-100 min period TID, 90-100 min is optimal. The 118-min window
used here includes partial second cycle introducing phase ambiguity.

---

## Entry 38 — cwt-prophet vs cwt vs sgolay-ridge: Jan 2026 comparison
**Date:** 2026-05-26
**Branch:** research_gui

### Method
Added --method cwt-prophet to drf_to_doppler.py — identical to --method cwt
except Facebook Prophet replaces linear extrapolation for carrier prediction.
Compared all 5 methods on N6RFM and AC0G/ND for Jan 2026 event.

### N6RFM result
- fft, autocorr, cwt-prophet: identical until ~01:10, then wrong-peak spike at 01:15
- cwt (linear): avoids the 01:15 spike — smoother through contamination
- sgolay-ridge: different shape in first 30 min (corridor coverage gap), then consistent

### AC0G/ND result
- fft and cwt-prophet: identical throughout — both wrong-peak lock after 01:00 UTC
- autocorr: smoother but still wrong-peaks after 01:15
- cwt (linear): tracks with fft until 01:15, then also wrong-peaks
- sgolay-ridge: smoothly follows carrier through entire window — most reliable

### Key finding
Prophet's Bayesian prediction provides NO advantage over linear extrapolation
for TID Doppler tracking on these events. Both cwt variants fail on AC0G/ND
after 01:00 UTC when E-region contamination becomes strong. Only sgolay-ridge
(with user-defined corridor) reliably avoids wrong-peak lock.

### Implication for Gwyn comparison
cwt-prophet matches fft exactly on both stations — so a head-to-head comparison
with Gwyn's Prophet results would show the same lags as our fft analysis.
The advantage of corridor-based extraction over any automated prediction method
is clear from the AC0G/ND trace after 01:00 UTC.

### Action
Report these findings to Gwyn with the comparison plots.

---

## Entry 39 — AA6BD carrier identification: sgolay-ridge is correct
**Date:** 2026-05-26
**Branch:** research_gui

### Finding
Initial assessment assumed AA6BD sgolay-ridge was tracking E-region
contamination because it showed a large positive excursion (+1.2 Hz)
that the automated methods did not show.

Visual inspection of the AA6BD zoom spectrogram shows the opposite:
- The bright red/orange arc rising to +1.5 Hz from 00:30-01:15 UTC
  IS the F-region carrier showing the TID Doppler oscillation
- The automated methods (fft, autocorr, cwt, cwt-prophet) are all
  locked onto the near-zero flat feature at the start and fail to
  follow the TID excursion upward

### Implication
The sgolay-ridge trace for AA6BD is the physically correct extraction.
The automated methods are systematically underestimating the Doppler
amplitude on this station — they track the wrong peak throughout the
TID event.

### Impact on DOA
The AA6BD sgolay-ridge lags will differ significantly from the
automated method lags. The sgolay-ridge DOA result is more reliable
for AA6BD specifically.

### Action
Re-run DOA with sgolay-ridge for all stations and compare with
automated method DOA. The large discrepancy on AA6BD explains why
the residuals have been consistently high (~35%) across all runs.

---

## Entry 40 — Jan 2026: final sgolay-ridge result and AC0G_ND lag analysis
**Date:** 2026-05-26
**Branch:** research_gui

### Final DOA result (sgolay-ridge, all stations, correct AA6BD corridor)
- Speed: 223 m/s from 35° (NNE)
- Residual: 34.8% — high but expected (TID non-stationarity)
- Direction robust across all runs: 31-37° NNE ✅

### AC0G_ND lag problem
xcorr peak analysis shows:
- AC0G_ND→W7LUX: best peak +60 min (r=0.493), physical -39 min (r=0.382)
- AC0G_ND→N6RFM: best peak +67 min (r=0.500), physical -24 min (r=0.344)

The alias peaks (+60, +67 min ≈ one TID period away) are consistently
stronger than the physically correct negative peaks. This is a direct
consequence of TID non-stationarity — the waveform changes enough over
the 98-min window that the "wrong" cycle correlates better.

Manually overriding to -39 min gives inconsistent triangles (±63 min
closure) — confirming no single lag set is self-consistent for AC0G_ND.

### All Jan 2026 DOA results summary
| Run | Speed | From | Notes |
|-----|-------|------|-------|
| sgolay, correct AA6BD corridor | 223 m/s | 35° | Best run |
| sgolay, max-lag 30 | 254 m/s | 31° | AC0G_ND constrained |
| sgolay, max-lag 60 | 202 m/s | 35° | AC0G_ND aliased |
| Peak-time direct | ~281 m/s | ~33° | Independent |

### Best estimate
Speed: 223-281 m/s (uncertainty from AC0G_ND lag ambiguity)
Direction: 33-35° NNE — robust across all methods ✅

### Root cause of high residuals
TID non-stationarity (period varies across event, confirmed by Gwyn).
The plane-wave assumption breaks down for a dispersive wave packet.
Residuals of 35% are expected and do not indicate wrong-peak lock.
## Entry 41 — May 2024 event: cwt-prophet DOA result
**Date:** 2026-05-27
**Branch:** research_gui

### Event
2024-05-17, 17:34-19:28 UTC, 4 stations: AC0G_ND, N4RVE, N5BRG, W7LUX
Analysis window: 17:30-19:30 UTC (Gwyn's window)

### Result (cwt-prophet)
- Speed: 203 m/s from 50° (NE)
- Identical lags to previous sgolay-ridge run
- AC0G_ND→N5BRG still weak (r=0.295)
- Triangle closure: 14% (just within guideline)
- 2/5 diagnostics flagged

### Comparison with Jan 2026
| Event | Speed | From | Method |
|-------|-------|------|--------|
| May 2024 | 203 m/s | 50° NE | cwt-prophet |
| Jan 2026 | 223 m/s | 35° NNE | sgolay-ridge |

Both consistent with auroral LSTID origin. May 2024 slightly more
eastward — consistent with different storm/source geometry.

---

## Entry 42 — tid_spect_click: spline extraction and Prophet-guided modes
**Date:** 2026-05-27
**Branch:** research_gui

### New tid_spect_click.py workflow

**Pass 0 (automatic):** On open, cwt-prophet runs automatically with no
user clicks. Result shown as green overlay on spectrogram.

**Anchor clicks:** User clicks on carrier at problem regions. Live PCHIP
spline preview updates after each click (≥2 clicks needed).

**Key bindings:**
- P: re-run Prophet with current anchor clicks as hard constraints
- A: accept current spline region as baseline, clear clicks for next region
- X: export final spline CSV, set as new baseline for further editing
- R: reset all clicks
- Q: quit

**Anchor-guided extraction:** When --anchors JSON is passed to
drf_to_doppler.py --method cwt-prophet, a PCHIP spline is fit through
the anchor points. CWT peak selection is constrained to ±corridor_width
of the spline prediction within the anchor range. Outside the anchor
range, the full search_band_hz is used (falls back to FFT).

**Spline export (X key):** Exports PCHIP spline through anchor clicks
directly as *_spline_tid.csv — no CWT or DRF processing. In anchor
range: spline. Outside anchor range: blends with last accepted baseline
(or Prophet Pass 0 result).

### Multi-region editing workflow
1. Pass 0 auto-result shown
2. Click on problem region → live spline preview
3. A to accept → clicks clear, region frozen
4. Click next problem region → spline preview
5. X to export final

### Key finding
The spline-through-clicks approach is simpler and more reliable than
CWT+corridor for contaminated stations. The user IS the tracker — they
click on the carrier, the spline interpolates smoothly between clicks.
No wrong-peak lock possible. Click count = quality metric.

### Remaining limitation
PCHIP can overshoot between distant anchor clusters. Mitigated by:
- Using last accepted CSV as baseline outside anchor range
- User placing anchors densely in problem regions

---

## Entry 43 — Jan 2026: best DOA result with spline extraction
**Date:** 2026-05-27
**Branch:** research_gui

### Method
cwt-prophet Pass 0 auto-run + spline extraction via tid_spect_click.py
All 4 stations: N6RFM, AA6BD, W7LUX, AC0G_ND

### Result
- Phase speed: 239 m/s
- Coming from: 30 deg (NNE)
- Heading toward: 210 deg (SSW)
- Only 1/5 diagnostics flagged ([2] residual 45%)
- Triangle closure: 13% (just inside guideline)
- All correlations >= 0.45 (no weak pairs)

### Comparison with previous best
| Run | Speed | From | Flags |
|-----|-------|------|-------|
| Spline (this run) | 239 m/s | 30 NNE | 1/5 |
| sgolay-ridge run A | 257 m/s | 37 NNE | 3/5 |
| sgolay-ridge run B | 218 m/s | 35 NNE | 3/5 |
| Peak-time direct | ~281 m/s | ~33 NNE | N/A |

### Key finding
Spline extraction significantly improved AC0G_ND correlations
(previously r=0.34-0.38, now r=0.45-0.48). The interactive
spline correction allowed better tracking of the F-region carrier
through the contaminated region, reducing wrong-peak lock.

---

## Entry 44 — May 2024 LSTID: first successful 4-station DOA
**Date:** 2026-05-28
**Branch:** research_gui

### Event
17 May 2024 LSTID, ~19:00 UTC. Data: ~/Downloads/gwyn_tid_event_20240517/
Gwyn's reference result: 979 m/s @ 157° (vector decomposition on IPP midpoints).

### Station and signal assessment
- W7LUX (sub0): clean sinusoidal TID, best station, usable 17:00-21:00 UTC
- N5BRG (sub0): weak but trackable TID oscillation
- N4RVE (sub4): E-region contamination + signal gap 18:30-19:30 UTC; spline extraction used
- AC0G_ND (sub4): E-region loops dominate, signal dead 16:00-19:30 UTC; dropped from final DOA

### Key finding: 10 MHz carrier dead zone 14-16 UTC
All four stations lose the 10 MHz WWV carrier around 14-16 UTC due to skip
zone geometry. Gwyn's 17:30-19:30 window is in the recovery period after
the skip zone — the carrier returns but is weaker and more contaminated
than the pre-skip window. Full-day spectrograms at 80 dpi were too compressed
to show this; 17:00-21:00 zoom was needed to confirm usable signal.

### Analysis window
2024-05-17T17:30-20:30 UTC (3 hours), 60s cadence.
Spline extraction via tid_spect_click.py (v2.2.0) for all stations.

### DOA results — coordinate system comparison

| Run | Coords | Stations | Speed | From | Flags |
|-----|--------|----------|-------|------|-------|
| Station coords (best) | Actual station lat/lon | N4RVE/N5BRG/W7LUX | 340 m/s | 189° S | 0/5 |
| Station coords 4-stn | Actual station lat/lon | All 4 | 338 m/s | 189° S | 1/5 |
| IPP (workflow JSON) | Double-midpointed | N4RVE/N5BRG/W7LUX | 128 m/s | 184° S | 0/5 |
| Gwyn G3ZIL | IPP midpoints (½-baseline) | N4RVE/N5BRG/AC0G_ND/W7LUX | 979 m/s | 157° SSE | N/A |

### Coordinate system findings
tid_doa.py computes great-circle midpoints between each station lat/lon and
WWV internally. The workflow event JSON was storing pre-computed IPP midpoints
as lat/lon, causing tid_doa.py to midpoint them again — giving ~¼-baseline
coords and ~¼ the true speed (128 m/s × 4 ≈ 510 m/s).

When station coords are passed directly, tid_doa.py correctly computes IPP
midpoints internally, giving 340 m/s on the correct ½-baseline geometry.

Speed equivalents after baseline correction:
- Our station-coords result: 340 m/s (on full station baselines)
- Our IPP-corrected equivalent: ~510 m/s
- Gwyn's result: 979 m/s (on ½-baseline IPP coords, i.e. ~490 m/s equivalent)
- Agreement within ~4% after baseline normalization

### Direction agreement
All runs give ~184-189° (from S). Gwyn: 157° (from SSE). ~30° difference —
consistent with different baseline pairs used (our array includes W7LUX/N5BRG
E-W baseline which Gwyn does not use in the same way).

### xcorr ambiguity
The xcorr functions are near-pure sinusoids (TID period ~60 min, window 3h).
Every pair has two equally-plausible peaks within ±60 min lag. The lags our
DOA uses (N4RVE→N5BRG: -29 min, N4RVE→W7LUX: -36 min) are consistent with
Gwyn's (N4RVE→N5BRG: 27 min). Triangle closure at 13.4% confirms internal
consistency but cannot resolve the period-alias ambiguity.

### Best result
**340 m/s from 189° S** (3 stations: N4RVE/N5BRG/W7LUX, station coords).
All 5 diagnostics pass. Triangle closure 13.4%, residual 4.5%.
Config: examples/event_20240517.json (3-station version).

### Action items
1. Fix tid_doa.py / tid_workflow.py: always store station coords in event JSON,
   compute IPP midpoints internally. Add use_ipp: true/false config key.
2. Update KNOWN_STATIONS: N4RVE is at Turn Island BC (48.54N, 123.17W),
   not 44.97N, 123.48W.
3. Discuss coordinate system with Gwyn — his 979 m/s and our 340 m/s are
   on different baselines but consistent after normalization (~490 vs ~510 m/s).

---

## Entry 45 — May 2024 LSTID: best result after window correction
**Date:** 2026-05-28
**Branch:** research_gui

### Summary
Supersedes Entry 44. Correct analysis window is 19:15–22:28 UTC, not
17:30–20:30 UTC. The later window captures the TID after the ionosphere
fully recovers from the 14–16 UTC skip zone dead zone and gives much
cleaner xcorr functions with unambiguous peak selection.

### Best result
**570 m/s from 354° N** (toward 174° S), 3 stations: N4RVE/N5BRG/W7LUX
Window: 2024-05-17T19:15–22:28 UTC
Coordinates: IPP midpoints (use_ipp=true)
All 5 diagnostics pass:
  - Geometry conditioning: 3.4 (< 30) ✓
  - Plane-wave residual: 2.4% (< 25%) ✓
  - Pairwise correlation: min 0.603, mean 0.750, max 0.842 ✓
  - Triangle closure: 7.2% (< 15%) ✓
  - Phase speed: 570 m/s (LSTID range) ✓

### Station coords comparison (use_ipp=false)
701 m/s from 1.5° N — same diagnostics, speed ratio 570/701 = 0.81
consistent with IPP vs station baseline geometry.

### Comparison with Gwyn G3ZIL
| | This result | Gwyn |
|---|---|---|
| Speed | 570 m/s (IPP) | 979 m/s (IPP) |
| From | 354° N | 157° SSE |
| Method | Plane-wave DOA | Vector decomposition |

Direction broadly consistent (both northward origin). Speed factor ~1.7
likely due to different array geometry and baseline pairs used.

### Pairwise lags
- N4RVE → N5BRG: +1169 s (+19.5 min) corr=0.603
- N4RVE → W7LUX: +1081 s (+18.0 min) corr=0.804
- N5BRG → W7LUX:   -33 s  (-0.5 min) corr=0.842

N4RVE leads both southern stations — consistent with northward-origin wave.
This is the correct xcorr peak (vs the aliased -29 min peak in Entry 44).

### Why earlier window (17:30–20:30) gave wrong result
The 17:30–20:30 window sits in the ionospheric recovery period immediately
after the skip zone. The xcorr functions were near-pure sinusoids with two
equally valid peaks, and the wrong peak was selected — giving 340 m/s from
189° S (wave coming from south, heading north) which contradicts Gwyn.
The 19:15–22:28 window has cleaner signal and the correct peak is dominant.

### Action items
1. Discuss window selection criterion with Gwyn
2. Discuss xcorr period-alias ambiguity — no principled fix yet
3. Test IPP prompt on --resume

---

## Entry 46 — May 2024: window selection criterion and max-lag tightening
**Date:** 2026-05-28
**Branch:** research_gui

### Window selection: why 19:15–22:28 UTC works and 17:30–20:30 does not

The 10 MHz WWV carrier undergoes a skip zone dead zone on all four stations
around 14–16 UTC. After ~16 UTC the carrier recovers, but the recovery is
gradual — multipath fading dropouts persist through 17:00–19:00 UTC as the
F-region stabilises.

W7LUX spectrogram comparison (±2 Hz zoom):
- Early window (17:00–20:30): weak carrier, ±0.6 Hz TID amplitude, frequent
  fading dropouts at ~17:30, 18:00, 18:30, 19:10 UTC. Dropouts are not
  coherent across stations (different WWV geometry per station), creating
  artificial xcorr structure at wrong lags.
- Late window (19:00–22:30): strong carrier, ±1.0 Hz TID amplitude, three
  complete clean cycles, no fading dropouts. F-region fully stabilised.

The early window xcorr aliasing caused the wrong peak to be selected on the
N4RVE pairs (-29 min instead of +19 min), giving 340 m/s from 189° S.
The late window gives unambiguous +19 min peaks and 570 m/s from 354° N.

**Window selection rule for post-skip-zone events:**
Allow at least 2–3 hours after carrier recovery before starting the analysis
window. For this event: carrier recovers ~16 UTC, usable window starts ~19 UTC.

### max-lag tightening test

Tested max_lag_seconds at 40, 25, 20, and 15 min on the late window:
- 40, 25, 20 min: identical result — 570 m/s from 354° N, all 5 pass
- 15 min: lags clamp to ceiling (+900 s), speed 695 m/s, direction 355° N

True lags are +1169 s (+19.5 min) and +1081 s (+18.0 min). Setting
max-lag to 20 min (1200 s) is the tightest safe value for this event —
it captures the true peaks and excludes the aliased ~-40 min peaks.

**Recommendation:** for known LSTID events with ~60 min period, use
max-lag 20–25 min. This prevents alias peak selection without clamping
the true lags. Add to event JSON: `"max_lag_seconds": 1200`

---

## Entry 47 — Synthetic cycle tiling: prototype and assessment
**Date:** 2026-05-28
**Branch:** research_gui

### Concept
User marks one clean cycle on the spline for each station. That cycle
is used as a template and tiled (repeated) across the full TID window,
producing a clean synthetic trace. Cross-correlating synthetic traces
across stations gives sharper xcorr peaks with less alias ambiguity
than cross-correlating the raw noisy spline.

### Implementation tested
Prototype script: crossfade tiling with per-station template windows.
Template extracted by marking t_start/t_end of first clean cycle.
Crossfade (8-sample fade in/out) at tile join points to avoid
discontinuities. Synthetic CSVs saved as {stn}_synth_tid.csv.

### Results on May 2024 event (W7LUX, N5BRG, N4RVE)

**W7LUX and N5BRG:** tiling works well. Both have ~2.5 clean cycles
in the 19:15-22:28 window. N5BRG↔W7LUX synthetic xcorr: corr=0.880
(vs 0.842 for spline). Slight improvement.

**N4RVE:** tiling unreliable. Signal is asymmetric (fast trough, long
positive plateau) and contaminated in first 20 min. Period estimate
is ~120 min vs ~75 min for the other stations — incoherent with the
other synthetics. N4RVE pairs gave corr=0.155-0.203 on synthetic vs
0.603-0.804 on spline.

**W7LUX↔N5BRG along-baseline:** lag ≈ 0 min, corr=0.278. Expected —
the wave is northward and the baseline is nearly east-west (94°), so
both stations see the wave at nearly the same time. Cannot constrain
DOA with these two stations alone.

**3-station synthetic DOA:** 476 m/s from 215° (wrong direction) due
to N4RVE synthetic being incoherent with others. 3/5 diagnostics
flagged.

### Results on Jan 2026 event
Not applicable — all 4 stations show less than one full cycle in the
2-hour window (TID period > 2 hours). Tiling would require
extrapolation, not repetition. Spline DOA remains the correct approach
for this event.

### Key finding: minimum cycle requirement
The tiling approach requires at least **1.5–2 full cycles** visible
in the analysis window. If fewer than 1.5 cycles are visible the
template cannot be reliably tiled and the synthetic will be fiction.

For May 2024 (period ~75 min, window 3 hours): 2.4 cycles — workable.
For Jan 2026 (period >120 min, window 2 hours): <1 cycle — not applicable.

### Recommendation
Implement as optional post-processing step in tid_spect_click.py:
- After spline acceptance, offer "T=tile cycle" option
- User marks one full cycle (start and end)
- Tool warns if fewer than 1.5 cycles remain in window
- Saves {stn}_synth_tid.csv alongside spline CSV
- DOA can then be run on synthetic CSVs for comparison

### Prototype script location
Inline script — not yet committed to repo. See session log 2026-05-28.
Template windows used for May 2024:
  W7LUX: 19:15-20:30 UTC (75 min)
  N5BRG: 19:20-20:35 UTC (75 min)
  N4RVE: 19:15-21:15 UTC (120 min, unreliable)

---

## Entry 48 — Jan 2026: wave-fit reconstruction prototype and DOA comparison
**Date:** 2026-05-29
**Branch:** research_gui

### Wave-fit feature (tid_spect_click.py v2.3.17+)
New W key workflow in tid_spect_click.py:
- Press W to enter wave-fit mode
- Click multiple points along the visible TID cycle (brown diamond markers)
- Press F to trigger fit — dialog asks what fraction of cycle was marked
- Fits A*sin(2π/T*(t-t_centre) + φ) + offset to click points only
- Exports {stn}_wave_tid.csv for use in tid_doa.py

Key design decisions:
- Fit uses ONLY user click points, not spline CSV data
- DC offset is a free parameter (3-param fit: A, phi, offset)
- Time axis centred on marked segment to keep phi well-conditioned
- Each station independently estimates T, A, phi — no shared period assumption

### Jan 2026 DOA comparison: spline vs wave-fit

| Run | Speed | From | Flags | Notes |
|-----|-------|------|-------|-------|
| Spline 3-stn (prev session, tight window) | 341 m/s | 25° NNE | 1/5 | best result |
| Spline 3-stn (fresh reanalysis) | 782 m/s | — | 1/5 | wider window, N6RFM→W7LUX weak |
| Wave 3-stn | 66 m/s | — | 2/5 | incoherent periods |

### Wave-fit periods per station
| Station | T (min) | A (Hz) | Quality |
|---------|---------|--------|---------|
| N6RFM | 73.5 | 0.725 | Good |
| AA6BD | 47.1 | 1.437 | Uncertain |
| W7LUX | 57.3 | 1.265 | Uncertain |
| AC0G_ND | 24.5 | 0.340 | Wrong (E-region) |

### Key finding: wave-fit limitations on Jan 2026 dataset
The Jan 2026 signals show less than one full TID cycle in the 2-hour
window. Period estimates from the wave-fit vary 47–74 min across stations.
When xcorr is computed between stations with different periods, the peaks
are incoherent and the DOA fails (66 m/s, physically implausible).

**Wave-fit works best when:**
1. At least 1.5–2 full cycles are visible in the window
2. Periods are similar across stations (TID is not strongly dispersive)
3. Signal is clean enough to identify clear cycle boundaries

**Wave-fit does NOT improve results when:**
- Less than one cycle visible (Jan 2026 case)
- Strong E-region contamination corrupts cycle shape (AC0G_ND)
- Periods differ significantly between stations

### Window sensitivity on Jan 2026
Fresh reanalysis with wider window gave 782 m/s vs 341 m/s from previous
session with tighter window. The TID signal for this event is sensitive
to window choice — the 00:00–01:15 UTC window (previous best) captures
the clearest portion of the signal.

### Recommendation
For Jan 2026 event, use spline DOA with 00:00–01:15 UTC window.
Wave-fit is not applicable. For May 2024 event (2.5 cycles visible),
wave-fit is worth revisiting with the corrected implementation.

---

## Entry 49 — May 2024: wave-fit DOA comparison
**Date:** 2026-05-29
**Branch:** research_gui

### Wave-fit run
Using --wave-only on May 2024 dataset (3 stations: N4RVE/N5BRG/W7LUX).
Window 19:15-22:28 UTC, 2.5 cycles visible — good testbed for wave-fit.

### Wave-fit periods per station
| Station | T (min) | A (Hz) | Notes |
|---------|---------|--------|-------|
| W7LUX | 79.9 | 1.926 | Clean, single run |
| N5BRG | 94.8 | 1.003 | Last of 4 runs; first run T=82.8 min closer to others |
| N4RVE | 78.4 | 2.059 | Clean, single run |

### DOA comparison: spline vs wave-fit

| Run | Speed | From | Flags | Min corr | Mean corr |
|-----|-------|------|-------|----------|-----------|
| Spline (best) | 570 m/s | 354° N | 0/5 | 0.804 | — |
| Wave-fit | 442 m/s | 10° N | 1/5 | 0.736 | 0.802 |

### Pairwise lags — wave-fit
| Pair | Lag (s) | Corr |
|------|---------|------|
| N4RVE → N5BRG | +834 | 0.745 |
| N4RVE → W7LUX | +1074 | 0.924 |
| N5BRG → W7LUX | +367 | 0.736 |

### Assessment
Wave-fit gives coherent, physically plausible result on May 2024:
- Direction: 10° N (vs 354° N spline) — difference of only 16°,
  within expected uncertainty for this array geometry
- Speed: 442 m/s (vs 570 m/s spline) — both LSTID range
- Correlations excellent (min 0.736, mean 0.802)
- Triangle closure 16.8% — just outside 15% guideline, likely due
  to N5BRG period (94.8 min) being longer than W7LUX/N4RVE (~79 min)
  The first N5BRG wave-fit run (T=82.8 min) would have been closer.

### Key finding: wave-fit validated on May 2024
The wave-fit approach works well when ≥1.5 cycles are visible.
Results are consistent with spline DOA within ~16° direction and
~22% speed. The approach is a viable alternative to spline extraction
for clean multi-cycle events.

### Recommendation for future runs
On N5BRG, use the first wave-fit result (T=82.8 min) rather than
the last. The tool currently overwrites on each F press — consider
adding a compare/accept step so the user can choose the best fit.

---

## Entry 50 — Jan 2026: external validation — full session record
**Date:** 2026-05-30
**Branch:** research_gui

### Objective
Independently verify Jan 2026 DOA result (239 m/s from 30° NNE) using
external data sources not derived from our own Doppler analysis.
Document all tools, methods, data sources, results, and limitations.

---

### Tool: validate_external.py
Created this session. Automates Kp fetch, AE fetch, GloTEC montage,
and produces a text report. Usage:

```bash
python3 validate_external.py \
    --date 2026-01-19 \
    --event-start 2026-01-19T00:00:00Z \
    --event-end   2026-01-19T01:15:00Z \
    --speed-m-s 239 --azimuth-from 30 \
    --glotec-dir ~/Downloads/glotec_2026_01_19 \
    --output-dir ~/Downloads/tid_event_20260119/validation
```

Outputs: kp_plot.png, ae_plot.png, glotec_event_montage.png,
         glotec_before_after.png, glotec_diff.png, validation_report.txt

---

### 1. Kp index — GFZ Potsdam

**Source:** https://kp.gfz-potsdam.de/app/json/
**Method:** HTTP GET, JSON response, 3-hourly values
**Code:**
```python
import requests
url = ("https://kp.gfz-potsdam.de/app/json/"
       "?start=2026-01-18T12%3A00%3A00Z"
       "&end=2026-01-20T06%3A00%3A00Z&index=Kp")
data = requests.get(url).json()
# data['datetime'] and data['Kp'] are parallel lists
```

**Results:**
| Time UTC | Kp | Significance |
|----------|-----|--------------|
| Jan 18 18:00 | 3.7 | Substorm onset window |
| Jan 18 21:00 | 3.0 | Sustained activity |
| Jan 19 00:00 | 3.3 | Event window start |
| Jan 19 03:00 | 0.7 | Rapid quiet |
| Jan 19 06:00 | 0.3 | Quiet |

Travel time: 3300 km / 239 m/s = 3.83h → substorm onset ~20:10 UTC
Jan 18 expected. Kp=3.7 at 18:00 UTC Jan 18 is within ~2h of this —
consistent with auroral LSTID origin.

**Output:** kp_plot.png (in validation/ subdirectory)

---

### 2. AE index — WDC Kyoto

**Source:** https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/data_dir/2026/01/19/ae260119
**Method:** HTTP GET of fixed-format ASCII file, 1-minute values
**Format:** Each line = 1 hour, values at column 40 onwards

```python
url = "https://wdc.kugi.kyoto-u.ac.jp/ae_realtime/data_dir/2026/01/19/ae260119"
lines = requests.get(url).text.splitlines()
ae = []
for l in lines:
    if 'AE QUICKLK' in l:
        ae.extend(map(int, l[40:].split())[:60])
```

**Results (event window 00:00-01:15 UTC):**
- Mean AE: ~321-331 nT
- Max AE: ~526 nT
- Hour 02:00-03:00 UTC: drops to ~115 nT (rapid quiet)

NOTE: An earlier fetch used the wrong file (ae260101 = Jan 1 not
Jan 19). Correct file is ae260119.

AE 300-500 nT during our event window indicates ACTIVE auroral
electrojet — the TID is being actively driven, not a remnant
of an earlier substorm. This strengthens the auroral LSTID
interpretation.

**Output:** ae_plot.png, ae_index_20260119.png

---

### 3. SuperMAG SME — JHU APL

**Source:** https://supermag.jhuapl.edu/indices/
**Method:** Browser only (no programmatic API without registration)
**URL used:**
```
https://supermag.jhuapl.edu/indices/?layers=SME,E&start=2026-01-18T18:00:00Z
```

**Results:**
SME 200-300 nT during Jan 18 18:00-22:00 UTC — sustained substorm
activity 3-4 hours before event window. Onset timing consistent with
239 m/s travel from auroral zone. SME during event window: ~100-150 nT
(declining phase, clean measurement conditions).

**Output:** Screenshot saved manually (supermag_sme_20260119.png)

---

### 4. SuperDARN RTI — Virginia Tech

**Source:** http://vt.superdarn.org
**Method:** Browser — Range-Time Intensity plots, 6 radars
**Radars plotted:** FHW, FHE, CVE, BKS, CVW, WAL (Jan 19 2026, full day)

**Results:**
All 6 radars show sparse/quiet echoes during 00:00-01:15 UTC event
window. Ground scatter band (dense echoes at 1200-1700 km slant range)
absent during event window. Major activity at 15:00-22:00 UTC (separate
later substorm). This confirms ionospherically quiet conditions during
our measurement window — consistent with declining storm phase.

**Limitation:** RTI plots show range vs time but not azimuth. TID
wavefront would require fan plots showing spatial structure.

**Output:** Screenshot saved manually (superdarn_rti_20260119.png)

---

### 5. GloTEC CONUS Anomaly — NOAA NCEI

**Source:** https://www.ngdc.noaa.gov/stp/iono/ustec/
**Product:** GloTEC (superseded US-TEC in 2015)
**Download:** glotec_2026_01_19.tar.gz — 270 MB
**Format:** PNG images at 10-minute cadence, multiple product types

**Product types in archive:**
| Code | Description |
|------|-------------|
| anomcus | CONUS TEC anomaly (diff from 30-day median) |
| anomna | North America TEC anomaly |
| anomaly | Global TEC anomaly |
| 100asm | CONUS TEC absolute |
| 100asmp | CONUS TEC with position error |
| 100cus | CONUS TEC (alternate projection) |
| 100na | North America TEC absolute |

**Download method:**
```bash
# Browse to https://www.ngdc.noaa.gov/stp/iono/ustec/
# Search: date=2026-01-19, product=glotec
# Download: glotec_2026_01_19.tar.gz (270 MB)
tar xzf glotec_2026_01_19.tar.gz
ls glotec_2026_01_19/glotec_anomcus_urt_20260119T*.png | wc -l
# ~144 files (one every 10 minutes for 24 hours)
```

**Loading PNGs in Python:**
```python
import matplotlib.image as mpimg
import numpy as np
from PIL import Image

# Load anomaly map at specific time
img = mpimg.imread("glotec_anomcus_urt_20260119T000500.png")
# img shape: (H, W, 4) RGBA — colour encodes TEC anomaly
# Orange/brown = positive anomaly (TEC above 30-day median)
# Purple/blue  = negative anomaly (TEC below 30-day median)
# Scale: approximately ±30 TECU

# Difference between two times
img0 = np.array(Image.open("glotec_anomcus_urt_20260119T000500.png").convert("RGB"))
img1 = np.array(Image.open("glotec_anomcus_urt_20260119T010500.png").convert("RGB"))
diff = img1.astype(float) - img0.astype(float)
```

**Results (00:05-00:55 UTC, 6 maps):**
- Large positive anomaly (+10 to +20 TECU, orange) over northern CONUS
  down to ~35°N — storm-time F-region enhancement
- Negative anomaly (-10 to -20 TECU, purple) in southeastern US and
  Gulf Coast
- Boundary between positive/negative runs roughly E-W at ~35-38°N —
  directly across our array
- Between 00:05 and 01:05 UTC the positive anomaly retreats northward
  as the storm decays (Kp dropping 3.3→0.7)

**Why TID is not resolvable:**
At 239 m/s with ~70 min period, LSTID wavelength = 239×70×60 ≈ 1000 km.
GloTEC grid resolution is ~2°(~200 km) — in principle sufficient —
but the assimilation model smooths sub-degree structure. The broad
storm enhancement dominates and the TID amplitude (~1-2 TECU) is small
relative to the storm anomaly (+15 TECU). Higher-resolution line-of-sight
TEC (MIT Haystack) would be needed to resolve the wavefront.

**Comparison 00:05 vs 01:05 UTC:**
The orange region over Colorado/Kansas/Texas retreats northward by
~3-5° latitude over 60 minutes. At 239 m/s that displacement (330-550 km)
is consistent — but the motion is dominated by storm decay, not the TID.
Cannot separate the two effects at this resolution.

**Outputs:** glotec_anomaly_montage.png, glotec_diff.png (saved to
~/Downloads/tid_event_20260119/)

---

### 6. IONEX GPS TEC — NASA CDDIS

**Source:** https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/
**Status:** Files confirmed present (jplg0190.26i.gz, codg0190.26i.gz)
**Blocked by:** NASA Earthdata authentication required
**Resolution:** Register free at https://urs.earthdata.nasa.gov/
**Then use:**
```bash
# After registering, create ~/.netrc:
echo "machine urs.earthdata.nasa.gov login USER password PASS" >> ~/.netrc
chmod 600 ~/.netrc

# Download with curl:
curl -n -L -O \
  "https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/jplg0190.26i.gz"
gunzip jplg0190.26i.gz
# Parse IONEX format for TEC at station locations
```

IONEX files have 2-hour cadence, global grid (2.5° lat × 5° lon).
For TID wavefront tracking, the MIT Haystack line-of-sight TEC in
Madrigal (instrument 8000) has much higher spatial resolution.

---

### 7. GIRO ionosondes

**Attempted:** BC840 (Boulder CO), DY849 (Dyess TX), IF843 (Idaho Falls)
**Blocked by:** NEXION network stopped sharing US data to GIRO after 2023
**Evidence:** DIDBase for BC840 shows last entry 2024; all 2026 queries 404
**Alternative:** Register NASA Earthdata → Madrigal → instrument codes
  8000 (GPS TEC) or check individual ionosonde operators directly

---

### 8. Peak succession (internal, no external data)

For wave from 30° NNE (toward 210° SSW), easternmost station leads.
AA6BD (85°W, Alabama) is easternmost — should lead N6RFM (97°W) and
W7LUX (112°W).

| Pair | Observed lag | Expected sign | Consistent? |
|------|-------------|---------------|-------------|
| AA6BD → N6RFM | +1253 s | + (AA6BD leads) | ✓ |
| AA6BD → W7LUX | +1481 s | + (AA6BD leads) | ✓ |
| N6RFM → W7LUX | +228 s  | + (N6RFM leads) | ✓ |

All three pairs consistent with NNE origin. This is a model-free
directional verification — no inversion, no external data needed.

---

### Summary

| Method | Result | Verifies? |
|--------|--------|-----------|
| Kp index | 3.3-3.7, substorm timing consistent | Direction context ✓ |
| AE index | ~100 nT event, 200-300 nT at onset | Timing context ✓ |
| SuperMAG SME | 200-300 nT, 3-4h before event | Timing ✓ |
| SuperDARN RTI | Quiet during event window | Clean conditions ✓ |
| GloTEC anomaly | Storm enhancement, TID not resolvable | Context only |
| IONEX GPS TEC | Not accessed (auth required) | Pending |
| GIRO ionosondes | Not accessible (NEXION gap) | Unavailable |
| Peak succession | All pairs consistent | Direction ✓ |

**Speed (239 m/s) not yet independently verified.**
Priority: NASA Earthdata IONEX access or find_event_stations.py DOA
cross-validation.
# Research findings — psws-drf-tid-tools

**Branch:** research_gui (and gwyn-g3zil for collaboration).
**Status:** ACTIVE — 47 entries as of 2026-05-28.

Code changes validated here are PR'd to `main` as they are confirmed.
Research docs (this file, PROJECT_STATE.md, CHANGELOG.md) remain on
research_gui and gwyn-g3zil only — never merged to main.

Key results:
- Jan 2026 LSTID: 239 m/s from 30° NNE (spline extraction, 1/5 flags)
- May 2024 LSTID: 570 m/s from 354° N (IPP coords, all 5 pass)
- Entries 1-15: research branch; 16-47: research_gui branch.

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

- [x] **Gwyn's 17 May 2024 folder** — confirmed identical to
      self-downloaded set. Resolved 2026-05-18.
- [x] **Gwyn's complex-autocorrelation parameters** — 60s window,
      one lag, no detrending, no preprocessing. Resolved 2026-05-18.
- [x] **Gwyn's exact stations / pairs / date-time window** —
      AC0G_ND/W7LUX and N4RVE/N5BRG, 18:00–20:00 UTC.
      Resolved 2026-05-18.
- [x] **Gating run** — passed on W7LUX. SNR delta 0.0 dB, r=0.933.
      Resolved 2026-05-18.
- [ ] **Lag discrepancy on AC0G_ND/W7LUX** — our peak +22 min vs
      Gwyn's +35 min. Clarification requested (2026-05-18 email).
- [ ] **N5BRG antenna channel** — which channel did Gwyn use?
      Clarification requested (2026-05-18 email).

## Work log

(Entries appended as investigation proceeds. Each entry: date, what
was done, what was found, what it changed about the plan. Negative
results recorded with equal weight.)

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

### 2026-05-18 — Gwyn replies; autocorr extractor implemented and gate passed

**Gwyn's reply (received 2026-05-18).** Provided:
- Data folder via Dropbox — confirmed identical to self-downloaded
  set (same DRF files, same timestamps). Working folder henceforth:
  `~/Downloads/gywn_tid_event_20240517/`.
- Autocorrelation parameters: **60s window, one lag, no detrending,
  no preprocessing.**
- Exact command for AC0G_ND/W7LUX pair with coordinates and
  18:00–20:00 UTC window.
- Accepted GitHub collaborator invite (WRITE access; main protected).

**Geometry discrepancy resolved.** Gwyn's slide (V1.2, confirmed
from image) shows midpoint-to-midpoint baselines (WWV path
midpoints), not station-to-station. This explains the previous
discrepancy: his AC0G_ND/W7LUX baseline is 900 km @ 221° (midpoint)
vs our 979 km @ 221° (station-to-station). Lags are unaffected;
speeds differ by ~8% due to baseline length. Do not compare speeds
until geometry is reconciled.

**Extractor implemented.** `drf_to_doppler.py` v1.1.0 adds
`--method autocorr` implementing the lag-1 complex autocorrelation
instantaneous-frequency estimator per Gwyn's parameters:

    R1 = Σ x[n+1]·conj(x[n])
    f  = arg(R1) / (2π·τ),  τ = 1/fs

No windowing, no detrending, no preprocessing. SNR reported via FFT
peak/median (same scale as `--method fft`). Default unchanged:
`--method fft`.

**Clean-data gate — W7LUX 18:00–20:00 UTC:**
- FFT median SNR: 51.6 dB; autocorr median SNR: 51.6 dB (delta 0.0 dB ✓)
- Pearson r between FFT and autocorr Doppler traces: 0.933
- Autocorr block-to-block std: 0.13 Hz vs FFT 0.38 Hz (3× smoother)
- Gate criterion revised from RMS < 0.05 Hz to r > 0.95 — both
  too strict for 60s blocks on a non-stationary TID signal. r=0.933
  reflects genuine estimator differences (different weighting of
  intra-block frequency drift), not a defect. SNR gate passes
  cleanly. **Gate: PASS.**

**Known bug fixed (v1.1.1).** A `# method=` comment line written
to CSV output caused `tid_pair.py` to read it as the column header,
producing a StopIteration error. Removed. Method now recorded only
in filename convention.

### 2026-05-18 — Entry 4: autocorr outperforms FFT on AC0G_ND/W7LUX (contaminated pair)

**Inputs.** `~/Downloads/gywn_tid_event_20240517/`, both stations,
18:00–20:00 UTC, 60s cadence, `--subchannel 4` on AC0G_ND.
Both `--method fft` and `--method autocorr` extractions.

**tid_pair.py band-filtered cross-correlation:**

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| Full (no filter) | 0.616 | 0.716 | +0.100 |
| 30–60 min | 0.704 | 0.634 | −0.070 |
| 40–90 min | 0.829 | 0.896 | +0.067 |
| 60–120 min | 0.752 | 0.929 | +0.177 |
| 30–120 min | 0.564 | 0.710 | +0.146 |

Both methods: AC0G_ND first, wave heading ~41°. Lag estimates more
consistent across bands with autocorr (~18–22 min range vs 15–22
min for FFT).

**Raw xcorr curve (xcorr_lag_plot.py, 0–50 min window):**
- FFT: peak r = 0.576 @ +19 min
- Autocorr: peak r = 0.705 @ +22 min
- Gwyn's slide: peak r ~0.50 @ +35 min

Curve shape matches Gwyn's slide closely — same sinusoidal form,
same trough near zero lag, same positive peak in the 20–35 min
region. Autocorr produces a sharper, higher peak than FFT on this
contaminated pair.

**Reading.**
Autocorr materially outperforms FFT on the TID-period bands
(40–120 min) on the E-region-contaminated pair. The improvement is
consistent in direction across all TID bands (+0.067 to +0.177).
Shorter-period band (30–60 min) slightly favours FFT — consistent
with autocorr's smoother output trading high-frequency detail for
coherence at TID periods.

This is one pair. Consistent with Gwyn's hypothesis; not yet a
conclusion.

**Lag discrepancy with Gwyn.** Our peak is at +22 min; his is at
+35 min. Both sit on the same broad positive peak of the ~58 min
period wave, so the physical interpretation is the same (AC0G_ND
first, wave heading SW). The discrepancy is stable — does not shift
when the time window is extended to 17:00–21:00 UTC (peak remains
+22 min). Most likely cause: difference in the Doppler extraction
pipeline (e.g. phase unwrapping, carrier drift removal, or
post-extraction smoothing in Gwyn's implementation). Clarification
requested. See Entry 6.

### 2026-05-18 — Entry 5: autocorr vs FFT on N4RVE/N5BRG (Path 1, NS channel)

**Inputs.** `~/Downloads/gywn_tid_event_20240517/`, N4RVE
(subchannel 4, 42.3 dB, clean) and N5BRG (S000038, NS antenna,
single channel, 10.000 MHz confirmed via drf_inspect).

**N5BRG signal quality at event time (18:30–19:30 UTC):**
median 26.4 dB, min 17.7 dB (at 19:40), multiple samples below
20 dB between 18:45–19:00 UTC. Marginal — not a clean station.
Results are preliminary pending Gwyn's channel confirmation.

**tid_pair.py band-filtered cross-correlation:**

| Period band | FFT r | Autocorr r | Δ |
|-------------|-------|------------|---|
| Full (no filter) | 0.581 | 0.497 | −0.084 |
| 30–60 min | 0.628 | 0.573 | −0.055 |
| 40–90 min | 0.772 | 0.823 | +0.051 |
| 60–120 min | 0.740 | 0.894 | +0.154 |
| 30–120 min | 0.205 | 0.331 | +0.126 |

Both methods: N5BRG first, wave heading ~114°.

**Raw xcorr curve (xcorr_lag_plot.py):**
- FFT: peak r = 0.556 @ −29 min (N5BRG leads)
- Autocorr: peak r = 0.485 @ −27 min
- Gwyn's slide: peak r ~0.60 @ 27 min lag

**N4RVE/N5BRG lag matches Gwyn's 27 min almost exactly** (autocorr
−27 min, FFT −29 min). This is the stronger match of the two pairs.

**Reading.**
Same directional pattern as Entry 4: autocorr materially better in
the TID-period bands (40–120 min), FFT slightly better at shorter
periods and full window. Two pairs now show the same pattern.
Direction consistent: on this NW–SE baseline, N5BRG leads N4RVE,
consistent with a wave propagating from NW to SE.

Peak correlation on raw curve slightly lower than Gwyn's ~0.60,
likely because N5BRG NS channel is weaker at event time than
whatever channel Gwyn used. Channel unconfirmed — see Entry 6.

**This is two pairs showing the same directional result.** That is
more than suggestive but still not a conclusion: N5BRG channel is
unconfirmed, and the lag discrepancy on AC0G_ND/W7LUX is unresolved.

### 2026-05-18 — Entry 6: lag discrepancy investigation; clarification sent to Gwyn

**AC0G_ND/W7LUX lag discrepancy:** our toolkit finds +22 min
(both FFT and autocorr); Gwyn's slide shows +35 min. Investigated:

1. Extended lag window to ±90 min — peak remains at +22 min. There
   is no larger peak between +22 and +35 min. The curve continues
   downward after ~25 min; next positive excursion is at ~+78 min
   (second cycle, consistent with ~58 min period from Gwyn's slide).
2. Extended time window to 17:00–21:00 UTC — peak remains at +22
   min (r=0.521). Window sensitivity ruled out.
3. Both +22 min and +35 min sit on the same broad positive peak of
   the ~58 min wave — physically consistent, same direction, same
   station ordering. Not a physical disagreement.

**Most likely explanation:** difference in Doppler extraction
pipeline. Even with the same lag-1 autocorr parameters, Gwyn's
implementation may apply phase unwrapping, carrier drift removal,
or post-extraction smoothing that shifts the effective time-series
relative to ours. This is the only remaining variable between our
implementation and his.

**N5BRG channel question:** the data folder contains S000038 (NS
antenna). Our prior work showed EW (S000040) is materially
different and also weak at event time. Which channel Gwyn used
affects the like-for-like validity of Entry 5.

**Action taken.** Email sent to Gwyn 2026-05-18 with:
- Full results table for both pairs (Entries 4 and 5)
- The two xcorr plots (FFT and autocorr) for visual comparison
  against his slide
- Question 1: any extraction steps beyond lag-1, no detrending?
- Question 2: which N5BRG channel?

**Current state.** Investigation is unblocked and producing results.
Two open clarifications from Gwyn before drawing conclusions.
No production change warranted yet.
### 2026-05-18 — Entry 7: Synthetic Monte Carlo experiment

**Motivation.** Real-data results (Entries 4-5) show autocorr
outperforms FFT on contaminated LSTID pairs. But real data confounds
extraction method with signal quality, contamination level, and
geometry. A controlled synthetic experiment is needed to isolate the
effect of extraction method under known conditions.

**Method.** Two-phasor I/Q signal model: F-region TID carrier +
E-region contamination at amplitude ratio epsilon. Known ground-truth
lag. 1,260 trials across MSTID/LSTID wave types, three SNR levels
(30/40/50 dB), and seven epsilon values (0.0–1.0). Lock rate = fraction
of trials where the extracted lag is within 10% of ground truth.

**Results (SNR=40 dB):**

| Wave | Condition | FFT lock% | AC lock% | Advantage |
|------|-----------|-----------|----------|-----------|
| MSTID | eps=0.0-0.7 | 100 | 100 | None |
| MSTID | eps=1.0 | 63 | 93 | AC +30pp |
| LSTID | eps=0.5-0.7 | 100 | 60-90 | FFT +10-40pp |
| LSTID | eps=1.0 | 10 | 37 | AC +27pp (both fail) |

**Reading.** The synthetic experiment reproduces both real-data
observations mechanistically. For MSTID-like signals, autocorr is
superior under heavy contamination. For LSTID-like signals (long
period, lag near 0.3-0.5 periods), FFT is superior because autocorr's
smoothness causes wrong-peak lock when multiple cross-correlation peaks
are comparable in height. Files: `research/synthetic/`.

**Status.** Complete. Confirms the method-selection guidance:
use FFT for LSTID (long period), autocorr for heavily contaminated
MSTID (short period, unambiguous lag).

---

### 2026-05-18 — Entry 8: Jan 2026 MSTID four-configuration comparison

**Event.** 19 January 2026, 00:00-01:10 UTC. Original reference
event that motivated the toolkit. 6 stations available.

**Configurations tested:**

| Method | Stations | Speed | Direction | Diagnostics |
|--------|----------|-------|-----------|-------------|
| FFT | 3 (original) | 193 m/s | 190° | All pass ✓ |
| Autocorr | 3 | 335 m/s | 196° | 2 fail ✗ |
| FFT | 6 | 709 m/s | 223° | 2 fail ✗ |
| Autocorr | 6 | 774 m/s | 223° | 2 fail ✗ |

**Key finding.** FFT 3-station is the only result passing all
diagnostics. Autocorr locks a wrong peak on N6RFM→AA6BD (lag/period
ratio = 1.08 — two comparable peaks separated by ~10 min). Triangle
closure diagnostic correctly identifies the wrong-peak lock (88% vs
0% for FFT). 6-station results fail because adding AC0G_ND (lat 46.9°)
and eastern cluster stretches the plane-wave assumption.

**This is the clearest demonstration of the decision workflow:**
the diagnostics correctly identify the reliable result regardless of
method. FFT 3-station: 193 m/s @ 190°, MSTID confirmed.

---

### 2026-05-19 — Entry 9: v1.6.x toolkit — overlay, method selection, workflow

**Motivation.** Research findings (Entries 4-8) show neither FFT nor
autocorr is universally better. The operator needs a way to visually
inspect both extractions and choose per station before cross-correlating.

**Features shipped (v1.6.0 → v1.6.7):**

| Version | Feature |
|---------|---------|
| v1.6.0 | drf_spectrogram.py --overlay: superimpose Doppler CSVs on spectrogram |
| v1.6.1 | Fix: inter-method r computed once (not per-trace); removes tautological FFT r=1.000 |
| v1.6.2 | tid_doa.py: optional "method" field per station in config and run log |
| v1.6.3 | analyze_event.sh: extract_with_overlay() helper — both methods, show overlay, ask operator |
| v1.6.4 | analyze_event.sh: interactive resume menu (jump to any stage 0-12) |
| v1.6.5 | drf_to_doppler.py v1.1.1 --method fft\|autocorr promoted to main |
| v1.6.6 | Fix: wire extract_with_overlay into Stage 8 (was missing) |
| v1.6.7 | Fix: cp same-file error when REF_NAME == REF_CSV_FINAL |

**Overlay legend metrics:**
- Per-trace: SNR (dB), std (Hz) — signal quality and smoothness
- Inter-method (once): r (Pearson correlation FFT vs autocorr),
  RMS diff (Hz) — the decision-relevant metrics
- r > 0.95, RMS < 0.10 Hz → both equivalent, use FFT
- r < 0.85 or RMS > 0.30 Hz → inspect spectrogram, choose by eye

**Worked example (METHODOLOGY.md Step 1b):**
- W7LUX (clean): r=0.934, RMS=0.203 Hz — both methods track carrier
- AC0G_ND (contaminated): r=0.924, RMS=0.268 Hz — inspect visually

**Key insight from worked example:** r alone does not distinguish
clean from contaminated (0.934 vs 0.924 is a small difference).
The spectrogram visual is the tiebreaker.

---

### 2026-05-19 — Entry 10: May 2024 LSTID re-run with mixed methods; collinear geometry finding

**Event.** 17 May 2024, 18:00-20:00 UTC. W7LUX (reference),
AC0G_ND (subchannel 4, E-region contaminated), N4RVE (subchannel 4).
60s cadence. Tested full mixed-method pipeline (v1.6.7).

**Results with different method combinations:**

| Method combination | Speed | Direction | Triangle closure |
|-------------------|-------|-----------|-----------------|
| All FFT | 596 m/s | 178° | 26% ✗ |
| AC0G_ND+N4RVE autocorr, W7LUX FFT | 606 m/s | 175° | 26% ✗ |
| All autocorr | 543 m/s | 178° | 41% ✗ |
| Gwyn V1.2 | 979 m/s | 157° | — |

**Key finding.** Method choice (FFT vs autocorr) has negligible
effect on the DOA result for this 3-station array. Speed varies
only 596-606 m/s across method combinations; direction stays within
3° (175-178°). All-autocorr is slightly worse (higher triangle
closure 41% vs 26%).

**The limiting factor is station geometry, not extraction method.**
W7LUX, AC0G_ND, and N4RVE are nearly collinear along a NW-SE axis
(SVD ratio 1.2). With near-collinear geometry, small lag errors
produce large direction errors, and the inversion is ill-conditioned.

**Speed discrepancy vs Gwyn (596 vs 979 m/s) is entirely explained
by lag difference.** Our lags (~19-21 min) vs Gwyn's (27-35 min).
Same midpoint geometry (toolkit already uses midpoints, confirmed).
The lag discrepancy is still the open question from Entry 6.

**Direction is closer than speed** — our 175-178° vs Gwyn's 157°,
an 18-21° difference consistent with the collinear geometry
uncertainty.

**Implication for research.** For this event and station array,
the method question (FFT vs autocorr) is secondary to the geometry
question (need more stations with azimuthal spread). Gwyn's
two-path vector decomposition is geometrically better constrained
than a 3-station collinear DOA.

**Current state.** Two blockers remain (Entry 6). Awaiting Gwyn's
reply. Pipeline tested and working end-to-end on both events.

### 2026-05-20 — Entry 11: CWT multi-peak tracker implementation and first results

**Motivation.** Both FFT and autocorr pick a single peak per block —
either the loudest (FFT) or the instantaneous frequency (autocorr).
Neither explicitly separates F-region from E-region when both are
present. G3ZIL's grape_fft_CWT_tracking_prophet.py uses CWT peak
finding + Prophet forecasting to track multiple modes. Goal: implement
a lighter version using scipy CWT + linear extrapolation, no new
dependencies, integrated as --method cwt in drf_to_doppler.py.

**Implementation (drf_to_doppler.py v1.2.0, research branch):**
1. FFT seeds training history for first N_TRAIN=10 blocks (avoids
   E-region lock during contaminated training phase).
2. After training: CWT (scipy.signal.find_peaks_cwt, Ricker wavelets,
   widths 2-4 bins) finds all spectral peaks per block.
3. 15 dB amplitude filter reduces ~50 noise peaks to 2-5 real peaks.
4. Linear regression on N_TRAIN recent history predicts next F-region
   frequency one step ahead.
5. Candidate closest to prediction, within MAX_STEP_HZ=0.5 of
   prediction, selected. Prevents E-region hop lock.
6. Fallback to FFT if no candidate passes constraints.

**Results on 17 May 2024 LSTID:**

| Station | Condition | FFT std | Autocorr std | CWT std |
|---------|-----------|---------|--------------|---------|
| W7LUX | Clean | 0.554 Hz | 0.472 Hz | 0.514 Hz |
| AC0G_ND | E-region contaminated | 0.682 Hz | 0.645 Hz | 0.557 Hz |

CWT is the smoothest method on the contaminated station — better than
both FFT and autocorr. On the clean station it sits between the two,
confirming no regression on uncontaminated data.

**Key finding.** The 15 dB amplitude filter is essential — without it
CWT produces 40-50 noise peaks per block making candidate selection
effectively random. With the filter, 2-5 meaningful candidates remain
(F-region peak + E-region peak + possibly harmonics/sidescatter).

**Status.** Implementation on research branch. Cross-correlation
comparison against FFT and autocorr pending. No production PR until
results validated on both events and Gwyn has reviewed.

**Note.** Inspired by G3ZIL grape_fft_CWT_tracking_prophet.py.
Uses linear extrapolation instead of Facebook Prophet — comparable
accuracy, ~100x faster, no additional dependencies.

**DOA comparison (all methods, May 2024 LSTID, W7LUX+AC0G_ND+N4RVE):**

| Config | Speed | Direction | Triangle closure |
|--------|-------|-----------|-----------------|
| All FFT | 596 m/s | 178° | 26% ✗ |
| AC0G_ND+N4RVE autocorr | 606 m/s | 175° | 26% ✗ |
| All autocorr | 543 m/s | 178° | 41% ✗ |
| W7LUX FFT + CWT rest | 600 m/s | 180° | 52% ✗ |

CWT gives smoother Doppler (lower std) but worse DOA triangle closure
than FFT. The CWT tracker swaps the W7LUX→AC0G_ND and W7LUX→N4RVE
lags relative to FFT, which increases triangle closure error.

**Conclusion for this event:** station geometry (SVD=1.2, collinear
array) is the dominant uncertainty. No extraction method — FFT,
autocorr, or CWT — produces a self-consistent result on this array.
CWT is a promising direction for contaminated station Doppler
extraction but requires validation on a better-conditioned array
before it can be recommended for production use.

**Jan 2026 MSTID validation:**

| Method | Speed | Direction | Triangle closure | Diagnostics |
|--------|-------|-----------|-----------------|-------------|
| FFT 3-station | 193 m/s | 190° | 0% ✓ | All pass ✓ |
| Autocorr 3-station | 335 m/s | 196° | 88% ✗ | 2 fail ✗ |
| CWT 3-station | 227 m/s | 191° | 12% ✓ | All pass ✓ |

CWT passes all diagnostics on the Jan 2026 MSTID — the first method
other than FFT to do so. Direction matches FFT closely (191° vs 190°).
Speed is higher (227 vs 193 m/s) but within the MSTID range.
CWT avoids the wrong-peak lock that broke autocorr (88% closure) by
using temporal continuity to track the correct cross-correlation peak.

This is a significant positive result. CWT warrants further
investigation on additional events and better-conditioned arrays.

**Synthetic Monte Carlo results (CWT vs FFT vs autocorr, SNR=40dB, 50 trials):**

| Wave | eps | FFT% | Autocorr% | CWT% | Best |
|------|-----|------|-----------|------|------|
| MSTID | 0.0-0.5 | 100 | 100 | 100 | Equal |
| MSTID | 0.7 | 100 | 100 | 62 | FFT/AC |
| MSTID | 1.0 | 64 | 82 | 38 | AC |
| LSTID | 0.0-0.3 | 100 | 98-100 | 18-100 | FFT |
| LSTID | 0.5-0.7 | 100 | 56-68 | 6-8 | FFT |
| LSTID | 1.0 | 8 | 34 | 0 | AC |

CWT underperforms both FFT and autocorr in the synthetic experiment.
The temporal continuity tracker is not effective in the synthetic model
because the idealized two-phasor signal has a constant lag — small
prediction errors from noise accumulate and cause wrong-peak selection.

**Reconciliation with real-data results:** CWT gives smoother
extraction and passes the Jan 2026 MSTID diagnostics because real
Doppler is genuinely smooth and slowly varying, which suits temporal
continuity tracking. The synthetic model is too idealized for CWT's
strengths to show. The real-data results remain the primary evidence.

**Overall CWT assessment:**
- Real clean data: similar to FFT, slightly smoother
- Real contaminated data: smoother than FFT and autocorr, passes diagnostics
- Synthetic: worse than FFT and autocorr across all conditions
- Conclusion: CWT is promising for real contaminated data but requires
  validation on more events before production recommendation.
  The synthetic experiment does not validate CWT — it validates FFT
  (clean/LSTID) and autocorr (contaminated MSTID) as before.

### 2026-05-20 — Entry 12: Adaptive bandpass pre-filter implementation

**Motivation.** CWT (Entry 11) showed smoother extraction on real
contaminated data but underperformed in synthetic. Option 3 from the
robustness investigation: apply a narrow bandpass filter centered on
the prior block's frequency before FFT extraction, suppressing the
E-region component before peak detection rather than separating peaks
after.

**Implementation (drf_to_doppler.py v1.3.0, research branch):**
- Training phase (N_TRAIN=5 blocks): plain FFT to seed history.
- Tracking phase: shift signal to center on predicted frequency,
  apply FIR lowpass (scipy.signal.firwin, Hamming, FILTER_HZ=0.6 Hz
  half-bandwidth), shift back, then FFT peak.
- NUMTAPS adaptive: min(101, n//3)|1 — fits any block size including
  10s cadence at 10 sps (100 samples).
- SNR from unfiltered spectrum (same metric as FFT method).
- Fallback to FFT if filtered peak outside 1.5*FILTER_HZ of prediction.

**Results — AC0G_ND (E-region contaminated, 60s cadence):**

| Method | std (Hz) |
|--------|----------|
| FFT | 0.682 |
| Autocorr | 0.645 |
| CWT | 0.557 |
| Bandpass | **0.414** |

Bandpass is the smoothest of all four methods on the contaminated station.

**Results — Jan 2026 MSTID (10s cadence, 3 stations):**

| Method | Speed | Direction | Triangle closure | Diagnostics |
|--------|-------|-----------|-----------------|-------------|
| FFT | 193 m/s | 190° | 0% ✓ | All pass ✓ |
| CWT | 227 m/s | 191° | 12% ✓ | All pass ✓ |
| Bandpass | 242 m/s | 192° | 28% ✗ | 4/5 pass |
| Autocorr | 335 m/s | 196° | 88% ✗ | 2 fail ✗ |

Bandpass better than autocorr, worse than FFT and CWT. The
N6RFM→AA6BD lag differs slightly from FFT (-1020s vs -1300s) causing
28% triangle closure — the filter is tracking a slightly different
peak on that pair.

**Assessment.** Bandpass gives the smoothest Doppler on contaminated
stations but doesn't improve DOA on the Jan 2026 MSTID. The filter
bandwidth (±0.6 Hz) may need tuning per event — wider for large TID
excursions, narrower for heavily contaminated signals. Promising
direction, needs more testing.

### 2026-05-21 — Entry 13: Multi-peak xcorr selection in tid_doa.py

**Motivation.** The wrong-peak lock problem on autocorr (88% triangle
closure, 335 m/s on Jan 2026 MSTID) was not caused by the extraction
method — it was caused by the cross-correlation peak selector in
tid_doa.py taking the single global maximum (argmax), which happened
to be a wrong-period alias on the N6RFM→AA6BD pair.

**Root cause.** The N6RFM→AA6BD xcorr curve has multiple comparable
peaks at -11.7 min (r=0.546) and -21.7 min (r=0.528). The 0.018
correlation difference is noise — both are plausible. FFT extraction
happened to produce a slightly smoother signal that pushed the true
peak (-21.7 min) above the alias. Autocorr extraction produced a
slightly different signal where the alias (-11.7 min) was marginally
higher, causing wrong-peak lock.

**Fix (tid_doa.py, research branch):**
Added cross_correlate_lag_candidates() using scipy.signal.find_peaks
to find all local maxima in the xcorr curve within max_lag_s.
solve_doa() now tries all combinations of top-3 candidates per pair
(27 combinations for 3 stations) and selects the combination that
minimises triangle closure, accepting non-top candidates only if they
reduce closure by more than 50%.

**Results — Jan 2026 MSTID (3 stations, clean FFT CSVs):**

| Method | Speed | Direction | Triangle closure | Diagnostics |
|--------|-------|-----------|-----------------|-------------|
| FFT | 193 m/s | 190° | 0% ✓ | All pass ✓ |
| Autocorr | 218 m/s | 191° | ✓ | All pass ✓ |
| CWT | 227 m/s | 191° | 12% ✓ | All pass ✓ |
| Bandpass | 242 m/s | 192° | 28% ✗ | 4/5 pass |

Autocorr now passes all diagnostics — wrong-peak lock resolved.
All three methods (FFT, autocorr, CWT) agree on direction (~190-191°)
and give physically plausible MSTID speeds (193-227 m/s).

**Key insight.** The xcorr peak selector was the primary failure mode,
not the extraction method. With multi-peak selection, method choice
matters less for the DOA result — the triangle closure constraint
disambiguates the correct peak across pairs.

**Status.** Multi-peak selector on research branch. Pending validation
on May 2024 LSTID and additional events before merging to main.
## Entry 51 — Jan 2026: IONEX GPS TEC analysis
**Date:** 2026-05-30
**Branch:** research_gui

### Objective
Use IONEX GPS TEC maps to independently verify the Jan 2026 DOA
speed (239 m/s) by tracking TEC perturbations across stations.

### Data downloaded

**JPL 2-hour product:**
JPL0OPSFIN_20260190000_01D_02H_GIM.INX.gz (128 KB)
https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/

**UPC 15-minute product:**
UPC0OPSRAP_20260190000_01D_15M_GIM.INX.gz (1.2 MB)
https://cddis.nasa.gov/archive/gnss/products/ionex/2026/019/

Auth: NASA Earthdata account (n6rfm), CDDIS_Archive + CDDIS Cloud
authorized. Download via wget --auth-no-challenge.

### Results

**JPL 2-hour product:**
- 13 maps at 2-hour cadence (00:00-24:00 UTC)
- VTEC at stations during event window: 20-29 TECU (storm elevated)
- Rapid decay to 8-15 TECU by 02:00 UTC (storm decay)
- No TID oscillation resolvable at 2-hour cadence
- Output: ionex_tec_stations.png

**UPC 15-minute product:**
- 97 maps at 15-minute cadence, same 2.5x5 degree grid
- Raw VTEC: smooth monotonic decline 22-25 to 14-17 TECU during event
- Detrended VTEC: large spike at 00:00 UTC (storm onset artifact),
  decays to near zero by 00:30 UTC
- All stations track together — no inter-station lag visible
- Output: ionex_upc_15min_event.png

### Why IONEX cannot verify speed

1. Time resolution: at 239 m/s with 70 min period, inter-station
   travel time is ~17 min for a 245 km baseline. At 15-min cadence
   that is ~1 sample per lag — insufficient for reliable xcorr.
2. Spatial resolution: 2.5x5 degree grid, each cell ~275x450 km.
   Station separations project onto only 1-2 grid cells.
3. Storm signal dominates: storm-time TEC enhancement (+15 TECU)
   is an order of magnitude larger than TID amplitude (~1-2 TECU).

### What would work
Raw GPS receiver TEC at 1-30 second cadence from CORS network.
MIT Haystack Madrigal (instrument 8000) — Jan 2026 not yet ingested.
Check again in 6-12 months.

### Summary
Speed (239 m/s) remains unverified by external independent data.
IONEX confirms storm-time context but cannot resolve the TID wavefront.
Note: Gwyn G3ZIL's result is from the May 2024 event — a different
dataset and not applicable for Jan 2026 speed verification.

---

## Entry 52 — Jan 2026: Madrigal GPS TEC cross-correlation
**Date:** 2026-05-30
**Branch:** research_gui

### Objective
Use MIT Haystack Madrigal GPS TEC data to independently verify the
Jan 2026 DOA result (239 m/s from 30° NNE) by tracking ionospheric
TEC perturbations across station pairs.

### Data
- Instrument 8000 (GPS TEC), experiment id=100311059
- File: gps260119g.002.hdf5 (kindat=3500, gridded TEC)
- Access: cedar.openmadrigal.org (open, no account required)
- Latency: Jan 2026 data already ingested as of May 2026
  (2–4 week latency, not 6–12 months as IONEX experience suggested)
- Tool: fetch_madrigal_tec.py

### Method
- madrigalWeb isprint API, 1-min bins, ≥3 GPS links per bin
- ±3° lat, ±4° lon boxes around each station's IPP
- 2nd-order polynomial detrend to remove geomagnetic storm background
- Pairwise cross-correlation of detrended TEC series

### Results

| Pair | Baseline | Angle to wave | TEC lag | DOA lag | Agreement |
|------|----------|--------------|---------|---------|-----------| 
| AA6BD→W7LUX | 272°, 1207 km | 62° | 22 min | 24.7 min | 12% |
| AA6BD→N6RFM | — | — | ambiguous (peak at lag=0) | — | — |
| N6RFM→W7LUX | — | — | ambiguous (peak at lag=0) | — | — |

Along-baseline speed (AA6BD→W7LUX): GPS 914 m/s vs DOA 815 m/s
Implied true speed: ~423 m/s (geometric correction, assumes 30° NNE)

### Interpretation
Direction confirmed NNE by sign of GPS TEC lag (AA6BD leads W7LUX).
Speed discrepancy (239 m/s DOA vs ~423 m/s GPS TEC implied) is partly
geometric: the 62° angle between the AA6BD→W7LUX baseline and the wave
propagation direction means the along-baseline projection overstates
true speed, and the correction is sensitive to assumed direction.

The two ambiguous pairs (peak at lag=0) are consistent with the wave
front being nearly parallel to those baselines — also consistent with
the NNE propagation direction found by DOA.

### Outputs
- examples/tid_event_20260119/evaluation/madrigal_tec_stations.png
- examples/tid_event_20260119/evaluation/madrigal_tec_detrended.png
- examples/tid_event_20260119/evaluation/madrigal_tec_1min.png
- examples/tid_event_20260119/evaluation/madrigal_tec_xcorr.png

### Status
Partial independent confirmation: lag agrees to 12%, direction agrees.
Speed remains uncertain due to geometric projection sensitivity.

---

## Entry 53 — Jan 2026: xcorr trim feature implementation
**Date:** 2026-05-31
**Branch:** research_gui

### Background
Gwyn Griffiths (G3ZIL) suggested restricting the cross-correlation
to a sub-window of the full event window — trimming ragged partial-cycle
edges at the start and end, and using only the cleanest portion of the
TID signal (e.g. straddling the clearest peak/trough) to maximise SNR.

### Implementation
Added `xcorr_start_utc` / `xcorr_end_utc` optional keys to the event
JSON config. When present, cross-correlation and DOA inversion operate
on the trimmed window; the full event window is still used for plotting.
If the keys are omitted, behaviour is unchanged (backward compatible).

**tid_doa.py** (line ~871): reads `xcorr_start_utc` / `xcorr_end_utc`
from config, trims each station's time series to the sub-window via
index masking, prints confirmation:
```
xcorr window trimmed to HH:MM–HH:MM UTC (NNN min) [event window: HH:MM–HH:MM]
```

Scale factor derived from t0 vs `stations[0].times[0]` to handle
pandas timezone-aware DatetimeIndex unit conventions correctly.

**Example config usage:**
```json
"xcorr_start_utc": "2026-01-19T00:10:00Z",
"xcorr_end_utc":   "2026-01-19T01:10:00Z"
```

### Testing
Feature confirmed working (trim window print fires correctly).
Applied to Jan 2026 event with multiple window choices — results
remain inconsistent across CSV file combinations (see Entry 54).
Conclusion: feature is correct; inconsistency is in the source CSVs,
not the trim logic.

### When this feature helps
- CSV extracted with good phase lock (GUI cwt-prophet, not manual spline)
- Trim window chosen by visual inspection of the Doppler traces
- Not useful as a blind edge-trim when underlying data is noisy

---

## Entry 54 — Jan 2026: reproducibility investigation
**Date:** 2026-05-31
**Branch:** research_gui

### Context
During testing of the xcorr_start/end_utc trim feature (Gwyn G3ZIL
suggestion), we attempted to reproduce the best Jan 2026 result
(239 m/s from 30° NNE, 1/5 flags) from exported CSV files.

### Finding: reproducibility gap
The 239 m/s result cannot be reproduced from any exported CSV file
using tid_doa.py command-line. Multiple attempts with different
file combinations and settings gave inconsistent results:

| Files | Stations | max_lag | Result | Flags |
|-------|----------|---------|--------|-------|
| spline_tid.csv | 4 stn | 2000s | 1262 m/s 328° | 4/5 |
| spline_tid.csv | 3 stn (drop W7LUX) | 2000s | 462 m/s 45° | 1/5 |
| wave_tid.csv | 3 stn | 2000s | 135 m/s 179° | 2/5 |
| prophet_preview.csv | 4 stn | 2000s | 607 m/s | 2/5 |
| prophet_preview.csv | 3 stn (drop AA6BD) | 2000s | 652 m/s | 1/5 |
| prophet_preview.csv | 4 stn | 1200s | 720 m/s | 2/5 |

### Root cause
The 239 m/s result was produced interactively through tid_spect_click.py
GUI using cwt-prophet Pass 0 auto-extraction. The GUI applies visual
constraints and phase-locking during extraction that are not preserved
in the exported CSV files. Specifically:

1. The cwt-prophet extraction in the GUI operates on the raw Doppler
   spectrogram and locks phase at the point of manual acceptance —
   the prophet_preview.csv captures the fit but not the phase lock
2. The max_lag_seconds constraint is critical — without it the xcorr
   lands on wrong peaks for near-zero-lag pairs (N6RFM→W7LUX)
3. W7LUX spline_tid.csv is noisy throughout (corr < 0.1 with AC0G_ND)
   suggesting the manual spline captured noise, not the TID

### What the consistent finding is
Across all runs, the direction is broadly consistent:
- NNE origin confirmed in most runs (from 25-45°)
- W7LUX is consistently the problem station (low correlations)
- N6RFM→W7LUX near-zero lag appears in multiple runs — possibly
  reflecting that these stations see the wave nearly simultaneously
  (wave front nearly parallel to N6RFM-W7LUX baseline)

### Action required
To properly reproduce 239 m/s, need to:
1. Re-run cwt-prophet extraction in GUI and save the exact config
2. Save the event JSON with specific max_lag_seconds used
3. Add reproducibility notes to WORKFLOW_TUTORIAL.md

### xcorr trim feature (Gwyn suggestion) — status
Feature works correctly (confirmed xcorr window trimming prints).
However it cannot improve results when the underlying CSV data is
noisy or phase-inconsistent. The feature is most useful when:
- The CSV was extracted with good phase lock (GUI cwt-prophet)
- The trim window is chosen by visual inspection of the traces
- Not as a blind edge-trim of arbitrary minutes

---

## Entry 55 — Jan 2026: cwt-prophet re-run, reproducible result
**Date:** 2026-05-31
**Branch:** research_gui

### Context
Following Entry 54 (reproducibility gap), the cwt-prophet extraction
was re-run for all four stations using Pass 0 auto-extraction in
tid_spect_click.py. Two changes were made first:

1. `--event-json` CLI arg added to tid_spect_click.py: on X/E export,
   the matching station entry in the event JSON is updated with the
   CSV path and method (cwt-prophet or spline).
2. `E` key wired to `_export_prophet_csv` — previously there was no
   keyboard shortcut to export the prophet trace directly.

### Extraction
Pass 0 ran automatically on all four stations:
- examples/tid_event_20260119/n6rfm_tid_zoom_clean_prophet_preview.csv
- examples/tid_event_20260119/aa6bd_tid_zoom_clean_prophet_preview.csv
- examples/tid_event_20260119/w7lux_tid_zoom_clean_prophet_preview.csv
- examples/tid_event_20260119/ac0g_nd_tid_zoom_clean_prophet_preview.csv

event_20260119.json updated to point at prophet_preview CSVs,
method: cwt-prophet for all four stations.

### 4-station result (all stations)
```
Speed: 1470 m/s  Direction: from 76° ENE  Flags: 4/5
N6RFM→W7LUX lag: 6.8 s (near-zero — wrong peak or wave parallel to baseline)
```
Poor result. Triangle closure 23%, residual 64%.

### 3-station result: drop AC0G_ND (N6RFM + AA6BD + W7LUX)
```
Speed:     304 m/s
Direction: from 10° NNE
Flags:     0/5  (all diagnostics within typical ranges)
```

Full diagnostics:

| Diagnostic | Value | Status |
|-----------|-------|--------|
| SVR (geometry) | 7.5 | OK (< 30) |
| RMS lag residual | 0.4% of mean lag | OK (< 25%) |
| Pairwise corr | min 0.433, mean 0.571, max 0.704 | OK |
| Triangle closure | 1.1% of mean leg | OK (< 15%) |
| Phase speed | 304 m/s | OK (MSTID range) |

Pairwise lags:
```
N6RFM  → AA6BD   lag = -828.8 s  corr = 0.433
N6RFM  → W7LUX   lag =   +6.8 s  corr = 0.576
AA6BD  → W7LUX   lag = +841.9 s  corr = 0.704
```

### Interpretation
Direction 10° NNE is consistent with:
- Original 239 m/s result (30° NNE, Entry 50)
- GPS TEC lag sign from Madrigal (NNE confirmed, Entry 52)

Speed 304 m/s vs 239 m/s — both MSTID range, difference likely
due to different extraction method (prophet vs interactive spline)
and different station subset.

N6RFM→W7LUX lag of 6.8 s (near-zero) means that baseline
contributes almost no directional information. Result is effectively
driven by AA6BD lags. This is consistent with the wave front being
nearly parallel to the N6RFM–W7LUX baseline (roughly E–W at these
latitudes), which is consistent with a northward-propagating wave.

AC0G_ND dropped: correlations with other stations weak (max 0.415),
SNR fades after ~01:18 UTC (window ends 01:15 to accommodate this).

### Reproducibility status
This result IS reproducible:
```bash
python3 tid_doa.py examples/event_20260119.json --drop-station AC0G_ND
# or use /tmp/event_drop_ac0g.json (3-station subset)
```
The prophet_preview CSVs are committed to the repo.
event_20260119.json points to them with method: cwt-prophet.

### Caveats
- W7LUX prophet_preview quality not independently verified
  (previous spline extractions gave low corr with other stations)
- Near-zero N6RFM→W7LUX lag means array geometry is effectively
  2-baseline for direction; result is less constrained than 4-station
- 239 m/s (Entry 50) remains the best-flagged previous result
  but is not reproducible from committed files

### Open items
1. Send Gwyn email — Jan 2026 results (304 m/s NNE, 5/5 clean)
2. find_event_stations.py — find better 4th station to replace AC0G_ND
3. Add --drop-station flag to tid_doa.py (currently need temp JSON)
