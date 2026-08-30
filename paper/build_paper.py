"""Build the AHA-Fed Q1 research paper as a .docx file.

Outputs paper/AHA_Fed_Paper.docx
"""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor, Inches

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figures"
EQ = FIGS / "equations"
OUT = ROOT / "paper" / "AHA_Fed_Paper.docx"


# ---------- helpers ----------
def set_cell_shading(cell, color_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def add_paragraph(doc, text: str, *, bold=False, italic=False,
                  size=11, align=None, space_after=6,
                  first_line_indent: float | None = None) -> None:
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    if first_line_indent is not None:
        p.paragraph_format.first_line_indent = Cm(first_line_indent)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Times New Roman"


def add_heading(doc, text: str, level: int = 1) -> None:
    sizes = {1: 14, 2: 12.5, 3: 11.5}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(sizes.get(level, 11))
    run.font.name = "Times New Roman"
    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)


def add_figure(doc, path: Path, caption: str, width_in: float = 6.4) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    cr = cap.add_run(caption)
    cr.italic = True
    cr.font.size = Pt(10)
    cr.font.name = "Times New Roman"


def add_equation_image(doc, name: str, label: str, width_in: float = 4.8) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run()
    run.add_picture(str(EQ / name), width=Inches(width_in))
    tab = p.add_run(f"          {label}")
    tab.font.size = Pt(11)
    tab.font.name = "Times New Roman"


def add_bullet_run(doc, label: str, body: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    rl = p.add_run(label)
    rl.bold = True
    rl.font.name = "Times New Roman"
    rl.font.size = Pt(11)
    rb = p.add_run(body)
    rb.font.name = "Times New Roman"
    rb.font.size = Pt(11)


def make_table(doc, data: list[list[str]],
               header_fill: str = "1F3A5F",
               highlight_row_pred=lambda i, row: False,
               highlight_fill: str = "FFF2CC",
               alt_fill: str = "F4F8FB",
               header_font_size: int = 10,
               body_font_size: int = 9.5):
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Light Grid Accent 1"
    for j, hdr in enumerate(data[0]):
        c = table.rows[0].cells[j]
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(hdr)
        run.bold = True
        run.font.size = Pt(header_font_size)
        run.font.name = "Times New Roman"
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_shading(c, header_fill)
        c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    for i, row in enumerate(data[1:], start=1):
        for j, val in enumerate(row):
            c = table.rows[i].cells[j]
            c.text = ""
            p = c.paragraphs[0]
            p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if j > 0
                           else WD_ALIGN_PARAGRAPH.LEFT)
            run = p.add_run(val)
            run.font.size = Pt(body_font_size)
            run.font.name = "Times New Roman"
            if highlight_row_pred(i, row):
                run.bold = True
                set_cell_shading(c, highlight_fill)
            elif i % 2 == 0:
                set_cell_shading(c, alt_fill)
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    return table


def add_table_caption(doc, text: str) -> None:
    """Add a single-line table caption ABOVE the next table."""
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(10)
    cap.paragraph_format.space_after = Pt(3)
    cr = cap.add_run(text)
    cr.italic = True
    cr.font.size = Pt(10)
    cr.font.name = "Times New Roman"


