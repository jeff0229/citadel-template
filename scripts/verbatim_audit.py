"""Verbatim quote auditor for the diss wiki.

The bash audits (quote-audit.sh, lint.sh) check ANCHORING COVERAGE only: that
every cited (p.N) has a matching (p.N) in the source page's Quotes section. They
never open the PDF, so they cannot catch a quote that was fabricated, stitched
together from two places, or grossly misquoted. That blind spot is what bit
batch ingestion (a workflow rubber-stamped a stitched TripAdvisor quote).

This script closes it. For every anchored quote on every source page it
re-extracts the source PDF with pdftotext and confirms the quote text is
actually present.

Matching is deliberately tolerant of the things that legitimately differ
between a wiki quote and a PDF extraction, and only those:
  - line-wraps and word hyphenation across line breaks  -> whitespace/hyphens dropped
  - dropped or glyph-encoded fi/fl/ff ligatures         -> NFKD fold + deligature()
  - accents, smart quotes, dashes, ellipses             -> NFKD fold + letters-only
  - single-vs-double inner quote style                  -> quotes dropped
  - footnote superscript digits inside the body         -> digits dropped
  - a citation or page-break footnote block dropped into the middle of a
    cross-page quote                                    -> one-gap forward fallback
Everything is reduced to a lowercase a-z string, so the test is "do the quote's
letters appear, in order, in the PDF's letters". A fabricated or reversed-stitch
quote still fails: its letters are not present in order.

What it does NOT check: page accuracy (right quote, wrong page) and numbers
inside a quote (years, page refs) -- digits are dropped. Page-offset
correctness stays the human/ingest discipline recorded in each page's [!note]
callout. Presence-in-the-source-PDF is the zero-config, high-leverage check that
covers the batch-ingest blind spot.

PDF resolution is automatic: each source page is matched to the raw PDF that
contains the most of its quotes (gated on its longest quote), so no frontmatter
pointer or offset config is needed. When auto-resolution picks the wrong PDF
(sibling papers with overlapping text, e.g. Bossetta 2018 vs 2023), a source
page may pin its PDF with a frontmatter line `verbatim-pdf: <exact filename>`.
Callout blocks (`> [!note]` etc.) in the Quotes section are meta-commentary,
not source quotes, and are skipped.

Usage (normally via verbatim-audit.sh):
    python verbatim_audit.py --sources DIR --raw DIR [--raw DIR ...]
        --pdftotext PATH [--cache DIR] [NAME_FILTER ...]

Exit: 0 = every resolved quote found (coverage gaps reported, not fatal);
      1 = at least one quote could not be found in its own source PDF.
"""

import argparse
import hashlib
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

CACHE_SPLIT = "\n\x00PDFTOTEXT_MODE_SPLIT\x00\n"
MIN_FRAG = 16  # canonical (a-z) chars; shorter fragments are too common to verify

# elision markers a quoter inserts: [...] [. . .] [...] ... . . . …
_ELISION = re.compile(r"\[\s*(?:\.\s*){2,}\]|\[\s*…\s*\]|(?:\.\s*){3,}|…")
# A trailing locator in parentheses. Page numbers for print; and since
# 2026-09-04, whatever leads back to the quote in a non-print artefact: a
# timestamp for a talk, path:line at a commit for code, a heading or message
# position for a chat. The audit never trusted the locator anyway -- it checks
# the quote text -- but a report that prints "(no anchor)" against every chat
# and video quote is unreadable, and an unreadable report gets skipped.
_ANCHOR = re.compile(
    r"\((?:"
    r"pp?\.\s*[0-9]"        # p.5 / pp.5-7
    r"|t\.\s*[0-9]"          # t.12:04
    r"|[0-9]{1,2}:[0-9]{2}"  # 12:04
    r"|§"                    # §Heading
    r"|msg\s*[0-9]"          # msg 14
    r"|[^)]*:[0-9]+"         # path/to/file.py:88
    r")[^)]*\)\s*$"
)
_FLIGS = ("ffi", "ffl", "ff", "fi", "fl")


