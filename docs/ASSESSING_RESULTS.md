# Assessing Results: The Technical Basis for TID Direction-of-Arrival Estimates

This document explains how a result is reasoned from the
measurements.

For the signal-processing mechanics (carrier tracking, Doppler
extraction, the cross-correlation implementation, why bandpassing
before correlation is harmful) see `METHODOLOGY.md`.

---

## 1. What question the toolkit is intended to answer

The toolkit is intended to estimate the horizontal phase velocity
(speed and azimuth) of a single travelling ionospheric disturbance
(TID) from the relative timing of its Doppler signature across a
small array of HF receivers monitoring a common time-standard
carrier (e.g., WWV at 10 MHz).

The inference chain is:

```
raw I/Q  ->  Doppler(t) per station  ->  pairwise time lags
         ->  least-squares slowness vector  ->  speed & azimuth
```

Each arrow carries assumptions.

1. **Single dominant plane wave.** The array is assumed to be
   traversed by one coherent quasi-planar disturbance during the
   analysis window. If two waves of comparable amplitude and
   different azimuth are present, the inversion still returns a
   single vector — a weighted compromise that may correspond to no
   physical wave. The plane-wave fit residual (Section 4.2) is the
   only internal signal that this assumption has failed.

2. **Stationarity over the window.** Speed and azimuth are assumed
   constant for the chosen interval. Real TIDs evolve; the result
   is an interval-average. Shrinking the window reduces this error
   but worsens lag precision (fewer wave cycles to correlate).

3. **Midpoint sampling.** Each station's measurement is attributed
   to the great-circle midpoint of its transmitter-to-receiver path,
   the nominal ionospheric reflection point for a single hop. This
   is a first-order geometric approximation. Multi-hop propagation,
   off-great-circle paths, and a non-thin reflecting layer all
   violate it. The toolkit assumes single-hop geometry and does not
   attempt to detect multi-hop contamination automatically.

4. **Lag estimates the wave's arrival-time difference.** The
   cross-correlation peak between two stations' Doppler series is
   taken to be the time delay of the same wavefront feature. This
   holds only if the two series share a common, dominant,
   band-limited oscillation. The pairwise correlation coefficient
   (Section 4.3) quantifies how well that holds for each pair.

Sections 4 and 6 describe how the toolkit's diagnostics are intended
to expose assumption failures, and how a reviewer should weigh them.

---

## 2. From timing differences to a wave: the inversion

### 2.1 The slowness model

A travelling ionospheric disturbance is a long, slow ripple in the 
ionosphere. As that ripple sweeps across the country it passes over
each receiver's reflection point at a slightly different moment, 
the way a single ocean swell reaches buoys spaced along a coast one
after another. If you know where each receiver "sees" the sky, and 
you measure how much later the same ripple arrived at one site than
at another, you can solve backwards for two things: how fast the
ripple is moving, and which way it is heading. The "slowness vector"
below is just the compact way to write "speed and direction" so that
the timing differences become a set of linear equations.

The formal statement follows. Let station *k* sample the disturbance
at position **r**_k (the azimuthal equidistant projection of its
WWV-path midpoint onto the local east-north plane centred on the
array centroid — preserving great-circle distances and bearings). For a plane wave with slowness vector **s** (units s m⁻¹,
pointing in the direction the wave travels, with magnitude 1/v where
v is the phase speed), the arrival time of a given wave crest at
station *k* is

  t_k = **s** · **r**_k + const.

The measurable quantity is the pairwise lag between stations *i* and
*j*:

  τ_ij = t_j − t_i = **s** · (**r**_j − **r**_i).

With N stations there are M = N(N−1)/2 pairwise lags and only two
unknowns (the two components of **s**). The system

  **A s** = **b**,  where row *ij* of **A** is (**r**_j − **r**_i)
  and **b** is the vector of measured τ_ij,

is overdetermined for N ≥ 3 and is solved by ordinary least squares
(`numpy.linalg.lstsq`). Phase speed is v = 1/‖**s**‖; azimuth of
propagation is atan2(s_x, s_y) measured clockwise from north.

### 2.2 What the inversion can and cannot establish

With more station pairs than unknowns, no single wave will fit every
measured lag perfectly, so the method finds the one wave that comes
closest to fitting all of them at once (a least-squares fit — it
minimises the total squared mismatch). Two consequences of this
matter, and a reviewer should keep both in view:

