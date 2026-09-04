"""Turn plain-text math in the prose into inline Word equations.

The manuscript writes variables as ASCII ("q_k", "n_min", "e^{s_k}",
"alpha.log n_k"), which renders as literal underscores and carets beside
properly typeset display equations. This module finds those forms and
emits inline OMML for them, so a subscript is a subscript.

Only unambiguous patterns are converted. Prose words that merely contain
an underscore, and anything inside a citation bracket, are left alone.
"""
import re

from paper.omml import run as r, op, sub, sup, math

# single letters that are variables in this paper, plus Greek
_VAR = r"[A-Za-z\u0391-\u03c9\u2211\u0303]"

# q_k, n_min, D_max, B_m, s_j ...
SUBSCRIPT = re.compile(rf"(?<![A-Za-z0-9_])({_VAR}{{1,4}})_([A-Za-z0-9]+)(?![A-Za-z0-9_])")
# e^{s_k}, e^S
SUPERSCRIPT = re.compile(rf"(?<![A-Za-z0-9])({_VAR})\^\{{?([A-Za-z0-9_]+)\}}?")


def _sub_element(base: str, subscript: str):
    """base_subscript, with the subscript itself possibly a variable."""
    return sub(r(base), r(subscript))


def _sup_element(base: str, superscript: str):
    inner = superscript
    m = SUBSCRIPT.fullmatch(inner)
    if m:
        return sup(r(base), _sub_element(m.group(1), m.group(2)))
    return sup(r(base), r(inner))


def split(text: str):
    """Split prose into (kind, payload) pieces.

    kind is "text" for a literal run, or "math" for a list of OMML
    elements. Callers emit each piece in order.
    """
    # A middle dot between a coefficient and a term reads as
    # multiplication; IEEE sets that as juxtaposition, not a visible dot.
    text = re.sub(r"([A-Za-z\u03b1-\u03c9])\u00b7(?=[A-Za-z\u03b1-\u03c9(])", r"\1 ", text)
    pieces, i = [], 0
    pattern = re.compile(
        SUPERSCRIPT.pattern + "|" + SUBSCRIPT.pattern)
    for m in pattern.finditer(text):
        if m.start() > i:
            pieces.append(("text", text[i:m.start()]))
        if m.group(1) is not None:          # superscript form
            pieces.append(("math", [_sup_element(m.group(1), m.group(2))]))
        else:                                # subscript form
            pieces.append(("math", [_sub_element(m.group(3), m.group(4))]))
        i = m.end()
    if i < len(text):
        pieces.append(("text", text[i:]))
    return pieces


def has_math(text: str) -> bool:
    return bool(SUBSCRIPT.search(text) or SUPERSCRIPT.search(text))