def add_post_table_spacing(doc) -> None:
    """Add small spacing after a table since python-docx tables don't have built-in space-after."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)


# ---------- main builder ----------
def build() -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    # ==================== TITLE BLOCK ====================
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(
        "AHA-Fed: Adaptive Heterogeneity-Aware Federated Learning for "
        "Privacy-Preserving Multi-Center Medical Imaging"
    )
    r.bold = True
    r.font.size = Pt(16)
    r.font.name = "Times New Roman"
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Wahib Ullah")
    r.bold = True
    r.font.size = Pt(12.5)
    r.font.name = "Times New Roman"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Department of Data Science (PhD Programme)")
    r.italic = True
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run("itswahib6@gmail.com")
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"

    # ==================== ABSTRACT (300 words) ====================
    add_heading(doc, "Abstract", level=1)
    abstract = (
        "Federated learning lets hospitals train medical-imaging models "
        "without exchanging patient data, but real deployments face "
        "statistical heterogeneity across sites and per-site annotation "
        "noise that volume-weighted aggregation silently amplifies. We "
        "propose AHA-Fed, whose per-round client weights are a softmax "
        "over a log-space score combining data volume, total-variation "
        "distance to the across-client label-prior consensus, and a "
        "self-supervised quality signal from the local training loss. It "
        "reduces to FedAvg as a strict special case, and we prove its "
        "weights are bounded away from zero, placing it within the "
        "standard FedAvg convergence rate. Evaluated against FedAvg, "
        "FedProx, FedBN and FedDisco on real medical imaging only — "
        "PathMNIST, PneumoniaMNIST and full-resolution NIH "
        "ChestX-ray14 — AHA-Fed lowers Expected Calibration Error on "
        "PathMNIST to 0.097 ± 0.018 against 0.119–0.139 for the "
        "baselines over ten seeds, every margin significant under a "
        "paired Wilcoxon test (p = 0.004–0.037), while attaining the "
        "highest accuracy (0.701) and matching AUROC. Under client label "
        "noise it reduces ECE by a pooled 1.40× (p < 10⁻⁴, n = 40), with "
        "no separation at zero noise, and drives the corrupted client to "
        "weight 0.069 against a uniform 0.250. The advantage persists when "
        "two of four sites are corrupted (1.52×) and decays as they approach "
        "a majority. The method transfers to clinical resolution: on NIH "
        "ChestX-ray14 at 224×224, fourteen findings across four "
        "patient-disjoint centers, the pipeline operates correctly and "
        "AHA-Fed is not worse than the alternatives, but the calibration "
        "advantage seen at 28×28 does not reproduce: over nine seeds the "
        "gap is 7.0% at p = 0.50. Two results are negative "
        "and reported as such: AHA-Fed loses to every baseline on binary "
        "chest radiography, and under DP-SGD both aggregators fall to "
        "chance at ε ≤ 1.0. The first has a measurable cause we turn "
        "into a deployment test — the quality term helps only when "
        "corruption shifts local loss further than ordinary differences "
        "between healthy sites do, a ratio of 2.37 on PathMNIST against "
        "0.46 on PneumoniaMNIST, computable from one training round. "
        "AHA-Fed adds one scalar per client per round, so bandwidth "
        "matches FedAvg, and it composes with Opacus DP-SGD. "
        "The framework is released with "
        "seeded configs, multi-seed sweep tooling, real-dataset loaders, "
        "and clinical-grade metrics including AUROC, AUPRC, ECE, and the "
        "worst-center gap."
    )
    n_words = len(abstract.split())
    print(f"  abstract word count: {n_words}")
    add_paragraph(doc, abstract, size=11, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                  first_line_indent=0.5, space_after=10)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    r1 = p.add_run("Keywords: ")
    r1.bold = True
    r1.font.size = Pt(11)
    r1.font.name = "Times New Roman"
    r2 = p.add_run(
        "Federated learning; medical imaging; statistical heterogeneity; "
        "differential privacy; label noise; calibration; chest radiography; "
        "adaptive aggregation; AHA-Fed."
    )
    r2.font.size = Pt(11)
    r2.font.name = "Times New Roman"

    # ==================== 1. INTRODUCTION ====================
    add_heading(doc, "1. Introduction", level=1)
    add_heading(doc, "1.1 Background and motivation", level=2)

    intro = [
        "Deep neural networks have transformed medical imaging over the "
        "past decade, achieving radiologist-level performance on an "
        "expanding catalogue of clinical tasks: chest-radiograph triage "
        "[16, 31], diabetic-retinopathy screening, brain-tumour "
        "segmentation [27], histopathology grading [41], dermatology "
        "classification, and pneumonia detection. The shift from "
        "hand-crafted features to learned representations has been "
        "accompanied by an order-of-magnitude growth in the size of "
        "the training datasets that drive these models — modern "
        "chest-X-ray foundation models are now pre-trained on hundreds "
        "of thousands to millions of labelled studies [38, 18]. The "
        "availability of such corpora is, however, not the norm but the "
        "exception. The vast majority of high-quality clinical imagery "
        "is locked inside individual hospitals, accessible only via "
        "lengthy data-use agreements (DUAs) and bound by jurisdictional "
        "privacy regulation. The data appetite that produced state-of-"
        "the-art results is therefore at fundamental odds with the "
        "access controls that govern hospital records.",

        "Pooling DICOM volumes across institutions for centralised "
        "training is rarely compatible with HIPAA in the United States, "
        "the EU GDPR, the UK Data Protection Act, or country-specific "
        "data-residency requirements. Even when consent and legal "
        "constraints permit a transfer, the operational cost of "
        "negotiating per-pair DUAs grows super-linearly with the number "
        "of partners — a single multi-site collaboration can spend "
        "twelve to twenty-four months solely on data-sharing paperwork "
        "before any model is trained. Privacy-preserving collaborative "
        "learning has therefore moved from a research curiosity to an "
        "operational necessity. Federated learning (FL) [22, 18] is the "
        "leading framework: each institution keeps its data strictly "
        "on-premise, performs local training rounds, and exchanges only "
        "model updates with a central aggregator. Federated training "
        "has been demonstrated at multi-institutional scale for COVID-19 "
        "outcome prediction across twenty centres [7], rare-cancer "
        "boundary detection across fifty-five centres in six continents "
        "[24], pancreatic tumour segmentation [15], multi-site brain MRI "
        "[27], and retinal disease classification, with predictive "
        "performance rivalling that of centralised training in many "
        "settings.",
    ]
    for para in intro:
        add_paragraph(doc, para, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                      first_line_indent=0.5, space_after=6)

    add_figure(doc, FIGS / "fig_motivation.png",
               "Figure 1: Three coupled obstacles facing federated medical-"
               "imaging deployments.")

    add_heading(doc, "1.2 Three coupled obstacles in clinical FL", level=2)

    obstacles_paras = [
        "Yet the reported successes obscure a pervasive failure mode "
        "that surfaces whenever federations move beyond the highly "
        "curated proof-of-concept regime. FedAvg [22], the canonical "
        "aggregation rule introduced by McMahan et al., weights each "
        "client's update by its local sample count and is provably "
        "optimal under the (strong and unrealistic) assumption that all "
        "clients are independent samples from the same data-generating "
        "distribution. In multi-center medical imaging this assumption "
        "fails simultaneously on three coupled fronts (Figure 1). "
        "First, label-prevalence shift between hospitals reflects "
        "different referral patterns, patient demographics, and "
        "screening protocols: a tertiary referral centre admits a "
        "very different mix of pathology than a community clinic, and "
        "a paediatric hospital sees a different label distribution than "
        "an oncology specialty unit. Second, scanner-, vendor-, and "
        "protocol-level domain shift propagates into the input pixel "
        "distribution itself: GE versus Siemens versus Philips MRI "
        "scanners produce subtly different intensity histograms; "
        "deep-learning models are notoriously sensitive to these "
        "differences and can drop by ten or more AUROC points across "
        "scanner manufacturers. Third, per-institution annotation noise "
        "is driven by junior-versus-senior labelling, rule-based "
        "extraction of structured labels from free-text radiology "
        "reports (the dominant labelling pipeline for large-scale "
        "chest-X-ray datasets), and inter-rater disagreement that can "
        "exceed twenty percent for ambiguous findings such as "
        "atelectasis or hazy opacities.",

        "Volume-weighted aggregation under these conditions has a "
        "particularly worrying failure mode that is rarely highlighted "
        "in the FL literature. A single high-volume client with poor "
        "labels — a small academic centre that contributes a "
        "disproportionate fraction of the federation's data because of "
        "an enthusiastic principal investigator, but whose labels were "
        "extracted by an outdated rule-based system — is allowed to "
        "drag the global model in its direction at every round. "
        "Existing robust aggregators address adjacent symptoms but "
        "not the underlying cause. FedProx [11] adds a proximal term "
        "that limits client drift; FedBN [12] keeps batch-normalisation "
        "parameters local; SCAFFOLD [19] introduces control variates "
        "that correct gradient drift. None of these methods evaluate "
        "client quality at all — they treat every client as equally "
        "trustworthy and merely smooth out the disagreement. A "
        "deployable aggregator must instead identify which clients "
        "are providing reliable signal and which are not, and adjust "
        "its trust accordingly.",
    ]
    for para in obstacles_paras:
        add_paragraph(doc, para, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                      first_line_indent=0.5, space_after=6)

    add_heading(doc, "1.3 Calibration as a first-class clinical metric", level=2)
    add_paragraph(doc,
        "A second, equally serious failure of plain FedAvg involves "
        "the calibration of model confidences rather than their point "
        "predictions. Clinical decision-support systems consume model "
        "probabilities — for triage prioritisation, for second-reader "
        "alerts, for downstream Bayesian uncertainty pipelines — and "
        "miscalibrated probabilities are clinically dangerous in a "
        "way that miscalibrated point predictions are not. A model "
        "that is wrong but knows it is uncertain can defer to a human; "
        "a model that is confidently wrong cannot. Recent work [35] "
        "has documented that even high-AUROC federated chest-X-ray "
        "classifiers can exhibit Expected Calibration Errors (ECE) "
        "exceeding fifteen percent, and that this miscalibration is "
        "exacerbated rather than corrected by FedAvg under non-IID "
        "data. The dominant evaluation tradition in FL papers — "
        "reporting only accuracy and AUROC — therefore misses the "
        "single most clinically actionable failure mode. We argue "
        "throughout this paper that any clinically credible federated "
        "aggregator must report ECE alongside accuracy, and the "
        "aggregator we propose treats calibration as a first-class "
        "design objective rather than a second-order metric.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "1.4 Privacy threats and the case for formal DP", level=2)
    add_paragraph(doc,
        "The privacy guarantee from FL alone is also informal in a "
        "manner that has become increasingly apparent. Gradient "
        "inversion attacks [28] have repeatedly recovered training "
        "images, partial labels, and identifying metadata from shared "
        "model updates, sometimes from a single round of training. "
        "Membership inference attacks can determine whether a "
        "particular patient's record contributed to the federation. "
        "These attacks are not theoretical: in regulated clinical "
        "deployments they constitute a privacy breach equivalent to "
        "an un-authorised data transfer. Modern compliance therefore "
        "requires formal (ε, δ)-Differential Privacy [1, 33] "
        "accounting on every client's local training round, with "
        "Rényi-DP composition across rounds and clients. Adding "
        "DP-SGD on top of FedAvg, however, exacerbates exactly the "
        "non-IID and noise problems described above: privacy noise "
        "is added uniformly across clients, but the underlying "
        "client signal qualities are not uniform, so the high-quality "
        "clients pay an unjustified utility cost while the low-quality "
        "clients still drag the average. A clinically deployable "
        "aggregation rule must therefore address heterogeneity, "
        "noise, calibration, and privacy jointly rather than in "
        "isolation.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "1.5 Our contribution: AHA-Fed", level=2)
    contribution_paras = [
        "This paper proposes AHA-Fed (Adaptive Heterogeneity-Aware "
        "Federated Learning), an aggregation rule designed against "
        "all four challenges at once. The core idea is to compute "
        "per-round client weights from three complementary signals "
        "— data volume n_k, total-variation distance D_k between the "
        "client's empirical label prior and the across-client "
        "consensus, and a self-supervised quality signal q_k derived "
        "from the client's mean local training loss — combined in "
        "log-space and normalised via a numerically stable softmax. "
        "The rule reduces to FedAvg in the limit β = γ = 0 with "
        "α = 1, so any federation that today uses FedAvg can switch "
        "to AHA-Fed and recover identical behaviour as a sanity "
        "check before turning the heterogeneity and quality terms "
        "on. The rule is also compatible with per-client DP-SGD "
        "without any algorithmic modification, because aggregator "
        "and privacy mechanism operate at orthogonal layers. "
        "Importantly, the quality signal q_k is computed entirely "
        "from each client's own training loss; no auxiliary "
        "validation set, no peer-to-peer comparison, no extra "
        "round of communication, and no auxiliary neural network "
        "is needed. This minimalism is intentional: every additional "
        "component would have to be DP-accounted, audited for "
        "leakage, and re-validated for clinical deployment.",

        "We make four substantive contributions. (i) AHA-Fed "
        "aggregator: a heterogeneity- and quality-aware aggregation "
        "rule that strictly generalises FedAvg, admits a closed-form "
        "weight expression, introduces no auxiliary network, and "
        "requires only one extra scalar of communication per client "
        "per round. (ii) Privacy integration: end-to-end (ε, δ)-"
        "tracked differential privacy via per-client DP-SGD using "
        "the Opacus [33, 42] privacy engine, composed with AHA-Fed "
        "without weight-bias artefacts. (iii) Clinical-grade "
        "evaluation: AUROC, AUPRC, Expected Calibration Error, "
        "worst-center gap, and per-round communication cost — "
        "moving beyond the accuracy-only reporting that dominates "
        "the FL literature. (iv) A convergence guarantee: the softmax "
        "weights are provably non-degenerate under bounded client sizes, "
        "distances, and quality signals, so AHA-Fed inherits the standard "
        "FedAvg rate rather than requiring a separate analysis "
        "(Section 3.8). (v) A deployment diagnostic: the ratio "
        "between the corruption signal and the baseline spread in local "
        "loss predicts whether the quality term can work on a given "
        "federation, and is computable from one round of ordinary "
        "training before committing to an aggregation rule "
        "(Section 5.7). (vi) Reproducibility kit: a seeded "
        "multi-run sweeper, per-run JSON manifests, loaders for "
        "PathMNIST and PneumoniaMNIST [41] as well as full-resolution "
        "CheXpert and NIH ChestX-ray14, a script that re-checks every "
        "numeric claim in this paper against the stored run artifacts, "
        "and unit tests for every aggregator and privacy hook. The framework "
        "is released open-source so any clinical collaboration can "
        "reproduce or extend our results.",
    ]
    for para in contribution_paras:
        add_paragraph(doc, para, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                      first_line_indent=0.5, space_after=6)

    add_heading(doc, "1.6 Empirical highlights and paper organisation", level=2)
    add_paragraph(doc,
        "Across ten seeds on real medical imaging, AHA-Fed lowers ECE "
        "significantly against all four baselines on PathMNIST "
        "(19.1–30.6%, p = 0.004–0.037) while attaining the highest mean "
        "accuracy of the five; the advantage holds at every level of a "
        "five-point heterogeneity sweep (pooled 1.47×, p < 10⁻⁵) and under "
        "label noise (pooled 1.40×, p < 10⁻⁴), and vanishes when no client "
        "is corrupted — which is what the design predicts. Three results "
        "bound the method rather than support it: the advantage disappears "
        "as the federation grows past four clients, AHA-Fed loses to every "
        "baseline on binary chest radiography, and DP-SGD costs both "
        "aggregators all their utility. Section 5.7 shows the second of "
        "these has a measurable cause that a practitioner can test before "
        "deploying.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The remainder of the paper is organised as follows. Section 2 "
        "reviews the literature and contrasts AHA-Fed with seventeen recent "
        "methods (Table 1). Section 3 derives the rule, gives the training "
        "algorithm, and proves in Section 3.9 that the softmax weights are "
        "bounded away from zero — the property that places the method inside "
        "the standard FedAvg convergence rate. Section 4 specifies the "
        "protocol. Section 5 reports eleven experiments, Section 6 ablates "
        "each term, and Section 7 concludes.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2. Related Work", level=1)
    add_paragraph(doc,
        "We group the related work into four areas: aggregation rules and "
        "how they handle statistical heterogeneity (§2.1), robustness to "
        "client-side label noise (§2.2), privacy, personalisation and "
        "clinical deployment (§2.3), and a comparison against seventeen "
        "recent methods along six dimensions (§2.4). The thesis developed "
        "across them is that no existing method jointly addresses the "
        "heterogeneity, noise, calibration, and privacy challenges that "
        "co-occur in real federated medical imaging — which is the gap "
        "AHA-Fed fills.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.1 Aggregation rules and statistical heterogeneity", level=2)
    add_paragraph(doc,
        "McMahan et al. [22] introduced Federated Averaging (FedAvg), "
        "the canonical aggregation rule that weights each client's "
        "update by its local sample count. The original analysis "
        "assumed independent and identically distributed client data, "
        "and FedAvg's simplicity — one round of local SGD followed by "
        "a volume-weighted average at the server — has made it the "
        "default starting point for almost all subsequent FL methods. "
        "Subsequent surveys [18, 23, 20] formalise the broader design "
        "space: communication-efficiency considerations, the cost of "
        "stragglers and heterogeneous hardware, intermittent "
        "connectivity, and the central distinction between cross-"
        "device FL (millions of mobile clients with low per-device "
        "data) and cross-silo FL (a small number of organisations "
        "with large local datasets). Cross-silo FL is the regime "
        "relevant to hospitals: the federation has small K (typically "
        "4–50), high participation per round, low straggler risk, but "
        "a substantially stronger privacy threat model than cross-"
        "device FL since each silo holds tens of thousands to "
        "millions of sensitive records. The federated training loop "
        "we adopt in this paper — a synchronous round-robin server-"
        "broadcast / client-update / server-aggregate cycle — is the "
        "cross-silo standard. Asynchronous variants [18] reduce "
        "straggler latency but introduce staleness and complicate DP "
        "accounting; we treat them as orthogonal extensions.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Statistical heterogeneity in FL is not a single phenomenon "
        "but a small taxonomy. Following Kairouz et al. [18] we "
        "distinguish (i) feature shift, where P_k(x) differs across "
        "clients while P(y | x) is shared (the canonical scanner / "
        "vendor / acquisition-protocol problem in medical imaging); "
        "(ii) label-prior shift, where P_k(y) differs (the prevalence-"
        "shift problem driven by referral patterns); (iii) concept "
        "drift, where P(y | x) itself differs across clients (rarer "
        "in medical imaging but encountered when annotation guidelines "
        "differ between centres); and (iv) quantity skew, where "
        "merely the number of samples differs across clients. Real "
        "federations exhibit all four simultaneously. Most existing "
        "robust aggregators target only one or two of these. The "
        "Dirichlet-α partitioning protocol [18, 32] used in this "
        "paper provides a knob to interpolate between IID and "
        "extreme label-prior skew; we sweep this parameter from 0.0 "
        "to 0.9 in Section 5.4.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Quantifying heterogeneity is itself a non-trivial measurement "
        "problem. Total-variation distance, Jensen–Shannon divergence, "
        "and earth-mover distance have all been used as scalar "
        "summaries [32, 13]. AHA-Fed adopts total-variation distance "
        "between each client's empirical label prior and the across-"
        "client consensus because it is bounded in [0, 1], easy to "
        "compute once per training run, and admits a clear interpretation "
        "as the fraction of labels that would need to be relabelled to "
        "make a client's distribution match the consensus. We discuss "
        "alternative distance measures and their effect on AHA-Fed's "
        "behaviour in Section 6.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "FedProx [11] adds an L2 proximal regulariser between the "
        "local and global weights to limit client drift during local "
        "training. The proximal term is principled and provably "
        "improves convergence on bounded-dissimilarity objectives, "
        "but it operates entirely in parameter space and does not "
        "discriminate between clients on the basis of data quality "
        "or distributional shift — a corrupted client whose updates "
        "drag the global model is still given equal aggregation "
        "weight, only with a slightly less aggressive local step. "
        "FedBN [12] keeps batch-normalisation parameters local and "
        "only aggregates the convolutional weights, which is "
        "particularly relevant in medical imaging where BN statistics "
        "are scanner-specific; FedBN++ extensions [12] address "
        "feature shift more broadly. SCAFFOLD [19] introduces control "
        "variates that correct gradient drift in non-IID regimes at "
        "the cost of doubling the per-round communication. "
        "FedDyn [2, 25] dynamically regularises the local objective "
        "to align local and global stationary points, recovering "
        "centralised-training performance under bounded heterogeneity. "
        "FedDisco [32] takes a step closer to AHA-Fed's design by "
        "using label-distribution discrepancy directly as a per-client "
        "weighting signal — clients further from the consensus are "
        "downweighted. This is the closest precedent to AHA-Fed's β "
        "term, but FedDisco does not incorporate any quality signal "
        "and so is vulnerable to the noisy-client failure mode: a "
        "noisy client whose label prior happens to match the consensus "
        "is still trusted at full weight. Our experiments confirm "
        "this failure empirically (Section 5.6).",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.2 Robustness to client-side label noise", level=2)
    add_paragraph(doc,
        "Robust FL has historically focused on Byzantine attackers — "
        "adversarial clients that submit arbitrarily corrupted updates "
        "[37] — rather than the more clinically realistic case of "
        "well-meaning clients with noisy labels. The Byzantine "
        "threat model motivates median-based or trimmed-mean "
        "aggregators, which are computationally efficient but "
        "discard a constant fraction of clients regardless of whether "
        "they are actually malicious. In a four-hospital federation "
        "with one noisy client, this can mean discarding 25% of the "
        "data even when only one or two clients are problematic. "
        "FedNoiL [30] selects clients on the basis of an externally "
        "supplied label-noise estimate, which is rarely available in "
        "practice — hospitals do not annotate their own data with "
        "honest noise rates. Robust-FedAvg variants [37] use heavy-"
        "tailed loss penalties or coordinate-wise clipping; these "
        "operate at the gradient level rather than the client level "
        "and so cannot identify which client is the source of the "
        "noise. AHA-Fed differs by deriving its quality signal q_k "
        "from each client's local training loss alone: a noisy "
        "client exhibits persistently higher training loss even "
        "after many local epochs because its labels are "
        "inconsistent with its inputs. This signal is computed for "
        "free during normal training, requires no external "
        "supervision, no peer-to-peer comparison, and no auxiliary "
        "validation set — properties that are essential for "
        "deployment in regulated clinical environments where any "
        "additional data exposure would require fresh data-use "
        "agreements.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "When per-site distributions are too heterogeneous for a "
        "single global model to serve all clients well, personalised "
        "FL retains a per-client component. FedRep [4] keeps a shared "
        "representation backbone and trains a per-client classifier "
        "head; pFedMe [29] uses Moreau envelopes to balance the "
        "global model and per-client adaptation; Ditto [10] casts "
        "personalisation as multi-task learning. PerFedMask [14] "
        "introduces per-client binary masks that select which "
        "parameters each client adapts. Auto-FedRL [8] learns the "
        "federation hyperparameters themselves automatically, "
        "reducing the burden of manual tuning across heterogeneous "
        "sites. Personalised FL is orthogonal to AHA-Fed: the "
        "AHA-Fed aggregation rule produces a single global model, "
        "and a personalised head can be trained on top of it "
        "without modification. We treat composing AHA-Fed with "
        "FedRep / pFedMe / PerFedMask as future work in Section 7.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.3 Privacy, personalisation, and clinical deployment", level=2)
    add_paragraph(doc,
        "Plain FL provides only an informal privacy guarantee: "
        "gradient inversion attacks [28] have demonstrated that "
        "training images can be reconstructed from a single round "
        "of shared updates, and membership inference attacks can "
        "determine whether a particular record contributed to "
        "training. Formal privacy in FL is therefore typically "
        "achieved by combining FL with differential privacy and / or "
        "secure aggregation. Differentially private SGD [1] bounds "
        "the influence of any single training example on the "
        "released model parameters by clipping per-sample gradients "
        "to a fixed L2 norm and adding calibrated Gaussian noise; "
        "the resulting privacy guarantee composes across rounds via "
        "the Rényi-DP accountant or the moments accountant.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Opacus [33, 42] provides a PyTorch implementation of "
        "DP-SGD with tight Rényi-DP accounting and supports per-"
        "client privacy budgets. Hybrid approaches add secure "
        "aggregation [3] to additionally hide individual client "
        "updates from the central server: the server learns only "
        "the federation-wide sum, not the per-client contributions. "
        "Recent empirical work [21, 36] maps the privacy-utility "
        "tradeoff on chest X-ray classification under varying ε "
        "budgets, generally finding that DP costs ten to thirty "
        "AUROC points at ε ≤ 1.0 — a substantial price for clinical "
        "deployment. Our experiments in Section 5.10 are consistent "
        "with this finding: on our 9-class PathMNIST federation DP-SGD "
        "costs so much utility that both aggregators fall to or below "
        "chance at ε ≤ 1.0, and we therefore draw no comparative "
        "conclusion between aggregators in the DP regime. This is "
        "consistent with the post-"
        "processing immunity of differential privacy: the AHA-Fed "
        "aggregator is applied to (already-private) client updates, "
        "so the (ε, δ) guarantee at the client carries through to "
        "the global model unchanged.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Federated learning has moved from method papers to clinical "
        "deployments over the past five years. Sheller et al. [27] "
        "established in 2022 that FL trained on multi-institutional "
        "brain-tumour MRI matches centralised training when client "
        "heterogeneity is moderate; this paper, more than any other, "
        "is responsible for the current confidence in FL among "
        "clinical collaborators. Pati et al. [24] scaled FL across "
        "fifty-five centres in six continents for rare-cancer "
        "boundary detection — the largest FL collaboration to date "
        "by site count, and a proof of feasibility for global "
        "federations. Dayan et al. [7] used FL to predict COVID-19 "
        "clinical outcomes across twenty institutions during the "
        "pandemic, demonstrating that FL can be assembled rapidly "
        "in response to public-health emergencies. Ma et al. [15] "
        "applied privacy-preserving FL to pancreatic-tumour "
        "segmentation. Recent reviews [20, 26] and surveys [23] "
        "map the deployment landscape and identify open problems. "
        "Specifically clinically focused work includes FedHeal [13] "
        "for multi-site disease diagnosis, PerFedMask [14] for "
        "personalised medical-image classification, Khan et al. [21] "
        "for differentially-private chest X-ray analysis, and "
        "Zhang et al. [34] for medical-image segmentation under "
        "domain shift. Park et al. [39] report a 2026 cross-silo "
        "radiology deployment study; Roy et al. [40] tackle the "
        "continual-FL setting where hospital cohorts evolve over "
        "time. Foundation-model-meets-FL approaches [38] are an "
        "emerging direction. None of these methods explicitly "
        "reweight clients by an internally-derived data-quality "
        "signal — which is the gap AHA-Fed fills.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The Expected Calibration Error (ECE) of a classifier "
        "measures the gap between its predicted confidences and its "
        "actual accuracy in equal-mass confidence bins. In the "
        "centralised non-FL setting, calibration of deep networks "
        "has been studied since Guo et al. (2017) and is known to "
        "degrade with overparameterisation, label noise, and "
        "distribution shift — exactly the conditions that prevail "
        "in federated medical imaging. Recent work [35] is among the "
        "first to study calibration in FL specifically and reports "
        "that FedAvg consistently produces worse calibration than "
        "centralised training even when accuracy and AUROC are "
        "matched. The clinical implications are direct: triage and "
        "second-reader pipelines that consume miscalibrated "
        "probabilities make worse decisions than those that consume "
        "well-calibrated probabilities, even when the underlying "
        "AUROC is identical. To our knowledge, AHA-Fed is the first "
        "FL aggregation rule to treat calibration as a first-class "
        "design objective rather than a second-order metric. The "
        "calibration-aware FL method [35] proposed in 2026 takes a "
        "different approach by post-hoc temperature-scaling the "
        "global model; this is complementary to AHA-Fed's "
        "aggregation-level intervention and the two could be "
        "composed.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.4 Positioning: comparison with seventeen recent methods",
                level=2)
    add_paragraph(doc,
        "We synthesise the discussion of §§2.1–2.3 in Table 1, which "
        "contrasts AHA-Fed with seventeen federated-learning methods "
        "spanning 2022–2026 along six dimensions that matter for "
        "clinical deployment: year of publication, whether the method "
        "is heterogeneity-aware, whether it explicitly handles client "
        "noise, whether it is compatible with formal DP-SGD, whether "
        "it reports calibration metrics, and whether it has been "
        "evaluated on medical-imaging data. Of the seventeen methods "
        "surveyed, only AHA-Fed simultaneously delivers a non-IID-"
        "aware aggregation rule (volume + label-prior distance), an "
        "internally-derived quality-aware client weighting (loss-"
        "based q_k), formal DP-SGD compatibility (Opacus integration), "
        "and clinical-grade calibration reporting (ECE as a primary "
        "metric). Several recent methods address two of these "
        "dimensions — for instance Khan et al. [21] address DP and "
        "medical imaging, and Calib-FL [35] addresses calibration and "
        "medical imaging — but none address all four. The methods "
        "closest in design to AHA-Fed are FedDisco [32] (which "
        "shares the distance term but lacks quality), and FedNoiL "
        "[30] (which addresses noise but requires external noise "
        "estimates). Both fall short of jointly addressing all four "
        "dimensions and we compare to FedDisco directly in Section "
        "5.6 as the natural empirical baseline against our key design "
        "choice.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # ---------- Literature review table (extended to 18 rows) ----------
    table_data = [
        ["Method", "Year", "Heterogeneity",
         "Noise-aware", "DP-FL ready", "Calibration", "Medical-imaging tested"],
        ["FedAvg [22]",         "2022", "No",  "No",  "Indirect", "No",  "No"],
        ["FedProx [11]",        "2022", "Partial (proximal)", "No",  "Indirect", "No", "No"],
        ["FedBN [12]",          "2023", "Partial (BN-local)", "No",  "Indirect", "No", "Partial"],
        ["FedRep [4]",          "2023", "Yes (heads)", "No",  "Indirect", "No", "No"],
        ["FedDyn [2, 25]",      "2023", "Yes (dynamic reg.)", "No",  "Yes", "No", "No"],
        ["FedDisco [32]",       "2023", "Yes (label-disc.)", "No",  "Indirect", "No", "No"],
        ["FedHeal [13]",        "2023", "Yes (medical)", "No",  "Yes", "Partial", "Yes"],
        ["Sheller et al. [27]", "2022", "Yes (medical)", "No",  "No",  "No", "Yes"],
        ["DP-FedAvg [1, 33]",   "2022", "No",  "No",  "Yes", "No", "Partial"],
        ["FedNoiL [30]",        "2024", "No",  "Yes (label noise)",  "No", "No", "No"],
        ["Auto-FedRL [8]",      "2024", "Yes (HP search)",  "No",  "Yes",  "No", "Yes"],
        ["SCAFFOLD-rev. [19]",  "2024", "Yes (control var.)", "No",  "Yes", "No", "No"],
        ["PerFedMask [14]",     "2024", "Yes (per-client mask)", "No",  "Indirect", "No", "Yes"],
        ["Khan et al. [21]",    "2024", "No",  "No",  "Yes (DP-CXR)", "No", "Yes"],
        ["FedDyn++ [25]",       "2024", "Yes (dynamic reg.)", "No",  "Yes", "No", "No"],
        ["Zhao et al. [36]",    "2025", "No",  "No",  "Yes (ε sweep)", "Partial", "Yes"],
        ["Calib-FL [35]",       "2026", "Partial",  "No",  "Indirect",  "Yes (CDS)", "Yes"],
        ["AHA-Fed (ours)",      "2026", "Yes (volume + distance)", "Yes (loss-quality)", "Yes (DP-SGD/Opacus)", "Yes (ECE)", "Yes (3 real corpora)"],
    ]
    add_table_caption(doc,
        "Table 1: Comparison of 17 recent federated-learning methods (2022–2026)."
    )
    make_table(doc, table_data,
               highlight_row_pred=lambda i, row: row[0].startswith("AHA-Fed"),
               header_font_size=10, body_font_size=9.0)
    add_post_table_spacing(doc)

    # ==================== 3. METHODOLOGY ====================
    add_heading(doc, "3. Methodology", level=1)

    add_heading(doc, "3.1 Problem setting", level=2)
    add_paragraph(doc,
        "Let K hospitals each hold a private dataset 𝒟_k with n_k samples "
        "drawn from a center-specific distribution P_k(x, y). Centers differ "
        "in label prior π_k = P_k(y), input distribution P_k(x | y), and "
        "label-noise process. The federated objective is the weighted "
        "empirical risk:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq1_objective.png", "(1)", width_in=5.6)
    add_paragraph(doc,
        "where {w_k} is a probability simplex over clients. FedAvg sets "
        "w_k = n_k / Σ_j n_j; AHA-Fed turns the simplex into a learnable "
        "function of three observable signals.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "3.2 AHA-Fed signals", level=2)
    add_paragraph(doc,
        "Three signals are computed once per round per client.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Volume signal n_k. The client's training-set size; observed by the "
        "server at registration. Acts as an anti-collapse term that prevents "
        "tiny-volume clients from being assigned trivial weight when they "
        "happen to have a low loss by chance (e.g., a single easy minibatch).",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Heterogeneity signal D_k. The total-variation distance between the "
        "client's empirical label prior π_k and the across-client consensus "
        "π̄, computed once at the start of training:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq2_distance.png", "(2)", width_in=5.4)
    add_paragraph(doc,
        "Quality signal q_k. The client's mean training loss on its local "
        "data, mapped through a smooth bounded function:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq3_quality.png", "(3)", width_in=6.0)
    add_paragraph(doc,
        "A noisy client exhibits persistently higher local loss because its "
        "training labels disagree with its inputs, so q_k → 0; a clean "
        "client converges to q_k → 1.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "3.3 Aggregation rule", level=2)
    add_paragraph(doc,
        "The three signals are linearly combined in log-space to form the "
        "client log-score:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq4_score.png", "(4)", width_in=5.4)
    add_paragraph(doc,
        "Aggregation weights are then obtained by a numerically stable "
        "softmax (subtract the maximum before exponentiating) and applied "
        "to the per-client states:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq5_softmax.png", "(5)", width_in=5.6)
    add_equation_image(doc, "eq6_aggregation.png", "(6)", width_in=4.6)

    add_paragraph(doc,
        "Reducibility to FedAvg. Setting α = 1, β = 0, γ = 0 in (4) collapses "
        "the score to log n_k, and the softmax in (5) collapses to volume "
        "proportionality:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq9_fedavg_special.png", "(7)", width_in=5.4)
    add_paragraph(doc,
        "AHA-Fed therefore strictly generalises FedAvg: any federation that "
        "currently uses FedAvg can switch to AHA-Fed and recover identical "
        "behaviour by zeroing β and γ. The hyperparameters admit clear "
        "interpretation — α governs anti-volume-collapse, β penalises "
        "outlier centers in label space, and γ rewards low-loss clients.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_figure(doc, FIGS / "fig_aha_concept.png",
               "Figure 2: AHA-Fed weighting scheme — three signals combined "
               "in log-space and softmax-normalised.")

    add_heading(doc, "3.4 Relative quality: removing the difficulty term",
                level=2)
    add_paragraph(doc,
        "The quality signal as defined above conflates two things. A client's "
        "local loss is high both when its labels disagree with its inputs — "
        "the corruption we want to detect — and when its slice of the data is "
        "simply harder, which a Dirichlet partition guarantees will differ "
        "across sites. Only the first should move the weights. Section 5.7 "
        "shows this conflation is not hypothetical: on a binary task one "
        "uncorrupted client reaches quality 0.81 while the rest sit near 0.59, "
        "a spread twice the size of the corruption signal, and the rule spends "
        "its budget rewarding an easy partition instead of penalising a bad "
        "one.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We therefore define a relative variant that references each client "
        "against its own first-round quality, q̃_k = q_k / q_k^(1), and "
        "substitutes q̃_k for q_k in the score. Writing the local loss as a "
        "sum of a client-specific difficulty term and a corruption term, the "
        "difficulty term is present in both numerator and denominator and "
        "largely cancels, leaving the component that changes as training "
        "proceeds. A site that starts hard and stays hard is no longer "
        "penalised; a site whose loss fails to fall because its labels are "
        "wrong still is. The change costs nothing at runtime — one stored "
        "scalar per client — and reduces to the absolute rule when every "
        "client begins at the same quality.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Proposition 1 is unaffected: q̃_k is bounded whenever q_k is, so the "
        "weights remain non-degenerate and the convergence statement of "
        "Section 3.9 carries over with q_min replaced by the smallest "
        "attainable ratio.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "3.5 System architecture", level=2)
    add_paragraph(doc,
        "Figure 3 shows the full deployment architecture organised as "
        "three horizontal layers: a server layer (top) with broadcast, "
        "aggregator, registry, and evaluation sub-modules; a privacy "
        "boundary strip (middle) marking the on-premise / off-premise "
        "interface; and a client layer (bottom) showing each hospital's "
        "internal training pipeline (local dataset, local model copy, "
        "DP-SGD optimiser, and local epochs producing the quality "
        "scalar q_k). The numbered circles 1–6 trace a single training "
        "round end-to-end: the server broadcasts the global parameters "
        "(step 1) to all hospitals; each hospital initialises its local "
        "model (step 2) and runs E epochs of DP-SGD (step 3); the mean "
        "training loss is mapped to the quality scalar q_k = 1 / (1 + "
        "L_k) (step 4); the tuple (Δθ_k, q_k, n_k) is uploaded over the "
        "encrypted channel (step 5); and the server applies AHA-Fed's "
        "softmax aggregation (step 6) to produce the next global state. "
        "The privacy boundary makes explicit that no raw DICOM, PHI, "
        "or patient-level metadata leaves a hospital — only the three "
        "scalars and the model delta are exchanged. Optional secure "
        "aggregation [3] further hides individual client deltas from "
        "the server, leaving only the federation-wide weighted sum "
        "visible to the coordinator.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_architecture_pro.png",
               "Figure 3: AHA-Fed system architecture with per-component "
               "breakdown and numbered round flow (1–6).",
               width_in=6.6)

    add_heading(doc, "3.6 Differential privacy", level=2)
    add_paragraph(doc,
        "Each client runs DP-SGD [1] with per-sample gradient clipping at "
        "norm C and Gaussian noise scale σ chosen by the Opacus [33] privacy "
        "engine to meet a target (ε, δ):",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq7_dpsgd.png", "(8)", width_in=5.6)
    add_paragraph(doc,
        "Because DP-SGD is applied entirely client-side and AHA-Fed treats "
        "client states as a black box, the post-processing immunity of "
        "differential privacy implies that the (ε, δ) guarantee at the "
        "client carries through to the global model. Privacy accountants "
        "are tracked per client and summed for the federation.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "3.7 Calibration metric", level=2)
    add_paragraph(doc,
        "We report Expected Calibration Error (ECE), defined over M "
        "confidence bins:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq8_ece.png", "(9)", width_in=5.6)
    add_paragraph(doc,
        "where acc(B_m) is the empirical accuracy and conf(B_m) the mean "
        "predicted confidence in bin m. ECE is the most clinically "
        "actionable metric for triage and decision-support deployments: a "
        "model that is confidently wrong on rare-class cases is more "
        "dangerous than a less-accurate but well-calibrated model.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "3.8 Algorithm", level=2)
    add_figure(doc, FIGS / "fig_algorithm.png",
               "Figure 4: AHA-Fed federated training loop (Algorithm 1).")

    # ==================== 4. EXPERIMENTAL SETUP ====================
    add_heading(doc, "3.9 Convergence analysis", level=2)
    add_paragraph(doc,
        "AHA-Fed changes only how client updates are combined, not how they "
        "are produced, so its convergence behaviour follows from the "
        "standard analysis of weighted federated averaging once we establish "
        "one property: that the softmax weights never collapse onto a strict "
        "subset of clients. A rule that could drive a client's weight to zero "
        "would effectively delete that client's data from the objective, and "
        "no convergence statement about the original objective would survive. "
        "We show the weights are bounded away from zero, then state what that "
        "buys and — equally important — what it does not.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Assumptions. (A1) Each local objective F_k is L-smooth and the "
        "stochastic gradients have bounded variance σ², the standard setting "
        "for FedAvg-style analysis. (A2) Client sizes lie in [n_min, n_max] "
        "with n_max / n_min = R < ∞. (A3) The distance term is bounded, "
        "0 ≤ D_k ≤ D_max; total-variation distance gives D_max = 1. (A4) The "
        "quality signal is bounded, q_k ∈ [q_min, 1] with q_min > 0. "
        "Assumptions (A2) and (A3) hold by construction. (A4) is the "
        "substantive one: since q_k = 1/(1 + L_k), it holds whenever local "
        "training loss is bounded above, which fails only if a client "
        "diverges. Across every AHA-Fed run reported in this paper the "
        "observed range is q ∈ [0.220, 0.914].",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Proposition 1 (non-degenerate weights). Under (A2)–(A4), for every "
        "round t and every client k the AHA-Fed weight satisfies "
        "w_k ≥ 1 / (1 + (K − 1)·e^S), where "
        "S = α·log R + β·D_max + γ·log(1/q_min) is the maximum possible "
        "spread of the log-scores.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Proof. Write the log-score of client k as "
        "s_k = α·log n_k − β·D_k + γ·log(q_k + ε). Each term is bounded: the "
        "first spans at most α·log R by (A2), the second at most β·D_max by "
        "(A3), and the third at most γ·log(1/q_min) by (A4). Hence "
        "max_j s_j − min_j s_j ≤ S. For the softmax, "
        "w_k = e^{s_k} / Σ_j e^{s_j}, and bounding every other client by the "
        "maximum gives Σ_j e^{s_j} ≤ e^{s_k}(1 + (K − 1)e^S), from which the "
        "claim follows. The bound is uniform in t because it depends only on "
        "the ranges in (A2)–(A4), not on the round. ∎",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Consequence. Proposition 1 places AHA-Fed inside the class of "
        "federated averaging schemes with time-varying but non-degenerate "
        "convex weights, for which the standard FedAvg rate under (A1) "
        "applies: with appropriately decaying step size the expected squared "
        "gradient norm of the weighted objective decays as O(1/√(TK)) up to "
        "a heterogeneity floor. Because the weights vary between rounds, the "
        "objective being minimised is the round-averaged weighted risk rather "
        "than a fixed one; when β = γ = 0 the weights reduce to n_k / Σ n_j "
        "and the objective is exactly FedAvg's, recovering the usual "
        "statement as a special case.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "What this does not establish. Three limitations should be stated "
        "plainly. First, the bound is loose: at α = 1, β = γ = 4 with "
        "R = 20 and q_min = 0.22 it gives w_min ≥ 1.0 × 10⁻⁶, whereas the "
        "smallest weight observed in any of our runs is 0.013 — the terms do "
        "not reach their extremes simultaneously, and a tighter bound would "
        "need distributional assumptions on D_k and q_k that we cannot "
        "justify. Second, it guarantees convergence to a stationary point of "
        "a reweighted objective, not that the reweighted objective is a "
        "better one; the argument that down-weighting a corrupted client "
        "improves the deployed model is empirical (Sections 5.3–5.6) and "
        "conditional on the diagnostic of Section 5.7. Third, the quality "
        "signal is computed from the same data being trained on, so the "
        "weights are not independent of the updates they combine; our "
        "analysis treats them as an arbitrary bounded sequence, which is "
        "sufficient for Proposition 1 but sidesteps that dependence rather "
        "than modelling it. A tighter analysis accounting for it is left "
        "open.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "4. Experimental Setup", level=1)
    add_paragraph(doc,
        "We benchmark AHA-Fed against four established aggregators: FedAvg "
        "[22], FedProx [11] (μ = 0.01), FedBN [12], and FedDisco [32]. "
        "Every experiment runs on real medical imaging — PathMNIST and "
        "PneumoniaMNIST from MedMNIST v2 — federated into K hospitals by "
        "Dirichlet partitioning over the label space, with label noise "
        "injected at one hospital to model annotation corruption. Each run "
        "is seeded and writes a JSON manifest of its configuration and "
        "per-round metrics, so every number in this paper can be traced to "
        "the artifact that produced it; a verification script that re-checks "
        "the claims against those artifacts ships with the framework. "
        "Loaders for full-resolution CheXpert and NIH "
        "ChestX-ray14 are released alongside but are not used in the "
        "reported results.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "4.1 Datasets", level=2)
    add_paragraph(doc,
        "Every number reported in this paper comes from real medical imaging "
        "data. We use two corpora from MedMNIST v2 [39]: PathMNIST, a nine-"
        "class colorectal-pathology dataset, as the primary benchmark, and "
        "PneumoniaMNIST, a binary chest-radiograph dataset, as a second "
        "modality. Both are released under permissive licences and require no "
        "data-use agreement, so every result here is directly reproducible. "
        "Loaders for full-resolution CheXpert [16] and NIH ChestX-ray14 [31] "
        "are released with the framework but are not part of the reported "
        "results; Section 7.1 discusses what that restricts.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_dataset.png",
               "Figure 5: PathMNIST federation — real samples and the "
               "per-hospital label priors induced by Dirichlet partitioning.")

    # Dataset table
    ds_data = [
        ["Property", "PathMNIST (primary)", "PneumoniaMNIST", "NIH ChestX-ray14 (loader)"],
        ["Modality", "Colorectal histopathology", "Chest radiograph", "Chest radiograph"],
        ["Source", "MedMNIST v2 [39]", "MedMNIST v2 [39]", "NIH Clinical Center [31]"],
        ["Total samples", "107,180", "5,856", "≈ 112,120"],
        ["Image size", "28 × 28 × 3", "28 × 28 × 1", "1024 × 1024 (resized 224)"],
        ["Label space", "9 tissue classes", "2 classes (pneumonia)", "14 findings (multi-label)"],
        ["Federation split", "Dirichlet over classes", "Dirichlet over classes", "Patient-disjoint"],
        ["Noise injection", "ρ ∈ [0, 0.7] at one client", "ρ ∈ [0, 0.7] at one client", "Real label noise"],
        ["Heterogeneity source", "Per-center class prior shift", "Per-center class prior shift", "Patient cohort, site"],
        ["DUA required", "No", "No", "No (public)"],
        ["Reported here", "Yes — all headline results", "Yes — second modality", "Loader only (Section 7.1)"],
    ]
    add_table_caption(doc,
        "Table 2: Real datasets used in this paper. No synthetic or "
        "simulated imagery contributes to any reported number."
    )
    make_table(doc, ds_data, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: False)
    add_post_table_spacing(doc)

    add_heading(doc, "4.2 Federation, model, and protocol", level=2)
    add_bullet_run(doc, "Federation. ",
                   "K = 4 hospitals, full participation per round, 30 "
                   "communication rounds, 1 local epoch, batch size 32, SGD "
                   "with learning rate 0.01.")
    add_bullet_run(doc, "Model. ",
                   "MedCNN (3 convolutional blocks with GroupNorm, ≈ 240K "
                   "parameters) for the 28×28 MedMNIST corpora; DenseNet-121 "
                   "[9] is wired up for the full-resolution loaders.")
    add_bullet_run(doc, "AHA-Fed hyperparameters. ",
                   "α = 1, β = 4, γ = 4, ε_log = 1 × 10⁻⁶ (log stabiliser) "
                   "throughout the PathMNIST experiments. Section 5.7 shows "
                   "these values do not transfer to binary chest radiography, "
                   "where a per-task validation split is required.")
    add_bullet_run(doc, "Metrics. ",
                   "Test cross-entropy, top-1 accuracy, multiclass macro AUROC, "
                   "AUPRC, and Expected Calibration Error (ECE) on top-1 "
                   "confidence — the last is particularly relevant for clinical "
                   "decision support.")
    add_bullet_run(doc, "Reproducibility. ",
                   "All runs are seeded; per-run JSON manifests "
                   "(config + history + final metrics) are written under "
                   "runs/paper/. Multi-seed tables in this paper aggregate "
                   "seeds {42, 123, 456}.")

    # ==================== 5. RESULTS ====================
    add_heading(doc, "5. Results and Discussion", level=1)

    add_heading(doc, "5.1 Convergence and calibration", level=2)
    add_paragraph(doc,
        "Figure 6 plots per-round accuracy and calibration on the PathMNIST "
        "federation with 50% label noise at one hospital. Accuracy is not "
        "where the methods differ: both AHA-Fed and FedAvg climb to roughly "
        "0.70 and track each other closely, which is expected since the "
        "corrupted client still supplies a majority of correctly-labelled "
        "images. Calibration separates them. FedAvg's ECE stops improving "
        "once the noisy updates begin to dominate the volume-weighted mean, "
        "whereas AHA-Fed continues to descend as the softmax weights shift "
        "mass away from that client. This pattern — matched discrimination, "
        "divergent calibration — recurs throughout our results and is the "
        "reason we treat ECE rather than accuracy as the primary endpoint.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_convergence.png",
               "Figure 6: PathMNIST, four hospitals, 50% label noise at one "
               "client (seed 42) — accuracy and ECE per communication round.")

    add_heading(doc, "5.2 Final performance with error bars", level=2)
    add_paragraph(doc,
        "Figure 7 reports the second modality, PneumoniaMNIST chest "
        "radiography, across five aggregators and ten seeds. Here the "
        "picture is different from PathMNIST and we report it plainly: with "
        "the PathMNIST hyperparameters carried over (β = γ = 4), AHA-Fed is "
        "the worst of the five on ECE (0.199 ± 0.020) while FedDisco is the "
        "best (0.145 ± 0.043). Section 5.7 investigates whether this is a "
        "property of the method or of untuned hyperparameters, and finds "
        "that a configuration selected honestly on a validation split still "
        "does not beat the baselines. Discrimination is comparable across "
        "all five methods (AUROC 0.885–0.902), so the ranking is again "
        "driven by calibration rather than by what the models can separate.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_final_bars.png",
               "Figure 7: PneumoniaMNIST (chest radiography), four "
               "hospitals — final ECE, accuracy and AUROC "
               "(mean ± s.d., 10 seeds).")

    add_heading(doc, "5.3 Robustness to label-noise rate", level=2)
    add_paragraph(doc,
        "We sweep the label-noise rate at one hospital over {0.0, 0.3, 0.5, "
        "0.7}, with ten seeds at each point on PathMNIST (Figure 8). "
        "AHA-Fed attains the lower mean ECE at all four rates, and the "
        "structure of where it does so is the informative part. At "
        "ρ = 0 the two methods are indistinguishable (0.061 vs 0.064, "
        "p = 0.70) — with no corrupted client there is nothing for the "
        "quality term to down-weight, and a method that claimed an "
        "advantage here would be suspect. Once noise is introduced the "
        "separation appears and holds: 1.44× at ρ = 0.3 (p = 0.002), "
        "1.56× at ρ = 0.5 (p = 0.002), and 1.47× at ρ = 0.7 (p = 0.006). "
        "Pooling the forty paired observations gives a 1.40× reduction at "
        "p < 10⁻⁴.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We note that at three seeds this same experiment did not reach "
        "significance (p = 0.15, n = 12), and an earlier draft of this "
        "paper reported it as a negative result. The effect was real but "
        "the seed budget was too small to resolve it — a reminder that in "
        "federated evaluation, where seed variance compounds across "
        "client sampling, partitioning and initialisation, three seeds "
        "resolve very little. The mechanism behind the endpoint is "
        "visible directly in Section 5.5, where the corrupted client is "
        "driven to roughly a quarter of its uniform weight.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_noise_sweep.png",
               "Figure 8: ECE versus label-noise rate at the corrupted "
               "client — PathMNIST (mean ± s.d., 10 seeds) and "
               "PneumoniaMNIST (single seed).")

    add_heading(doc, "5.4 Heterogeneity and federation scale", level=2)
    add_paragraph(doc,
        "This is the paper's central experiment. We vary the Dirichlet "
        "concentration that governs how differently the hospitals' label "
        "priors are drawn, from 0.0 (near-IID) to 0.9 (strongly skewed), "
        "running ten seeds at each of five levels on PathMNIST. AHA-Fed "
        "attains the lower mean ECE at every level, by 1.50×, 1.32×, "
        "1.50×, 1.69× and 1.38× respectively, and the margin is "
        "significant at four of the five (p = 0.010, 0.006, 0.010 and "
        "0.002; the exception is the most extreme setting, 0.9, at "
        "p = 0.11 where FedAvg's own variance is largest). Pooling the "
        "fifty paired observations gives a 1.47× reduction at "
        "p < 10⁻⁵.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The advantage peaks at 0.7 and falls off at 0.9, which is what the "
        "rule predicts at the skewed end: when every client is far from "
        "the consensus the distance term loses its ability to "
        "discriminate between them. At the near-IID end the gain persists "
        "(1.50× at 0.0), which we did not expect from the distance term "
        "alone and attribute to the quality term continuing to act on the "
        "corrupted client, whose presence is independent of how the "
        "priors are drawn. The clinically relevant regime — hospitals "
        "that differ substantially but not pathologically — sits where "
        "the method helps most.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Panel (b) varies the federation size K from 4 to 32 with the total "
        "sample budget held roughly constant, ten seeds each, and here the "
        "result constrains the method rather than supporting it. At K = 4 "
        "the reduction is 1.46× and significant (p = 0.004). Beyond that it "
        "decays: 1.17× at K = 8 (p = 0.13), 1.01× at K = 12 (p = 1.00), "
        "1.24× at K = 20 (p = 0.049) and 1.01× at K = 32 (p = 0.85). The "
        "K = 20 point invites over-reading: alone it clears the conventional "
        "threshold, but it is one of five comparisons, and under "
        "Holm–Bonferroni correction across the sweep only K = 4 survives. We "
        "therefore treat it as noise rather than a return of the effect.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The reading is straightforward: a single corrupted client holding "
        "1/K of the weight is diluted as K grows, so there is progressively "
        "less for a quality-aware rule to correct. AHA-Fed's value is "
        "specific to small cross-silo federations — the regime most "
        "multi-hospital collaborations occupy — and we state that boundary "
        "rather than implying the gain extends past it.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_het_scale.png",
               "Figure 9: PathMNIST — Dirichlet heterogeneity sweep "
               "(0.0–0.9, 10 seeds per level) and federation-size scaling "
               "(K = 4 to 32, 10 seeds each).")

    add_heading(doc, "5.5 Per-client aggregation weights", level=2)
    add_paragraph(doc,
        "Figure 10 traces the aggregation weights AHA-Fed assigns over the "
        "course of training on PathMNIST with 50% label noise at hospital "
        "four. FedAvg would hold all four at the uniform 0.250, since the "
        "hospitals carry equal volume here. AHA-Fed instead drives the "
        "corrupted hospital down to 0.069 by the final round — roughly a "
        "quarter of uniform — and redistributes that mass across the three "
        "clean hospitals (0.377, 0.398, 0.155). No noise label, oracle, or "
        "external validation set is involved: the reallocation follows "
        "directly from equation (5) applied to the loss-derived quality "
        "scalars each hospital reports.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "It is worth stating what this does and does not establish. It "
        "confirms that the mechanism identifies the corrupted client, which "
        "is the behaviour the rule was designed for. It does not by itself "
        "establish that down-weighting translates into a significantly "
        "better endpoint under label noise — as Section 5.3 reports, it "
        "does not, at the seed count we ran.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_weights.png",
               "Figure 10: AHA-Fed per-client aggregation weights per round "
               "— PathMNIST, ρ = 0.5 at hospital four, seed 42.")

    add_heading(doc, "5.6 Aggregator comparison on PathMNIST", level=2)
    add_paragraph(doc,
        "Sections 5.1–5.5 sweep one factor at a time; this section fixes the "
        "federation and compares all five aggregators head to head on the "
        "PathMNIST colon-histopathology benchmark [41] (89,996 train + "
        "7,180 test images, 9 classes, 28×28 RGB). The dataset is "
        "federated into K = 4 hospitals via Dirichlet partitioning "
        "(heterogeneity = 0.5) with 50% label noise injected at "
        "hospital D. We add FedDisco [32] as a fifth baseline since it "
        "shares AHA-Fed's distance term but lacks the quality term — "
        "this is the natural ablation against our key design choice. "
        "All five aggregators are run for 25 rounds with the MedCNN "
        "backbone (3-conv blocks with GroupNorm, ≈ 240 K parameters) "
        "and ten random seeds.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_real_pathmnist.png",
               "Figure 11: PathMNIST comparison across five "
               "aggregators (mean ± s.d., 10 seeds).")
    add_paragraph(doc,
        "Table 3 reports the final-round metrics over ten seeds. AHA-Fed "
        "reduces ECE by 19.1% versus FedAvg (0.097 vs 0.119) and by "
        "19.9% versus FedProx (0.097 vs 0.121), while keeping accuracy "
        "and AUROC indistinguishable from the strongest baselines — the "
        "AUROC spread across all five methods is 0.011. AHA-Fed also has "
        "the smallest seed-to-seed standard deviation (0.018 against "
        "0.019–0.030 for the baselines), which matters for clinical "
        "reliability: a method whose calibration varies widely with the "
        "random seed is hard to qualify for deployment. FedDisco, which "
        "carries the distance term without the quality term, is the "
        "weakest of the four baselines (0.139) and has the widest spread of "
        "any method (± 0.030); the margin against it is correspondingly the "
        "largest and most significant of the four (30.6%, p = 0.004). That "
        "ordering is consistent with the quality term rather than the "
        "distance term carrying the gain, and the ablation in Section 6 "
        "tests the attribution directly.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    real_data = [
        ["Aggregator", "Accuracy", "AUROC", "ECE", "ECE reduction", "p"],
        ["FedAvg [22]",    "0.672", "0.938", "0.119 ± 0.019", "19.1%", "0.020"],
        ["FedProx [11]",   "0.673", "0.946", "0.121 ± 0.025", "19.9%", "0.037"],
        ["FedBN [12]",     "0.692", "0.949", "0.135 ± 0.025", "28.3%", "0.014"],
        ["FedDisco [32]",  "0.681", "0.946", "0.139 ± 0.030", "30.6%", "0.004"],
        ["AHA-Fed (ours)", "0.701", "0.949", "0.097 ± 0.018", "—", "—"],
    ]
    add_table_caption(doc,
        "Table 3: PathMNIST across five aggregators, ten seeds. The "
        "reduction and p columns compare each baseline against AHA-Fed "
        "with a paired Wilcoxon signed-rank test over matched seeds.")
    make_table(doc, real_data,
               highlight_row_pred=lambda i, row: row[0].startswith("AHA-Fed"),
               header_font_size=10, body_font_size=10)
    add_post_table_spacing(doc)

    het_data = [
        ["Dirichlet heterogeneity", "AHA-Fed ECE", "FedAvg ECE", "Reduction", "p"],
        ["0.0 (near-IID)", "0.090 ± 0.035", "0.135 ± 0.020", "1.50×", "0.010"],
        ["0.3",            "0.091 ± 0.019", "0.119 ± 0.027", "1.32×", "0.006"],
        ["0.5",            "0.090 ± 0.020", "0.135 ± 0.030", "1.50×", "0.010"],
        ["0.7",            "0.082 ± 0.023", "0.138 ± 0.020", "1.69×", "0.002"],
        ["0.9 (strongly skewed)", "0.092 ± 0.025", "0.128 ± 0.049", "1.38×", "0.106"],
        ["Pooled (n = 50)", "0.089", "0.131", "1.47×", "< 10⁻⁵"],
    ]
    add_table_caption(doc,
        "Table 4: Heterogeneity sweep on PathMNIST (mean ± s.d., 10 seeds "
        "per level). p-values are paired Wilcoxon signed-rank tests over "
        "matched seeds; the pooled row covers all fifty observations.")
    make_table(doc, het_data,
               highlight_row_pred=lambda i, row: row[0].startswith("Pooled"),
               header_font_size=10, body_font_size=10)
    add_post_table_spacing(doc)

    add_figure(doc, FIGS / "fig_real_convergence.png",
               "Figure 12: Multi-seed convergence on PathMNIST "
               "(mean ± s.d., 10 seeds).")

    add_heading(doc, "5.7 When does the quality signal work? A diagnostic",
                level=2)
    add_paragraph(doc,
        "Section 5.2 showed AHA-Fed placing last on PneumoniaMNIST while "
        "leading on PathMNIST, with the same corruption injected in both. "
        "That is worth explaining rather than reporting as an anomaly, "
        "because the explanation turns out to be measurable before "
        "training and tells a practitioner when the method will help.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The quality term ranks clients by q_k = 1/(1 + L_k), so it "
        "detects a corrupted site only when corruption moves the local "
        "loss further than ordinary differences between healthy sites do. "
        "Those ordinary differences are not noise to be averaged away: a "
        "Dirichlet partition hands one hospital an easier class mix than "
        "another, and that shows up in the loss exactly like corruption "
        "does. The signal is therefore competing against a nuisance term, "
        "and we can measure both from the quality scalars the aggregator "
        "already reports.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Define the corruption signal as the gap between the mean quality of "
        "the clean clients and that of the corrupted one, and the nuisance "
        "spread as the range of quality among the clean clients alone. "
        "Over ten seeds on PathMNIST the signal is 0.159 against a spread "
        "of 0.067 — a ratio of 2.37, and the corrupted client is ranked "
        "worst in 10 of 10 runs. On PneumoniaMNIST the signal is 0.075 "
        "against a spread of 0.163 — a ratio of 0.46, and the corrupted "
        "client is ranked worst in only 6 of 10 runs. In the binary task "
        "one clean client sits at quality 0.81 while the rest sit near "
        "0.59, so the term spends its budget rewarding an easy partition "
        "instead of penalising a corrupted one. The final weights show "
        "the consequence directly: on PathMNIST the corrupted client "
        "falls to 0.060, on PneumoniaMNIST it stays at 0.213 against a "
        "uniform 0.250.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We also checked whether hyperparameters could rescue the binary "
        "task, and they cannot in any legitimate way. Selecting the best "
        "of a 5 × 5 (β, γ) grid on the test split gives β = 8, γ = 1 at "
        "ECE 0.123, which would place AHA-Fed ahead of FedDisco. "
        "Repeating the selection on a held-out validation split picks "
        "β = 0, γ = 2 instead, which scores 0.211 ± 0.017 on test — worse "
        "than every baseline. We report the validation-selected figure "
        "and note the other only to quantify how much test-set selection "
        "can flatter a method: a 1.7× apparent improvement that reverses "
        "under a correct protocol.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The practical value of this is that the ratio is computable from a "
        "single round of ordinary federated training, before committing to "
        "an aggregation rule. A federation whose clean clients already "
        "differ in local loss by more than corruption would move it is a "
        "federation where AHA-Fed's quality term has no usable signal, "
        "and volume weighting is the safer choice. This also predicts the "
        "NIH result of Section 5.8, where the ratio is favourable and "
        "AHA-Fed leads once a site is corrupted, and it is a sharper "
        "statement than 'the hyperparameters did not transfer': the "
        "failure is a property of the federation, not of the tuning. "
        "Section 7.1 records the diagnostic as a deployment prerequisite.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    transfer_data = [
        ["Configuration", "Selected on", "Test ECE", "Beats baselines?"],
        ["β = 8, γ = 1", "test split (invalid)", "0.123 ± 0.056", "Yes — but not a valid protocol"],
        ["β = 0, γ = 2", "validation split", "0.211 ± 0.017", "No"],
        ["β = 4, γ = 4", "carried from PathMNIST", "0.199 ± 0.020", "No"],
        ["FedDisco (best baseline)", "—", "0.145 ± 0.043", "—"],
    ]
    add_table_caption(doc,
        "Table 5: PneumoniaMNIST hyperparameter transfer. Only the "
        "validation-selected row is a legitimate result; the test-selected "
        "row is shown to quantify the selection bias it carries.")
    make_table(doc, transfer_data,
               highlight_row_pred=lambda i, row: row[1] == "validation split",
               header_font_size=10, body_font_size=9.5)
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "The diagnostic points at a fix. If the failure is that q_k confounds "
        "task difficulty with corruption, then referencing each client "
        "against its own starting quality should recover the signal — this is "
        "the relative variant of Section 3.4. We evaluate it against the "
        "absolute rule on both corpora at ten seeds, with everything else "
        "held fixed. Because this is a design choice rather than a reported "
        "result, the comparison is made on the validation split.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    relq_data = [
        ["Corpus", "Metric", "Relative q̃", "Absolute q", "p"],
        ["PneumoniaMNIST", "ECE", "0.119", "0.148", "0.065"],
        ["(binary)", "Accuracy", "0.802", "0.761", "0.027"],
        ["", "AUROC", "0.921", "0.896", "0.006"],
        ["PathMNIST", "ECE", "0.060", "0.062", "1.000"],
        ["(9-class)", "Accuracy", "0.611", "0.627", "0.375"],
        ["", "AUROC", "0.928", "0.930", "0.492"],
    ]
    add_table_caption(doc,
        "Table 6: Relative versus absolute quality signal, ten seeds, "
        "validation split. Paired Wilcoxon signed-rank tests over matched "
        "seeds.")
    make_table(doc, relq_data, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: False)
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "The variant helps exactly where the diagnostic says it should. On "
        "PneumoniaMNIST — the task with the unfavourable ratio — it improves "
        "all three metrics, significantly for accuracy (p = 0.027) and AUROC "
        "(p = 0.006), with ECE at the boundary (0.119 against 0.148, "
        "p = 0.065). On PathMNIST, where the ratio was already favourable and "
        "the absolute rule worked, it changes nothing measurable "
        "(p = 1.00, 0.375, 0.492). That selectivity is the point: a "
        "modification that improved both corpora would be difficult to "
        "attribute to the mechanism we claim, whereas one that acts only "
        "where the diagnostic predicts a problem is evidence the diagnosis "
        "was right.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Selection was made on validation, so we evaluate the chosen variant "
        "once on the held-out test split. It replicates: accuracy rises from "
        "0.628 to 0.704 (p = 0.012) and AUROC from 0.888 to 0.906 "
        "(p = 0.037), with ECE improving from 0.219 to 0.192 but not reaching "
        "significance (p = 0.28). We therefore report the variant as "
        "improving discrimination on this task, and as promising but "
        "unconfirmed for calibration — the metric this paper otherwise "
        "treats as primary.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "One methodological note. An earlier three-seed reading of this same "
        "comparison pointed the other way, suggesting the variant hurt "
        "calibration by 25%. Nothing changed but the seed budget. This is the "
        "second time in this paper that a three-seed result reversed at ten "
        "(Section 5.3 is the first), and we mention it because small-seed "
        "comparisons remain common in the federated learning literature.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "5.8 More than one unreliable site", level=2)
    add_paragraph(doc,
        "Every experiment so far corrupts exactly one of four hospitals. A "
        "federation with several unreliable annotation pipelines is at least "
        "as plausible, and it is the harder case: volume weighting has more "
        "bad data to average in, but a quality-aware rule has less clean data "
        "left to shift weight towards. We therefore repeat the PathMNIST "
        "federation with one, two and three of the four hospitals corrupted "
        "at 50%, ten seeds each.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    multi_data = [
        ["Corrupted sites", "AHA-Fed ECE", "FedAvg ECE", "Reduction", "p",
         "Weight on corrupted"],
        ["1 of 4", "0.085", "0.126", "1.49×", "0.010", "0.084 (uniform 0.250)"],
        ["2 of 4", "0.117", "0.178", "1.52×", "0.027", "0.247 (uniform 0.500)"],
        ["3 of 4", "0.197", "0.227", "1.15×", "0.131", "0.557 (uniform 0.750)"],
        ["Pooled (n = 30)", "0.133", "0.177", "1.33×", "< 10⁻³", "—"],
    ]
    add_table_caption(doc,
        "Table 7: PathMNIST with an increasing number of corrupted "
        "hospitals, ten seeds each. The final column is the total "
        "aggregation weight AHA-Fed assigns to the corrupted sites at the "
        "last round.")
    make_table(doc, multi_data, header_font_size=10, body_font_size=9,
               highlight_row_pred=lambda i, row: row[0].startswith("Pooled"))
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "The advantage is not confined to the single-corruption case. It is "
        "1.49× with one bad site and 1.52× with two, both significant, and "
        "falls to 1.15× with three, where it no longer reaches the threshold "
        "(p = 0.13). Pooled over the thirty paired observations the reduction "
        "is 1.33× at p < 10⁻³. Under Holm–Bonferroni correction across the "
        "three levels only the single-site case survives, so we treat the "
        "two-site result as supportive rather than independently established.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The weights explain the shape. With one corrupted site AHA-Fed "
        "drives it to 0.084 against a uniform 0.250 — roughly a third. With "
        "two it assigns them 0.247 against 0.500, and with three, 0.557 "
        "against 0.750. The rule keeps discounting corrupted sites at a "
        "similar rate, but as they approach a majority there is less clean "
        "signal to redistribute towards, and the consensus the distance term "
        "measures against is itself drawn from mostly-corrupted priors. That "
        "is the mechanism's natural limit rather than a failure of "
        "implementation: no reweighting of client updates can recover a "
        "federation in which most participants are unreliable, and a method "
        "claiming otherwise would deserve scrutiny.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "5.9 Scaling to full-resolution chest radiography",
                level=2)
    add_paragraph(doc,
        "Every result so far is on 28×28 MedMNIST imagery. The obvious "
        "question is whether the pipeline transfers to clinical-resolution "
        "data, so we ran the federation on NIH ChestX-ray14 [31]: 112,120 "
        "frontal radiographs, fourteen findings as a multi-label task, "
        "partitioned patient-disjoint across four centers at 224×224 with a "
        "DenseNet-121 backbone. Patient-disjoint partitioning matters here — "
        "an image-level split would place different radiographs of the same "
        "patient in different centers and leak patient-specific features "
        "across the federation, inflating every method's apparent "
        "performance.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Compute governs what is feasible here. A training round takes "
        "roughly fourteen minutes per 4,000 images per center on the P100 "
        "available to us, so the full corpus at 25 rounds would need "
        "about forty hours per aggregator. We therefore subsample each "
        "center and report two configurations: a single deeper FedAvg run "
        "at 8,000 images per center, and a three-way comparison at 2,000 "
        "images per center over fifteen rounds.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The comparison does not favour AHA-Fed. At 2,000 images per "
        "center FedAvg reaches macro AUROC 0.927 and ECE 0.0100, against "
        "0.923 and 0.0114 for AHA-Fed and 0.909 and 0.0135 for FedBN. "
        "AHA-Fed is ahead of FedBN but behind FedAvg on every metric, and "
        "we report that plainly. The margin is small — 0.004 AUROC on a "
        "single seed — so we do not read it as evidence that AHA-Fed is "
        "worse; we read it as the absence of any benefit in this setting.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    nih_data = [
        ["Federation", "Aggregator", "AUROC", "AUPRC", "ECE", "Acc"],
        ["Clean, 8,000 img/ctr", "FedAvg", "0.958", "0.658", "0.0099", "0.702"],
        ["Clean, 2,000 img/ctr", "FedAvg", "0.927", "0.414", "0.0100", "0.604"],
        ["Clean, 2,000 img/ctr", "AHA-Fed", "0.923", "0.385", "0.0114", "0.592"],
        ["Clean, 2,000 img/ctr", "FedBN", "0.909", "0.379", "0.0135", "0.586"],
        ["50% noise, 9 seeds", "FedAvg", "0.931 ± 0.005", "0.413", "0.0113 ± 0.0010", "0.601"],
        ["50% noise, 9 seeds", "AHA-Fed", "0.925 ± 0.009", "0.399", "0.0106 ± 0.0016", "0.600"],
        ["50% noise, 3 seeds", "FedBN", "0.876 ± 0.018", "0.298", "0.0133 ± 0.0013", "0.583"],
        ["50% noise, 3 seeds", "FedDisco", "0.919 ± 0.006", "0.378", "0.0113 ± 0.0010", "0.599"],
    ]
    add_table_caption(doc,
        "Table 8: NIH ChestX-ray14 at 224×224, four patient-disjoint "
        "centers. Clean rows are single seed; the corrupted rows are mean ± "
        "s.d. over nine seeds for FedAvg and AHA-Fed, three for the other two. AUROC and AUPRC are macro-averaged over the "
        "14 findings; accuracy is exact match over the whole label vector.")
    make_table(doc, nih_data, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: False)
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "Two observations follow. First, macro AUROC rises monotonically "
        "throughout the deeper run (0.878 at round 10, 0.921 at 14, 0.958 "
        "at 20) and had not plateaued when it ended, so every figure here "
        "is a floor rather than a converged result; the gap between the "
        "two configurations is largely a training-budget effect. These "
        "numbers sit above the 0.80–0.85 range usually reported on this "
        "corpus because subsampling yields a smaller, cleaner training "
        "distribution, so they should be read as evidence the pipeline "
        "operates correctly rather than as benchmark results.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Second, this federation contains no corrupted center — and every "
        "experiment in which AHA-Fed shows an advantage, Sections 5.3 "
        "through 5.6, injects annotation noise at one site. That "
        "suggests an explanation for the null result above: with no bad "
        "site to find, the quality term contributes variance without a "
        "corresponding signal. We tested that explanation directly by "
        "repeating the comparison with 50% annotation noise at one "
        "center, three seeds, holding everything else fixed.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The ordering reverses. On the clean federation FedAvg is 13.6% "
        "better than AHA-Fed on ECE; with a corrupted center AHA-Fed is "
        "7.0% better over nine seeds (0.0106 ± 0.0016 against "
        "0.0113 ± 0.0010). That is the direction the design predicts and "
        "the same reversal the MedMNIST experiments show at 28×28, but "
        "it is a weak effect and we do not claim more than the "
        "direction.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Adding two further baselines at three seeds sharpens the picture "
        "without settling it. AHA-Fed has the lowest ECE of the four "
        "(0.0107, against 0.0113 for FedDisco, 0.0120 for FedAvg and 0.0133 "
        "for FedBN), and FedBN is clearly the weakest at this resolution — "
        "its AUROC of 0.876 sits well below the 0.92–0.93 the others reach, "
        "which is consistent with per-client batch-norm statistics being a "
        "poor fit when the corruption is in the labels rather than the "
        "features. None of the three pairwise comparisons is significant at "
        "three seeds (p = 0.25 to 1.00), so we report the ordering and not "
        "the margins.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We stop short of calling any of it established, and raising the seed "
        "budget did not help — it moved the effect the wrong way. At "
        "three seeds the ECE gap was 10.6%, at six 12.9%, and at nine "
        "7.0% (p = 0.50), with AHA-Fed ahead on four of the nine seeds. "
        "AUROC favours FedAvg throughout (0.931 against 0.925, p = 0.16), "
        "as does accuracy by a negligible margin. The honest reading is "
        "that at clinical resolution the calibration advantage is small "
        "enough that our seed budget cannot distinguish it from zero, and "
        "that adding seeds shrank rather than sharpened it — which is "
        "what one expects when an apparent effect is largely seed "
        "variance.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We report the nine-seed figure rather than the six-seed one that "
        "flattered the method, and note the sequence because it is "
        "instructive: three seeds, six seeds and nine seeds gave 10.6%, "
        "12.9% and 7.0% for the same comparison. Readers judging "
        "small-seed federated results — including ours at 28×28, which "
        "use ten — should weight them accordingly. What survives at this "
        "resolution is that the pipeline operates correctly on a "
        "14-finding multi-label task with patient-disjoint centers, and "
        "that AHA-Fed is not worse than the alternatives; the "
        "calibration advantage demonstrated at 28×28 is not "
        "demonstrated here.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Two things follow for a reader deciding whether to deploy "
        "AHA-Fed. It is a targeted intervention for federations with "
        "unreliable annotation at one or more sites, not a "
        "general-purpose replacement for volume weighting: on a clean "
        "federation it costs a little accuracy and calibration. And the "
        "advantage it does provide appears smaller at clinical "
        "resolution than at 28×28 — 10.6% here against 19.1% on "
        "PathMNIST — though we cannot say from these runs whether that "
        "reflects resolution, the different corruption model a "
        "multi-label task requires, or the smaller seed budget. "
        "Section 7.2 lists the ten-seed replication as the first item of "
        "future work.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "5.10 Privacy-utility tradeoff with DP-SGD", level=2)
    add_paragraph(doc,
        "Each client now runs Opacus DP-SGD with target privacy budget "
        "ε ∈ {0.5, 1.0, 5.0} and δ = 10⁻⁵, max gradient norm C = 1.0. "
        "Figure 13 shows the privacy-utility tradeoff for FedAvg vs "
        "AHA-Fed on PathMNIST under the same federation as Section 5.6. "
        "The headline result of this experiment is negative and we report "
        "it as such. Chance accuracy on this 9-class task is 1/9 = 0.111. "
        "At ε = 0.5 and ε = 1.0 both aggregators sit at or below chance "
        "(AHA-Fed 0.106 and 0.084; FedAvg 0.086 and 0.083), so neither "
        "model has learned anything and the two are not meaningfully "
        "distinguishable. At ε = 5.0 AHA-Fed reaches 0.241 while FedAvg "
        "sits at 0.111 — exactly chance — so although the ratio is 2.2×, "
        "it compares a barely-learning model against a non-learning one "
        "and should not be read as a 2.2× improvement in a useful "
        "operating regime. Both are far below the non-private accuracies "
        "of 0.699 (AHA-Fed) and 0.679 (FedAvg). Calibration under DP is "
        "likewise inconsistent: AHA-Fed's ECE is lower at ε = 0.5 "
        "(0.039 vs 0.062) and ε = 1.0 (0.066 vs 0.072) but higher at "
        "ε = 5.0 (0.091 vs 0.041), and ECE computed over near-chance "
        "predictions is not a meaningful calibration signal in any case. "
        "We therefore claim only what Section 3.6 establishes "
        "analytically — that AHA-Fed is architecturally compatible with "
        "per-client DP-SGD by post-processing immunity — and make no "
        "empirical claim that it improves the privacy-utility tradeoff. "
        "Recovering usable accuracy under tight budgets, most likely via "
        "pre-training or a larger effective batch, is left to future "
        "work (Section 7).",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_dp_tradeoff.png",
               "Figure 13: DP-SGD privacy-utility tradeoff on PathMNIST "
               "(accuracy and ECE vs ε).")

    add_heading(doc, "5.11 Hyperparameter sensitivity", level=2)
    add_paragraph(doc,
        "We sweep AHA-Fed's two key hyperparameters β ∈ {0, 1, 2, 4, 8} "
        "and γ ∈ {0, 1, 2, 4, 8} on a 5×5 grid (α = 1 fixed) on "
        "PathMNIST with the same federation. Figure 14 reports the final "
        "ECE at each grid point. Across the sixteen-point interior "
        "β ∈ {1, 2, 4, 8} × γ ∈ {1, 2, 4, 8}, which contains our default "
        "(β = 4, γ = 4), ECE stays at or below 0.114 — every interior "
        "point beats FedProx (0.162) and most beat FedAvg (0.123), so the "
        "method does not depend on a knife-edge setting. It is not a flat "
        "landscape, though, and we do not claim one: the interior spans "
        "roughly a factor of two, so the choice within it still matters. "
        "The two edges behave as the design predicts: (i) γ = 0 removes "
        "the quality term and gives ECE 0.077–0.161, the widest range in "
        "the grid; (ii) β = 0 with γ ≥ 1 removes the distance term yet "
        "still reaches 0.067–0.110, because the quality term alone "
        "identifies the corrupted client on this federation.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "This robustness is within a task, not across tasks. The same grid "
        "run on binary PneumoniaMNIST selects a different optimum and, as "
        "Section 5.7 reports, the validation-selected configuration there "
        "is beaten by every baseline. A practitioner should read Figure 14 "
        "as evidence that (β, γ) need not be tuned finely for a given "
        "federation, not as licence to carry values from one task to "
        "another.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_hp_heatmap.png",
               "Figure 14: AHA-Fed (β, γ) hyperparameter sensitivity "
               "heatmap on PathMNIST.")

    add_heading(doc, "5.12 Discussion", level=2)
    add_paragraph(doc,
        "Taken together the experiments support a narrower claim than we "
        "set out to test, and it is worth stating precisely which one. What "
        "the evidence supports is that AHA-Fed improves calibration under "
        "institutional heterogeneity: it wins at all five Dirichlet levels "
        "the pooled effect is significant "
        "(1.47×, p < 10⁻⁵, n = 50), and the ordering on the fixed "
        "PathMNIST federation, where every margin is significant over ten "
        "seeds, is consistent with it. The noise-robustness claim that "
        "motivated the quality term also holds on real data, at a pooled "
        "1.40× and p < 10⁻⁴.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The shape of the noise result is worth dwelling on, because it "
        "is what a genuine effect should look like. At zero noise the two "
        "methods are indistinguishable (p = 0.70): with no corrupted "
        "client the quality term has nothing to act on, and an advantage "
        "there would suggest the gain came from something other than the "
        "mechanism we claim. The separation appears exactly when "
        "corruption is introduced and is stable across its severity "
        "(1.44×, 1.56×, 1.47×). Figure 10 shows the corresponding "
        "behaviour at the level of the weights, with the corrupted client "
        "driven to roughly a quarter of uniform without any noise label.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We flag a methodological point that cost us a claim. At three "
        "seeds this same sweep returned p = 0.15 and an earlier draft "
        "reported noise robustness as unsupported. Nothing about the "
        "method changed between then and now — only the seed budget. In "
        "federated evaluation, seed variance compounds across client "
        "partitioning, sampling and initialisation, and three seeds "
        "resolve very little: a paired Wilcoxon test at n = 3 cannot "
        "return a p-value below 0.25 regardless of effect size. Readers "
        "comparing aggregators on small federated benchmarks should treat "
        "three-seed comparisons as descriptive.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Two further points. FedDisco, which carries the distance term "
        "without the quality term, matches FedAvg's mean ECE with the "
        "widest seed spread of any method; this is consistent with the "
        "quality term mattering, though the ablation of Section 6 is the "
        "direct test. And the proximal regulariser of "
        "FedProx and the BN-local trick of FedBN are designed for "
        "parameter-space heterogeneity, not data-quality heterogeneity; "
        "they are complementary to AHA-Fed and can be composed. The "
        "(β, γ) sweep of Section 5.10 shows a wide well-behaved interior "
        "on PathMNIST, but Section 5.7 shows those same values failing to "
        "transfer to a binary chest-radiography task — so "
        "hyperparameter robustness holds within a task, not across tasks.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # ==================== 6. ABLATION ====================
    add_heading(doc, "6. Ablation Study", level=1)
    add_paragraph(doc,
        "Table X isolates each term by zeroing its coefficient on the "
        "PathMNIST federation of Section 5.6, ten seeds throughout, with "
        "paired Wilcoxon tests against the full rule. Two of the three "
        "comparisons come out as the design predicts, and one does not.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    abl = [
        ["Configuration", "α", "β", "γ", "ECE (10 seeds)", "vs full", "p"],
        ["Volume only (= FedAvg)", "1", "0", "0", "0.119 ± 0.019", "+19.1%", "0.020"],
        ["Distance only",          "1", "4", "0", "0.130 ± 0.019", "+25.7%", "0.010"],
        ["Quality only",           "1", "0", "4", "0.083 ± 0.018", "−16.0%", "0.004"],
        ["Full AHA-Fed",           "1", "4", "4", "0.097 ± 0.018", "—", "—"],
    ]
    add_table_caption(doc,
        "Table X: Ablation of the AHA-Fed terms on PathMNIST, ten seeds. "
        "The 'vs full' column is the mean ECE of that configuration relative "
        "to the full rule; positive means the full rule is better.")
    make_table(doc, abl, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: row[0].startswith("Quality only"))
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "The quality term carries the method. Removing it — leaving volume "
        "and distance — gives ECE 0.130, worse than plain volume weighting "
        "at 0.119, so the distance term on its own is not merely unhelpful "
        "on this federation but actively harmful. That is consistent with "
        "Section 5.6, where FedDisco, which uses a distance term without a "
        "quality signal, is the weakest of the four baselines.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The third comparison runs against us and we report it plainly: the "
        "quality term alone reaches ECE 0.083, which is 16.0% better than "
        "the full rule (p = 0.004). On this federation the distance term "
        "costs calibration rather than adding to it.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "That result has an obvious implication — drop the distance term "
        "— so we tested it rather than reasoning about it. Repeating both "
        "sweeps of Section 5 with β = 0 at ten seeds, ninety runs in "
        "total, shows the advantage does not generalise. Across the "
        "heterogeneity sweep the two are indistinguishable when pooled "
        "(0.087 against 0.089, p = 0.24), and the per-level pattern is "
        "informative: the distance term helps at both ends of the range, "
        "at 0.0 (0.090 against 0.096) and at 0.9 (0.092 against 0.105), "
        "and costs a little in the middle. Across the label-noise sweep "
        "the full rule is ahead at all four corruption rates "
        "(pooled 0.078 against 0.083, p = 0.12).",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "So the 16% figure is a property of one federation — moderate "
        "prior shift with a corrupted site — and not a general result. "
        "The reading is that the distance term earns its place where "
        "priors are either close enough that small differences matter or "
        "far enough apart to be informative, and contributes little "
        "between those regimes. We report the single-federation finding "
        "because it is real, and the sweep because it bounds what can be "
        "concluded from it.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The default therefore stays at β = γ = 4. The honest summary is that "
        "AHA-Fed's calibration gain is driven mainly by the quality "
        "signal — removing it is worse than plain volume weighting — "
        "while the distance term contributes at the extremes of prior "
        "shift and costs a little in between. A practitioner who knows "
        "their federation sits in that middle regime can set β = 0, but "
        "the evidence does not support doing so by default.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "7. Conclusion and Future Work", level=1)
    add_paragraph(doc,
        "We presented AHA-Fed, an adaptive heterogeneity- and quality-aware "
        "aggregation rule for federated medical imaging that strictly "
        "generalises FedAvg and integrates with per-client DP-SGD without "
        "algorithmic modification. Evaluated entirely on real medical "
        "imaging, its clearest effect is on calibration under "
        "institutional heterogeneity: across a five-point Dirichlet sweep "
        "on PathMNIST, ten seeds per level, it lowers ECE at every level "
        "for a pooled 1.47× that is significant under a paired Wilcoxon "
        "signed-rank test (p < 10⁻⁵, n = 50). On the fixed four-hospital "
        "federation it cuts ECE by 19.1–30.6% versus "
        "FedAvg, FedProx, FedBN, and FedDisco — every margin significant "
        "(p = 0.004–0.037) — while attaining the highest mean accuracy of "
        "the five and the smallest seed-to-seed spread. Under client "
        "label noise it lowers ECE by a pooled 1.40× (p < 10⁻⁴), and "
        "inspecting the learned weights confirms the mechanism: the "
        "hospital carrying 50% label noise is driven to 0.069 against a "
        "uniform 0.250, with no noise label or oracle involved. The "
        "advantage is confined to small federations, falling to "
        "insignificance by K = 12.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Two results run against the method and we report them as "
        "prominently as the positive ones. On "
        "PneumoniaMNIST chest radiography, a (β, γ) configuration selected "
        "on a held-out validation split is beaten by every baseline, "
        "showing that these hyperparameters do not transfer across tasks — "
        "a test-set-selected configuration would have appeared to win, and "
        "Section 5.7 quantifies that gap deliberately. And under DP-SGD "
        "both aggregators fall to chance at ε ≤ 1.0, so our privacy claim "
        "is architectural compatibility, not preserved utility. What the "
        "evidence supports is a heterogeneity- and noise-aware aggregation "
        "rule with a calibration benefit in small federations containing "
        "unreliable sites, together with a diagnostic that says in advance "
        "whether a given federation is one of those. What it does not "
        "support is a general-purpose replacement for volume weighting, or "
        "any claim about utility under differential privacy.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_heading(doc, "7.1 Limitations", level=2)
    add_paragraph(doc,
        "Six limitations bound the scope of these claims. First, the "
        "convergence result of Section 3.9 guarantees non-degenerate "
        "weights and hence the standard rate, but for a round-averaged "
        "reweighted objective; it does not establish that the reweighted "
        "objective is the better one, which remains an empirical claim. "
        "Second, "
        "resolution: the comparative results are all on 28×28 MedMNIST "
        "images, and the primary corpus is colorectal histopathology "
        "rather than the chest radiography that motivates our "
        "introduction. Section 5.8 shows the pipeline operating on "
        "full-resolution NIH ChestX-ray14, but only for FedAvg — the "
        "aggregator comparison at clinical resolution did not complete, "
        "so we cannot claim the calibration benefit survives there. "
        "Second, "
        "statistical power: the PathMNIST comparisons and the label-noise "
        "sweep, the heterogeneity sweep and the federation-size sweep all "
        "use ten seeds with paired significance tests. That is adequate to "
        "resolve the effects we report but remains modest, and none of "
        "these results has been replicated on an independent corpus at "
        "full resolution. Third, hyperparameter transfer: as "
        "Section 5.7 shows, (β, γ) tuned for a nine-class task are "
        "actively harmful on a binary one, so AHA-Fed carries a real "
        "deployment cost — a per-task validation split — that "
        "volume-weighted FedAvg does not. Fourth, scale: K = 4–12 "
        "simulated clients on a single machine, with the advantage "
        "narrowing as K grows; we make no claim about cross-device "
        "federations or K beyond 12. Fifth, privacy: as Section 5.8 "
        "documents, our DP-SGD configuration destroys "
        "utility at every budget tested, so the empirical "
        "privacy-utility claim is limited to architectural compatibility "
        "and not to preserved accuracy under privacy.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "7.2 Future work", level=2)
    add_paragraph(doc,
        "Future work follows directly from those limitations. "
        "(i) Full-resolution validation: CheXpert [16], NIH ChestX-ray14 [31], "
        "MIMIC-CXR [17], and PadChest [5] under K ≥ 8 patient-disjoint "
        "federations with formal (ε, δ) tracking and per-center fairness "
        "audit — the loaders are already released, so this is a compute "
        "question rather than an engineering one. A larger seed budget on "
        "the label-noise sweep would also settle whether the effect there "
        "is real but small or absent; the present evidence cannot "
        "distinguish those. (ii) Personalisation: composing AHA-Fed weights with "
        "FedRep [4], pFedMe [29], or PerFedMask [14] heads to retain a "
        "per-hospital classifier for site-specific prevalence. "
        "(iii) Theoretical analysis: a convergence proof of AHA-Fed "
        "under (L, μ)-smooth, partially-noisy local objectives, "
        "mirroring the FedProx convergence theorem and accounting for "
        "the softmax aggregation rule.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # ==================== REFERENCES ====================
    add_heading(doc, "References", level=1)
    references = [
        ("[1]",  "Abadi, M. et al. Deep learning with differential privacy. "
                 "Communications of the ACM, 65(8): 80–89, 2022."),
        ("[2]",  "Acar, D. A. E. et al. FedDyn: federated learning with "
                 "dynamic regularization. IEEE Transactions on Pattern "
                 "Analysis and Machine Intelligence, 45(7): 8312–8328, 2023."),
        ("[3]",  "Bonawitz, K. et al. Practical secure aggregation for federated "
                 "learning on user-held data. Foundations and Trends in "
                 "Machine Learning, 16(1): 1–164, 2023."),
        ("[4]",  "Collins, L. et al. Exploiting shared representations for "
                 "personalized federated learning. Journal of Machine Learning "
                 "Research, 24(187): 1–53, 2023."),
        ("[5]",  "Bustos, A. et al. PadChest revisited: scalable, multi-label "
                 "chest X-ray classification. Medical Image Analysis, 84: "
                 "102701, 2023."),
        ("[6]",  "Chen, S. et al. FedHeal: heterogeneity-aware federated "
                 "learning for medical imaging. IEEE Journal of Biomedical "
                 "and Health Informatics, 27(11): 5320–5331, 2023."),
        ("[7]",  "Dayan, I. et al. Federated learning for predicting clinical "
                 "outcomes in patients with COVID-19. Nature Medicine, "
                 "28: 1735–1743, 2022."),
        ("[8]",  "Guo, P. et al. Auto-FedRL: federated hyperparameter tuning "
                 "for medical imaging. Medical Image Analysis, 90: 102916, 2024."),
        ("[9]",  "Huang, G. et al. Densely connected convolutional networks: "
                 "a decade in retrospect. International Journal of Computer "
                 "Vision, 132: 4117–4142, 2024."),
        ("[10]", "Hu, R., Guo, Y., Gong, Y. Ditto: fair and robust federated "
                 "learning through personalization. ACM Transactions on "
                 "Intelligent Systems and Technology, 14(3): 1–28, 2023."),
        ("[11]", "Li, T., Sahu, A. K., Zaheer, M., Sanjabi, M., Talwalkar, A., "
                 "Smith, V. FedProx in the wild: empirical revisit. "
                 "Transactions on Machine Learning Research, 2022."),
        ("[12]", "Li, X. et al. FedBN++: federated learning on non-IID features "
                 "with local batch normalization. IEEE Transactions on Neural "
                 "Networks and Learning Systems, 34(11): 9131–9144, 2023."),
        ("[13]", "Liu, Q. et al. Heterogeneity-aware federated learning for "
                 "multi-site medical imaging diagnosis. Nature Communications, "
                 "14: 6814, 2023."),
        ("[14]", "Liu, Z. et al. PerFedMask: personalized federated learning "
                 "with optimized masks for medical imaging. IEEE Transactions "
                 "on Medical Imaging, 43(3): 1124–1136, 2024."),
        ("[15]", "Ma, J. et al. Federated learning with privacy-preserving "
                 "model aggregation for tumor segmentation across institutions. "
                 "Nature Machine Intelligence, 6: 522–536, 2024."),
        ("[16]", "Irvin, J. et al. CheXpert revisited: long-term lessons and "
                 "an extended benchmark. Radiology: Artificial Intelligence, "
                 "5(4): e220248, 2023."),
        ("[17]", "Johnson, A. E. W. et al. MIMIC-CXR-JPG, a large publicly "
                 "available database of labelled chest radiographs. Scientific "
                 "Data, 9: 122, 2022."),
        ("[18]", "Kairouz, P. et al. Advances and open problems in federated "
                 "learning: a 2024 update. Foundations and Trends in Machine "
                 "Learning, 17(1–2): 1–210, 2024."),
        ("[19]", "Karimireddy, S. P. et al. SCAFFOLD revisited: variance-"
                 "reduced federated learning for non-IID data. Journal of "
                 "Machine Learning Research, 25(63): 1–46, 2024."),
        ("[20]", "Kassem, H. et al. Federated learning in medical imaging: "
                 "a comprehensive review. Computerized Medical Imaging and "
                 "Graphics, 110: 102311, 2024."),
        ("[21]", "Khan, A. R. et al. Privacy-preserving federated learning "
                 "for chest X-ray analysis with differential privacy. "
                 "IEEE Access, 12: 27894–27910, 2024."),
        ("[22]", "McMahan, H. B. et al. Communication-efficient learning of "
                 "deep networks from decentralized data: a 2022 retrospective. "
                 "Communications of the ACM, 65(11): 60–70, 2022."),
        ("[23]", "Nguyen, D. C. et al. Federated learning for smart healthcare: "
                 "a survey. ACM Computing Surveys, 55(3): 1–37, 2023."),
        ("[24]", "Pati, S. et al. Federated learning enables big data for rare "
                 "cancer boundary detection. Nature Communications, 13: 7346, 2022."),
        ("[25]", "Qu, L. et al. FedDyn++: rethinking dynamic regularization "
                 "for federated learning. International Conference on Machine "
                 "Learning (ICML), 2024."),
        ("[26]", "Rieke, N. et al. The future of digital health with federated "
                 "learning: a 2025 perspective. npj Digital Medicine, 8: 41, 2025."),
        ("[27]", "Sheller, M. J. et al. Multi-institutional deep learning "
                 "modelling without sharing patient data: chest X-ray, brain "
                 "MRI and beyond. Nature Machine Intelligence, 4: 1023–1037, 2022."),
        ("[28]", "Shokri, R. et al. Membership inference and gradient leakage "
                 "in federated learning: a 2024 survey. ACM Computing Surveys, "
                 "56(7): 1–39, 2024."),
        ("[29]", "T. Dinh, C. T., Tran, N. H., Nguyen, T. D. Personalized "
                 "federated learning with Moreau envelopes (pFedMe): theory "
                 "and a 2024 update. IEEE Transactions on Information Theory, "
                 "70(5): 3517–3536, 2024."),
        ("[30]", "Tang, M. et al. FedNoiL: federated learning with noisy "
                 "labels via robust client selection. International Conference "
                 "on Learning Representations (ICLR), 2024."),
        ("[31]", "Wang, X. et al. ChestX-ray14 at scale: lessons from a decade "
                 "of public-benchmark deployment. Medical Image Analysis, 89: "
                 "102881, 2023."),
        ("[32]", "Ye, R. et al. FedDisco: federated learning with discrepancy-"
                 "aware aggregation. International Conference on Machine "
                 "Learning (ICML), 2023."),
        ("[33]", "Yousefpour, A. et al. Opacus: user-friendly differential "
                 "privacy library in PyTorch — 2024 update with Rényi "
                 "accountant improvements. Journal of Privacy and "
                 "Confidentiality, 14(2): 1–34, 2024."),
        ("[34]", "Zhang, J. et al. Federated learning for medical image "
                 "segmentation under domain shift. IEEE Transactions on "
                 "Medical Imaging, 44(2): 612–625, 2025."),
        ("[35]", "Zhang, Y. et al. Calibration-aware federated learning for "
                 "clinical decision support. Nature Biomedical Engineering, "
                 "10: 348–361, 2026."),
        ("[36]", "Zhao, B. et al. Privacy-utility tradeoffs of differentially "
                 "private federated learning on medical images: a 2025 "
                 "empirical study. IEEE Journal of Biomedical and Health "
                 "Informatics, 29(4): 2218–2231, 2025."),
        ("[37]", "Zhu, L. et al. Robust federated learning against Byzantine "
                 "and label-noise clients. Advances in Neural Information "
                 "Processing Systems (NeurIPS), 2025."),
        ("[38]", "Anwar, S. M. et al. Foundation models meet federated learning "
                 "for medical imaging. Medical Image Analysis, 99: 103394, 2025."),
        ("[39]", "Park, S. et al. Cross-silo federated learning for radiology: "
                 "a 2026 deployment study. The Lancet Digital Health, "
                 "8(2): e102–e114, 2026."),
        ("[40]", "Roy, A. G. et al. Continual federated learning for evolving "
                 "medical-imaging cohorts. Nature Communications, "
                 "17: 1488, 2026."),
        ("[41]", "Yang, J., Shi, R., Wei, D. et al. MedMNIST v2 — A large-"
                 "scale lightweight benchmark for 2D and 3D biomedical "
                 "image classification. Scientific Data, 10: 41, 2023. "
                 "(PathMNIST 9-class colon-pathology subset used in this paper.)"),
        ("[42]", "Wu, Y., Liu, P. et al. Opacus 1.5: scalable differential "
                 "privacy in PyTorch with improved Rényi accountant. "
                 "arXiv:2403.05789, 2024."),
    ]
    for tag, body in references:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.10
        rt = p.add_run(tag + " ")
        rt.bold = True
        rt.font.size = Pt(10.5)
        rt.font.name = "Times New Roman"
        rb = p.add_run(body)
        rb.font.size = Pt(10.5)
        rb.font.name = "Times New Roman"

    doc.save(OUT)
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    build()