- **It always returns an answer, good or bad.** A bad station layout,
  lags that are mostly noise, or two waves present at once will all still
  produce a clean-looking speed and direction. Getting a number back
  is not evidence the number is right. This is the single most
  important caveat in the whole method, and it is why the diagnostics
  in Section 4 exist.

- **It cannot, by itself, tell you the single-wave assumption was
  wrong.** Only the fit residual (Section 4.2) and the internal
  consistency of the lags (Section 4.4) carry that information, and
  they do so as warnings to weigh, not as proofs.

---

## 3. Why this approach was selected

The central question is not "what does the toolkit do" but
"is this approach valid". This section sets out the reasoning
for choosing this approach.

### 3.1 Why cross-correlation of Doppler series

A TID moves the ionospheric reflection point of an HF path up and
down as it passes, which shifts the received carrier frequency: the
Doppler signature is the most direct, continuously sampled trace a
modest amateur receiver can record of the disturbance passing
overhead. Two receivers under the same disturbance record the same
slow oscillation, offset in time by however long the wavefront took
to travel between their sampling points. Cross-correlation is a
standard, assumption-light way to recover that time offset from two
noisy series sharing a common waveform. It does not presume a
particular wave period, amplitude, or shape — only that a common
oscillation exists, which the correlation coefficient itself then
measures.

### 3.2 Why timing differences are sufficient for speed and azimuth

A plane wave's geometry has exactly two unknowns: a speed and a
heading (equivalently, the two components of the slowness vector).
Each station pair contributes one timing measurement that constrains
those unknowns. Three non-collinear stations give three pair
measurements for two unknowns — an overdetermined system whose
least-squares solution is the propagation vector. The approach was
judged appropriate because the observable (relative timing) maps
directly onto the quantity sought (the propagation vector) through
elementary geometry, with no intermediate ionospheric model
required. This deliberate scope limit — it recovers one plane wave,
not a spectrum or a curved front — is a conscious simplification
matched to what a handful of stations can actually constrain, not an
oversight. Section 7 states that limit plainly.

### 3.3 On what basis the approach is believed to work

- **It reproduces the expected result for a reference event.** On
  the 19 January 2026 event, an independent geomagnetic context
  (an auroral-zone disturbance) predicts an equatorward LSTID in a
  known speed band. The toolkit, run blind to that expectation,
  returned a speed and heading consistent with it (Section 6.1).

- **It fails recognisably, not silently, on a known-bad case.** The
  same machinery, run on a deliberately contaminated window, did not
  return a plausible-looking wrong answer; it returned an
  implausible speed together with a failed internal-consistency
  check — a flagged failure, not a silent one (Section 6.2).

- **It is adapted from peer-reviewed work.** Frissell et al. (2022),
  cross-validated amateur-radio observations of a continental-scale
  TID against SuperDARN HF radar and GNSS total-electron-content
  measurements. This toolkit does not re-derive that cross-instrument
  validation; it relies on the demonstrated premise that amateur HF
  data carries recoverable TID signals, and applies a direct
  timing inversion to a much smaller receiving station set.

- **It has been validated against synthetic data with known ground
  truth.** The `synthetic_tests/` suite generates complete synthetic
  DRF recordings (known TID speed, azimuth, period, amplitude) and
  runs the full pipeline on them. Across 20 representative test
  conditions, the autocorr extraction method recovers the correct
  speed within 12% and azimuth within 5° for clean AWGN conditions
  (SNR ≥ 20 dB), and within 20% / 8° for realistic ionospheric noise
  (carrier drift + fading). The tests also characterise the regime
  where the method fails: very low SNR (< 8 dB), and period aliasing
  when any station-pair lag exceeds half the TID period.

---

## 4. The five diagnostics: what each one is intended to test

The toolkit reports five diagnostics after every result. They are
observational, not pass/fail: each prints a measured value against a
guideline range and flags values outside it, but never renders a
verdict and never alters or suppresses the result. The reasoning
below explains what each quantity means and why it bears on
trustworthiness. The provenance of the numerical thresholds is
deferred to Section 5.

### 4.1 Geometry conditioning (singular-value ratio)

