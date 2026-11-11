---
name: ingest
description: Ingest a source into the Citadel knowledge library following the CLAUDE.md v3 intake rules. Handles any medium, from PDFs to exported chats, saved web pages, code and transcripts. Creates a source page with anchored quotes, updates entity and concept pages, updates index.md, and appends a log entry. Use when the user says "ingest X" or drops something new. Operates on the vault root (the folder that holds CLAUDE.md).
---

# ingest

Execute the CLAUDE.md v3 intake workflow on a source of any medium.

**Before starting, check whether this should be ingested at all.** Citadel keeps `wiki/` deliberately scarce, and promotion is triggered by use rather than by capture. Material earns a page when a question makes it matter or when the alternative is deriving the same conclusion twice. If it does not clear that bar, file it in `archive/` (or `raw/` for a PDF), say so, and stop. An un-promoted artefact is not a backlog.

## Workflow

1. **Read the source.**
   - **PDF:** from `raw/<NN-topic>/` or a top-level drop. Use `pdftotext -layout`. Flag image-only PDFs rather than guessing at their text.
   - **Chat export, markdown, code, saved page, transcript:** from `archive/<chats|notes-md|code|web|media>/`. If it is still in `inbox/`, triage it into `archive/` first with a `YYYY-MM-DD - <what> - <title>` filename. Never cite an artefact that exists only in a scrollback or a browser tab.

2. **Draft the source page** at `wiki/sources/<Name - ShortTitle>.md`:
   ```yaml
   ---
   type: source
   domain: dissertation | phd-application | careers | craft | tech | personal
   rigour: citable | personal
   medium: pdf | chat | web | code | media | markdown
   artefact: archive/<path>            # provenance, for a reader
   verbatim-text: archive/<path>       # non-PDF only, the audit hook
   tags: [...]
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   confidence: 0.0-1.0
   last_confirmed: YYYY-MM-DD
   ---
   ```
   `domain:` organises, `rigour:` decides which audits apply. Never conflate them. A text-backed page without `verbatim-text:` reports as an unresolved coverage gap forever, which means its quotes are never checked against anything.

3. **Anchor every citation.** Every locator cited anywhere on the page must have a verbatim quote in `## Quotes` carrying that same locator. The locator is whatever leads a reader back to the words in the stored artefact: `(p.5)` for print, a timestamp for a talk, `path:line` at a named commit for code, a heading or message position for a chat. No paraphrase, no "within range" fallback. There is no per-medium citation syntax to memorise: the quote is the anchor.

4. **Update or create entity pages** at `wiki/entities/` for named people, organisations, platforms and datasets.

5. **Update concept pages** at `wiki/concepts/` — bump the `sources:` counter and add to the page's Sources section.

6. **Update `index.md`** — add to the right list and update the footer counts (sources / entities / concepts / synthesis / notes).

7. **Prepend to `log.md`** (newest first, never edit older entries):
   ```
   ## [YYYY-MM-DD] ingest | <name> — one-line summary
   ```

8. **File the artefact.** A top-level PDF drop moves into the right `raw/<NN-topic>/`; ask when ambiguous, use `raw/99-unclassified/` when unrelated. Non-PDF material stays where it was archived, and `inbox/` is left empty.

9. **Verify.** Run `bash scripts/lint.sh --quiet`, and `bash scripts/verbatim-audit.sh` when the page is `rigour: citable`, to confirm the quotes are actually present in the artefact rather than merely well formed.

## Confidence scoring

- `0.9+` — primary empirical work directly relevant to a live question
- `0.7–0.85` — relevant methodology or theory
- `0.5–0.7` — reference or tangential but useful
- `<0.5` — flagged, consider de-prioritising

Score honestly rather than dismissively. A source that neither supports, challenges nor bounds anything currently live is peripheral, and saying so is more useful than inflating it.

## Do not

- Do not ingest from `raw/00-submissions-rubric-scratch/` or `raw/99-unclassified/`.
- Do not ingest into the **dissertation** domain. It closed on 2026-08-13. Its pages stay readable, linkable and citable, and submitted drafts are immutable.
- Do not use paraphrase or "within range" as an anchor.
- Do not mirror a live repo into the archive. Git is the better store, and a copy goes stale silently.
- Do not rewrite older `log.md` entries.

## After ingest

Report what was created and updated. Run `lint` to confirm a clean state.
