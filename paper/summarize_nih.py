"""Summarise the NIH ChestX-ray14 runs into the numbers the paper needs.

NIH results land in runs/paper/nih/ (from the Kaggle notebooks' output zips).
This is a 14-finding multi-label task at 224x224, so AUROC/AUPRC are macro-
averaged over findings and accuracy is exact-match over the whole label vector.

Runs are grouped by configuration — images per center, rounds, and whether a
center was corrupted — because averaging across those would compare unlike
things.

Run:  python paper/summarize_nih.py
"""
from __future__ import annotations

import glob
import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
NIH = ROOT / "runs" / "paper" / "nih"

LABEL = {"aha_fed": "AHA-Fed", "fedavg": "FedAvg", "fedbn": "FedBN",
         "fedprox": "FedProx", "feddisco": "FedDisco"}


def fmt(vals: list[float], nd: int = 4) -> str:
    if not vals:
        return "—"
    if len(vals) == 1:
        return f"{vals[0]:.{nd}f}"
    return f"{st.mean(vals):.{nd}f} ± {st.pstdev(vals):.{nd}f} (n={len(vals)})"


files = sorted(glob.glob(str(NIH / "*.json")))
if not files:
    print(f"No NIH runs yet under {NIH}")
    print("Download a Kaggle notebook's results zip and unzip it here.")
    raise SystemExit(0)

# group: (images/center, rounds, noise rate) -> aggregator -> metric -> values
groups: dict[tuple, dict[str, dict[str, list[float]]]] = defaultdict(
    lambda: defaultdict(lambda: defaultdict(list)))

for f in files:
    d = json.loads(Path(f).read_text())
    cfg = d.get("config", {})
    fin = d.get("final") or {}
    stem = Path(f).stem
    m = re.search(r"nih_(?:noisy_|clean_)?(aha_fed|fedavg|fedbn|fedprox|feddisco)",
                  stem)
    if not m:
        continue
    key = (cfg.get("images_per_center"), len(d.get("history", [])),
           cfg.get("noisy_rate") or 0.0)
    for metric in ("auroc", "auprc", "ece", "accuracy"):
        v = fin.get(metric)
        if v is not None:
            groups[key][m.group(1)][metric].append(v)

for key in sorted(groups, key=lambda k: (-(k[2] or 0), -(k[0] or 0))):
    imgs, rounds, noise = key
    title = (f"{imgs} images/center, {rounds} rounds"
             + (f", {noise:.0%} label noise at one center" if noise
                else ", clean federation"))
    print("=" * 74)
    print(title)
    print("=" * 74)
    print(f"{'aggregator':<12}{'AUROC':<26}{'AUPRC':<20}{'ECE':<22}acc")
    rows = groups[key]
    for tag in ["aha_fed", "fedavg", "fedbn", "fedprox", "feddisco"]:
        if tag not in rows:
            continue
        r = rows[tag]
        print(f"{LABEL[tag]:<12}{fmt(r['auroc']):<26}{fmt(r['auprc']):<20}"
              f"{fmt(r['ece']):<22}{fmt(r['accuracy'])}")

    aha, avg = rows.get("aha_fed"), rows.get("fedavg")
    if aha and avg and aha["auroc"] and avg["auroc"]:
        d_au = st.mean(aha["auroc"]) - st.mean(avg["auroc"])
        d_ece = (st.mean(avg["ece"]) - st.mean(aha["ece"])) / st.mean(avg["ece"]) * 100
        print(f"\nAHA-Fed vs FedAvg: AUROC {d_au:+.4f}, ECE {d_ece:+.1f}% "
              f"({'AHA-Fed better' if d_ece > 0 else 'FedAvg better'} on ECE)")
    print()

print("Note: runs subsample each center. The full corpus needs roughly 41 h "
      "per aggregator at 25 rounds on a P100.")
