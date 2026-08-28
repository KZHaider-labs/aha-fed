"""Run all experiments needed for the AHA-Fed paper.

Saves JSON histories under runs/paper/. Reuses the existing run_experiment.py
machinery so we get identical training code paths and metric definitions.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
from torch.utils.data import DataLoader

from src.data.datasets import SyntheticMedicalImaging
from src.data.partitioning import make_synthetic_clients
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer, build_aggregator
from src.models.backbones import build_model
from src.utils.seed import set_seed

OUT_DIR = ROOT / "runs" / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_one(
    out_path: Path,
    aggregator: str,
    *,
    seed: int = 42,
    num_clients: int = 4,
    samples_per_client: int = 200,
    num_classes: int = 4,
    image_size: int = 32,
    heterogeneity: float = 0.7,
    noisy_client: int = 3,
    noisy_rate: float = 0.5,
    num_rounds: int = 30,
    local_epochs: int = 1,
    local_lr: float = 0.01,
    batch_size: int = 32,
    proximal_mu: float = 0.0,
    alpha: float = 1.0,
    beta: float = 4.0,
    gamma: float = 4.0,
) -> dict:
    set_seed(seed)
    rates = [0.0] * num_clients
    if 0 <= noisy_client < num_clients:
        rates[noisy_client] = noisy_rate
    client_ds = make_synthetic_clients(
        num_clients=num_clients,
        samples_per_client=samples_per_client,
        num_classes=num_classes,
        image_size=image_size,
        heterogeneity=heterogeneity,
        base_seed=seed,
        label_noise=rates,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    clients = [
        FederatedClient(i, ds, batch_size=batch_size, device=device)
        for i, ds in enumerate(client_ds)
    ]
    eval_dataset = SyntheticMedicalImaging(
        num_samples=400,
        num_classes=num_classes,
        image_size=image_size,
        center_id=0,
        center_offset=0.0,
        seed=seed + 9999,
    )
    eval_loader = DataLoader(eval_dataset, batch_size=batch_size)
    model = build_model("small_cnn", num_classes=num_classes, pretrained=False)
    if aggregator == "adaptive":
        agg = build_aggregator(aggregator, alpha=alpha, beta=beta, gamma=gamma)
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
        eval_every=max(1, num_rounds // 15),
    )
    payload = {
        "config": {
            "aggregator": aggregator,
            "seed": seed,
            "num_clients": num_clients,
            "samples_per_client": samples_per_client,
            "num_classes": num_classes,
            "image_size": image_size,
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
        },
        "history": history,
        "final": history[-1] if history else None,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  [done] {out_path.name}")
    return payload


def matrix_a_multiseed():
    """Multi-seed sweep across 4 aggregators."""
    seeds = [42, 123, 456]
    aggs = {
        "fedavg":   {"aggregator": "fedavg"},
        "fedprox":  {"aggregator": "fedprox", "proximal_mu": 0.01},
        "fedbn":    {"aggregator": "fedbn"},
        "aha_fed":  {"aggregator": "adaptive", "alpha": 1.0, "beta": 4.0, "gamma": 4.0},
    }
    print("\n=== Matrix A: multi-seed (3 seeds x 4 aggregators) ===")
    for tag, kwargs in aggs.items():
        for seed in seeds:
            out = OUT_DIR / f"seed_{tag}_s{seed}.json"
            run_one(out, seed=seed, **kwargs)


def matrix_b_heterogeneity():
    """Heterogeneity sweep for FedAvg vs AHA-Fed."""
    levels = [0.0, 0.3, 0.5, 0.7, 0.9]
    print("\n=== Matrix B: heterogeneity sweep (5 levels x 2 aggregators) ===")
    for h in levels:
        run_one(OUT_DIR / f"het_fedavg_h{h}.json",
                aggregator="fedavg", heterogeneity=h)
        run_one(OUT_DIR / f"het_aha_h{h}.json",
                aggregator="adaptive", heterogeneity=h,
                alpha=1.0, beta=4.0, gamma=4.0)


def matrix_c_clients():
    """Scaling: 4 vs 8 vs 12 clients (each with 1 noisy)."""
    print("\n=== Matrix C: client-count scaling ===")
    for nc in [4, 8, 12]:
        spc = max(50, 800 // nc)
        run_one(OUT_DIR / f"scale_fedavg_k{nc}.json",
                aggregator="fedavg", num_clients=nc,
                samples_per_client=spc, noisy_client=nc - 1)
        run_one(OUT_DIR / f"scale_aha_k{nc}.json",
                aggregator="adaptive", num_clients=nc,
                samples_per_client=spc, noisy_client=nc - 1,
                alpha=1.0, beta=4.0, gamma=4.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--seeds", action="store_true")
    parser.add_argument("--het", action="store_true")
    parser.add_argument("--scale", action="store_true")
    args = parser.parse_args()
    if args.all or not (args.seeds or args.het or args.scale):
        matrix_a_multiseed()
        matrix_b_heterogeneity()
        matrix_c_clients()
        return
    if args.seeds:
        matrix_a_multiseed()
    if args.het:
        matrix_b_heterogeneity()
    if args.scale:
        matrix_c_clients()


if __name__ == "__main__":
    main()
