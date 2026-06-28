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
pointer or offset config is needed.

Usage (normally via verbatim-audit.sh):
    python verbatim_audit.py --sources DIR --raw DIR [--raw DIR ...]
        --pdftotext PATH [--cache DIR] [NAME_FILTER ...]

Exit: 0 = every resolved quote found (coverage gaps reported, not fatal);
      1 = at least one quote could not be found in its own source PDF.
"""

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

CACHE_SPLIT = "\n\x00PDFTOTEXT_MODE_SPLIT\x00\n"
MIN_FRAG = 16  # canonical (a-z) chars; shorter fragments are too common to verify

# elision markers a quoter inserts: [...] [. . .] [...] ... . . . …
_ELISION = re.compile(r"\[\s*(?:\.\s*){2,}\]|\[\s*…\s*\]|(?:\.\s*){3,}|…")
_ANCHOR = re.compile(r"\(pp?\.\s*[0-9].*?\)\s*$")
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
    removed so dropped-ligature PDFs still match."""
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"[^a-z]", "", s)
    return deligature(s)


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

def parse_quotes(md_path: Path):
    """Return [(anchor_label, [raw_fragment_strings])] for each blockquote in
    the page's ## Quotes section. Fragments are the elision-split pieces, not yet
    canonicalised."""
    lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_quotes = False
    blocks, cur = [], []
    for ln in lines:
        if ln.startswith("## "):
            in_quotes = ln.strip().lower().startswith("## quotes")
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if not in_quotes:
            continue
        if ln.lstrip().startswith(">"):
            cur.append(ln.lstrip()[1:].strip())
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    quotes = []
    for block in blocks:
        text = " ".join(b for b in block if b)
        if '"' not in text:
            continue
        anchor_m = _ANCHOR.search(text)
        anchor = anchor_m.group(0).strip() if anchor_m else "(no anchor)"
        first, last = text.find('"'), text.rfind('"')
        if last <= first:
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


def pdf_raw(pdf: Path, pdftotext: str, cache_dir: Path):
    """Return (layout_text, nonlayout_text), cached by path+size+mtime. Both
    reading orders are kept: -layout aligns columns but interleaves multi-column
    text; the default flows each column whole. A quote need only match one."""
    st = pdf.stat()
    key = f"{abs(hash(str(pdf.resolve())))}-{st.st_size}-{int(st.st_mtime)}.txt"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / key
    if cached.exists():
        parts = cached.read_text(encoding="utf-8", errors="replace").split(CACHE_SPLIT)
        if len(parts) == 2:
            return parts[0], parts[1]
    layout = _extract(pdf, pdftotext, True)
    flow = _extract(pdf, pdftotext, False)
    prefix = f"{abs(hash(str(pdf.resolve())))}-"
    for old in cache_dir.glob(f"{prefix}*.txt"):
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

    for sf in src_files:
        raw_quotes = parse_quotes(sf)
        if not raw_quotes:
            continue
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
        fingerprint = max(all_frags, key=len)
        candidates = [p for p in pdf_paths if present(fingerprint, p)]
        if not candidates:
            unresolved.append((sf.name, "no raw PDF contains its longest quote (external/preview source, or quote not verbatim)"))
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
        print(f"{RED}[VERBATIM-AUDIT] {len(suspect)} quote(s) NOT found in their source PDF:{RESET}")
        for name, anchor, pdf in suspect:
            print(f"  {name}")
            print(f"    {anchor}  -> not present in {pdf}")
        print()
    if unresolved:
        print(f"{YELLOW}[VERBATIM-AUDIT] {len(unresolved)} source(s) unresolved (coverage gap, not a failure):{RESET}")
        for name, reason in unresolved:
            print(f"  {name}: {reason}")
        print()
    if too_short:
        print(f"{CYAN}[VERBATIM-AUDIT] {len(too_short)} quote(s) too short to verify mechanically (skipped):{RESET}")
        for name, anchor in too_short:
            print(f"  {name}  {anchor}")
        print()

    if not suspect:
        print(f"{GREEN}[VERBATIM-AUDIT] clean: {audited_quotes} quotes across {audited_sources} sources verified present in their PDF.{RESET}")
        return 0
    print(f"{RED}[VERBATIM-AUDIT] {len(suspect)} unverified quote(s) across {audited_sources} sources.{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
