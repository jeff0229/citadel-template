"""Which PDFs in raw/ have no source page? Content-based, not filename-based.

WHY THIS EXISTS
---------------
`/bootup`'s raw-folder scan covers `raw/01-...` through `raw/09-...` only, so
`raw/10-PHD-application` -- 108 PDFs -- was never diffed against wiki/sources.
Nine book reviews sat filed and un-ingested for weeks because of it, and a prep
page came to claim an ingest that never ran.

On 2026-07-09 two separate filename-similarity matchers were written to close
that gap and both lied. The first flagged sources ingested an hour earlier
(their PDFs are named `2302.04062v10.pdf`). The second declared the book-review
folder fully ingested because `Wood 2016 - Review of Browne Dark Matters`
matched `Mann 1999 - Review of Scott Seeing Like a State` on the word "Review".
Filenames are not evidence. Quotes are.

METHOD
------
Invert `verbatim_audit.py`'s PDF resolution. A source page claims the PDF that
contains its longest quote (or the one its `verbatim-pdf:` frontmatter pins).
Any PDF no source page claims is a candidate for ingestion. The same matcher
that verifies quotes decides this, so there is exactly one notion of "this page
came from that PDF" in the vault.

VERDICTS
--------
  INGESTED     a source page resolves to this PDF by quote content or a pin.
  AMBIGUOUS    no page resolves to it, but a source page's name overlaps its
               filename or its own first-page title. Usually one of: a duplicate
               / "(alt copy)" sibling; a page whose quotes cannot be matched at
               all (image-only PDF, OCR damage, preview pagination -- the eight
               `unresolved` pages verbatim-audit already reports); or a book the
               vault cites from a review rather than the book itself.
               Reported, never asserted as un-ingested.
  UN-INGESTED  no page resolves to it and nothing looks like a source page for
               it. This is the actionable list.

Filenames are used ONLY to soften a claim (INGESTED -> AMBIGUOUS), never to make
one. A false "un-ingested" wastes an ingest; a false "ingested" hides a gap.

Usage:
  python uningested_audit.py --sources DIR --raw DIR --pdftotext PATH
                             [--cache DIR] [--include-00] [--quiet]
Exit: 0 always. This reports; it does not gate.
"""

import argparse
import collections
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from verbatim_audit import MIN_FRAG, canon, ordered_in, parse_pin, parse_quotes, pdf_raw  # noqa: E402

# raw/00-* are the user's own drafts, rubrics and craft references: never ingested.
# raw/99-* is the untriaged backlog, flagged separately by new-drop.sh.
EXCLUDE_DEFAULT = ("00-", "99-")

STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "review",
        "chapter", "final", "draft", "copy", "main", "pdf", "article", "paper"}


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def toks(s):
    return {t for t in re.findall(r"[a-z]{4,}", fold(s).lower()) if t not in STOP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--pdftotext", default="pdftotext")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--include-00", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    pdftotext = args.pdftotext
    if not pathlib.Path(pdftotext).exists() and pathlib.Path(pdftotext + ".exe").exists():
        pdftotext += ".exe"

    raw = pathlib.Path(args.raw)
    sources_dir = pathlib.Path(args.sources)
    cache_dir = pathlib.Path(args.cache) if args.cache else pathlib.Path(__file__).parent / ".cache" / "verbatim"

    pdfs = []
    for p in sorted(raw.rglob("*.pdf")):
        rel = p.relative_to(raw).as_posix()
        parts = rel.split("/")[:-1]
        # Exclude at ANY depth: raw/99-unclassified and raw/10-.../99-offtopic both
        # mean "not for ingestion", and 00-* folders are the user's own artefacts.
        if not args.include_00 and any(d.startswith(EXCLUDE_DEFAULT) for d in parts):
            continue
        pdfs.append(p)

    sys.stderr.write(f"  resolving {len(pdfs)} PDFs against source pages (uses the verbatim cache)\n")
    pdf_canon = {}
    for p in pdfs:
        layout, flow = pdf_raw(p, pdftotext, cache_dir)
        pdf_canon[p] = [canon(layout), canon(flow)]

    def present(fc, p):
        return any(ordered_in(fc, t) for t in pdf_canon[p])

    claimed = {}            # pdf -> [source page names]
    unresolved_pages = []   # source pages whose quotes match no PDF here
    src_names = []

    for sf in sorted(sources_dir.glob("*.md")):
        src_names.append(sf.stem)
        raw_quotes = parse_quotes(sf)
        if not raw_quotes:
            unresolved_pages.append(sf.stem)   # Quotes section yields nothing
            continue
        frags = [c for _, fr in raw_quotes for c in map(canon, fr) if len(c) >= MIN_FRAG]
        if not frags:
            unresolved_pages.append(sf.stem)   # nothing to resolve with
            continue

        pin = parse_pin(sf)
        if pin:
            hit = [p for p in pdfs if p.name.lower() == pin.lower()]
            if hit:
                claimed.setdefault(hit[0], []).append(sf.stem)
                continue
            # pin points outside this scan (e.g. an excluded folder): fall through

        fingerprint = max(frags, key=len)
        cands = [p for p in pdfs if present(fingerprint, p)]
        if not cands:
            unresolved_pages.append(sf.stem)
            continue
        best = max(cands, key=lambda p: sum(1 for c in frags if present(c, p)))
        claimed.setdefault(best, []).append(sf.stem)

    src_tok = {s: toks(s) for s in src_names}
    # A source page's identity, for matching against a PDF's own first page:
    # surname tokens + year, taken from the page's filename.
    src_ident = {}
    for s in src_names:
        m = re.match(r"^(.*?)\s((?:19|20)\d{2})\b", s)
        if m:
            names = re.sub(r"\b(et al|and|&)\b", " ", m.group(1), flags=re.I)
            surnames = [w for w in re.findall(r"[A-Za-zÀ-ɏ'’-]{3,}", fold(names))]
            if surnames:
                src_ident[s] = (surnames, m.group(2))

    claimed_texts = [pdf_canon[p][1] for p in claimed]

    def is_duplicate_of_claimed(p):
        """A byte-different copy of a PDF a page already claims. Sample from the
        middle so a shared cover sheet cannot fake a match."""
        t = pdf_canon[p][1]
        if len(t) < 1200:
            return False
        probe = t[len(t) // 2: len(t) // 2 + 400]
        return any(probe in ct for ct in claimed_texts)

    def page_named_on_first_page(p):
        """Does some source page's author+year appear in this PDF's own opening?
        Catches a PDF whose page exists but claims nothing (its Quotes carry no
        quotation marks, so there is no fingerprint to resolve with).

        Matched on RAW text with word boundaries, not on the canonical letter
        soup: 'Lei' and 'Beer' are substrings of ordinary prose, and matching
        there softened four unrelated PDFs out of the un-ingested list.

        Only pages that claimed NO PDF are candidates. That is what makes a short
        surname safe here: 'Cath 2018' cannot be confused with anything when the
        candidate set is the handful of pages actually missing a PDF. Searching
        all 166 pages instead is what let 'Lei' and 'Beer' match prose.
        """
        head = fold(pdf_raw_head.get(p, "")).lower()
        if not head:
            return None
        zone = head[:800]  # masthead, title, byline, copyright line
        file_year = re.search(r"(19|20)\d{2}", fold(p.stem))
        for s in unresolved_pages:
            ident = src_ident.get(s)
            if not ident:
                continue
            surnames, year = ident
            # If the filename states a year and it is not this page's year, the
            # PDF is a different work by the same authors. "Braun and Clarke 2012
            # - APA Handbook" cites "(Braun & Clarke, 2006)" in its own opening
            # paragraph, so surname-and-year adjacency alone matched the 2006
            # source page and hid a real gap. A stated, contradicting year wins.
            if file_year and file_year.group(0) != year:
                continue
            # Surname and year must sit TOGETHER in the byline zone. Requiring
            # only that both appear somewhere in the head matched "Braun and
            # Clarke ... (Braun & Clarke, 2006)" in their 2012 APA chapter, a
            # different paper with no source page, and softened a real gap away.
            for sn in surnames:
                sn = re.escape(fold(sn).lower())
                # A short window, and periods allowed: "Cite this article: Cath C.
                # 2018 Governing artificial intelligence" must match, while
                # "Virginia Braun and Victoria Clarke" ... "(Braun & Clarke, 2006)"
                # 270 characters later must not.
                if re.search(rf"\b{sn}\b.{{0,40}}{year}", zone) or re.search(rf"{year}.{{0,40}}\b{sn}\b", zone):
                    return s
        return None

    # digits are stripped by canon(), so keep a raw head for the year test
    pdf_raw_head = {}
    for p in pdfs:
        if p not in claimed:
            pdf_raw_head[p] = pdf_raw(p, pdftotext, cache_dir)[1][:3000]

    ingested, ambiguous, missing = [], [], []
    for p in pdfs:
        if p in claimed:
            ingested.append((p, claimed[p]))
            continue
        if is_duplicate_of_claimed(p):
            ambiguous.append((p, "duplicate of a PDF a source page already claims"))
            continue
        named = page_named_on_first_page(p)
        if named:
            ambiguous.append((p, f"{named} (author+year on this PDF's first page)"))
            continue
        # Filename softening, last and weakest. It requires a MATCHING YEAR as
        # well as shared words, because bare word overlap hid real gaps:
        # "Taylor 2017 - What is Data Justice" was softened by "Jordon et al 2022
        # - Synthetic Data What Why and How" on the words "what" and "data";
        # "beer-2012-using-social-media-data-aggregators" by "Beer 2016"; and
        # "Braun and Clarke 2012 - APA Handbook" by "Braun Clarke 2006". Each of
        # those is a different paper, and each was a gap this bucket concealed.
        # A PDF whose filename carries no year is never softened this way.
        t = toks(p.stem)
        yr = re.search(r"(19|20)\d{2}", fold(p.stem))
        near = None
        if yr:
            for s, st in src_tok.items():
                if yr.group(0) not in s:
                    continue
                if len(t & st) >= 2:
                    near = s
                    break
        (ambiguous if near else missing).append((p, near))

    def rel(p):
        return p.relative_to(raw).as_posix()

    print()
    if missing:
        print(f"\033[31m[UN-INGESTED] {len(missing)} PDF(s) no source page resolves to, and nothing resembles one:\033[0m")
        by_dir = collections.defaultdict(list)
        for p, _ in missing:
            by_dir[rel(p).rsplit("/", 1)[0]].append(rel(p).rsplit("/", 1)[-1])
        for d in sorted(by_dir):
            print(f"  {d}/  ({len(by_dir[d])})")
            for n in sorted(by_dir[d]):
                print(f"     - {n}")

    if ambiguous:
        print(f"\n\033[33m[AMBIGUOUS] {len(ambiguous)} PDF(s) unclaimed by quote content, but a source page's name is close:\033[0m")
        print("  (duplicate/alt copies, image-only or preview-paginated pages, or a book cited via its review)")
        for p, near in sorted(ambiguous, key=lambda x: rel(x[0])):
            print(f"  - {rel(p)}\n       nearest source page: {near}")

    if unresolved_pages and not args.quiet:
        print(f"\n\033[36m[NOTE] {len(unresolved_pages)} source page(s) match no PDF in this scan "
              f"(they are why AMBIGUOUS exists):\033[0m")
        for s in unresolved_pages:
            print(f"  - {s}")

    print(f"\n[UN-INGESTED] {len(pdfs)} PDFs scanned | ingested {len(ingested)} | "
          f"ambiguous {len(ambiguous)} | un-ingested {len(missing)}")
    if not missing:
        print("\033[32m[UN-INGESTED] every PDF in scope is claimed by a source page.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