def deligature(s: str) -> str:
    """Remove f-ligature letter-pairs. Some PDFs (OUP/SAGE handbooks here) drop
    the fi/fl/ff glyphs on extraction ('justifiability' -> 'justi ability' ->
    'justiability'). Stripping the same pairs from BOTH sides makes them match.
    It bridges ligature gaps only -- not arbitrary gaps -- so a stitched quote
    still fails."""
    for lig in _FLIGS:
        s = s.replace(lig, "")
    return s


def canon(s: str) -> str:
    """Reduce to a lowercase a-z string: NFKD folds accents and ligature glyphs,
    then everything that is not an ascii letter (whitespace, hyphens, digits,
    punctuation, quote marks, backslashes) is dropped, then f-ligatures are
    removed per word so dropped-ligature PDFs still match.

    2026-07-09: deligature() used to run AFTER whitespace was stripped, so it
    chewed across word boundaries. Pillow 2003 p.184 reads "her/his self. I
    suggest that a self-reflexivity ..."; with the spaces already gone,
    "self"+"I" fused to "selfi" and the 'fi' was eaten, yielding "selsuggest".
    The wiki quote begins at "I suggest", so its canonical form could not be
    found and a perfectly verbatim quote was reported unresolved. Any quote
    starting after a word ending in f hit this.

    The obvious repair -- split on every non-letter, deligature each piece -- is
    also wrong. `pdftotext -enc UTF-8` emits SOFT HYPHENS inside words: Tufekci
    2017 p.30 extracts as "twenty-f\\xadirst". Splitting there yields "f"+"irst",
    the 'fi' never forms, and the PDF canonicalises to "twentyfirst" while the
    wiki quote canonicalises to "twentyrst". A verbatim quote fails.

    So: tokenise on WHITESPACE only, strip non-letters WITHIN each token, then
    deligature the token. Soft hyphens, apostrophes and hyphens vanish inside the
    word (the ligature still forms); a hyphenated line-wrap or a dropped glyph
    still collapses to the same letters; and two words never fuse.
    """
    s = unicodedata.normalize("NFKD", s).lower()
    out = []
    for tok in s.split():
        tok = re.sub(r"[^a-z]", "", tok)
        if tok:
            out.append(deligature(tok))
    return "".join(out)


_MIN_CHUNK = 4   # a corruption that cannot match even this many chars forward fails
_MAX_CHUNKS = 14  # a quote that only matches as many tiny scattered pieces is suspect


def ordered_in(fc: str, text: str) -> bool:
    """Can canonical fragment fc be covered by forward-ordered substrings of the
    canonical PDF text? Exact substring is the fast path. Otherwise consume fc
    greedily: from the current quote position, take the longest run that occurs
    in the PDF at or after the last match, advance, repeat. Every character of
    the quote must be covered, but the PDF may have extra text between runs.

    This tolerates the legitimate divergences -- footnote digits, a page-break
    footnote block, a figure/caption inserted where a quote crosses a column or
    page break (multiple gaps) -- because those are extra text in the PDF, not in
    the quote. It still catches the real failures: a fabricated or corrupted
    quote has characters that appear nowhere forward (a run shorter than
    _MIN_CHUNK -> fail), and a reversed stitch cannot be consumed in forward
    order. A quote that only matches as many scattered crumbs (> _MAX_CHUNKS)
    is treated as unverified."""
    if not fc:
        return True
    if fc in text:
        return True
    i, pos, chunks = 0, 0, 0
    n = len(fc)
    while i < n:
        lo, hi, best, best_end = 1, n - i, 0, -1
        while lo <= hi:
            mid = (lo + hi) // 2
            idx = text.find(fc[i:i + mid], pos)
            if idx >= 0:
                best, best_end, lo = mid, idx + mid, mid + 1
            else:
                hi = mid - 1
        if best < _MIN_CHUNK:
            return False
        i += best
        pos = best_end
        chunks += 1
        if chunks > _MAX_CHUNKS:
            return False
    return True


# --- quote extraction ------------------------------------------------------

