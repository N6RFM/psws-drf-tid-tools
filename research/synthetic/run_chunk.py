"""
run_chunk.py  --tid MSTID --snr 30 --trials 50 --out /home/claude/chunks/
Runs one (tid_type, snr_db) chunk of the Monte Carlo experiment.
"""
import argparse
import numpy as np
import pandas as pd
import warnings
import sys
sys.path.insert(0, '/home/claude')
warnings.filterwarnings('ignore')

from synthetic_tid_experiment import (make_station, extract_doppler_series, xcorr_lag)

CONFIGS = {
    'MSTID': dict(tid_period_s=20*60, dt_iq=0.1,  block_s=10.0,
                  duration_s=120*60,  tid_amp_hz=0.8,  gt_lag=300.0),
    'LSTID': dict(tid_period_s=58*60, dt_iq=1.0,  block_s=60.0,
                  duration_s=120*60,  tid_amp_hz=1.2,  gt_lag=1320.0),
}
EPSILONS = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

def run_trial(cfg, snr_db, epsilon, seed):
    rng = np.random.default_rng(seed)
    ph  = rng.uniform(0, 2*np.pi)
    ep1 = rng.uniform(0, 2*np.pi)
    ep2 = rng.uniform(0, 2*np.pi)
    fs  = 1.0 / cfg['dt_iq']

    _, s1, _, _ = make_station(cfg['duration_s'], cfg['dt_iq'],
                               cfg['tid_period_s'], cfg['tid_amp_hz'],
                               snr_db, epsilon,
                               tid_phase=ph, e_phase=ep1, lag_s=0.0)
    _, s2, _, _ = make_station(cfg['duration_s'], cfg['dt_iq'],
                               cfg['tid_period_s'], cfg['tid_amp_hz'],
                               snr_db, epsilon,
                               tid_phase=ph, e_phase=ep2, lag_s=cfg['gt_lag'])

    max_lag = cfg['duration_s'] * 0.40
    out = {'tid_type': args.tid, 'snr_db': snr_db, 'epsilon': epsilon,
           'gt_lag': cfg['gt_lag'], 'tid_period_s': cfg['tid_period_s']}
    for method in ('fft', 'autocorr'):
        d1, _ = extract_doppler_series(s1, fs, cfg['block_s'], method)
        d2, _ = extract_doppler_series(s2, fs, cfg['block_s'], method)
        lag, r = xcorr_lag(d1, d2, cfg['block_s'], max_lag_s=max_lag)
        out[f'{method}_lag']  = lag
        out[f'{method}_err']  = lag - cfg['gt_lag']
        out[f'{method}_r']    = r
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tid',    required=True, choices=['MSTID','LSTID'])
    parser.add_argument('--snr',    required=True, type=int)
    parser.add_argument('--trials', default=50,    type=int)
    parser.add_argument('--out',    default='/home/claude/chunks/')
    args = parser.parse_args()

    cfg = CONFIGS[args.tid]
    rows = []
    for epsilon in EPSILONS:
        for trial in range(args.trials):
            seed = hash((args.tid, args.snr, epsilon, trial)) % (2**31)
            r = run_trial(cfg, args.snr, epsilon, seed)
            r['trial'] = trial
            rows.append(r)
        print(f"  {args.tid} SNR={args.snr} eps={epsilon:.1f} done {args.trials} trials")

    df = pd.DataFrame(rows)
    import os; os.makedirs(args.out, exist_ok=True)
    outpath = f"{args.out}/chunk_{args.tid}_{args.snr}dB.csv"
    df.to_csv(outpath, index=False)
    print(f"Saved {outpath}  ({len(df)} rows)")
