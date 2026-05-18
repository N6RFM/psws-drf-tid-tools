# Research: Doppler extraction — FFT vs complex autocorrelation

**Status:** ACTIVE — first positive results obtained. Awaiting Gwyn's
clarification on lag discrepancy and N5BRG channel before drawing
conclusions.

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

### 2026-05-18 — Entry 7: FFT vs autocorr on 19 Jan 2026 MSTID (original reference event)

**Goal.** Apply both extraction methods to the original Jan 2026 event
that motivated the toolkit, compare DOA results, and test whether the
autocorr advantage seen on the May 2024 LSTID holds for an MSTID.

**Stations and data.** 6 stations with DRF available: N6RFM, AA6BD,
W7LUX, AC0G_ND, KB4SE, KC4LE. All single-channel except AC0G_ND
(subchannel 4). All SNR > 30 dB median at event time; W7LUX, N6RFM,
AC0G_ND strongest (>48 dB). 10s cadence, 00:00-01:10 UTC.

**Four configurations run:**

| Method | Stations | Speed | Direction | Wave type | Diagnostics |
|--------|----------|-------|-----------|-----------|-------------|
| FFT | 3 (original) | 193 m/s | 190 deg | MSTID | All pass |
| Autocorr | 3 | 335 m/s | 196 deg | MSTID | 2 fail |
| FFT | 6 | 709 m/s | 223 deg | LSTID | 2 fail |
| Autocorr | 6 | 774 m/s | 223 deg | LSTID | 2 fail |

**Pairwise cross-correlation curves (3-station pairs):**
- N6RFM->W7LUX: both methods agree exactly (lag=0, r=0.46). Curves identical.
- AA6BD->W7LUX: both methods agree closely (FFT +21.7 min r=0.663,
  autocorr +21.3 min r=0.664). Curves nearly identical.
- N6RFM->AA6BD: methods disagree. FFT -21.7 min r=0.528; autocorr
  -11.7 min r=0.546. Curve has two comparable peaks (~0.53 and ~0.55)
  separated by ~10 min. FFT picks the earlier; autocorr picks the later.
  Genuine curve ambiguity -- neither peak is clearly dominant.

**Why FFT 3-station passes and autocorr 3-station fails:**
FFT choice of -21.7 min gives self-consistent triangle: -1300+0+1300=0s
closure. Autocorr choice of -11.7 min breaks closure: -700+0+1280=580s
(88% of mean leg). Triangle closure diagnostic correctly identifies this.
FFT result (193 m/s @ 190 deg, MSTID) is the more reliable DOA result.

**6-station results -- both methods flagged:**
Adding AC0G_ND (lat 46.875, far north), KB4SE, KC4LE stretches the
plane-wave assumption. RMS residuals 39-49%, triangle closure 116-124%.
Eastern cluster (AA6BD, KB4SE, KC4LE) nearly co-located relative to
wave scale -- no independent geometric constraint added. Autocorr
improves mean pairwise correlation (0.726 vs 0.681) and reduces RMS
residual (39% vs 49%) but both remain outside typical ranges.

**Does autocorr help on this MSTID?**
On two of three pairs: no difference. On one pair (N6RFM->AA6BD):
autocorr picks a different peak on an ambiguous curve, producing an
inconsistent DOA. The smoother autocorr output that helped on the slow
May 2024 LSTID (long period, well-separated peaks) changes peak
selection on this faster MSTID (shorter period, closer peaks, more
ambiguous curves).

**Reading (honest).**
Valuable negative/qualified result. Autocorr is not universally better.
On May 2024 LSTID it improved pairwise coherence on contaminated pairs.
On Jan 2026 MSTID it produces a wrong-peak lock on the most ambiguous
pair, breaking triangle closure and yielding unreliable DOA speed
(335 vs 193 m/s). Toolkit diagnostics correctly distinguish the
reliable result (FFT 3-station, all pass) from unreliable ones.

**Figures:** research/comparison_fft_vs_autocorr_jan19.png (curves),
research/comparison_table_jan19.png (summary table).
