"""Regenerate the paper's synthetic-sourced figures from real-data runs.

Six figures in the paper were drawn from the synthetic benchmark by
``make_figures.py``. This script redraws each from runs/paper/real/ so the
paper can drop the synthetic benchmark entirely:

    fig_dataset       real MedMNIST samples + per-hospital label priors
    fig_convergence   convergence on PathMNIST under 50% client noise
    fig_final_bars    PneumoniaMNIST final metrics with seed error bars
    fig_noise_sweep   label-noise sweep (the former headline claim)
    fig_het_scale     heterogeneity sweep + client-count scaling
    fig_weights       per-client AHA-Fed weights over rounds

Every number plotted comes from a run artifact; nothing is illustrative.

Run:  python paper/make_real_only_figures.py
"""
from __future__ import annotations

import glob
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REAL = ROOT / "runs" / "paper" / "real"
FIGS = ROOT / "paper" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "savefig.dpi": 400,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

C_AHA, C_AVG = "#C0392B", "#2C3E50"
C_OTHER = ["#7F8C8D", "#16A085", "#8E44AD"]


def load(name: str) -> dict | None:
    p = REAL / name
    return json.loads(p.read_text()) if p.exists() else None


def hist(name: str) -> list[dict]:
    d = load(name)
    return (d or {}).get("history", [])


def finals(pattern: str, key: str) -> list[float]:
    out = []
    for f in sorted(glob.glob(str(REAL / pattern))):
        d = json.loads(Path(f).read_text())
        v = (d.get("final") or (d.get("history") or [{}])[-1]).get(key)
        if v is not None:
            out.append(v)
    return out


def ms(vals: list[float]) -> tuple[float, float]:
    return (st.mean(vals), st.pstdev(vals)) if vals else (float("nan"), 0.0)


