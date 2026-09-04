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

import copy

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figures"
DEFAULT_TEMPLATE = Path.home() / "Downloads" / "Access_Word_Template.docx"
DEFAULT_OUT = ROOT / "paper" / "AHA_Fed_IEEE_Access.docx"

# IEEE Access wants 150-250 words, one paragraph, no citations or equations.
ABSTRACT = (
    "Aggregation rules that reweight federated clients by estimated data "
    "quality are common, but the conditions under which they help are "
    "uncharacterised. We study this through AHA-Fed, which weights "
    "clients by a softmax over data volume, label-prior distance from "
    "consensus, and a local-loss quality signal. It reduces to federated "
    "averaging as a strict special case, with weights provably bounded "
    "from zero and hence the standard convergence rate. Evaluated on real "
    "medical imaging only, AHA-Fed lowers Expected Calibration Error on "
    "colorectal histopathology to 0.097 against 0.119-0.139 for four "
    "baselines over ten seeds, every margin significant under a paired "
    "signed-rank test. Under client label noise it reduces calibration "
    "error by a pooled factor of 1.40, with no separation when no client "
    "is corrupted. At a fixed 25% corrupted fraction with 1,000 images "
    "per client the advantage is flat from four to sixteen hospitals, "
    "decaying only when a fixed corpus is split further: the constraint "
    "is per-client sample size. On NIH ChestX-ray14, fourteen findings "
    "across four patient-disjoint centers, the pipeline transfers but the "
    "calibration advantage does not, and AHA-Fed loses to every baseline "
    "on binary chest radiography. Under per-round DP-SGD at the same "
    "per-client data budget both aggregators stay usable and the "
    "calibration advantage survives over ten seeds, at a small but "
    "significant accuracy cost. The negative results have a measurable "
    "cause we turn into a deployment test costing one round: a "
    "signal-to-spread ratio that orders all three corpora by outcome,"
    "2.37 on PathMNIST, 1.15 on NIH, 0.46 on PneumoniaMNIST."
)

INDEX_TERMS = (
    "Calibration, chest radiography, differential privacy, federated "
    "learning, label noise, medical image analysis, statistical heterogeneity"
)

TITLE = ("Quality-Aware Aggregation Improves Calibration but Only Under "
         "Measurable Conditions in Federated Medical Imaging")

AUTHORS = ("ABU UBAIDA¹, KHURRAM ZEESHAN HAIDER², "
           "FARHAN AADIL³, and CELAL ALAGOZ³")
AFFILIATIONS = [
    "¹Center of Data Science, Government College University Faisalabad, "
    "Faisalabad 38000, Pakistan",
    "²Department of Software Engineering, Government College University "
    "Faisalabad, Faisalabad 38000, Pakistan",
    "³Department of Computer Engineering, Sivas University of Science "
    "and Technology, Sivas 58000, Türkiye",
]
BIOS = [
    "ABU UBAIDA",
    "KHURRAM ZEESHAN HAIDER",
    "FARHAN AADIL",
    "CELAL ALAGOZ",
]
CORRESPONDING = ("Corresponding author: Farhan Aadil "
                 "(e-mail: farhan.aadil@sivas.edu.tr).")
# No external funding to declare; the template's support-acknowledgement
# paragraph is therefore omitted rather than left as a placeholder.
# Access expects the support-information footnote present even when
# there is nothing to declare.
FUNDING = "This work received no specific grant from any funding agency."


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def strip_body(doc: Document):
    """Clear the template's text but keep its column structure.

    IEEE Access is one column for the title block, abstract and index terms,
    then two columns for the body. That split lives in a section break, which
    a naive strip removes along with the paragraphs, leaving the title and
    abstract laid out in two columns. Here the first section's properties are
    captured before clearing so the break can be reinstated.

    Returns the one-column sectPr to place after the front matter.
    """
    body = doc.element.body

    # The first paragraph carrying a sectPr defines the one-column region.
    front_sectpr = None
    for para in body.findall(W + "p"):
        pPr = para.find(W + "pPr")
        if pPr is not None:
            found = pPr.find(W + "sectPr")
            if found is not None:
                front_sectpr = copy.deepcopy(found)
                break

    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)
    return front_sectpr


