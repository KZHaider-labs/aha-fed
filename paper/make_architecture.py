"""Render the AHA-Fed system architecture diagram (publication-quality).

Outputs paper/figures/fig_architecture_pro.png at 400 DPI.

Design:
- 3 horizontal layers (server / privacy boundary / clients)
- Per-hospital internal breakdown (data, model, DP-SGD, q_k)
- Server-side breakdown (broadcast / aggregator / registry / evaluator)
- Numbered round flow 1..6 inline as a single bottom strip
- Privacy boundary line with on-premise / off-premise labels
- Colour coded: blue server, yellow clean clients, red noisy client
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import (
    FancyArrowPatch,
    FancyBboxPatch,
    Circle,
)

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)


# ---------- colour palette ----------
SERVER_FILL  = "#cfe2f3"
SERVER_EDGE  = "#1f3a5f"
SERVER_INNER = "#e8f0fe"
CLEAN_FILL   = "#fff2cc"
CLEAN_EDGE   = "#7a4f00"
NOISY_FILL   = "#fadbd8"
NOISY_EDGE   = "#7a1f1f"
INNER_FILL   = "#ffffff"
UPLINK       = "#444444"
DOWNLINK     = "#aa3333"
PRIVACY_FILL = "#f4f8fb"
STEP_SERVER  = "#1f3a5f"
STEP_CLIENT  = "#7a4f00"
STEP_LINK    = "#444444"


def rbox(ax, x, y, w, h, fc, ec, lw=1.4, pad=0.05):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad={pad}",
                         linewidth=lw, edgecolor=ec, facecolor=fc)
    ax.add_patch(box)
    return box


def step_circle(ax, x, y, n, color, r=0.20):
    c = Circle((x, y), r, facecolor=color, edgecolor="white",
               linewidth=1.4, zorder=10)
    ax.add_patch(c)
    ax.text(x, y, str(n), ha="center", va="center",
            fontsize=10, fontweight="bold", color="white", zorder=11)


def render():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    })

    fig, ax = plt.subplots(figsize=(12.5, 10.2))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # ============================================================
    # SERVER LAYER (top)
    # ============================================================
    server_y, server_h = 8.0, 2.7
    server_x, server_w = 1.0, 14.0

    rbox(ax, server_x, server_y, server_w, server_h,
         SERVER_FILL, SERVER_EDGE, lw=2.0, pad=0.10)
    ax.text(server_x + 0.30, server_y + server_h - 0.32,
            "Federated Server  (off-premise / coordinator)",
            ha="left", va="center", fontsize=12.5,
            fontweight="bold", color=SERVER_EDGE)

    # --- Server inner sub-blocks (4 columns) ---
    inner_y = server_y + 0.40
    inner_h = 1.55
    gap = 0.30
    block_widths = [2.6, 5.6, 2.0, 2.4]
    block_x = server_x + 0.40
    blocks = []
    for w in block_widths:
        blocks.append((block_x, w))
        block_x += w + gap

    # 1. Broadcast block
    bx, bw = blocks[0]
    rbox(ax, bx, inner_y, bw, inner_h, INNER_FILL, SERVER_EDGE, lw=1.2)
    ax.text(bx + bw / 2, inner_y + inner_h - 0.25, "Broadcast",
            ha="center", fontsize=11, fontweight="bold", color=SERVER_EDGE)
    ax.text(bx + bw / 2, inner_y + inner_h - 0.60,
            r"send  $\theta^{\,t}$", ha="center", fontsize=10)
    ax.text(bx + bw / 2, inner_y + inner_h - 0.95,
            "to all $K$ hospitals",
            ha="center", fontsize=9.5)
    ax.text(bx + bw / 2, inner_y + 0.20,
            "encrypted channel",
            ha="center", fontsize=9, color="#444", style="italic")

    # 2. AHA-Fed aggregator block
    ax_x, ax_w = blocks[1]
    rbox(ax, ax_x, inner_y, ax_w, inner_h, SERVER_INNER, SERVER_EDGE, lw=1.6)
    ax.text(ax_x + ax_w / 2, inner_y + inner_h - 0.25,
            "AHA-Fed Aggregator",
            ha="center", fontsize=11.5, fontweight="bold",
            color=SERVER_EDGE)
    ax.text(ax_x + ax_w / 2, inner_y + inner_h - 0.62,
            r"$s_k=\alpha\log n_k - \beta D_k + \gamma\log q_k$",
            ha="center", fontsize=11)
    ax.text(ax_x + ax_w / 2, inner_y + inner_h - 0.97,
            r"$w_k=\mathrm{softmax}(s_1,\ldots,s_K)$",
            ha="center", fontsize=11)
    ax.text(ax_x + ax_w / 2, inner_y + 0.23,
            r"$\theta^{\,t+1}=\sum_{k=1}^{K} w_k\,\theta_k^{\,t+1}$",
            ha="center", fontsize=11.5, color=SERVER_EDGE,
            fontweight="bold")

    # 3. Registry block
    qx, qw = blocks[2]
    rbox(ax, qx, inner_y, qw, inner_h, INNER_FILL, SERVER_EDGE, lw=1.2)
    ax.text(qx + qw / 2, inner_y + inner_h - 0.25, "Registry",
            ha="center", fontsize=11, fontweight="bold", color=SERVER_EDGE)
    ax.text(qx + qw / 2, inner_y + inner_h - 0.62,
            r"$\{\,n_k,\,\boldsymbol{\pi}_k\,\}$",
            ha="center", fontsize=10.5)
    ax.text(qx + qw / 2, inner_y + inner_h - 0.97,
            r"$\bar{\boldsymbol{\pi}},\;D_k$",
            ha="center", fontsize=10.5)
    ax.text(qx + qw / 2, inner_y + 0.20,
            "(once at start)",
            ha="center", fontsize=9, color="#444", style="italic")

    # 4. Evaluation block
    ex_, ew_ = blocks[3]
    rbox(ax, ex_, inner_y, ew_, inner_h, INNER_FILL, SERVER_EDGE, lw=1.2)
    ax.text(ex_ + ew_ / 2, inner_y + inner_h - 0.25, "Evaluation",
            ha="center", fontsize=11, fontweight="bold", color=SERVER_EDGE)
    ax.text(ex_ + ew_ / 2, inner_y + inner_h - 0.62,
            "AUROC, AUPRC,",
            ha="center", fontsize=9.5)
    ax.text(ex_ + ew_ / 2, inner_y + inner_h - 0.92,
            "ECE, accuracy",
            ha="center", fontsize=9.5)
    ax.text(ex_ + ew_ / 2, inner_y + 0.20,
            "held-out test set",
            ha="center", fontsize=9, color="#444", style="italic")

    # ============================================================
    # PRIVACY BOUNDARY LAYER
    # ============================================================
    privacy_y, privacy_h = 7.10, 0.55
    rbox(ax, 0.4, privacy_y, 15.2, privacy_h,
         PRIVACY_FILL, "#9a9a9a", lw=1.0, pad=0.0)
    ax.text(0.6, privacy_y + privacy_h / 2 + 0.03,
            "Privacy boundary  ·  encrypted in transit  ·  optional secure aggregation",
            ha="left", va="center", fontsize=10.5, style="italic",
            color="#1f1f1f")
    ax.text(15.4, privacy_y + privacy_h / 2 + 0.03,
            r"only $\,(\Delta\theta_k,\,q_k,\,n_k)\,$ leaves each site",
            ha="right", va="center", fontsize=10.5, style="italic",
            color="#1f1f1f")

    # ============================================================
    # CLIENT LAYER
    # ============================================================
    client_y, client_h = 1.85, 5.0
    centers = [
        (0.4,  CLEAN_FILL, CLEAN_EDGE,
         "Hospital A",  "clean labels\n$n_A\\approx 200$",
         r"$\rho=0.0$ · clean labels"),
        (8.60, NOISY_FILL, NOISY_EDGE,
         "Hospital D",  "low-quality labels\n$n_D\\approx 200$",
         r"$\rho=0.5$ · 50% label noise"),
    ]
    cw = 7.00

    # B and C are identical to A; an ellipsis stands for them rather than
    # drawing the same pipeline two more times.
    ax.text(8.10, client_y + client_h / 2, "\u00b7 \u00b7 \u00b7",
            ha="center", va="center", fontsize=15,
            color="#8a8a8a", linespacing=0.75)
    ax.text(8.10, client_y + client_h + 0.62,
            "B, C as A", ha="center", va="center",
            fontsize=9, style="italic", color="#6b6b6b")

    for x, fill, edge, name, body, badge in centers:
        # Outer hospital box
        rbox(ax, x, client_y, cw, client_h, fill, edge, lw=1.7, pad=0.08)

        # Header
        ax.text(x + cw / 2, client_y + client_h - 0.32, name,
                ha="center", fontsize=12, fontweight="bold", color=edge)
        ax.text(x + cw / 2, client_y + client_h - 0.72, body,
                ha="center", fontsize=9.5)

        # Badge
        bx_, by_ = x + cw / 2 - 1.10, client_y + client_h - 1.32
        bw_, bh_ = 2.20, 0.36
        rbox(ax, bx_, by_, bw_, bh_,
             "white" if fill == CLEAN_FILL else "#fff5f4",
             edge, lw=1.0, pad=0.02)
        ax.text(bx_ + bw_ / 2, by_ + bh_ / 2 + 0.02, badge,
                ha="center", va="center", fontsize=9.5, color=edge)

        # Inner stack: dataset → model → DP-SGD → quality
        items = [
            ("Local dataset $\\mathcal{D}_k$",
             "stays on-premise"),
            ("Local model copy",
             r"$\theta_k\,\leftarrow\,\theta^{\,t}$"),
            ("DP-SGD optimiser",
             r"Opacus $\,C=1.0,\,(\varepsilon,\delta)$"),
            ("$E$ local epochs",
             r"$q_k\,=\,1/(1+\mathcal{L}_k)$"),
        ]
        ih = 0.65
        gap_v = 0.08
        top = client_y + client_h - 1.85
        for j, (head, sub) in enumerate(items):
            iy = top - j * (ih + gap_v)
            rbox(ax, x + 0.20, iy - ih, cw - 0.40, ih,
                 INNER_FILL, edge, lw=0.9, pad=0.03)
            ax.text(x + cw / 2, iy - 0.22, head,
                    ha="center", fontsize=9.5, fontweight="bold",
                    color="#1f1f1f")
            ax.text(x + cw / 2, iy - 0.48, sub,
                    ha="center", fontsize=9, color="#444")

    # ============================================================
    # ARROWS: downlink (red dashed, left of each hospital column)
    # and uplink (black solid, right of each column)
    # ============================================================
    arrow_top = server_y - 0.05      # just below server
    arrow_bot = client_y + client_h - 0.05  # just above hospital
    for x, *_ in centers:
        col_cx = x + cw / 2
        # downlink (red dashed, left of column centre)
        ax.add_patch(FancyArrowPatch(
            (col_cx - 0.55, arrow_top),
            (col_cx - 0.55, arrow_bot),
            arrowstyle="->", mutation_scale=15,
            linewidth=1.6, color=DOWNLINK, linestyle="--",
            zorder=4,
        ))
        # uplink (black solid, right of column centre)
        ax.add_patch(FancyArrowPatch(
            (col_cx + 0.55, arrow_bot),
            (col_cx + 0.55, arrow_top),
            arrowstyle="->", mutation_scale=15,
            linewidth=1.6, color=UPLINK,
            zorder=4,
        ))

    # ============================================================
    # NUMBERED STEP CIRCLES
    # ============================================================
    # Step 1: server-broadcast (bottom-left of server)
    step_circle(ax, 1.40, server_y + 0.20, 1, STEP_SERVER)
    # Step 2: hospital receives θ (above first hospital, on downlink)
    step_circle(ax, 1.65, client_y + client_h + 0.16, 2, STEP_CLIENT)
    # Step 3: DP-SGD training inside Hospital A (centre of DP-SGD block)
    step_circle(ax, 0.90, client_y + 1.95, 3, STEP_CLIENT)
    # Step 4: compute q_k inside Hospital A
    step_circle(ax, 0.90, client_y + 1.20, 4, STEP_CLIENT)
    # Step 5: uplink (right of Hospital A, on uplink arrow start)
    step_circle(ax, 2.86, client_y + client_h + 0.16, 5, STEP_LINK)
    # Step 6: Aggregator block centre (server side)
    step_circle(ax, ax_x + 0.35, inner_y + inner_h - 0.30, 6, STEP_SERVER)

    # ============================================================
    # BOTTOM STRIP: round-flow legend (single row)
    # ============================================================
    foot_y, foot_h = 0.70, 0.78
    rbox(ax, 0.4, foot_y, 15.2, foot_h, "#fafafa", "#bbbbbb",
         lw=1.0, pad=0.02)
    ax.text(0.65, foot_y + foot_h - 0.18,
            "Per-round flow",
            ha="left", va="center", fontsize=10.5,
            fontweight="bold", color=SERVER_EDGE)

    descs = [
        (1, STEP_SERVER, "Server broadcasts $\\theta^{\\,t}$"),
        (2, STEP_CLIENT, "Hospital receives $\\theta^{\\,t}$"),
        (3, STEP_CLIENT, "Local DP-SGD"),
        (4, STEP_CLIENT, "Compute $q_k$"),
        (5, STEP_LINK,   "Uplink update"),
        (6, STEP_SERVER, "AHA-Fed softmax"),
    ]
    inner_x = 2.10
    inner_w_strip = 13.40
    step_w = inner_w_strip / len(descs)
    for i, (n, col, txt) in enumerate(descs):
        cx = inner_x + i * step_w + 0.18
        cy = foot_y + foot_h / 2 - 0.03
        c = Circle((cx, cy), 0.16, facecolor=col,
                   edgecolor="white", linewidth=1.0)
        ax.add_patch(c)
        ax.text(cx, cy, str(n), ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")
        ax.text(cx + 0.30, cy, txt,
                ha="left", va="center", fontsize=9.5, color="#1f1f1f")
        if i < len(descs) - 1:
            ax.annotate("",
                        xy=(inner_x + (i + 1) * step_w - 0.05, cy),
                        xytext=(inner_x + i * step_w + step_w - 0.45, cy),
                        arrowprops=dict(arrowstyle="->",
                                        color="#999", lw=1.0))

    # ============================================================
    # BOTTOM-MOST LEGEND: arrow styles + step marker colours
    # ============================================================
    leg_y, leg_h = 0.05, 0.55
    rbox(ax, 0.4, leg_y, 15.2, leg_h, "white", "#bbbbbb",
         lw=1.0, pad=0.02)

    legend_x = 0.7
    legend_y_c = leg_y + leg_h / 2 + 0.02

    # downlink
    ax.plot([legend_x, legend_x + 0.55],
            [legend_y_c, legend_y_c],
            color=DOWNLINK, linestyle="--", linewidth=2.0)
    ax.text(legend_x + 0.65, legend_y_c,
            r"Downlink: server $\to$ client ($\theta^{\,t}$)",
            ha="left", va="center", fontsize=10, color="#1f1f1f")

    # uplink
    legend_x = 5.0
    ax.plot([legend_x, legend_x + 0.55],
            [legend_y_c, legend_y_c],
            color=UPLINK, linewidth=2.0)
    ax.text(legend_x + 0.65, legend_y_c,
            r"Uplink: client $\to$ server ($\Delta\theta_k,\,q_k,\,n_k$)",
            ha="left", va="center", fontsize=10, color="#1f1f1f")

    # server step
    legend_x = 10.0
    c = Circle((legend_x + 0.18, legend_y_c), 0.13,
               facecolor=STEP_SERVER, edgecolor="white", linewidth=1.0)
    ax.add_patch(c)
    ax.text(legend_x + 0.45, legend_y_c,
            "Server-side step", ha="left", va="center",
            fontsize=10, color="#1f1f1f")

    # client step
    legend_x = 12.6
    c = Circle((legend_x + 0.18, legend_y_c), 0.13,
               facecolor=STEP_CLIENT, edgecolor="white", linewidth=1.0)
    ax.add_patch(c)
    ax.text(legend_x + 0.45, legend_y_c,
            "Client-side step", ha="left", va="center",
            fontsize=10, color="#1f1f1f")

    plt.savefig(FIGS / "fig_architecture_pro.png")
    plt.close()
    print(f"Wrote: {FIGS / 'fig_architecture_pro.png'}")


if __name__ == "__main__":
    render()
