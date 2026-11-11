# Feature catalog

Every feature, what it is for, and where it lives.

## The library (vault root)

| Feature | What it does | Where |
|---|---|---|
| Three layers | `inbox/` for capture, `archive/` and `raw/` for immutable originals, `wiki/` for a small set of audited pages | `CLAUDE.md` → The three layers |
| Promotion by use | A page is written when a question needs it, not when material arrives; answers that will recur are filed the same session | `CLAUDE.md` → Purpose, filing rule |
| Domain and rigour | `domain:` organises; `rigour: citable` turns the locator audits on, `personal` turns them off by declaration | `CLAUDE.md` → Domain and rigour |
| Closed domains | A submitted project stays readable and citable; nothing new is ingested and submitted drafts are immutable | `CLAUDE.md` |
| Page types | source, entity, concept, synthesis, note, each with fixed sections | `CLAUDE.md` → Page sections by type |
| Confidence and decay | A 0.1 to 1.0 score per page, decaying by 0.1 after 90 days unconfirmed; stale flags after 180 days | `CLAUDE.md` → Confidence scale |
| Tiers | episodic → semantic → procedural, with promotion criteria | `CLAUDE.md` → Knowledge lifecycle |
| Supersession and contradiction | Callouts on both pages; the old claim is never deleted | `CLAUDE.md` → Knowledge lifecycle |
| Intake by medium | Rules and locators for PDFs, LLM chats, code, web pages, talks and imported markdown | `CLAUDE.md` → Intake by medium |
| Live systems | Repos with their own `CLAUDE.md` stay separate; the wiki keeps a pointer note | `CLAUDE.md`, `cv-applier/`, `influencer-search/` |
| Prepend-only log | Newest first, never edited, with a Carried forward list at each session end | `log.md`, `CLAUDE.md` → Log conventions |
| Disposition | Finish the loop, ship the complete thing, honest confidence, no trailing summaries | `soul.md` |

## The audits (`scripts/`)

| Script | Checks |
|---|---|
| `lint.sh` | filesystem vs index counts, phantom wikilinks across every page, unanchored citations, stale sources (`phantom_audit.py`) |
| `quote-audit.sh` | anchoring in both directions: on each source page (`quote_audit.py`) and from every synthesis, concept, entity or citable note to the source it cites (`xref_audit.py`). Comma lists and ranges are parsed page by page |
| `verbatim-audit.sh` | re-extracts each cited PDF or pinned text file and confirms the quote is present (`verbatim_audit.py`); tolerant of line wraps, ligatures and quote style |
| `new-drop.sh` | top-level PDF drops, the 99-unclassified backlog, and every PDF in `raw/` that no source page claims, judged by content (`uningested_audit.py`) |
| `decay.sh 90` | sources whose `last_confirmed` is more than 90 days old, closed domains exempt |
| `freshness.sh` | edited pages whose `updated:` was not bumped (`--fix`) |
| `lint-strict.sh` | lint with failures as a non-zero exit, for hooks |
| `transcript-audit.sh` | thesis domains: every participant quotation in the submission is found in its transcript; NOT-IN-CORPUS is a hard fail (`transcript_audit.py`) |
| `redundancy_audit.py` | thesis domains: near-duplicate claims across chapters (advisory) |
| `docx-xref.sh` | thesis domains: every page citation in the submission docx is anchored (`docx_xref_audit.py`) |
| `sort-pdf.sh` | files a top-level PDF into a topic folder |
| `session-start.sh`, `session-stop.sh` | optional hook orchestrators |

## Commands and skills (`.claude/`)

| Name | Does |
|---|---|
| `/bootup` | reads the rule books and the log tail, scans inbox and raw, runs the weekly lint when due, greets with the open items |
| `/wrapup` | runs the audits, auto-fixes, prepends a session-end entry with a Carried forward list |
| `/ingest` | one source end to end: page, entities and concepts, index, log, PDF filed |
| `/crystallize` | a synthesis page from a finished thread |
| `/archive` | moves superseded material into `_archive/` without breaking links |

## The CV applier (`cv-applier/`)

| Feature | Where |
|---|---|
| One application end to end: audit, positioning, keywords, achievement rewrite, structure, tone, letter, outputs | `cv-applier/CLAUDE.md`, `.claude/skills/cv-tailor` |
| A single source of truth for dates and figures | `data/verified_facts.md` |
| Build to PDF with live links and a letter that steps its typography down to fit one page | `scripts/build.py` |
| Page count, link, text-order, fill, leakage and stale-string checks | `scripts/verify.py` |
| Retired claims fail the build | `scripts/check_claims.py` |

## The influencer search (`influencer-search/`)

| Feature | Where |
|---|---|
| A client brief written as pass/fail requirements; borderline is out | `influencer-search/CLAUDE.md` |
| Numbers passes, review images, add and reject, workbook rebuilt on every add | `process/score.py` |
| Contact sheets, 4 profiles per image, for fast visual review | `process/sheets.py` |
| A moving target | `process/target.py` |
| Review cycle, send to client, change the search focus | `skills/` |

## Thesis module

`rules.md` and `reference/` carry binding drafting rules and craft notes for a UK taught-masters dissertation: argument shape, chapter tests, literature review craft, methodology and ethics scaffolds, a page-number discipline and prose mechanics. Programme-specific rules must be checked against your own handbook.