def save(fig, name: str) -> None:
    fig.savefig(FIGS / name, dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {name}")


# ---------------------------------------------------------------- fig_dataset
def fig_dataset() -> None:
    """Real MedMNIST samples plus the Dirichlet label priors actually used."""
    from src.data.medmnist_loader import federate_dirichlet, load_pathmnist

    ds = load_pathmnist("train", image_size=28)
    cfg = (load("real_het_aha_h0.5.json") or {}).get("config", {})
    clients = federate_dirichlet(
        ds,
        num_clients=cfg.get("num_clients", 4),
        num_classes=cfg.get("num_classes", 9),
        heterogeneity=cfg.get("heterogeneity", 0.5),
        base_seed=cfg.get("seed", 42),
        label_noise=[0.0] * cfg.get("num_clients", 4),
        samples_per_client=cfg.get("samples_per_client", 1000),
    )

    fig = plt.figure(figsize=(11, 4.2))
    gs = fig.add_gridspec(2, 6, width_ratios=[1, 1, 1, 1, 0.25, 2.4])

    for i in range(8):
        ax = fig.add_subplot(gs[i // 4, i % 4])
        img, lab = ds[i]
        arr = img.numpy() if hasattr(img, "numpy") else np.asarray(img)
        arr = np.transpose(arr, (1, 2, 0)) if arr.ndim == 3 and arr.shape[0] in (1, 3) else arr
        arr = arr.squeeze()
        ax.imshow(arr, cmap="gray" if arr.ndim == 2 else None)
        ax.set_title(f"class {int(lab)}", fontsize=8, pad=2)
        ax.axis("off")

    ax = fig.add_subplot(gs[:, 5])
    ncls = cfg.get("num_classes", 9)
    width = 0.8 / len(clients)
    for k, sub in enumerate(clients):
        # federate_dirichlet returns _NoisedView (own .y) or Subset (.dataset.y).
        y = (sub.y.numpy() if hasattr(sub, "y")
             else np.array([int(sub.dataset.y[i]) for i in sub.indices]))
        counts = np.bincount(y.astype(int), minlength=ncls) / max(1, len(y))
        ax.bar(np.arange(ncls) + k * width - 0.4, counts, width,
               label=f"hospital {k + 1}")
    ax.set_xlabel("class")
    ax.set_ylabel("label prior")
    ax.set_title(f"PathMNIST, Dirichlet heterogeneity {cfg.get('heterogeneity', 0.5)}")
    ax.set_xticks(range(ncls))
    ax.legend(frameon=False, fontsize=8)

    fig.suptitle("Real PathMNIST federation (MedMNIST v2) — samples and per-hospital label priors",
                 fontsize=12, y=1.02)
    save(fig, "fig_dataset.png")


# ------------------------------------------------------------ fig_convergence
def fig_convergence() -> None:
    """Accuracy and ECE per round on PathMNIST with 50% noise at one client."""
    runs = {
        "AHA-Fed": ("real_noise_aha_n0.5_s42.json", C_AHA),
        "FedAvg": ("real_noise_fedavg_n0.5_s42.json", C_AVG),
    }
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for label, (fname, color) in runs.items():
        h = hist(fname)
        if not h:
            continue
        rounds = [r.get("round", i + 1) for i, r in enumerate(h)]
        for ax, key, name in ((axes[0], "accuracy", "accuracy"),
                              (axes[1], "ece", "ECE")):
            ys = [(r.get(key), rd) for r, rd in zip(h, rounds) if r.get(key) is not None]
            if ys:
                ax.plot([b for _, b in ys], [a for a, _ in ys], "o-",
                        color=color, label=label, lw=1.8, ms=3.5)
            ax.set_xlabel("communication round")
            ax.set_ylabel(name)
    axes[0].set_title("Accuracy")
    axes[1].set_title("Calibration error (lower is better)")
    axes[0].legend(frameon=False)
    fig.suptitle("PathMNIST, 4 hospitals, 50% label noise at one client (seed 42)",
                 fontsize=12, y=1.02)
    save(fig, "fig_convergence.png")


# ------------------------------------------------------------- fig_final_bars
def fig_final_bars() -> None:
    """PneumoniaMNIST final metrics across seeds — real chest radiography."""
    methods = ["aha_fed", "fedavg", "fedprox", "fedbn", "feddisco"]
    names = ["AHA-Fed", "FedAvg", "FedProx", "FedBN", "FedDisco"]
    colors = [C_AHA, C_AVG] + C_OTHER

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9))
    for ax, key, title, better in (
        (axes[0], "ece", "ECE (lower is better)", "lower"),
        (axes[1], "accuracy", "Accuracy", "higher"),
        (axes[2], "auroc", "AUROC", "higher"),
    ):
        means, errs = [], []
        for m in methods:
            mu, sd = ms(finals(f"pneu_{m}_s*.json", key))
            means.append(mu)
            errs.append(sd)
        ax.bar(names, means, yerr=errs, capsize=4, color=colors,
               edgecolor="black", linewidth=0.6)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=30)
        finite = [v for v in means if v == v]
        if finite and better == "higher":
            ax.set_ylim(min(finite) * 0.9, max(finite) * 1.06)
    fig.suptitle("PneumoniaMNIST (chest radiography), 4 hospitals, mean ± s.d. over 3 seeds",
                 fontsize=12, y=1.04)
    save(fig, "fig_final_bars.png")


# ------------------------------------------------------------ fig_noise_sweep
def fig_noise_sweep() -> None:
    """Label-noise sweep on both real datasets, with seed spread shown."""
    rates = [0.0, 0.3, 0.5, 0.7]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    for label, tag, color in (("AHA-Fed", "aha", C_AHA), ("FedAvg", "fedavg", C_AVG)):
        mus, sds = [], []
        for r in rates:
            mu, sd = ms(finals(f"real_noise_{tag}_n{r}_s*.json", "ece"))
            mus.append(mu)
            sds.append(sd)
        axes[0].errorbar([r * 100 for r in rates], mus, yerr=sds, fmt="o-",
                         color=color, label=label, lw=1.8, ms=5, capsize=4)

        vals = [(load(f"pneu_noise_{tag}_n{r}.json") or {}).get("final", {}).get("ece")
                for r in rates]
        axes[1].plot([r * 100 for r in rates], vals, "s-", color=color,
                     label=label, lw=1.8, ms=5)

    axes[0].set_title("PathMNIST — mean ± s.d. over 3 seeds")
    axes[1].set_title("PneumoniaMNIST (chest radiography) — 1 seed")
    for ax in axes:
        ax.set_xlabel("label noise at the corrupted client (%)")
        ax.set_ylabel("ECE")
        ax.legend(frameon=False)
    fig.suptitle("Calibration under client label noise, real data",
                 fontsize=12, y=1.02)
    save(fig, "fig_noise_sweep.png")


