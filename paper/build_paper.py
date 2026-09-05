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


def add_algorithm(doc, title, rows):
    """Set an algorithm the way IEEE does: ruled above and below, with
    the step numbers in a hanging indent so the body text aligns.

    A tab stop is not enough -- a wrapped step returns to the left margin
    and its continuation collides with the numbers. The hanging indent
    keeps continuations under the body, which is what makes the block
    readable.
    """
    from docx.enum.text import WD_TAB_ALIGNMENT

    def rule(space_before, space_after):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = Pt(space_before)
        pf.space_after = Pt(space_after)
        pPr = p._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        top = OxmlElement("w:top")
        top.set(qn("w:val"), "single")
        top.set(qn("w:sz"), "8")
        top.set(qn("w:space"), "1")
        top.set(qn("w:color"), "000000")
        borders.append(top)
        pPr.append(borders)
        return p

    rule(6, 2)
    head = doc.add_paragraph()
    head.paragraph_format.space_after = Pt(2)
    r = head.add_run(title)
    r.bold = True
    r.font.size = Pt(9.5)
    rule(0, 3)

    for tag, body in rows:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(0)
        pf.left_indent = Cm(1.05)
        pf.first_line_indent = Cm(-1.05)
        pf.tab_stops.add_tab_stop(Cm(1.05), WD_TAB_ALIGNMENT.LEFT)
        run = p.add_run(f"{tag}\t{body}")
        run.font.size = Pt(9)
        run.font.name = "Times New Roman"

    rule(3, 6)


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
        "Measurable Conditions for Quality-Aware Federated "
        "Aggregation in Medical Imaging"
    )
    r.bold = True
    r.font.size = Pt(16)
    r.font.name = "Times New Roman"
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Abu Ubaida, Khurram Zeeshan Haider, "
                  "Farhan Aadil, Celal Alagoz")
    r.bold = True
    r.font.size = Pt(12.5)
    r.font.name = "Times New Roman"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Government College University Faisalabad, Pakistan; "
                  "Sivas University of Science and Technology, Turkiye")
    r.italic = True
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run("Corresponding author: farhan.aadil@sivas.edu.tr")
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"

    # ==================== ABSTRACT (300 words) ====================
    add_heading(doc, "Abstract", level=1)
    abstract = (
        "Federated learning lets hospitals train medical-imaging models "
        "without exchanging patient data, but real deployments face "
        "statistical heterogeneity across sites and per-site annotation "
        "noise that volume-weighted aggregation silently amplifies. "
        "Aggregation rules that reweight clients by an estimate of their "
        "data quality are an established response, yet the conditions "
        "under which they help have not been characterised. We study this "
        "through AHA-Fed, whose per-round client weights are a softmax "
        "over a log-space score combining data volume, total-variation "
        "distance to the across-client label-prior consensus, and a "
        "self-supervised quality signal from the local training loss. It "
        "reduces to FedAvg as a strict special case, and we prove its "
        "weights are bounded away from zero, placing it within the "
        "standard FedAvg convergence rate. Evaluated against FedAvg, "
        "FedProx, FedBN and FedDisco on real medical imaging only, "
        "PathMNIST, PneumoniaMNIST and full-resolution NIH "
        "ChestX-ray14, AHA-Fed lowers Expected Calibration Error on "
        "PathMNIST to 0.097 ± 0.018 against 0.119–0.139 for the "
        "baselines over ten seeds, every margin significant under a "
        "paired Wilcoxon test (p = 0.004–0.037), while attaining the "
        "highest accuracy (0.701) and matching AUROC. Under client label "
        "noise it reduces ECE by a pooled 1.40× (p < 10⁻⁴, n = 40), with "
        "no separation at zero noise, and drives the corrupted client to "
        "weight 0.069 against a uniform 0.250. The advantage persists when "
        "two of four sites are corrupted (1.52×) and decays as they approach "
        "a majority. Holding the corrupted fraction at 25% and per-client "
        "data at 1,000 images, the advantage is flat from four to "
        "twenty-four hospitals (1.29× to 1.65×, no trend in K, all "
        "significant); it decays "
        "only when a fixed corpus is divided among more clients, so the "
        "binding constraint is per-client sample size rather than "
        "federation size. On NIH "
        "ChestX-ray14 at 224×224, fourteen findings across four "
        "patient-disjoint centers, the pipeline operates correctly and "
        "AHA-Fed is not worse than the alternatives, but the calibration "
        "advantage seen at 28×28 does not reproduce: over nine seeds the "
        "gap is 7.0% at p = 0.50. One result is negative and reported as "
        "such: AHA-Fed loses to every baseline on binary chest "
        "radiography. Under per-round DP-SGD at the same per-client data "
        "budget as our non-private runs, both aggregators retain usable "
        "accuracy (0.47 against 0.70 non-private) and the calibration "
        "advantage survives: ECE 0.194 against 0.215 at ε = 1.0 over "
        "ten seeds (p = 0.006), for a 2.2% accuracy cost that also "
        "reaches significance. An earlier sweep at a third of the data "
        "collapsed to chance, which we report because the difference is "
        "instructive. The negative result has a measurable cause we "
        "turn "
        "into a deployment test, the quality term helps only when "
        "corruption shifts local loss further than ordinary differences "
        "between healthy sites do, computable from one training round. "
        "The ratio orders all three corpora by outcome, 2.37 on "
        "PathMNIST, 1.15 on NIH, 0.46 on PneumoniaMNIST; and the NIH "
        "value was computed after that result was measured. "
        "AHA-Fed adds one scalar per client per round, so bandwidth "
        "matches FedAvg, and it composes with Opacus DP-SGD. The framework "
        "and every run artifact behind these numbers are released."
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
    add_paragraph(doc,
        "Federated aggregation rules that reweight hospitals by an estimate "
        "of their data quality are a standard response to unreliable "
        "annotation at one site. The literature reports them as "
        "improvements over volume weighting, but not the conditions under "
        "which the improvement holds, which leaves a practitioner unable "
        "to tell in advance whether such a rule will help their federation "
        "or quietly cost them accuracy.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "This paper answers that question for one such rule. We find the "
        "advantage is real but narrow. It requires a corrupted site: on a "
        "clean federation volume weighting is better. It requires enough "
        "data at each site: with 1,000 images per hospital the reduction "
        "in calibration error holds from four hospitals to twenty-four, "
        "and fades only when a fixed corpus is divided among more of "
        "them. "
        "It survives two corrupted sites of four but not three. And it "
        "did not reproduce when we moved from "
        "28×28 images to full-resolution chest radiographs. Each boundary "
        "is measured over ten seeds with paired significance tests, and we "
        "report the cases that went against the method as prominently as "
        "those that did not.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The practically useful part is that the boundary is predictable. "
        "The quality signal can only separate a corrupted site when "
        "corruption moves local training loss further than ordinary "
        "differences between healthy sites do. That ratio is computable "
        "from a single round of ordinary federated training, before "
        "choosing an aggregation rule at all: it is 2.37 on the corpus "
        "where the method works, and 0.46 on the one where it fails. A "
        "practitioner can therefore run one round, compute one number, and "
        "know whether quality-aware weighting has anything to work with.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "1.1 Background and motivation", level=2)

    intro = [
        "Deep neural networks have transformed medical imaging over the "
        "past decade, achieving radiologist-level performance on an "
        "expanding catalogue of clinical tasks: chest-radiograph triage "
        "[10, 25], diabetic-retinopathy screening, brain-tumour "
        "segmentation [24], histopathology grading [28], dermatology "
        "classification, and pneumonia detection. The shift from "
        "hand-crafted features to learned representations has been "
        "accompanied by an order-of-magnitude growth in the size of "
        "the training datasets that drive these models, modern "
        "chest-X-ray foundation models are now pre-trained on hundreds "
        "of thousands to millions of labelled studies [23]. The "
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
        "of partners, a single multi-site collaboration can spend "
        "twelve to twenty-four months solely on data-sharing paperwork "
        "before any model is trained. Privacy-preserving collaborative "
        "learning has therefore moved from a research curiosity to an "
        "operational necessity. Federated learning (FL) [18, 11] is the "
        "leading framework: each institution keeps its data strictly "
        "on-premise, performs local training rounds, and exchanges only "
        "model updates with a central aggregator. Federated training "
        "has been demonstrated at multi-institutional scale for COVID-19 "
        "outcome prediction across twenty centres [5], rare-cancer "
        "boundary detection across seventy-one centres in six continents "
        "[22], multi-site image segmentation [17], multi-site brain MRI "
        "[24], and retinal disease classification, with predictive "
        "performance rivalling that of centralised training in many "
        "settings.",
    ]
    for para in intro:
        add_paragraph(doc, para, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                      first_line_indent=0.5, space_after=6)

    add_figure(doc, FIGS / "fig_motivation.png",
               "Figure 1: The paper in three panels. (a) On PathMNIST with "
               "one of four hospitals corrupted, quality-aware weighting "
               "lowers calibration error from 0.119 to 0.097 over ten seeds "
               "(bars are means, whiskers one standard deviation). (b) The "
               "benefit is predicted by a diagnostic computable from a "
               "single training round: the ratio between the corruption "
               "signal and the spread among healthy clients orders all "
               "three corpora by outcome, and a ratio below one means no "
               "benefit. (c) The limit is per-client data, not federation "
               "size: holding 1,000 images per hospital the advantage is "
               "flat to twenty-four sites (band spans the series; r = +0.11, "
               "no trend in K), while dividing a fixed corpus among "
               "more hospitals erodes it.")

    add_heading(doc, "1.2 Three coupled obstacles in clinical FL", level=2)

    obstacles_paras = [
        "Yet the reported successes obscure a pervasive failure mode "
        "that surfaces whenever federations move beyond the highly "
        "curated proof-of-concept regime. FedAvg [18], the canonical "
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
        "differences and can drop by ten or more points of area under the "
        "receiver operating characteristic curve (AUROC) across "
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
        "labels, a small academic centre that contributes a "
        "disproportionate fraction of the federation's data because of "
        "an enthusiastic principal investigator, but whose labels were "
        "extracted by an outdated rule-based system, is allowed to "
        "drag the global model in its direction at every round. "
        "Existing robust aggregators address adjacent symptoms but "
        "not the underlying cause. FedProx [15] adds a proximal term "
        "that limits client drift; FedBN [16] keeps batch-normalisation "
        "parameters local; SCAFFOLD [12] introduces control variates "
        "that correct gradient drift. None of these methods evaluate "
        "client quality at all; they treat every client as equally "
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
        "probabilities, for triage prioritisation, for second-reader "
        "alerts, for downstream Bayesian uncertainty pipelines, and "
        "miscalibrated probabilities are clinically dangerous in a "
        "way that miscalibrated point predictions are not. A model "
        "that is wrong but knows it is uncertain can defer to a human; "
        "a model that is confidently wrong cannot. Prior work [7] "
        "has documented that even high-AUROC federated chest-X-ray "
        "classifiers can exhibit Expected Calibration Errors (ECE) "
        "exceeding fifteen percent, and that this miscalibration is "
        "exacerbated rather than corrected by FedAvg under non-independent "
        "and identically distributed (non-IID) "
        "data. The dominant evaluation tradition in FL papers, "
        "reporting only accuracy and AUROC, therefore misses the "
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
        "inversion attacks [33] have repeatedly recovered training "
        "images, partial labels, and identifying metadata from shared "
        "model updates, sometimes from a single round of training. "
        "Membership inference attacks can determine whether a "
        "particular patient's record contributed to the federation. "
        "These attacks are not theoretical: in regulated clinical "
        "deployments they constitute a privacy breach equivalent to "
        "an un-authorised data transfer. Modern compliance therefore "
        "requires formal (ε, δ)-Differential Privacy [1, 30] "
        "accounting on every client's local training round, with "
        "Rényi-DP composition across rounds and clients. Adding "
        "differentially private stochastic gradient descent (DP-SGD) "
        "on top of FedAvg, however, exacerbates exactly the "
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
        ", data volume n_k, total-variation distance D_k between the "
        "client's empirical label prior and the across-client "
        "consensus, and a self-supervised quality signal q_k derived "
        "from the client's mean local training loss, combined in "
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

        "We make five contributions. (i) A characterisation of when "
        "quality-aware weighting helps. The advantage is not uniform: it "
        "appears when a site is corrupted and disappears when none is, it "
        "holds from four hospitals to twenty-four while each keeps "
        "1,000 images and fades only when a fixed corpus is divided "
        "among more of them, it survives two "
        "corrupted sites of four but not three, and it does not reproduce "
        "at clinical resolution. We map each boundary with ten seeds and "
        "paired tests rather than asserting a general improvement. "
        "(ii) A diagnostic that predicts the boundary in advance: the ratio "
        "between the corruption signal and the baseline spread in local "
        "loss, computable from one round of ordinary federated training "
        "before committing to an aggregation rule (Section 5.7). It "
        "orders all three corpora by outcome, including one whose result "
        "was measured before the ratio was computed there, and "
        "it motivated a variant that recovers the discrimination that "
        "failure costs, though not the calibration. "
        "(iii) AHA-Fed itself: a heterogeneity- and quality-aware rule that "
        "strictly generalises FedAvg, admits a closed-form weight "
        "expression, introduces no auxiliary network, requires one extra "
        "scalar of communication per client per round, and composes with "
        "per-client DP-SGD without weight-bias artefacts. (iv) A "
        "convergence guarantee: the softmax weights are provably "
        "non-degenerate under bounded client sizes, distances and quality "
        "signals, so the rule inherits the standard FedAvg rate rather than "
        "requiring a separate analysis (Section 3.9). (v) A reproducibility "
        "kit: a seeded multi-run sweeper, per-run JSON manifests, loaders "
        "for PathMNIST and PneumoniaMNIST [28] as well as full-resolution "
        "CheXpert and NIH ChestX-ray14, unit tests for every aggregator and "
        "privacy hook, and a script that re-checks every numeric claim in "
        "this paper against the stored run artifacts. Every result reported "
        "here is on real medical imaging, and the framework is released so "
        "any clinical collaboration can reproduce or extend it.",
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
        "is corrupted, which is what the design predicts. Three results "
        "bound the method rather than support it: the advantage fades "
        "once a fixed corpus is divided among more than twelve clients, "
        "AHA-Fed loses to every baseline on binary chest radiography, and "
        "the calibration advantage does not reproduce at clinical "
        "resolution. Section 5.7 shows the second of these has a "
        "measurable cause that a practitioner can test before deploying.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The remainder of the paper is organised as follows. Section 2 "
        "reviews the literature and contrasts AHA-Fed with nineteen recent "
        "methods (Table 1). Section 3 derives the rule, gives the training "
        "algorithm, and proves in Section 3.9 that the softmax weights are "
        "bounded away from zero, the property that places the method inside "
        "the standard FedAvg convergence rate. Section 4 specifies the "
        "protocol. Section 5 reports thirteen experiments, Section 6 ablates "
        "each term, and Section 7 concludes.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2. Related Work", level=1)
    add_paragraph(doc,
        "We group the related work into four areas: aggregation rules and "
        "how they handle statistical heterogeneity (§2.1), robustness to "
        "client-side label noise (§2.2), privacy, personalisation and "
        "clinical deployment (§2.3), and a comparison against nineteen "
        "recent methods along six dimensions (§2.4). The thesis developed "
        "across them is that no existing method jointly addresses the "
        "heterogeneity, noise, calibration, and privacy challenges that "
        "co-occur in real federated medical imaging, which is the gap "
        "AHA-Fed fills.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.1 Aggregation rules and statistical heterogeneity", level=2)
    add_paragraph(doc,
        "McMahan et al. [18] introduced Federated Averaging (FedAvg), "
        "the canonical aggregation rule that weights each client's "
        "update by its local sample count. The original analysis "
        "assumed independent and identically distributed client data, "
        "and FedAvg's simplicity, one round of local SGD followed by "
        "a volume-weighted average at the server, has made it the "
        "default starting point for almost all subsequent FL methods. "
        "Subsequent surveys [11, 19] formalise the broader design "
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
        "we adopt in this paper, a synchronous round-robin server-"
        "broadcast / client-update / server-aggregate cycle, is the "
        "cross-silo standard. Asynchronous variants [11] reduce "
        "straggler latency but introduce staleness and complicate DP "
        "accounting; we treat them as orthogonal extensions.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Statistical heterogeneity in FL is not a single phenomenon "
        "but a small taxonomy. Following Kairouz et al. [11] we "
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
        "Dirichlet-α partitioning protocol [13, 29] used in this "
        "paper provides a knob to interpolate between IID and "
        "extreme label-prior skew; we sweep this parameter from 0.0 "
        "to 0.9 in Section 5.4.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Quantifying heterogeneity is itself a non-trivial measurement "
        "problem. Total-variation distance, Jensen–Shannon divergence, "
        "and earth-mover distance have all been used as scalar "
        "summaries [29, 32]. AHA-Fed adopts total-variation distance "
        "between each client's empirical label prior and the across-"
        "client consensus because it is bounded in [0, 1], easy to "
        "compute once per training run, and admits a clear interpretation "
        "as the fraction of labels that would need to be relabelled to "
        "make a client's distribution match the consensus. We discuss "
        "alternative distance measures and their effect on AHA-Fed's "
        "behaviour in Section 6.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "FedProx [15] adds an L2 proximal regulariser between the "
        "local and global weights to limit client drift during local "
        "training. The proximal term is principled and provably "
        "improves convergence on bounded-dissimilarity objectives, "
        "but it operates entirely in parameter space and does not "
        "discriminate between clients on the basis of data quality "
        "or distributional shift, a corrupted client whose updates "
        "drag the global model is still given equal aggregation "
        "weight, only with a slightly less aggressive local step. "
        "FedBN [16] keeps batch-normalisation parameters local and "
        "only aggregates the convolutional weights, which is "
        "particularly relevant in medical imaging where batch-normalisation "
        "(BN) statistics "
        "are scanner-specific; FedBN variants [16] address "
        "feature shift more broadly. SCAFFOLD [12] introduces control "
        "variates that correct gradient drift in non-IID regimes at "
        "the cost of doubling the per-round communication. "
        "Logits calibration [31] reweights the local objective "
        "to align local and global stationary points, recovering "
        "centralised-training performance under bounded heterogeneity. "
        "FedDisco [29] takes a step closer to AHA-Fed's design by "
        "using label-distribution discrepancy directly as a per-client "
        "weighting signal, clients further from the consensus are "
        "downweighted. This is the closest precedent to AHA-Fed's β "
        "term, but FedDisco does not incorporate any quality signal "
        "and so is vulnerable to the noisy-client failure mode: a "
        "noisy client whose label prior happens to match the consensus "
        "is still trusted at full weight. Our experiments confirm "
        "this failure empirically (Section 5.6).",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.2 Robustness to client-side label noise", level=2)
    add_paragraph(doc,
        "Robust FL has historically focused on Byzantine attackers, "
        "adversarial clients that submit arbitrarily corrupted updates "
        "[33], rather than the more clinically realistic case of "
        "well-meaning clients with noisy labels. The Byzantine "
        "threat model motivates median-based or trimmed-mean "
        "aggregators, which are computationally efficient but "
        "discard a constant fraction of clients regardless of whether "
        "they are actually malicious. In a four-hospital federation "
        "with one noisy client, this can mean discarding 25% of the "
        "data even when only one or two clients are problematic. "
        "FedCorr [27] identifies noisy clients on the basis of an "
        "supplied label-noise estimate, which is rarely available in "
        "practice, hospitals do not annotate their own data with "
        "honest noise rates. Robust-FedAvg variants [13] use heavy-"
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
        "validation set, properties that are essential for "
        "deployment in regulated clinical environments where any "
        "additional data exposure would require fresh data-use "
        "agreements.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "When per-site distributions are too heterogeneous for a "
        "single global model to serve all clients well, personalised "
        "FL retains a per-client component. FedRep [4] keeps a shared "
        "representation backbone and trains a per-client classifier "
        "head; pFedMe [6] uses Moreau envelopes to balance the "
        "global model and per-client adaptation. Ditto [14] casts "
        "personalisation as multi-task learning, trading global "
        "accuracy against per-client fairness. Auto-FedRL [8] learns the "
        "federation hyperparameters themselves automatically, "
        "reducing the burden of manual tuning across heterogeneous "
        "sites. Personalised FL is orthogonal to AHA-Fed: the "
        "AHA-Fed aggregation rule produces a single global model, "
        "and a personalised head can be trained on top of it "
        "without modification. We treat composing AHA-Fed with "
        "FedRep / pFedMe / Ditto as future work in Section 7.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.3 Privacy, personalisation, and clinical deployment", level=2)
    add_paragraph(doc,
        "Plain FL provides only an informal privacy guarantee: "
        "gradient inversion attacks [33] have demonstrated that "
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
        "Opacus [30] provides a PyTorch implementation of "
        "DP-SGD with tight Rényi-DP accounting and supports per-"
        "client privacy budgets. Hybrid approaches add secure "
        "aggregation [2] to additionally hide individual client "
        "updates from the central server: the server learns only "
        "the federation-wide sum, not the per-client contributions. "
        "The DP-SGD literature [1, 30] maps the privacy-utility "
        "tradeoff on chest X-ray classification under varying ε "
        "budgets, generally finding that DP costs ten to thirty "
        "AUROC points at ε ≤ 1.0, a substantial price for clinical "
        "deployment. Our experiments in Section 5.11 are consistent "
        "with this finding: on our 9-class PathMNIST federation per-round "
        "DP-SGD at ε = 1.0 costs roughly a third of accuracy and eight "
        "points of AUROC, while the calibration advantage survives over "
        "ten seeds (0.194 against 0.215, p = 0.006). This is "
        "consistent with the post-"
        "processing immunity of differential privacy: the AHA-Fed "
        "aggregator is applied to (already-private) client updates, "
        "so the (ε, δ) guarantee at the client carries through to "
        "the global model unchanged.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Federated learning has moved from method papers to clinical "
        "deployments over the past five years. Sheller et al. [24] "
        "established in 2022 that FL trained on multi-institutional "
        "brain-tumour MRI matches centralised training when client "
        "heterogeneity is moderate; this paper, more than any other, "
        "is responsible for the current confidence in FL among "
        "clinical collaborators. Pati et al. [22] scaled FL across "
        "seventy-one centres in six continents for rare-cancer "
        "boundary detection, the largest FL collaboration to date "
        "by site count, and a proof of feasibility for global "
        "federations. Dayan et al. [5] used FL to predict COVID-19 "
        "clinical outcomes across twenty institutions during the "
        "pandemic, demonstrating that FL can be assembled rapidly "
        "in response to public-health emergencies. Rieke et al. [23] "
        "survey the clinical prospects of federated "
        "digital health. Recent reviews [11] and surveys [19, 32] "
        "map the deployment landscape and identify open problems. "
        "Specifically clinically focused work includes Chen et al. [3] and "
        "Liu et al. [17] for multi-site medical-image segmentation, "
        "FedIIC [26] for "
        "class-imbalanced medical-image classification, Xu et al. [27] "
        "for federated learning under label noise. "
        "Ogier du Terrail et al. [20] provide a cross-silo "
        "healthcare benchmark suite. None of these methods "
        "explicitly "
        "reweight clients by an internally-derived data-quality "
        "signal, which is the gap AHA-Fed fills.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The Expected Calibration Error (ECE) of a classifier "
        "measures the gap between its predicted confidences and its "
        "actual accuracy in equal-mass confidence bins. In the "
        "centralised non-FL setting, calibration of deep networks "
        "has been studied since Guo et al. (2017) [7, 21] and is known to "
        "degrade with overparameterisation, label noise, and "
        "distribution shift, exactly the conditions that prevail "
        "in federated medical imaging. Prior work [7] is among the "
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
        "logits-calibration method [31] takes a "
        "different approach by post-hoc temperature-scaling the "
        "global model; this is complementary to AHA-Fed's "
        "aggregation-level intervention and the two could be "
        "composed.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "2.4 Positioning: comparison with nineteen recent methods",
                level=2)
    add_paragraph(doc,
        "We synthesise the discussion of §§2.1–2.3 in Table 1, which "
        "contrasts AHA-Fed with nineteen federated-learning methods "
        "spanning 2016–2026 along six dimensions that matter for "
        "clinical deployment: year of publication, whether the method "
        "is heterogeneity-aware, whether it explicitly handles client "
        "noise, whether it is compatible with formal DP-SGD, whether "
        "it reports calibration metrics, and whether it has been "
        "evaluated on medical-imaging data. Of the nineteen methods "
        "surveyed, only AHA-Fed simultaneously delivers a non-IID-"
        "aware aggregation rule (volume + label-prior distance), an "
        "internally-derived quality-aware client weighting (loss-"
        "based q_k), formal DP-SGD compatibility (Opacus integration), "
        "and clinical-grade calibration reporting (ECE as a primary "
        "metric). Several recent methods address two of these "
        "dimensions, for instance DP-SGD [1] addresses privacy and "
        "medical imaging, and logits calibration [31] addresses it and "
        "medical imaging; but none address all four. The methods "
        "closest in design to AHA-Fed are FedDisco [29] (which "
        "shares the distance term but lacks quality), and FedCorr "
        "[27] (which addresses noise but requires a multi-stage "
        "detection procedure). Both fall short of jointly addressing all four "
        "dimensions and we compare to FedDisco directly in Section "
        "5.6 as the natural empirical baseline against our key design "
        "choice.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # ---------- Literature review table (extended to 18 rows) ----------
    table_data = [
        ["Method", "Yr", "1", "2", "3", "4", "5"],
        ["FedAvg [18]",        "17", "–", "–", "~", "–", "–"],
        ["DP-SGD [1]",         "16", "–", "–", "Y", "–", "–"],
        ["Sheller et al. [24]", "20", "Y", "–", "–", "–", "Y"],
        ["FedProx [15]",       "20", "P", "–", "~", "–", "–"],
        ["SCAFFOLD [12]",      "20", "Y", "–", "~", "–", "–"],
        ["pFedMe [6]",         "20", "Y", "–", "~", "–", "–"],
        ["FedBN [16]",         "21", "P", "–", "~", "–", "P"],
        ["FedRep [4]",         "21", "Y", "–", "~", "–", "–"],
        ["Ditto [14]",         "21", "Y", "P", "~", "–", "–"],
        ["FedDG [17]",         "21", "Y", "–", "–", "–", "Y"],
        ["Rieke et al. [23]",  "20", "P", "–", "P", "–", "Y"],
        ["FedCorr [27]",       "22", "–", "Y", "–", "–", "–"],
        ["Auto-FedRL [8]",     "22", "Y", "–", "–", "–", "Y"],
        ["Logits calib. [31]", "22", "Y", "–", "–", "Y", "–"],
        ["Chen et al. [3]",    "22", "Y", "P", "–", "–", "Y"],
        ["FLamby [20]",        "22", "Y", "–", "P", "–", "Y"],
        ["FedDisco [29]",      "23", "Y", "–", "~", "–", "–"],
        ["FedIIC [26]",        "23", "Y", "P", "–", "–", "Y"],
        ["AHA-Fed (ours)",     "26", "Y", "Y", "Y", "Y", "Y"],
    ]
    add_table_caption(doc,
        "Table 1: Nineteen federated-learning methods, 2016 to 2026, "
        "against the five capabilities this paper combines. "
        "1 heterogeneity-aware, 2 client-noise-aware, 3 DP-SGD-ready, "
        "4 calibration-reporting, 5 medical-imaging tested. "
        "Y is yes, P partial, ~ indirect and – no. Yr is the year of "
        "publication. Only AHA-Fed carries all five."
    )
    make_table(doc, table_data,
               highlight_row_pred=lambda i, row: row[0].startswith("AHA-Fed"),
               header_font_size=10, body_font_size=9.0)
    add_post_table_spacing(doc)

    # ==================== 3. METHODOLOGY ====================
    add_heading(doc, "3. Methodology", level=1)

    add_heading(doc, "3.1 Problem setting", level=2)
    add_paragraph(doc,
        "Let K hospitals each hold a private dataset D_k with n_k samples "
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
        "client log-score, where the quality term is evaluated as "
        "log(q_k + ε) with ε = 10⁻⁶ guarding against a zero argument:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq4_score.png", "(4)", width_in=5.4)
    add_paragraph(doc,
        "Aggregation weights are then obtained by a numerically stable "
        "softmax, subtracting the largest score s⋆ = max_j s_j before "
        "exponentiating:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_equation_image(doc, "eq5_softmax.png", "(5)", width_in=5.6)
    add_paragraph(doc,
        "The weights are positive and sum to one by construction, so the "
        "server forms the next global state as their convex combination "
        "of the per-client states:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
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
        "interpretation, α governs anti-volume-collapse, β penalises "
        "outlier centers in label space, and γ rewards low-loss clients. "
        "Figure 2 shows how the three signals combine.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_figure(doc, FIGS / "fig_aha_concept.png",
               "Figure 2: The weighting rule, and the rule at work. "
               "(a) The three signals enter a log-space score that is "
               "softmax-normalised into a weight. (b) The quality "
               "signal on the PathMNIST federation with one of four "
               "hospitals corrupted: the clean sites separate from "
               "the corrupted one within a few rounds. (c) The "
               "weights that follow, with the corrupted site falling "
               "from near-uniform to 0.08 while the clean sites rise "
               "above 0.25. Both panels are means over ten seeds.")

    add_heading(doc, "3.4 Relative quality: removing the difficulty term",
                level=2)
    add_paragraph(doc,
        "The quality signal as defined above conflates two things. A client's "
        "local loss is high both when its labels disagree with its inputs "
        "(the corruption we want to detect) and when its slice of the data is "
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
        "against its own first-round quality, forming q̃_k as the ratio of "
        "q_k to its own first-round value, and "
        "substitutes q̃_k for q_k in the score. Writing the local loss as a "
        "sum of a client-specific difficulty term and a corruption term, the "
        "difficulty term is present in both numerator and denominator and "
        "largely cancels, leaving the component that changes as training "
        "proceeds. A site that starts hard and stays hard is no longer "
        "penalised; a site whose loss fails to fall because its labels are "
        "wrong still is. The change costs nothing at runtime (one stored "
        "scalar per client) and reduces to the absolute rule when every "
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
        "or patient-level metadata leaves a hospital, only the three "
        "scalars and the model delta are exchanged. Optional secure "
        "aggregation [2] further hides individual client deltas from "
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
        "norm C and Gaussian noise scale σ chosen by the Opacus [30] privacy "
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
        "where A(B_m) is the empirical accuracy and C(B_m) the mean "
        "predicted confidence in bin m [21]. ECE is the most clinically "
        "actionable metric for triage and decision-support deployments: a "
        "model that is confidently wrong on rare-class cases is more "
        "dangerous than a less-accurate but well-calibrated model.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "3.8 Algorithm", level=2)
    add_paragraph(doc,
        "Algorithm 1 states the complete training loop. Each round the "
        "server broadcasts the global model, every client trains "
        "locally and returns its update together with three scalars, "
        "and the server forms the softmax weights of Equation (5) and "
        "aggregates.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    ALGO_ROWS = [
        ("Input:", "K hospitals holding local datasets D_k, total rounds "
                   "T, and hyperparameters α, β and γ."),
        ("1", "Server initialises θ⁰; computes label priors π_k and "
              "the consensus prior."),
        ("2", "for round t = 0 to T-1 do"),
        ("3", "    Server broadcasts the current θ to all clients."),
        ("4", "    for each hospital k = 1 to K in parallel do"),
        ("5", "        Run local DP-SGD for E epochs to obtain θ_k."),
        ("6", "        Compute the local loss L_k and quality q_k by (3)."),
        ("7", "        Send the update, q_k and n_k to the server."),
        ("8", "    end for"),
        ("9", "    Server: s_k = α log n_k − β D_k + "
              "γ log(q_k + ε)."),
        ("10", "    Server: w_k = softmax(s_1, ..., s_K)."),
        ("11", "    Server: aggregate the client states with weights w_k."),
        ("12", "end for"),
        ("Output:", "Global model θᵀ with a per-client "
                    "(ε, δ)-DP guarantee."),
    ]
    add_algorithm(doc, "Algorithm 1  AHA-Fed federated training loop",
                  ALGO_ROWS)

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
        "buys and, equally important, what it does not.",
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
        "the ranges in (A2)–(A4), not on the round.",
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
        "R = 20 and q_min = 0.22 it gives w_min ≥ 7.2 × 10⁻⁷ at K = 4 and "
        "1.1 × 10⁻⁷ at K = 20, whereas the smallest weight observed in any "
        "of our runs is 0.0035; the terms do "
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
        "[18], FedProx [15] (μ = 0.01), FedBN [16], and FedDisco [29]. "
        "Every experiment runs on real medical imaging, PathMNIST and "
        "PneumoniaMNIST from MedMNIST v2, federated into K hospitals by "
        "Dirichlet partitioning over the label space, with label noise "
        "injected at one hospital to model annotation corruption. Each run "
        "is seeded and writes a JSON manifest of its configuration and "
        "per-round metrics, so every number in this paper can be traced to "
        "the artifact that produced it; a verification script that re-checks "
        "the claims against those artifacts ships with the framework. "
        "A loader for full-resolution CheXpert is released alongside but is "
        "not used in the reported results; the NIH ChestX-ray14 loader "
        "drives the clinical-resolution experiments of Section 5.10.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "4.1 Datasets", level=2)
    add_paragraph(doc,
        "Every number reported in this paper comes from real medical imaging "
        "data. We use two corpora from MedMNIST v2 [28]: PathMNIST, a nine-"
        "class colorectal-pathology dataset, as the primary benchmark, and "
        "PneumoniaMNIST, a binary chest-radiograph dataset, as a second "
        "modality. Both are released under permissive licences and require no "
        "data-use agreement, so every result here is directly reproducible. "
        "NIH ChestX-ray14 [25] supplies the clinical-resolution experiments "
        "of Section 5.10 at 224×224; a CheXpert [10] loader is released "
        "with the framework but is not used in the reported results. "
        "Table 2 "
        "summarises the three corpora and their federated partitions, "
        "and Figure 4 shows real PathMNIST samples alongside the "
        "per-hospital label priors the partitioning induces.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_dataset.png",
               "Figure 4: PathMNIST federation, real samples and the "
               "per-hospital label priors induced by Dirichlet partitioning.")

    # Dataset table
    # Eleven properties across three datasets does not fit an IEEE
    # column with a property per row: "Per-center class prior shift"
    # cannot break. Transposed, each dataset is one row and the shared
    # properties (Dirichlet split, no DUA, noise range) move to the
    # caption, which states them once instead of three times.
    ds_data = [
        ["Dataset", "Modality", "Size", "Labels", "Used for"],
        ["PathMNIST", "Colorectal histopathology", "107,180 at 28×28",
         "9 classes", "All headline results"],
        ["PneumoniaMNIST", "Chest radiograph", "5,856 at 28×28",
         "2 classes", "Second modality"],
        ["NIH CXR14", "Chest radiograph", "112,120 at 224×224",
         "14 findings", "Section 5.10"],
    ]
    add_table_caption(doc,
        "Table 2: Real datasets used in this paper. No synthetic or "
        "simulated imagery appears anywhere. PathMNIST and "
        "PneumoniaMNIST come from MedMNIST v2 [28] and are split "
        "Dirichlet over classes with label noise ρ ∈ [0, 0.7] "
        "injected at one client; NIH ChestX-ray14 [25] comes from the "
        "NIH Clinical Center, is split patient-disjoint, and carries "
        "its own real annotation noise. None requires a data-use "
        "agreement.")
    add_bullet_run(doc, "Model. ",
                   "MedCNN (3 convolutional blocks with GroupNorm, ≈ 240K "
                   "parameters) for the 28×28 MedMNIST corpora; DenseNet-121 [9] "
                   "is wired up for the full-resolution loaders.")
    add_bullet_run(doc, "AHA-Fed hyperparameters. ",
                   "α = 1, β = 4, γ = 4, ε_log = 1 × 10⁻⁶ (log stabiliser) "
                   "throughout the PathMNIST experiments. Section 5.7 shows "
                   "these values do not transfer to binary chest radiography, "
                   "where a per-task validation split is required.")
    add_bullet_run(doc, "Metrics. ",
                   "Test cross-entropy, top-1 accuracy, multiclass macro AUROC, "
                   "AUPRC, and Expected Calibration Error (ECE) on top-1 "
                   "confidence; the last is particularly relevant for clinical "
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
        "Figure 5 plots per-round accuracy and calibration on the PathMNIST "
        "federation with 50% label noise at one hospital. Accuracy is not "
        "where the methods differ: both AHA-Fed and FedAvg climb to roughly "
        "0.70 and track each other closely, which is expected since the "
        "corrupted client still supplies a majority of correctly-labelled "
        "images. Calibration separates them. FedAvg's ECE stops improving "
        "once the noisy updates begin to dominate the volume-weighted mean, "
        "whereas AHA-Fed continues to descend as the softmax weights shift "
        "mass away from that client. This pattern, matched discrimination, "
        "divergent calibration, recurs throughout our results and is the "
        "reason we treat ECE rather than accuracy as the primary endpoint.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_convergence.png",
               "Figure 5: PathMNIST, four hospitals, 50% label noise at one "
               "client (seed 42), accuracy and ECE per communication round.")

    add_heading(doc, "5.2 Final performance with error bars", level=2)
    add_paragraph(doc,
        "Figure 6 reports the second modality, PneumoniaMNIST chest "
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
               "Figure 6: PneumoniaMNIST (chest radiography), four "
               "hospitals, final ECE, accuracy and AUROC "
               "(mean ± s.d., 10 seeds).")

    add_heading(doc, "5.3 Robustness to label-noise rate", level=2)
    add_paragraph(doc,
        "We sweep the label-noise rate at one hospital over {0.0, 0.3, 0.5, "
        "0.7}, with ten seeds at each point on PathMNIST (Figure 7). "
        "AHA-Fed attains the lower mean ECE at all four rates, and the "
        "structure of where it does so is the informative part. At "
        "ρ = 0 the two methods are indistinguishable (0.061 vs 0.064, "
        "p = 0.70), with no corrupted client there is nothing for the "
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
        "the seed budget was too small to resolve it, a reminder that in "
        "federated evaluation, where seed variance compounds across "
        "client sampling, partitioning and initialisation, three seeds "
        "resolve very little. The mechanism behind the endpoint is "
        "visible directly in Section 5.5, where the corrupted client is "
        "driven to roughly a quarter of its uniform weight.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_noise_sweep.png",
               "Figure 7: ECE versus label-noise rate at the corrupted "
               "client, PathMNIST (mean ± s.d., 10 seeds) and "
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
        "priors are drawn. The clinically relevant regime, hospitals "
        "that differ substantially but not pathologically, sits where "
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
        "less for a quality-aware rule to correct. Section 2.1 notes that "
        "clinical cross-silo federations typically span four to fifty "
        "sites, so our advantage covers the lower end of that range and not "
        "the upper; we state that plainly rather than implying otherwise.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Two things qualify how limiting this is. First, part of what K = 12 "
        "tests is the mildness of the corruption rather than the size of "
        "the federation: one bad site among twelve is an 8% corrupted "
        "fraction, and raising it to 25% at the same K recovers some of "
        "the advantage (1.20× against 1.01×). The rest is an artifact of "
        "this sweep holding the corpus fixed, which shrinks per-client "
        "data as K grows: Section 5.9 shows the advantage flat from "
        "four to twenty-four hospitals once per-client data is held "
        "constant instead. Second, a practitioner does "
        "not have to guess: the diagnostic of Section 5.7 is computed on "
        "the federation at hand, whatever its size, and reports directly "
        "whether the quality signal has anything to separate. Figure 8 plots "
        "the sweep across both axes.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_het_scale.png",
               "Figure 8: PathMNIST, Dirichlet heterogeneity sweep "
               "(0.0–0.9, 10 seeds per level) and federation-size scaling "
               "(K = 4 to 32, 10 seeds each).")

    add_heading(doc, "5.5 Per-client aggregation weights", level=2)
    add_paragraph(doc,
        "Figure 9 traces the aggregation weights AHA-Fed assigns over the "
        "course of training on PathMNIST with 50% label noise at hospital "
        "four. FedAvg would hold all four at the uniform 0.250, since the "
        "hospitals carry equal volume here. AHA-Fed instead drives the "
        "corrupted hospital down to 0.069 by the final round, roughly a "
        "quarter of uniform, and redistributes that mass across the three "
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
        "better endpoint under label noise, as Section 5.3 reports, it "
        "does not, at the seed count we ran.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_weights.png",
               "Figure 9: AHA-Fed per-client aggregation weights per round "
               ", PathMNIST, ρ = 0.5 at hospital four, seed 42.")

    add_heading(doc, "5.6 Aggregator comparison on PathMNIST", level=2)
    add_paragraph(doc,
        "Sections 5.1–5.5 sweep one factor at a time; this section fixes the "
        "federation and compares all five aggregators head to head on the "
        "PathMNIST colon-histopathology benchmark [28] (89,996 train + "
        "7,180 test images, 9 classes, 28×28 RGB). The dataset is "
        "federated into K = 4 hospitals via Dirichlet partitioning "
        "(heterogeneity = 0.5) with 50% label noise injected at "
        "hospital D. We add FedDisco [29] as a fifth baseline since it "
        "shares AHA-Fed's distance term but lacks the quality term, "
        "this is the natural ablation against our key design choice. "
        "All five aggregators are run for 25 rounds with the MedCNN "
        "backbone (3-conv blocks with GroupNorm, ≈ 240 K parameters) "
        "and ten random seeds. Figure 10 plots the five aggregators across "
        "all four metrics.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_real_pathmnist.png",
               "Figure 10: PathMNIST comparison across five "
               "aggregators (mean ± s.d., 10 seeds).")
    add_paragraph(doc,
        "Table 3 reports the final-round metrics over ten seeds. AHA-Fed "
        "reduces ECE by 19.1% versus FedAvg (0.097 vs 0.119) and by "
        "19.9% versus FedProx (0.097 vs 0.121), while keeping accuracy "
        "and AUROC indistinguishable from the strongest baselines, the "
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
        "tests the attribution directly. All four comparisons survive "
        "Holm–Bonferroni correction across the family of four, which we "
        "state explicitly because the sweeps of Sections 5.4 and 5.8 do "
        "not.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # Six columns of five-character values do not fit an IEEE column.
    # AUROC moves to the caption: it separates the aggregators by
    # 0.011 at most, while the paper's claim is about calibration.
    real_data = [
        ["Method", "Acc", "ECE", "Redn", "p"],
        ["FedAvg [18]",    "0.672", "0.119±0.019", "19.1%", "0.020"],
        ["FedProx [15]",   "0.673", "0.121±0.025", "19.9%", "0.037"],
        ["FedBN [16]",     "0.692", "0.135±0.025", "28.3%", "0.014"],
        ["FedDisco [29]",  "0.681", "0.139±0.030", "30.6%", "0.004"],
        ["AHA-Fed (ours)", "0.701", "0.097±0.018", "—", "—"],
    ]
    add_table_caption(doc,
        "Table 3: PathMNIST across five aggregators, ten seeds. The "
        "reduction and p columns compare each baseline against AHA-Fed "
        "with a paired Wilcoxon signed-rank test over matched seeds. "
        "Macro AUROC separates the aggregators by at most 0.011 "
        "(0.938, 0.946, 0.949, 0.946 and 0.949 in row order).")
    make_table(doc, real_data,
               highlight_row_pred=lambda i, row: row[0].startswith("AHA-Fed"),
               header_font_size=10, body_font_size=10)
    add_post_table_spacing(doc)

    het_data = [
        ["Dirichlet α", "AHA-Fed", "FedAvg", "Redn", "p"],
        ["0.0", "0.090±0.035", "0.135±0.020", "1.50×", "0.010"],
        ["0.3", "0.091±0.019", "0.119±0.027", "1.32×", "0.006"],
        ["0.5", "0.090±0.020", "0.135±0.030", "1.50×", "0.010"],
        ["0.7", "0.082±0.023", "0.138±0.020", "1.69×", "0.002"],
        ["0.9", "0.092±0.025", "0.128±0.049", "1.38×", "0.106"],
        ["Pooled", "0.089", "0.131", "1.47×", "< 10⁻⁵"],
    ]
    add_paragraph(doc,
        "Table 4 reports the same comparison across five levels of "
        "Dirichlet heterogeneity, ten seeds at each.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_table_caption(doc,
        "Table 4: Heterogeneity sweep on PathMNIST (mean ± s.d., 10 seeds "
        "per level). p-values are paired Wilcoxon signed-rank tests over "
        "matched seeds; the pooled row covers all fifty observations. α = 0.0 is near-IID and α = 0.9 strongly skewed; the pooled row is n = 50.")
    make_table(doc, het_data,
               highlight_row_pred=lambda i, row: row[0].startswith("Pooled"),
               header_font_size=10, body_font_size=10)
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "Figure 11 shows the convergence behaviour behind these "
        "endpoints: the calibration gap opens within the first ten "
        "rounds and holds, rather than emerging only at the round "
        "budget we happened to choose.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_real_convergence.png",
               "Figure 11: Multi-seed convergence on PathMNIST "
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
        "of 0.067, a ratio of 2.37, and the corrupted client is ranked "
        "worst in 10 of 10 runs. On PneumoniaMNIST the signal is 0.075 "
        "against a spread of 0.163, a ratio of 0.46, and the corrupted "
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
        "β = 0, γ = 2 instead, which scores 0.211 ± 0.017 on test, worse "
        "than every baseline. We report the validation-selected figure "
        "and note the other only to quantify how much test-set selection "
        "can flatter a method: a 1.7× apparent improvement that reverses "
        "under a correct protocol.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Both of those corpora are ones the diagnostic was constructed to "
        "explain, so on their own they do not test it. NIH ChestX-ray14 "
        "does: it is a third corpus at clinical resolution, and its "
        "calibration result, a 7.0% advantage that does not reach "
        "significance over nine seeds (Section 5.10), was measured "
        "before we computed the ratio there. Applying the same "
        "computation to the corrupted NIH federation gives a signal of "
        "0.0097 against a spread of 0.0084, a ratio of 1.15, with the "
        "corrupted center ranked worst in 9 of 9 runs.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "That is the value a weak but correctly directed result should "
        "have. The corrupted site is identified every time, so the signal "
        "is real; but at 1.15 it barely exceeds the variation among "
        "healthy centers, leaving little margin for the reweighting to "
        "convert into calibration. Ordered by the diagnostic, the three "
        "corpora are PathMNIST 2.37, NIH 1.15, PneumoniaMNIST 0.46, and "
        "ordered by outcome they are a 1.47× ECE reduction at p < 10⁻⁵, "
        "a 1.07× reduction at p = 0.50, and a loss to every baseline. "
        "The ranking is the same in both, which is the strongest evidence "
        "we have that the diagnostic measures what it claims to. Three "
        "points cannot establish a quantitative threshold, and we do not "
        "propose one; what they support is the ordering and the reading "
        "that a ratio near unity predicts a null rather than a reversal.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The practical value of this is that the ratio is computable from a "
        "single round of ordinary federated training, before committing to "
        "an aggregation rule. A federation whose clean clients already "
        "differ in local loss by more than corruption would move it is a "
        "federation where AHA-Fed's quality term has no usable signal, "
        "and volume weighting is the safer choice. This also predicts the "
        "NIH result of Section 5.10, where the ratio is favourable and "
        "AHA-Fed leads once a site is corrupted, and it is a sharper "
        "statement than 'the hyperparameters did not transfer': the "
        "failure is a property of the federation, not of the tuning. "
        "Section 7.1 records the diagnostic as a deployment prerequisite. "
        "Table 5 gives the underlying transfer result.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    transfer_data = [
        ["Configuration", "Selected on", "Test ECE", "Beats baselines?"],
        ["β = 8, γ = 1", "test split (invalid)", "0.123 ± 0.056", "Yes; but not a valid protocol"],
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
        "against its own starting quality should recover the signal; this is "
        "the relative variant of Section 3.4. We evaluate it against the "
        "absolute rule on both corpora at twenty seeds, with everything else "
        "held fixed. Because this is a design choice rather than a reported "
        "result, the comparison is made on the validation split; "
        "Table 6 reports it.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    relq_data = [
        ["Corpus", "Metric", "Relative q̃", "Absolute q", "p"],
        ["PneumoniaMNIST", "ECE", "0.123", "0.142", "0.105"],
        ["(binary)", "Acc", "0.811", "0.782", "0.049"],
        ["", "AUROC", "0.930", "0.912", "0.006"],
        ["PathMNIST", "ECE", "0.057", "0.057", "0.784"],
        ["(9-class)", "Acc", "0.620", "0.617", "1.000"],
        ["", "AUROC", "0.932", "0.932", "0.870"],
    ]
    add_table_caption(doc,
        "Table 6: Relative versus absolute quality signal, twenty seeds, "
        "validation split. Paired Wilcoxon signed-rank tests over matched "
        "seeds; only the AUROC gain survives Holm–Bonferroni across the "
        "three PneumoniaMNIST metrics.")
    make_table(doc, relq_data, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: False)
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "The variant acts exactly where the diagnostic says it should, but "
        "not on every metric. On PneumoniaMNIST, the task with the "
        "unfavourable ratio, it improves all three, significantly for "
        "AUROC (0.930 against 0.912, p = 0.006, ahead on 15 of 20 "
        "seeds) and marginally for accuracy (p = 0.049). ECE improves by "
        "13.7% in the mean (0.123 against 0.142) but does not reach "
        "significance (p = 0.105). Under Holm–Bonferroni across the "
        "three metrics only the AUROC gain survives. On PathMNIST, "
        "where the ratio was already favourable and the absolute rule "
        "worked, the variant changes nothing measurable (p = 0.78, "
        "1.00, 0.87). That selectivity is the point: a modification "
        "that improved both corpora would be hard to attribute to the "
        "mechanism we claim, whereas one acting only where the "
        "diagnostic predicts a problem is evidence the diagnosis was "
        "right.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The calibration result deserves a note on how it moved. At ten "
        "seeds ECE stood at p = 0.065, close enough that we ran ten "
        "more to settle it. It went the wrong way, to p = 0.105, which "
        "is what an apparent effect made largely of seed variance does "
        "when given more seeds. We report the twenty-seed figure rather "
        "than the ten-seed one that read better, and note the sequence "
        "for the same reason we note the NIH one in Section 5.10: a "
        "borderline p-value at a modest seed budget is not weak "
        "evidence of an effect, it is an absence of evidence either "
        "way.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Selection was made on validation, so we evaluate the chosen variant "
        "once on the held-out test split. It replicates: accuracy rises from "
        "0.628 to 0.704 (p = 0.012) and AUROC from 0.888 to 0.906 "
        "(p = 0.037), with ECE improving from 0.219 to 0.192 but not reaching "
        "significance (p = 0.28). We therefore report the variant as "
        "improving discrimination on this task and as not improving "
        "calibration, the metric this paper otherwise treats as "
        "primary. That is a partial fix, and calling it one matters: "
        "the diagnostic of this section identifies why AHA-Fed fails "
        "on a binary task, and the variant recovers the "
        "discrimination that failure costs, but the calibration "
        "advantage that motivates the method does not return.",
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
        "at 50%, ten seeds each. Table 7 reports the sweep.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # "Weight on corrupted" and its "0.084 (uniform 0.250)" values are
    # the widest content in the paper; carried in the caption instead,
    # where the comparison against uniform reads more directly anyway.
    multi_data = [
        ["Sites", "Ours", "Base", "Redn", "p"],
        ["1 of 4", "0.085", "0.126", "1.49×", "0.010"],
        ["2 of 4", "0.117", "0.178", "1.52×", "0.027"],
        ["3 of 4", "0.197", "0.227", "1.15×", "0.131"],
        ["Pooled", "0.133", "0.177", "1.33×", "< 10⁻³"],
    ]
    add_table_caption(doc,
        "Table 7: PathMNIST with an increasing number of corrupted "
        "hospitals, ten seeds each; the pooled row is n = 30. AHA-Fed "
        "Ours is AHA-Fed and Base is FedAvg; both columns are ECE. The total weight AHA-Fed places on "
        "the corrupted sites at the last round is 0.084, 0.247 and 0.557 "
        "against uniform shares of 0.250, 0.500 and 0.750, so the rule "
        "down-weights them in every case but by a shrinking margin as "
        "they approach a majority.")
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
        "drives it to 0.084 against a uniform 0.250, roughly a third. With "
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

    add_heading(doc,
                "5.9 What the scale limit actually is",
                level=2)
    add_paragraph(doc,
        "Sections 5.4 and 5.8 vary the number of hospitals and the number "
        "of corrupted ones, and both move a third quantity with them: the "
        "fraction of the federation's data carrying unreliable labels. An "
        "earlier draft read the constraint as one on that fraction. We "
        "tested it by holding the fraction at 25% and moving the client "
        "count to 8, 12 and 16 at ten seeds each, and the advantage decayed "
        ": 1.32×, 1.20× and 0.97× against 1.46× at K = 4, which we read as "
        "evidence that federation size binds independently.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "That reading was also wrong, and the design is why. To isolate "
        "federation size those runs hold the total corpus near 4,000 "
        "images, so per-client data falls as K grows: sixteen sites get "
        "250 images each. Client count and per-client sample size are "
        "perfectly anti-correlated, and the sweep cannot say which one "
        "drives the decay. We therefore repeated it with per-client data "
        "held at 1,000 images, the same as the K = 4 experiments, "
        "letting the corpus grow with the federation. Table 8 reports "
        "both.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # Six columns with two separate p columns will not fit an IEEE
    # column. One row per (design, K) keeps four columns and reads in
    # the same order the text discusses them.
    frac_data = [
        ["Design", "Sites", "Redn", "p"],
        ["Fixed",  "1 of 4",  "1.49×", "0.010"],
        ["Fixed",  "2 of 8",  "1.48×", "0.002"],
        ["Fixed",  "3 of 12", "1.42×", "0.006"],
        ["Fixed",  "4 of 16", "1.42×", "0.002"],
        ["Fixed",  "5 of 20", "1.29×", "0.010"],
        ["Fixed",  "6 of 24", "1.65×", "0.002"],
        ["Shared", "1 of 4",  "1.46×", "0.004"],
        ["Shared", "2 of 8",  "1.32×", "0.002"],
        ["Shared", "3 of 12", "1.20×", "0.275"],
        ["Shared", "4 of 16", "0.97×", "0.846"],
    ]
    add_table_caption(doc,
        "Table 8: The same 25% corrupted fraction at six federation "
        "sizes, ten seeds each. Sites gives corrupted of total. "
        "Fixed holds 1,000 images per client so the corpus grows with "
        "the federation; Shared divides a constant corpus of about "
        "4,000 images and was not run past sixteen sites. Values are "
        "ECE reduction against FedAvg, with paired Wilcoxon p. Holding "
        "per-client data fixed keeps the advantage flat in K; dividing "
        "a fixed corpus erodes it.")
    make_table(doc, frac_data, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: row[0] == "16")
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "With per-client data held fixed the advantage is flat across a "
        "fourfold range of federation sizes: 1.46×, 1.48×, 1.42×, 1.42× "
        "at K = 4, 8, 12 and 16, and every point is significant, with "
        "AHA-Fed ahead on 37 of the 40 paired seeds. Across the seven "
        "25%-corrupted configurations we have run, the ECE ratio "
        "correlates +0.91 with per-client sample size and −0.57 with "
        "client count. The operative variable is how much data each "
        "hospital holds, not how many hospitals there are.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "The mechanism is the quality signal. It is estimated from a "
        "client's local training loss, and that estimate gets noisier as "
        "the client's sample shrinks; at 250 images the corruption signal "
        "no longer separates cleanly from ordinary sampling variation, "
        "which is the same failure the diagnostic of Section 5.7 measures "
        "directly. Federation size enters only through this channel, "
        "which is why the constant-corpus sweep looked like a size limit. "
        "It is a per-client sample-size limit that a constant corpus "
        "converts into one.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "This is the more useful statement of the two, because it maps "
        "onto how federations actually grow. Recruiting more hospitals "
        "usually adds their data rather than dividing a fixed pool, which "
        "is the fixed-per-client column, and that column shows no decay to "
        "K = 24. We have not tested beyond twenty-four sites, nor below 250 "
        "images per client, and we do not extrapolate past either. Nor "
        "does this rescue Section 5.4, whose sweep holds the corpus "
        "constant by design and where the advantage does fade; it "
        "explains it. The corrupted fraction still matters "
        "independently: at K = 8 the reduction goes from 1.17× at one "
        "corrupted site to 1.32× at two, and at K = 12 from 1.01× to "
        "1.20×.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "5.10 Scaling to full-resolution chest radiography",
                level=2)
    add_paragraph(doc,
        "Every result so far is on 28×28 MedMNIST imagery. The obvious "
        "question is whether the pipeline transfers to clinical-resolution "
        "data, so we ran the federation on NIH ChestX-ray14 [25]: 112,120 "
        "frontal radiographs, fourteen findings as a multi-label task, "
        "partitioned patient-disjoint across four centers at 224×224 with a "
        "DenseNet-121 [9] backbone. Patient-disjoint partitioning matters "
        "here, "
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
        "we report that plainly. The margin is small, 0.004 AUROC on a "
        "single seed, so we do not read it as evidence that AHA-Fed is "
        "worse; we read it as the absence of any benefit in this setting. "
        "Table 9 reports both federations.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # Six columns will not fit an IEEE column: "0.0113 ± 0.0010" alone
    # needs most of the width. Federation and aggregator merge into one
    # label, and AUPRC moves to the caption, which the text already
    # discusses rather than reading off the table.
    nih_data = [
        ["Setting", "Method", "AUROC", "ECE", "Acc"],
        ["Clean, 8,000", "FedAvg", "0.958", "0.0099", "0.702"],
        ["Clean, 2,000", "FedAvg", "0.927", "0.0100", "0.604"],
        ["Clean, 2,000", "AHA-Fed", "0.923", "0.0114", "0.592"],
        ["Clean, 2,000", "FedBN", "0.909", "0.0135", "0.586"],
        ["Noisy, 9 seeds", "FedAvg", "0.931±0.005", "0.0113±0.0010", "0.601"],
        ["Noisy, 9 seeds", "AHA-Fed", "0.925±0.009", "0.0106±0.0016", "0.600"],
        ["Noisy, 3 seeds", "FedBN", "0.876±0.018", "0.0133±0.0013", "0.583"],
        ["Noisy, 3 seeds", "FedDisco", "0.919±0.006", "0.0113±0.0010", "0.599"],
    ]
    add_table_caption(doc,
        "Table 9: NIH ChestX-ray14 at 224×224, four patient-disjoint "
        "centers; settings give images per center and noise is 50% at one "
        "site. Clean rows are single seed. AUROC is macro-averaged over the "
        "14 findings and accuracy is exact match over the whole label "
        "vector. Macro AUPRC follows the same ordering: 0.658, 0.414, "
        "0.385 and 0.379 on the clean rows, and 0.413, 0.399, 0.298 and "
        "0.378 on the noisy ones.")
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
        "Second, this federation contains no corrupted center, and every "
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
        "for FedBN), and FedBN is clearly the weakest at this resolution, "
        "its AUROC of 0.876 sits well below the 0.92–0.93 the others reach, "
        "which is consistent with per-client batch-norm statistics being a "
        "poor fit when the corruption is in the labels rather than the "
        "features. None of the three pairwise comparisons is significant at "
        "three seeds (p = 0.25 to 1.00), so we report the ordering and not "
        "the margins.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We stop short of calling any of it established, and raising the seed "
        "budget did not help; it moved the effect the wrong way. At "
        "three seeds the ECE gap was 10.6%, at six 12.9%, and at nine "
        "7.0% (p = 0.50), with AHA-Fed ahead on four of the nine seeds. "
        "AUROC favours FedAvg throughout (0.931 against 0.925, p = 0.16), "
        "as does accuracy by a negligible margin. Section 5.7 gives a "
        "reason rather than leaving this as an anomaly: the diagnostic "
        "on this federation is 1.15 against 2.37 on PathMNIST, so the "
        "corruption signal barely clears the variation among healthy "
        "centers even though it identifies the corrupted one in 9 of 9 "
        "runs, a near-unity ratio predicts the right direction at a "
        "magnitude too small to resolve, which is what we observe. "
        "The honest reading is "
        "that at clinical resolution the calibration advantage is small "
        "enough that our seed budget cannot distinguish it from zero, and "
        "that adding seeds shrank rather than sharpened it, which is "
        "what one expects when an apparent effect is largely seed "
        "variance.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We report the nine-seed figure rather than the six-seed one that "
        "flattered the method, and note the sequence because it is "
        "instructive: three seeds, six seeds and nine seeds gave 10.6%, "
        "12.9% and 7.0% for the same comparison. Readers judging "
        "small-seed federated results, including ours at 28×28, which "
        "use ten, should weight them accordingly. What survives at this "
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
        "resolution than at 28×28, 10.6% here against 19.1% on "
        "PathMNIST, though we cannot say from these runs whether that "
        "reflects resolution, the different corruption model a "
        "multi-label task requires, or the smaller seed budget. "
        "Section 7.3 lists the ten-seed replication as the first item of "
        "future work.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "5.11 Privacy-utility tradeoff with DP-SGD", level=2)
    add_paragraph(doc,
        "Each client runs Opacus DP-SGD with a per-round target privacy "
        "budget ε, δ = 10⁻⁵ and max gradient norm C = 1.0, on the "
        "federation of Section 5.6. One accounting caveat bounds what "
        "the numbers mean and belongs before them: our implementation "
        "instantiates a fresh Opacus accountant each communication "
        "round, so the quoted ε is the per-round budget for one client's "
        "local training and not an end-to-end guarantee composed over "
        "training. Composing across rounds would give a substantially "
        "larger effective ε, so the privacy delivered here is weaker "
        "than the labels suggest and the utility costs below are a lower "
        "bound on what a properly composed budget would cost. Per-round "
        "reporting is common in the federated DP literature but is not "
        "the guarantee a deployment needs, and we flag it rather than "
        "leave it to be inferred.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Our first attempt at this experiment produced a negative result "
        "that turned out to be our own doing, and the correction is "
        "instructive enough to report. That sweep gave each client 300 "
        "images over 15 rounds with batch 64, against the 1,000 images "
        "and 25 rounds behind every non-private number in this paper. "
        "Accuracy sat at or below the 0.111 chance level at every "
        "budget, and we concluded that DP-SGD destroyed utility. It "
        "confounded the cost of privacy with the cost of training on a "
        "third of the data, the same per-client sample-size effect "
        "Section 5.9 identifies as the variable governing whether the "
        "quality signal works at all, and DP-SGD is the setting most "
        "exposed to it, since the noise added per step is calibrated to "
        "the sampling rate. Table 11 reports both configurations and "
        "Figure 12 plots the original sweep.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    dp_data = [
        ["Config", "ε", "Method", "Acc", "AUROC", "ECE"],
        ["300 img/client, 15 rd", "1.0",  "FedAvg",  "0.082", "—", "—"],
        ["300 img/client, 15 rd", "1.0",  "AHA-Fed", "0.084", "—", "—"],
        ["1,000 img/client, 25 rd", "1.0",  "FedAvg",  "0.481", "0.857", "0.215"],
        ["1,000 img/client, 25 rd", "1.0",  "AHA-Fed", "0.470", "0.858", "0.194"],
        ["1,000 img/client, 25 rd", "10.0", "FedAvg",  "0.484", "0.869", "0.203"],
        ["1,000 img/client, 25 rd", "10.0", "AHA-Fed", "0.476", "0.870", "0.185"],
        ["Non-private", "∞", "FedAvg",  "0.679", "0.938", "0.119"],
        ["Non-private", "∞", "AHA-Fed", "0.702", "0.949", "0.097"],
    ]
    add_table_caption(doc,
        "Table 11: DP-SGD on PathMNIST under two data budgets. The "
        "300-image rows are our original sweep, single seed; the "
        "1,000-image rows are ten seeds at the same per-client budget "
        "as every non-private result in this paper. Chance accuracy is "
        "0.111.")
    make_table(doc, dp_data, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: row[0].startswith("1,000"))
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "Repeated at the paper's standard per-client budget with batch "
        "128, a larger batch is standard DP-SGD practice, since it "
        "improves the noise-to-signal ratio at fixed ε, the picture "
        "changes entirely. Accuracy rises from 0.084 to 0.470 at ε = 1.0 "
        "and AUROC reaches 0.858, against 0.702 and 0.949 without "
        "privacy. That is a real privacy cost, roughly a third of "
        "accuracy and eight points of AUROC, but it is a working model "
        "rather than a broken one, and it is in line with the ten to "
        "thirty AUROC points reported elsewhere at comparable budgets "
        "[1].",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_paragraph(doc,
        "Ten seeds resolve the comparison between aggregators, and it is a "
        "trade-off rather than a win. AHA-Fed keeps its calibration "
        "advantage under privacy: ECE 0.194 against 0.215 at ε = 1.0 "
        "(p = 0.006) and 0.185 against 0.203 at ε = 10.0 (p = 0.004), "
        "ahead on nine of ten seeds at both budgets. FedAvg is the more "
        "accurate of the two, significantly so at ε = 1.0 (0.481 against "
        "0.470, p = 0.002, ahead on ten of ten). Discrimination is "
        "indistinguishable (AUROC p = 0.28 and 0.43). Under "
        "Holm–Bonferroni across the six comparisons both calibration "
        "results and the ε = 1.0 accuracy result survive; the ε = 10.0 "
        "accuracy margin does not.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "The effect sizes matter as much as the signs. AHA-Fed buys "
        "roughly a tenth off calibration error for roughly a fiftieth "
        "of accuracy, 9.7% ECE reduction against 2.2% accuracy cost at "
        "ε = 1.0. Whether that trade is worth making is a deployment "
        "question rather than a methodological one, and it depends on "
        "whether the model feeds a triage decision, where confidence "
        "calibration governs whether a clinician can act on it, or a "
        "throughput metric, where accuracy is the thing. We report the "
        "trade rather than recommending one side of it. What the "
        "experiment settles is that the architectural compatibility "
        "argued in Section 3.6 is not merely formal: the calibration "
        "benefit that motivates AHA-Fed survives DP-SGD noise at a "
        "budget that leaves a usable model, which the earlier "
        "300-image sweep could not show. Composing ε across rounds "
        "remains the open item and is listed in Section 7.3.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_figure(doc, FIGS / "fig_dp_tradeoff.png",
               "Figure 12: The original 300-image DP-SGD sweep on "
               "PathMNIST, accuracy and ECE against the target budget "
               "ε, where smaller ε is stronger privacy. Retained to show "
               "the collapse to chance that the 1,000-image runs of "
               "Table 11 correct.")

    add_heading(doc, "5.12 Hyperparameter sensitivity", level=2)
    add_paragraph(doc,
        "We sweep AHA-Fed's two key hyperparameters β ∈ {0, 1, 2, 4, 8} "
        "and γ ∈ {0, 1, 2, 4, 8} on a 5×5 grid (α = 1 fixed) on "
        "PathMNIST with the same federation. Figure 13 reports the final "
        "ECE at each grid point. Across the sixteen-point interior "
        "β ∈ {1, 2, 4, 8} × γ ∈ {1, 2, 4, 8}, which contains our default "
        "(β = 4, γ = 4), ECE stays at or below 0.114, every interior "
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
        "is beaten by every baseline. A practitioner should read Figure 13 "
        "as evidence that (β, γ) need not be tuned finely for a given "
        "federation, not as licence to carry values from one task to "
        "another.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_figure(doc, FIGS / "fig_hp_heatmap.png",
               "Figure 13: AHA-Fed (β, γ) hyperparameter sensitivity "
               "heatmap on PathMNIST.")

    add_heading(doc, "5.13 Discussion", level=2)
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
        "(1.44×, 1.56×, 1.47×). Figure 9 shows the corresponding "
        "behaviour at the level of the weights, with the corrupted client "
        "driven to roughly a quarter of uniform without any noise label.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "We flag a methodological point that cost us a claim. At three "
        "seeds this same sweep returned p = 0.15 and an earlier draft "
        "reported noise robustness as unsupported. Nothing about the "
        "method changed between then and now, only the seed budget. In "
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
        "(β, γ) sweep of Section 5.12 shows a wide well-behaved interior "
        "on PathMNIST, but Section 5.7 shows those same values failing to "
        "transfer to a binary chest-radiography task, so "
        "hyperparameter robustness holds within a task, not across tasks.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # ==================== 6. ABLATION ====================
    add_heading(doc, "6. Ablation Study", level=1)
    add_paragraph(doc,
        "Table 10 isolates each term by zeroing its coefficient on the "
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
        "Table 10: Ablation of the AHA-Fed terms on PathMNIST, ten seeds. "
        "The 'vs full' column is (row ECE − full ECE) / row ECE, the same "
        "convention as Table 3; positive means the full rule is better.")
    make_table(doc, abl, header_font_size=10, body_font_size=9.5,
               highlight_row_pred=lambda i, row: row[0].startswith("Quality only"))
    add_post_table_spacing(doc)

    add_paragraph(doc,
        "The quality term carries the method. Removing it, leaving volume "
        "and distance, gives ECE 0.130, worse than plain volume weighting "
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
        "That result has an obvious implication, drop the distance term "
        ", so we tested it rather than reasoning about it. Repeating both "
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
        "So the 16% figure is a property of one federation, moderate "
        "prior shift with a corrupted site, not a general result. "
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
        "signal, removing it is worse than plain volume weighting, "
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
        "FedAvg, FedProx, FedBN, and FedDisco, every margin significant "
        "(p = 0.004–0.037), while attaining the highest mean accuracy of "
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
        "showing that these hyperparameters do not transfer across tasks, "
        "a test-set-selected configuration would have appeared to win, and "
        "Section 5.7 quantifies that gap deliberately. Under per-round "
        "DP-SGD, given the same per-client data as the non-private "
        "runs, both aggregators retain usable accuracy and the "
        "comparison is a trade rather than a win: AHA-Fed holds its "
        "calibration advantage over ten seeds while FedAvg is the more "
        "accurate, both significantly. What the "
        "evidence supports is a heterogeneity- and noise-aware aggregation "
        "rule with a calibration benefit in small federations containing "
        "unreliable sites, together with a diagnostic that says in advance "
        "whether a given federation is one of those. What it does not "
        "support is a general-purpose replacement for volume weighting, or "
        "any claim that AHA-Fed outperforms volume weighting under "
        "differential privacy.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_heading(doc, "7.1 Limitations", level=2)
    add_paragraph(doc,
        "Six limitations bound the scope of these claims. First, the "
        "convergence result of Section 3.9 guarantees non-degenerate "
        "weights and hence the standard rate, but for a round-averaged "
        "reweighted objective; it does not establish that the reweighted "
        "objective is the better one, which remains an empirical claim.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Second, resolution: the comparative results are all on 28×28 "
        "MedMNIST images, and the primary corpus is colorectal "
        "histopathology rather than the chest radiography that motivates "
        "our introduction. Section 5.10 compares three aggregators on "
        "full-resolution NIH ChestX-ray14 and the calibration advantage "
        "does not reproduce there, so we do not claim it survives at "
        "clinical resolution. Third, statistical power: the PathMNIST "
        "comparisons, the label-noise sweep, the heterogeneity sweep and "
        "the federation-size sweep all use ten seeds with paired "
        "significance tests. That is adequate to resolve the effects we "
        "report but remains modest, and none of these results has been "
        "replicated on an independent corpus at full resolution.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Fourth, hyperparameter transfer: as Section 5.7 shows, (β, γ) "
        "tuned for a nine-class task are actively harmful on a binary "
        "one, so AHA-Fed carries a real deployment cost that "
        "volume-weighted FedAvg does not: a per-task validation split. "
        "Fifth, "
        "scale: K = 4–32 simulated clients on a single machine. Section "
        "5.9 shows the advantage holding to K = 24 when each client keeps "
        "1,000 images, and decaying when a fixed corpus is divided "
        "further; we have not tested beyond twenty-four sites or below 250 "
        "images per client, and make no claim about cross-device "
        "federations.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)
    add_paragraph(doc,
        "Sixth, privacy: as Section 5.11 documents, our DP-SGD budgets "
        "are per-round rather than composed across training, so the "
        "effective end-to-end ε is substantially larger than the labels "
        "and the utility costs we report are a lower bound. Our privacy "
        "claim is therefore a calibration advantage at a per-round budget "
        "that leaves a usable model, not a demonstrated advantage under a "
        "deployment-grade guarantee.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "7.2 Code and data availability", level=2)
    add_paragraph(doc,
        "The framework, the seeded sweep runner, the per-run JSON "
        "manifests behind every number reported here, and the "
        "verification script that re-checks each claim against those "
        "manifests are available at "
        "https://github.com/AUTHOR/aha-fed (to be replaced with the "
        "archival DOI on acceptance). PathMNIST and PneumoniaMNIST are "
        "distributed with MedMNIST v2 [28] under CC BY 4.0; NIH "
        "ChestX-ray14 [25] is available from the NIH Clinical Center. "
        "No data-use agreement is required to reproduce any result in "
        "this paper.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    add_heading(doc, "7.3 Future work", level=2)
    add_paragraph(doc,
        "Future work follows directly from those limitations. "
        "(i) Full-resolution validation: CheXpert [10], NIH ChestX-ray14 [25], "
        "under K ≥ 8 patient-disjoint "
        "federations with formal (ε, δ) tracking and per-center fairness "
        "audit; the loaders are already released, so this is a compute "
        "question rather than an engineering one. A larger seed budget on "
        "the label-noise sweep would also settle whether the effect there "
        "is real but small or absent; the present evidence cannot "
        "distinguish those. (ii) Personalisation: composing AHA-Fed weights with "
        "FedRep [4], pFedMe [6], or Ditto [14] heads to retain a "
        "per-hospital classifier for site-specific prevalence. "
        "(iii) Theoretical analysis: a convergence proof of AHA-Fed "
        "under (L, μ)-smooth, partially-noisy local objectives, "
        "mirroring the FedProx convergence theorem and accounting for "
        "the softmax aggregation rule.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=0.5)

    # ==================== REFERENCES ====================
    add_heading(doc, "References", level=1)
    references = [
        ("[1]", "Abadi, M., Chu, A., Goodfellow, I., McMahan, H. B., Mironov, I., "
               "Talwar, K., Zhang, L. Deep learning with differential privacy. "
               "In Proceedings of the 2016 ACM SIGSAC Conference on Computer and "
               "Communications Security (CCS), pages 308–318, 2016."),
        ("[2]", "Bonawitz, K., Ivanov, V., Kreuter, B., Marcedone, A., McMahan, "
               "H. B., Patel, S., Ramage, D., Segal, A., Seth, K. Practical "
               "secure aggregation for privacy-preserving machine learning. In "
               "Proceedings of the 2017 ACM SIGSAC Conference on Computer and "
               "Communications Security (CCS), pages 1175–1191, 2017."),
        ("[3]", "Chen, Z., Yang, C., Zhu, M., Peng, Z., Yuan, Y. Personalized "
               "retrogress-resilient federated learning toward imbalanced "
               "medical data. IEEE Transactions on Medical Imaging, 41(12): "
               "3663–3674, 2022."),
        ("[4]", "Collins, L., Hassani, H., Mokhtari, A., Shakkottai, S. "
               "Exploiting shared representations for personalized federated "
               "learning. In Proceedings of the 38th International Conference on "
               "Machine Learning (ICML), PMLR 139, 2021."),
        ("[5]", "Dayan, I., Roth, H. R., Zhong, A., Harouni, A., Gentili, A., "
               "Abidin, A. Z. et al. Federated learning for predicting clinical "
               "outcomes in patients with COVID-19. Nature Medicine, 27(10): "
               "1735–1743, 2021."),
        ("[6]", "Dinh, C. T., Tran, N. H., Nguyen, T. D. Personalized federated "
               "learning with Moreau envelopes. In Advances in Neural "
               "Information Processing Systems (NeurIPS) 33, 2020."),
        ("[7]", "Guo, C., Pleiss, G., Sun, Y., Weinberger, K. Q. On calibration "
               "of modern neural networks. In Proceedings of the 34th "
               "International Conference on Machine Learning (ICML), PMLR 70, "
               "2017."),
        ("[8]", "Guo, P., Yang, D., Hatamizadeh, A., Xu, A., Xu, Z., Li, W. et "
               "al. Auto-FedRL: federated hyperparameter optimization for "
               "multi-institutional medical image segmentation. In Proceedings "
               "of the European Conference on Computer Vision (ECCV), 2022."),
        ("[9]", "Huang, G., Liu, Z., van der Maaten, L., Weinberger, K. Q. "
                "Densely connected convolutional networks. In Proceedings of the "
                "IEEE Conference on Computer Vision and Pattern Recognition "
                "(CVPR), 2017."),
        ("[10]", "Irvin, J., Rajpurkar, P., Ko, M., Yu, Y., Ciurea-Ilcus, S., "
                "Chute, C. et al. CheXpert: a large chest radiograph dataset with "
                "uncertainty labels and expert comparison. In Proceedings of the "
                "AAAI Conference on Artificial Intelligence, 33(1), 2019."),
        ("[11]", "Kairouz, P., McMahan, H. B., Avent, B., Bellet, A., Bennis, M., "
                "Bhagoji, A. N. et al. Advances and open problems in federated "
                "learning. Foundations and Trends in Machine Learning, 14(1–2): "
                "1–210, 2021."),
        ("[12]", "Karimireddy, S. P., Kale, S., Mohri, M., Reddi, S. J., Stich, S. "
                "U., Suresh, A. T. SCAFFOLD: stochastic controlled averaging for "
                "federated learning. In Proceedings of the 37th International "
                "Conference on Machine Learning (ICML), PMLR 119: 5132–5143, "
                "2020."),
        ("[13]", "Li, Q., Diao, Y., Chen, Q., He, B. Federated learning on non-IID "
                "data silos: an experimental study. In Proceedings of the IEEE "
                "38th International Conference on Data Engineering (ICDE), 2022."),
        ("[14]", "Li, T., Hu, S., Beirami, A., Smith, V. Ditto: fair and robust "
                "federated learning through personalization. In Proceedings of "
                "the 38th International Conference on Machine Learning (ICML), "
                "PMLR 139, 2021."),
        ("[15]", "Li, T., Sahu, A. K., Zaheer, M., Sanjabi, M., Talwalkar, A., "
                "Smith, V. Federated optimization in heterogeneous networks. In "
                "Proceedings of Machine Learning and Systems (MLSys) 2, 2020."),
        ("[16]", "Li, X., Jiang, M., Zhang, X., Kamp, M., Dou, Q. FedBN: federated "
                "learning on non-IID features via local batch normalization. In "
                "International Conference on Learning Representations (ICLR), "
                "2021."),
        ("[17]", "Liu, Q., Chen, C., Qin, J., Dou, Q., Heng, P.-A. FedDG: "
                "federated domain generalization on medical image segmentation "
                "via episodic learning in continuous frequency space. In "
                "Proceedings of the IEEE/CVF Conference on Computer Vision and "
                "Pattern Recognition (CVPR), 2021."),
        ("[18]", "McMahan, H. B., Moore, E., Ramage, D., Hampson, S., Agüera y "
                "Arcas, B. Communication-efficient learning of deep networks from "
                "decentralized data. In Proceedings of the 20th International "
                "Conference on Artificial Intelligence and Statistics (AISTATS), "
                "PMLR 54: 1273–1282, 2017."),
        ("[19]", "Nguyen, D. C., Pham, Q.-V., Pathirana, P. N., Ding, M., "
                "Seneviratne, A., Lin, Z., Dobre, O., Hwang, W.-J. Federated "
                "learning for smart healthcare: a survey. ACM Computing Surveys, "
                "55(3): 1–37, 2023."),
        ("[20]", "Ogier du Terrail, J., Ayed, S.-S., Cyffers, E., Grimberg, F., "
                "He, C., Loeb, R. et al. FLamby: datasets and benchmarks for "
                "cross-silo federated learning in realistic healthcare settings. "
                "In Advances in Neural Information Processing Systems (NeurIPS) "
                "35, Datasets and Benchmarks Track, 2022."),
        ("[21]", "Pakdaman Naeini, M., Cooper, G., Hauskrecht, M. Obtaining well "
                "calibrated probabilities using Bayesian binning. In Proceedings "
                "of the AAAI Conference on Artificial Intelligence, 29(1), 2015."),
        ("[22]", "Pati, S., Baid, U., Edwards, B., Sheller, M., Wang, S.-H., "
                "Reina, G. A. et al. Federated learning enables big data for rare "
                "cancer boundary detection. Nature Communications, 13: 7346, "
                "2022."),
        ("[23]", "Rieke, N., Hancox, J., Li, W., Milletarì, F., Roth, H. R., "
                "Albarqouni, S. et al. The future of digital health with "
                "federated learning. npj Digital Medicine, 3: 119, 2020."),
        ("[24]", "Sheller, M. J., Edwards, B., Reina, G. A., Martin, J., Pati, S., "
                "Kotrotsou, A. et al. Federated learning in medicine: "
                "facilitating multi-institutional collaborations without sharing "
                "patient data. Scientific Reports, 10: 12598, 2020."),
        ("[25]", "Wang, X., Peng, Y., Lu, L., Lu, Z., Bagheri, M., Summers, R. M. "
                "ChestX-ray8: hospital-scale chest X-ray database and benchmarks "
                "on weakly-supervised classification and localization of common "
                "thorax diseases. In Proceedings of the IEEE Conference on "
                "Computer Vision and Pattern Recognition (CVPR), pages 2097–2106, "
                "2017."),
        ("[26]", "Wu, N., Yu, L., Yang, X., Cheng, K.-T., Yan, Z. FedIIC: towards "
                "robust federated learning for class-imbalanced medical image "
                "classification. In Medical Image Computing and Computer Assisted "
                "Intervention (MICCAI), LNCS 14221, 2023."),
        ("[27]", "Xu, J., Chen, Z., Quek, T. Q. S., Chong, K. F. E. FedCorr: "
                "multi-stage federated learning for label noise correction. In "
                "Proceedings of the IEEE/CVF Conference on Computer Vision and "
                "Pattern Recognition (CVPR), pages 10184–10193, 2022."),
        ("[28]", "Yang, J., Shi, R., Wei, D., Liu, Z., Zhao, L., Ke, B., Pfister, "
                "H., Ni, B. MedMNIST v2: a large-scale lightweight benchmark for "
                "2D and 3D biomedical image classification. Scientific Data, 10: "
                "41, 2023."),
        ("[29]", "Ye, R., Xu, M., Wang, J., Xu, C., Chen, S., Wang, Y. FedDisco: "
                "federated learning with discrepancy-aware collaboration. In "
                "Proceedings of the 40th International Conference on Machine "
                "Learning (ICML), PMLR 202, 2023."),
        ("[30]", "Yousefpour, A., Shilov, I., Sablayrolles, A., Testuggine, D., "
                "Prasad, K., Malek, M. et al. Opacus: user-friendly differential "
                "privacy library in PyTorch. In NeurIPS 2021 Workshop Privacy in "
                "Machine Learning, 2021."),
        ("[31]", "Zhang, J., Li, Z., Li, B., Xu, J., Wu, S., Ding, S., Wu, C. "
                "Federated learning with label distribution skew via logits "
                "calibration. In Proceedings of the 39th International Conference "
                "on Machine Learning (ICML), PMLR 162, 2022."),
        ("[32]", "Zhu, H., Xu, J., Liu, S., Jin, Y. Federated learning on non-IID "
                "data: a survey. Neurocomputing, 465: 371–390, 2021."),
        ("[33]", "Zhu, L., Liu, Z., Han, S. Deep leakage from gradients. In "
                "Advances in Neural Information Processing Systems (NeurIPS) 32, "
                "2019."),
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