def start_two_column_body(doc: Document, front_sectpr) -> None:
    """Close the one-column front matter so the body runs in two columns."""
    if front_sectpr is None:
        return
    para = doc.add_paragraph()
    pPr = para._p.get_or_add_pPr()
    pPr.append(front_sectpr)


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


# The template's own heading styles, in preference order. It does not use
# Word's generic "Heading 1"/"Heading 2".
H1_STYLES = ["H1_List (Space)", "H1_List (No Space)", "H1", "Heading 1"]
H2_STYLES = ["H2_Cont", "H2_First", "H2_After H1", "H2", "Heading 2"]


def first_style(doc: Document, candidates: list[str]) -> str | None:
    for name in candidates:
        if style_or_none(doc, name) is not None:
            return name
    return None


def romanise_refs(text: str) -> str:
    """Access titles tables in roman, so in-text references must match.

    The source document numbers them 1..10; the Access renderer emits
    TABLE I..X in the same order, so the mapping is positional. Figures
    stay Arabic, Access uses FIGURE 1. for those.
    """
    return re.sub(
        r"\bTable\s+(\d+)\b",
        lambda m: "Table " + (ROMAN[int(m.group(1)) - 1]
                              if 1 <= int(m.group(1)) <= len(ROMAN)
                              else m.group(1)),
        text)


def strip_number(text: str) -> str:
    """Drop a leading '3.' or '5.7', Access numbers sections itself."""
    return re.sub(r"^\d+(\.\d+)*\.?\s+", "", text).strip()


_first_h1 = [True]
_after_h1 = [False]


def heading(doc: Document, text: str, level: int = 1):
    """Access sets headings in uppercase and numbers them via the style."""
    if level == 1:
        if _first_h1[0]:
            # INTRODUCTION sits directly under the index terms, so the
            # template uses the no-space variant for it and the spaced one
            # thereafter.
            names = ["H1_List (No Space)"] + H1_STYLES
            _first_h1[0] = False
        else:
            names = H1_STYLES
        _after_h1[0] = True
    else:
        # The first subsection of a section sits tight under its heading;
        # later ones follow a body paragraph and carry space above.
        names = (["H2_First"] + H2_STYLES if _after_h1[0]
                 else ["H2_Cont"] + H2_STYLES)
        _after_h1[0] = False
    style = first_style(doc, names)
    body = strip_number(text)
    body = body.upper() if level == 1 else body.upper()
    if style:
        p = doc.add_paragraph(body)
        p.style = doc.styles[style]
        return p
    return para(doc, body, bold=True, size=11 if level == 1 else 10)


# One Access column: (8.00 - 0.51 - 0.51 - 0.28 gutter) / 2 = 3.35 in.
# Figures are set slightly narrower so they never force a column to reflow.
COLUMN_WIDTH_IN = 3.30


def figure(doc: Document, name: str, caption: str,
           width_in: float = COLUMN_WIDTH_IN):
    path = FIGS / name
    if not path.exists():
        print(f"  [warn] missing figure {name}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width_in))
    cap_style = first_style(doc, ["Fig Caption", "Figure Caption"])
    # IEEE sets captions as "FIGURE 1. Text", not "Figure 1: Text".
    body = re.sub(r"^Figure\s+(\d+)\s*[:.]\s*",
                  lambda m: f"FIGURE {m.group(1)}. ", caption)
    # a figure caption may cite a table, which follows the roman titles
    body = romanise_refs(body)
    # Fig Caption carries its own alignment and size in the template.
    para(doc, body, style=cap_style,
         align=None if cap_style else WD_ALIGN_PARAGRAPH.LEFT,
         size=None if cap_style else 8)


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
         "XI", "XII"]
_table_no = [0]


