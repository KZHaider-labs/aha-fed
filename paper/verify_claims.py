"""Cross-check every numeric claim in the paper against runs/paper/real/*.json.

All claims are checked against real MedMNIST v2 runs; the synthetic benchmark
is no longer cited by the paper and is not read here.

Run:  python paper/verify_claims.py
Exits non-zero if a positive claim is unsupported, or if a documented
limitation silently stops being true.
"""
from __future__ import annotations

import glob
import json
import re
import statistics as st
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "runs" / "paper" / "real"

FAILED: list[str] = []

# Facts the paper states openly as limitations rather than claiming the reverse.
# They are expected to be False; a flip to True means the text needs updating.
KNOWN_LIMITATIONS = {
    "DP eps=0.5 AHA above chance",
    "DP eps=0.5 FedAvg above chance",
    "DP eps=1.0 AHA above chance",
    "DP eps=1.0 FedAvg above chance",
    "DP eps=5.0 FedAvg above chance",
    "DP eps=5.0 AHA calibration better",
    "AHA-Fed leads on PneumoniaMNIST",
    "AHA-Fed leads FedAvg on the clean NIH federation",
    "corrupted NIH advantage is significant",
    "relative-quality ECE gain is significant",
    "the full rule beats the quality term alone",
}

METHODS = ["aha_fed", "fedavg", "fedprox", "fedbn", "feddisco"]
LABEL = {"aha_fed": "AHA-Fed", "fedavg": "FedAvg", "fedprox": "FedProx",
         "fedbn": "FedBN", "feddisco": "FedDisco"}


def final(path: str) -> dict:
    d = json.loads(Path(path).read_text())

    return d.get("final") or (d.get("history") or [{}])[-1]


def vals(patterns: list[str], key: str) -> list[float]:
    files = sorted({f for p in patterns for f in glob.glob(str(REAL / p))})
    out = [final(f).get(key) for f in files]
    return [v for v in out if v is not None]


def by_seed(pattern: str, key: str) -> dict[str, float]:
    """Map seed -> value, so comparisons pair like with like.

    A trailing _s<digits> names the seed; filenames without one are seed 42.
    Matching only a digit suffix matters because "real_scale_..." itself
    contains "_s".
    """
    out = {}
    for f in sorted(glob.glob(str(REAL / pattern))):
        v = final(f).get(key)
        if v is None:
            continue
        m = re.search(r"_s(\d+)$", Path(f).stem)
        out[m.group(1) if m else "42"] = v
    return out


def paired(a: dict[str, float], b: dict[str, float]) -> tuple[float, float | None, int]:
    """Mean reduction of a vs b and a Wilcoxon p over their shared seeds."""
    common = sorted(set(a) & set(b))
    if not common:
        return float("nan"), None, 0
    x = [a[k] for k in common]
    y = [b[k] for k in common]
    red = (st.mean(y) - st.mean(x)) / st.mean(y) * 100
    return red, wilcoxon_p(x, y), len(common)


def check(label: str, ok: bool, detail: str) -> None:
    if label in KNOWN_LIMITATIONS:
        print(f"[{'NEW  ' if ok else 'LIMIT'}] {label}: {detail}")
        if ok:
            FAILED.append(f"{label} (now TRUE — paper still calls it a limitation)")
        return
    print(f"[{'OK ' if ok else 'FAIL'}] {label}: {detail}")
    if not ok:
        FAILED.append(label)


