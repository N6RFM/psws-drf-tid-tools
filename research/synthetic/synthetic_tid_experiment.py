"""
synthetic_tid_experiment.py
===========================
Monte Carlo comparison of FFT vs complex-autocorrelation Doppler extraction
under controlled E-region contamination.

Physical model
--------------
The raw I/Q at each station is modelled as the sum of two phasors:

  s(t) = sqrt(P_F) * exp(j * phi_F(t))   -- F-region (TID-modulated)
       + sqrt(P_E) * exp(j * phi_E(t))   -- E-region (slow drift / near-flat)
       + n(t)                             -- complex Gaussian noise

where phi(t) = 2*pi * integral(f(t)) dt  (accumulated Doppler phase).

The F-region Doppler is a sinusoid with the TID period.
The E-region Doppler is a low-amplitude slowly-varying signal
(longer period, near-zero mean) representing the essentially flat
E-region reflection seen in spectrograms.

Both FFT and autocorr operate on windowed blocks of s(t):
  - FFT:      peak of |FFT(w * s_block)|  (Hanning window)
  - Autocorr: arg(R1) / (2*pi*tau) where R1 = sum(s[n+1]*conj(s[n]))

Station 2 receives the same F-region signal delayed by ground_truth_lag,
with its own independent E-region component and noise.

Contamination ratio epsilon = sqrt(P_E / P_F) = A_E / A_F.

Experiment sweeps:
  epsilon  : 0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0
  TID type : MSTID (period=20 min, lag=1300s, cadence=10s)
              LSTID (period=58 min, lag=1320s, cadence=60s)
  SNR      : 30, 40, 50 dB
  N_trials : 50 Monte Carlo realisations per condition

Authors: Bob Mattaliano N6RFM / Gwyn Griffiths G3ZIL collaboration
Date: 2026-05-18
"""

import numpy as np
import pandas as pd
from scipy.signal import correlate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from itertools import product
import warnings
warnings.filterwarnings('ignore')

RNG = np.random.default_rng(42)

# ── Signal synthesis ─────────────────────────────────────────────────────────

def make_iq(
    duration_s, dt_s, f_tid_hz, snr_db, epsilon,
    tid_phase=0.0, e_period_s=None, e_phase=0.0, e_offset_hz=0.0,
    lag_s=0.0
):
    """
    Generate complex I/Q for one station.

    Parameters
    ----------
    duration_s   : total window length in seconds
    dt_s         : sample interval (e.g. 1/10 for 10 sps)
    f_tid_hz     : TID Doppler amplitude in Hz
    snr_db       : signal-to-noise ratio in dB (F-region power / noise power)
    epsilon      : E/F amplitude ratio (0 = clean)
    tid_phase    : initial phase of TID sinusoid (rad)
    e_period_s   : E-region modulation period (default: 4 * TID period)
    e_phase      : initial phase of E-region modulation
    e_offset_hz  : DC Doppler offset of E-region (Hz)
    lag_s        : delay applied to F-region phasor (seconds)

    Returns
    -------
    s : complex ndarray, length N = duration_s / dt_s
    t : time axis (seconds)
    f_true : true F-region Doppler at each sample (Hz)
    """
    fs = 1.0 / dt_s
    t = np.arange(0, duration_s, dt_s)
    N = len(t)

    # TID period from amplitude and a fixed period passed via caller
    # (caller sets tid_period_s; f_tid_hz is amplitude)
    # We reconstruct period from the caller's tid_period_s stored as a global
    # -- see make_station() below which wraps this

    return t, N  # placeholder; real work in make_station


