"""Generate all publication-quality figures and equation images.

Outputs PNGs at 400 DPI to paper/figures/. All visualizations are derived
from real experiment JSONs in runs/paper/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data.partitioning import make_synthetic_clients

RUNS = ROOT / "runs" / "paper"
FIGS = ROOT / "paper" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
EQ = FIGS / "equations"
EQ.mkdir(parents=True, exist_ok=True)

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
    "aha_fed":  "#d62728",
}
LABELS = {
    "fedavg":  "FedAvg",
    "fedprox": "FedProx",
    "fedbn":   "FedBN",
    "aha_fed": "AHA-Fed (ours)",
}
SEEDS = [42, 123, 456]


# ---------- helpers ----------
def load_history(name: str) -> tuple[list[int], dict[str, list[float]]]:
    payload = json.loads((RUNS / f"{name}.json").read_text())
    rounds = [h["round"] for h in payload["history"]]
    metrics = {
        k: [h[k] for h in payload["history"]]
        for k in ("loss", "accuracy", "auroc", "ece")
    }
    return rounds, metrics


def load_seeds(tag: str) -> tuple[list[int], np.ndarray, np.ndarray]:
    """Return (rounds, loss_matrix [seed x rounds], ece_matrix)."""
    losses, eces = [], []
    rounds = None
    for s in SEEDS:
        p = json.loads((RUNS / f"seed_{tag}_s{s}.json").read_text())
        h = p["history"]
        if rounds is None:
            rounds = [r["round"] for r in h]
        losses.append([r["loss"] for r in h])
        eces.append([r["ece"]  for r in h])
    return rounds, np.array(losses), np.array(eces)


# =====================================================================
#                         EQUATION IMAGES
# =====================================================================
def render_equation(eq_text: str, filename: str, fontsize: int = 22,
                    width: float = 7.0, height: float = 0.9):
    fig = plt.figure(figsize=(width, height))
    fig.patch.set_alpha(0)
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.5, eq_text, ha="center", va="center",
            fontsize=fontsize, transform=ax.transAxes)
    fig.savefig(EQ / filename, dpi=400, bbox_inches="tight",
                pad_inches=0.05, transparent=False, facecolor="white")
    plt.close(fig)


def make_equations():
    eqs = [
        ("eq1_objective.png",
         r"$F(\theta)\;=\;\sum_{k=1}^{K}\,w_k\;\,\mathbb{E}_{(x,y)\sim\mathcal{D}_k}\,[\,\ell(f_\theta(x),\,y)\,]$",
         24, 7.5, 1.0),
        ("eq2_distance.png",
         r"$D_k\;=\;\frac{1}{2}\,\|\boldsymbol{\pi}_k-\bar{\boldsymbol{\pi}}\|_1\;\;,\quad\bar{\boldsymbol{\pi}}=\frac{1}{K}\sum_{j=1}^{K}\boldsymbol{\pi}_j$",
         22, 7.5, 1.1),
        ("eq3_quality.png",
         r"$q_k\;=\;\frac{1}{1+\mathcal{L}_k}\;\in\;(0,1]\;\;,\quad\mathcal{L}_k=\frac{1}{n_k}\sum_{i=1}^{n_k}\ell(f_{\theta_k}(x_i^{(k)}),\,y_i^{(k)})$",
         20, 8.5, 1.1),
        ("eq4_score.png",
         r"$s_k\;=\;\alpha\,\log n_k\;-\;\beta\,D_k\;+\;\gamma\,\log(q_k+\varepsilon)$",
         24, 7.5, 1.0),
        ("eq5_softmax.png",
         r"$w_k\;=\;\frac{\exp(s_k-s^{\star})}{\sum_{j=1}^{K}\exp(s_j-s^{\star})}\;\;,\quad s^{\star}=\max_{j}\,s_j$",
         22, 7.8, 1.2),
        ("eq6_aggregation.png",
         r"$\theta^{\,t+1}\;=\;\sum_{k=1}^{K}\,w_k\,\theta_k^{\,t+1}$",
         24, 6.0, 1.0),
        ("eq7_dpsgd.png",
         r"$\tilde{g}_k^{\,t}\;=\;\frac{1}{B}\sum_{i\in\mathcal{B}}\;\mathrm{clip}_C(\nabla\ell_i)\;+\;\mathcal{N}(\mathbf{0},\,\sigma^{2}C^{2}\mathbf{I})$",
         22, 7.8, 1.1),
        ("eq8_ece.png",
         r"$\mathrm{ECE}\;=\;\sum_{m=1}^{M}\frac{|B_m|}{N}\,|\,\mathrm{acc}(B_m)\;-\;\mathrm{conf}(B_m)\,|$",
         22, 7.5, 1.1),
        ("eq9_fedavg_special.png",
         r"$\alpha=1,\;\beta=\gamma=0\;\;\Longrightarrow\;\;w_k\,=\,\frac{n_k}{\sum_{j} n_j}\quad\mathrm{(FedAvg)}$",
         22, 7.5, 1.1),
    ]
    for name, tex, fs, w, h in eqs:
        render_equation(tex, name, fontsize=fs, width=w, height=h)
    print(f"  [done] {len(eqs)} equation images")


# =====================================================================
#                         FIGURE 0 — INTRO MOTIVATION
# =====================================================================
def fig_motivation():
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis("off")

    title = ax.text(6.0, 4.55,
                    "Three coupled obstacles in multi-center medical FL",
                    ha="center", va="center", fontsize=13, fontweight="bold",
                    color="#1f3a5f")

    panels = [
        (0.4, 0.4, 3.7, 3.7, "#cfe2f3", "#1f3a5f",
         "Statistical\nHeterogeneity",
         "• Different label priors\n• Scanner / vendor shift\n• Protocol variability\n→ Volume-weighted\n   averaging diverges"),
        (4.3, 0.4, 3.7, 3.7, "#fdebd0", "#7a4f00",
         "Client-side\nLabel Noise",
         "• Junior vs senior raters\n• Rule-based extraction\n• Inter-rater disagreement\n→ Noisy hospital silently\n   poisons the global model"),
        (8.2, 0.4, 3.7, 3.7, "#fadbd8", "#7a1f1f",
         "Privacy\nRequirements",
         "• HIPAA / GDPR / DPA\n• Gradient inversion risk\n• (ε, δ) clinical audit\n→ Need formal DP-SGD\n   composable with FL"),
    ]
    for x, y, w, h, fc, ec, head, body in panels:
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.05",
                                    edgecolor=ec, linewidth=1.5,
                                    facecolor=fc))
        ax.text(x + w / 2, y + h - 0.55, head,
                ha="center", va="center", fontsize=12.5,
                fontweight="bold", color=ec)
        ax.text(x + 0.25, y + h - 1.4, body,
                ha="left", va="top", fontsize=10.5, color="#1f1f1f")

    plt.savefig(FIGS / "fig_motivation.png")
    plt.close()


# =====================================================================
#                         FIGURE 1 — ARCHITECTURE
# =====================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.0)
    ax.axis("off")

    # Server box
    sb = FancyBboxPatch((3.5, 5.0), 5.0, 1.6,
                        boxstyle="round,pad=0.1", linewidth=2,
                        edgecolor="#1f3a5f", facecolor="#cfe2f3")
    ax.add_patch(sb)
    ax.text(6.0, 6.25, "Federated Server",
            ha="center", va="center", fontsize=13, fontweight="bold",
            color="#1f3a5f")
    ax.text(6.0, 5.75, "AHA-Fed Aggregator",
            ha="center", va="center", fontsize=11, color="#1f3a5f")
    ax.text(6.0, 5.30,
            r"$w_k=\mathrm{softmax}(\alpha\log n_k-\beta D_k+\gamma\log q_k)$",
            ha="center", va="center", fontsize=10.5, color="#3a3a3a")

    # Hospital boxes
    centers = [
        (0.3, 1.5, "#fff2cc", "#7a4f00",
         "Hospital A", "Frontal CXR\nn ≈ 200, IID prior"),
        (3.3, 1.5, "#fff2cc", "#7a4f00",
         "Hospital B", "Lateral CXR\nn ≈ 200, mild shift"),
        (6.3, 1.5, "#fff2cc", "#7a4f00",
         "Hospital C", "High prevalence\nn ≈ 200, strong shift"),
        (9.3, 1.5, "#fadbd8", "#7a1f1f",
         "Hospital D", "Noisy labels\nn ≈ 200, 50% noise"),
    ]
    for x, y, fc, ec, head, body in centers:
        ax.add_patch(FancyBboxPatch((x, y), 2.4, 1.5,
                                    boxstyle="round,pad=0.06",
                                    linewidth=1.4,
                                    edgecolor=ec, facecolor=fc))
        ax.text(x + 1.2, y + 1.2, head,
                ha="center", va="center", fontsize=11.5,
                fontweight="bold", color=ec)
        ax.text(x + 1.2, y + 0.6, body,
                ha="center", va="center", fontsize=9.5, color="#1f1f1f")
        ax.text(x + 1.2, y - 0.18,
                "Local SmallCNN / DenseNet-121\n+ DP-SGD (Opacus)",
                ha="center", va="top", fontsize=8.5,
                style="italic", color="#444")

    # Arrows: client -> server (uplinks) and server -> client (downlinks)
    for x, y, *_ in centers:
        cx, cy = x + 1.2, y + 1.5
        ax.add_patch(FancyArrowPatch((cx, cy + 0.55), (cx, 5.0),
                                     arrowstyle="->", mutation_scale=14,
                                     linewidth=1.2, color="#444"))
        ax.add_patch(FancyArrowPatch((cx + 0.18, 5.0), (cx + 0.18, cy + 0.55),
                                     arrowstyle="->", mutation_scale=14,
                                     linewidth=1.2, color="#aa3333",
                                     linestyle="--"))

    ax.text(0.5, 4.55, r"Uplink: $\Delta\theta_k,\,q_k$",
            ha="left", va="center", fontsize=10, color="#444",
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="#444", linewidth=0.8))
    ax.text(11.5, 4.55, r"Downlink: $\theta^{\,t}$",
            ha="right", va="center", fontsize=10, color="#7a1f1f",
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="#aa3333", linewidth=0.8))

    # Bottom data layer
    ax.add_patch(Rectangle((0, 0), 12, 1.0, facecolor="#f4f8fb",
                           edgecolor="#cccccc"))
    ax.text(6.0, 0.5,
            "Raw DICOM, PHI, and patient records remain on-premise — only model state and quality scalars are exchanged.",
            ha="center", va="center", fontsize=10, style="italic",
            color="#1f3a5f")

    plt.savefig(FIGS / "fig1_architecture.png")
    plt.close()


# =====================================================================
#                         FIGURE 2 — DATASET VISUALIZATION
# =====================================================================
def fig_dataset():
    client_ds = make_synthetic_clients(
        num_clients=4, samples_per_client=200, num_classes=4,
        image_size=32, heterogeneity=0.7, base_seed=42,
        label_noise=[0.0, 0.0, 0.0, 0.5],
    )
    fig = plt.figure(figsize=(14.5, 7.4))
    gs = fig.add_gridspec(2, 5, height_ratios=[1.1, 1.0],
                          width_ratios=[1.0, 1.0, 1.0, 1.0, 0.95],
                          hspace=0.55, wspace=0.55)

    # Top: 4 client × 4 sample grid
    titles = ["Hospital A\n(clean)", "Hospital B\n(clean)",
              "Hospital C\n(prevalence shift)",
              "Hospital D\n(50% label noise)"]
    colors_title = ["#1f3a5f", "#1f3a5f", "#7a4f00", "#7a1f1f"]

    for ci, ds in enumerate(client_ds):
        sub = fig.add_subplot(gs[0, ci])
        n_show = 16
        idx = np.linspace(0, len(ds) - 1, n_show, dtype=int)
        imgs = torch.stack([ds[int(i)][0] for i in idx])
        # 4x4 grid
        grid = np.zeros((4 * 32, 4 * 32, 3))
        for k in range(n_show):
            r, c = divmod(k, 4)
            img = imgs[k].permute(1, 2, 0).numpy()
            img = (img - img.min()) / (img.max() - img.min() + 1e-9)
            grid[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = img
        sub.imshow(grid)
        sub.set_xticks([]); sub.set_yticks([])
        sub.set_title(titles[ci], fontsize=10.5, color=colors_title[ci],
                      fontweight="bold", pad=4)

    # Top-right: dataset stats table-as-text
    ax_t = fig.add_subplot(gs[0, 4])
    ax_t.axis("off")
    ax_t.set_title("Synthetic benchmark spec", fontsize=11,
                   fontweight="bold", color="#1f3a5f", pad=8)
    rows = [
        ("Centers (K)",      "4"),
        ("Samples/center",   "200"),
        ("Total samples",    "800"),
        ("Image size",       "32×32×3"),
        ("Classes",          "4"),
        ("Heterogeneity",    "0.7"),
        ("Eval set",         "400"),
        ("Noisy hosp.",      "D (ρ=0.5)"),
    ]
    y0 = 0.92
    for k, v in rows:
        ax_t.text(0.0, y0, k, fontsize=9.5, color="#1f1f1f",
                  transform=ax_t.transAxes)
        ax_t.text(1.0, y0, v, fontsize=9.5, ha="right",
                  fontweight="bold", color="#1f3a5f",
                  transform=ax_t.transAxes)
        y0 -= 0.105

    # Bottom: per-client label-prior histograms
    for ci, ds in enumerate(client_ds):
        sub = fig.add_subplot(gs[1, ci])
        labels = ds.y.numpy()
        counts = np.bincount(labels, minlength=4) / len(labels)
        bars = sub.bar(range(4), counts,
                       color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                       edgecolor="black", linewidth=0.6)
        sub.set_ylim(0, 1.0)
        sub.set_xticks(range(4))
        sub.set_xticklabels([f"c{i}" for i in range(4)])
        sub.set_xlabel("class", fontsize=9.5)
        if ci == 0:
            sub.set_ylabel("empirical prior", fontsize=9.5)
        sub.set_title(f"Hospital {chr(65+ci)} prior", fontsize=10,
                      color=colors_title[ci])
        for bar, v in zip(bars, counts):
            sub.text(bar.get_x() + bar.get_width() / 2, v + 0.02,
                     f"{v:.2f}", ha="center", fontsize=8.5)

    # Bottom-right: noise demonstration
    ax_n = fig.add_subplot(gs[1, 4])
    ax_n.axis("off")
    ax_n.set_title("Label-noise model", fontsize=11, color="#7a1f1f",
                   fontweight="bold", pad=8)
    ax_n.text(0.0, 0.88,
              r"$y_k \sim P_k(y\mid x)$,",
              fontsize=10.5, transform=ax_n.transAxes)
    ax_n.text(0.0, 0.74,
              r"then with probability $\rho_k$:",
              fontsize=10.5, transform=ax_n.transAxes)
    ax_n.text(0.0, 0.56,
              r"  $y_k \leftarrow \mathrm{Uniform}\{1,\dots,C\}$",
              fontsize=10.5, transform=ax_n.transAxes)
    ax_n.text(0.0, 0.38,
              r"Hospital D: $\rho = 0.5$",
              fontsize=10.5, transform=ax_n.transAxes,
              color="#7a1f1f", fontweight="bold")
    ax_n.text(0.0, 0.26,
              r"A / B / C: $\rho = 0.0$",
              fontsize=10.5, transform=ax_n.transAxes, color="#1f1f1f")
    ax_n.text(0.0, 0.06,
              "Inputs come from the true\nlatent label; noise affects\nlabels only (not features).",
              fontsize=9.5, color="#444",
              transform=ax_n.transAxes, style="italic")

    plt.savefig(FIGS / "fig_dataset.png")
    plt.close()


# =====================================================================
#                         FIGURE 3 — AHA-FED CONCEPT
# =====================================================================
def fig_aha_concept():
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis("off")

    inputs = [
        (0.3, 3.5, r"$n_k$" + "\n(volume)",
         "#cfe2f3", "anti-collapse\nterm $\\alpha\\log n_k$"),
        (0.3, 2.0, r"$D_k$" + "\n(prior distance)",
         "#fdebd0", "hetero. penalty\n$-\\beta\\,D_k$"),
        (0.3, 0.5, r"$q_k$" + "\n(quality)",
         "#d5e8d4", "quality reward\n$\\gamma\\log q_k$"),
    ]
    for x, y, t, col, anno in inputs:
        ax.add_patch(FancyBboxPatch((x, y), 1.7, 1.1,
                                    boxstyle="round,pad=0.06",
                                    edgecolor="black", facecolor=col,
                                    linewidth=1.0))
        ax.text(x + 0.85, y + 0.55, t, ha="center", va="center",
                fontsize=11.5)
        ax.text(x + 1.95, y + 0.55, anno, ha="left", va="center",
                fontsize=9, color="#444", style="italic")

    # central score box
    ax.add_patch(FancyBboxPatch((5.6, 2.0), 3.6, 1.5,
                                boxstyle="round,pad=0.08",
                                edgecolor="#1f3a5f", facecolor="#e8f0fe",
                                linewidth=1.6))
    ax.text(7.4, 3.05, "log-score", ha="center", fontsize=10,
            color="#1f3a5f")
    ax.text(7.4, 2.55,
            r"$s_k=\alpha\log n_k-\beta D_k+\gamma\log q_k$",
            ha="center", fontsize=12.5, fontweight="bold",
            color="#1f3a5f")

    # softmax + aggregation
    ax.add_patch(FancyBboxPatch((10.0, 2.0), 1.8, 1.5,
                                boxstyle="round,pad=0.08",
                                edgecolor="#7a1f1f", facecolor="#fadbd8",
                                linewidth=1.6))
    ax.text(10.9, 2.85, r"softmax", ha="center", fontsize=11,
            color="#7a1f1f")
    ax.text(10.9, 2.4, r"$w_k=\dfrac{e^{s_k}}{\sum_j e^{s_j}}$",
            ha="center", fontsize=12, color="#7a1f1f")

    # arrows
    for _, y, _, _, _ in inputs:
        ax.add_patch(FancyArrowPatch((2.0, y + 0.55), (5.6, 2.75),
                                     arrowstyle="->", mutation_scale=12,
                                     color="#444"))
    ax.add_patch(FancyArrowPatch((9.2, 2.75), (10.0, 2.75),
                                 arrowstyle="->", mutation_scale=14,
                                 color="#444", linewidth=1.5))

    # bottom aggregation line
    ax.text(6.0, 0.45,
            r"Aggregation: $\;\theta^{\,t+1}=\sum_{k=1}^{K}w_k\,\theta_k^{\,t+1}$",
            ha="center", fontsize=12, color="#1f3a5f")
    ax.text(6.0, 0.0,
            r"Reduces to FedAvg when $\beta=\gamma=0$ and $\alpha=1$",
            ha="center", fontsize=9.5, style="italic", color="#666")

    plt.savefig(FIGS / "fig_aha_concept.png")
    plt.close()


# =====================================================================
#                  FIGURE 4 — MULTI-SEED CONVERGENCE
# =====================================================================
def fig_convergence_multiseed():
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    for tag in ("fedavg", "fedprox", "fedbn", "aha_fed"):
        rounds, losses, eces = load_seeds(tag)
        mean_l, std_l = losses.mean(0), losses.std(0)
        mean_e, std_e = eces.mean(0), eces.std(0)
        col = PALETTE[tag]
        axes[0].plot(rounds, mean_l, marker="o", markersize=4,
                     linewidth=1.8, color=col, label=LABELS[tag])
        axes[0].fill_between(rounds, mean_l - std_l, mean_l + std_l,
                             color=col, alpha=0.18, linewidth=0)
        axes[1].plot(rounds, mean_e, marker="o", markersize=4,
                     linewidth=1.8, color=col, label=LABELS[tag])
        axes[1].fill_between(rounds, mean_e - std_e, mean_e + std_e,
                             color=col, alpha=0.18, linewidth=0)

    axes[0].set_yscale("log")
    axes[0].set_xlabel("Communication round")
    axes[0].set_ylabel("Test loss (cross-entropy)")
    axes[0].set_title("(a) Convergence — test loss (mean ± 1 std, 3 seeds)")
    axes[0].legend(loc="upper right")

    axes[1].set_xlabel("Communication round")
    axes[1].set_ylabel("Expected Calibration Error (ECE)")
    axes[1].set_title("(b) Calibration — ECE (mean ± 1 std, 3 seeds)")
    axes[1].legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(FIGS / "fig_convergence.png")
    plt.close()


# =====================================================================
#                  FIGURE 5 — FINAL BARS WITH ERROR BARS
# =====================================================================
def fig_final_bars_multiseed():
    names = ["fedavg", "fedprox", "fedbn", "aha_fed"]
    means_l, stds_l, means_e, stds_e = [], [], [], []
    for tag in names:
        _, losses, eces = load_seeds(tag)
        means_l.append(losses[:, -1].mean()); stds_l.append(losses[:, -1].std())
        means_e.append(eces[:, -1].mean());   stds_e.append(eces[:, -1].std())

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    x = np.arange(len(names))
    bars0 = axes[0].bar(x, means_l, yerr=stds_l,
                        color=[PALETTE[n] for n in names],
                        edgecolor="black", linewidth=0.8,
                        capsize=6, error_kw={"linewidth": 1.4})
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([LABELS[n] for n in names], rotation=12)
    axes[0].set_ylabel("Final test loss")
    axes[0].set_title("(a) Final test loss (mean ± std, 3 seeds)")
    for bar, m, s in zip(bars0, means_l, stds_l):
        axes[0].text(bar.get_x() + bar.get_width() / 2, m + s + 0.005,
                     f"{m:.3f}±{s:.3f}", ha="center", fontsize=9)
    axes[0].set_ylim(0, max(np.array(means_l) + np.array(stds_l)) * 1.25)

    bars1 = axes[1].bar(x, means_e, yerr=stds_e,
                        color=[PALETTE[n] for n in names],
                        edgecolor="black", linewidth=0.8,
                        capsize=6, error_kw={"linewidth": 1.4})
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([LABELS[n] for n in names], rotation=12)
    axes[1].set_ylabel("Final ECE")
    axes[1].set_title("(b) Final calibration error (mean ± std, 3 seeds)")
    for bar, m, s in zip(bars1, means_e, stds_e):
        axes[1].text(bar.get_x() + bar.get_width() / 2, m + s + 0.005,
                     f"{m:.3f}±{s:.3f}", ha="center", fontsize=9)
    axes[1].set_ylim(0, max(np.array(means_e) + np.array(stds_e)) * 1.25)

    plt.tight_layout()
    plt.savefig(FIGS / "fig_final_bars.png")
    plt.close()


# =====================================================================
#                  FIGURE 6 — NOISE-RATE ROBUSTNESS
# =====================================================================
def fig_noise_robustness():
    rates = [0.0, 0.3, 0.5, 0.7]
    fa_ece, ah_ece, fa_loss, ah_loss, ah_q = [], [], [], [], []
    for r in rates:
        f = json.loads((RUNS / f"fedavg_n{r}.json").read_text())["final"]
        a = json.loads((RUNS / f"aha_n{r}.json").read_text())["final"]
        fa_ece.append(f["ece"]); ah_ece.append(a["ece"])
        fa_loss.append(f["loss"]); ah_loss.append(a["loss"])
        ah_q.append(a["client_quality"][3])

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    axes[0].plot(rates, fa_ece, marker="o", linewidth=2.0, markersize=7,
                 color=PALETTE["fedavg"], label="FedAvg")
    axes[0].plot(rates, ah_ece, marker="s", linewidth=2.0, markersize=7,
                 color=PALETTE["aha_fed"], label="AHA-Fed (ours)")
    axes[0].fill_between(rates, fa_ece, ah_ece, alpha=0.12,
                         color="#888", label="Robustness gap")
    axes[0].set_xlabel("Label-noise rate at noisy client (ρ)")
    axes[0].set_ylabel("Final ECE")
    axes[0].set_title("(a) ECE vs. noise rate")
    axes[0].legend()

    axes[1].plot(rates, ah_q, marker="D", linewidth=2.0, markersize=7,
                 color="#7a1f7a", label=r"Inferred $q_k$ (noisy client)")
    axes[1].axhline(0.99, color="#2ca02c", linestyle="--", linewidth=1.4,
                    label="Clean clients (avg ≈ 0.99)")
    axes[1].set_xlabel("Label-noise rate at noisy client (ρ)")
    axes[1].set_ylabel(r"Inferred quality $q_k=1/(1+\mathcal{L}_k)$")
    axes[1].set_title("(b) AHA-Fed downweights the noisy client automatically")
    axes[1].legend()
    axes[1].set_ylim(0, 1.05)

    plt.tight_layout()
    plt.savefig(FIGS / "fig_noise_sweep.png")
    plt.close()


# =====================================================================
#              FIGURE 7 — HETEROGENEITY + CLIENT-COUNT
# =====================================================================
def fig_heterogeneity_and_scale():
    levels = [0.0, 0.3, 0.5, 0.7, 0.9]
    fa_h = [json.loads((RUNS / f"het_fedavg_h{h}.json").read_text())["final"]["ece"]
            for h in levels]
    ah_h = [json.loads((RUNS / f"het_aha_h{h}.json").read_text())["final"]["ece"]
            for h in levels]

    Ks = [4, 8, 12]
    fa_k = [json.loads((RUNS / f"scale_fedavg_k{k}.json").read_text())["final"]["ece"]
            for k in Ks]
    ah_k = [json.loads((RUNS / f"scale_aha_k{k}.json").read_text())["final"]["ece"]
            for k in Ks]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    axes[0].plot(levels, fa_h, marker="o", linewidth=2.0, markersize=7,
                 color=PALETTE["fedavg"], label="FedAvg")
    axes[0].plot(levels, ah_h, marker="s", linewidth=2.0, markersize=7,
                 color=PALETTE["aha_fed"], label="AHA-Fed (ours)")
    axes[0].set_xlabel("Heterogeneity level (Dirichlet skew)")
    axes[0].set_ylabel("Final ECE")
    axes[0].set_title("(a) Robustness to label-prior heterogeneity")
    axes[0].legend()

    width = 0.35
    x = np.arange(len(Ks))
    axes[1].bar(x - width / 2, fa_k, width, color=PALETTE["fedavg"],
                edgecolor="black", linewidth=0.8, label="FedAvg")
    axes[1].bar(x + width / 2, ah_k, width, color=PALETTE["aha_fed"],
                edgecolor="black", linewidth=0.8, label="AHA-Fed (ours)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"K = {k}" for k in Ks])
    axes[1].set_ylabel("Final ECE")
    axes[1].set_title("(b) Scaling: number of participating clients")
    axes[1].legend()
    for xi, (a, b) in enumerate(zip(fa_k, ah_k)):
        axes[1].text(xi - width / 2, a + 0.003, f"{a:.3f}",
                     ha="center", fontsize=9)
        axes[1].text(xi + width / 2, b + 0.003, f"{b:.3f}",
                     ha="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGS / "fig_het_scale.png")
    plt.close()


# =====================================================================
#                  FIGURE 8 — PER-CLIENT WEIGHTS
# =====================================================================
def fig_client_weights():
    a = json.loads((RUNS / "aha_n0.5.json").read_text())
    qual = a["final"]["client_quality"]
    n_clients = len(qual)
    log_eps = 1e-6
    log_scores = [np.log(max(q, log_eps)) for q in qual]
    m = max(log_scores)
    exps = [np.exp(s - m) for s in log_scores]
    z = sum(exps)
    weights = [e / z for e in exps]
    fedavg_w = [1 / n_clients] * n_clients

    x = np.arange(n_clients)
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bars1 = ax.bar(x - width / 2, fedavg_w, width,
                   color=PALETTE["fedavg"], edgecolor="black",
                   label="FedAvg (uniform)")
    bars2 = ax.bar(x + width / 2, weights, width,
                   color=PALETTE["aha_fed"], edgecolor="black",
                   label="AHA-Fed (quality-aware)")
    ax.set_xticks(x)
    ax.set_xticklabels(["Hospital A", "Hospital B", "Hospital C",
                        "Hospital D\n(50% noisy)"])
    ax.set_ylabel(r"Aggregation weight $w_k$")
    ax.set_title("Per-client aggregation weights at convergence (noise = 0.5)")
    ax.legend()
    for bar, v in zip(bars1, fedavg_w):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.005,
                f"{v:.3f}", ha="center", fontsize=9.5)
    for bar, v in zip(bars2, weights):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.005,
                f"{v:.3f}", ha="center", fontsize=9.5,
                fontweight="bold")
    ax.set_ylim(0, 0.45)
    plt.tight_layout()
    plt.savefig(FIGS / "fig_weights.png")
    plt.close()


# =====================================================================
#                  FIGURE 9 — TRAINING ALGORITHM
# =====================================================================
def fig_algorithm():
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.0)
    ax.axis("off")
    ax.set_title("Algorithm 1 — AHA-Fed federated training loop",
                 fontsize=12.5, fontweight="bold", color="#1f3a5f",
                 loc="left", pad=4)

    lines = [
        ("Input:",  "K hospitals with $\\mathcal{D}_k$, total rounds T, hyperparameters $\\alpha,\\beta,\\gamma$."),
        ("1.",      "Server initialises $\\theta^{0}$; computes priors $\\pi_k$ and consensus $\\bar\\pi$."),
        ("2.",      "for round $t=0,\\dots,T-1$ do"),
        ("3.",      "    Server broadcasts $\\theta^{t}$ to all clients."),
        ("4.",      "    for each hospital $k\\in\\{1,\\dots,K\\}$ in parallel do"),
        ("5.",      "        Run local DP-SGD for $E$ epochs $\\rightarrow$ $\\theta_k^{t+1}$."),
        ("6.",      "        Compute mean training loss $\\mathcal{L}_k$; quality $q_k=1/(1+\\mathcal{L}_k)$."),
        ("7.",      "        Send $(\\theta_k^{t+1},\\,q_k,\\,n_k)$ to server."),
        ("8.",      "    end for"),
        ("9.",      "    Server: $s_k=\\alpha\\log n_k-\\beta D_k+\\gamma\\log(q_k+\\varepsilon)$."),
        ("10.",     "    Server: $w_k=\\mathrm{softmax}(s_1,\\dots,s_K)$."),
        ("11.",     "    Server: $\\theta^{t+1}=\\sum_{k}w_k\\theta_k^{t+1}$."),
        ("12.",     "end for"),
        ("Output:", "Global model $\\theta^{T}$ with per-client (ε, δ)-DP guarantee."),
    ]
    y = 6.5
    for tag, body in lines:
        ax.text(0.0, y, tag, fontsize=11, fontweight="bold",
                color="#7a1f1f", family="monospace")
        ax.text(1.0, y, body, fontsize=11, color="#1f1f1f")
        y -= 0.42

    ax.add_patch(Rectangle((-0.1, y + 0.15), 12.2, 6.5 - y,
                           fill=False, edgecolor="#1f3a5f",
                           linewidth=1.4))

    plt.savefig(FIGS / "fig_algorithm.png")
    plt.close()


# =====================================================================
def main():
    make_equations()
    fig_motivation();     print("  [done] fig_motivation")
    fig_architecture();   print("  [done] fig1_architecture")
    fig_dataset();        print("  [done] fig_dataset")
    fig_aha_concept();    print("  [done] fig_aha_concept")
    fig_convergence_multiseed(); print("  [done] fig_convergence")
    fig_final_bars_multiseed();  print("  [done] fig_final_bars")
    fig_noise_robustness();      print("  [done] fig_noise_sweep")
    fig_heterogeneity_and_scale(); print("  [done] fig_het_scale")
    fig_client_weights(); print("  [done] fig_weights")
    fig_algorithm();      print("  [done] fig_algorithm")
    print("\nAll figures written to", FIGS)


if __name__ == "__main__":
    main()