_PIN = re.compile(r"^verbatim-pdf:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)
_TEXT_PIN = re.compile(r"^verbatim-text:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)


def parse_text_pin(md_path: Path):
    """Return the frontmatter `verbatim-text:` vault-relative path, or None.

    2026-09-04 -- the knowledge-library generalisation. A source page whose
    artefact is a chat export, a markdown file or a source file has no PDF, so
    the PDF resolver files it under "unresolved (coverage gap)" forever and its
    quotes are never checked against anything. That is the 2026-08-10
    audit-the-auditors shape again: a page nobody verifies, reported in a colour
    that reads as fine. `verbatim-text: archive/<path>` names the stored text
    artefact and the identical fragment check runs against it.
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    fm = text[: end if end > 0 else 2000]
    m = _TEXT_PIN.search(fm)
    return m.group(1).strip() if m else None


def parse_pin(md_path: Path):
    """Return the frontmatter `verbatim-pdf:` filename, or None."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    fm = text[: end if end > 0 else 2000]
    m = _PIN.search(fm)
    return m.group(1) if m else None


_QUOTE_CHARS = '"“”'


def parse_quotes(md_path: Path):
    """Return [(anchor_label, [raw_fragment_strings])] for each quote in the
    page's ## Quotes section. Fragments are the elision-split pieces, not yet
    canonicalised.

    2026-07-09: this used to read ONLY lines beginning with `>` and containing a
    straight double quote. The vault writes quotes in four shapes, and three of
    them were invisible to it:

        > "text" (p.5)          blockquote          <- the only one it saw
        - "text" (p.5)          bullet              (Cotter, Zulli, Van Dijck & Poell)
        "text" (p.5)            bare line           (Castells, Fraser)
        - p.262 - *"text"*      bullet, page-first  (Guillemin)

    Eighteen of 166 source pages were therefore skipped in silence by main(),
    never verified and never reported: their quotes had never once been checked
    against a PDF. Curly quotation marks are now recognised too. A block inside
    the Quotes section that contains no quotation marks at all cannot be verified
    (it is a paraphrase or a callout); it is returned with an empty fragment list
    so the caller can REPORT it rather than drop it.
    """
    lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_quotes = False
    blocks, cur = [], []

    def flush():
        nonlocal cur
        if cur:
            blocks.append(cur)
            cur = []

    for ln in lines:
        if ln.startswith("## "):
            in_quotes = ln.strip().lower().startswith("## quotes")
            flush()
            continue
        if not in_quotes:
            continue
        s = ln.strip()
        if not s:
            flush()
            continue
        if s.startswith(">"):
            body = s[1:].strip()
            if body.startswith("[!"):          # callout: commentary, not a quote
                flush()
                cur = ["[!"]
                continue
            if cur and cur[0] == "[!":         # still inside that callout
                continue
            cur.append(body)
        elif s.startswith(("- ", "* ", "+ ")):
            flush()
            cur.append(s[2:].strip())
        elif s[0] in _QUOTE_CHARS:
            flush()
            cur.append(s)
        elif cur and cur[0] != "[!":
            cur.append(s)                       # continuation of the current quote
        else:
            flush()
    flush()

    quotes = []
    for block in blocks:
        if block and block[0] == "[!":
            continue
        text = " ".join(b for b in block if b)
        anchor_m = _ANCHOR.search(text)
        anchor = anchor_m.group(0).strip() if anchor_m else "(no anchor)"
        first = min((text.find(c) for c in _QUOTE_CHARS if c in text), default=-1)
        last = max((text.rfind(c) for c in _QUOTE_CHARS if c in text), default=-1)
        if first < 0 or last <= first:
            quotes.append((anchor, []))        # unquoted block: report, do not drop
            continue
        inner = text[first + 1:last]
        frags = [p for p in _ELISION.split(inner) if p.strip()]
        quotes.append((anchor, frags))
    return quotes


# --- pdf text --------------------------------------------------------------

def _extract(pdf: Path, pdftotext: str, layout: bool) -> str:
    cmd = [pdftotext, "-q", "-enc", "UTF-8"]
    if layout:
        cmd.append("-layout")
    cmd += [str(pdf), "-"]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=120)
        return res.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - a broken PDF must not abort the run
        sys.stderr.write(f"  ! pdftotext failed on {pdf.name}: {e}\n")
        return ""


def _cache_key(pdf: Path) -> str:
    """Stable across processes. `hash(str)` is salted per interpreter unless
    PYTHONHASHSEED is set, so the old key never matched on a later run: the cache
    missed every time, re-extracted every PDF, and left a file behind. It had
    grown to 26,182 files by 2026-07-09 while never once being read."""
    return hashlib.sha1(str(pdf.resolve()).encode("utf-8")).hexdigest()[:16]


def pdf_raw(pdf: Path, pdftotext: str, cache_dir: Path):
    """Return (layout_text, nonlayout_text), cached by path+size+mtime. Both
    reading orders are kept: -layout aligns columns but interleaves multi-column
    text; the default flows each column whole. A quote need only match one."""
    st = pdf.stat()
    h = _cache_key(pdf)
    key = f"{h}-{st.st_size}-{int(st.st_mtime)}.txt"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / key
    if cached.exists():
        parts = cached.read_text(encoding="utf-8", errors="replace").split(CACHE_SPLIT)
        if len(parts) == 2:
            return parts[0], parts[1]
    layout = _extract(pdf, pdftotext, True)
    flow = _extract(pdf, pdftotext, False)
    for old in cache_dir.glob(f"{h}-*.txt"):
        if old.name != key:
            old.unlink(missing_ok=True)
    cached.write_text(layout + CACHE_SPLIT + flow, encoding="utf-8")
    return layout, flow


# --- main ------------------------------------------------------------------

GREEN, RED, YELLOW, CYAN, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[0m"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # en-dashes in anchors print clean
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True)
    ap.add_argument("--raw", action="append", required=True)
    ap.add_argument("--pdftotext", default="pdftotext")
    ap.add_argument("--cache", default=None)
    ap.add_argument("filters", nargs="*", help="only audit source files whose name contains one of these")
    args = ap.parse_args()

    pdftotext = args.pdftotext
    if not Path(pdftotext).exists() and Path(pdftotext + ".exe").exists():
        pdftotext += ".exe"

    sources_dir = Path(args.sources)
    cache_dir = Path(args.cache) if args.cache else Path(__file__).parent / ".cache" / "verbatim"
    vault_root = sources_dir.parent.parent   # wiki/sources -> vault root

    pdf_paths, seen = [], set()
    for r in args.raw:
        for p in Path(r).rglob("*.pdf"):
            rp = str(p.resolve())
            if rp not in seen:
                seen.add(rp)
                pdf_paths.append(p)
    sys.stderr.write(f"  scanning {len(pdf_paths)} PDFs (first run extracts + caches; re-runs are fast)\n")
    # canonical text per PDF, per reading order
    pdf_canon = {}
    for p in pdf_paths:
        layout, flow = pdf_raw(p, pdftotext, cache_dir)
        pdf_canon[p] = [canon(layout), canon(flow)]

    def present(fc, p):
        return any(ordered_in(fc, t) for t in pdf_canon[p])

    src_files = sorted(sources_dir.glob("*.md"))
    if args.filters:
        src_files = [f for f in src_files if any(flt.lower() in f.name.lower() for flt in args.filters)]

    suspect, unresolved, too_short = [], [], []
    audited_quotes = audited_sources = 0

    unquoted = []   # blocks in a Quotes section with no quotation marks at all
    no_quotes = []  # pages whose Quotes section yields nothing to verify

    for sf in src_files:
        raw_quotes = parse_quotes(sf)
        if not raw_quotes:
            # Was a silent `continue` until 2026-07-09. A page with no parseable
            # quote is not "clean", it is unchecked, and it must say so.
            no_quotes.append((sf.name, "Quotes section has no parseable quote"))
            continue
        n_unquoted = sum(1 for _, fr in raw_quotes if not fr)
        if n_unquoted:
            unquoted.append((sf.name, n_unquoted))
        # canonicalise fragments; keep only those long enough to verify
        quotes = []  # (anchor, [canon_frag])
        for anchor, frags in raw_quotes:
            cfrags = [canon(f) for f in frags]
            cfrags = [c for c in cfrags if len(c) >= MIN_FRAG]
            quotes.append((anchor, cfrags))

        all_frags = [c for _, cf in quotes for c in cf]
        if not all_frags:
            too_short.append((sf.name, "(all quotes too short to verify)"))
            continue
        tpin = parse_text_pin(sf)
        pin = parse_pin(sf)
        if tpin:
            tp = vault_root / tpin
            if not tp.exists():
                unresolved.append((sf.name, f"frontmatter verbatim-text not found: {tpin}"))
                continue
            if tp not in pdf_canon:
                pdf_canon[tp] = [canon(tp.read_text(encoding="utf-8", errors="replace"))]
            best = tp
        elif pin:
            pinned = [p for p in pdf_paths if p.name.lower() == pin.lower()]
            if not pinned:
                unresolved.append((sf.name, f"frontmatter verbatim-pdf not found in raw/: {pin}"))
                continue
            best = pinned[0]
        else:
            fingerprint = max(all_frags, key=len)
            candidates = [p for p in pdf_paths if present(fingerprint, p)]
            if not candidates:
                unresolved.append((sf.name, "no raw PDF contains its longest quote (external/preview source, or quote not verbatim)"))
                continue
            # A short fingerprint is not evidence. Magrani 2019's longest quote is
            # 27 canonical characters and occurs in 73 PDFs; picking the argmax
            # would have silently verified it against an arbitrary paper.
            if len(fingerprint) < 60 and len(candidates) > 3:
                unresolved.append((sf.name, f"longest quote is only {len(fingerprint)} chars and matches "
                                            f"{len(candidates)} PDFs: too weak to resolve. Pin it with `verbatim-pdf:`."))
                continue
            best = max(candidates, key=lambda p: sum(1 for _, cf in quotes if cf and all(present(c, p) for c in cf)))
        audited_sources += 1
        for anchor, cf in quotes:
            if not cf:
                too_short.append((sf.name, anchor))
                continue
            audited_quotes += 1
            if not all(present(c, best) for c in cf):
                suspect.append((sf.name, anchor, best.name))

    print()
    if suspect:
        print(f"{RED}[VERBATIM-AUDIT] {len(suspect)} quote(s) NOT found in their source artefact:{RESET}")
        for name, anchor, pdf in suspect:
            print(f"  {name}")
            print(f"    {anchor}  -> not present in {pdf}")
        print()
    if unresolved:
        print(f"{YELLOW}[VERBATIM-AUDIT] {len(unresolved)} source(s) unresolved (coverage gap, not a failure):{RESET}")
        for name, reason in unresolved:
            print(f"  {name}: {reason}")
        print()
    if no_quotes:
        print(f"{YELLOW}[VERBATIM-AUDIT] {len(no_quotes)} source(s) UNCHECKED: no parseable quote in their Quotes section:{RESET}")
        for name, reason in no_quotes:
            print(f"  {name}: {reason}")
        print()
    if unquoted:
        print(f"{CYAN}[VERBATIM-AUDIT] {len(unquoted)} source(s) contain block(s) with no quotation marks (cannot be verified):{RESET}")
        for name, n in unquoted:
            print(f"  {name}  ({n} block(s))")
        print()
    if too_short:
        print(f"{CYAN}[VERBATIM-AUDIT] {len(too_short)} quote(s) too short to verify mechanically (skipped):{RESET}")
        for name, anchor in too_short:
            print(f"  {name}  {anchor}")
        print()

    if not suspect:
        print(f"{GREEN}[VERBATIM-AUDIT] clean: {audited_quotes} quotes across {audited_sources} sources verified present in their source artefact.{RESET}")
        return 0
    print(f"{RED}[VERBATIM-AUDIT] {len(suspect)} unverified quote(s) across {audited_sources} sources.{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