The least-squares matrix **A** encodes only the array geometry, not
the data. Its two singular values σ_max ≥ σ_min characterise how
well the two components of **s** are separable. When the station
midpoints are nearly collinear, σ_min → 0, the matrix is
ill-conditioned, and small lag errors produce large errors in the
inferred speed and azimuth. The ratio σ_max/σ_min is a standard
numerical-analysis condition number for the problem; a large ratio
means the geometry — independent of data quality — cannot resolve
the direction.

This is a property of *where the stations are*, knowable before any
data is examined. It is the first thing to check, because no amount
of clean data rescues a degenerate array.

### 4.2 Plane-wave fit residual

For the overdetermined system, the residual ‖**A s** − **b**‖
measures how well *one* plane wave explains *all* the lags
simultaneously. The toolkit reports the RMS lag residual as a
fraction of the mean absolute lag. A small fraction means a single
coherent wave is a good model. A large fraction means the lags are
mutually inconsistent under any single plane wave — the signature of
noise-dominated lags or, more interestingly, of two or more
superimposed waves. The residual does not distinguish these causes;
it only flags that the single-wave assumption (Section 1,
assumption 1) is in tension with the data.

**Diagnostic tool:** `tid_doa_residual.py` (in the repo root)
implements an iterative single-wave subtraction test that can
help distinguish these causes. It fits a single sinusoid to
each station's Doppler trace, subtracts it, and re-runs the
broadband DOA on the residual. If the residual RMS is less than
15% of the original signal ("residual too small" guard), the
single-wave fit absorbed essentially all of the signal — meaning
a second coherent wave is not detectable by this method, and the
elevated RMS residual is more likely due to extraction-period
variability or array geometry strain. If the residual RMS clears
the guard and the residual DOA returns a physically plausible
speed and reasonable pairwise correlation, that is positive
evidence for a second superimposed wave. Edit the CONFIG block
at the top of `tid_doa_residual.py` (EVENT_JSON, MAX_LAG_S,
OUTPUT_DIR) and run it directly.

### 4.3 Pairwise correlation

Each lag is the argmax of a normalised cross-correlation between two
stations' Doppler series. The peak correlation coefficient is the
quality of that estimate: a value near 1 means the two series share
a dominant common oscillation and the lag is well determined; a low
value means the "lag" is the argmax of what is largely noise and
should not be trusted. The toolkit reports the min, mean, and max
across all pairs and explicitly names any weak pair, because a
single bad station typically shows up as low correlation in every
pair containing it — which also suggests the remedy (drop that
station and re-run).

### 4.4 Triangle closure

This is the most physically rigorous of the five and deserves a
precise statement. For any three stations A, B, C, the pairwise lags
satisfy

  τ_AB + τ_BC + τ_CA = 0

*exactly*, for any single coherent wavefront, because the three lags
are differences of three arrival times and the sum telescopes
identically to zero. This is not a fitted relationship or a
statistical expectation; it is an identity that holds for *any*
common feature tracked consistently across the three stations,
independent of the wave model. A non-zero closure is therefore
unambiguous evidence that at least one of the three lags does **not**
correspond to the same wavefront feature — typically because a
cross-correlation locked onto a secondary peak (an aliasing-type
failure for a quasi-periodic signal). The *principle* is exact. The
*tolerance* used to call a closure "large" is a separate, and purely
operational, choice (Section 5).

### 4.5 Phase-speed plausibility

The recovered speed is compared against the empirically established
range for travelling ionospheric disturbances. Unlike the preceding
four, this threshold is derived from the published TID
climatology literature (Section 5). A speed far outside the accepted
range is not proof of error, but in combination with a closure or
residual flag it is a recognised signature of contaminated lags
rather than a real wave — the pattern seen, for example, when an
end-of-window signal fade injects spurious timing.

---

## 5. Where the boundary conditions come from

### 5.1 Provenance of each threshold

The rows are in the same order as the diagnostics are introduced in
Section 4 (4.1 through 4.5), and every subsequent subsection of
Section 5 follows the same order.

