"""Build real Word equations (OMML) instead of embedding images.

Images cannot be copied, searched, or re-typeset, and IEEE production has
to reset them by hand. Word's native math (Office MathML) is editable,
scales with the font, and survives conversion to the publisher's format.

This module emits the OMML XML directly. python-docx has no math API, so
the elements are built with lxml against the m: namespace and inserted
into a paragraph.
"""
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement

# python-docx knows the w: namespace but not m:; register it once.
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
nsmap.setdefault("m", M)


def _m(tag):
    return OxmlElement(f"m:{tag}")


def run(text, *, italic=True):
    """A math run. Variables are italic, operators and digits upright."""
    r = _m("r")
    if not italic:
        rpr = _m("rPr")
        sty = _m("sty")
        sty.set(qn("m:val"), "p")          # plain: upright
        rpr.append(sty)
        r.append(rpr)
    t = _m("t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def op(text):
    """An operator or punctuation: upright, with thin spacing kept."""
    return run(text, italic=False)


def sub(base, subscript):
    """base_subscript"""
    e = _m("sSub")
    b = _m("e"); b.append(base)
    s = _m("sub"); s.append(subscript)
    e.append(b); e.append(s)
    return e


def sup(base, superscript):
    """base^superscript"""
    e = _m("sSup")
    b = _m("e"); b.append(base)
    s = _m("sup"); s.append(superscript)
    e.append(b); e.append(s)
    return e


def subsup(base, subscript, superscript):
    e = _m("sSubSup")
    b = _m("e"); b.append(base)
    s = _m("sub"); s.append(subscript)
    p = _m("sup"); p.append(superscript)
    e.append(b); e.append(s); e.append(p)
    return e


def frac(num_children, den_children):
    """A built-up fraction."""
    f = _m("f")
    n = _m("num")
    for c in num_children:
        n.append(c)
    d = _m("den")
    for c in den_children:
        d.append(c)
    f.append(n); f.append(d)
    return f


def nary(char, sub_children, sup_children, body_children, *, limloc="undOvr"):
    """Big operator (sum, product) with limits above and below."""
    n = _m("nary")
    pr = _m("naryPr")
    ch = _m("chr"); ch.set(qn("m:val"), char); pr.append(ch)
    ll = _m("limLoc"); ll.set(qn("m:val"), limloc); pr.append(ll)
    if not sup_children:
        h = _m("supHide"); h.set(qn("m:val"), "1"); pr.append(h)
    if not sub_children:
        h = _m("subHide"); h.set(qn("m:val"), "1"); pr.append(h)
    n.append(pr)
    s = _m("sub")
    for c in sub_children:
        s.append(c)
    n.append(s)
    p = _m("sup")
    for c in sup_children:
        p.append(c)
    n.append(p)
    e = _m("e")
    for c in body_children:
        e.append(c)
    n.append(e)
    return n


def func(name, arg_children):
    """A named function such as log or exp, set upright."""
    f = _m("func")
    fn = _m("fName")
    fn.append(op(name))
    f.append(fn)
    e = _m("e")
    for c in arg_children:
        e.append(c)
    f.append(e)
    return f


def delim(children, *, left="(", right=")"):
    """Bracketed group that grows with its content."""
    d = _m("d")
    pr = _m("dPr")
    b = _m("begChr"); b.set(qn("m:val"), left); pr.append(b)
    en = _m("endChr"); en.set(qn("m:val"), right); pr.append(en)
    d.append(pr)
    e = _m("e")
    for c in children:
        e.append(c)
    d.append(e)
    return d


def brk():
    """A hard line break inside an equation.

    IEEE breaks a long display equation before a binary operator rather
    than letting Word wrap it, which strands the equation number.
    """
    r = _m("r")
    rpr = _m("rPr")
    brk = _m("brk")
    rpr.append(brk)
    r.append(rpr)
    return r


def set_size(element, pt):
    """Force a point size on every run inside an OMML element.

    Word otherwise sizes inline math from the document default, so a
    variable in an 8 pt block comes out at 11 pt.
    """
    half = str(int(round(pt * 2)))
    for r in element.iter(f"{{{M}}}r"):
        rpr = r.find(f"{{{M}}}rPr")
        if rpr is None:
            rpr = _m("rPr")
            r.insert(0, rpr)
        wpr = r.find(qn("w:rPr"))
        if wpr is None:
            wpr = OxmlElement("w:rPr")
            r.insert(list(r).index(rpr) + 1, wpr)
        for tag in ("w:sz", "w:szCs"):
            el = wpr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                wpr.append(el)
            el.set(qn("w:val"), half)
    return element


def math(children, size_pt=None):
    """Wrap children in an oMath element ready to drop into a paragraph."""
    m = _m("oMath")
    for c in children:
        m.append(c)
    if size_pt is not None:
        set_size(m, size_pt)
    return m


def add_math(paragraph, children):
    """Append an OMML equation to a python-docx paragraph."""
    paragraph._p.append(math(children))
    return paragraph