def equation(doc: Document, name: str, label: str,
             width_in: float = 2.6):
    """Native Word math, with the number flush right on the same line.

    OMML rather than an image: editable, searchable, scales with the font,
    and does not have to be re-typeset by the publisher. The PNG name is
    kept as the lookup key and used only as a fallback.
    """
    from paper.equations_omml import EQUATIONS
    from paper.omml import add_math

    p = doc.add_paragraph()
    eq_style = first_style(doc, ["Equation"])
    if eq_style:
        p.style = doc.styles[eq_style]

    # The style's left tab at 3.18 in was set for the template's
    # one-column sample; in the 3.35 in body column it leaves too little
    # room and the number wraps. A right tab at the column edge puts the
    # number flush right whatever its width.
    pf = p.paragraph_format
    pf.tab_stops.clear_all()
    pf.tab_stops.add_tab_stop(Inches(COLUMN_WIDTH_IN),
                              WD_TAB_ALIGNMENT.RIGHT)

    builder = EQUATIONS.get(name)
    if builder is not None:
        add_math(p, builder())
    else:
        path = FIGS / "equations" / name
        if not path.exists():
            print(f"  [warn] missing equation {name}")
            return
        print(f"  [warn] no OMML for {name}; falling back to the image")
        p.add_run().add_picture(str(path), width=Inches(width_in))

    if label:
        # A right tab is ignored once the formula has passed it, which
        # glues the number to the equation. The spaces guarantee a gap
        # in that case; where the tab still works they are absorbed by it.
        run = p.add_run(f"  	{label}")
        run.italic = False


def table(doc: Document, rows: list[list[str]], caption: str):
    """Access precedes each table with a 'TABLE N' title line."""
    _table_no[0] += 1
    numeral = ROMAN[_table_no[0] - 1] if _table_no[0] <= len(ROMAN) else str(_table_no[0])
    title_style = "Table Title" if style_or_none(doc, "Table Title") else None
    para(doc, f"TABLE {numeral}", style=title_style,
         size=None if title_style else 8,
         align=None if title_style else WD_ALIGN_PARAGRAPH.CENTER)

    # The extracted caption already reads "Table 3: ..."; keep only the text.
    # A caption may also cite another table ("the same convention as
    # Table 3"), which has to follow the roman titles like body text does.
    body = re.sub(r"^Table\s+\d+[:.]?\s*", "", caption).strip()
    body = romanise_refs(body)
    # The template sets the caption text in Table Title too, not in a
    # separate caption style.
    cap_style = first_style(doc, ["Table Title", "Table Caption"])
    para(doc, body.upper() if len(body) < 60 else body,
         style=cap_style, size=None if cap_style else 8,
         align=None if cap_style else WD_ALIGN_PARAGRAPH.CENTER)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    if style_or_none(doc, "Normal Table") is not None:
        t.style = doc.styles["Normal Table"]
    # Let Word size columns to their content and cap the table at the text
    # width. Without this a 6- or 7-column table keeps its default widths and
    # runs off the edge of a 3.35 in column.
    t.autofit = True
    t.allow_autofit = True
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            run = c.paragraphs[0].add_run(str(cell))
            # Wide tables need a smaller face to stay inside the column.
            run.font.size = Pt(6.5 if len(rows[0]) >= 6 else 7.5)
            run.bold = (i == 0)
    doc.add_paragraph()


