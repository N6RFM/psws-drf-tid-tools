# Methodology

The mathematical and signal-processing details behind the toolkit. For
practical "how to use it" guidance, see the [tutorial](TUTORIAL.md) and
[cookbook](COOKBOOK.md).

---

## The physical setup

A HamSCI Grape station receives the WWV time-signal carrier from Fort
Collins, CO, on one or more standard frequencies (2.5, 5, 10, 15, 20,
25 MHz). The transmitter is fixed in space and time; the carrier is
extraordinarily stable (10⁻¹² level). Any apparent Doppler shift seen
at the receiver is therefore caused by motion in the **ionospheric
reflection point** — the F-region patch that bounced the signal from
WWV to the receiver.

The signal arrives at the receiver after one bounce off the F-region
(single-hop propagation). The bouncing point lies approximately at the
**great-circle midpoint** between transmitter and receiver, at an
altitude of ~250 km. When a TID passes through this region, the local
electron density changes, which shifts the reflection height, which
appears at the receiver as a Doppler frequency shift.

For a TID of horizontal phase speed `v` propagating in direction `θ`,
the apparent Doppler at a station with midpoint at position `r` arrives
delayed relative to a reference station with midpoint at `r_0` by:

```
τ = (r - r_0) · ŝ / v
```

where `ŝ` is the unit vector in the wave's direction of motion.
Equivalently, defining the slowness vector `s = ŝ/v`:

```
τ = (r - r_0) · s
```

This is the equation the toolkit inverts to extract `s` (and hence `v`
and `θ`) from observed pairwise lags.

---

## Step 1: Doppler extraction

The raw DRF I/Q stream is complex baseband, sampled at 10 Hz. The WWV
carrier sits within ±5 Hz of zero after baseband mixing.

For each output sample of duration `T = decim_seconds`:

1. Read `N = 10 × T` complex I/Q samples.
2. Apply a Hanning window: `x_w[k] = x[k] · 0.5(1 - cos(2πk/N))`.
3. FFT: `X[m] = Σ_k x_w[k] · exp(-2πi·mk/N)`.
4. Find the maximum-magnitude bin `m*` within ±5 Hz of zero.
5. Quadratic interpolation for sub-bin precision:
   ```
   f_peak = m* · (fs/N) + 0.5 · (|X[m*-1]| - |X[m*+1]|) /
            (|X[m*-1]| - 2|X[m*]| + |X[m*+1]|)
   ```
   Gives ~0.01 Hz precision on a 10-second block at 10 Hz sample rate.
6. SNR estimate: `20 · log10(|X[m*]| / median(|X|))` dB. Median is
   robust to spurious in-band tones.

The output is a CSV with columns `timestamp_utc, doppler_hz, snr_db`
at the chosen cadence.

This is a **bin-peak tracker** rather than a phase-locked loop. Each
block is independent, so brief signal dropouts don't propagate as
tracking errors. The cost is some temporal smoothness; SNR > 30 dB
gives ~0.01–0.02 Hz block-to-block noise on the Doppler estimate.

---

## Step 2: Cross-correlation

For two Doppler series `x[n]` and `y[n]` (resampled to common cadence
`dt`, mean-subtracted), the cross-correlation as a function of lag is:

```
R(τ) = Σ_n x[n] · y[n + τ/dt]
```

`scipy.signal.correlate(y, x, mode='full')` computes this; the lag
that maximizes `R` is the best-fit time offset of `y` relative to `x`.

In the toolkit, both series are also **z-normalized** before
correlation:

```
x' = (x - mean(x)) / std(x)
y' = (y - mean(y)) / std(y)
```

so that the correlation coefficient is in [-1, +1] and amplitude
differences between stations don't affect the lag estimate.

### The bandpass problem (and why we don't do it)

A natural intuition is: "TIDs have characteristic periods of 15–120
minutes; we should bandpass-filter the Doppler to that range before
correlating". This produces **incorrect lags** for slowly-varying TID
signals.

Why: a strongly bandpassed signal becomes nearly sinusoidal. The
autocorrelation of a sinusoid has lobes one period apart. When two
stations see the same wave, the cross-correlation has high-correlation
lobes at each integer multiple of the period. The lag-finder picks the
*highest* lobe within the search range, which is often *not* the true
lag.

For an 80-minute wave, the lag-finder might return a lag of -3 minutes
(grabbing a secondary lobe) instead of the true -15 minutes (which sits
on the broader main lobe of the unfiltered correlation).

The fix: **don't bandpass**. The raw mean-subtracted Doppler trace has
enough broadband content (the slowly-rising trend over the wave's
duration) that its cross-correlation has one dominant peak at the true
lag. Z-normalization handles amplitude variation; mean-subtraction
handles DC offsets.

`tid_doa.py` defaults `use_bandpass: false`. Override only when there's
a specific reason to (e.g., your raw Doppler has a large terminator
gradient that swamps the TID).

