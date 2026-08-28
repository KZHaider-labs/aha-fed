"""Build AHA_Fed_Equations.docx with typed text equations — NO images."""
from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "paper" / "AHA_Fed_Equations.docx"

BLUE  = RGBColor(0x1F, 0x3A, 0x5F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY  = RGBColor(0x55, 0x55, 0x55)


def _shade(para, hex_color: str):
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    pPr.append(shd)


def _border_bottom(para, color="1F3A5F", sz="6"):
    pPr  = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    sz)
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), color)
    pBdr.append(bot)
    pPr.append(pBdr)


def sec_heading(doc, text: str):
    """Blue banner heading."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    _shade(p, "1F3A5F")
    r = p.add_run(f"  {text}")
    r.bold = True
    r.font.size = Pt(12)
    r.font.name = "Times New Roman"
    r.font.color.rgb = WHITE


def sub_heading(doc, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(3)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"
    r.font.color.rgb = BLUE


def body_text(doc, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(0.5)
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"


def equation(doc, label: str, eq_text: str, note: str = ""):
    """
    Renders a typed equation with:
      left side  = equation text (bold, Cambria Math-like via Cambria)
      right side = label like (1)
    Followed by an optional note line.
    """
    # equation row
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(2)
    _shade(p, "F0F4FF")

    # equation body
    r_eq = p.add_run(eq_text)
    r_eq.font.size = Pt(13)
    r_eq.font.name = "Cambria"
    r_eq.bold = True

    # spacer + label
    r_lbl = p.add_run(f"          ({label})")
    r_lbl.font.size = Pt(11)
    r_lbl.font.name = "Times New Roman"
    r_lbl.font.color.rgb = GREY

    # optional note
    if note:
        np_ = doc.add_paragraph()
        np_.alignment = WD_ALIGN_PARAGRAPH.LEFT
        np_.paragraph_format.left_indent  = Cm(1.5)
        np_.paragraph_format.space_after  = Pt(8)
        nr = np_.add_run(note)
        nr.italic = True
        nr.font.size = Pt(10)
        nr.font.name = "Times New Roman"
        nr.font.color.rgb = GREY


def algo_line(doc, text: str, indent_cm: float = 0.5, bold=False, shade=False):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(indent_cm)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after  = Pt(1)
    if shade:
        _shade(p, "DDE8FF")
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    r.font.name = "Courier New"
    r.bold = bold


# ═══════════════════════════════════════════════════════════════════════════════

def build():
    doc = Document()
    for sec in doc.sections:
        sec.top_margin    = Cm(2.2)
        sec.bottom_margin = Cm(2.2)
        sec.left_margin   = Cm(2.8)
        sec.right_margin  = Cm(2.8)

    # ── Title ─────────────────────────────────────────────────────────────────
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_after = Pt(2)
    tr = tp.add_run("AHA-Fed: Adaptive Heterogeneity-Aware Federated Learning")
    tr.bold = True; tr.font.size = Pt(16); tr.font.name = "Times New Roman"
    tr.font.color.rgb = BLUE

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.paragraph_format.space_after = Pt(6)
    sr = sp.add_run("Equations & Algorithm — Mathematical Framework")
    sr.font.size = Pt(12); sr.font.name = "Times New Roman"
    sr.font.color.rgb = GREY

    div = doc.add_paragraph()
    div.paragraph_format.space_after = Pt(2)
    _border_bottom(div)

    # ══════════════════════════════════════════════════════════════════════════
    # A. PROBLEM FORMULATION
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "A.  Problem Formulation")
    body_text(doc,
        "Let K hospitals each hold a private dataset 𝒟k with nk samples drawn "
        "from centre-specific distribution Pk(x, y). The federated objective is "
        "the weighted empirical risk minimised jointly across all centres:")

    equation(doc, "1",
        "min  Σk  wk · Lk(θ)",
        "θ = global model,  wk = aggregation weight (Σwk = 1),  Lk = empirical risk at client k.\n"
        "FedAvg sets wk = nk / Σnj.  AHA-Fed learns wk adaptively using Eqs 2–6.")

    # ══════════════════════════════════════════════════════════════════════════
    # B. CLIENT SIGNALS
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "B.  AHA-Fed Client Signals  (computed each round)")

    sub_heading(doc, "B.1  Heterogeneity Signal  Dk")
    body_text(doc,
        "Total-variation distance between client k's empirical label prior πk "
        "and the federation-wide consensus π̄. High Dk means the centre is a "
        "distributional outlier and should be down-weighted.")
    equation(doc, "2",
        "Dk  =  ½ · Σc | πk(c) − π̄(c) |",
        "πk(c) = fraction of class c at client k.   π̄(c) = (1/K) Σk πk(c).\n"
        "Range: Dk ∈ [0, 1].   Dk = 0  ⟹  perfectly representative client.")

    sub_heading(doc, "B.2  Quality Signal  qk")
    body_text(doc,
        "Mean training loss mapped through a smooth bounded function. Noisy "
        "clients (corrupted labels) sustain high loss so qk → 0; clean clients "
        "converge to low loss so qk → 1.")
    equation(doc, "3",
        "qk  =  1 / (1 + Lk)",
        "Lk = mean cross-entropy on client k's local mini-batch after local training.\n"
        "Range: qk ∈ (0, 1].   qk → 1  ⟹  clean well-converging client.")

    # ══════════════════════════════════════════════════════════════════════════
    # C. AGGREGATION RULE
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "C.  AHA-Fed Aggregation Rule")

    sub_heading(doc, "C.1  Log-Space Client Score  sk")
    body_text(doc,
        "Three signals are combined in log-space to form a scalar score for "
        "each client.  α controls volume influence, β penalises outliers, "
        "γ rewards quality.")
    equation(doc, "4",
        "sk  =  α · log(nk)  −  β · Dk  +  γ · log(qk)",
        "Default hyperparameters:  α = 1,  β = 4,  γ = 4.\n"
        "α · log(nk) : anti-collapse term   |   −β · Dk : outlier penalty   |   γ · log(qk) : quality reward")

    sub_heading(doc, "C.2  Softmax Weight Normalisation")
    body_text(doc,
        "Aggregation weights are produced by a numerically stable softmax "
        "(subtract the row maximum before exponentiating):")
    equation(doc, "5",
        "wk  =  exp(sk) / Σj exp(sj)",
        "Stable form:  wk = exp(sk − maxj sj) / Σj exp(sj − maxj sj).\n"
        "Properties:  wk > 0 for all k,   Σk wk = 1.")

    sub_heading(doc, "C.3  Global Model Update")
    body_text(doc,
        "The softmax weights are applied to per-client parameter deltas to "
        "form the new global model state:")
    equation(doc, "6",
        "θglobal  ←  Σk  wk · Δθk",
        "Δθk = model delta uploaded by client k.  Only Δθk and scalar qk leave the hospital.")

    sub_heading(doc, "C.4  Reduction to FedAvg  (Special Case)")
    body_text(doc,
        "Setting α = 1, β = 0, γ = 0 collapses the score to log(nk) and "
        "the softmax reduces to standard volume-proportional FedAvg weights:")
    equation(doc, "7",
        "wk  =  nk / Σj nj        [when β = γ = 0]",
        "AHA-Fed strictly generalises FedAvg.  Set β = γ = 0 to recover identical FedAvg behaviour.")

    # ══════════════════════════════════════════════════════════════════════════
    # D. DP-SGD
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "D.  Differential Privacy — DP-SGD Noise Mechanism")
    body_text(doc,
        "Each client runs DP-SGD with per-sample gradient clipping at norm C "
        "and Gaussian noise calibrated by Opacus to meet a target (ε, δ)-budget:")
    equation(doc, "8",
        "g̃t  =  (1/B) · [ Σi∈Bt clip(∇Li, C) ]  +  𝒩(0, σ²C²I)",
        "B = mini-batch size,  C = clipping norm (default 1.0),  σ = noise multiplier.\n"
        "Post-processing immunity of DP ⟹ the (ε, δ) guarantee holds for the global model.")

    # ══════════════════════════════════════════════════════════════════════════
    # E. ECE
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "E.  Calibration Metric — Expected Calibration Error (ECE)")
    body_text(doc,
        "ECE measures alignment between predicted confidence and empirical "
        "accuracy across M equal-width confidence bins.  Perfect calibration ⟹ ECE = 0.")
    equation(doc, "9",
        "ECE  =  Σm  (|Bm| / N) · | acc(Bm) − conf(Bm) |",
        "M = 10 bins,  N = total test samples,  Bm = samples in bin m.\n"
        "Results:  AHA-Fed ECE = 0.085   vs   FedAvg ECE = 0.123  (PathMNIST, 3-seed mean).")

    # ══════════════════════════════════════════════════════════════════════════
    # F. ALGORITHM
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "F.  AHA-Fed Training Algorithm  (Algorithm 1)")

    algo_line(doc, "Input:  K clients, global model θ₀, rounds T, local epochs E,", bold=True)
    algo_line(doc, "        learning rate η, hyperparameters α, β, γ", bold=True)
    algo_line(doc, "        Optional DP config: (C, σ, δ, target ε)", bold=True)
    algo_line(doc, "Output: Trained global model θT", bold=True)
    algo_line(doc, "─" * 65)

    algo_line(doc, "SERVER PRE-COMPUTE:", bold=True)
    algo_line(doc, "   Compute  Dk = ½ Σc |πk(c) − π̄(c)|  for each client k     [Eq 2]", indent_cm=1.0)

    algo_line(doc, "FOR round t = 1, 2, …, T:", bold=True)

    algo_line(doc, "   ── BROADCAST ──────────────────────────────────────────────", indent_cm=1.0)
    algo_line(doc, "   1. Server sends  θt-1  to all K clients", indent_cm=1.0)

    algo_line(doc, "   ── LOCAL TRAINING  (each client k in parallel) ─────────────", indent_cm=1.0)
    algo_line(doc, "   2. Client k: initialise  θk ← θt-1", indent_cm=1.0)
    algo_line(doc, "   3. FOR epoch e = 1, …, E:", indent_cm=1.0)
    algo_line(doc, "         FOR each mini-batch B ⊆ Dk:", indent_cm=1.5)
    algo_line(doc, "           IF DP enabled:", indent_cm=2.0)
    algo_line(doc, "             g̃ ← (1/B)[Σi clip(∇Li, C)] + 𝒩(0,σ²C²I)   [Eq 8]", indent_cm=2.5, shade=True)
    algo_line(doc, "           ELSE:", indent_cm=2.0)
    algo_line(doc, "             g̃ ← standard SGD gradient", indent_cm=2.5)
    algo_line(doc, "           θk ← θk − η · g̃", indent_cm=2.5)
    algo_line(doc, "   4. Lk ← mean training loss on Dk", indent_cm=1.0)
    algo_line(doc, "      qk ← 1 / (1 + Lk)                                   [Eq 3]", indent_cm=1.0, shade=True)
    algo_line(doc, "   5. Upload  (Δθk = θk − θt-1,  qk,  nk)  to server", indent_cm=1.0)

    algo_line(doc, "   ── AHA-FED AGGREGATION  (server) ────────────────────────────", indent_cm=1.0)
    algo_line(doc, "   6. FOR each client k:", indent_cm=1.0)
    algo_line(doc, "         sk ← α·log(nk) − β·Dk + γ·log(qk)               [Eq 4]", indent_cm=1.5, shade=True)
    algo_line(doc, "   7. wk ← exp(sk) / Σj exp(sj)                           [Eq 5]", indent_cm=1.0, shade=True)
    algo_line(doc, "   8. θt ← Σk  wk · Δθk                                  [Eq 6]", indent_cm=1.0, shade=True)

    algo_line(doc, "   ── EVALUATION ──────────────────────────────────────────────", indent_cm=1.0)
    algo_line(doc, "   9. Evaluate θt → record loss, accuracy, AUROC, ECE     [Eq 9]", indent_cm=1.0)
    algo_line(doc, "END FOR", bold=True)
    algo_line(doc, "Return  θT", bold=True)
    algo_line(doc, "─" * 65)

    # ══════════════════════════════════════════════════════════════════════════
    # G. HYPERPARAMETER TABLE
    # ══════════════════════════════════════════════════════════════════════════
    sec_heading(doc, "G.  Hyperparameter Quick Reference")

    tbl = doc.add_table(rows=1, cols=4)
    tbl.style = "Table Grid"
    headers = ["Symbol", "Default", "Role", "Effect when increased"]
    for cell, txt in zip(tbl.rows[0].cells, headers):
        p = cell.paragraphs[0]
        run = p.add_run(txt)
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = "Times New Roman"
        tcPr = cell._tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  "1F3A5F")
        tcPr.append(shd)
        run.font.color.rgb = WHITE

    rows = [
        ("α", "1.0",  "Volume anti-collapse weight", "Larger clients gain more influence"),
        ("β", "4.0",  "Heterogeneity penalty",        "Outlier centres down-weighted more"),
        ("γ", "4.0",  "Quality (loss) reward",         "Low-loss clients up-weighted more"),
        ("ε", "—",    "DP privacy budget",              "Weaker privacy, lower noise added"),
        ("δ", "1e-5", "DP failure probability",         "—"),
        ("C", "1.0",  "Gradient clipping norm",         "More clipping, more noise needed"),
        ("σ", "auto", "DP noise multiplier",             "More noise, stronger privacy"),
        ("E", "2",    "Local epochs per round",          "More compute, more client drift"),
        ("η", "0.01", "Local learning rate",             "Faster convergence, instability risk"),
    ]
    for sym, default, role, effect in rows:
        row = tbl.add_row().cells
        for cell, txt in zip(row, [sym, default, role, effect]):
            p = cell.paragraphs[0]
            run = p.add_run(txt)
            run.font.size = Pt(10)
            run.font.name = "Times New Roman"

    doc.add_paragraph()

    doc.save(OUT)
    print(f"[done] {OUT}")


if __name__ == "__main__":
    build()
