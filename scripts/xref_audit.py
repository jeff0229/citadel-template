"""Cross-page citation-anchor audit for the diss wiki.

WHY THIS EXISTS
---------------
`quote-audit.sh` checks each SOURCE page against ITSELF: every (p.N) cited
outside its Quotes section has a quote anchored at that page. That is a useful
but inward-facing check.

CLAUDE.md states the rule the other way round, and that direction was never
audited by anything:

    "Every page number cited in any synthesis must first exist as an anchored
     quote in the source page's Quotes section."

So a chapter draft could cite (Cotter, 2019, p.901) forever without anyone
checking that Cotter's page anchors p.901. This script closes that.

It also fixes two parser bugs found 2026-07-09 in the bash audits:
  * `(pp.97, 98)` -> the old regex captured only "97". Page 98 went unchecked.
    That is the comma form CLAUDE.md tells authors to PREFER, so the preferred
    form was the under-audited one.
  * lint.sh's copy of the check matched `(p.N)` only and ignored `(pp....)`.

ATTRIBUTION (deliberately conservative)
--------------------------------------
A citation is only checked when its source can be pinned with confidence:
  A. `(Author, Year, p.N)` / `(Author et al., Year, pp.N, M)` -- author inside
     the parens. Highest confidence; the dominant form in the chapter drafts.
  B. `Author (Year, p.N)` -- surname immediately before the paren.
  C. bare `(p.N)` attributed to the last `[[Source Page]]` link or `Author Year`
     mention IN THE SAME SENTENCE. Sentence boundaries stop attribution, so
     "[[X]] says A (p.5). Y says B (p.9)." never blames X for p.9.
Anything else is reported as UNATTRIBUTED and never fails the build. A false
"clean" is worse than a gap we can see, so gaps are printed, not hidden.

Accents are folded (Törnberg == Tornberg, Mihăilescu == Mihailescu) because
that exact mismatch produced dead wikilinks in this vault.

Verdicts:
  MISS               attributed, source HAS anchors, cited page is NOT among
                     them                                        -> exit 1
  NO-ANCHOR-SOURCE   attributed, source page has zero machine-readable anchors
                     (e.g. Beer 2019 uses "(SRM p.10)")          -> warn
  NO-SOURCE-PAGE     author-year resolves to no source page      -> warn
  UNATTRIBUTED       bare (p.N), no antecedent in its sentence   -> info

Usage:  python xref_audit.py [--vault DIR] [--all] [--list-unattributed]
"""

import argparse
import os
import collections
import pathlib
import re
import sys
import unicodedata

CODE_FENCE = re.compile(r"```.*?```", re.S)
CODE_SPAN = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"(?<!!)\[\[([^\]|#\n]+?)(?:\|[^\]\n]*)?\]\]")

# (p.5) (p. 5) (pp.5, 7) (pp. 43-44)
BARE_CITE = re.compile(r"\(\s*pp?\.\s*([0-9][^)]*)\)")
# Anchors written without parentheses inside a Quotes section: "p.69", "pp.233-235".
# Bossetta 2023 and Mason 2018 use this form; treating them as anchor-less produced
# four false "unverifiable" citations in the submission draft.
LOOSE_ANCHOR = re.compile(r"pp?\.\s*([0-9]+(?:\s*[–—-]\s*[0-9]+)?)")
# (Author, 2019, p.5)  (Author et al., 2019, pp.5, 7)  (A; B, 2020, p.3)
PAREN_CITE = re.compile(r"\(([^)]*?(?:19|20)\d{2}[a-z]?[^)]*?pp?\.\s*[0-9][^)]*)\)")
# Author (2019, p.5)
YEAR_CITE = re.compile(r"\(\s*((?:19|20)\d{2}[a-z]?)\s*[,;]\s*pp?\.\s*([0-9][^)]*)\)")

# Candidate sentence ends; abbreviations are rejected in sentence_segment().
SENT_END = re.compile(r"\.\s+(?=[A-Z\[\"“(])")
ABBREV = {"pp", "p", "al", "ed", "eds", "vs", "cf", "ch", "no", "fig",
          "g", "e", "i", "dr", "prof", "st", "mr", "ms", "mrs"}

_RIGOUR = re.compile(r"^rigour:\s*(\w+)", re.MULTILINE)

SKIP_DIRS = ("_archive", "audits and review")
NOFAIL_DIRS = ("assignment-drafts",)  # submission-immutable: report, never fail


