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
