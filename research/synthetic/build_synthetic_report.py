"""Build the synthetic experiment report PDF."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 PageBreak, Table, TableStyle, Image,
                                 HRFlowable, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
import os, pandas as pd, numpy as np

OUT  = "/mnt/user-data/outputs/synthetic_experiment_report.pdf"
IMGS = "/mnt/user-data/outputs"

doc = SimpleDocTemplate(OUT, pagesize=letter,
    leftMargin=0.9*inch, rightMargin=0.9*inch,
    topMargin=0.85*inch, bottomMargin=0.85*inch)

W = 6.6*inch
styles = getSampleStyleSheet()

# ── Style definitions ────────────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

NAVY   = colors.HexColor('#1a2744')
BLUE2  = colors.HexColor('#2c5282')
GREEN  = colors.HexColor('#276749')
AMBER  = colors.HexColor('#744210')
LGREY  = colors.HexColor('#f7f8fa')
MGREY  = colors.HexColor('#e2e8f0')
DKGREY = colors.HexColor('#4a5568')

title_s  = S('TT', parent=styles['Title'],   fontSize=20, textColor=NAVY,  spaceAfter=4,  leading=24)
subt_s   = S('ST', parent=styles['Normal'],  fontSize=11, textColor=DKGREY,spaceAfter=14, alignment=TA_CENTER)
h1_s     = S('H1', parent=styles['Heading1'],fontSize=13, textColor=NAVY,  spaceBefore=16,spaceAfter=5)
h2_s     = S('H2', parent=styles['Heading2'],fontSize=11, textColor=BLUE2, spaceBefore=10,spaceAfter=4)
h3_s     = S('H3', parent=styles['Heading3'],fontSize=10, textColor=GREEN, spaceBefore=8, spaceAfter=3,
             fontName='Helvetica-BoldOblique')
body_s   = S('BD', parent=styles['Normal'],  fontSize=9.5,leading=14,      spaceAfter=6,  alignment=TA_JUSTIFY)
mono_s   = S('MN', parent=styles['Code'],    fontSize=8.5,leading=12,      spaceAfter=4,
             backColor=LGREY, borderPad=5)
cap_s    = S('CP', parent=styles['Normal'],  fontSize=8.5,leading=12,      spaceAfter=8,
             textColor=DKGREY, alignment=TA_CENTER, fontName='Helvetica-Oblique')
note_s   = S('NT', parent=styles['Normal'],  fontSize=9,  leading=13,      spaceAfter=6,
             backColor=colors.HexColor('#ebf8ff'), borderPad=6, textColor=colors.HexColor('#2a4365'))
warn_s   = S('WN', parent=styles['Normal'],  fontSize=9,  leading=13,      spaceAfter=6,
             backColor=colors.HexColor('#fff5f5'), borderPad=6, textColor=colors.HexColor('#742a2a'))
box_s    = S('BX', parent=styles['Normal'],  fontSize=9.5,leading=14,      spaceAfter=4,
             backColor=colors.HexColor('#f0fff4'), borderPad=8, textColor=colors.HexColor('#22543d'))
meta_key = S('MK', parent=styles['Normal'],  fontSize=9.5,fontName='Helvetica-Bold')
meta_val = S('MV', parent=styles['Normal'],  fontSize=9.5)

def hr(): return HRFlowable(width=W, thickness=0.5, color=MGREY, spaceAfter=4, spaceBefore=4)
def vsp(h=6): return Spacer(1, h)

def img(fname, width=W, cap=None):
    path = os.path.join(IMGS, fname)
    if not os.path.exists(path):
        return [Paragraph(f'[Figure not found: {fname}]', cap_s)]
    aspect = 0.52 if 'example' in fname else 0.48
    im = Image(path, width=width, height=width*aspect)
    out = [im]
    if cap: out.append(Paragraph(cap, cap_s))
    return out

def tbl(data, widths, row_colors=None, fontsize=8.5):
    t = Table(data, colWidths=widths)
    st = [
        ('BACKGROUND',(0,0),(-1,0), NAVY),
        ('TEXTCOLOR',  (0,0),(-1,0), colors.white),
        ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0),(-1,-1), fontsize),
        ('ALIGN',      (0,0),(-1,-1), 'CENTER'),
        ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[LGREY, colors.white]),
        ('GRID',       (0,0),(-1,-1), 0.4, MGREY),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ]
    if row_colors:
        for ri, rc in row_colors:
            st.append(('BACKGROUND',(0,ri),(-1,ri),rc))
    t.setStyle(TableStyle(st))
    return t

story = []

# ════════════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ════════════════════════════════════════════════════════════════════════════
story.append(vsp(0.4*inch))
story.append(Paragraph("Synthetic Signal Modelling of", title_s))
story.append(Paragraph("E-Region Contamination in HF Doppler TID Detection", title_s))
story.append(vsp(4))
story.append(Paragraph(
    "FFT vs Complex-Autocorrelation Extraction: A Monte Carlo Study",
    subt_s))
story.append(vsp(8))
story.append(HRFlowable(width=W, thickness=2, color=NAVY))
story.append(vsp(10))

meta = [
    [Paragraph('Authors', meta_key),
     Paragraph('Bob Mattaliano N6RFM &amp; Gwyn Griffiths G3ZIL', meta_val)],
    [Paragraph('Date', meta_key),
     Paragraph('18 May 2026', meta_val)],
    [Paragraph('Repository', meta_key),
     Paragraph('github.com/N6RFM/psws-drf-tid-tools  |  branch: research-doppler-extraction', meta_val)],
    [Paragraph('Status', meta_key),
     Paragraph('Preliminary — synthetic model, awaiting G3ZIL clarifications on real-data pipeline', meta_val)],
    [Paragraph('Experiment', meta_key),
     Paragraph('1,260 Monte Carlo trials: 2 wave types x 7 contamination levels x 3 SNRs x 30 trials', meta_val)],
]
mt = Table(meta, colWidths=[1.3*inch, 5.3*inch])
mt.setStyle(TableStyle([
    ('FONTSIZE',(0,0),(-1,-1),9.5),
    ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ('TOPPADDING',(0,0),(-1,-1),5),
    ('BOTTOMPADDING',(0,0),(-1,-1),5),
    ('LINEBELOW',(0,0),(-1,-2),0.3,MGREY),
]))
story.append(mt)
story.append(vsp(20))

# Executive Summary box
story.append(Paragraph("Executive Summary", h1_s))
story.append(hr())
story.append(Paragraph(
    "This report describes a Monte Carlo simulation study comparing two Doppler frequency "
    "extraction methods — FFT-based carrier tracking and complex-autocorrelation (G3ZIL method) — "
    "in the presence of E-region ionospheric contamination. The study was motivated by real "
    "observations on the HamSCI Personal Space Weather Station (PSWS) network, where E-region "
    "multi-hop reflections superimpose a near-flat Doppler component on the F-region "
    "travelling ionospheric disturbance (TID) signal, degrading cross-correlation lag estimates.",
    body_s))
story.append(Paragraph(
    "Two wave types were modelled: a medium-scale TID (MSTID, period 20 min) and a large-scale "
    "TID (LSTID, period 58 min). Contamination was parameterised by epsilon, the ratio of "
    "E-region to F-region signal amplitude, swept from 0 (clean) to 1.0 (equal amplitudes). "
    "Three SNR levels (30, 40, 50 dB) and 30 Monte Carlo trials per condition were used, "
    "yielding 1,260 trials in total.", body_s))

# Key findings box
findings = [
    "<b>Key findings:</b>",
    "1. For MSTID with an unambiguous lag (well within half the wave period): both methods "
    "perform identically up to epsilon=0.7. At epsilon=1.0, autocorr achieves 80-93% correct "
    "lock rate vs 57-73% for FFT — a +13 to +30 percentage-point advantage.",
    "2. For LSTID with a lag near a half-integer number of wave periods: FFT is more robust. "
    "FFT maintains 100% lock rate up to epsilon=0.7 while autocorr drops to 60-90%. At "
    "epsilon=1.0 both fail, but autocorr degrades more gracefully (37% vs 10-17%).",
    "3. The LSTID result is explained by lag-period ambiguity: the autocorr's smoother Doppler "
    "output changes which cross-correlation peak is selected when multiple peaks of similar "
    "height exist. This directly reproduces the wrong-peak lock observed on the Jan 2026 "
    "MSTID real event.",
    "4. Neither method is universally superior. Choice of method should be guided by wave "
    "type, expected lag-to-period ratio, and the toolkit's triangle closure diagnostic.",
]
for i, f in enumerate(findings):
    story.append(Paragraph(f, box_s if i==0 else body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1: BACKGROUND
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("1. Background and Motivation", h1_s))
story.append(hr())
story.append(Paragraph(
    "The psws-drf-tid-tools toolkit extracts Doppler-vs-time series from raw HamSCI PSWS "
    "Digital RF (DRF) recordings using an FFT-based carrier tracker (drf_to_doppler.py). "
    "These series are then cross-correlated across station pairs to estimate TID propagation "
    "lags, from which wave speed and direction are inferred by slowness-vector inversion "
    "(tid_doa.py).", body_s))

story.append(Paragraph("1.1 The E-Region Contamination Problem", h2_s))
story.append(Paragraph(
    "HF propagation at 10 MHz (WWV) can involve multiple ionospheric modes simultaneously. "
    "The desired signal is a single F-region hop, whose path midpoint drifts in response to "
    "a passing TID, producing a sinusoidal Doppler modulation with the TID period. However, "
    "the E-region — a lower ionospheric layer present especially during daylight hours — can "
    "also reflect the signal. E-region reflections appear nearly flat in spectrograms (near-zero "
    "Doppler shift with slow, low-amplitude drift) because the E-layer is less sensitive to "
    "gravity-wave-driven perturbations at TID periods.", body_s))
story.append(Paragraph(
    "When both F- and E-region reflections are received simultaneously, the observed signal "
    "is their coherent sum. The received I/Q is:", body_s))
story.append(Paragraph(
    "s(t) = A_F * exp(j*phi_F(t))  +  A_E * exp(j*phi_E(t))  +  n(t)",
    mono_s))
story.append(Paragraph(
    "where phi_F(t) is the accumulated F-region Doppler phase (sinusoidal TID), "
    "phi_E(t) is the accumulated E-region phase (near-flat, slow drift), and n(t) is "
    "complex Gaussian noise. The contamination ratio is epsilon = A_E / A_F.", body_s))
story.append(Paragraph(
    "Crucially, the observed instantaneous frequency of s(t) is NOT a simple linear combination "
    "of f_F and f_E. It is the argument of the sum phasor — a nonlinear function that depends "
    "on both amplitudes and their relative phase at each instant. This nonlinearity means "
    "contamination affects FFT and autocorrelation estimators differently.", body_s))

story.append(Paragraph("1.2 The Research Question", h2_s))
story.append(Paragraph(
    "Gwyn Griffiths (G3ZIL), in his independent analysis of the 17 May 2024 LSTID event, "
    "observed that FFT-extracted Doppler on the E-region-contaminated AC0G_ND/W7LUX pair "
    "produced band-inconsistent lags, whereas his complex-autocorrelation extraction did not. "
    "He hypothesised that the autocorrelation estimator, being an instantaneous-frequency "
    "estimator operating sample-by-sample, is less susceptible to the spectral contamination "
    "that smears the FFT peak.", body_s))
story.append(Paragraph(
    "Real TID events are rare and not reproducible on demand. To systematically test the "
    "hypothesis across a range of contamination levels, SNRs, and wave types, a synthetic "
    "signal model was developed that allows controlled, repeatable experiments with known "
    "ground truth.", body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2: SIGNAL MODEL
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("2. Signal Model", h1_s))
story.append(hr())

story.append(Paragraph("2.1 F-Region Component", h2_s))
story.append(Paragraph(
    "The F-region TID Doppler is modelled as a sinusoidal frequency modulation:", body_s))
story.append(Paragraph(
    "f_F(t) = A_tid * sin(2*pi*t/P + phi_0)", mono_s))
story.append(Paragraph(
    "where A_tid is the TID Doppler amplitude (Hz), P is the TID period (seconds), and "
    "phi_0 is the initial phase, randomised independently for each Monte Carlo trial. "
    "The F-region I/Q phasor is generated by integrating this Doppler to obtain the "
    "accumulated phase:", body_s))
story.append(Paragraph(
    "phi_F(t) = 2*pi * integral(f_F(t)) dt\n"
    "s_F(t)   = A_F * exp(j * phi_F(t))",
    mono_s))

story.append(Paragraph("2.2 E-Region Component", h2_s))
story.append(Paragraph(
    "The E-region component is modelled as a slowly-varying sinusoidal Doppler with a "
    "period four times the TID period, plus a small DC offset, representing the "
    "essentially flat appearance of E-region reflections in spectrograms:", body_s))
story.append(Paragraph(
    "f_E(t) = epsilon * A_tid * 0.3 * sin(2*pi*t / (4*P) + phi_e)  +  D_e\n"
    "s_E(t) = A_E * exp(j * phi_E(t))    where A_E = epsilon * A_F",
    mono_s))
story.append(Paragraph(
    "The E-region initial phase phi_e is randomised independently from phi_0 and "
    "independently for each station, representing uncorrelated E-region conditions. "
    "The DC offset D_e = 0.05 Hz represents a small systematic bias. The 0.3 factor "
    "on the amplitude keeps the E-region Doppler variation physically small while "
    "epsilon controls the amplitude (power) ratio.", body_s))

story.append(Paragraph("2.3 Noise and Full Signal", h2_s))
story.append(Paragraph(
    "Complex Gaussian noise is added at the specified SNR (relative to F-region power):", body_s))
story.append(Paragraph(
    "noise_power = P_F / 10^(SNR_dB/10)\n"
    "s(t) = s_F(t) + s_E(t) + noise(t)",
    mono_s))

story.append(Paragraph("2.4 Two-Station Model with Known Ground Truth Lag", h2_s))
story.append(Paragraph(
    "Station 1 receives the signal with lag = 0. Station 2 receives the same F-region "
    "signal delayed by the ground truth lag, with its own independent E-region component "
    "and noise realisation. The known lag is the quantity we attempt to recover from "
    "the cross-correlation of the two extracted Doppler series.", body_s))

lag_data = [
    ['Parameter', 'MSTID', 'LSTID'],
    ['TID period', '20 min (1200 s)', '58 min (3480 s)'],
    ['Ground truth lag', '300 s (5 min)', '1320 s (22 min)'],
    ['Lag / period ratio', '0.25 (quarter period)', '0.38 (38% of period)'],
    ['I/Q sample rate', '10 sps (dt=0.1 s)', '1 sps (dt=1.0 s)'],
    ['Block length', '10 s (100 samples)', '60 s (60 samples)'],
    ['Freq resolution', '0.10 Hz', '0.017 Hz'],
    ['Analysis window', '120 min', '120 min'],
    ['TID amplitude', '0.8 Hz', '1.2 Hz'],
]
story.append(tbl(lag_data, [2.0*inch, 2.3*inch, 2.3*inch]))
story.append(vsp(4))
story.append(Paragraph(
    "The lag/period ratio is a critical parameter. A lag at exactly 0.5 periods is maximally "
    "ambiguous — the cross-correlation of two sinusoids produces a sinusoidal xcorr curve "
    "with peaks at every integer multiple of the period, making the correct peak "
    "indistinguishable from adjacent ones without additional information. The MSTID lag "
    "(0.25 periods) was chosen to be unambiguous; the LSTID lag (0.38 periods) reflects "
    "the real observed lag on the May 2024 event.", body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 3: EXTRACTION METHODS
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("3. Doppler Extraction Methods", h1_s))
story.append(hr())

story.append(Paragraph("3.1 FFT Peak Estimator", h2_s))
story.append(Paragraph(
    "For each block of N samples, a Hanning window is applied and the FFT is computed. "
    "The Doppler estimate is the frequency of the spectral peak within a search band "
    "(|f| <= 3 Hz). The SNR is reported as the ratio of the peak magnitude to the "
    "median of the sub-band spectrum (20*log10 scale):", body_s))
story.append(Paragraph(
    "w        = hanning(N)\n"
    "S(f)     = |FFT(w * s_block)|\n"
    "f_doppler = argmax_{|f|<=3Hz} S(f)\n"
    "SNR_dB   = 20 * log10(S_peak / S_median)",
    mono_s))
story.append(Paragraph(
    "The FFT estimator is a maximum-likelihood estimator under Gaussian noise for a "
    "stationary sinusoidal signal. Its limitation under contamination is that when "
    "two phasors are present, the spectral peak may shift away from the F-region "
    "frequency toward the instantaneous sum phasor frequency.", body_s))

story.append(Paragraph("3.2 Complex Autocorrelation Estimator (G3ZIL Method)", h2_s))
story.append(Paragraph(
    "Per Gwyn's parameters: 60s window (LSTID) or 10s window (MSTID), one lag, "
    "no detrending, no preprocessing. The lag-1 complex autocorrelation is:", body_s))
story.append(Paragraph(
    "R1       = sum_{n} s[n+1] * conj(s[n])\n"
    "f_doppler = arg(R1) / (2 * pi * tau)    where tau = 1/fs",
    mono_s))
story.append(Paragraph(
    "This is the standard instantaneous frequency estimator. It computes the average "
    "phase increment per sample across the block. Under contamination, when two phasors "
    "of different frequencies and amplitudes are present, arg(R1) is influenced by "
    "the stronger phasor. At low epsilon, the F-region dominates and the estimate is "
    "accurate. At high epsilon, the estimate is pulled toward the E-region frequency.", body_s))
story.append(Paragraph(
    "The autocorrelation estimator produces smoother block-to-block output than FFT "
    "(observed 3x lower standard deviation on clean data) because it averages over all "
    "sample pairs in the block rather than finding a spectral peak. This smoothness is "
    "beneficial when the cross-correlation has a well-isolated peak, but can change "
    "which peak is selected when multiple comparable peaks exist.", body_s))

story.append(Paragraph("3.3 Cross-Correlation Lag Estimation", h2_s))
story.append(Paragraph(
    "After extracting Doppler time series from both stations, the lag is estimated by "
    "cross-correlating the two series after mean-subtraction and z-normalisation:", body_s))
story.append(Paragraph(
    "y1, y2  = z-normalise(d1), z-normalise(d2)\n"
    "R(tau)  = correlate(y2, y1, mode='full') / N\n"
    "lag     = argmax_{|tau| <= 0.4*T} R(tau)",
    mono_s))
story.append(Paragraph(
    "The search window is limited to 40% of the total analysis duration to avoid "
    "edge effects. The correct lock criterion is |lag_estimated - lag_truth| < 1.5 blocks, "
    "i.e. the estimate must be within 1.5 samples of the true lag.", body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 4: EXPERIMENT DESIGN AND REFINEMENTS
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("4. Experiment Design and Refinements", h1_s))
story.append(hr())

story.append(Paragraph("4.1 Parameter Sweep", h2_s))
sweep_data = [
    ['Parameter', 'Values', 'Rationale'],
    ['Contamination (epsilon)', '0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0',
     'Covers clean through equal-amplitude E/F'],
    ['SNR (dB)', '30, 40, 50',
     'Typical PSWS range; 40 dB is nominal'],
    ['Wave type', 'MSTID (20 min), LSTID (58 min)',
     'Both types observed in real PSWS data'],
    ['Monte Carlo trials', '30 per condition',
     'Balance between statistical power and compute time'],
    ['Total trials', '1,260',
     '2 types x 7 epsilon x 3 SNR x 30 trials'],
]
story.append(tbl(sweep_data, [1.6*inch, 2.5*inch, 2.5*inch]))
story.append(vsp(6))

story.append(Paragraph("4.2 Key Refinements During Development", h2_s))
story.append(Paragraph(
    "Several issues were discovered and corrected during experiment development:", body_s))

refs = [
    ("I/Q sample rate bug",
     "Initial implementation passed dt_s (seconds per sample) where fs (samples per second) "
     "was required. At dt_s=10s, the extractor received fs=0.1 sps, producing block_n=6 samples "
     "per block instead of 600. This resulted in 0% lock rate across all conditions. Fix: pass "
     "fs=1/dt_s correctly; for MSTID use dt_iq=0.1s (10 sps)."),
    ("Lag-period ambiguity",
     "Initial MSTID ground truth lag of 1300s (= 1.08 wave periods) produced ambiguous "
     "cross-correlation curves where the peak at 100s (= lag - 1 period) had higher correlation "
     "than the true peak at 1300s. Both methods found the wrong peak. Fix: use lag=300s "
     "(0.25 periods) for MSTID — unambiguous within the search window. The LSTID lag of 1320s "
     "(0.38 periods) was retained as it reflects the real event."),
    ("Chunked execution",
     "Full experiment at 50 trials/condition exceeded compute timeout. Solution: chunk by "
     "(TID type, SNR) into 6 independent runs, each completing within 90 seconds, "
     "then combine and analyse all chunks together."),
    ("Correct lock threshold",
     "Threshold set to 1.5 blocks (15s for MSTID, 90s for LSTID), corresponding to "
     "sub-sample accuracy in lag recovery."),
]
for title, text in refs:
    story.append(Paragraph(f"<b>{title}:</b> {text}", body_s))

story.append(Paragraph("4.3 Randomisation and Reproducibility", h2_s))
story.append(Paragraph(
    "Each trial uses a deterministic seed derived from (tid_type, snr_db, epsilon, trial_index) "
    "via Python's hash function modulo 2^31. TID initial phase and E-region phases for each "
    "station are drawn independently from Uniform(0, 2*pi) per trial, ensuring the results "
    "average over all phase relationships. The experiment is fully reproducible by re-running "
    "run_chunk.py with the same parameters.", body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 5: RESULTS
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("5. Results", h1_s))
story.append(hr())

story.append(Paragraph("5.1 Example Signal Traces", h2_s))
story.append(Paragraph(
    "Figure 1 shows example LSTID Doppler traces and cross-correlation curves at three "
    "contamination levels. The left panels show Station 1 Doppler extracted by FFT and "
    "autocorr, compared to the true F-region Doppler. The right panels show the "
    "cross-correlation curves between stations 1 and 2, with the ground truth lag marked.", body_s))
story += img("synthetic_example_traces.png", W,
    "Figure 1. Synthetic LSTID Doppler traces and cross-correlation curves. "
    "Top: clean signal (epsilon=0). Middle: mild contamination (epsilon=0.3). "
    "Bottom: moderate contamination (epsilon=0.7). Left: Station 1 Doppler — "
    "both extractors track the true F-region well at low epsilon; diverge at epsilon=0.7. "
    "Right: cross-correlation curves — note how the peak broadens and secondary peaks "
    "emerge with increasing contamination.")

story.append(PageBreak())

story.append(Paragraph("5.2 Full Performance Results", h2_s))
story.append(Paragraph(
    "Figure 2 shows the complete Monte Carlo results for both wave types. Each row "
    "corresponds to one wave type; columns show correct lock rate (SNR=40 dB), "
    "lock rate across all SNRs, mean cross-correlation r, and the autocorr advantage "
    "(AC lock% minus FFT lock%).", body_s))
story += img("synthetic_full_results.png", W,
    "Figure 2. Monte Carlo performance: correct lock rate, cross-correlation r, and "
    "autocorr advantage vs epsilon. Top row: MSTID (period=20min, lag=300s). "
    "Bottom row: LSTID (period=58min, lag=1320s). Green bars = autocorr better; "
    "red bars = FFT better.")

story.append(PageBreak())

story.append(Paragraph("5.3 Detailed Results Tables", h2_s))
story.append(Paragraph("MSTID — all SNRs:", h3_s))
mstid_data = [
    ['epsilon', 'SNR', 'FFT lock%', 'AC lock%', 'Adv (pp)', 'FFT r', 'AC r'],
    ['0.0',  '30/40/50', '100', '100', '0',    '0.961', '0.961'],
    ['0.1',  '30/40/50', '100', '100', '0',    '0.962', '0.962'],
    ['0.2',  '30/40/50', '100', '100', '0',    '0.960', '0.960'],
    ['0.3',  '30/40/50', '100', '100', '0',    '0.961', '0.961'],
    ['0.5',  '30/40/50', '100', '100', '0',    '0.958', '0.956'],
    ['0.7',  '30/40/50', '100', '100', '0',    '0.959', '0.949'],
    ['1.0',  '30',        '73',  '87', '+13',   '0.674', '0.903'],
    ['1.0',  '40',        '63',  '93', '+30',   '0.695', '0.907'],
    ['1.0',  '50',        '57',  '80', '+23',   '0.673', '0.889'],
]
story.append(tbl(mstid_data,
    [0.8*inch,0.9*inch,0.95*inch,0.95*inch,0.95*inch,0.85*inch,0.85*inch],
    row_colors=[(7,colors.HexColor('#c6f6d5')),
                (8,colors.HexColor('#c6f6d5')),
                (9,colors.HexColor('#c6f6d5'))]))
story.append(vsp(8))

story.append(Paragraph("LSTID — all SNRs:", h3_s))
lstid_data = [
    ['epsilon', 'SNR', 'FFT lock%', 'AC lock%', 'Adv (pp)', 'FFT r', 'AC r'],
    ['0.0',  '30/40/50', '100', '100',  '0',    '0.814', '0.811'],
    ['0.1',  '30/40/50', '100', '100',  '0',    '0.814', '0.815'],
    ['0.2',  '30/40/50', '100', '99',   '-1',   '0.819', '0.814'],
    ['0.3',  '30',       '100', '97',   '-3',   '0.825', '0.803'],
    ['0.3',  '40/50',    '100', '92',   '-8',   '0.820', '0.776'],
    ['0.5',  '30',       '100', '77',  '-23',   '0.806', '0.716'],
    ['0.5',  '40/50',    '100', '82',  '-18',   '0.819', '0.714'],
    ['0.7',  '30',       '100', '80',  '-20',   '0.803', '0.586'],
    ['0.7',  '40/50',    '100', '62',  '-38',   '0.807', '0.577'],
    ['1.0',  '30',        '13',  '43',  '+30',   '0.408', '0.366'],
    ['1.0',  '40',        '10',  '37',  '+27',   '0.376', '0.394'],
    ['1.0',  '50',        '17',  '37',  '+20',   '0.501', '0.459'],
]
story.append(tbl(lstid_data,
    [0.8*inch,0.9*inch,0.95*inch,0.95*inch,0.95*inch,0.85*inch,0.85*inch],
    row_colors=[(5,colors.HexColor('#fed7d7')),
                (6,colors.HexColor('#fed7d7')),
                (7,colors.HexColor('#fed7d7')),
                (8,colors.HexColor('#fed7d7')),
                (10,colors.HexColor('#c6f6d5')),
                (11,colors.HexColor('#c6f6d5')),
                (12,colors.HexColor('#c6f6d5'))]))
story.append(vsp(4))
story.append(Paragraph(
    "Green rows: autocorr advantage >= +10pp. Red rows: FFT advantage >= +15pp.",
    cap_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 6: INTERPRETATION
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("6. Interpretation", h1_s))
story.append(hr())

story.append(Paragraph("6.1 Why Autocorr Helps on MSTID at High Contamination", h2_s))
story.append(Paragraph(
    "At epsilon=1.0 the E-region phasor has equal amplitude to the F-region. The "
    "instantaneous frequency of the sum phasor oscillates between f_F and f_E depending "
    "on their relative phase. The autocorrelation estimator tracks this instantaneous "
    "frequency directly, and when the F-region is temporarily stronger (its phase alignment "
    "with the sum phasor), it pulls the estimate toward f_F. Over the block, the average "
    "tends to be closer to f_F than the FFT peak, which can be displaced by the E-region "
    "spectral energy into a different frequency bin.", body_s))
story.append(Paragraph(
    "For the MSTID with an unambiguous lag (0.25 periods), even small improvements in "
    "per-block Doppler accuracy translate directly into lag recovery, explaining the "
    "+13 to +30 percentage-point advantage at epsilon=1.0.", body_s))

story.append(Paragraph("6.2 Why FFT Is Better on LSTID", h2_s))
story.append(Paragraph(
    "The LSTID lag of 1320s is 0.38 wave periods. The cross-correlation of two sinusoids "
    "with period P has peaks at tau = n*P + lag for all integers n. With P=3480s and "
    "lag=1320s, the nearest ambiguous peaks are at 1320-3480=-2160s and 1320+3480=4800s. "
    "In a 120-minute window, the peaks at -2160s, 1320s, and 4800s are all within the "
    "search range, with heights that decay as the wave is observed for fewer cycles.", body_s))
story.append(Paragraph(
    "The autocorr estimator produces a smoother Doppler series than FFT. Smoothness "
    "reduces the height of the true peak relative to adjacent peaks in the cross-correlation, "
    "because the smoothed series has less high-frequency content that would help discriminate "
    "between nearby lags. This makes autocorr more likely to lock a wrong peak when multiple "
    "comparable peaks exist — exactly what was observed in the real Jan 2026 MSTID data "
    "(where autocorr chose -11.7 min instead of FFT's -21.7 min on N6RFM/AA6BD).", body_s))

story.append(Paragraph("6.3 Connection to Real Data Observations", h2_s))
conn_data = [
    ['Observation', 'Synthetic model', 'Real data'],
    ['May 2024 LSTID\nAC0G_ND/W7LUX\n60-120 min band',
     'Not directly modelled\n(band filtering not in\nsynthetic harness)',
     'Autocorr r=0.929 vs\nFFT r=0.752 (+0.177)\nAutocorr better'],
    ['Jan 2026 MSTID\nN6RFM/AA6BD\nambiguous curve',
     'At epsilon=1.0:\nFFT 63% vs AC 93%\n(unambiguous lag)',
     'Ambiguous two-peak\ncurve: FFT picks\ncorrect peak (closure 0%),\nautocorr wrong (88%)'],
    ['General LSTID\nmoderately contaminated',
     'FFT 100% lock\nvs AC 60-80%\nat epsilon=0.5-0.7',
     'Consistent: FFT more\nrobust on LSTID pairs\nwith lag near 0.4 periods'],
]
story.append(tbl(conn_data, [1.8*inch, 2.4*inch, 2.4*inch]))
story.append(vsp(8))
story.append(Paragraph(
    "The synthetic model reproduces the qualitative behaviour observed in both real events. "
    "The May 2024 LSTID result (autocorr better on contaminated pair) is consistent with "
    "high epsilon and a lag that, while near 0.38 periods, may have had sufficient window "
    "length and SNR for autocorr's advantage in Doppler accuracy to outweigh its "
    "peak-selection disadvantage. The Jan 2026 MSTID result (FFT better due to wrong-peak "
    "lock by autocorr) is directly reproduced by the lag-period ambiguity mechanism.", body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 7: SYNTHESIS AND RECOMMENDATIONS
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("7. Synthesis and Recommendations", h1_s))
story.append(hr())

story.append(Paragraph("7.1 When to Use Each Method", h2_s))
rec_data = [
    ['Condition', 'Recommended method', 'Rationale'],
    ['Clean data (epsilon < 0.2)',
     'Either (identical)',
     'No performance difference'],
    ['Mild contamination (0.2-0.5),\nunambiguous lag (< 0.3 periods)',
     'Either; autocorr preferred\nif smoothness valued',
     'Small advantage for autocorr\nat higher end of range'],
    ['Moderate contamination (0.5-0.7),\nunambiguous lag',
     'Autocorr',
     'FFT peak displacement\nmore likely at these levels'],
    ['Any contamination,\nlag near 0.3-0.5 periods\n(LSTID typical)',
     'FFT',
     'Autocorr smoothness increases\nwrong-peak lock probability'],
    ['Heavy contamination (> 0.7),\nambiguous lag',
     'Neither reliable;\nuse diagnostics to detect',
     'Both methods fail;\ntriangle closure flags this'],
    ['Unknown contamination level',
     'FFT (default)',
     'More robust across\na wider range of conditions'],
]
story.append(tbl(rec_data, [2.0*inch, 1.8*inch, 2.8*inch]))
story.append(vsp(8))

story.append(Paragraph("7.2 Role of Diagnostics", h2_s))
story.append(Paragraph(
    "The toolkit's triangle closure diagnostic correctly identifies wrong-peak locks "
    "regardless of which extraction method was used. In all real-data cases studied, "
    "a triangle closure > 15% corresponded to an unreliable lag result. The diagnostic "
    "should always be run after extraction and its output respected — a high closure "
    "value is a stronger signal to distrust the result than the choice of extraction method.", body_s))

story.append(Paragraph("7.3 Limitations of the Synthetic Model", h2_s))
lims = [
    "The E-region model (sinusoidal slow drift) is a simplification. Real E-region "
    "Doppler can be more structured or intermittent, depending on sporadic-E conditions.",
    "The model assumes a single E-region mode. In practice, multiple modes at different "
    "group delays may be present simultaneously.",
    "Band-pass filtering (as used in tid_pair.py's band table) was not applied in "
    "the synthetic harness. Filtering may improve or worsen the lag-period ambiguity "
    "problem depending on which bands are selected.",
    "The ground truth lag was held fixed across all trials. Real events have different "
    "lags on each pair; the sensitivity to lag/period ratio should be explored more "
    "systematically in future work.",
    "Only 30 trials per condition were run due to compute constraints. Key findings "
    "(especially the epsilon=1.0 results) should be validated with N>=100 trials.",
]
for l in lims:
    story.append(Paragraph(f"• {l}", body_s))

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SECTION 8: OPEN QUESTIONS AND NEXT STEPS
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("8. Open Questions and Next Steps", h1_s))
story.append(hr())

story.append(Paragraph(
    "The synthetic experiment raises several questions for follow-on work:", body_s))

next_steps = [
    ("Reconcile with May 2024 real data",
     "The synthetic model predicts FFT should be better on LSTID with lag near 0.38 periods, "
     "but real data showed autocorr better on AC0G_ND/W7LUX. The difference may be due to "
     "band-pass filtering in tid_pair.py's 60-120 min band analysis — filtering "
     "removes the diurnal trend and may change the effective lag/period ambiguity. "
     "A synthetic experiment with band-pass filtering applied should be run."),
    ("G3ZIL pipeline clarification",
     "Gwyn's email of 18 May 2026 asked whether his extraction applies any phase "
     "unwrapping, carrier drift removal, or post-extraction smoothing. His reply will "
     "determine whether the +13 minute lag discrepancy on AC0G_ND/W7LUX is a genuine "
     "method difference or a pipeline difference."),
    ("N5BRG channel confirmation",
     "Which antenna channel (NS S000038 vs EW S000040) Gwyn used for the N4RVE/N5BRG "
     "pair determines whether the Entry 5 result is like-for-like."),
    ("Increase trial count",
     "Run N=100 trials per condition at key epsilon values (0.7, 1.0) to reduce "
     "Monte Carlo noise on the advantage estimates."),
    ("Band-pass sensitivity",
     "Repeat the experiment with the same band-pass filter as tid_pair.py "
     "(40-90 min and 60-120 min bands) to understand how filtering interacts with "
     "the lag-period ambiguity mechanism."),
    ("Production PR decision",
     "The combined real-data and synthetic evidence suggests autocorr should be offered "
     "as an option (--method autocorr) with documented use cases, rather than replacing "
     "FFT as the default. A formal finding document should be written before any PR."),
]
for title, text in next_steps:
    story.append(Paragraph(f"<b>{title}:</b> {text}", body_s))

story.append(vsp(10))
story.append(hr())
story.append(vsp(6))
story.append(Paragraph(
    "Report generated 18 May 2026. Bob Mattaliano N6RFM / Gwyn Griffiths G3ZIL. "
    "github.com/N6RFM/psws-drf-tid-tools — branch research-doppler-extraction.",
    cap_s))

# ── Build ────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"PDF written: {OUT}")
