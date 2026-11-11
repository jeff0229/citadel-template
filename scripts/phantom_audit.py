"""Vault-wide phantom-wikilink audit.

WHY THIS EXISTS
---------------
Until 2026-07-09, lint.sh's phantom check read `index.md` and nothing else. Its
own comment described basename resolution across `wiki/**/*.md`, but the loop
underneath only ever fed it the index. Every session-end entry that said
"lint CLEAN" therefore meant "index.md has no dead links", not "the vault has
no dead links". Nine broken source citations had accumulated behind that.

WHAT COUNTS
-----------
A phantom is a `[[target]]` with no `target.md` anywhere under wiki/ or
archive/ (archive added 2026-10-15, see main()). Obsidian
resolves by basename, so `[[folder/Name]]` and `[[Name]]` are the same link.

Not phantoms, and excluded:
  * `![[embeds]]`  -- images and transclusions
  * links inside `code spans` or ```fenced blocks``` -- an audit page that
    *documents* a phantom must not be reported as having one
  * the `|alias` and `#heading` parts of a link

SEVERITY
--------
source-shaped   the target name contains a 4-digit year, so it is a citation to
                a source page that does not exist. These are real breakage:
                a reader clicks and lands nowhere. -> exit 1 (on live pages)
soft            a person or concept named with [[...]] whose page was never
                written (e.g. [[Orit Halpern]]). Obsidian shows these as
                unresolved. Cosmetic. Counted, listed with --soft.

Pages under `_archive/` and `assignment-drafts/` are reported but never fail the
build: archived material and submitted drafts are historical record.

Usage:  python phantom_audit.py [--vault DIR] [--soft] [--quiet]
"""

import argparse
import os
import collections
import pathlib
import re
import sys

CODE_FENCE = re.compile(r"```.*?```", re.S)
CODE_SPAN = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"(?<!!)\[\[([^\]|#\n]+?)(?:\|[^\]\n]*)?(?:#[^\]\n]*)?\]\]")
YEARISH = re.compile(r"\b(?:19|20)\d{2}\b")

IMMUTABLE = ("_archive", "assignment-drafts")

# 2026-08-10 -- the audit-the-auditors pass.
#
# The 2026-07-09 repair broadened this scan from "index.md and nothing else" to
# "wiki/ and nothing else", and in doing so it DROPPED index.md, which lives at
# the vault root. For thirteen months the master catalog -- 462 wikilinks, the
# one page a reader actually navigates from -- went from being the only page
# scanned to being the only page NOT scanned. Measured at the time of the fix:
# index.md was clean, 0 broken of 462, so the blind spot had cost nothing yet.
# Fixing an over-narrow scan by moving the window instead of widening it is its
# own failure mode.
#
# log.md is deliberately excluded and must stay excluded. It is append-only
# historical record and carries 18 source-shaped links to page names that were
# later renamed (Milner 2012 -> Milner 2016, Bossetta 2018 - Digital
# Architectures Framework -> ... of Social Media, and so on). Those links are
# correct as history and repairing them would mean editing the log, which
# soul.md forbids.
ROOT_SCAN = ("index.md", "rules.md", "CLAUDE.md", "soul.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.environ.get("VAULT_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--soft", action="store_true", help="list soft phantoms too")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    vault = pathlib.Path(args.vault)
    wiki = vault / "wiki"

    pages = {p.stem for p in wiki.rglob("*.md")}
    # 2026-10-15 -- wiki pages may link to stored text artefacts in archive/
    # (for example topic hubs that link many issues in archive/web/). Obsidian
    # resolves those by basename like any page, so they are real targets, not
    # phantoms. Only .md artefacts count; raw/ PDFs are cited through source
    # pages, never linked directly. A target missing from both wiki/ and
    # archive/ is still a phantom.
    pages |= {p.stem for p in (vault / "archive").rglob("*.md")}

    scan = sorted(wiki.rglob("*.md"))
    scan += [vault / n for n in ROOT_SCAN if (vault / n).is_file()]

    hard, soft = collections.defaultdict(set), collections.defaultdict(set)
    for p in scan:
        rel = str(p.relative_to(vault)).replace("\\", "/")
        text = CODE_SPAN.sub(" ", CODE_FENCE.sub(" ", p.read_text(encoding="utf-8", errors="replace")))
        for m in LINK.finditer(text):
            target = m.group(1).split("/")[-1].strip()
            if not target or target in pages:
                continue
            (hard if YEARISH.search(target) else soft)[target].add(rel)

    fail = 0
    if hard:
        live = {t: fs for t, fs in hard.items() if any(not any(i in f for i in IMMUTABLE) for f in fs)}
        print("\033[31m[PHANTOM] broken source citations (target page does not exist):\033[0m")
        for t, fs in sorted(hard.items()):
            for f in sorted(fs):
                tag = ""
                if any(i in f for i in IMMUTABLE):
                    tag = "  [immutable: report only]"
                print(f"  [[{t}]]\n     in {f}{tag}")
        fail = 1 if live else 0

    if soft and args.soft:
        print(f"\n\033[33m[PHANTOM] soft phantoms (person/concept pages never written): {len(soft)}\033[0m")
        for t, fs in sorted(soft.items(), key=lambda kv: -len(kv[1]))[:40]:
            print(f"  [[{t}]]  <- {len(fs)} page(s)")

    if not args.quiet:
        n_soft_inst = sum(len(v) for v in soft.values())
        # Report the size of what was actually READ, not the size of the target
        # universe. Those differ now that the root files are in scope, and a
        # scan-coverage number that silently means something else is the exact
        # habit this pass exists to break.
        print(f"\n[PHANTOM] scanned {len(scan)} pages ({len(pages)} link targets) | "
              f"broken source links: {sum(len(v) for v in hard.values())} | "
              f"soft phantoms: {len(soft)} targets / {n_soft_inst} links")
        if not fail:
            print("\033[32m[PHANTOM] no broken source citations on live pages.\033[0m")

    return fail


if __name__ == "__main__":
    sys.exit(main())