def make_station(
    duration_s, dt_s, tid_period_s, tid_amp_hz, snr_db, epsilon,
    tid_phase=0.0, e_period_factor=4.0, e_phase=0.0, e_offset_hz=0.05,
    lag_s=0.0
):
    """
    Full station I/Q synthesis.

    Returns
    -------
    t         : time axis (s)
    s         : complex I/Q array
    f_tid_true: true F-region Doppler (Hz) — the ground truth
    f_e_true  : true E-region Doppler (Hz)
    """
    fs = 1.0 / dt_s
    t = np.arange(0, duration_s, dt_s)
    N = len(t)

    # F-region: sinusoidal TID Doppler, delayed by lag_s
    t_lag = t - lag_s
    f_tid_true = tid_amp_hz * np.sin(2 * np.pi * t_lag / tid_period_s + tid_phase)

    # Integrate Doppler to get F-region phase
    phi_F = 2 * np.pi * np.cumsum(f_tid_true) * dt_s

    # E-region: slow sinusoid + DC offset (near-flat in spectrogram)
    e_period_s = e_period_factor * tid_period_s
    f_e_true = (epsilon * tid_amp_hz * 0.3 *
                np.sin(2 * np.pi * t / e_period_s + e_phase) + e_offset_hz)
    phi_E = 2 * np.pi * np.cumsum(f_e_true) * dt_s

    # Amplitudes: F-region power = P_F, E-region power = epsilon^2 * P_F
    P_F = 1.0
    A_F = np.sqrt(P_F)
    A_E = epsilon * A_F

    # Noise power from SNR
    noise_power = P_F / (10 ** (snr_db / 10.0))
    noise_sigma = np.sqrt(noise_power / 2.0)

    # Complex I/Q
    f_phasor = A_F * np.exp(1j * phi_F)
    e_phasor = A_E * np.exp(1j * phi_E)
    noise = noise_sigma * (RNG.standard_normal(N) + 1j * RNG.standard_normal(N))

    s = f_phasor + e_phasor + noise

    return t, s, f_tid_true, f_e_true


# ── Doppler extraction ───────────────────────────────────────────────────────

def extract_fft(s_block, fs, search_band_hz=3.0):
    """FFT peak estimator (Hanning window, peak/median SNR)."""
    n = len(s_block)
    w = np.hanning(n)
    spec = np.abs(np.fft.fftshift(np.fft.fft(s_block * w)))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mask = np.abs(freqs) <= search_band_hz
    sub = spec[mask]
    peak_idx = np.argmax(sub)
    doppler_hz = freqs[mask][peak_idx]
    snr_db = 20.0 * np.log10(sub.max() / (np.median(sub) + 1e-12))
    return doppler_hz, snr_db


def extract_autocorr(s_block, fs, search_band_hz=3.0):
    """Lag-1 complex autocorrelation estimator (G3ZIL method)."""
    R1 = np.dot(s_block[1:], s_block[:-1].conj())
    tau = 1.0 / fs
    doppler_hz = np.angle(R1) / (2 * np.pi * tau)
    # SNR via FFT peak/median (same scale as FFT method)
    n = len(s_block)
    w = np.hanning(n)
    spec = np.abs(np.fft.fftshift(np.fft.fft(s_block * w)))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mask = np.abs(freqs) <= search_band_hz
    sub = spec[mask]
    snr_db = 20.0 * np.log10(sub.max() / (np.median(sub) + 1e-12))
    return doppler_hz, snr_db


def extract_doppler_series(s, fs, block_s, method='fft'):
    """
    Extract Doppler time series from I/Q using block processing.

    Parameters
    ----------
    s       : complex I/Q array
    fs      : sample rate (Hz)
    block_s : block length in seconds
    method  : 'fft' or 'autocorr'

    Returns
    -------
    doppler : Doppler Hz array, one value per block
    snr     : SNR dB array
    """
    block_n = int(block_s * fs)
    n_blocks = len(s) // block_n
    doppler = np.zeros(n_blocks)
    snr = np.zeros(n_blocks)
    extractor = extract_fft if method == 'fft' else extract_autocorr

    for i in range(n_blocks):
        blk = s[i * block_n:(i + 1) * block_n]
        doppler[i], snr[i] = extractor(blk, fs)

    return doppler, snr


# ── Cross-correlation lag estimator ──────────────────────────────────────────

def xcorr_lag(y1, y2, dt_s, max_lag_s=None):
    """
    Cross-correlate two Doppler series, return peak lag and correlation.

    Returns
    -------
    lag_s : lag in seconds (positive = y2 lags y1)
    r     : peak correlation coefficient
    """
    y1 = (y1 - y1.mean()) / (y1.std() + 1e-12)
    y2 = (y2 - y2.mean()) / (y2.std() + 1e-12)
    cc = correlate(y2, y1, mode='full') / len(y1)
    lags = np.arange(-(len(y1) - 1), len(y1)) * dt_s
    if max_lag_s is not None:
        mask = np.abs(lags) <= max_lag_s
        lags = lags[mask]
        cc = cc[mask]
    peak_idx = np.argmax(cc)
    return lags[peak_idx], cc[peak_idx]


