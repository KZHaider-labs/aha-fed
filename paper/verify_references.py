"""Resolve every reference against Crossref and report what does not exist.

A reference list is the one part of a paper a reviewer can check without
reading it, so it is the one part that must never be invented. This script
takes each entry's title, asks Crossref for the best match, and reports the
similarity along with the venue and year Crossref holds. Anything that does
not resolve, or resolves to a different year or container, is printed for a
human to look at. It is deliberately advisory rather than a hard gate:
Crossref does not index every conference proceedings, so a low score means
"check this by hand", not "this is fake".
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

from docx import Document

MAILTO = "itswahib6@gmail.com"          # Crossref asks for a contact
UA = "AHA-Fed-ref-check/1.0 (mailto:%s)" % MAILTO


def entries(path):
    """Pull (number, text) for each reference out of the built document."""
    out = []
    for p in Document(path).paragraphs:
        m = re.match(r"^\[(\d+)\]\s+(.+)", p.text.strip())
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def title_of(text):
    """The title is what sits between the author list and the venue.

    Author lists end in "et al." or in a run of surname/initial pairs, where
    an initial may be hyphenated ("Q.-V.", "P.-A.") or a particle may carry
    a lowercase word ("van der Maaten", "Ogier du Terrail"). Splitting on
    ". " alone cuts inside those and hands Crossref nothing but surnames.
    """
    body = text
    m = re.match(r"^.*?et\s+al\.\s+", body)
    if m:
        return re.split(r"\.\s+(?=[A-Z])", body[m.end():])[0].strip(" .")
    # walk author groups off the front: "Surname, A. B.," / "Surname, A.-B.,"
    pat = re.compile(r"^[A-Z][\w'\-]+(?:\s+[a-z]+)*(?:\s+[A-Z][\w'\-]+)*,"
                     r"(?:\s*[A-Z]\.(?:-[A-Z]\.)*)+,?\s*")
    while True:
        m = pat.match(body)
        if not m:
            break
        body = body[m.end():]
    return re.split(r"\.\s+(?=[A-Z])", body)[0].strip(" .")


def query(title):
    url = ("https://api.crossref.org/works?rows=1&select=title,container-title,"
           "issued,DOI,type&query.bibliographic=" + urllib.parse.quote(title))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.load(r)["message"]["items"]
    if not items:
        return None
    it = items[0]
    return {
        "title": (it.get("title") or [""])[0],
        "venue": (it.get("container-title") or [""])[0],
        "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "doi": it.get("DOI", ""),
        "type": it.get("type", ""),
    }


def claimed_year(text):
    yrs = re.findall(r"\b(19|20)(\d\d)\b", text)
    return int(yrs[-1][0] + yrs[-1][1]) if yrs else None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "paper/AHA_Fed_Paper.docx"
    bad = 0
    for n, text in entries(path):
        t = title_of(text)
        try:
            hit = query(t)
        except Exception as exc:                      # network, rate limit
            print("[%2d] LOOKUP FAILED  %s (%s)" % (n, t[:60], exc))
            bad += 1
            continue
        if not hit:
            print("[%2d] NO MATCH       %s" % (n, t[:70]))
            bad += 1
            continue
        score = SequenceMatcher(None, t.lower(), hit["title"].lower()).ratio()
        cy, hy = claimed_year(text), hit["year"]
        flag = "ok "
        note = ""
        if score < 0.75:
            flag, note = "TTL", "-> %s" % hit["title"][:60]
            bad += 1
        elif cy and hy and abs(cy - hy) > 0:
            flag, note = "YR ", "claimed %s, Crossref %s" % (cy, hy)
            bad += 1
        print("[%2d] %s %.2f  %-52s %s" % (n, flag, score, t[:52], note))
        if flag != "ok ":
            print("          venue: %s (%s)  doi:%s" % (hit["venue"][:60], hit["type"], hit["doi"]))
        time.sleep(0.3)                               # be polite to Crossref
    print("\n%d entr%s need a human look" % (bad, "y" if bad == 1 else "ies"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
