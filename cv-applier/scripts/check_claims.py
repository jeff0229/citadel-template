#!/usr/bin/env python3
"""
Scan the live drafting files for claims that verified_facts.md has retired.

Usage:
    python scripts/check_claims.py            # scan the default set
    python scripts/check_claims.py FILE ...   # scan named files

Why it exists: a correction made in verified_facts.md does not reach the CV bases and letters by itself. This script fails the build when a retired claim survives in any draft.

Paste-ready text is checked. Sections headed "Source notes", "Notes" or
"Open questions" are skipped, because they name retired claims on purpose.
Exit code 1 if anything is found.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Retired in verified_facts.md. Add a line here whenever a claim is retired there.
RETIRED = [
    # Claims retired in data/verified_facts.md. Add a line here in the same edit that retires one.
    # Lower-case; matched case-insensitively against every CV and letter draft. Examples:
    "led a team of 20",          # inflated: the team was 6
    "result pending",            # the result is in
]

SKIP_HEADINGS = re.compile(r"^#{1,3} +(source notes|notes|open questions|standing rules)\b", re.I | re.M)

DEFAULT = (
    [f for f in glob.glob(os.path.join(ROOT, "data", "*.md"))
     if os.path.basename(f) not in ("verified_facts.md",)
     and not os.path.basename(f).startswith("legacy_")]
    + glob.glob(os.path.join(ROOT, "applications", "_linkedin", "*", "profile_rewrite.md"))
)


def live_text(text):
    """Drop every section whose heading names it as notes, not paste-ready text."""
    out, skipping, level = [], False, 0
    for line in text.splitlines():
        m = re.match(r"^(#{1,6}) ", line)
        if m:
            this = len(m.group(1))
            if skipping and this <= level:
                skipping = False
            if not skipping and SKIP_HEADINGS.match(line):
                skipping, level = True, this
        if not skipping:
            out.append(line)
    return "\n".join(out)


def main():
    files = sys.argv[1:] or DEFAULT
    hits = 0
    for f in sorted(files):
        with open(f, encoding="utf-8") as fh:
            lines = live_text(fh.read()).splitlines()
        for n, line in enumerate(lines, 1):
            low = line.lower()
            for s in RETIRED:
                if s in low:
                    hits += 1
                    print("%s: retired claim %r: %s" % (os.path.relpath(f, ROOT), s, line.strip()[:120]))
    print("check_claims: %d file(s), %d hit(s)" % (len(files), hits))
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
