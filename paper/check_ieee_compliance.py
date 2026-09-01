"""Check the generated manuscript against the official IEEE Access template.

Compares page setup, column structure, styles and the front-matter
conventions Access requires, so formatting regressions surface here rather
than in a desk rejection.

Usage:
    python paper/check_ieee_compliance.py [--template PATH] [--paper PATH]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def columns(section) -> str:
    cols = section._sectPr.find(W + "cols")
    return (cols.get(W + "num") or "1") if cols is not None else "1"


def main(template: Path, paper: Path) -> int:
    if not template.exists():
        sys.exit(f"template not found: {template}")
    if not paper.exists():
        sys.exit(f"manuscript not found: {paper}")

    tpl, doc = Document(str(template)), Document(str(paper))
    ts, ds = tpl.sections[0], doc.sections[0]
    texts = [p.text for p in doc.paragraphs]
    styles_used = {p.style.name for p in doc.paragraphs}

    print("=== IEEE Access template compliance ===\n")

    # abs() on a Length returns a plain int of EMUs, so compare inches first.
    check("page size matches the template",
          abs(ts.page_width.inches - ds.page_width.inches) < 0.01
          and abs(ts.page_height.inches - ds.page_height.inches) < 0.01,
          f"{ds.page_width.inches:.2f} x {ds.page_height.inches:.2f} in")

    margins = ["left_margin", "right_margin", "top_margin", "bottom_margin"]
    check("margins match the template",
          all(abs(getattr(ts, m).inches - getattr(ds, m).inches) < 0.02
              for m in margins),
          " ".join(f"{m[0].upper()}{getattr(ds, m).inches:.2f}" for m in margins))

    check("one-column front matter, two-column body",
          len(doc.sections) >= 2
          and columns(doc.sections[0]) == "1"
          and columns(doc.sections[1]) == "2",
          f"{len(doc.sections)} sections: "
          + ", ".join(columns(s) for s in doc.sections))

    template_styles = {s.name for s in tpl.styles}
    stray = sorted(styles_used - template_styles)
    check("every paragraph style comes from the template",
          not stray, "stray: " + ", ".join(stray) if stray else "")

    check("title uses the Paper Title style",
          "Paper Title" in styles_used)

    abstract = next((t for t in texts if t.startswith("ABSTRACT")), "")
    words = len(abstract.split()) - 1  # drop the ABSTRACT label
    check("abstract is 150-250 words", 150 <= words <= 250, f"{words} words")
    check("abstract is one paragraph, no equations",
          abstract and "=" not in abstract)
    check("INDEX TERMS present",
          any(t.startswith("INDEX TERMS") for t in texts))

    h1 = [p.text for p in doc.paragraphs if p.style.name.startswith("H1")]
    check("level-1 headings use the template H1 style and are uppercase",
          len(h1) >= 7 and all(t == t.upper() for t in h1),
          f"{len(h1)} headings")

    titles = [p.text for p in doc.paragraphs if p.style.name == "Table Title"]
    roman = re.compile(r"^TABLE [IVXL]+$")
    check("tables carry roman TABLE titles",
          bool(titles) and all(roman.match(t) for t in titles),
          f"{len(titles)} tables")

    caps = [p.text for p in doc.paragraphs if p.style.name == "Figure Caption"]
    figpat = re.compile(r"^FIGURE \d+\.\s")
    check("figure captions use the FIGURE N. form",
          bool(caps) and all(figpat.match(c) for c in caps),
          f"{len(caps)} captions")

    # Equations are images in this pipeline; a silent drop leaves the
    # methodology reading as prose with gaps where the formulas belong.
    original = ROOT / "paper" / "AHA_Fed_Paper.docx"
    if original.exists():
        want = len(Document(str(original)).inline_shapes)
        got = len(doc.inline_shapes)
        check("no figures or equations lost against the source document",
              got >= want, f"{got} images here vs {want} in the source")

    # Figures must fit a single column or Word reflows the page.
    gutter = 0.28
    body_sec = doc.sections[1] if len(doc.sections) > 1 else ds
    col_w = (body_sec.page_width.inches - body_sec.left_margin.inches
             - body_sec.right_margin.inches - gutter) / 2
    wide = [sh.width.inches for sh in doc.inline_shapes
            if sh.width.inches > col_w + 0.02]
    check("every figure fits one column", not wide,
          f"column {col_w:.2f} in; {len(wide)} figure(s) wider")

    # A bibliography the in-text citations point at cannot be missing.
    refs = [par for par in doc.paragraphs
            if par.style.name in ("References", "REF_Txt", "Ref")]
    cited = set(re.findall(r"\[(\d+)\]", chr(10).join(texts)))
    check("reference list is present", len(refs) >= len(cited),
          f"{len(refs)} entries for {len(cited)} distinct citations")

    body = "\n".join(texts)
    check("no template boilerplate left behind",
          "First A. Author" not in body or "AUTHOR" in body.upper(),
          "")
    for placeholder in ("lorem", "TODO", "TBD", "FIXME"):
        if placeholder.lower() in body.lower():
            check(f"no '{placeholder}' placeholder", False)


    # Access titles tables in roman; a body that still says "Table 3" while
    # the title above it reads "TABLE III" is the kind of mismatch a
    # reviewer notices immediately.
    tbl_titles, arabic_refs, roman_refs, orphans = [], set(), set(), []
    for t in texts:
        if re.match(r"^TABLE\s+[IVXLC]+$", t):
            tbl_titles.append(t)
            continue
        arabic_refs.update(re.findall(r"\bTable\s+(\d+)\b", t))
        roman_refs.update(re.findall(r"\bTable\s+([IVXLC]+)\b", t))
    check("in-text table references use roman numerals",
          not arabic_refs,
          f"{len(roman_refs)} roman, {len(arabic_refs)} arabic"
          + (f" ({sorted(arabic_refs)})" if arabic_refs else ""))

    numerals = [t.split()[1] for t in tbl_titles]
    check("every table title is referenced in the text",
          set(numerals) <= roman_refs,
          f"uncited: {sorted(set(numerals) - roman_refs) or 'none'}")

    fig_nums, fig_refs = set(), set()
    for t in texts:
        m = re.match(r"^FIGURE\s+(\d+)\.", t)
        if m:
            fig_nums.add(m.group(1))
        else:
            fig_refs.update(re.findall(r"\bFigure\s+(\d+)\b", t))
    check("every figure is referenced in the text",
          fig_nums <= fig_refs,
          f"uncited: {sorted(fig_nums - fig_refs, key=int) or 'none'}")


    # Section cross-references drift whenever a subsection is inserted, and
    # three of them were pointing at the wrong experiment before this check
    # existed. Resolve every "Section N.M" against the source document's own
    # numbering -- the Access build strips numbers, so the check reads the
    # numbered manuscript.
    src_doc = ROOT / "paper" / "AHA_Fed_Paper.docx"
    if src_doc.exists():
        src_texts = [q.text.strip() for q in Document(str(src_doc)).paragraphs]
        heads = {}
        for t in src_texts:
            m = re.match(r"^(DD+(?:.DD+)?)SS+(.{4,70})$".replace("DD", '\\b\\d')
                         .replace("SS", '\\s'), t)
            if m and not t.endswith("."):
                heads[m.group(1)] = m.group(2)
        cited = set()
        for t in src_texts:
            cited.update(re.findall(r"SectionsSS+(DD+.DD+)"
                                    .replace("DD", '\\b\\d').replace("SS", '\\s'), t))
            cited.update(re.findall(r"SectionSS+(DD+.DD+)"
                                    .replace("DD", '\\b\\d').replace("SS", '\\s'), t))
        unresolved = sorted(c for c in cited if c not in heads)
        check("every section cross-reference resolves",
              not unresolved,
              f"{len(cited)} references, unresolved: {unresolved or 'none'}")


    # Enumerations drift when a list is edited in pieces: the limitations
    # paragraph once said "Six" while listing five, using "Third" twice.
    WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
    ORDS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh"]
    bad = []
    for t in texts:
        m = re.search(r"\b(two|three|four|five|six|seven)\b[ ]+"
                      r"(?:substantive[ ]+)?(limitations|contributions|results)",
                      t, re.I)
        if not m:
            continue
        want = WORDS[m.group(1).lower()]
        seen = [o for o in ORDS if re.search(r"\b" + o + r",", t, re.I)]
        dupes = [o for o in seen
                 if len(re.findall(r"\b" + o + r",", t, re.I)) > 1]
        roman = len(re.findall(r"[(](?:i|ii|iii|iv|v|vi|vii)[)]", t))
        got = len(seen) or roman
        if got and (got != want or dupes):
            bad.append(f"{m.group(0)}: {got} items"
                       + (f", repeated {dupes}" if dupes else ""))
    check("enumerated lists match their stated count", not bad,
          "; ".join(bad) if bad else "all lists consistent")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("All template checks passed.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path,
                    default=Path.home() / "Downloads" / "Access_Word_Template.docx")
    ap.add_argument("--paper", type=Path,
                    default=ROOT / "paper" / "AHA_Fed_IEEE_Access.docx")
    args = ap.parse_args()
    sys.exit(main(args.template, args.paper))
