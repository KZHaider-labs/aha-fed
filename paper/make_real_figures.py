"""Generate the new real-data, DP, and HP-sensitivity figures.

Reads from runs/paper/real/*.json. Outputs PNGs to paper/figures/.
"""
from __future__ import annotations

import json
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

PALETTE = {
    "fedavg":   "#1f77b4",
    "fedprox":  "#ff7f0e",
    "fedbn":    "#2ca02c",
    "feddisco": "#9467bd",
    "aha_fed":  "#d62728",
}
LABELS = {
    "fedavg":   "FedAvg",
    "fedprox":  "FedProx",
    "fedbn":    "FedBN",
    "feddisco": "FedDisco",
    "aha_fed":  "AHA-Fed (ours)",
}
SEEDS = [7, 13, 21, 42, 99, 123, 456, 555, 2024, 31337]


def load_path_seeds(tag: str):
    accs, aurocs, eces, losses = [], [], [], []
    for s in SEEDS:
        d = json.loads((REAL / f"path_{tag}_s{s}.json").read_text())
        f = d["final"]
        accs.append(f["accuracy"])
        aurocs.append(f["auroc"])
        eces.append(f["ece"])
        losses.append(f["loss"])
    return (np.array(accs), np.array(aurocs), np.array(eces), np.array(losses))


# =====================================================================
#       FIGURE — REAL DATA: 5-aggregator comparison (PathMNIST)
# =====================================================================
def fig_real_data():
    tags = ["fedavg", "fedprox", "fedbn", "feddisco", "aha_fed"]
    accs_m, accs_s, aurocs_m, aurocs_s = [], [], [], []
    eces_m, eces_s = [], []
    for t in tags:
        a, ar, e, _ = load_path_seeds(t)
        accs_m.append(a.mean()); accs_s.append(a.std())
        aurocs_m.append(ar.mean()); aurocs_s.append(ar.std())
        eces_m.append(e.mean()); eces_s.append(e.std())

    fig, axes = plt.subplots(3, 1, figsize=(3.4, 5.0))
    x = np.arange(len(tags))
    colors = [PALETTE[t] for t in tags]

    bars = axes[0].bar(x, accs_m, yerr=accs_s, color=colors, edgecolor="black",
                       linewidth=0.8, capsize=5, error_kw={"linewidth": 1.3})
    axes[0].set_xticks(x); axes[0].set_xticklabels([LABELS[t] for t in tags], rotation=15)
    axes[0].set_ylabel("Test accuracy")
    axes[0].set_title("(a) Accuracy")
    for bar, m, s in zip(bars, accs_m, accs_s):
        axes[0].text(bar.get_x()+bar.get_width()/2, m+s+0.005,
                     f"{m:.3f}", ha="center", fontsize=9)
    axes[0].set_ylim(0, max(np.array(accs_m)+np.array(accs_s))*1.18)

    bars = axes[1].bar(x, aurocs_m, yerr=aurocs_s, color=colors,
                       edgecolor="black", linewidth=0.8, capsize=5,
                       error_kw={"linewidth": 1.3})
    axes[1].set_xticks(x); axes[1].set_xticklabels([LABELS[t] for t in tags], rotation=15)
    axes[1].set_ylabel("AUROC (macro)")
    axes[1].set_title("(b) AUROC")
    for bar, m in zip(bars, aurocs_m):
        axes[1].text(bar.get_x()+bar.get_width()/2, m+0.003,
                     f"{m:.3f}", ha="center", fontsize=9)
    axes[1].set_ylim(0.9, 1.0)

    bars = axes[2].bar(x, eces_m, yerr=eces_s, color=colors,
                       edgecolor="black", linewidth=0.8, capsize=5,
                       error_kw={"linewidth": 1.3})
    axes[2].set_xticks(x); axes[2].set_xticklabels([LABELS[t] for t in tags], rotation=15)
    axes[2].set_ylabel("Expected Calibration Error")
    axes[2].set_title("(c) Calibration error (ECE)")
    for bar, m, s in zip(bars, eces_m, eces_s):
        axes[2].text(bar.get_x()+bar.get_width()/2, m+s+0.003,
                     f"{m:.3f}", ha="center", fontsize=9)
    axes[2].set_ylim(0, max(np.array(eces_m)+np.array(eces_s))*1.20)

    plt.tight_layout()
    plt.savefig(FIGS / "fig_real_pathmnist.png")
    plt.close()


