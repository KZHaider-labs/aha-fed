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