| # | Diagnostic (per §4) | Threshold used | Provenance category | Basis |
|---|---|---|---|---|
| 4.1 | Geometry conditioning | σ_max/σ_min ≲ 30 | **Arbitrary** | Chosen value to guide review; not derived or calibrated |
| 4.2 | Plane-wave residual | < ~25% of mean lag | **Arbitrary** | Chosen value to guide review; not derived or calibrated |
| 4.3 | Pairwise correlation | weak < ~0.4, strong > ~0.7 | **Arbitrary** | Chosen values to guide review; not derived or calibrated |
| 4.4 | Triangle closure | principle exact; ~15% tolerance | **Principle: exact physical identity. Tolerance: arbitrary** | Closure identity is geometric and exact; the 15% tolerance is a chosen value to guide review |
| 4.5 | Phase speed | ~100–1000 m/s (LSTID/MSTID regime) | **Literature-derived** | Hocke & Schlegel (1996) review and corroborating climatology; see §5.4 |
| 7 | Extraction SNR | warn < 15 dB; flag < 8 dB | **Empirical** | Synthetic validation: results degrade sharply below 8 dB; 15 dB is a safe operating floor |
| [!] | Aliasing risk | any lag > 0.7 × T/2 | **Physical constraint** | When lag > T/2 the cross-correlation of a sinusoidal signal is inherently ambiguous; not a code issue |
| 7 | Extraction SNR | warn < 15 dB; flag < 8 dB | **Empirical** | Synthetic validation: results degrade sharply below 8 dB; 15 dB is a safe operating floor |
| [!] | Aliasing risk | any lag > 0.7 × T/2 | **Physical constraint** | When lag > T/2 the cross-correlation of a sinusoidal signal is inherently ambiguous; not a code issue |

### 5.2 The arbitrary review-guidance values (§4.1–4.3, and the §4.4 tolerance)

The values for conditioning (≈30), plane-wave residual (≈25%),
triangle-closure tolerance (≈15%), and pairwise correlation
(≈0.4 / ≈0.7) were chosen arbitrarily, as reasonable starting points
to guide a user through reviewing a result.

For reference, what each value nominally marks:

- **Geometry conditioning, ~30 (§4.1).** Larger σ_max/σ_min means
  the station midpoints are closer to collinear and the direction is
  less well constrained; ~30 is the chosen point at which the
  toolkit says "treat the direction with caution."

- **Plane-wave residual, < ~25% of mean lag (§4.2).** Above the
  chosen fraction, the single-plane-wave model is flagged as a poor
  description of the lags.

- **Pairwise correlation, ~0.4 / ~0.7 (§4.3).** A peak below ~0.4 is
  flagged as too weak to trust; above ~0.7 is treated as solid.

### 5.3 The closure tolerance, in detail (§4.4)

As stated in §4.4, τ_AB + τ_BC + τ_CA = 0 is an exact identity for a
single consistently-tracked feature. In practice, finite sampling
(the Doppler series is decimated to a fixed cadence) and finite SNR
perturb each lag by a small error, so the measured closure is small
but non-zero even for a perfectly good result. The toolkit flags a
closure that exceeds ~15% of the mean leg length of the triple.

That 15% was chosen arbitrarily, so that discretisation-scale
closures (a few sample intervals) pass while gross failures (a
correlation locked a full secondary lobe away) flag. The closure
*principle* remains an exact physical identity; only this *tolerance*
is an arbitrary value. A reviewer wishing to apply a principled
tolerance could instead propagate the per-lag timing uncertainty
(set by the sampling cadence and correlation sharpness) into an
expected closure distribution; the toolkit does not currently do
this.

### 5.4 The phase-speed range, in detail (§4.5)

This is the one diagnostic threshold genuinely derived from the
published TID literature. TIDs are conventionally divided into
large-scale (LSTID) and medium-scale (MSTID) classes by period,
wavelength, and horizontal phase speed. The canonical review is:

> Hocke, K. and Schlegel, K. (1996). A review of atmospheric gravity
> waves and travelling ionospheric disturbances: 1982–1995.
> *Annales Geophysicae*, 14, 917–940.

This review consolidates the LSTID horizontal-velocity range of
approximately **300–1000 m/s** (periods ~30 min to several hours,
wavelengths ≳1000 km) and the MSTID range of approximately
**50–300 m/s** (shorter periods and wavelengths). These ranges
remain the values cited by current literature; independent recent
climatologies report typical LSTID velocities consistent with this
envelope (for example, European ionosonde climatology giving typical
LSTID velocities of ~500–700 m/s).

The toolkit's plausibility band of roughly 100–1000 m/s is therefore
deliberately *wider* than the strict LSTID range: it spans the
union of the MSTID and LSTID regimes plus margin, so that the
diagnostic flags only speeds implausible for *any* TID class, not
speeds that merely fall between conventional class boundaries. The
intent is a conservative outlier check, not a classifier.