# =====================================================================
#       FIGURE — DP-SGD privacy-utility tradeoff
# =====================================================================
def fig_dp():
    eps_list = [0.5, 1.0, 5.0]
    fa_acc, ah_acc, fa_ece, ah_ece = [], [], [], []
    for eps in eps_list:
        fa = json.loads((REAL / f"path_fedavg_dp_eps{eps}.json").read_text())["final"]
        ah = json.loads((REAL / f"path_aha_dp_eps{eps}.json").read_text())["final"]
        fa_acc.append(fa["accuracy"]); fa_ece.append(fa["ece"])
        ah_acc.append(ah["accuracy"]); ah_ece.append(ah["ece"])

    # No-privacy reference (eps=inf): seed 42 from matrix D
    fa_inf = json.loads((REAL / "path_fedavg_s42.json").read_text())["final"]
    ah_inf = json.loads((REAL / "path_aha_fed_s42.json").read_text())["final"]

    eps_axis = eps_list + [float("inf")]
    fa_acc_full = fa_acc + [fa_inf["accuracy"]]
    ah_acc_full = ah_acc + [ah_inf["accuracy"]]
    fa_ece_full = fa_ece + [fa_inf["ece"]]
    ah_ece_full = ah_ece + [ah_inf["ece"]]
    xticks_lab = [str(e) for e in eps_list] + [r"$\infty$"]

    fig, axes = plt.subplots(2, 1, figsize=(3.4, 3.9))
    xs = np.arange(len(eps_axis))
    axes[0].plot(xs, fa_acc_full, marker="o", linewidth=2.0, markersize=8,
                 color=PALETTE["fedavg"], label="FedAvg + DP-SGD")
    axes[0].plot(xs, ah_acc_full, marker="s", linewidth=2.0, markersize=8,
                 color=PALETTE["aha_fed"], label="AHA-Fed + DP-SGD")
    axes[0].axhline(1/9, color="gray", linestyle=":", linewidth=1.0,
                    label="random (1/9)")
    axes[0].set_xticks(xs); axes[0].set_xticklabels(xticks_lab)
    axes[0].set_xlabel(r"Target privacy budget $\varepsilon$")
    axes[0].set_ylabel("Test accuracy")
    axes[0].set_title("(a) Accuracy under DP-SGD")
    axes[0].legend(loc="upper left")

    axes[1].plot(xs, fa_ece_full, marker="o", linewidth=2.0, markersize=8,
                 color=PALETTE["fedavg"], label="FedAvg + DP-SGD")
    axes[1].plot(xs, ah_ece_full, marker="s", linewidth=2.0, markersize=8,
                 color=PALETTE["aha_fed"], label="AHA-Fed + DP-SGD")
    axes[1].set_xticks(xs); axes[1].set_xticklabels(xticks_lab)
    axes[1].set_xlabel(r"Target privacy budget $\varepsilon$")
    axes[1].set_ylabel("Expected Calibration Error")
    axes[1].set_title("(b) Calibration under DP-SGD")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(FIGS / "fig_dp_tradeoff.png")
    plt.close()