# ── Single trial ─────────────────────────────────────────────────────────────

def run_trial(tid_period_s, dt_s, block_s, duration_s, tid_amp_hz,
              snr_db, epsilon, ground_truth_lag_s, trial_seed):
    """Run one Monte Carlo trial. Returns dict of results."""
    # Independent random phases for each trial / station
    rng = np.random.default_rng(trial_seed)
    tid_phase1 = rng.uniform(0, 2 * np.pi)
    tid_phase2 = tid_phase1  # same wave, same phase (just delayed)
    e_phase1   = rng.uniform(0, 2 * np.pi)
    e_phase2   = rng.uniform(0, 2 * np.pi)  # independent E-region per station

    # Station 1 (reference, no lag)
    _, s1, f_tid1, _ = make_station(
        duration_s, dt_s, tid_period_s, tid_amp_hz, snr_db, epsilon,
        tid_phase=tid_phase1, e_phase=e_phase1, lag_s=0.0
    )

    # Station 2 (delayed by ground_truth_lag_s)
    _, s2, f_tid2, _ = make_station(
        duration_s, dt_s, tid_period_s, tid_amp_hz, snr_db, epsilon,
        tid_phase=tid_phase2, e_phase=e_phase2, lag_s=ground_truth_lag_s
    )

    max_lag = duration_s * 0.45  # search up to 45% of window

    results = {'epsilon': epsilon, 'snr_db': snr_db,
               'tid_period_s': tid_period_s, 'ground_truth_lag_s': ground_truth_lag_s}

    for method in ('fft', 'autocorr'):
        d1, _ = extract_doppler_series(s1, 1.0/dt_s, block_s, method)
        d2, _ = extract_doppler_series(s2, 1.0/dt_s, block_s, method)
        lag, r = xcorr_lag(d1, d2, block_s, max_lag_s=max_lag)
        results[f'{method}_lag_s']   = lag
        results[f'{method}_lag_err_s'] = lag - ground_truth_lag_s
        results[f'{method}_r']       = r

    return results


# ── Monte Carlo experiment ───────────────────────────────────────────────────

def run_experiment(n_trials=50, verbose=True):
    """Full sweep over all conditions."""

    conditions = {
        'MSTID': dict(tid_period_s=20*60, dt_s=10.0,  block_s=10.0,
                      duration_s=70*60,   tid_amp_hz=0.8,
                      ground_truth_lag_s=1300.0),
        'LSTID': dict(tid_period_s=58*60, dt_s=1.0,   block_s=60.0,
                      duration_s=120*60,  tid_amp_hz=1.2,
                      ground_truth_lag_s=1320.0),
    }

    epsilons = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    snrs     = [30, 40, 50]

    all_results = []
    total = len(conditions) * len(epsilons) * len(snrs) * n_trials
    done = 0

    for tid_type, cparams in conditions.items():
        for epsilon, snr_db in product(epsilons, snrs):
            for trial in range(n_trials):
                seed = hash((tid_type, epsilon, snr_db, trial)) % (2**31)
                r = run_trial(
                    tid_period_s=cparams['tid_period_s'],
                    dt_s=cparams['dt_s'],
                    block_s=cparams['block_s'],
                    duration_s=cparams['duration_s'],
                    tid_amp_hz=cparams['tid_amp_hz'],
                    snr_db=snr_db,
                    epsilon=epsilon,
                    ground_truth_lag_s=cparams['ground_truth_lag_s'],
                    trial_seed=seed,
                )
                r['tid_type'] = tid_type
                all_results.append(r)
                done += 1

            if verbose:
                print(f"  {tid_type} eps={epsilon:.1f} SNR={snr_db}dB — done {n_trials} trials")

    return pd.DataFrame(all_results)


# ── Summary statistics ───────────────────────────────────────────────────────