The physical reason a speed range exists at all is that TIDs are the
ionospheric manifestation of atmospheric gravity waves (Hines,
1960), whose propagation in the thermosphere is bounded by the
medium's buoyancy and dissipation; the high-latitude auroral
electrojet/Joule-heating source of LSTIDs and the resulting
equatorward propagation are reviewed by Hunsucker (1982). These
references establish that the speed bounds are physically motivated,
not merely empirical curve-fitting.

### 5.5 Closing note on all thresholds

Every threshold discussed in this section — the four arbitrary
values (§5.2–5.3) and the one literature-derived range (§5.4) — is
marked tunable in the toolkit's source, so that a reviewer or
advanced user can adjust any of them for a particular array or
campaign. The phase-speed range should be adjusted only with
reference to the climatology literature; the other four may be
changed freely.

The two additional indicators ([7] SNR and [!] Aliasing risk) have
thresholds that are empirically grounded via the synthetic test suite
(`synthetic_tests/`): the SNR thresholds (warn < 15 dB, flag < 8 dB)
were established by running the autocorr extraction method at known
SNR levels and observing where results become unreliable; the aliasing
threshold (lag > T/2) is a physical constraint of the cross-correlation
method, not an arbitrary choice.

The two additional indicators ([7] SNR and [!] Aliasing risk) have
thresholds that are empirically grounded via the synthetic test suite
(`synthetic_tests/`): the SNR thresholds (warn < 15 dB, flag < 8 dB)
were established by running the autocorr extraction method at known
SNR levels and observing where results become unreliable; the aliasing
threshold (lag > T/2) is a physical constraint of the cross-correlation
method, not an arbitrary choice.

---

## 6. Reasoning from the whole picture

No single diagnostic decides a result. The intended practice — and
the one demonstrated in the worked case study — is to weigh the five
diagnostics together, against physical plausibility, and against any
independent corroboration available.

### 6.1 A result that should be trusted

In the 19 January 2026 reference event (see the case study), a
four-station array yielded a phase speed of 239 m/s from 30° NNE, consistent with equatorward
propagation from an auroral-zone source during the early phase of a
geomagnetic disturbance. The diagnostics showed: well-conditioned
geometry, a small plane-wave residual, pairwise correlations in a
coherent range, triangle closures within a few percent, and a speed
squarely within the LSTID regime. Independently, the inferred propagation
direction agreed with the visible succession of peak times across
the stations (a check requiring no inversion at all), and the
classification was physically consistent with the geomagnetic
context. Agreement across independent lines of evidence — internal
consistency, physical plausibility, and a model-free visual check —
is what makes confidence warranted. No one of them alone would.

### 6.2 A result that should be distrusted

A contaminated-window analysis of the same event (an end-of-window
signal fade left in the interval) produced a physically implausible
speed far above the LSTID regime and a heading inconsistent with the
geomagnetic context. The diagnostic pattern was distinctive: the
speed-plausibility flag and the triangle-closure flag fired
together. That conjunction — implausible speed *and* failed internal
consistency — is the recognisable signature of spurious lags, as
opposed to a genuine but unusual wave (which would be fast yet still
internally consistent). The lesson for a reviewer is that the
*pattern* of flags carries more information than any single flag:
closure failure plus speed implausibility indicates contamination;
a lone speed flag on otherwise-consistent data may indicate a real
fast event.

### 6.3 The role of the run log

Every run writes a self-contained record (inputs, result, the full
diagnostics block, and provenance including the exact command and
code revision). This exists so that a result can be reconstructed
and audited after the fact, and so that a reported anomaly carries
its own context.

---

## 7. What this method cannot do

The following are acknowledged limitations:

- **It assumes single-hop propagation.** Multi-hop or
  off-great-circle paths violate the midpoint geometry and are not
  detected automatically.

- **It resolves one plane wave.** A multi-wave field yields a
  composite vector that may correspond to no physical wave; the
  residual flags tension with the single-wave model but does not
  decompose the field.

- **It cannot, alone, certify a result as physically real.** The
  diagnostics test internal consistency and plausibility. They do
  not substitute for independent corroboration (an unrelated
  instrument, a known driver, a model-free visual check). The
  toolkit states this in its own output and this document restates
  it deliberately.

