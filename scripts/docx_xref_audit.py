"""Outward citation audit for the SUBMISSION DOCX.

WHY THIS EXISTS
---------------
2026-08-10, the audit-the-auditors pass. The vault's citation chain runs in two
directions and neither of them reaches the file being submitted:

    verbatim_audit.py   wiki source page  ->  the PDF it cites   (is the quote real?)
    xref_audit.py       wiki synthesis    ->  wiki source page   (is the page anchored?)

Both walk `wiki/`. The dissertation master is a .docx sitting outside the vault
entirely, so no script has ever checked that ITS in-text page citations are
anchored in the wiki. The gap was masked because the chapter mirrors in
`wiki/synthesis/dissertation-drafts/` used to track the master, so auditing them
was a proxy for auditing it. Since 2026-07-25 every drafting session has edited
the docx alone and the mirrors lag by the whole v14 -> v29 sequence. The proxy
stopped being a proxy and nothing noticed, because the thing that would have
noticed audits the proxy.

WHAT IT CHECKS
--------------
Every `(Author, YEAR, p. N)` / `(Author et al., YEAR, pp. N-M)` in the docx body
is resolved to a source page in `wiki/sources/`, and each cited page must carry
an anchored quote in that page's `## Quotes` section. Same anchor grammar as
quote_audit.py (bare `p.5` and `(p.5)` both count; comma lists and ranges are
parsed, not eyeballed).

WHAT IT DOES NOT CHECK
----------------------
  * Whether the quote at that page SUPPORTS the claim. Semantic fit is a model
    job; range containment passing while semantics failed is exactly how
    Toernberg 2026 p.18 survived the 2026-08-05 checklist.
  * Citations with no page number (gist and whole-text references, which the
    Handbook exempts).
  * The bibliography. Orphan and missing entries are a separate check.

Multi-author citations resolve on ANY surname in the citation, not just the
last one, because "(Lane, Do and Molina-Rogers, 2022, p. 332)" read
last-surname-first resolves to nothing and reports a false miss.

Usage: python docx_xref_audit.py --docx PATH [--vault DIR] [--quiet]
Exit:  0 = every cited page anchored; 1 = an unanchored or unresolvable citation.
"""

import argparse
import os
import pathlib
import re
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

CITE = re.compile(
    r"([A-Z][A-Za-z\u00C0-\u024F'\u2019-]+"
    r"(?:\s*,\s*[A-Z][A-Za-z\u00C0-\u024F'\u2019-]+)*"
    r"(?:\s+(?:and|&)\s+[A-Z]?[A-Za-z\u00C0-\u024F'\u2019-]+)?"
    r"(?:\s+et\s+al\.?)?)"
    r"[,\s]+(\d{4})[a-z]?,\s*pp?\.\s*([0-9][0-9,\s\u2013\u2014-]*)"
)
LOOSE_ANCHOR = re.compile(r"pp?\.\s*([0-9]+(?:\s*[\u2013\u2014-]\s*[0-9]+)?)")
STOPWORDS = {"and", "et", "al", "in", "the", "see", "cf"}


def parse_pages(blob):
    pages, ranges = set(), []
    for part in blob.split(","):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[\u2013\u2014-]\s*(\d+)\b", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b >= a:
                ranges.append((a, b))
            continue
        m = re.match(r"^(\d+)\b", part)
        if m:
            pages.add(int(m.group(1)))
            continue
        break
    return pages, ranges


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def docx_text(path):
    z = zipfile.ZipFile(path)
    body = ET.fromstring(z.read("word/document.xml")).find(f"{W}body")
    return "\n".join(
        "".join(t.text or "" for t in p.iter(f"{W}t")) for p in body.iter(f"{W}p")
    )


def anchors_for(path):
    inq, kept = False, []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## Quotes"):
            inq = True
            continue
        if inq and line.startswith("## "):
            inq = False
        if inq:
            kept.append(line)
    got = set()
    for m in LOOSE_ANCHOR.finditer("\n".join(kept)):
        s, r = parse_pages(m.group(1))
        got |= s
        for lo, hi in r:
            got.update(range(lo, hi + 1) if hi - lo < 40 else [lo])
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--vault", default=os.environ.get("VAULT_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    docx = pathlib.Path(args.docx)
    src_dir = pathlib.Path(args.vault) / "wiki" / "sources"
    if not docx.is_file():
        print(f"\033[31m[DOCX-XREF] docx NOT FOUND at {docx}; NOTHING WAS AUDITED.\033[0m")
        return 2
    if not src_dir.is_dir():
        print(f"\033[31m[DOCX-XREF] wiki/sources not found at {src_dir}; NOTHING WAS AUDITED.\033[0m")
        return 2

    src_norm = {p: norm(p.stem) for p in src_dir.glob("*.md")}
    text = docx_text(docx)

    misses, unresolved, seen, ok = [], [], set(), 0
    for author, year, blob in CITE.findall(text):
        pages, ranges = parse_pages(blob)
        want = set(pages) | {lo for lo, _ in ranges}
        key = (norm(author), year, tuple(sorted(want)))
        if key in seen:
            continue
        seen.add(key)

        toks = [t for t in norm(author).split() if t not in STOPWORDS]
        cands = [p for p, n in src_norm.items()
                 if year in n and any(t in n.split() for t in toks)]
        if not cands:
            unresolved.append((f"{author} {year}", sorted(want)))
            continue

        best = min(((c, sorted(want - anchors_for(c))) for c in cands),
                   key=lambda cm: len(cm[1]))
        if best[1]:
            misses.append((f"{author} {year}", best[1], best[0].name))
        else:
            ok += 1

    for cite, pages, page in misses:
        print(f"\033[31m  [UNANCHORED]\033[0m {cite}  pages {pages}  -> {page}")
    for cite, pages in unresolved:
        print(f"\033[33m  [NO SOURCE PAGE]\033[0m {cite}  pages {pages}")

    total = ok + len(misses) + len(unresolved)
    if misses or unresolved:
        print(f"\033[31m[DOCX-XREF] {len(misses)} unanchored, {len(unresolved)} unresolvable "
              f"of {total} distinct citation groups in {docx.name}.\033[0m")
        return 1
    if not args.quiet:
        print(f"\033[32m[DOCX-XREF] all {total} distinct citation groups in {docx.name} "
              f"are anchored in wiki/sources.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
