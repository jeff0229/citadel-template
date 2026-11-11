"""Source-page internal quote-anchor audit.

Every (p.N) cited on a source page OUTSIDE its Quotes section must have a quote
anchored at that page INSIDE the Quotes section.

This replaces the grep in quote-audit.sh, which had two parser bugs found
2026-07-09:

  * `(pp.97, 98)` -> the old PCRE captured only "97", so page 98 was never
    checked. That is the comma form CLAUDE.md tells authors to PREFER over a
    dash range, which means the recommended citation form was the one the
    auditor half-ignored. The rule in CLAUDE.md exists to route around a
    *different* symptom of the same bug (a dash range reads as one opaque
    token), so the rulebook was encoding a workaround for a defect.

  * lint.sh carried a second, divergent copy of this check whose regex matched
    `(p.N)` only and skipped every `(pp....)` citation outright. Two copies of
    one check, both wrong in different ways. lint.sh now calls this file.

Anchors may be written `(p.5)` or bare `p.5` inside the Quotes section; both
forms occur in this vault (Bossetta 2023, Mason 2018 use the bare form).

Usage: python quote_audit.py [--vault DIR] [--quiet]
Exit:  0 clean, 1 unanchored citations found.
"""

import argparse
import os
import pathlib
import re
import sys

CITE = re.compile(r"\(\s*pp?\.\s*([0-9][^)]*)\)")
LOOSE_ANCHOR = re.compile(r"pp?\.\s*([0-9]+(?:\s*[–—-]\s*[0-9]+)?)")


def parse_pages(blob):
    """Comma/range aware. Stops at the first non-page part so a nested citation
    ('p. 898, citing Bucher 2012, pp. 1174') cannot inject foreign pages, and a
    trailing year list ('p.87, 2019, 2022') is not read as pages."""
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
            if 1900 <= n <= 2099 and pages and max(pages) < 1900:
                break
            pages.add(n)
            continue
        break
    return pages, ranges


def split_sections(text):
    cited, quoted, in_q = [], [], False
    for line in text.splitlines():
        if line.startswith("## Quotes"):
            in_q = True
            continue
        if in_q and line.startswith("## "):
            in_q = False
        if "Full citation:" in line:
            continue
        (quoted if in_q else cited).append(line)
    return "\n".join(cited), "\n".join(quoted)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.environ.get("VAULT_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    src_dir = pathlib.Path(args.vault) / "wiki" / "sources"
    issues = total = 0

    for f in sorted(src_dir.glob("*.md")):
        total += 1
        cited_txt, quoted_txt = split_sections(f.read_text(encoding="utf-8", errors="replace"))

        anchored = set()
        for m in LOOSE_ANCHOR.finditer(quoted_txt):
            s, r = parse_pages(m.group(1))
            anchored |= s
            for a, b in r:
                anchored.update(range(a, b + 1) if b - a < 40 else [a])

        bad = []
        for m in CITE.finditer(cited_txt):
            s, r = parse_pages(m.group(1))
            bad += [str(p) for p in sorted(s - anchored)]
            for a, b in r:
                if not anchored & set(range(a, b + 1)):
                    bad.append(f"{a}-{b}")

        if bad:
            issues += 1
            print(f"{f.name}\n  cited but not quoted: {' '.join(sorted(set(bad)))}")

    if issues:
        print(f"\033[31m[QUOTE-AUDIT] {issues} of {total} source pages have unanchored citations.\033[0m")
        return 1
    if not args.quiet:
        print(f"\033[32m[QUOTE-AUDIT] all {total} source pages clean.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