def fold(s: str) -> str:
    """Strip accents so Törnberg == Tornberg."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def strip_code(t: str) -> str:
    return CODE_SPAN.sub(" ", CODE_FENCE.sub(" ", t))


def quotes_section(text: str) -> str:
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("## Quotes"):
            on = True
            continue
        if on and line.startswith("## "):
            on = False
        if on:
            out.append(line)
    return "\n".join(out)


def parse_pages(blob: str):
    """'898, citing Bucher 2012, pp. 1174' -> ({898}, [])

    Returns (single_pages, ranges). Ranges are kept AS ranges and never
    expanded: a cite like (pp.87-101) is a gist reference to a procedure that
    spans pages, and demanding an anchor on every page in it manufactures
    failures. A range is satisfied when the source anchors any page inside it.

    Parsing stops at the first comma-part that is not purely a page or range,
    so a nested citation cannot inject its pages.
    """
    pages, ranges = set(), []
    for part in blob.split(","):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[–—-]\s*(\d+)\b", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b >= a:
                ranges.append((a, b))
            continue
        m = re.match(r"^(\d+)\b", part)
        if m:
            n = int(m.group(1))
            # A trailing 4-digit year is not a page. "(Braun and Clarke, 2006,
            # p.87, 2019, 2022)" cites one page and then two further years.
            if 1900 <= n <= 2099 and pages and max(pages) < 1900:
                break
            pages.add(n)
            continue
        break  # non-numeric part: stop, do not scan further
    return pages, ranges


def build_source_index(sources_dir: pathlib.Path):
    anchors, author_year = {}, collections.defaultdict(set)
    for p in sorted(sources_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        q = quotes_section(text)
        pages = set()
        for m in LOOSE_ANCHOR.finditer(q):
            singles, rngs = parse_pages(m.group(1))
            pages |= singles
            for a, b in rngs:
                if b - a < 40:
                    pages.update(range(a, b + 1))
                else:
                    pages.add(a)
        anchors[p.stem] = pages

        m = re.match(r"^(.*?)\s((?:19|20)\d{2}|nd)\b", p.stem)
        if not m:
            continue
        names, year = m.group(1), m.group(2)
        names = re.sub(r"\b(et al|and|&)\b", " ", names, flags=re.I)
        for tok in re.findall(r"[A-Za-zÀ-ɏ'’-]{3,}", fold(names)):
            author_year[(tok.lower(), year)].add(p.stem)
    return anchors, author_year


NESTED = re.compile(r"(citing|cited in|as cited|quoted in|see also|via)", re.I)


# Surname particles and connectives. Without this, "Helmond and van der Vlist,
# 2019" also matched "Van Dijck ... 2019" on the token "van", so the reference
# looked like it named two works and was skipped: a real citation went
# unchecked. Erring toward silence is right, but not for a spurious reason.
PARTICLES = {"van", "der", "den", "de", "del", "la", "le", "von", "and",
             "et", "al", "eds", "ed", "the", "for", "per", "see", "cited",
             "citing", "with", "pages", "added", "status", "sweep"}

# A reference is only judged when it is in canonical Harvard form: author(s),
# then the year, then the page. Prose that merely mentions a work and a page
# nearby -- "(Targets Cotter 2019 *threat of invisibility*, p.898, and the
# engagement loop per Bucher 2012)" -- is not a citation, and attributing its
# page to whichever author the regex reached first produced false accusations
# against Bucher, Funkhouser, Braun & Clarke and Tornberg. Skip, and count.
HARVARD = re.compile(
    r"^\s*[A-ZÀ-ɏ][^,;()]{0,70}?,?\s*(?:19|20)\d{2}[a-z]?\s*[,;:]?\s*pp?\.\s*[0-9]"
)


def ambiguous(ref, author_year):
    """True when a reference names works by DIFFERENT authors, so a page number
    inside it cannot be pinned to one of them.

    "(Braun and Clarke, 2006, p.87, 2019, 2022)" names three works by the same
    authors; p.87 belongs to the year it follows, and the citation is not
    ambiguous. "(Targets Cotter 2019 ..., p.898, ... per Bucher 2012)" names two
    different authors and is.
    """
    works = distinct_works(ref, author_year)
    surnames = {w.split()[0].lower() for w in works}
    return len(surnames) > 1


def distinct_works(ref, author_year):
    """Which source pages a reference names. More than one means its page
    numbers cannot be attributed: "(Targets Cotter 2019 ..., p.898, and the
    engagement loop per Bucher 2012)" sets p.898 beside two works and nothing
    in the string says which owns it. Guessing produced false accusations
    against Bucher, Funkhouser and Tornberg. Refuse, and report, instead.

    Anchored on the YEARS, looking back for a surname. Scanning forward with one
    regex let a spurious early match ("sweep status ... 2026") swallow the real
    author and hide the second work.
    """
    text = fold(ref)
    found = set()
    for ym in re.finditer(r"(?:19|20)\d{2}", text):
        year = ym.group(0)
        window = text[max(0, ym.start() - 50):ym.start()]
        for tok in re.findall(r"[A-Za-z'’-]{3,}", window):
            if tok.lower() in PARTICLES:
                continue
            found |= author_year.get((tok.lower(), year), set())
    return found


def resolve(ref: str, author_year, anchors, prefer="first"):
    """Resolve 'Van Dijck, Nieborg and Poell, 2019' -> one source stem or None.

    prefer="first": the citation's own year leads the reference, as in
      "(Braun and Clarke, 2006, p.87, 2019, 2022)" -> 2006, not 2022.
      Taking the last year attributed that citation to the wrong sibling paper.
    prefer="last":  the author sits outside the parens and the year was appended
      by the caller, as in "...Gillespie (2010, p.348)".
    """
    ref = fold(ref)
    years = re.findall(r"(?:19|20)\d{2}", ref)
    if not years:
        return None
    year = years[0] if prefer == "first" else years[-1]
    toks = [t.lower() for t in re.findall(r"[A-Za-zÀ-ɏ'’-]{3,}", ref)]
    toks = [t for t in toks if t not in {"and", "et", "al", "pp", "see", "also", "cited", "in"}]
    cands = set()
    for t in toks:
        cands |= author_year.get((t, year), set())
    if len(cands) == 1:
        return next(iter(cands))
    if len(cands) > 1:
        tight = [s for s in cands if all(t in fold(s).lower() for t in toks if len(t) > 3)]
        if len(tight) == 1:
            return tight[0]
    return None


def sentence_segment(prefix: str) -> str:
    """Text after the last real sentence end. 'p. 5' / 'et al.' are not ends."""
    cut = 0
    for m in SENT_END.finditer(prefix):
        word = re.search(r"([A-Za-z]+)$", prefix[: m.start()])
        if word and word.group(1).lower() in ABBREV:
            continue
        if prefix[m.start() - 1 : m.start()].isdigit():
            continue  # "p.5. " style: digit before the period
        cut = m.end()
    return prefix[cut:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.environ.get("VAULT_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--all", action="store_true", help="include _archive and 'audits and review'")
    ap.add_argument("--list-unattributed", action="store_true")
    args = ap.parse_args()

    vault = pathlib.Path(args.vault)
    anchors, author_year = build_source_index(vault / "wiki" / "sources")

    stats = collections.Counter()
    misses, no_anchor, no_page, unattr = [], [], [], []

    for d in ("wiki/concepts", "wiki/entities", "wiki/synthesis", "wiki/notes"):
        for p in sorted((vault / d).rglob("*.md")):
            rel = str(p.relative_to(vault)).replace("\\", "/")
            if not args.all and any(s in rel for s in SKIP_DIRS):
                stats["pages_skipped"] += 1
                continue
            immutable = any(s in rel for s in NOFAIL_DIRS)
            body = p.read_text(encoding="utf-8", errors="replace")
            # 2026-09-04: enforcement follows `rigour:`, not folder. A personal
            # note carries no locator anyone will ever check, so auditing it
            # would only train the reader to skim past the report. Anything
            # marked citable is audited wherever it lives.
            m_rig = _RIGOUR.search(body)
            if m_rig and m_rig.group(1).lower() == "personal":
                stats["personal_skipped"] += 1
                continue
            stats["pages_scanned"] += 1
            text = strip_code(body)

            for line in text.splitlines():
                claimed = []  # (start, end) spans already consumed

                # A. (Author, Year, p.N) and the author-outside form Author (Year, p.N)
                for m in PAREN_CITE.finditer(line):
                    claimed.append((m.start(), m.end()))
                    for ref in m.group(1).split(";"):
                        if not re.search(r"pp?\.\s*[0-9]", ref):
                            continue
                        if NESTED.search(ref):
                            stats["nested_skipped"] += 1
                            continue
                        if ambiguous(ref, author_year):
                            stats["ambiguous_multiwork"] += 1
                            continue
                        if not HARVARD.match(ref):
                            stats["not_harvard_form"] += 1
                            continue
                        cited = parse_pages(re.split(r"pp?\.\s*", ref, 1)[1])
                        if not cited[0] and not cited[1]:
                            continue
                        stats["citations"] += 1
                        src = resolve(ref, author_year, anchors, prefer="first")
                        if src is None:
                            # "Gillespie (2010, p.348)": author sits before the paren.
                            seg = sentence_segment(line[: m.start()])
                            src = resolve(seg[-90:] + " " + ref, author_year, anchors, prefer="last")
                        if src is None:
                            for lm in LINK.finditer(sentence_segment(line[: m.start()])):
                                base = lm.group(1).split("/")[-1].strip()
                                if base in anchors:
                                    src = base
                        record(src, cited, rel, line, immutable, stats,
                               misses, no_anchor, no_page, anchors)

                # B. Author (Year, p.N)
                for m in YEAR_CITE.finditer(line):
                    if any(s <= m.start() < e for s, e in claimed):
                        continue
                    claimed.append((m.start(), m.end()))
                    cited = parse_pages(m.group(2))
                    if not cited[0] and not cited[1]:
                        continue
                    stats["citations"] += 1
                    seg = sentence_segment(line[: m.start()])
                    src = resolve(seg[-80:] + " " + m.group(1), author_year, anchors, prefer="last")
                    record(src, cited, rel, line, immutable, stats,
                           misses, no_anchor, no_page, anchors)

                # C. bare (p.N) -> last [[link]] or Author Year in same sentence
                for m in BARE_CITE.finditer(line):
                    if any(s <= m.start() < e for s, e in claimed):
                        continue
                    open_paren = line.rfind("(", 0, m.start())
                    guard_from = open_paren if open_paren != -1 else max(0, m.start() - 60)
                    if NESTED.search(line[guard_from:m.start()]):
                        stats["nested_skipped"] += 1
                        continue
                    cited = parse_pages(m.group(1))
                    if not cited[0] and not cited[1]:
                        continue
                    stats["citations"] += 1
                    seg = sentence_segment(line[: m.start()])
                    src = None
                    for lm in LINK.finditer(seg):
                        base = lm.group(1).split("/")[-1].strip()
                        if base in anchors:
                            src = base
                    if src is None:
                        # Same refusal as the parenthetical path: a sentence that
                        # names several works cannot tell us who owns this page.
                        if ambiguous(seg, author_year):
                            stats["ambiguous_multiwork"] += 1
                            continue
                        am = list(re.finditer(r"([A-ZÀ-ɏ][\w'’-]{2,}(?:[^.()\[\]]{0,40}?))((?:19|20)\d{2})", seg))
                        if am:
                            src = resolve(am[-1].group(0), author_year, anchors, prefer="last")
                    if src is None:
                        stats["unattributed"] += 1
                        unattr.append((rel, sorted(cited[0]), line.strip()[:100]))
                        continue
                    record(src, cited, rel, line, immutable, stats,
                           misses, no_anchor, no_page, anchors)

    # ---- report ----------------------------------------------------------
    def show(title, rows, colour):
        if not rows:
            return
        print(f"\n{colour}[XREF] {title}: {len(rows)}\033[0m")
        for rel, src, pages, line, imm in rows[:60]:
            tag = " [immutable]" if imm else ""
            print(f"  {rel}{tag}\n     -> {src}   p.{pages}\n     {line}")
        if len(rows) > 60:
            print(f"  ... and {len(rows) - 60} more")

    show("UNANCHORED page citations (cited page has no quote on the source page)", misses, "\033[31m")
    show("source page has NO machine-readable anchors (coverage gap)", no_anchor, "\033[33m")
    show("author-year resolves to no source page (never ingested)", no_page, "\033[33m")

    if args.list_unattributed:
        print(f"\n\033[36m[XREF] UNATTRIBUTED bare citations: {len(unattr)}\033[0m")
        for rel, pages, line in unattr[:60]:
            print(f"  {rel}  p.{pages}\n     {line}")

    print()
    print(f"[XREF] pages scanned {stats['pages_scanned']} "
          f"(skipped {stats['pages_skipped']}, personal {stats['personal_skipped']}) | "
          f"citations {stats['citations']} | attributed {stats['attributed']} | "
          f"unattributed {stats['unattributed']}")

    hard = [r for r in misses if not r[4]]
    if hard:
        print(f"\033[31m[XREF] {len(hard)} unanchored citation(s) on non-immutable pages.\033[0m")
        return 1
    if misses:
        print("\033[33m[XREF] unanchored citations exist only on submission-immutable pages (reported, not failed).\033[0m")
    print("\033[32m[XREF] no unanchored citations on live pages.\033[0m")
    return 0


def record(src, cited, rel, line, immutable, stats, misses, no_anchor, no_page, anchors):
    singles, ranges = cited
    if src is None:
        stats["no_source_page"] += 1
        no_page.append((rel, "(unresolved author-year)", sorted(singles), line.strip()[:100], immutable))
        return
    stats["attributed"] += 1
    have = anchors[src]
    if not have:
        stats["no_anchor_source"] += 1
        no_anchor.append((rel, src, sorted(singles), line.strip()[:100], immutable))
        return
    bad = sorted(singles - have)
    # a range is satisfied if the source anchors ANY page inside it
    for a, b in ranges:
        if not have & set(range(a, min(b, a + 200) + 1)):
            bad.append(f"{a}-{b}")
    if bad:
        stats["miss"] += 1
        misses.append((rel, src, bad, line.strip()[:100], immutable))


if __name__ == "__main__":
    sys.exit(main())