---

## Step 3: Slowness-vector inversion

For N stations at positions `r_1, ..., r_N` (projected to a local
east-north tangent plane), we have N(N-1)/2 observed pairwise lags
`τ_ij`. The forward model is:

```
τ_ij = (r_j - r_i) · s
```

This is an overdetermined linear system (more pairs than unknowns,
since `s` has two components). Stack the equations into matrix form:

```
A · s = b
```

where:
- Each row of `A` is `[x_j - x_i, y_j - y_i]` (the position difference
  in local coordinates)
- The corresponding entry of `b` is `τ_ij`
- `s = [s_x, s_y]ᵀ` is the unknown 2D slowness vector

Solve by ordinary least-squares using `numpy.linalg.lstsq`:

```
s* = (AᵀA)⁻¹ Aᵀ b
```

Then:
- Phase speed: `v = 1/|s*|`
- Direction of motion (heading toward): `θ = atan2(s_x, s_y)`
- Direction wave is coming from: `θ + 180°`

The least-squares fit minimizes the sum of squared residuals across all
N(N-1)/2 pairs simultaneously, so 3+ stations gives a well-determined
result robust to any single bad lag.

### Geographic projection

The local east-north tangent plane is computed from each station's
**WWV-path midpoint** (not the station location), since the midpoint is
where the wave actually passes through (the F-region reflection point):

```python
midpoint = great_circle_midpoint(wwv_lat, wwv_lon, station_lat, station_lon)
```

The local projection uses equirectangular coordinates centered on the
array centroid:

```python
x_east_m  = (lon - lon_0) · R · cos(lat_0)
y_north_m = (lat - lat_0) · R
```

This is exact in the limit of small arrays (when curvature can be
ignored). For arrays spanning more than ~2000 km, replace with a more
careful projection (e.g. Mercator with cosine-of-latitude correction).
For the 19 Jan 2026 4-station array (~1500 km span), the
equirectangular projection is good to ~1% in distances.

---

## Step 4: Quality assessment

Several quantitative checks indicate whether to trust the result:

### Triangle closure

For any three stations A, B, C, the lag sum should approximately equal
the direct lag:

```
τ(A→B) + τ(B→C) ≈ τ(A→C)
```

The script implicitly checks this by least-squares fitting — non-closing
triangles produce larger fit residuals. Closure to within ~5–10 minutes
is typical for real-world TID work.

### Pairwise correlation

For a wave that propagates coherently across the array, pairwise
correlations should be **> 0.5** for all pairs and ideally > 0.7. A
single pair with correlation 0.1–0.3 is a sign that one station's
trace is noisy or seeing a different feature.

### Lag distribution

If any pair's lag is at the edge of `max_lag_seconds`, the search
window was too narrow or that pair's signals can't be aligned. Either
extend the window or drop that station from the inversion.

### Speed in physical range

LSTIDs: 300–1000 m/s. MSTIDs: 100–300 m/s. Results outside these
ranges should be regarded with skepticism — either a methodological
problem (bandpass, wrong window, etc.) or a non-planar wave that
the toolkit's planar assumption doesn't capture.

### Direction stability under station perturbation

Drop one station and re-run. If the direction changes by less than
~10° and speed by less than ~20%, the answer is robust. Larger
changes mean the array geometry is poorly conditioned for the wave.

---

## Limitations

The toolkit assumes:

1. **A single planar wave** dominates the analysis window. Multiple
   waves at different periods superpose and degrade the fit.
2. **Single-hop propagation** so the midpoint is the relevant
   reflection point. Two-hop paths (typical for very long baselines
   on certain frequencies) violate this; check that all your paths
   are < ~2500 km on 10 MHz.
3. **Flat-Earth geometry** within the array. Good to ~1% for arrays
   under 2000 km; degrades for larger arrays.
4. **Vertical-incidence reflection** at the path midpoint. The actual
   reflection point varies slightly with frequency, ionospheric
   conditions, and ray angle, but is typically within a few tens of
   km of the great-circle midpoint.

For events that violate these assumptions, the toolkit still produces
a "best-fit plane wave" result, but it should be reported with explicit
caveats. Future work directions: spherical-Earth projection, two-hop
support, multi-wave decomposition.

---

## References

- Hines, C.O. (1960). Internal atmospheric gravity waves at
  ionospheric heights. *Can. J. Phys.*, 38(11), 1441–1481.
- Hocke, K. & Schlegel, K. (1996). A review of atmospheric gravity
  waves and travelling ionospheric disturbances: 1982–1995. *Ann.
  Geophys.*, 14(9), 917–940.
- Frissell, N. et al. The HamSCI Personal Space Weather Station (PSWS)
  network: http://hamsci.org/psws
- MIT Haystack Observatory, Digital RF format:
  https://github.com/MITHaystack/digital_rf