def wilcoxon_p(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    try:
        from scipy.stats import wilcoxon
        return float(wilcoxon(a, b).pvalue)
    except Exception:
        return None


# ------------------------------------------------- headline: heterogeneity
print("=== Heterogeneity sweep on PathMNIST (the paper's headline claim) ===")
LEVELS = ["0.0", "0.3", "0.5", "0.7", "0.9"]
het_a, het_v, wins = [], [], 0
for h in LEVELS:
    # Pair by seed so the signed-rank test compares matched runs.
    a_by = by_seed(f"real_het_aha_h{h}.json", "ece")
    a_by.update(by_seed(f"real_het_aha_h{h}_s*.json", "ece"))
    v_by = by_seed(f"real_het_fedavg_h{h}.json", "ece")
    v_by.update(by_seed(f"real_het_fedavg_h{h}_s*.json", "ece"))
    common = sorted(set(a_by) & set(v_by))
    if not common:
        continue
    a = [a_by[c] for c in common]
    v = [v_by[c] for c in common]
    het_a += a
    het_v += v
    wins += st.mean(a) < st.mean(v)
    pv = wilcoxon_p(a, v)
    ps = f"p={pv:.4f}" if pv is not None else ""
    print(f"  h={h}  AHA {st.mean(a):.4f}±{st.pstdev(a):.4f}   "
          f"FedAvg {st.mean(v):.4f}±{st.pstdev(v):.4f}   "
          f"{st.mean(v) / st.mean(a):.2f}x   {ps} (n={len(common)})")

check("AHA-Fed wins at every heterogeneity level", wins == len(LEVELS),
      f"{wins}/{len(LEVELS)} levels")
if het_a and het_v:
    p = wilcoxon_p(het_a, het_v)
    ratio = st.mean(het_v) / st.mean(het_a)
    check("heterogeneity separation is significant", p is not None and p < 0.05,
          f"pooled {ratio:.2f}x, Wilcoxon p={p:.4f} (n={len(het_a)})"
          if p is not None else "scipy unavailable")

# ---------------------------------------------------------- client scaling
print("\n=== Client-count scaling on PathMNIST ===")
scale_a, scale_v = [], []
k4_sig = False
for k in ["4", "8", "12", "20", "32"]:
    a = by_seed(f"real_scale_aha_k{k}_s*.json", "ece")
    a.update(by_seed(f"real_scale_aha_k{k}.json", "ece"))
    v = by_seed(f"real_scale_fedavg_k{k}_s*.json", "ece")
    v.update(by_seed(f"real_scale_fedavg_k{k}.json", "ece"))
    common = sorted(set(a) & set(v))
    if not common:
        continue
    x = [a[c] for c in common]
    y = [v[c] for c in common]
    scale_a += x
    scale_v += y
    pv = wilcoxon_p(x, y)
    ps = f"p={pv:.4f}" if pv is not None else ""
    print(f"  K={k:<3} AHA {st.mean(x):.4f}   FedAvg {st.mean(v_ := y):.4f}   "
          f"{st.mean(y) / st.mean(x):.2f}x   {ps} (n={len(common)})")
    if k == "4":
        k4_sig = pv is not None and pv < 0.05

# The advantage is real at K=4 and washes out as K grows; the paper says so,
# so that is what we check rather than a blanket "wins everywhere".
check("AHA-Fed advantage is significant at K=4", k4_sig, "see per-K rows above")
if scale_a:
    pv = wilcoxon_p(scale_a, scale_v)
    check("pooled scaling advantage is significant",
          pv is not None and pv < 0.05,
          f"pooled {st.mean(scale_v) / st.mean(scale_a):.2f}x, p={pv:.4f} "
          f"(n={len(scale_a)})" if pv is not None else "scipy unavailable")

# ------------------------------------------------------ PathMNIST baselines
print("\n=== PathMNIST baselines ===")
ece = {m: vals([f"path_{m}_s*.json"], "ece") for m in METHODS}
auroc = {m: vals([f"path_{m}_s*.json"], "auroc") for m in METHODS}
for m in METHODS:
    if ece[m]:
        print(f"  {LABEL[m]:<9} ECE {st.mean(ece[m]):.4f}±{st.pstdev(ece[m]):.4f} "
              f"(n={len(ece[m])})  AUROC {st.mean(auroc[m]):.4f}")

if ece["aha_fed"]:
    check("AHA-Fed has the lowest mean ECE on PathMNIST",
          min(METHODS, key=lambda m: st.mean(ece[m])) == "aha_fed",
          f"lowest is {min(METHODS, key=lambda m: st.mean(ece[m]))}")
    spread = max(st.mean(auroc[m]) for m in METHODS) - min(st.mean(auroc[m]) for m in METHODS)
    check("AUROC parity across aggregators", spread < 0.02, f"spread {spread:.4f}")
    aha_seeds = by_seed("path_aha_fed_s*.json", "ece")
    for m in METHODS[1:]:
        red, pv, n = paired(aha_seeds, by_seed(f"path_{m}_s*.json", "ece"))
        detail = (f"{red:.1f}% lower, p={pv:.4f} (n={n})" if pv is not None
                  else f"{red:.1f}% lower (n={n})")
        check(f"AHA-Fed beats {LABEL[m]} on PathMNIST ECE", red > 0, detail)
        check(f"PathMNIST ECE gain vs {LABEL[m]} is significant",
              pv is not None and pv < 0.05, detail)

    acc = {m: vals([f"path_{m}_s*.json"], "accuracy") for m in METHODS}
    if all(acc[m] for m in METHODS):
        best = max(METHODS, key=lambda m: st.mean(acc[m]))
        check("AHA-Fed does not trade accuracy for calibration",
              best == "aha_fed",
              f"highest mean accuracy is {LABEL[best]} "
              f"({st.mean(acc[best]):.4f})")

# ------------------------------------------------------------- noise sweep
print("\n=== Label-noise sweep on PathMNIST ===")
na, nv = [], []
for rate in ["0.0", "0.3", "0.5", "0.7"]:
    a = vals([f"real_noise_aha_n{rate}_s*.json"], "ece")
    v = vals([f"real_noise_fedavg_n{rate}_s*.json"], "ece")
    if a and v:
        na += a
        nv += v
        print(f"  noise={rate}  AHA {st.mean(a):.4f}   FedAvg {st.mean(v):.4f}   "
              f"{st.mean(v) / st.mean(a):.2f}x")
if na:
    p = wilcoxon_p(na, nv)
    check("noise sweep separation is significant", p is not None and p < 0.05,
          f"pooled {st.mean(nv) / st.mean(na):.2f}x, p={p:.4f} (n={len(na)})"
          if p is not None else "scipy unavailable")

# ------------------------------------------ PneumoniaMNIST (chest radiography)
print("\n=== PneumoniaMNIST (chest radiography) ===")
pneu = {m: vals([f"pneu_{m}_s*.json"], "ece") for m in METHODS}
for m in METHODS:
    if pneu[m]:
        print(f"  {LABEL[m]:<9} ECE {st.mean(pneu[m]):.4f}±{st.pstdev(pneu[m]):.4f} "
              f"(n={len(pneu[m])})")
sel = vals(["pneu_ahatuned_b0_g2_s*.json"], "ece")
if sel:
    print(f"  AHA-Fed (β=0, γ=2, selected on val) ECE {st.mean(sel):.4f}"
          f"±{st.pstdev(sel):.4f} (n={len(sel)})")
    rivals = [st.mean(pneu[m]) for m in METHODS[1:] if pneu[m]]
    check("AHA-Fed leads on PneumoniaMNIST",
          bool(rivals) and st.mean(sel) < min(rivals),
          f"val-selected config {st.mean(sel):.4f} vs best baseline {min(rivals):.4f}")

# ------------------------------------------------------------------- DP-SGD
print("\n=== DP-SGD on PathMNIST (chance = 1/9 = 0.111) ===")
CHANCE = 1 / 9
for eps in ["0.5", "1.0", "5.0"]:
    a = vals([f"path_aha_dp_eps{eps}.json"], "accuracy")
    v = vals([f"path_fedavg_dp_eps{eps}.json"], "accuracy")
    ae = vals([f"path_aha_dp_eps{eps}.json"], "ece")
    ve = vals([f"path_fedavg_dp_eps{eps}.json"], "ece")
    if not (a and v):
        continue
    print(f"  eps={eps:<4} AHA acc {a[0]:.4f} ece {ae[0]:.4f} | "
          f"FedAvg acc {v[0]:.4f} ece {ve[0]:.4f}")
    check(f"DP eps={eps} AHA above chance", a[0] > CHANCE, f"acc {a[0]:.4f}")
    check(f"DP eps={eps} FedAvg above chance", v[0] > CHANCE, f"acc {v[0]:.4f}")
    check(f"DP eps={eps} AHA calibration better", ae[0] < ve[0],
          f"{ae[0]:.4f} vs {ve[0]:.4f}")

# Section 5.11's corrected sweep: the same per-client budget as the
# non-private runs. The 300-image sweep above collapsed to chance and the
# paper reports both, so both need pinning.
print("\n=== DP-SGD at the standard per-client budget (Sec 5.11) ===")
dp2 = {}
for eps2 in ("1.0", "10.0"):
    aa = by_seed(f"dp2_aha_eps{eps2}_s*.json", "accuracy")
    va = by_seed(f"dp2_fedavg_eps{eps2}_s*.json", "accuracy")
    ae2 = by_seed(f"dp2_aha_eps{eps2}_s*.json", "ece")
    ve2 = by_seed(f"dp2_fedavg_eps{eps2}_s*.json", "ece")
    sh2 = sorted(set(aa) & set(va))
    if not sh2:
        continue
    dp2[eps2] = (st.mean([aa[k] for k in sh2]),
                 st.mean([va[k] for k in sh2]),
                 st.mean([ae2[k] for k in sh2]),
                 st.mean([ve2[k] for k in sh2]))
    print(f"  eps={eps2:<5} AHA acc {dp2[eps2][0]:.3f} ece {dp2[eps2][2]:.4f}"
          f" | FedAvg acc {dp2[eps2][1]:.3f} ece {dp2[eps2][3]:.4f}"
          f" (n={len(sh2)})")
for eps2, dpv in dp2.items():
    check(f"DP eps={eps2} retains usable accuracy at 1000 img/client",
          min(dpv[0], dpv[1]) > 3 * CHANCE,
          f"AHA {dpv[0]:.3f}, FedAvg {dpv[1]:.3f} vs chance {CHANCE:.3f}")
    # ten seeds resolve this; the paper reports it as significant.
    _ae = by_seed(f"dp2_aha_eps{eps2}_s*.json", "ece")
    _ve = by_seed(f"dp2_fedavg_eps{eps2}_s*.json", "ece")
    _sh = sorted(set(_ae) & set(_ve))
    _p = wilcoxon_p([_ae[k] for k in _sh], [_ve[k] for k in _sh])
    check(f"DP eps={eps2} AHA calibration better and significant",
          dpv[2] < dpv[3] and _p is not None and _p < 0.05,
          f"{dpv[2]:.4f} vs {dpv[3]:.4f}, p={_p:.4f}, n={len(_sh)}")
    _aa = by_seed(f"dp2_aha_eps{eps2}_s*.json", "accuracy")
    _va = by_seed(f"dp2_fedavg_eps{eps2}_s*.json", "accuracy")
    _s2 = sorted(set(_aa) & set(_va))
    check(f"DP eps={eps2} FedAvg is the more accurate (the trade-off)",
          st.mean([_va[k] for k in _s2]) > st.mean([_aa[k] for k in _s2]),
          f"FedAvg {st.mean([_va[k] for k in _s2]):.4f} vs "
          f"AHA {st.mean([_aa[k] for k in _s2]):.4f}")
if "1.0" in dp2:
    old_acc = final(str(REAL / "path_aha_dp_eps1.0.json")).get("accuracy")
    if old_acc is not None:
        check("the data budget, not epsilon, caused the original collapse",
              old_acc < CHANCE < dp2["1.0"][0],
              f"300 img: {old_acc:.3f}, 1000 img: {dp2['1.0'][0]:.3f}")

# --------------------------------------------------- hyperparameter grid
print("\n=== (beta, gamma) grid on PathMNIST ===")
GRID = [0, 1, 2, 4, 8]
grid = {}
for b in GRID:
    for g in GRID:
        v = vals([f"hp_b{b}_g{g}.json"], "ece")
        if v:
            grid[(b, g)] = v[0]

if grid:
    interior = [v for (b, g), v in grid.items() if b >= 1 and g >= 1]
    g0 = [v for (b, g), v in grid.items() if g == 0]
    b0 = [v for (b, g), v in grid.items() if b == 0 and g >= 1]
    print(f"  interior (b>=1, g>=1): max {max(interior):.4f} "
          f"over {len(interior)} points")
    print(f"  gamma=0 column:        {min(g0):.4f}-{max(g0):.4f}")
    print(f"  beta=0, gamma>=1:      {min(b0):.4f}-{max(b0):.4f}")
    check("interior grid ECE stays at or below 0.114",
          max(interior) <= 0.114, f"max {max(interior):.4f}")
    if ece.get("fedprox"):
        fedprox = st.mean(ece["fedprox"])
        check("every interior grid point beats FedProx",
              max(interior) < fedprox,
              f"worst interior {max(interior):.4f} vs FedProx {fedprox:.4f}")

# ---------------------------------------- NIH four-way aggregator ordering
NIH_DIR = ROOT / "runs" / "paper" / "nih"


def nih_final(tag: str, seed: str) -> dict | None:
    f = NIH_DIR / f"nih_noisy_{tag}_s{seed}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text()).get("final")


NIH_SEEDS = ["42", "123", "456"]
nih_ece = {}
for tag in ("aha_fed", "fedavg", "fedbn", "feddisco"):
    finals = [nih_final(tag, sd) for sd in NIH_SEEDS]
    if all(v is not None for v in finals):
        nih_ece[tag] = [v["ece"] for v in finals]

if len(nih_ece) == 4:
    print("\n=== NIH four-way comparison (3 shared seeds) ===")
    for tag in ("aha_fed", "fedavg", "fedbn", "feddisco"):
        au = [nih_final(tag, sd)["auroc"] for sd in NIH_SEEDS]
        print(f"  {tag:<9} ECE {st.mean(nih_ece[tag]):.4f}  "
              f"AUROC {st.mean(au):.4f}")
    best = min(nih_ece, key=lambda t: st.mean(nih_ece[t]))
    check("AHA-Fed has the lowest ECE of the four at full resolution",
          best == "aha_fed", f"lowest is {best}")
    fedbn_au = st.mean([nih_final("fedbn", sd)["auroc"] for sd in NIH_SEEDS])
    others = [st.mean([nih_final(t, sd)["auroc"] for sd in NIH_SEEDS])
              for t in ("aha_fed", "fedavg", "feddisco")]
    check("FedBN is the weakest on AUROC at full resolution",
          fedbn_au < min(others),
          f"{fedbn_au:.4f} vs {min(others):.4f}")

# ------------------------------------------------- multiple corrupted sites
print("\n=== Multiple corrupted sites (Section 5.8) ===")
multi_a, multi_v = [], []
n1_sig = False
for nn in (1, 2, 3):
    a = by_seed(f"multi_aha_n{nn}_s*.json", "ece")
    v = by_seed(f"multi_fedavg_n{nn}_s*.json", "ece")
    shared = sorted(set(a) & set(v))
    if not shared:
        continue
    x = [a[k] for k in shared]
    y = [v[k] for k in shared]
    multi_a += x
    multi_v += y
    pv = wilcoxon_p(x, y)
    print(f"  {nn} of 4  AHA {st.mean(x):.4f}  FedAvg {st.mean(y):.4f}  "
          f"{st.mean(y) / st.mean(x):.2f}x  "
          + (f"p={pv:.4f}" if pv is not None else "") + f"  (n={len(shared)})")
    if nn == 1:
        n1_sig = pv is not None and pv < 0.05

check("AHA-Fed advantage holds with a single corrupted site",
      n1_sig, "see per-level rows above")
if multi_a:
    pv = wilcoxon_p(multi_a, multi_v)
    check("pooled multi-site advantage is significant",
          pv is not None and pv < 0.05,
          f"pooled {st.mean(multi_v) / st.mean(multi_a):.2f}x, p={pv:.5f} "
          f"(n={len(multi_a)})" if pv is not None else "scipy unavailable")

# The two sweeps agree at 25% corrupted despite different client counts;
# that agreement is what licenses reading the constraint as a fraction.
scale4_a = by_seed("real_scale_aha_k4_s*.json", "ece")
scale4_a.update(by_seed("real_scale_aha_k4.json", "ece"))
scale4_v = by_seed("real_scale_fedavg_k4_s*.json", "ece")
scale4_v.update(by_seed("real_scale_fedavg_k4.json", "ece"))
multi1_a = by_seed("multi_aha_n1_s*.json", "ece")
multi1_v = by_seed("multi_fedavg_n1_s*.json", "ece")
sh4 = sorted(set(scale4_a) & set(scale4_v))
sh1 = sorted(set(multi1_a) & set(multi1_v))
if sh4 and sh1:
    r_scale = (st.mean([scale4_v[k] for k in sh4])
               / st.mean([scale4_a[k] for k in sh4]))
    r_multi = (st.mean([multi1_v[k] for k in sh1])
               / st.mean([multi1_a[k] for k in sh1]))
    print(f"  25% corrupted: scaling sweep {r_scale:.2f}x, "
          f"multi-site sweep {r_multi:.2f}x")
    check("the two K=4 sweeps agree at the same corrupted fraction",
          abs(r_scale - r_multi) < 0.10,
          f"{r_scale:.2f}x vs {r_multi:.2f}x")

    # Table 8's K=4 row is quoted as 1.46x; it is the scaling sweep's
    # K=4 point, and both of its columns are that same run. The paper
    # briefly carried 1.47x, which matched neither sweep.
    check("Table 8 K=4 reference matches the scaling sweep",
          abs(r_scale - 1.46) < 0.006,
          f"{r_scale:.3f}x (paper says 1.46x)")

# Section 5.9 claims the advantage decays with federation size at a fixed
# 25% corrupted fraction. This is the claim the frac sweep tested and the
# earlier fraction-only reading failed, so it is worth pinning down.
frac_ratios = {}
for _K, _nn in ((8, 2), (12, 3), (16, 4)):
    _a = by_seed(f"frac_aha_k{_K}_n{_nn}_s*.json", "ece")
    _v = by_seed(f"frac_fedavg_k{_K}_n{_nn}_s*.json", "ece")
    _sh = sorted(set(_a) & set(_v))
    if _sh:
        frac_ratios[_K] = (st.mean([_v[k] for k in _sh])
                           / st.mean([_a[k] for k in _sh]))
if len(frac_ratios) == 3:
    print("  25% corrupted at K=8/12/16: "
          + ", ".join(f"{k}:{v:.2f}x" for k, v in sorted(frac_ratios.items())))
    _ordered = [frac_ratios[k] for k in (8, 12, 16)]
    check("the constant-corpus sweep decays with K",
          _ordered[0] > _ordered[1] > _ordered[2],
          ", ".join(f"{r:.2f}x" for r in _ordered))
    check("the constant-corpus advantage is gone by K=16",
          frac_ratios[16] < 1.05,
          f"{frac_ratios[16]:.2f}x")

# Section 5.9's actual conclusion: with per-client data held at 1000 the
# advantage does NOT decay, so the limit is sample size and not client
# count. This is the claim the fixn sweep established, reversing the
# constant-corpus reading above.
fixn_ratios = {}
for _K, _nn in ((8, 2), (12, 3), (16, 4)):
    _a = by_seed(f"fixn_aha_k{_K}_n{_nn}_s*.json", "ece")
    _v = by_seed(f"fixn_fedavg_k{_K}_n{_nn}_s*.json", "ece")
    _sh = sorted(set(_a) & set(_v))
    if _sh:
        fixn_ratios[_K] = (st.mean([_v[k] for k in _sh])
                           / st.mean([_a[k] for k in _sh]))
if len(fixn_ratios) == 3:
    print("  25% corrupted, 1000 img/client: "
          + ", ".join(f"{k}:{v:.2f}x" for k, v in sorted(fixn_ratios.items())))
    check("the advantage survives to K=16 at fixed per-client data",
          min(fixn_ratios.values()) > 1.25,
          ", ".join(f"{fixn_ratios[k]:.2f}x" for k in (8, 12, 16)))
    check("fixed per-client data beats the constant corpus at every K",
          all(fixn_ratios[k] > frac_ratios[k] for k in (8, 12, 16)),
          ", ".join(f"K={k}: {fixn_ratios[k]:.2f}x vs {frac_ratios[k]:.2f}x"
                    for k in (8, 12, 16)))

# Proposition 1 quotes the smallest weight ever observed. Nothing checked
# it, and the paper carried 0.013 while the artifacts held 0.0035.
_wmin = 1.0
for _f in glob.glob(str(REAL / "*.json")):
    _d = json.loads(Path(_f).read_text())
    if (_d.get("config") or {}).get("aggregator") != "adaptive":
        continue
    for _h in (_d.get("history") or []):
        _w = _h.get("weights") or _h.get("client_weights")
        if _w:
            _wmin = min(_wmin, min(_w))
if _wmin < 1.0:
    print(f"  smallest AHA-Fed weight across all runs: {_wmin:.4f}")
    check("the quoted minimum weight matches the artifacts",
          abs(_wmin - 0.0035) < 0.0005,
          f"{_wmin:.4f} (paper says 0.0035)")



# The paper reports the rule keeps discounting corrupted sites at every level.
for nn in (1, 2, 3):
    weights = []
    for f in sorted(glob.glob(str(REAL / f"multi_aha_n{nn}_s*.json"))):
        d = json.loads(Path(f).read_text())
        w = [r.get("client_weights") for r in d.get("history", [])
             if r.get("client_weights")]
        if w:
            weights.append(sum(w[-1][-nn:]))
    if weights:
        uniform = nn * 0.25
        check(f"corrupted sites down-weighted below uniform at n={nn}",
              st.mean(weights) < uniform,
              f"{st.mean(weights):.3f} vs uniform {uniform:.3f}")

# ------------------------------------------ relative vs absolute quality
print("\n=== Relative vs absolute quality (Section 5.7, validation split) ===")
for corpus, label in (("pneuval", "PneumoniaMNIST"), ("pathval", "PathMNIST")):
    rel = {k: v for k, v in by_seed(f"{corpus}_relq_s*.json", "ece").items()}
    ab = {k: v for k, v in by_seed(f"{corpus}_absq_s*.json", "ece").items()}
    shared = sorted(set(rel) & set(ab))
    if not shared:
        continue
    x = [rel[k] for k in shared]
    y = [ab[k] for k in shared]
    pv = wilcoxon_p(x, y)
    print(f"  {label:<15} ECE relative {st.mean(x):.4f}  absolute {st.mean(y):.4f}"
          f"  p={pv:.4f} (n={len(shared)})" if pv is not None else
          f"  {label:<15} ECE relative {st.mean(x):.4f}  absolute {st.mean(y):.4f}")

    if corpus == "pneuval":
        # The paper claims the variant helps on the binary task.
        check("relative quality lowers ECE on PneumoniaMNIST",
              st.mean(x) < st.mean(y),
              f"{st.mean(x):.4f} vs {st.mean(y):.4f}")
        # ...and says the ECE gain is not yet significant.
        check("relative-quality ECE gain is significant",
              pv is not None and pv < 0.05,
              f"p={pv:.4f}" if pv is not None else "scipy unavailable")
        for metric in ("accuracy", "auroc"):
            rm = by_seed(f"{corpus}_relq_s*.json", metric)
            am = by_seed(f"{corpus}_absq_s*.json", metric)
            sh = sorted(set(rm) & set(am))
            if not sh:
                continue
            xv = [rm[k] for k in sh]
            yv = [am[k] for k in sh]
            pm = wilcoxon_p(xv, yv)
            check(f"relative quality improves {metric} on PneumoniaMNIST",
                  st.mean(xv) > st.mean(yv) and pm is not None and pm < 0.05,
                  f"{st.mean(xv):.4f} vs {st.mean(yv):.4f}, p={pm:.4f}"
                  if pm is not None else "scipy unavailable")
        # Section 5.7 now says only the AUROC gain survives Holm across
        # the three metrics. Twenty seeds moved ECE the wrong way
        # (p = 0.065 at n = 10), so the claim has to be pinned.
        _ps = []
        for _met in ("ece", "accuracy", "auroc"):
            _r = by_seed(f"{corpus}_relq_s*.json", _met)
            _a = by_seed(f"{corpus}_absq_s*.json", _met)
            _sh = sorted(set(_r) & set(_a))
            if len(_sh) > 1:
                _ps.append((_met, wilcoxon_p([_r[k] for k in _sh],
                                             [_a[k] for k in _sh])))
        _ps = [q for q in _ps if q[1] is not None]
        if len(_ps) == 3:
            _ps.sort(key=lambda q: q[1])
            _surv, _ok = [], True
            for _i, (_m, _pv) in enumerate(_ps):
                _ok = _ok and _pv < 0.05 / (3 - _i)
                if _ok:
                    _surv.append(_m)
            check("only AUROC survives Holm on PneumoniaMNIST",
                  _surv == ["auroc"],
                  f"survivors: {_surv}")
    else:
        # And that it is neutral where the absolute rule already worked.
        check("relative quality is neutral on PathMNIST",
              pv is None or pv > 0.05,
              f"p={pv:.4f}" if pv is not None else "scipy unavailable")

# ------------------------------------------------------ ablation (Sec. 6)
print("\n=== Ablation of the AHA-Fed terms (Section 6) ===")
abl_cfg = {
    "volume only":   "path_fedavg_s*.json",
    "distance only": "abl_b4_g0_s*.json",
    "quality only":  "abl_b0_g4_s*.json",
    "full":          "path_aha_fed_s*.json",
}
abl = {k: by_seed(v, "ece") for k, v in abl_cfg.items()}
if all(abl.values()):
    shared_seeds = sorted(set.intersection(*[set(v) for v in abl.values()]))
    for name, vals_by_seed in abl.items():
        xs = [vals_by_seed[k] for k in shared_seeds]
        print(f"  {name:<15} ECE {st.mean(xs):.4f} ± {st.pstdev(xs):.4f} "
              f"(n={len(xs)})")

    full = [abl["full"][k] for k in shared_seeds]
    dist = [abl["distance only"][k] for k in shared_seeds]
    vol = [abl["volume only"][k] for k in shared_seeds]
    qual = [abl["quality only"][k] for k in shared_seeds]

    check("removing the quality term hurts",
          st.mean(dist) > st.mean(full),
          f"distance only {st.mean(dist):.4f} vs full {st.mean(full):.4f}")
    check("the distance term alone is worse than volume weighting",
          st.mean(dist) > st.mean(vol),
          f"{st.mean(dist):.4f} vs {st.mean(vol):.4f}")
    # The paper states this against itself; a reversal would need the text
    # changed, so it is tracked as a documented limitation.
    check("the full rule beats the quality term alone",
          st.mean(full) < st.mean(qual),
          f"full {st.mean(full):.4f} vs quality only {st.mean(qual):.4f}")

    # Table 10's "vs full" column uses (row - full)/row, the same convention
    # as Table 3. Nothing checked the arithmetic, and the two tables using
    # different conventions would be a fair referee complaint.
    for _name, _vals, _claim in (("volume only", vol, 19.1),
                                 ("distance only", dist, 25.7),
                                 ("quality only", qual, -16.0)):
        _pct = (st.mean(_vals) - st.mean(full)) / st.mean(_vals) * 100
        check(f"Table 10 '{_name}' percentage",
              abs(_pct - _claim) < 0.6,
              f"{_pct:+.1f}% (paper says {_claim:+.1f}%)")


# The 16% quality-only advantage is claimed to be federation-specific;
# these sweeps are what bounds it.
qonly_h, full_h = [], []
for h in ("0.0", "0.3", "0.5", "0.7", "0.9"):
    q = by_seed(f"qonly_het_h{h}_s*.json", "ece")
    fl = by_seed(f"real_het_aha_h{h}_s*.json", "ece")
    fl.update(by_seed(f"real_het_aha_h{h}.json", "ece"))
    sh = sorted(set(q) & set(fl))
    qonly_h += [q[k] for k in sh]
    full_h += [fl[k] for k in sh]

qonly_n, full_n = [], []
for r in ("0.0", "0.3", "0.5", "0.7"):
    q = by_seed(f"qonly_noise_n{r}_s*.json", "ece")
    fl = by_seed(f"real_noise_aha_n{r}_s*.json", "ece")
    sh = sorted(set(q) & set(fl))
    qonly_n += [q[k] for k in sh]
    full_n += [fl[k] for k in sh]

if qonly_h and qonly_n:
    ph = wilcoxon_p(qonly_h, full_h)
    pn = wilcoxon_p(qonly_n, full_n)
    print(f"  heterogeneity sweep: q-only {st.mean(qonly_h):.4f} vs full "
          f"{st.mean(full_h):.4f}, p={ph:.4f} (n={len(qonly_h)})")
    print(f"  noise sweep        : q-only {st.mean(qonly_n):.4f} vs full "
          f"{st.mean(full_n):.4f}, p={pn:.4f} (n={len(qonly_n)})")
    check("dropping the distance term does not help across the sweeps",
          not (ph < 0.05 and st.mean(qonly_h) < st.mean(full_h)),
          f"heterogeneity p={ph:.4f}")
    check("the full rule leads on the noise sweep",
          st.mean(full_n) < st.mean(qonly_n),
          f"{st.mean(full_n):.4f} vs {st.mean(qonly_n):.4f}")


# ------------------------------------------- quality-signal diagnostic
def quality_ratio_paths(paths) -> tuple[float, float, int, int] | None:
    """Same computation as quality_ratio, over an explicit path list."""
    signals, spreads, correct, n = [], [], 0, 0
    for f in sorted(paths):
        d = json.loads(Path(f).read_text())
        qs = [r.get("client_quality") for r in d.get("history", [])
              if r.get("client_quality")]
        if not qs:
            continue
        q = qs[-1]
        noisy_idx = (d.get("config") or {}).get("noisy_client")
        if noisy_idx is None:
            noisy_idx = len(q) - 1   # NIH corrupts the last center
        if noisy_idx >= len(q):
            continue
        clean = [x for i, x in enumerate(q) if i != noisy_idx]
        signals.append(st.mean(clean) - q[noisy_idx])
        spreads.append(max(clean) - min(clean))
        correct += q[noisy_idx] == min(q)
        n += 1
    if not n:
        return None
    return st.mean(signals), st.mean(spreads), correct, n


def quality_ratio(pattern: str) -> tuple[float, float, int, int] | None:
    """Corruption signal vs spread among clean clients, from stored quality.

    Returns (signal, spread, times the corrupted client ranked worst, runs).
    """
    signals, spreads, correct, n = [], [], 0, 0
    for f in sorted(glob.glob(str(REAL / pattern))):
        d = json.loads(Path(f).read_text())
        qs = [r.get("client_quality") for r in d.get("history", [])
              if r.get("client_quality")]
        if not qs:
            continue
        q = qs[-1]
        noisy_idx = (d.get("config") or {}).get("noisy_client")
        if noisy_idx is None or noisy_idx >= len(q):
            continue
        clean = [x for i, x in enumerate(q) if i != noisy_idx]
        signals.append(st.mean(clean) - q[noisy_idx])
        spreads.append(max(clean) - min(clean))
        correct += q[noisy_idx] == min(q)
        n += 1
    if not n:
        return None
    return st.mean(signals), st.mean(spreads), correct, n


print("\n=== Quality-signal diagnostic (Section 5.7) ===")
diag = {}
for name, pat in (("PathMNIST", "path_aha_fed_s*.json"),
                  ("PneumoniaMNIST", "pneu_aha_fed_s*.json")):
    r = quality_ratio(pat)
    if not r:
        continue
    sig, spr, correct, n = r
    diag[name] = sig / spr if spr else float("inf")
    print(f"  {name:<15} signal {sig:.4f}  spread {spr:.4f}  "
          f"ratio {diag[name]:.2f}  corrupted ranked worst {correct}/{n}")

if "PathMNIST" in diag and "PneumoniaMNIST" in diag:
    check("diagnostic ratio separates the two tasks",
          diag["PathMNIST"] > 1 > diag["PneumoniaMNIST"],
          f"PathMNIST {diag['PathMNIST']:.2f}, "
          f"PneumoniaMNIST {diag['PneumoniaMNIST']:.2f}")

# Section 5.7 now reports the diagnostic on NIH as an out-of-sample test:
# it was computed after the NIH outcome was measured, and the ordering
# across all three corpora is the paper's main evidence for it.
_nih_q = quality_ratio_paths(sorted(glob.glob(
    str(ROOT / "runs" / "paper" / "nih" / "nih_noisy_aha_fed_s*.json"))))
if _nih_q:
    _sig, _spr, _worst, _n = _nih_q
    _ratio = _sig / _spr if _spr else float("inf")
    diag["NIH"] = _ratio
    print(f"  {'NIH':<15} signal {_sig:.4f}  spread {_spr:.4f}  "
          f"ratio {_ratio:.2f}  corrupted ranked worst {_worst}/{_n}")
    check("the NIH diagnostic sits between the two MedMNIST corpora",
          diag["PneumoniaMNIST"] < _ratio < diag["PathMNIST"],
          f"{diag['PneumoniaMNIST']:.2f} < {_ratio:.2f} < "
          f"{diag['PathMNIST']:.2f}")
    check("the corrupted NIH center is always ranked worst",
          _worst == _n, f"{_worst}/{_n}")
    check("the diagnostic orders the three corpora by outcome",
          diag["PathMNIST"] > diag["NIH"] > diag["PneumoniaMNIST"],
          f"PathMNIST {diag['PathMNIST']:.2f} > NIH {diag['NIH']:.2f} > "
          f"PneumoniaMNIST {diag['PneumoniaMNIST']:.2f}")


# ------------------------------------------------------- NIH ChestX-ray14
NIH = ROOT / "runs" / "paper" / "nih"
nih_files = sorted(glob.glob(str(NIH / "*.json")))
if nih_files:
    print("\n=== NIH ChestX-ray14 (224x224, 14 findings) ===")
    nih = {}
    for f in nih_files:
        d = json.loads(Path(f).read_text())
        cfg, fin = d.get("config", {}), d.get("final") or {}
        agg = cfg.get("aggregator")
        key = (cfg.get("images_per_center"), cfg.get("noisy_rate") or 0.0)
        nih.setdefault(key, {})[agg] = fin
        print(f"  {Path(f).stem}: AUROC {fin.get('auroc', 0):.4f}  "
              f"ECE {fin.get('ece', 0):.4f}  acc {fin.get('accuracy', 0):.4f}")

    deep = nih.get((8000, 0.0), {}).get("fedavg")
    if deep:
        check("NIH FedAvg macro AUROC is at least 0.95",
              (deep.get("auroc") or 0) >= 0.95, f"{deep.get('auroc', 0):.4f}")
        check("NIH scores all 14 findings",
              deep.get("findings_scored") == 14,
              f"{deep.get('findings_scored')} findings")

    clean = nih.get((2000, 0.0), {})
    if "aha_fed" in clean and "fedavg" in clean:
        a, v = clean["aha_fed"], clean["fedavg"]
        # The paper reports this as a null result, so a reversal is news.
        check("AHA-Fed leads FedAvg on the clean NIH federation",
              (a.get("ece") or 1) < (v.get("ece") or 1),
              f"ECE {a.get('ece', 0):.4f} vs {v.get('ece', 0):.4f}")
    if "fedbn" in clean and "aha_fed" in clean:
        check("AHA-Fed beats FedBN on the clean NIH federation",
              (clean["aha_fed"].get("ece") or 1) < (clean["fedbn"].get("ece") or 1),
              f"ECE {clean['aha_fed'].get('ece', 0):.4f} vs "
              f"{clean['fedbn'].get('ece', 0):.4f}")

    # Corrupted federation: several seeds, so pair them rather than
    # overwriting one with the next.
    noisy_by_seed = {}
    for f in nih_files:
        d = json.loads(Path(f).read_text())
        cfg, fin = d.get("config", {}), d.get("final") or {}
        if (cfg.get("noisy_rate") or 0.0) == 0.0:
            continue
        noisy_by_seed.setdefault(cfg.get("aggregator"), {})[
            str(cfg.get("seed"))] = fin

    a_by = noisy_by_seed.get("aha_fed", {})
    v_by = noisy_by_seed.get("fedavg", {})
    common = sorted(set(a_by) & set(v_by))
    if common:
        a_ece = [a_by[c]["ece"] for c in common]
        v_ece = [v_by[c]["ece"] for c in common]
        red = (st.mean(v_ece) - st.mean(a_ece)) / st.mean(v_ece) * 100
        pv = wilcoxon_p(a_ece, v_ece)
        detail = (f"ECE {st.mean(a_ece):.4f} vs {st.mean(v_ece):.4f} "
                  f"({red:+.1f}%, p={pv:.3f}, n={len(common)})"
                  if pv is not None else
                  f"ECE {st.mean(a_ece):.4f} vs {st.mean(v_ece):.4f} "
                  f"({red:+.1f}%, n={len(common)})")
        check("AHA-Fed beats FedAvg on the corrupted NIH federation",
              red > 0, detail)
        # The paper says this is the right direction but not established.
        check("corrupted NIH advantage is significant",
              pv is not None and pv < 0.05, detail)

# ----------------------------------------------------------------- weights
print("\n=== AHA-Fed down-weights the corrupted client ===")
w = vals(["real_noise_aha_n0.5_s42.json"], "client_weights")
if w:
    weights = w[0]
    cfg = json.loads((REAL / "real_noise_aha_n0.5_s42.json").read_text())["config"]
    noisy = cfg.get("noisy_client")
    uniform = 1 / len(weights)
    print(f"  final weights {weights}, noisy client index {noisy}, "
          f"uniform {uniform:.3f}")
    check("noisy client is down-weighted below uniform",
          weights[noisy] < uniform,
          f"{weights[noisy]:.4f} < {uniform:.4f}")

print("\n" + "=" * 60)
if FAILED:
    print(f"{len(FAILED)} CLAIM(S) OUT OF SYNC WITH THE PAPER:")
    for f in FAILED:
        print(f"  - {f}")
    sys.exit(1)
print(f"All positive claims verified against real-data run artifacts; "
      f"{len(KNOWN_LIMITATIONS)} documented limitations still hold.")
