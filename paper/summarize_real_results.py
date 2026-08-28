"""Summarise the real-data runs into the numbers the paper needs.

Reads runs/paper/real/ and prints, per experiment, the mean +/- std figures that
go straight into the text and tables — so the paper can be rewritten against
real data without hand-copying numbers out of JSON.

Run:  python paper/summarize_real_results.py
"""
from __future__ import annotations

import glob
import json
import statistics as st
import sys
from pathlib import Path

# Windows consoles default to cp1252, which cannot encode the box/±/— glyphs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "runs" / "paper" / "real"

METHODS = ["aha_fed", "fedavg", "fedprox", "fedbn", "feddisco"]
LABEL = {"aha_fed": "AHA-Fed", "fedavg": "FedAvg", "fedprox": "FedProx",
         "fedbn": "FedBN", "feddisco": "FedDisco"}


def final(path: str) -> dict:
    d = json.loads(Path(path).read_text())
    return d.get("final") or (d.get("history") or [{}])[-1]


def agg(pattern: str, key: str) -> tuple[float, float, int] | None:
    """Mean, population std and n for `key` across every run matching pattern."""
    vals = [final(f).get(key) for f in sorted(glob.glob(str(REAL / pattern)))]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return st.mean(vals), st.pstdev(vals), len(vals)


def agg2(patterns: list[str], key: str) -> tuple[float, float, int] | None:
    """Same as agg but over several patterns, de-duplicating matched files."""
    files = sorted({f for p in patterns for f in glob.glob(str(REAL / p))})
    vals = [final(f).get(key) for f in files]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return st.mean(vals), st.pstdev(vals), len(vals)


def fmt(r: tuple[float, float, int] | None, nd: int = 4) -> str:
    if r is None:
        return "—"
    m, s, n = r
    return f"{m:.{nd}f} ± {s:.{nd}f} (n={n})" if n > 1 else f"{m:.{nd}f}"


def paired_test(pat_a: list[str], pat_b: list[str], key: str) -> str:
    """Paired comparison across matched seeds, for reviewers who ask.

    Three seeds is too few for a meaningful p-value, so we report the paired
    mean difference with a Wilcoxon signed-rank p only as a descriptive
    statistic and say so in the caption rather than claiming significance.
    """
    fa = sorted({f for p in pat_a for f in glob.glob(str(REAL / p))})
    fb = sorted({f for p in pat_b for f in glob.glob(str(REAL / p))})
    va = [final(f).get(key) for f in fa]
    vb = [final(f).get(key) for f in fb]
    va = [x for x in va if x is not None]
    vb = [x for x in vb if x is not None]
    if len(va) != len(vb) or len(va) < 2:
        return "—"
    diff = st.mean(vb) - st.mean(va)
    try:
        from scipy.stats import wilcoxon
        p = wilcoxon(va, vb).pvalue
        return f"Δ={diff:+.4f}, p={p:.3f} (n={len(va)})"
    except Exception:
        return f"Δ={diff:+.4f} (n={len(va)})"