- **Few-station geometry is fragile.** With three stations the
  inversion is exactly constrained-plus-one; a single bad lag has
  nowhere to hide. More stations and better azimuthal spread improve
  robustness; the conditioning diagnostic quantifies how much.

- **Four of the five original thresholds are arbitrary.** As Section 5
  states plainly, four of the five original diagnostic values were
  chosen arbitrarily to guide review. The two additional indicators
  ([7] SNR and [!] Aliasing risk) have empirically grounded or
  physically exact thresholds.

- **Period aliasing occurs when any station-pair lag exceeds T/2.**
  For a sinusoidal TID, the cross-correlation cannot distinguish lag L
  from lag L − T (one period earlier). This happens when the baseline
  is long relative to the wave speed and period — for example, a
  1200 km E-W array observing a 300 m/s TID at 60-minute period has a
  maximum pairwise lag of ~2100 s, which exceeds T/2 = 1800 s. The
  [!] Aliasing risk diagnostic flags this condition, but cannot
  correct it; the only remedies are a shorter baseline, a faster
  wave, or a longer period.

- **Low extraction SNR is not detected by the five core diagnostics.**
  The five diagnostics measure internal consistency of the lags, not
  the quality of the underlying Doppler extraction. A noisy extraction
  (median SNR < 8 dB) can produce lags that appear self-consistent
  while being noise-driven. The [7] SNR diagnostic addresses this by
  reading median SNR from each station's CSV; it is informational and
  does not contribute to the flag count.

---

## 8. Further Reading

The HamSCI Personal Space Weather Station. — Instrument and network context
for the Grape DRF receivers used by this toolkit.
(https://hamsci.org/psws-overview)

Fedorenko, Y.P., Tyrnov O.F., Fedorenko, V.N., and Dorohov, D.L. (2013) 
Model of traveling ionospheric disturbances. J. Space Weather Space Clim., 3, A30
(https://www.swsc-journal.org/articles/swsc/full_html/2013/01/swsc110031/swsc110031.html)

Frissell, N. A., et al. (2022). First observations of
large-scale travelling ionospheric disturbances using automated
amateur radio receiving networks. *Geophysical Research
Letters*, 49. https://doi.org/10.1029/2022GL097879 — The direct
methodological antecedent: LSTID detection from amateur HF data,
cross-validated against SuperDARN and GNSS TEC, attributed to
auroral electrojet/Joule heating. Establishes the premise that
amateur HF observations carry recoverable LSTID signal.
(https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2022GL097879)

Hines, C. O. (1960). Internal atmospheric gravity waves at
ionospheric heights. *Canadian Journal of Physics*, 38,
1441–1481. — Foundational theory of atmospheric gravity waves,
the physical basis of TIDs.
(https://apps.dtic.mil/sti/tr/pdf/AD0250769.pdf)

Hocke, K. and Schlegel, K. (1996). A review of atmospheric
gravity waves and travelling ionospheric disturbances:
1982–1995. *Annales Geophysicae*, 14, 917–940.
https://doi.org/10.1007/s00585-996-0917-6 — The canonical
climatological review; primary source for the LSTID/MSTID
speed, period, and wavelength ranges used by the phase-speed
diagnostic.
(https://www.researchgate.net/profile/Klemens-Hocke/publication/41086051_A_review_of_atmospheric_gravity_waves_and_travelling_ionospheric_disturbances_1982-1995/links/5b62e486a6fdccf0b20776fa/A-review-of-atmospheric-gravity-waves-and-travelling-ionospheric-disturbances-1982-1995.pdf)

Hunsucker, R. D. (1982). Atmospheric gravity waves generated in
the high-latitude ionosphere: A review. *Reviews of Geophysics*,
20(2), 293–315. https://doi.org/10.1029/RG020i002p00293 —
AGW→TID generation at high latitudes; the auroral source
mechanism for LSTIDs.

---

## Appendix: some ways to challenge this method

A reviewer wishing to stress-test the approach is invited to:

- Re-run a published TID event of known speed and azimuth through
  the toolkit and compare (an independent expert hand-analysis is
  the strongest such check).
- Perturb the analysis window and confirm the result is stable for a
  genuine wave and unstable for a marginal one.
- Drop each station in turn and confirm the result is not the
  artefact of a single receiver.
- Inspect whether the diagnostic flag *pattern* on a known-bad case
  matches the contamination signature described in Section 6.2.
