"""Extract the manuscript from build_paper.py so other renderers can reuse it.

build_paper.py builds the document by calling add_heading / add_paragraph /
add_figure / make_table in order. Rather than duplicating that text into a
second file — which would drift the moment either is edited — this runs the
builder against a recording stub and captures the calls in sequence.

Produces:
    SECTIONS : [("h1"|"h2"|"p"|"fig"|"table"|"ref", payload), ...] in order
    FIGURES  : {index: (filename, caption)}
    TABLES   : {index: (rows, caption)}

Usage:
    from paper.extract_sections import extract
    sections, figures, tables = extract()
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


def references_from_source() -> list[tuple[str, str]]:
    """Read the reference list straight out of build_paper's source.

    build_paper emits references with doc.add_paragraph() rather than its own
    helper, so the recording stubs never see them. Rather than duplicate the
    list here, evaluate the literal from the source file.
    """
    import ast

    src = (ROOT / "paper" / "build_paper.py").read_text(encoding="utf8")
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", None) == "references" for t in node.targets)
                and isinstance(node.value, ast.List)):
            return [tuple(ast.literal_eval(e)) for e in node.value.elts]
    return []


def extract() -> tuple[list, dict, dict]:
    sections: list = []
    figures: dict = {}
    tables: dict = {}
    pending_caption = {"table": None}

    def rec_heading(doc, text, level=1):
        sections.append((f"h{min(level, 2)}", text))

    def rec_paragraph(doc, text, **kw):
        if text and text.strip():
            sections.append(("p", text))

    def rec_equation(doc, name, label, **kw):
        # Equations are images in build_paper; without them the Access
        # build reads as prose with gaps where the formulas belong.
        sections.append(("eq", (name, label)))

    def rec_figure(doc, path, caption, **kw):
        idx = len(figures)
        figures[idx] = (Path(str(path)).name, caption)
        sections.append(("fig", idx))

    def rec_table_caption(doc, caption, **kw):
        pending_caption["table"] = caption

    def rec_table(doc, rows, **kw):
        idx = len(tables)
        tables[idx] = ([[str(c) for c in row] for row in rows],
                       pending_caption["table"] or "")
        pending_caption["table"] = None
        sections.append(("table", idx))

    # Equation images and spacing helpers carry no text; swallow them.
    noop = lambda *a, **k: None  # noqa: E731

    sys.path.insert(0, str(ROOT))
    import paper.build_paper as bp

    with mock.patch.object(bp, "add_heading", rec_heading), \
         mock.patch.object(bp, "add_paragraph", rec_paragraph), \
         mock.patch.object(bp, "add_figure", rec_figure), \
         mock.patch.object(bp, "add_table_caption", rec_table_caption), \
         mock.patch.object(bp, "make_table", rec_table), \
         mock.patch.object(bp, "add_equation_image", rec_equation), \
         mock.patch.object(bp, "add_post_table_spacing", noop), \
         mock.patch.object(bp, "add_bullet_run", noop):
        # build() saves a docx as a side effect. build_paper does
        # `from docx import Document`, so the name to patch is the one bound
        # in that module — patching docx.Document leaves it untouched and the
        # real manuscript gets overwritten with a figure-less copy.
        doc = mock.MagicMock()
        with mock.patch.object(bp, "Document", return_value=doc):
            bp.build()

    # References live outside the recorded helpers; append them so renderers
    # do not silently drop a bibliography that 34 in-text citations rely on.
    refs = references_from_source()
    if refs:
        sections.append(("h1", "References"))
        for tag, body in refs:
            sections.append(("ref", f"{tag} {body}"))

    return sections, figures, tables


if __name__ == "__main__":
    secs, figs, tabs = extract()
    kinds = {}
    for k, _ in secs:
        kinds[k] = kinds.get(k, 0) + 1
    print("extracted:", kinds)
    print(f"figures: {len(figs)}  tables: {len(tabs)}")
    print("\nfirst few headings:")
    for k, v in secs[:12]:
        if k.startswith("h"):
            print(f"  [{k}] {v}")