# =====================================================================
#       FIGURE — HP sensitivity heatmap (β, γ)
# =====================================================================
def fig_hp_heatmap():
    grid = [0, 1, 2, 4, 8]
    ece = np.zeros((len(grid), len(grid)))
    acc = np.zeros((len(grid), len(grid)))
    for i, b in enumerate(grid):
        for j, g in enumerate(grid):
            f = REAL / f"hp_b{b}_g{g}.json"
            if f.exists():
                d = json.loads(f.read_text())["final"]
                ece[i, j] = d["ece"]
                acc[i, j] = d["accuracy"]
            else:
                ece[i, j] = np.nan
                acc[i, j] = np.nan

    fig, axes = plt.subplots(2, 1, figsize=(3.4, 4.0))
    im0 = axes[0].imshow(ece, cmap="RdYlGn_r", aspect="auto")
    axes[0].set_xticks(range(len(grid))); axes[0].set_xticklabels(grid)
    axes[0].set_yticks(range(len(grid))); axes[0].set_yticklabels(grid)
    axes[0].set_xlabel(r"$\gamma$  (quality reward)")
    axes[0].set_ylabel(r"$\beta$  (heterogeneity penalty)")
    axes[0].set_title("(a) Final ECE  (lower is better)")
    for i in range(len(grid)):
        for j in range(len(grid)):
            v = ece[i, j]
            if not np.isnan(v):
                color = "white" if v > np.nanmean(ece) else "black"
                axes[0].text(j, i, f"{v:.3f}", ha="center", va="center",
                             fontsize=9, color=color)
    plt.colorbar(im0, ax=axes[0])

    im1 = axes[1].imshow(acc, cmap="RdYlGn", aspect="auto")
    axes[1].set_xticks(range(len(grid))); axes[1].set_xticklabels(grid)
    axes[1].set_yticks(range(len(grid))); axes[1].set_yticklabels(grid)
    axes[1].set_xlabel(r"$\gamma$  (quality reward)")
    axes[1].set_ylabel(r"$\beta$  (heterogeneity penalty)")
    axes[1].set_title("(b) Final accuracy  (higher is better)")
    for i in range(len(grid)):
        for j in range(len(grid)):
            v = acc[i, j]
            if not np.isnan(v):
                color = "black" if v > np.nanmean(acc) else "white"
                axes[1].text(j, i, f"{v:.2f}", ha="center", va="center",
                             fontsize=9, color=color)
    plt.colorbar(im1, ax=axes[1])

    plt.tight_layout()
    plt.savefig(FIGS / "fig_hp_heatmap.png")
    plt.close()


# =====================================================================
#       FIGURE — Multi-seed convergence on PathMNIST (real data)
# =====================================================================
def fig_real_convergence():
    fig, axes = plt.subplots(2, 1, figsize=(3.4, 3.9))
    for tag in ["fedavg", "fedprox", "fedbn", "feddisco", "aha_fed"]:
        all_loss, all_ece, rounds = [], [], None
        for s in SEEDS:
            d = json.loads((REAL / f"path_{tag}_s{s}.json").read_text())
            h = d["history"]
            if rounds is None:
                rounds = [r["round"] for r in h]
            all_loss.append([r["loss"] for r in h])
            all_ece.append([r["ece"] for r in h])
        loss = np.array(all_loss)
        ece = np.array(all_ece)
        col = PALETTE[tag]
        axes[0].plot(rounds, loss.mean(0), marker="o", markersize=4,
                     linewidth=1.7, color=col, label=LABELS[tag])
        axes[0].fill_between(rounds, loss.mean(0)-loss.std(0),
                             loss.mean(0)+loss.std(0), color=col, alpha=0.15)
        axes[1].plot(rounds, ece.mean(0), marker="o", markersize=4,
                     linewidth=1.7, color=col, label=LABELS[tag])
        axes[1].fill_between(rounds, ece.mean(0)-ece.std(0),
                             ece.mean(0)+ece.std(0), color=col, alpha=0.15)

    axes[0].set_xlabel("Communication round")
    axes[0].set_ylabel("Test loss (cross-entropy)")
    axes[0].set_title("(a) Test loss, mean ± s.d. over 10 seeds")
    axes[0].legend(loc="upper right")

    axes[1].set_xlabel("Communication round")
    axes[1].set_ylabel("Expected Calibration Error")
    axes[1].set_title("(b) ECE, mean ± s.d. over 10 seeds")
    axes[1].legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(FIGS / "fig_real_convergence.png")
    plt.close()


def main():
    fig_real_data();        print("  [done] fig_real_pathmnist")
    fig_real_convergence(); print("  [done] fig_real_convergence")
    fig_dp();               print("  [done] fig_dp_tradeoff")
    fig_hp_heatmap();       print("  [done] fig_hp_heatmap")


if __name__ == "__main__":
    main()
