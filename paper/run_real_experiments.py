"""Run real-data + DP + HP-sensitivity experiments for the AHA-Fed paper.

Saves JSON histories under runs/paper/real/.

Experiments:
- D: PathMNIST 4-center federation (5 aggregators, 3 seeds)
- E: PathMNIST 8-center federation (5 aggregators, 1 seed)
- F: DP-SGD privacy-utility sweep (FedAvg vs AHA-Fed at ε ∈ {0.5, 1, 5})
- G: AHA-Fed (β, γ) hyperparameter sensitivity (5x5 grid)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
from torch.utils.data import DataLoader

from src.data.medmnist_loader import (
    federate_dirichlet,
    load_pathmnist,
    load_pneumoniamnist,
)
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer, build_aggregator
from src.models.backbones import build_model
from src.utils.seed import set_seed

OUT_DIR = ROOT / "runs" / "paper" / "real"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_clients(client_datasets, batch_size: int, device: str):
    return [
        FederatedClient(i, ds, batch_size=batch_size, device=device)
        for i, ds in enumerate(client_datasets)
    ]


def run_one(
    out_path: Path,
    aggregator: str,
    *,
    seed: int = 42,
    num_clients: int = 4,
    samples_per_client: int = 1000,
    num_classes: int = 9,
    heterogeneity: float = 0.5,
    noisy_client: int = 3,
    noisy_rate: float = 0.5,
    num_rounds: int = 25,
    local_epochs: int = 2,
    local_lr: float = 0.01,
    batch_size: int = 64,
    proximal_mu: float = 0.0,
    alpha: float = 1.0,
    beta: float = 4.0,
    gamma: float = 4.0,
    feddisco_a: float = 4.0,
    dataset: str = "pathmnist",
    eval_split: str = "test",
    dp_config: dict | None = None,
) -> dict:
    if out_path.exists():
        print(f"  [skip] {out_path.name} (already exists)")
        return json.loads(out_path.read_text())

    set_seed(seed)
    if dataset == "pathmnist":
        train_ds = load_pathmnist("train", image_size=28)
        test_ds = load_pathmnist(eval_split, image_size=28)
    elif dataset == "pneumoniamnist":
        train_ds = load_pneumoniamnist("train", image_size=28)
        test_ds = load_pneumoniamnist(eval_split, image_size=28)
    else:
        raise ValueError(f"unknown dataset {dataset}")

    rates = [0.0] * num_clients
    if 0 <= noisy_client < num_clients:
        rates[noisy_client] = noisy_rate
    client_ds = federate_dirichlet(
        train_ds,
        num_clients=num_clients,
        num_classes=num_classes,
        heterogeneity=heterogeneity,
        base_seed=seed,
        label_noise=rates,
        samples_per_client=samples_per_client,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    clients = build_clients(client_ds, batch_size=batch_size, device=device)

    eval_loader = DataLoader(test_ds, batch_size=128)
    arch = "med_cnn" if dataset in ("pathmnist", "pneumoniamnist") else "small_cnn"
    model = build_model(arch, num_classes=num_classes, pretrained=False)

    if aggregator == "adaptive":
        agg = build_aggregator(aggregator, alpha=alpha, beta=beta, gamma=gamma)
    elif aggregator == "feddisco":
        agg = build_aggregator(aggregator, a=feddisco_a)
    else:
        agg = build_aggregator(aggregator)

    server = FederatedServer(
        global_model=model,
        clients=clients,
        aggregator=agg,
        eval_loader=eval_loader,
        num_classes=num_classes,
        device=device,
    )
    history = server.run(
        num_rounds=num_rounds,
        local_epochs=local_epochs,
        local_lr=local_lr,
        proximal_mu=proximal_mu,
        eval_every=max(1, num_rounds // 10),
        dp_config=dp_config,
    )
    payload = {
        "config": {
            "aggregator": aggregator,
            "seed": seed,
            "num_clients": num_clients,
            "samples_per_client": samples_per_client,
            "num_classes": num_classes,
            "heterogeneity": heterogeneity,
            "noisy_client": noisy_client,
            "noisy_rate": noisy_rate,
            "num_rounds": num_rounds,
            "local_epochs": local_epochs,
            "local_lr": local_lr,
            "batch_size": batch_size,
            "proximal_mu": proximal_mu,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "feddisco_a": feddisco_a,
            "dataset": dataset,
            "eval_split": eval_split,
        },
        "dp_config": dp_config,
        "history": history,
        "final": history[-1] if history else None,
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    f = payload["final"] or {}
    auroc = f.get("auroc")
    auroc_s = f"{auroc:.3f}" if auroc is not None else "n/a"
    print(f"  [done] {out_path.name}  acc={f.get('accuracy',0):.3f} "
          f"auroc={auroc_s} ece={f.get('ece',0):.3f}")
    return payload


# =========================================================
def matrix_d_real():
    """5 aggregators x 3 seeds on PathMNIST."""
    print("\n=== Matrix D: PathMNIST 4-center, 5 aggregators, 3 seeds ===")
    aggs = {
        "fedavg":   {"aggregator": "fedavg"},
        "fedprox":  {"aggregator": "fedprox", "proximal_mu": 0.01},
        "fedbn":    {"aggregator": "fedbn"},
        "feddisco": {"aggregator": "feddisco", "feddisco_a": 4.0},
        "aha_fed":  {"aggregator": "adaptive", "alpha": 1.0, "beta": 4.0, "gamma": 4.0},
    }
    seeds = [42, 123, 456]
    for tag, kw in aggs.items():
        for s in seeds:
            run_one(OUT_DIR / f"path_{tag}_s{s}.json", seed=s, **kw)


def matrix_e_pneumonia():
    """5 aggregators on PneumoniaMNIST (binary CXR)."""
    print("\n=== Matrix E: PneumoniaMNIST 4-center, 5 aggregators, 1 seed ===")
    aggs = {
        "fedavg":   {"aggregator": "fedavg"},
        "fedprox":  {"aggregator": "fedprox", "proximal_mu": 0.01},
        "fedbn":    {"aggregator": "fedbn"},
        "feddisco": {"aggregator": "feddisco", "feddisco_a": 4.0},
        "aha_fed":  {"aggregator": "adaptive", "alpha": 1.0, "beta": 4.0, "gamma": 4.0},
    }
    for tag, kw in aggs.items():
        run_one(OUT_DIR / f"pneu_{tag}.json",
                dataset="pneumoniamnist", num_classes=2,
                samples_per_client=300, num_rounds=20, **kw)


def matrix_f_dp():
    """DP-SGD privacy-utility sweep, FedAvg vs AHA-Fed."""
    print("\n=== Matrix F: DP-SGD privacy-utility sweep ===")
    targets = [0.5, 1.0, 5.0]
    for eps in targets:
        dp_cfg = {"epsilon": eps, "delta": 1e-5, "max_grad_norm": 1.0}
        run_one(OUT_DIR / f"path_fedavg_dp_eps{eps}.json",
                aggregator="fedavg", dp_config=dp_cfg,
                num_rounds=15, samples_per_client=300, batch_size=64,
                local_lr=0.05)
        run_one(OUT_DIR / f"path_aha_dp_eps{eps}.json",
                aggregator="adaptive", alpha=1.0, beta=4.0, gamma=4.0,
                dp_config=dp_cfg,
                num_rounds=15, samples_per_client=300, batch_size=64,
                local_lr=0.05)


def matrix_g_hp():
    """AHA-Fed (β, γ) sensitivity grid on PathMNIST (one seed)."""
    print("\n=== Matrix G: AHA-Fed (beta, gamma) sensitivity grid ===")
    grid = [0, 1, 2, 4, 8]
    for b in grid:
        for g in grid:
            tag = f"hp_b{b}_g{g}"
            run_one(OUT_DIR / f"{tag}.json",
                    aggregator="adaptive",
                    alpha=1.0, beta=float(b), gamma=float(g),
                    num_rounds=20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--pneumonia", action="store_true")
    parser.add_argument("--dp", action="store_true")
    parser.add_argument("--hp", action="store_true")
    args = parser.parse_args()

    if args.all or not (args.real or args.pneumonia or args.dp or args.hp):
        matrix_d_real()
        matrix_e_pneumonia()
        matrix_f_dp()
        matrix_g_hp()
        return
    if args.real:        matrix_d_real()
    if args.pneumonia:   matrix_e_pneumonia()
    if args.dp:          matrix_f_dp()
    if args.hp:          matrix_g_hp()


if __name__ == "__main__":
    main()