# -------------------------------------------------------------- fig_het_scale
def fig_het_scale() -> None:
    """Heterogeneity sweep and client-count scaling, both on PathMNIST."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    levels = [0.0, 0.3, 0.5, 0.7, 0.9]
    for label, tag, color in (("AHA-Fed", "aha", C_AHA), ("FedAvg", "fedavg", C_AVG)):
        vals = [(load(f"real_het_{tag}_h{h}.json") or {}).get("final", {}).get("ece")
                for h in levels]
        axes[0].plot(levels, vals, "o-", color=color, label=label, lw=1.8, ms=5)
    axes[0].set_xlabel("Dirichlet heterogeneity")
    axes[0].set_ylabel("ECE")
    axes[0].set_title("Heterogeneity sweep")

    ks = [4, 8, 12]
    width = 0.36
    for i, (label, tag, color) in enumerate(
            (("AHA-Fed", "aha", C_AHA), ("FedAvg", "fedavg", C_AVG))):
        vals = [(load(f"real_scale_{tag}_k{k}.json") or {}).get("final", {}).get("ece")
                for k in ks]
        axes[1].bar(np.arange(len(ks)) + (i - 0.5) * width, vals, width,
                    color=color, label=label, edgecolor="black", linewidth=0.6)
    axes[1].set_xticks(range(len(ks)))
    axes[1].set_xticklabels([f"K = {k}" for k in ks])
    axes[1].set_ylabel("ECE")
    axes[1].set_title("Client-count scaling (one noisy client each)")

    for ax in axes:
        ax.legend(frameon=False)
    fig.suptitle("PathMNIST: heterogeneity and federation size", fontsize=12, y=1.02)
    save(fig, "fig_het_scale.png")


# ---------------------------------------------------------------- fig_weights
def fig_weights() -> None:
    """AHA-Fed's per-client weights over rounds, with the noisy client marked."""
    d = load("real_noise_aha_n0.5_s42.json")
    h = (d or {}).get("history", [])
    series = [r["client_weights"] for r in h if r.get("client_weights")]
    if not series:
        print("  skip fig_weights.png (no client_weights recorded)")
        return

    w = np.asarray(series, dtype=float)
    noisy = (d.get("config") or {}).get("noisy_client")
    rounds = np.arange(1, len(w) + 1)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for k in range(w.shape[1]):
        is_noisy = k == noisy
        ax.plot(rounds, w[:, k], "o-" if is_noisy else "-",
                color=C_AHA if is_noisy else C_OTHER[k % len(C_OTHER)],
                lw=2.2 if is_noisy else 1.5, ms=3,
                label=f"hospital {k + 1}" + (" (50% noise)" if is_noisy else ""))
    ax.axhline(1.0 / w.shape[1], color="gray", ls=":", lw=1.2,
               label=f"uniform ({1 / w.shape[1]:.3f})")
    ax.set_xlabel("communication round")
    ax.set_ylabel("aggregation weight")
    ax.set_title("AHA-Fed client weights — PathMNIST, 50% noise at one client")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "fig_weights.png")


if __name__ == "__main__":
    print("Regenerating synthetic-sourced figures from real runs:")
    for fn in (fig_dataset, fig_convergence, fig_final_bars,
               fig_noise_sweep, fig_het_scale, fig_weights):
        try:
            fn()
        except Exception as exc:  # keep going; report what failed
            print(f"  FAILED {fn.__name__}: {type(exc).__name__}: {exc}")
    print("Done.")
