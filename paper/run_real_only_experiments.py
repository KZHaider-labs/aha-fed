"""Real-data replacements for every experiment the paper previously ran on
the synthetic benchmark.

Each matrix here mirrors one in ``run_experiments.py`` (synthetic) but runs on
real MedMNIST v2 data, so the paper can drop the synthetic benchmark entirely:

    synthetic matrix A (multi-seed)      -> R1  PathMNIST + PneumoniaMNIST
    synthetic matrix B (heterogeneity)   -> R2  PathMNIST
    synthetic matrix C (client scaling)  -> R3  PathMNIST
    synthetic noise sweep                -> R4  PathMNIST + PneumoniaMNIST

Plus R5, which has no synthetic counterpart: a (beta, gamma) grid on
PneumoniaMNIST, since the multi-seed chest-radiography runs inherited
hyperparameters tuned on 9-class PathMNIST.

Results land in runs/paper/real/ alongside the existing real-data runs and are
skipped if the JSON already exists, so the script is resumable.

Run:
    python paper/run_real_only_experiments.py --all
    python paper/run_real_only_experiments.py --noise --pneuhp
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paper.run_real_experiments import OUT_DIR, run_one  # noqa: E402

# PneumoniaMNIST is binary and much smaller than PathMNIST, so it gets its own
# sample budget; everything else matches the PathMNIST settings already used in
# run_real_experiments.matrix_d_real so results stay comparable.
PNEU = {"dataset": "pneumoniamnist", "num_classes": 2, "samples_per_client": 300}
PATH = {"dataset": "pathmnist", "num_classes": 9, "samples_per_client": 1000}

AGGS = {
    "fedavg":   {"aggregator": "fedavg"},
    "fedprox":  {"aggregator": "fedprox", "proximal_mu": 0.01},
    "fedbn":    {"aggregator": "fedbn"},
    "feddisco": {"aggregator": "feddisco", "feddisco_a": 4.0},
    "aha_fed":  {"aggregator": "adaptive", "alpha": 1.0, "beta": 4.0, "gamma": 4.0},
}
SEEDS = [42, 123, 456]


def r1_pneumonia_multiseed() -> None:
    """PneumoniaMNIST across 5 aggregators x 3 seeds (was 1 seed).

    Gives the paper a real chest-radiography result with error bars, which the
    synthetic benchmark was previously standing in for.
    """
    print("\n=== R1: PneumoniaMNIST 4-center, 5 aggregators, 3 seeds ===")
    for tag, kw in AGGS.items():
        for seed in SEEDS:
            run_one(OUT_DIR / f"pneu_{tag}_s{seed}.json",
                    seed=seed, num_rounds=20, **PNEU, **kw)


def r2_heterogeneity() -> None:
    """Heterogeneity sweep on real data (mirrors synthetic matrix B).

    Seed 42 keeps the original single-seed filenames; the extra seeds add a
    _s<seed> suffix, so both naming schemes resolve for existing analysis code.
    """
    print("\n=== R2: PathMNIST heterogeneity sweep (5 levels x 2 aggregators x 3 seeds) ===")
    for h in [0.0, 0.3, 0.5, 0.7, 0.9]:
        for seed in SEEDS:
            suffix = "" if seed == 42 else f"_s{seed}"
            run_one(OUT_DIR / f"real_het_fedavg_h{h}{suffix}.json",
                    aggregator="fedavg", heterogeneity=h, seed=seed, **PATH)
            run_one(OUT_DIR / f"real_het_aha_h{h}{suffix}.json",
                    aggregator="adaptive", alpha=1.0, beta=4.0, gamma=4.0,
                    heterogeneity=h, seed=seed, **PATH)


def r3_client_scaling() -> None:
    """Client-count scaling on real data (mirrors synthetic matrix C)."""
    print("\n=== R3: PathMNIST client-count scaling (K = 4, 8, 12) ===")
    for nc in [4, 8, 12]:
        # Hold the federation's total sample budget roughly constant as K grows.
        spc = max(200, 4000 // nc)
        common = {"dataset": "pathmnist", "num_classes": 9,
                  "num_clients": nc, "samples_per_client": spc,
                  "noisy_client": nc - 1}
        for seed in SEEDS:
            suffix = "" if seed == 42 else f"_s{seed}"
            run_one(OUT_DIR / f"real_scale_fedavg_k{nc}{suffix}.json",
                    aggregator="fedavg", seed=seed, **common)
            run_one(OUT_DIR / f"real_scale_aha_k{nc}{suffix}.json",
                    aggregator="adaptive", alpha=1.0, beta=4.0, gamma=4.0,
                    seed=seed, **common)


def r4_noise_sweep() -> None:
    """Label-noise sweep on real data — the paper's headline robustness claim.

    This is the experiment that most needed to move off synthetic data: it is
    what the 3-fold ECE reduction was based on.
    """
    print("\n=== R4: label-noise sweep 0-70% (PathMNIST + PneumoniaMNIST) ===")
    for rate in [0.0, 0.3, 0.5, 0.7]:
        for seed in SEEDS:
            run_one(OUT_DIR / f"real_noise_fedavg_n{rate}_s{seed}.json",
                    aggregator="fedavg", noisy_rate=rate, seed=seed, **PATH)
            run_one(OUT_DIR / f"real_noise_aha_n{rate}_s{seed}.json",
                    aggregator="adaptive", alpha=1.0, beta=4.0, gamma=4.0,
                    noisy_rate=rate, seed=seed, **PATH)
        # Chest-radiography counterpart, single seed to keep the runtime sane.
        run_one(OUT_DIR / f"pneu_noise_fedavg_n{rate}.json",
                aggregator="fedavg", noisy_rate=rate, num_rounds=20, **PNEU)
        run_one(OUT_DIR / f"pneu_noise_aha_n{rate}.json",
                aggregator="adaptive", alpha=1.0, beta=4.0, gamma=4.0,
                noisy_rate=rate, num_rounds=20, **PNEU)



def r5_pneumonia_hp() -> None:
    """(beta, gamma) sensitivity for AHA-Fed on PneumoniaMNIST.

    The multi-seed PneumoniaMNIST runs reuse PathMNIST's beta=gamma=4, tuned on
    a 9-class task. Binary chest radiography has a very different label-prior
    geometry, so this grid checks whether AHA-Fed's showing there is a property
    of the method or of an untuned hyperparameter.
    """
    print("\n=== R5: PneumoniaMNIST (beta, gamma) grid ===")
    for b in [0, 1, 2, 4, 8]:
        for g in [0, 1, 2, 4, 8]:
            run_one(OUT_DIR / f"pneu_hp_b{b}_g{g}.json",
                    aggregator="adaptive", alpha=1.0,
                    beta=float(b), gamma=float(g),
                    num_rounds=20, **PNEU)


MATRICES = {
    "pneu": r1_pneumonia_multiseed,
    "het": r2_heterogeneity,
    "scale": r3_client_scaling,
    "noise": r4_noise_sweep,
    "pneuhp": r5_pneumonia_hp,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    for name in MATRICES:
        parser.add_argument(f"--{name}", action="store_true")
    args = parser.parse_args()

    picked = [n for n in MATRICES if getattr(args, n)]
    if args.all or not picked:
        picked = list(MATRICES)
    for name in picked:
        MATRICES[name]()
    print("\nDone. Re-run paper/verify_claims.py to re-check the paper.")


if __name__ == "__main__":
    main()

