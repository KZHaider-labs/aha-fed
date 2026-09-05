"""Check the generated manuscript against the official IEEE Access template.

Compares page setup, column structure, styles and the front-matter
conventions Access requires, so formatting regressions surface here rather
than in a desk rejection.

Usage:
    python paper/check_ieee_compliance.py [--template PATH] [--paper PATH]
"""
from __future__ import annotations

import argparse
import datetime
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

    # The template sets both the "TABLE I" line and the caption text in
    # Table Title, so count the title lines and check they are roman and
    # consecutive.
    tt = [p.text.strip() for p in doc.paragraphs
          if p.style.name in ("Table Title", "Table Caption")]
    roman = re.compile(r"^TABLE ([IVXL]+)$")
    titles = [t for t in tt if roman.match(t)]
    ROM = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
           "XI", "XII"]
    want = [f"TABLE {r}" for r in ROM[:len(titles)]]
    check("tables carry consecutive roman TABLE titles",
          bool(titles) and titles == want,
          f"{len(titles)} tables"
          + ("" if titles == want else f"; got {titles[:4]}"))

    caps = [p.text.strip() for p in doc.paragraphs
            if p.style.name in ("Fig Caption", "Figure Caption")
            and p.text.strip()]
    # The template's Fig Caption style supplies "FIGURE n." itself, so a
    # prefix in the text would print twice.
    dup = [c[:40] for c in caps if re.match(r"^FIGURE\s+\d+\s*[.:]", c, re.I)]
    check("figure captions are not double-numbered",
          bool(caps) and not dup,
          f"{len(caps)} captions"
          + (f"; {len(dup)} carry their own prefix" if dup else ""))

    # A silent drop leaves the methodology reading as prose with gaps
    # where the formulas belong. The source document carries equations as
    # images; this build renders them as native Word math, so the two are
    # counted separately.
    n_omml = doc.element.body.xml.count("<m:oMath")
    check("equations are native Word math, not images",
          n_omml >= 9, f"{n_omml} OMML equations")

    original = ROOT / "paper" / "AHA_Fed_Paper.docx"
    if original.exists():
        src = Document(str(original))
        src_imgs = len(src.inline_shapes)
        got = len(doc.inline_shapes) + n_omml
        check("no figures or equations lost against the source document",
              got >= src_imgs,
              f"{len(doc.inline_shapes)} figures + {n_omml} equations "
              f"= {got} vs {src_imgs} in the source")

    # A figure may span both columns -- IEEE allows it and the
    # architecture diagram needs it -- but none may exceed the text
    # block, which would overflow the page.
    gutter = 0.28
    body_sec = doc.sections[1] if len(doc.sections) > 1 else ds
    text_w = (body_sec.page_width.inches - body_sec.left_margin.inches
              - body_sec.right_margin.inches)
    col_w = (text_w - gutter) / 2
    over = [sh.width.inches for sh in doc.inline_shapes
            if sh.width.inches > text_w + 0.02]
    spanning = [sh.width.inches for sh in doc.inline_shapes
                if col_w + 0.02 < sh.width.inches <= text_w + 0.02]
    check("no figure exceeds the text width", not over,
          f"{len(spanning)} span both columns"
          + (f"; {len(over)} overflow" if over else ""))

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
    for i, t in enumerate(texts):
        m = re.search(r"\b(two|three|four|five|six|seven)\b[ ]+"
                      r"(?:substantive[ ]+)?(limitations|contributions|results)",
                      t, re.I)
        if not m:
            continue
        want = WORDS[m.group(1).lower()]
        # A list may span paragraphs. Gather following ones while they
        # keep contributing ordinals, stopping at a heading or at another
        # paragraph that announces its own count.
        ORD_RE = r"\b(" + "|".join(ORDS) + r"),"
        ROM_RE = r"[(](?:i|ii|iii|iv|v|vi|vii)[)]"
        span = [t]
        for nxt in texts[i + 1:]:
            if not nxt.strip():
                continue
            if nxt.isupper() and len(nxt.split()) < 12:
                break
            if re.search(r"\b(two|three|four|five|six|seven)\b[ ]+"
                         r"(?:substantive[ ]+)?(limitations|contributions|results)",
                         nxt, re.I):
                break
            if not re.search(ORD_RE, nxt, re.I) and not re.search(ROM_RE, nxt):
                break
            span.append(nxt)
        joined = " ".join(span)
        seen = [o for o in ORDS if re.search(r"\b" + o + r",", joined, re.I)]
        dupes = [o for o in seen
                 if len(re.findall(r"\b" + o + r",", joined, re.I)) > 1]
        roman = len(re.findall(ROM_RE, joined))
        got = len(seen) or roman
        if got and (got != want or dupes):
            bad.append(f"{m.group(0)}: {got} items"
                       + (f", repeated {dupes}" if dupes else ""))
    check("enumerated lists match their stated count", not bad,
          "; ".join(bad) if bad else "all lists consistent")


    # Citation integrity: every [n] in the prose must resolve, and every
    # listed reference should be cited. [6] FedHeal was listed but never
    # cited because both mentions pointed at [13], a different paper.
    entries, cites = {}, set()
    for t in texts:
        m = re.match(r"^\[(\d+)\] +(.{10,})", t)
        if m:
            entries[int(m.group(1))] = m.group(2)
            continue
        for grp in re.findall(r"\[([\d,\s-]+)\]", t):
            # skip intervals like [0, 1] -- a reference id is never 0
            nums = [int(n) for n in re.findall(r"\d+", grp)]
            if 0 in nums:
                continue
            cites.update(nums)
    dangling = sorted(c for c in cites if c not in entries)
    uncited = sorted(e for e in entries if e not in cites)
    check("every in-text citation resolves to a reference",
          not dangling, f"dangling: {dangling or chr(110)+chr(111)+chr(110)+chr(101)}")
    check("every listed reference is cited",
          not uncited, f"uncited: {uncited or chr(110)+chr(111)+chr(110)+chr(101)}")


    # Access closes with one biography per author. The paper had none
    # until the author block was filled in.
    bio_paras = [pp for pp in doc.paragraphs
                 if pp.style.name in ("AU_Bios", "Author Bios", "Biography")
                 and pp.text.strip()]
    # The author line carries superscript affiliation marks, so
    # str.isupper() is False; test the letters only.
    def _is_author_line(t):
        # IEEE sets the names in caps but keeps a lowercase "and"
        letters = [c for c in re.sub(r"(?<![A-Za-z])and(?![A-Za-z])", "", t)
                   if c.isalpha()]
        return (letters and all(c.isupper() for c in letters)
                and "," in t and 10 < len(t) < 250
                and not t.startswith(("ABSTRACT", "INDEX", "TABLE",
                                      "FIGURE")))
    authors_line = next((t for t in texts[:12] if _is_author_line(t)), "")
    n_authors = len(re.split(r",|(?<![A-Za-z])and(?![A-Za-z])",
                             authors_line)) if authors_line else 0
    n_authors = len([x for x in re.split(r",| and ", authors_line)
                     if x.strip()]) if authors_line else 0
    check("one author biography per author",
          bool(bio_paras) and len(bio_paras) == n_authors,
          f"{len(bio_paras)} biographies for {n_authors} authors")
    todo = [b.text[:40] for b in bio_paras if "TO BE SUPPLIED" in b.text]
    check("author biographies are written",
          not todo,
          f"{len(todo)} still placeholders" if todo else "all written")

    # Variables written in ASCII ("q_k", "e^{s_k}") render as literal
    # underscores and carets beside properly typeset displays.
    body = " ".join(t for t in texts if not t.startswith("["))
    leftovers = {
        "subscripts": re.findall(r"\b[A-Za-z]{1,4}_[A-Za-z0-9]+", body),
        "carets": re.findall(r"\^", body),
        "sigma": re.findall(r"\u03a3_", body),
    }
    found = {k: len(v) for k, v in leftovers.items() if v}
    check("prose math is typeset, not ASCII",
          not found, str(found) if found else "no ASCII math left")

    # Section numbering: I, II, III with subsections restarting at A.
    # The template numbers headings from three unrelated lists that
    # never reset against each other, which ran the letters A..Z
    # straight across the paper and numbered REFERENCES as a section.
    ROM = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
    sec, sub, bad_head = 0, 0, []
    for pp in doc.paragraphs:
        t = pp.text.strip()
        if not t:
            continue
        if pp.style.name.startswith("H1"):
            if t.upper().startswith(("REFERENCES", "ACKNOWLEDG",
                                     "APPENDIX")):
                continue
            sec += 1
            sub = 0
            want = ROM[sec - 1] + "." if sec <= len(ROM) else None
            if want and not t.startswith(want):
                bad_head.append(f"{t[:26]} (want {want})")
        elif pp.style.name.startswith("H2"):
            sub += 1
            want = chr(ord("A") + sub - 1) + "."
            if not t.startswith(want):
                bad_head.append(f"{t[:26]} (want {want})")
    check("sections number I..N with subsections restarting at A",
          not bad_head,
          "; ".join(bad_head[:3]) if bad_head else
          f"{sec} sections")

    # References are alphabetical by first author, with no gaps.
    entries = {}
    for t in texts:
        m = re.match(r"^\[(\d+)\] +(.{6,})", t)
        if m:
            entries[int(m.group(1))] = m.group(2)
    if entries:
        sur = [entries[n].split(".")[0].split(",")[0].strip()
               for n in sorted(entries)]
        check("the reference list is alphabetical by first author",
              sur == sorted(sur, key=str.lower),
              f"{len(sur)} entries")

    # Punctuation faults the em-dash removal introduced: a comma with
    # no space after it, and a semicolon followed by a conjunction,
    # which is what a paired dash becomes if only one end is converted.
    prose = " ".join(t for t in texts if not t.startswith("["))
    nospace = re.findall(r"[a-z],[a-z]{2,}", prose)
    # A semicolon before "and" is correct when it separates the last two
    # items of a list whose items contain commas, so judge by the whole
    # sentence: two or more semicolons means a list, exactly one means
    # the fault.
    semiconj = []
    for sent in re.split(r"(?<=[.!?])\s+", prose):
        if sent.count(";") == 1 and re.search(r";\s+(?:and|that|which)\s", sent):
            semiconj.append(sent[:60])
    faults = []
    if nospace:
        faults.append(f"{len(nospace)} commas without a space")
    if semiconj:
        faults.append(f"{len(semiconj)} semicolons before a conjunction")
    check("no punctuation left broken by the dash removal",
          not faults, "; ".join(faults) if faults else "clean")

    # A figure squeezed below about an inch has unreadable axis labels;
    # one taller than the column crowds out the text beside it.
    heights = [doc.inline_shapes[i].height.inches
               for i in range(len(doc.inline_shapes))]
    cramped = [round(h, 2) for h in heights if h < 1.25]
    check("no figure is too short to read",
          not cramped, f"{len(cramped)} under 1.25 in: {cramped}"
          if cramped else f"{len(heights)} figures")

    # A table cell holding only a comma is a placeholder dash the
    # em-dash removal ate.
    stray = sum(1 for t in doc.tables for r in t.rows for c in r.cells
                if c.text.strip() == ",")
    check("no table cell is a bare comma", not stray,
          f"{stray} cells" if stray else "clean")

    # Times New Roman has no glyph for the mathematical-alphanumeric
    # block, so those characters print as empty boxes.
    script = [c for t in texts for c in t if 0x1D400 <= ord(c) <= 0x1D7FF]
    check("no unrenderable maths-script characters", not script,
          f"{len(script)} found" if script else "clean")

    # The mirror of the lost-space defect ("per round , PathMNIST")
    # lives in build_paper.py, where the prose is assembled. Checking it
    # here would mean sifting OMML gaps out of the rendered text, which
    # produces more false positives than findings; check_source.py reads
    # the source strings instead, where a space before punctuation is
    # unambiguous.

    # A list was once shipped in which real papers had been relabelled
    # into journals with invented volumes and "a 2022 retrospective"
    # style suffixes on their titles. The tells below catch six of the
    # eight worst entries from that list, but they are only tells: a
    # fabrication with a clean title and a plausible volume passes here.
    # verify_references.py resolves each entry against Crossref and is
    # the check that actually establishes a reference exists; run it
    # whenever the list changes.
    refs = []
    for t in texts:
        m = re.match(r"^\[(\d+)\] +(.{6,})", t.strip())
        if m:
            refs.append(m.group(2))
    if refs:
        # A reference dated in the current year or later cannot have been
        # read while this work was done, so it wants a human to confirm it
        # exists. Two entries dated 2026 in an earlier list did not.
        cutoff = datetime.date.today().year
        suspicious = []
        for r in refs:
            years = [int(y) for y in re.findall(r"(?:19|20)\d\d", r)]
            if years and max(years) >= cutoff:
                suspicious.append(("unverifiable year", r))
            elif re.search(r"(?:a )?20\d\d (?:retrospective|update)"
                           r"|revisited|in the wild", r, re.I):
                suspicious.append(("retitled", r))
        check("no reference looks retitled or post-dated", not suspicious,
              "; ".join(f"{why}: {r[:48]}" for why, r in suspicious[:3])
              if suspicious else f"{len(refs)} entries")

        # IEEE sets the bracketed number flush left with the entry text
        # indented under it. The template style indents the whole block,
        # which reads as a long quotation.
        ref_paras = [p for p in doc.paragraphs
                     if re.match(r"^\[\d+\] ", p.text.strip())]
        if ref_paras:
            hung = sum(1 for p in ref_paras
                       if (p.paragraph_format.first_line_indent or 0) < 0)
            check("reference entries use a hanging indent",
                  hung == len(ref_paras),
                  f"{hung}/{len(ref_paras)} hung")

        no_venue = [r for r in refs if not re.search(
            r"In Proceedings|Conference|Symposium|Workshop|Transactions"
            r"|Journal|IEEE|ACM|Nature|Science|Medical|Pattern|Radiology"
            r"|npj|Neurocomputing|Foundations|PMLR|NeurIPS|ICLR|MLSys"
            r"|Scientific|Lancet|Cell|PLOS|BMJ|Informatics|Access", r)]
        check("every reference names a venue", not no_venue,
              no_venue[0][:60] if no_venue else f"{len(refs)} entries")
    # Building prose by concatenating string literals loses the space
    # whenever a fragment ends in punctuation, giving "only,PathMNIST".
    # Digit groups (1,000) and URLs are legitimate.
    jammed = []
    for t in texts:
        # a letter then punctuation then a letter or digit; "1,000"
        # is a digit on both sides and so never matches
        for m in re.finditer(r"[a-z][,;](?=[A-Za-z0-9])", t):
            frag = t[max(0, m.start() - 26):m.end() + 20]
            if "//" in frag or "http" in frag:
                continue
            jammed.append(frag.strip())
    check("no space lost where prose fragments were joined", not jammed,
          f"{len(jammed)}: {jammed[0][:46]}" if jammed else "clean")

    # The template ships literal page numbers in its sample footers, so
    # without a PAGE field every page of the body renders the same digit.
    lit = 0
    for sec in doc.sections:
        for p in sec.footer.paragraphs:
            xml = p._p.xml
            if re.search(r">\s*\d+\s*<", xml) and "PAGE" not in xml:
                lit += 1
    check("footers number pages with a field, not literal text", not lit,
          f"{lit} literal" if lit else "PAGE fields")

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