def summarise(df):
    """Compute per-condition summary statistics."""
    rows = []
    for (tid_type, epsilon, snr_db), grp in df.groupby(['tid_type', 'epsilon', 'snr_db']):
        gt = grp['ground_truth_lag_s'].iloc[0]
        one_sample = grp['tid_period_s'].iloc[0] / (grp['tid_period_s'].iloc[0] / 60)
        # "correct lock" = |error| < 1.5 blocks
        block_s = 60.0 if tid_type == 'LSTID' else 10.0
        for method in ('fft', 'autocorr'):
            err = grp[f'{method}_lag_err_s']
            rows.append({
                'tid_type':    tid_type,
                'epsilon':     epsilon,
                'snr_db':      snr_db,
                'method':      method,
                'bias_s':      err.mean(),
                'rms_s':       np.sqrt((err**2).mean()),
                'mae_s':       err.abs().mean(),
                'correct_pct': (err.abs() < 1.5 * block_s).mean() * 100,
                'mean_r':      grp[f'{method}_r'].mean(),
                'std_r':       grp[f'{method}_r'].std(),
            })
    return pd.DataFrame(rows)


# ── Plotting ─────────────────────────────────────────────────────────────────

COLORS = {'fft': '#2196F3', 'autocorr': '#FF9800'}
LABELS = {'fft': 'FFT', 'autocorr': 'Autocorr'}
MARKERS = {'fft': 'o', 'autocorr': 's'}

