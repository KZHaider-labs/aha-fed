"""Check the rendered PDF for tokens split across lines by a narrow column.

Word does not hyphenate here, so when a table column is too narrow for
its contents it breaks inside a token rather than overflowing: a p-value
renders as "0.00" above "6", a header as "Aggregato" above "r". Neither
is visible in the source or in the .docx XML, only in the rendered page,
which is why this check drives Word to produce the PDF and reads that.

Two unambiguous signatures:

  - a decimal cut in half: a line ending "0.10" whose next line is "5"
  - a word cut mid-word: a line ending in letters whose next line is one
    or two lowercase letters alone, which is never a real word here

Ordinary wrapping between words produces neither, because a real next
word is three or more characters or begins a phrase. Short function
words that legitimately end a wrapped line are listed in REAL.

Requires Word (COM) and PyMuPDF. Exits 1 if anything is split.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

import fitz

REAL = {"a", "an", "on", "of", "in", "is", "as", "at", "to", "it", "by",
        "or", "and", "for", "the", "its", "was", "are", "not", "any",
        "own", "one", "two", "per", "vs", "we", "no", "so", "up", "if"}


def render(docx_path, pdf_path):
    """Drive Word to produce the PDF a reviewer will actually see."""
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    src = os.path.abspath(docx_path)
    ps = ('$w=New-Object -ComObject Word.Application; $w.Visible=$false; '
          f'$d=$w.Documents.Open("{src}"); '
          f'$d.SaveAs([ref]"{pdf_path}",[ref]17); $d.Close($false); $w.Quit()')
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True, timeout=300)
    return os.path.exists(pdf_path)


def split_tokens(doc):
    hits = []
    for i, page in enumerate(doc):
        for block in page.get_text("blocks"):
            lines = [l.strip() for l in block[4].split("\n") if l.strip()]
            for a, b in zip(lines, lines[1:]):
                if re.search(r"\d\.\d+$", a) and re.fullmatch(r"\d{1,2}", b):
                    hits.append((i + 1, "number", a[-10:], b))
                elif (re.search(r"[A-Za-z]{5,}$", a)
                      and re.fullmatch(r"[a-z]{1,3}", b)
                      and b not in REAL):
                    hits.append((i + 1, "word", a[-14:], b))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="paper/AHA_Fed_IEEE_Access.docx")
    args = ap.parse_args()

    pdf = os.path.join(tempfile.gettempdir(), "aha_rendered_check.pdf")
    if not render(args.paper, pdf):
        print("could not render the document; is Word available?")
        return 2

    doc = fitz.open(pdf)
    hits = split_tokens(doc)
    for pg, kind, a, b in hits:
        print('page %2d  %-6s  "%s" / "%s"' % (pg, kind, a, b))
    print("\n%d token(s) split across lines in %d pages"
          % (len(hits), len(doc)))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
