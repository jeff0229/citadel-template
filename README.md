# Citadel

A template for running your own knowledge library, CV applier and influencer search on Claude Code and Obsidian. Clone it, open the folder as an Obsidian vault, start Claude Code inside it, and run `/bootup`.

This repo is the structure only: the schema, the rules, the audit scripts, the skills and the commands. It holds no one's content. Your notes, sources and documents stay in your copy.

## What is inside

```
citadel/
  CLAUDE.md            # the library's operating manual: layers, page types, intake, workflows, audits
  soul.md              # the librarian's disposition, carried between sessions
  rules.md             # optional: binding drafting rules for a thesis or dissertation domain
  index.md, log.md     # empty catalog and prepend-only log
  inbox/               # drop zone, emptied by triage
  archive/             # kept originals (chats, web, code, notes, media), immutable
  raw/                 # the PDF wing, one folder per topic
  wiki/                # sources, entities, concepts, synthesis, notes
  scripts/             # the audits (lint, two-way quote anchoring, verbatim check, un-ingested sweep, decay, freshness, thesis audits)
  .claude/commands/    # /bootup and /wrapup
  .claude/skills/      # /ingest, /crystallize, /archive
  reference/           # dissertation-craft notes behind rules.md
  cv-applier/          # a job application system with its own CLAUDE.md
  influencer-search/   # a brief-driven creator shortlist with its own CLAUDE.md
```

## The three systems

**Citadel, the library.** Capture and knowledge are kept apart. `inbox/` takes anything, `archive/` and `raw/` keep immutable originals without limit, and `wiki/` holds a deliberately small set of linked, audited pages. A page is written when a question is asked that it answers, not when material arrives. Two frontmatter fields do separate jobs: `domain:` organises, `rigour:` (`citable` or `personal`) decides which audits apply.

The core rule is quote-anchoring: every page number cited anywhere is backed by a verbatim quote on the source page. The audits check this in both directions, and `verbatim-audit.sh` re-opens the PDF (or the pinned text file) to prove the quote is really there. `new-drop.sh` finds every PDF no source page claims, by content rather than filename.

**The CV applier** (`cv-applier/`). One application end to end: a rejection audit, positioning, keyword alignment, achievement rewriting, structure, tone, cover letter and verified PDFs. `data/verified_facts.md` is the single source for dates and figures; `check_claims.py` and `verify.py` fail the build when a retired claim or a wrong date comes back. Rendering lessons for wkhtmltopdf on Windows are written into its `CLAUDE.md`.

**The influencer search** (`influencer-search/`). A client's brief written as pass/fail requirements, a numbers check on every candidate, a visual review on contact sheets, and a shortlist workbook rebuilt on every add. Borderline is out. It ships the workflow and the scoring and workbook code, not platform automation: plug in a data source you are allowed to use.

Each sub-system is a live system with its own `CLAUDE.md`. Start its sessions inside its folder so its rules govern the work.

## Start here

See `GETTING-STARTED.md` for setup on Windows and macOS, and `FEATURE-CATALOG.md` for every feature and where it lives.

## Keeping your copy private

Fork or clone this into a **private** repository before you add your own material. The `.gitignore` files keep PDFs, office documents, images, research participant data, CV documents and creator data out of git by default.