def plot_results(summary, out_prefix='/home/claude'):
    """Generate four-panel comparison figure."""

    for tid_type in ('MSTID', 'LSTID'):
        sub = summary[summary.tid_type == tid_type]
        snrs = sorted(sub.snr_db.unique())
        epsilons = sorted(sub.epsilon.unique())

        fig = plt.figure(figsize=(15, 10))
        fig.suptitle(
            f'{tid_type}: FFT vs Autocorr Doppler Extraction Under E-Region Contamination\n'
            f'Monte Carlo N=50 trials per condition | epsilon = A_E / A_F',
            fontsize=13, fontweight='bold')

        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.32)

        # Panel 1: RMS lag error vs epsilon, per SNR, FFT
        # Panel 2: RMS lag error vs epsilon, per SNR, Autocorr
        # Panel 3: RMS lag error: FFT vs Autocorr at SNR=40dB
        # Panel 4: Correct lock rate vs epsilon at SNR=40dB
        # Panel 5: Mean cross-corr r vs epsilon at SNR=40dB
        # Panel 6: Bias vs epsilon at SNR=40dB

        axes = [fig.add_subplot(gs[i // 3, i % 3]) for i in range(6)]

        snr_colors = {30: '#e53935', 40: '#43a047', 50: '#1e88e5'}

        for method, ax_idx in [('fft', 0), ('autocorr', 1)]:
            ax = axes[ax_idx]
            for snr in snrs:
                d = sub[(sub.method == method) & (sub.snr_db == snr)]
                d = d.sort_values('epsilon')
                ax.plot(d.epsilon, d.rms_s, marker='o', lw=1.8,
                        color=snr_colors[snr], label=f'SNR={snr}dB')
                ax.fill_between(d.epsilon,
                                d.rms_s - d.rms_s*0.1,
                                d.rms_s + d.rms_s*0.1,
                                alpha=0.1, color=snr_colors[snr])
            ax.set_title(f'RMS Lag Error — {LABELS[method]}', fontsize=10)
            ax.set_xlabel('E-region contamination (epsilon)')
            ax.set_ylabel('RMS lag error (s)')
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            ax.set_xlim(-0.05, 1.05)

        # Panel 3: head-to-head RMS at SNR=40
        ax = axes[2]
        for method in ('fft', 'autocorr'):
            d = sub[(sub.method == method) & (sub.snr_db == 40)].sort_values('epsilon')
            ax.plot(d.epsilon, d.rms_s, marker=MARKERS[method], lw=2,
                    color=COLORS[method], label=LABELS[method])
        ax.set_title('RMS Lag Error: FFT vs Autocorr\n(SNR=40dB)', fontsize=10)
        ax.set_xlabel('E-region contamination (epsilon)')
        ax.set_ylabel('RMS lag error (s)')
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlim(-0.05, 1.05)

        # Panel 4: Correct lock rate
        ax = axes[3]
        for method in ('fft', 'autocorr'):
            d = sub[(sub.method == method) & (sub.snr_db == 40)].sort_values('epsilon')
            ax.plot(d.epsilon, d.correct_pct, marker=MARKERS[method], lw=2,
                    color=COLORS[method], label=LABELS[method])
        ax.axhline(95, color='gray', lw=0.8, ls='--', label='95% threshold')
        ax.set_title('Correct Peak Lock Rate\n(SNR=40dB)', fontsize=10)
        ax.set_xlabel('E-region contamination (epsilon)')
        ax.set_ylabel('Correct lock rate (%)')
        ax.set_ylim(0, 105)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlim(-0.05, 1.05)

        # Panel 5: Mean cross-correlation r
        ax = axes[4]
        for method in ('fft', 'autocorr'):
            d = sub[(sub.method == method) & (sub.snr_db == 40)].sort_values('epsilon')
            ax.plot(d.epsilon, d.mean_r, marker=MARKERS[method], lw=2,
                    color=COLORS[method], label=LABELS[method])
            ax.fill_between(d.epsilon,
                            d.mean_r - d.std_r,
                            d.mean_r + d.std_r,
                            alpha=0.15, color=COLORS[method])
        ax.set_title('Mean Cross-Corr Coefficient r\n(SNR=40dB, shaded=+/-1 std)', fontsize=10)
        ax.set_xlabel('E-region contamination (epsilon)')
        ax.set_ylabel('Mean r')
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlim(-0.05, 1.05)

        # Panel 6: Bias
        ax = axes[5]
        for method in ('fft', 'autocorr'):
            d = sub[(sub.method == method) & (sub.snr_db == 40)].sort_values('epsilon')
            ax.plot(d.epsilon, d.bias_s, marker=MARKERS[method], lw=2,
                    color=COLORS[method], label=LABELS[method])
        ax.axhline(0, color='k', lw=0.5)
        ax.set_title('Lag Bias (mean error)\n(SNR=40dB)', fontsize=10)
        ax.set_xlabel('E-region contamination (epsilon)')
        ax.set_ylabel('Bias (s)')
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlim(-0.05, 1.05)

        outpath = f'{out_prefix}/synthetic_{tid_type.lower()}_results.png'
        plt.savefig(outpath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f'Saved {outpath}')


def plot_example_signals(out_prefix='/home/claude'):
    """Show example synthetic Doppler traces at three contamination levels."""
    fig, axes = plt.subplots(3, 2, figsize=(14, 9), sharey='col')
    fig.suptitle('Example Synthetic Doppler Traces: FFT vs Autocorr\n'
                 'LSTID period=58 min, SNR=40dB, ground truth lag=1320s',
                 fontsize=12, fontweight='bold')

    epsilons = [0.0, 0.3, 0.7]
    labels = ['Clean (epsilon=0)', 'Mild contamination (epsilon=0.3)',
              'Moderate contamination (epsilon=0.7)']

    tid_period_s = 58 * 60
    dt_s = 1.0
    block_s = 60.0
    duration_s = 120 * 60
    tid_amp_hz = 1.2
    snr_db = 40
    ground_truth_lag_s = 1320.0

    for row, (eps, label) in enumerate(zip(epsilons, labels)):
        _, s1, f_true, _ = make_station(
            duration_s, dt_s, tid_period_s, tid_amp_hz, snr_db, eps,
            tid_phase=0.3, e_phase=1.1, lag_s=0.0
        )
        _, s2, _, _ = make_station(
            duration_s, dt_s, tid_period_s, tid_amp_hz, snr_db, eps,
            tid_phase=0.3, e_phase=2.4, lag_s=ground_truth_lag_s
        )

        d1_fft,  _ = extract_doppler_series(s1, 1.0/dt_s, block_s, 'fft')
        d1_ac,   _ = extract_doppler_series(s1, 1.0/dt_s, block_s, 'autocorr')
        d2_fft,  _ = extract_doppler_series(s2, 1.0/dt_s, block_s, 'fft')
        d2_ac,   _ = extract_doppler_series(s2, 1.0/dt_s, block_s, 'autocorr')

        n_blocks = len(d1_fft)
        t_min = np.arange(n_blocks) * block_s / 60.0

        # True F-region at block centres
        block_centres = (np.arange(n_blocks) + 0.5) * int(block_s / dt_s)
        f_true_blocks = f_true[block_centres.astype(int)]

        ax_left  = axes[row, 0]
        ax_right = axes[row, 1]

        ax_left.plot(t_min, f_true_blocks, 'k--', lw=1.0, label='True F-region', alpha=0.6)
        ax_left.plot(t_min, d1_fft,  color=COLORS['fft'],      lw=1.2, label='FFT stn1')
        ax_left.plot(t_min, d1_ac,   color=COLORS['autocorr'], lw=1.2, label='Autocorr stn1', alpha=0.8)
        ax_left.set_ylabel('Doppler (Hz)')
        ax_left.set_title(f'{label} — Station 1', fontsize=9)
        ax_left.legend(fontsize=7)
        ax_left.grid(alpha=0.3)
        ax_left.set_ylim(-2.5, 2.5)

        # Cross-correlation curves
        lag_f, r_f = xcorr_lag(d1_fft, d2_fft, block_s, max_lag_s=duration_s*0.45)
        lag_a, r_a = xcorr_lag(d1_ac,  d2_ac,  block_s, max_lag_s=duration_s*0.45)

        from scipy.signal import correlate as _corr
        def _cc_curve(y1, y2, dt):
            y1n = (y1-y1.mean())/(y1.std()+1e-12)
            y2n = (y2-y2.mean())/(y2.std()+1e-12)
            cc = _corr(y2n, y1n, mode='full') / len(y1)
            lags = np.arange(-(len(y1)-1), len(y1)) * dt / 60
            mask = np.abs(lags) <= duration_s*0.45/60
            return lags[mask], cc[mask]

        lags_f, cc_f = _cc_curve(d1_fft, d2_fft, block_s)
        lags_a, cc_a = _cc_curve(d1_ac,  d2_ac,  block_s)

        ax_right.plot(lags_f, cc_f, color=COLORS['fft'],      lw=1.5,
                      label=f'FFT r={r_f:.3f} @ {lag_f/60:+.1f}min')
        ax_right.plot(lags_a, cc_a, color=COLORS['autocorr'], lw=1.5, ls='--',
                      label=f'Autocorr r={r_a:.3f} @ {lag_a/60:+.1f}min')
        ax_right.axvline(ground_truth_lag_s/60, color='k', lw=1.0, ls=':', label='Truth')
        ax_right.axhline(0, color='k', lw=0.4)
        ax_right.set_title(f'{label} — Cross-correlation', fontsize=9)
        ax_right.set_xlabel('Lag (minutes)')
        ax_right.legend(fontsize=7)
        ax_right.grid(alpha=0.3)

    for ax in axes[-1]:
        ax.set_xlabel('Time (minutes)')
    axes[-1, 1].set_xlabel('Lag (minutes)')

    outpath = f'{out_prefix}/synthetic_example_signals.png'
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved {outpath}')


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Running Monte Carlo experiment (N=50 trials per condition)...")
    print("Conditions: 2 TID types x 7 epsilon x 3 SNR = 42 conditions, 2100 trials total")
    print()

    df = run_experiment(n_trials=50, verbose=True)
    df.to_csv('/home/claude/synthetic_results_raw.csv', index=False)
    print(f"\nRaw results saved: {len(df)} trials")

    summary = summarise(df)
    summary.to_csv('/home/claude/synthetic_results_summary.csv', index=False)
    print(f"Summary saved: {len(summary)} condition rows")

    print("\nGenerating example signal figure...")
    plot_example_signals('/home/claude')

    print("Generating performance figure...")
    plot_results(summary, '/home/claude')

    print("\nDone. Key results at SNR=40dB:")
    print()
    for tid_type in ('MSTID', 'LSTID'):
        print(f"  {tid_type}:")
        sub = summary[(summary.tid_type == tid_type) & (summary.snr_db == 40)]
        print(f"  {'epsilon':>8} {'FFT RMS':>10} {'AC RMS':>10} {'FFT lock%':>10} {'AC lock%':>10} {'FFT r':>8} {'AC r':>8}")
        for eps in sorted(sub.epsilon.unique()):
            row_f = sub[(sub.method=='fft')     & (sub.epsilon==eps)].iloc[0]
            row_a = sub[(sub.method=='autocorr')& (sub.epsilon==eps)].iloc[0]
            print(f"  {eps:>8.1f} {row_f.rms_s:>10.1f} {row_a.rms_s:>10.1f} "
                  f"{row_f.correct_pct:>10.1f} {row_a.correct_pct:>10.1f} "
                  f"{row_f.mean_r:>8.3f} {row_a.mean_r:>8.3f}")
        print()
