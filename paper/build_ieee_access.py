"""Render the paper into the IEEE Access Word template.

Rather than reformatting the existing document, this opens the official
Access template, strips its instructional body, and rebuilds the manuscript
inside it using the template's own styles (Paper Title, Abstract, Heading 1..3,
Text, Table Caption, Figure Caption). That way the output carries Access's
page setup, fonts and heading numbering rather than an approximation of them.

Content comes from build_paper.py's section text, so there is one source of
truth for the numbers: edit build_paper.py, rebuild both.

Usage:
    python paper/build_ieee_access.py [--template PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figures"
DEFAULT_TEMPLATE = Path.home() / "Downloads" / "Access_Word_Template.docx"
DEFAULT_OUT = ROOT / "paper" / "AHA_Fed_IEEE_Access.docx"

# IEEE Access wants 150-250 words, one paragraph, no citations or equations.
ABSTRACT = (
    "Federated learning lets hospitals train medical-imaging models without "
    "exchanging patient data, but deployments face statistical heterogeneity "
    "across sites and per-site annotation noise that volume-weighted "
    "aggregation silently amplifies. We propose AHA-Fed, whose per-round "
    "client weights are a softmax over a log-space score combining data "
    "volume, total-variation distance to the across-client label-prior "
    "consensus, and a self-supervised quality signal from the local training "
    "loss. It reduces to federated averaging as a strict special case, and we "
    "prove its weights are bounded away from zero, placing it within the "
    "standard convergence rate. Evaluated on real medical imaging only, "
    "AHA-Fed lowers Expected Calibration Error on colorectal histopathology "
    "to 0.097 against 0.119 to 0.139 for four baselines over ten seeds, every "
    "margin significant under a paired signed-rank test, while attaining the "
    "highest accuracy and matching discrimination. Under client label noise "
    "it reduces calibration error by a pooled factor of 1.40, with no "
    "separation when no client is corrupted, and drives the corrupted client "
    "to a fifth of its uniform weight. Two results are negative and reported "
    "as such: AHA-Fed loses to every baseline on binary chest radiography, "
    "and under differentially private training both aggregators fall to "
    "chance. The first has a measurable cause we turn into a deployment test "
    "computable from one training round."
)

INDEX_TERMS = (
    "Calibration, chest radiography, differential privacy, federated "
    "learning, label noise, medical image analysis, statistical heterogeneity"
)

TITLE = ("Adaptive Heterogeneity-Aware Aggregation for Calibrated Federated "
         "Learning in Medical Imaging")

AUTHORS = "FIRST A. AUTHOR1, SECOND B. AUTHOR2, and THIRD C. AUTHOR3"
AFFILIATIONS = [
    "1Department, University, City, Country",
    "2Department, University, City, Country",
    "3Department, University, City, Country",
]
CORRESPONDING = "Corresponding author: First A. Author (e-mail: author@example.edu)."
FUNDING = ("This work was supported in part by [funder] under Grant [number]. "
           "Replace or delete this paragraph as appropriate.")


def strip_body(doc: Document) -> None:
    """Remove the template's instructional content, keeping styles and setup."""
    body = doc.element.body
    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)


def style_or_none(doc: Document, name: str):
    try:
        return doc.styles[name]
    except KeyError:
        return None


def para(doc: Document, text: str, style: str | None = None,
         align=None, size: float | None = None, bold: bool = False,
         italic: bool = False):
    p = doc.add_paragraph()
    if style and style_or_none(doc, style) is not None:
        p.style = doc.styles[style]
    run = p.add_run(text)
    if size is not None:
        run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if align is not None:
        p.alignment = align
    return p


def heading(doc: Document, text: str, level: int = 1):
    style = f"Heading {level}"
    if style_or_none(doc, style) is not None:
        p = doc.add_paragraph(text)
        p.style = doc.styles[style]
        return p
    return para(doc, text, bold=True, size=11 if level == 1 else 10)


def figure(doc: Document, name: str, caption: str, width_in: float = 3.4):
    path = FIGS / name
    if not path.exists():
        print(f"  [warn] missing figure {name}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width_in))
    cap_style = ("Figure Caption" if style_or_none(doc, "Figure Caption")
                 else "Fig Caption" if style_or_none(doc, "Fig Caption") else None)
    para(doc, caption, style=cap_style, align=WD_ALIGN_PARAGRAPH.LEFT, size=8)


def table(doc: Document, rows: list[list[str]], caption: str):
    cap_style = "Table Caption" if style_or_none(doc, "Table Caption") else None
    para(doc, caption, style=cap_style, size=8)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    if style_or_none(doc, "Normal Table") is not None:
        t.style = doc.styles["Normal Table"]
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            run = c.paragraphs[0].add_run(str(cell))
            run.font.size = Pt(7.5)
            run.bold = (i == 0)
    doc.add_paragraph()


def build(template: Path, out: Path) -> None:
    if not template.exists():
        sys.exit(f"IEEE Access template not found: {template}\n"
                 f"Download it from https://template-selector.ieee.org/ "
                 f"(Transactions/Journals -> IEEE Access -> Word).")

    doc = Document(str(template))
    strip_body(doc)

    # ---- front matter -------------------------------------------------
    para(doc, "Date of publication xxxx 00, 0000, date of current version "
              "xxxx 00, 0000.", size=8)
    para(doc, "Digital Object Identifier 10.1109/ACCESS.2024.Doi Number", size=8)

    title_style = "Paper Title" if style_or_none(doc, "Paper Title") else None
    para(doc, TITLE, style=title_style, size=None if title_style else 20)

    para(doc, AUTHORS, size=10)
    for aff in AFFILIATIONS:
        para(doc, aff, size=8)
    para(doc, CORRESPONDING, size=8)
    para(doc, FUNDING, size=8)

    abs_style = "Abstract" if style_or_none(doc, "Abstract") else None
    p = doc.add_paragraph()
    if abs_style:
        p.style = doc.styles[abs_style]
    r = p.add_run("ABSTRACT ")
    r.bold = True
    p.add_run(ABSTRACT)

    p = doc.add_paragraph()
    if abs_style:
        p.style = doc.styles[abs_style]
    r = p.add_run("INDEX TERMS ")
    r.bold = True
    p.add_run(INDEX_TERMS)

    # ---- body ---------------------------------------------------------
    from paper.extract_sections import extract  # noqa: E402

    SECTIONS, FIGURES, TABLES = extract()

    skip_until_intro = True
    for item in SECTIONS:
        kind = item[0]
        # The template's front matter already carries title/abstract, so drop
        # everything the builder emits before Section 1.
        if skip_until_intro:
            if kind == "h1" and item[1].strip().startswith("1."):
                skip_until_intro = False
            else:
                continue
        if kind == "h1":
            heading(doc, item[1], 1)
        elif kind == "h2":
            heading(doc, item[1], 2)
        elif kind == "p":
            para(doc, item[1], style="Text" if style_or_none(doc, "Text") else None,
                 align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        elif kind == "fig":
            figure(doc, FIGURES[item[1]][0], FIGURES[item[1]][1])
        elif kind == "table":
            rows, cap = TABLES[item[1]]
            table(doc, rows, cap)

    doc.save(str(out))
    words = sum(len(p.text.split()) for p in doc.paragraphs)
    print(f"Wrote: {out}")
    print(f"  abstract words: {len(ABSTRACT.split())} (IEEE Access wants 150-250)")
    print(f"  body words    : ~{words}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    build(args.template, args.out)
