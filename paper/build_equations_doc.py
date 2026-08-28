"""Generate AHA_Fed_Equations.docx — all 9 equations + Algorithm 1."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT  = Path(__file__).resolve().parent.parent
FIGS  = ROOT / "paper" / "figures"
EQ    = FIGS / "equations"
OUT   = ROOT / "paper" / "AHA_Fed_Equations.docx"

BLUE  = RGBColor(0x1F, 0x3A, 0x5F)
LIGHT = RGBColor(0xE8, 0xF0, 0xFB)   # light blue shading

# ── helpers ──────────────────────────────────────────────────────────────────

def _shade_para(para, hex_color: str):
    """Apply background shading to a paragraph."""
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    pPr.append(shd)


def heading(doc, text: str, level: int = 1):
    sizes = {1: 16, 2: 13, 3: 12}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18 if level == 1 else 12)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(sizes.get(level, 12))
    run.font.name = "Times New Roman"
    run.font.color.rgb = BLUE


def body(doc, text: str, indent: float = 0.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(indent)
    p.paragraph_format.space_after  = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.name = "Times New Roman"


def eq_image(doc, fname: str, label: str, description: str,
             width_in: float = 5.4):
    """Blue label row  →  shaded equation image  →  description."""

    # label banner
    lp = doc.add_paragraph()
    lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    lp.paragraph_format.space_before = Pt(8)
    lp.paragraph_format.space_after  = Pt(0)
    lr = lp.add_run(f"  Equation {label}")
    lr.bold = True
    lr.font.size = Pt(10.5)
    lr.font.name = "Times New Roman"
    lr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    _shade_para(lp, "1F3A5F")

    # equation image (centred, light-shaded row)
    ip = doc.add_paragraph()
    ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ip.paragraph_format.space_before = Pt(6)
    ip.paragraph_format.space_after  = Pt(6)
    _shade_para(ip, "EBF2FF")
    ip.add_run().add_picture(str(EQ / fname), width=Inches(width_in))

    # italic description
    dp = doc.add_paragraph()
    dp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    dp.paragraph_format.space_after  = Pt(12)
    dp.paragraph_format.left_indent  = Cm(0.4)
    dr = dp.add_run(description)
    dr.italic = True
    dr.font.size = Pt(10)
    dr.font.name = "Times New Roman"


def algo_image(doc, path: Path, caption: str, width_in: float = 6.2):
    lp = doc.add_paragraph()
    lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    lp.paragraph_format.space_before = Pt(8)
    lp.paragraph_format.space_after  = Pt(0)
    lr = lp.add_run("  Algorithm 1  —  AHA-Fed Federated Training Loop")
    lr.bold = True
    lr.font.size = Pt(10.5)
    lr.font.name = "Times New Roman"
    lr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    _shade_para(lp, "1F3A5F")

    ip = doc.add_paragraph()
    ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ip.paragraph_format.space_before = Pt(6)
    ip.paragraph_format.space_after  = Pt(6)
    _shade_para(ip, "EBF2FF")
    ip.add_run().add_picture(str(path), width=Inches(width_in))

    dp = doc.add_paragraph()
    dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dp.paragraph_format.space_after  = Pt(12)
    dr = dp.add_run(caption)
    dr.italic = True
    dr.font.size = Pt(10)
    dr.font.name = "Times New Roman"


def divider(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "4")
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), "1F3A5F")
    pBdr.append(bot)
    pPr.append(pBdr)


# ── build document ────────────────────────────────────────────────────────────

def build():
    doc = Document()

    # page margins
    for section in doc.sections:
        section.top_margin    = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin   = Cm(2.8)
        section.right_margin  = Cm(2.8)

    # ── title block ──────────────────────────────────────────────────────────
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_before = Pt(6)
    tp.paragraph_format.space_after  = Pt(4)
    tr = tp.add_run("AHA-Fed: Adaptive Heterogeneity-Aware Federated Learning")
    tr.bold = True
    tr.font.size = Pt(17)
    tr.font.name = "Times New Roman"
    tr.font.color.rgb = BLUE

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.paragraph_format.space_after = Pt(2)
    sr = sp.add_run("Mathematical Framework: Equations & Algorithm")
    sr.font.size = Pt(13)
    sr.font.name = "Times New Roman"
    sr.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    divider(doc)

    # ── Section A: Problem Formulation ───────────────────────────────────────
    heading(doc, "A.  Problem Formulation", level=1)
    body(doc,
         "Let K hospitals each hold a private dataset 𝒟_k with n_k samples "
         "drawn from centre-specific distribution P_k(x, y). Centres differ in "
         "label prior π_k, input distribution P_k(x|y), and label-noise rate. "
         "The federated objective is the weighted empirical risk minimised "
         "jointly across all centres:")
    eq_image(doc,
             "eq1_objective.png", "(1)",
             "Federated objective: weighted sum of per-client empirical risks. "
             "{w_k} lives on the probability simplex. FedAvg sets w_k = n_k / Σ n_j; "
             "AHA-Fed turns the simplex into an adaptive function of three "
             "per-round observable signals.",
             width_in=5.6)

    divider(doc)

    # ── Section B: AHA-Fed Signals ───────────────────────────────────────────
    heading(doc, "B.  AHA-Fed Client Signals (computed once per round)", level=1)

    heading(doc, "B.1  Heterogeneity signal  D_k", level=2)
    body(doc,
         "Total-variation distance between client k's empirical label prior π_k "
         "and the across-client consensus π̄. High D_k indicates a centre whose "
         "class distribution is far from the federation mean — its gradient "
         "direction may conflict with the global objective and should receive a "
         "down-weighted aggregation contribution.")
    eq_image(doc,
             "eq2_distance.png", "(2)",
             "D_k = ½ Σ_c |π_k(c) − π̄(c)|. Computed once at training start "
             "from clients' label-count vectors. Ranges in [0, 1]; "
             "D_k = 0 ⟺ client is perfectly representative of the federation.",
             width_in=5.4)

    heading(doc, "B.2  Quality signal  q_k", level=2)
    body(doc,
         "The client's mean training loss mapped through a smooth bounded "
         "function. A noisy client (corrupted labels) sustains persistently high "
         "loss, so q_k → 0; a clean well-converging client achieves low loss, "
         "so q_k → 1.")
    eq_image(doc,
             "eq3_quality.png", "(3)",
             "q_k = 1 / (1 + L_k), where L_k is mean cross-entropy on client k's "
             "local mini-batch at the end of its local training phase. Bounded in "
             "(0, 1]; monotonically decreasing in loss.",
             width_in=6.0)

    divider(doc)

    # ── Section C: Aggregation Rule ──────────────────────────────────────────
    heading(doc, "C.  AHA-Fed Aggregation Rule", level=1)

    heading(doc, "C.1  Log-space scoring", level=2)
    body(doc,
         "Three signals — volume n_k (anti-collapse), heterogeneity D_k "
         "(outlier penalty), and quality q_k (quality reward) — are linearly "
         "combined in log-space to form the client log-score:")
    eq_image(doc,
             "eq4_score.png", "(4)",
             "s_k = α·log(n_k) − β·D_k + γ·log(q_k). "
             "α ≥ 0 prevents volume-collapse, β ≥ 0 penalises distributional "
             "outliers, γ ≥ 0 rewards low-loss clients. "
             "Default values: α = 1, β = 4, γ = 4.",
             width_in=5.4)

    heading(doc, "C.2  Softmax weight normalisation", level=2)
    body(doc,
         "Aggregation weights are produced by a numerically stable softmax "
         "(subtract the row maximum before exponentiating) applied to the "
         "log-scores:")
    eq_image(doc,
             "eq5_softmax.png", "(5)",
             "w_k = exp(s_k) / Σ_j exp(s_j). Numerically stable variant: "
             "subtract max_j s_j from all scores before exponentiation. "
             "Weights sum to 1; each w_k > 0.",
             width_in=5.6)

    heading(doc, "C.3  Global model aggregation", level=2)
    body(doc,
         "The softmax weights are applied to the per-client parameter deltas "
         "to form the new global state:")
    eq_image(doc,
             "eq6_aggregation.png", "(6)",
             "θ_global ← Σ_k w_k · Δθ_k. "
             "No raw client data ever leaves the hospital — only the model "
             "delta Δθ_k and the scalar q_k are transmitted.",
             width_in=4.6)

    heading(doc, "C.4  Reduction to FedAvg (special case)", level=2)
    body(doc,
         "Setting α = 1, β = 0, γ = 0 collapses s_k = log(n_k), and the "
         "softmax reduces to volume-proportional weights — exactly FedAvg. "
         "AHA-Fed therefore strictly generalises FedAvg:")
    eq_image(doc,
             "eq9_fedavg_special.png", "(7)",
             "w_k = n_k / Σ_j n_j when β = γ = 0. Any federation using FedAvg "
             "can switch to AHA-Fed and recover identical behaviour by zeroing "
             "β and γ, with no other code change required.",
             width_in=5.4)

    divider(doc)

    # ── Section D: Differential Privacy ──────────────────────────────────────
    heading(doc, "D.  Differential Privacy — DP-SGD Noise Mechanism", level=1)
    body(doc,
         "Each client runs DP-SGD with per-sample gradient clipping at norm C "
         "and Gaussian noise scale σ chosen by the Opacus privacy engine to "
         "meet a target (ε, δ)-budget. The noised gradient update is:")
    eq_image(doc,
             "eq7_dpsgd.png", "(8)",
             "g̃_t = (1/B)·[Σ_i clip(∇L_i, C)] + N(0, σ²C²I). "
             "B = mini-batch size, σ = noise multiplier calibrated to target ε. "
             "Post-processing immunity of DP implies the (ε, δ) guarantee "
             "carries through the AHA-Fed aggregation step unchanged.",
             width_in=5.6)

    divider(doc)

    # ── Section E: Calibration Metric ────────────────────────────────────────
    heading(doc, "E.  Calibration Metric — Expected Calibration Error (ECE)", level=1)
    body(doc,
         "ECE measures alignment between predicted confidence and empirical "
         "accuracy, partitioned into M equal-width confidence bins. It is the "
         "primary clinical metric because a confidently-wrong model is more "
         "dangerous than an uncertain but well-calibrated one:")
    eq_image(doc,
             "eq8_ece.png", "(9)",
             "ECE = Σ_m (|B_m|/N) · |acc(B_m) − conf(B_m)|. "
             "M = 10 bins used throughout. Perfect calibration ⟹ ECE = 0. "
             "AHA-Fed achieves ECE ≈ 0.085 vs. FedAvg ECE ≈ 0.123 on PathMNIST.",
             width_in=5.6)

    divider(doc)

    # ── Section F: Algorithm ─────────────────────────────────────────────────
    heading(doc, "F.  AHA-Fed Training Algorithm", level=1)
    body(doc,
         "Algorithm 1 below gives the complete round-by-round training loop. "
         "Steps 1–3 are identical to FedAvg (broadcast, local train, upload). "
         "The only AHA-Fed-specific computation is in steps 4–6: computing the "
         "three signals, forming log-scores via Equation (4), and aggregating "
         "via Equations (5)–(6). The per-round overhead is O(K) arithmetic — "
         "negligible versus the local training cost.")
    algo_image(doc,
               FIGS / "fig_algorithm.png",
               "Algorithm 1: AHA-Fed federated training loop. "
               "AHA-Fed-specific steps are highlighted in blue.",
               width_in=6.2)

    divider(doc)

    # ── quick-reference table ─────────────────────────────────────────────────
    heading(doc, "G.  Hyperparameter Quick Reference", level=1)

    tbl = doc.add_table(rows=1, cols=4)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for cell, txt in zip(hdr, ["Symbol", "Default", "Role", "Effect when ↑"]):
        cell.text = txt
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.size = Pt(10)
            run.font.name = "Times New Roman"
        from docx.oxml import OxmlElement as OE
        tcPr = cell._tc.get_or_add_tcPr()
        shd  = OE("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  "1F3A5F")
        tcPr.append(shd)
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    rows_data = [
        ("α", "1.0", "Volume anti-collapse weight", "Larger clients gain more influence"),
        ("β", "4.0", "Heterogeneity penalty",        "Outlier centres down-weighted more"),
        ("γ", "4.0", "Quality (loss) reward",         "Low-loss clients up-weighted more"),
        ("ε", "—",   "DP privacy budget",             "Weaker privacy, lower noise"),
        ("δ", "1e-5","DP failure probability",         "—"),
        ("C", "1.0", "Gradient clipping norm",        "Stronger clipping, more noise needed"),
    ]
    for sym, default, role, effect in rows_data:
        row = tbl.add_row().cells
        for cell, txt in zip(row, [sym, default, role, effect]):
            cell.text = txt
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(10)
                run.font.name = "Times New Roman"

    doc.add_paragraph()   # bottom spacing

    doc.save(OUT)
    print(f"[done] Saved: {OUT}")


if __name__ == "__main__":
    build()
