# Citadel Dissertation Support Pack

A portable version of "Citadel" — a dissertation-support operating system that runs on top of Claude Code. It turns a plain folder of PDFs into an audited, cross-referenced research wiki, and gives the assistant a fixed disposition, a strict schema, a binding set of drafting rules, and the automation to keep all of it honest. You curate the sources and ask the questions; Citadel does the reading, writing, cross-referencing, citation-anchoring, and maintenance, and refuses to cite a page it cannot quote.

## What this pack is

Citadel is not a single tool. It is a small operating system for a Master's dissertation, made of six parts that work together:

- **Schema** — the rules for how knowledge is stored: page types (source / entity / concept / synthesis), frontmatter, confidence scores, the index, and the append-only log.
- **Disposition** — the stance the assistant carries between sessions: finish the loop, ship the complete artefact, anchor every citation, be brutally honest, no filler.
- **Rules** — a binding rule book for actually drafting a UK MSc dissertation: argument shape, chapter opening/closing tests, literature-review craft, methodology and ethics scaffolds, referencing, and a banned-word / prose-mechanics list.
- **Audit scripts** — shell and Python automation that checks the wiki for drift, broken links, unanchored citations, and quotes that are not really in the PDF.
- **Workflows** — the repeatable routines: ingest a source, answer a question, lint the wiki, and the session start/end commands.
- **Craft reference** — the longer-form dissertation-craft notes that the binding rule book distils.

The core promise is the **quote-anchoring rule**: every page number cited anywhere in the wiki must be backed by a verbatim quote on that source's page, and an audit script re-opens the PDF to prove the quote is really there. No "within range", no paraphrase with a page number tacked on, no fabricated citations.

## What is inside

```
Citadel Dissertation Support Pack/
  README.md             # this file — what the pack is
  GETTING-STARTED.md    # macOS step-by-step setup and the daily loop
  CLAUDE.md             # the schema + workflows (the operating manual; lives at the vault root)
  soul.md               # the disposition / stance file (lives at the vault root)
  rules.md              # binding UK MSc dissertation drafting rules (lives at the vault root)
  commands/
    bootup.md           # the /bootup slash command — session-start routine
    wrapup.md           # the /wrapup slash command — session-end audit + log
  scripts/
    lib.sh              # shared helpers; set your vault path here
    lint.sh             # drift + phantom-link + quote-anchor + decay audit
    quote-audit.sh      # quote-anchor coverage check (never opens the PDF)
    verbatim-audit.sh   # re-opens each cited PDF and confirms the quote is real
    decay.sh            # flags sources whose confidence has gone stale
    new-drop.sh         # finds un-filed PDFs dropped into raw/
    freshness.sh        # flags pages whose metadata was not bumped after edits
    sort-pdf.sh         # files a top-level PDF into a topic subfolder
    session-start.sh / session-stop.sh   # optional hook orchestrators
    extract_office.py / verbatim_audit.py # Python helpers used by the audits
    README.md           # what each script does and how to run it
  reference/            # dissertation-craft reference notes behind rules.md
```

`CLAUDE.md`, `soul.md`, and `rules.md` are the three files that get copied to the **root of your own vault folder**; `commands/` get copied into Claude Code's commands directory so `/bootup` and `/wrapup` work as slash commands; `scripts/` get copied into the vault so the audits can run. `GETTING-STARTED.md` walks through all of this for macOS.

## The pitch

Most dissertation "AI help" is a chat window with no memory, no rules, and no way to tell whether the citation it just gave you is real. Citadel is the opposite: a disciplined second brain that reads your sources once, files them with anchored quotes, remembers everything across sessions in a log it can never quietly rewrite, refuses to invent a page reference, and audits itself every time you close the laptop. It does not write your argument for you and it does not pretend your sources say things they do not. It keeps the evidence base clean, cross-referenced, and submission-ready, so the thinking that is actually yours has somewhere solid to stand.

---

*Institution-specific rules in this pack (word counts, named ethics committees, handbook specifics) reflect one UK MSc programme and must be verified against your own programme handbook. See `GETTING-STARTED.md`.*
