"""Check the assembled prose in build_paper.py for joining defects.

Prose is built by concatenating string literals, and two defects follow
from that: a fragment ending in punctuation loses the space after it
("only,PathMNIST"), and a fragment opening with punctuation leaves a
space in front of it ("per round , PathMNIST"). Neither is visible in
the source line, only once the fragments are joined, so this joins them
the way the builder does and reads the result.

Checking the source rather than the .docx avoids the inline equations,
which read as gaps in the rendered text and produce false positives
faster than they produce findings.
"""
import io
import re
import sys

SRC = "paper/build_paper.py"

# one string literal, allowing escaped characters inside it
LITERAL = r'"(?:[^"\\]|\\.)*"'


def joined_runs(text):
    """Yield (line number, concatenation) for each run of adjacent literals."""
    run = re.compile(r'(?:' + LITERAL + r'\s*\n?\s*){2,}')
    piece = re.compile(LITERAL)
    for m in run.finditer(text):
        parts = [p[1:-1] for p in piece.findall(m.group(0))]
        yield text[:m.start()].count("\n") + 1, "".join(parts)


def main():
    text = io.open(SRC, encoding="utf8").read()
    bad = []
    for line_no, joined in joined_runs(text):
        for m in re.finditer(r"\s[,;.](?:\s|$)", joined):
            bad.append((line_no, "space before",
                        joined[max(0, m.start() - 34):m.end() + 16]))
        for m in re.finditer(r"[a-z][,;](?=[A-Za-z0-9])", joined):
            bad.append((line_no, "space lost",
                        joined[max(0, m.start() - 34):m.end() + 16]))
    for line_no, kind, frag in bad:
        print("%s:%d  %-13s ...%s..." % (SRC, line_no, kind, frag.strip()))
    print("\n%d joining defect(s)" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