def build(template: Path, out: Path) -> None:
    if not template.exists():
        sys.exit(f"IEEE Access template not found: {template}\n"
                 f"Download it from https://template-selector.ieee.org/ "
                 f"(Transactions/Journals -> IEEE Access -> Word).")

    doc = Document(str(template))
    front_sectpr = strip_body(doc)

    # ---- front matter -------------------------------------------------
    para(doc, "Date of publication xxxx 00, 0000, date of current version "
              "xxxx 00, 0000.",
         style="DOP" if style_or_none(doc, "DOP") else None,
         size=None if style_or_none(doc, "DOP") else 8)
    para(doc, "Digital Object Identifier 10.1109/ACCESS.2024.Doi Number",
         style="DOI" if style_or_none(doc, "DOI") else None,
         size=None if style_or_none(doc, "DOI") else 8)

    title_style = "Paper Title" if style_or_none(doc, "Paper Title") else None
    para(doc, TITLE, style=title_style, size=None if title_style else 20)

    au_style = "AU" if style_or_none(doc, "AU") else None
    para(doc, AUTHORS, style=au_style, size=None if au_style else 10)
    # The template runs every affiliation but the last tight against the
    # one above (PI_No Space) and gives the last, plus the corresponding
    # line, the spaced PI style.
    pi_tight = first_style(doc, ["PI_No Space", "PI"])
    pi_spaced = first_style(doc, ["PI", "PI_No Space"])
    last = len(AFFILIATIONS) - 1
    for i, aff in enumerate(AFFILIATIONS):
        st = pi_spaced if i == last else pi_tight
        ap = para(doc, aff, style=st, size=None if st else 8)
        if i == last and ap is not None:
            # PI carries 27pt after; the template zeroes it here so the gap
            # falls before the abstract instead of before this line.
            ap.paragraph_format.space_after = Pt(0)
    cp = para(doc, CORRESPONDING, style=pi_spaced,
              size=None if pi_spaced else 8)
    if cp is not None:
        cp.paragraph_format.space_before = Pt(5)
        cp.paragraph_format.space_after = Pt(5)
    if FUNDING:
        fn_style = first_style(doc, ["footnote text", "Footnote Text"])
        fp = para(doc, FUNDING, style=fn_style, size=None if fn_style else 8)
        if fp is not None:
            fp.paragraph_format.space_after = Pt(27)

    abs_style = "Abstract" if style_or_none(doc, "Abstract") else None
    p = doc.add_paragraph()
    if abs_style:
        p.style = doc.styles[abs_style]
    r = p.add_run("ABSTRACT ")
    r.bold = True
    p.add_run(ABSTRACT)

    p = doc.add_paragraph()
    it_style = "IT" if style_or_none(doc, "IT") else abs_style
    if it_style:
        p.style = doc.styles[it_style]
    r = p.add_run("INDEX TERMS ")
    r.bold = True
    p.add_run(INDEX_TERMS)

    # Everything above is one column; the body below is two.
    start_two_column_body(doc, front_sectpr)

    # ---- body ---------------------------------------------------------
    from paper.extract_sections import extract  # noqa: E402

    SECTIONS, FIGURES, TABLES = extract()

    skip_until_intro = True
    after_heading = True
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
            after_heading = True
        elif kind == "h2":
            heading(doc, item[1], 2)
            after_heading = True
        elif kind == "p":
            # Access does not indent the first paragraph of a section and
            # does indent the rest; the template carries both styles.
            body_style = (first_style(doc, ["PARA", "Text"]) if after_heading
                          else first_style(doc, ["PARA_Indent", "PARA", "Text"]))
            para(doc, romanise_refs(item[1]), style=body_style,
                 align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            after_heading = False
        elif kind == "fig":
            figure(doc, FIGURES[item[1]][0], FIGURES[item[1]][1])
        elif kind == "table":
            rows, cap = TABLES[item[1]]
            table(doc, rows, cap)
        elif kind == "eq":
            equation(doc, *item[1])
        elif kind == "ref":
            ref_style = first_style(doc, ["REF_Txt", "References", "Ref"])
            para(doc, item[1], style=ref_style,
                 size=None if ref_style else 8)

    # Access closes with one short biography per author, in AU_Bios.
    # These are career details only the authors can supply; they are
    # emitted as marked placeholders so the structure and styling are
    # right and the text is obviously outstanding.
    bio_style = first_style(doc, ["AU_Bios", "Author Bios", "Biography"])
    for name in BIOS:
        para(doc, f"{name} [AUTHOR BIOGRAPHY TO BE SUPPLIED: degrees with "
                  f"field, institution and year; current position and "
                  f"affiliation; research interests.]",
             style=bio_style, size=8)

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
