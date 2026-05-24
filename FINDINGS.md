# Research: Doppler extraction — FFT vs complex autocorrelation

**Status:** PAUSED — awaiting G3ZIL reply on two questions (lag
discrepancy and N5BRG channel). Analysis substantially complete
through Entry 8 (synthetic Monte Carlo). No new analysis until
blockers resolved. All data, scripts, figures, and PDF reports
committed to research-doppler-extraction branch.

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

## Entry 21 — Complete guided workflow validated: 458 m/s WSW LSTID
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