def section(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


# ---------------------------------------------------------------- PathMNIST
section("PathMNIST — 4 centers, prevalence shift, 50% noise at one client")
print(f"{'method':<10} {'ECE':<24} {'accuracy':<24} AUROC")
path_ece = {}
for m in METHODS:
    e = agg(f"path_{m}_s*.json", "ece")
    path_ece[m] = e
    print(f"{LABEL[m]:<10} {fmt(e):<24} {fmt(agg(f'path_{m}_s*.json', 'accuracy')):<24}"
          f" {fmt(agg(f'path_{m}_s*.json', 'auroc'))}")

if path_ece.get("aha_fed") and path_ece.get("fedavg"):
    a = path_ece["aha_fed"][0]
    print("\nECE reduction vs AHA-Fed:")
    for m in METHODS[1:]:
        if path_ece.get(m):
            print(f"  vs {LABEL[m]:<9} {(path_ece[m][0] - a) / path_ece[m][0] * 100:+.1f}%")

# ---------------------------------------------------- PneumoniaMNIST (CXR)
section("PneumoniaMNIST (chest radiography) — 4 centers, 3 seeds")
found = False
print(f"{'method':<10} {'ECE':<24} {'accuracy':<24} AUROC")
for m in METHODS:
    e = agg(f"pneu_{m}_s*.json", "ece")
    if e:
        found = True
    print(f"{LABEL[m]:<10} {fmt(e):<24} {fmt(agg(f'pneu_{m}_s*.json', 'accuracy')):<24}"
          f" {fmt(agg(f'pneu_{m}_s*.json', 'auroc'))}")
if not found:
    print("  (multi-seed runs not present yet — run --pneu)")

# ------------------------------------------------------------- noise sweep
section("Label-noise sweep on PathMNIST (3 seeds per point)")
print(f"{'noise':<8} {'AHA-Fed ECE':<24} {'FedAvg ECE':<24} ratio")
rows = []
for rate in ["0.0", "0.3", "0.5", "0.7"]:
    a = agg(f"real_noise_aha_n{rate}_s*.json", "ece")
    v = agg(f"real_noise_fedavg_n{rate}_s*.json", "ece")
    ratio = f"{v[0] / a[0]:.2f}x" if a and v and a[0] else "—"
    rows.append((rate, a, v))
    print(f"{rate:<8} {fmt(a):<24} {fmt(v):<24} {ratio}")

if all(r[1] and r[2] for r in rows):
    a0, a7 = rows[0][1][0], rows[-1][1][0]
    v0, v7 = rows[0][2][0], rows[-1][2][0]
    print(f"\nAcross 0 -> 70% noise:  AHA-Fed {a7 / a0:.2f}x   FedAvg {v7 / v0:.2f}x")
    print("(the paper's headline robustness claim, now on real data)")

section("Label-noise sweep on PneumoniaMNIST (chest radiography, 1 seed)")
print(f"{'noise':<8} {'AHA-Fed ECE':<16} {'FedAvg ECE':<16} ratio")
for rate in ["0.0", "0.3", "0.5", "0.7"]:
    a = agg(f"pneu_noise_aha_n{rate}.json", "ece")
    v = agg(f"pneu_noise_fedavg_n{rate}.json", "ece")
    ratio = f"{v[0] / a[0]:.2f}x" if a and v and a[0] else "—"
    print(f"{rate:<8} {fmt(a):<16} {fmt(v):<16} {ratio}")

# ---------------------------------------------------------- heterogeneity
section("Heterogeneity sweep on PathMNIST")
print(f"{'level':<8} {'AHA-Fed ECE':<24} {'FedAvg ECE':<24} ratio")
for h in ["0.0", "0.3", "0.5", "0.7", "0.9"]:
    # seed 42 has no suffix; later seeds are _s<seed>
    a = agg2([f"real_het_aha_h{h}.json", f"real_het_aha_h{h}_s*.json"], "ece")
    v = agg2([f"real_het_fedavg_h{h}.json", f"real_het_fedavg_h{h}_s*.json"], "ece")
    ratio = f"{v[0] / a[0]:.2f}x" if a and v and a[0] else "—"
    print(f"{h:<8} {fmt(a):<24} {fmt(v):<24} {ratio}")

# --------------------------------------------------------- client scaling
section("Client-count scaling on PathMNIST")
print(f"{'K':<8} {'AHA-Fed ECE':<24} {'FedAvg ECE':<24} ratio")
for k in ["4", "8", "12"]:
    # Two patterns, not one glob: "k4*" would also match k12's files.
    a = agg2([f"real_scale_aha_k{k}.json", f"real_scale_aha_k{k}_s*.json"], "ece")
    v = agg2([f"real_scale_fedavg_k{k}.json", f"real_scale_fedavg_k{k}_s*.json"], "ece")
    ratio = f"{v[0] / a[0]:.2f}x" if a and v and a[0] else "—"
    print(f"{k:<8} {fmt(a):<24} {fmt(v):<24} {ratio}")

# ------------------------------------- PneumoniaMNIST hyperparameter tuning
section("PneumoniaMNIST (beta, gamma) selection — chosen on the val split")
GRID = [0, 1, 2, 4, 8]
val = {}
for b in GRID:
    for g in GRID:
        r = agg(f"pneuval_hp_b{b}_g{g}_s*.json", "ece")
        if r:
            val[(b, g)] = r

if val:
    print("Validation ECE (mean over seeds); selection is made here, not on test")
    print("        " + "".join(f"g={g:<8}" for g in GRID))
    for b in GRID:
        row = f"b={b:<5} "
        for g in GRID:
            r = val.get((b, g))
            row += f"{r[0]:.4f}   " if r else "  --      "
        print(row)
    pick = min(val, key=lambda k: val[k][0])
    print(f"\nselected on val: beta={pick[0]}, gamma={pick[1]} "
          f"(val ECE {val[pick][0]:.4f})")

    held = agg(f"pneu_ahatuned_b{pick[0]}_g{pick[1]}_s*.json", "ece")
    if held:
        print("held-out test ECE for that config: " + fmt(held))
    else:
        print("held-out test runs for that config not present yet")
else:
    print("  (validation grid not present yet — run the pneuval_hp_* sweep)")

section("PneumoniaMNIST leaderboard on the held-out test split")
board = []
for b, g in [(0, 2), (4, 0), (8, 1), (8, 0)]:
    e = agg(f"pneu_ahatuned_b{b}_g{g}_s*.json", "ece")
    if e:
        board.append((f"AHA-Fed (β={b}, γ={g})", e,
                      agg(f"pneu_ahatuned_b{b}_g{g}_s*.json", "accuracy"),
                      agg(f"pneu_ahatuned_b{b}_g{g}_s*.json", "auroc")))
for m in METHODS:
    e = agg(f"pneu_{m}_s*.json", "ece")
    if e:
        name = f"{LABEL[m]} (β=4, γ=4)" if m == "aha_fed" else LABEL[m]
        board.append((name, e, agg(f"pneu_{m}_s*.json", "accuracy"),
                      agg(f"pneu_{m}_s*.json", "auroc")))
if board:
    print(f"{'config':<24}{'ECE':<24}{'accuracy':<24}AUROC")
    for name, e, a, u in sorted(board, key=lambda r: r[1][0]):
        print(f"{name:<24}{fmt(e):<24}{fmt(a):<24}{fmt(u)}")

# ------------------------------------------------------- significance notes
section("Paired seed-wise comparisons (descriptive; n=3 is too small for power)")
print("AHA-Fed vs each baseline, PathMNIST final ECE")
for m in METHODS[1:]:
    print(f"  vs {LABEL[m]:<9} "
          + paired_test(["path_aha_fed_s*.json"], [f"path_{m}_s*.json"], "ece"))
print()
print("AHA-Fed vs FedAvg, heterogeneity sweep (pooled over levels and seeds)")
print("  " + paired_test(["real_het_aha_h*.json"],
                         ["real_het_fedavg_h*.json"], "ece"))
print()
print("AHA-Fed vs FedAvg, label-noise sweep (pooled)")
print("  " + paired_test(["real_noise_aha_n*_s*.json"],
                         ["real_noise_fedavg_n*_s*.json"], "ece"))

# ------------------------------------------------------------------- DP
section("DP-SGD on PathMNIST (chance accuracy = 1/9 = 0.111)")
print(f"{'eps':<8} {'AHA-Fed acc':<14} {'FedAvg acc':<14} {'AHA ECE':<12} FedAvg ECE")
for eps in ["0.5", "1.0", "5.0"]:
    a = agg(f"path_aha_dp_eps{eps}.json", "accuracy")
    v = agg(f"path_fedavg_dp_eps{eps}.json", "accuracy")
    ae = agg(f"path_aha_dp_eps{eps}.json", "ece")
    ve = agg(f"path_fedavg_dp_eps{eps}.json", "ece")
    at_chance = [name for name, r in (("AHA-Fed", a), ("FedAvg", v))
                 if r and r[0] <= 1 / 9]
    flag = f"  <- {' and '.join(at_chance)} at/below chance" if at_chance else ""
    print(f"{eps:<8} {fmt(a, 3):<14} {fmt(v, 3):<14} {fmt(ae, 3):<12} {fmt(ve, 3)}{flag}")

# ------------------------------------------------------------ inventory
section("Run inventory")
groups = {
    "PathMNIST baselines": "path_*_s*.json",
    "PneumoniaMNIST multi-seed": "pneu_*_s*.json",
    "noise sweep (PathMNIST)": "real_noise_*.json",
    "noise sweep (PneumoniaMNIST)": "pneu_noise_*.json",
    "heterogeneity": "real_het_*.json",
    "client scaling": "real_scale_*.json",
    "DP-SGD": "path_*_dp_*.json",
    "hyperparameter grid": "hp_b*_g*.json",
}
for name, pat in groups.items():
    print(f"  {name:<32} {len(glob.glob(str(REAL / pat))):>3} runs")
print(f"\n  {'TOTAL in runs/paper/real':<32} {len(glob.glob(str(REAL / '*.json'))):>3} runs")
