# Feature Catalog

This is the centrepiece of the dissertation support pack. It enumerates everything the system does: the knowledge base, the audit machinery, the session protocols, the workflows, and the skills. Each capability below states what it is, why it matters for a dissertation, and how to invoke or use it.

**How to read this catalog.** The system is a single-folder knowledge vault ("the wiki") driven by a wiki agent (Claude Code), a set of bash and Python audit scripts, and a library of slash-command skills. None of it is tied to any one topic; it works for any literature-heavy dissertation that ingests sources, cites pages, and needs the citations to stay honest.

**Placeholder conventions used throughout.**
- `<VAULT>` is your vault root (the top folder that holds `CLAUDE.md`, `index.md`, `log.md`, `wiki/`, `raw/`, `scripts/`). Replace it with your own absolute path. In Git Bash form it looks like `/c/Users/you/.../YourVault`.
- `[your topic]`, `[your field]`, `[your code set]` mark places where the source vault hard-coded a specific subject. Substitute your own.
- Lines flagged "verify against your own programme handbook" are institution-specific (word counts, submission deadlines, named ethics committees, viva conventions). The machinery is reusable; the numbers are not. Confirm them against your own MSc/MA handbook before relying on them.

The original vault is a UK MSc dissertation build. The craft baked into it (chapter-opening and closing tests, a banned-word list, a page-number discipline, quote-anchored citation) is reusable across UK taught-masters dissertations. Keep it; re-point the specifics.

---

## 1. The knowledge base and the v2 page schema

**What it is.** A plain-Markdown vault, designed to open in Obsidian, with a fixed directory layout and a versioned page schema. The human curates sources and asks questions; the agent does all the reading, writing, cross-referencing, and maintenance. Four page types carry the whole knowledge base:

- `wiki/sources/` — one summary page per ingested source (a PDF, book, or paper).
- `wiki/entities/` — people, platforms, organisations, datasets.
- `wiki/concepts/` — theoretical frameworks, ideas, debates.
- `wiki/synthesis/` — analyses, comparisons, and answers filed as reusable pages, with subfolders for drafts, audits/review, planning, and methodology.

Source PDFs live under `raw/`, sorted into numbered topic subfolders (`01-<theme>`, `02-<theme>`, and so on, one per literature-review section or theme), plus `00-<your own drafts and rubric>` and `99-unclassified` for untriaged items. PDF contents are immutable. Only folder relocation is permitted.

Three control files sit at the vault root: `CLAUDE.md` (the schema and workflow rulebook, auto-read every session), `index.md` (the content catalog, updated on every ingest), and `log.md` (an append-only operation log). A fourth file, `rules.md`, holds your binding drafting rules (argument shape, chapter tests, word allocation, banned words); the source vault read it at every boot.

**The v2 page schema.** Every page carries YAML frontmatter and a one-line footer:

```yaml
---
type: entity | concept | source | synthesis
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: N                   # how many sources this page draws from
confidence: 0.0-1.0          # how well-supported the core claims are
last_confirmed: YYYY-MM-DD   # date last verified against a source
tier: episodic | semantic | procedural   # omit for source pages
---
```

Each page type has a fixed set of `##` sections so pages are predictable and foldable:
- **Source**: Overview, Key Points, Quotes, Entities and Concepts, Connections, Gaps and Questions.
- **Entity**: Summary, Key Facts, Role in Dissertation, Appearances, Connections, Open Questions.
- **Concept**: Definition, Why It Matters for This Dissertation, Examples, Tensions and Debates, Related Concepts, Sources.
- **Synthesis**: Question/Prompt, Answer/Analysis, Evidence, Caveats, Related Pages.

Cross-references use `[[wikilinks]]`, optionally typed inline (for example `[[Author Year]] (foundational)`, `(challenges)`, `(supersedes)`, `(supports)`). No orphan pages: every new page is linked from at least one existing page and added to `index.md`. A controlled domain vocabulary (your field's core constructs and key theoretical traditions) keeps terminology consistent across pages.

**Why it matters for a dissertation.** It replaces the usual scatter of Zotero, a reference manager, a notes app, and a pile of half-read PDFs with one queryable, internally consistent store. The fixed schema means a source page from week one and week twelve look the same, so you can audit the whole corpus mechanically. The wiki becomes the single source of truth: if a draft chapter cites a page and a fact, the page exists and the fact is on it.

**How to use it.** Open `<VAULT>` in Obsidian for navigation and the graph view. Drop new PDFs into `raw/` and run the INGEST workflow (section 6). Ask questions and run the QUERY workflow. Maintain it with LINT and the audit suite. Treat `index.md` and `log.md` as the spine: every operation updates the index and prepends a log line.

---

## 2. The quote-anchoring discipline and page-citation form rules

**What it is.** The non-negotiable rule at the heart of the system: every page number cited anywhere in the wiki must first exist as an anchored, verbatim quote in the cited source page's **Quotes** section. Verification is then a wiki-to-wiki match, with no PDF re-reads needed at audit time, no "within range" fallback, and no "structurally sound" hand-waving. If a synthesis needs a page that is not yet anchored, you read the PDF once, add the verbatim quote (quote marks only around actual source text) to the source page, then cite. The Quotes section becomes the single record of what a source says on a given page.

**Page-citation form rules.** These exist because the audit scripts tokenise citations:
- Cite a single page as `(p.5)`.
- Cite multiple discrete pages as a comma-separated list, `(pp.5, 7)`.
- Use a hyphenated range `(pp.5-7)` only when one quote genuinely spans the two facing pages. The anchor audit reads a hyphenated range as one token, so `(pp.5-7)` flags as unanchored even when pages 5 and 7 are each separately anchored. Comma-separated lists do not have this problem.

**Why it matters for a dissertation.** This is the difference between a citation you can defend in a viva and one you cannot. Page-specific claims are where examiners probe and where careless drafting invents support a source never gave. Anchoring forces the evidence to exist before the claim is made, and it makes every later audit cheap. It is the structural guard against the most common and most damaging research-integrity failure: a confident claim attributed to a page that does not carry it.

**How to use it.** When you write or revise any synthesis or source page, for every `(p.N)` you introduce, confirm a matching verbatim quote line sits in the source page's `## Quotes` section, formatted with the same `(p.N)`. If it is missing, open the PDF, copy the exact sentence, paste it under `## Quotes`, then cite. Two scripts check anchoring coverage automatically (`lint.sh` and `quote-audit.sh`, section 4); one checks the quote is real (`verbatim-audit.sh`, section 3).

---

## 3. The verbatim audit: the one audit that opens the PDF

**What it is.** `scripts/verbatim-audit.sh` (driven by `scripts/verbatim_audit.py`) is the only audit in the suite that re-opens the source PDF. For every anchored quote on every source page it re-extracts the PDF with `pdftotext` and confirms the quote's text is actually present in the document. The bash and lint audits only check anchoring coverage (does every cited page have a quote line?); they never open the PDF, so they cannot tell whether a quote is real. This one can.

**What it catches that string audits cannot.** Coverage audits are blind to fabrication. A quote can be invented, stitched together from two different places, reversed, or grossly misquoted, and still pass a coverage check because a quote line with the right page number exists. That blind spot is exactly what batch ingestion gets wrong: an agent rubber-stamps a quote that was never in the source. The verbatim audit closes it by reducing both the wiki quote and the PDF text to a lowercase a-to-z string and asking whether the quote's letters appear, in order, in the PDF.

**How it stays tolerant without losing teeth.** It folds out the things that legitimately differ between a wiki quote and a PDF extraction, and only those: line-wraps and hyphenation across line breaks, dropped or glyph-encoded fi/fl/ff ligatures, accents, smart quotes, dashes, ellipses, single-versus-double inner quote style, and footnote superscript digits. A footnote or page-break block dropped into the middle of a cross-page quote is tolerated by a forward-gap fallback. Despite that tolerance, a fabricated, corrupted, or reverse-stitched quote still fails, because its letters do not appear in forward order. (The matcher was validated against deliberately corrupted fragments.) PDF resolution is automatic: each source page is matched to the raw PDF that contains the most of its quotes, gated on its longest quote, so there is no per-source pointer or page-offset config to maintain.

**What it does not check (by design).** Page accuracy (right quote, wrong page) and any digits inside a quote (years, page numbers), because digits are dropped in normalisation. Quotes under about 16 canonical characters are flagged "too short to verify" and skipped. A source whose longest quote matches no PDF in `raw/` is reported "unresolved" (an external or preview source, not a failure). Only a quote missing from a resolved PDF is a failure.

**Why it matters for a dissertation.** It is the one mechanical defence against accidental fabrication, the single worst thing a literature-heavy dissertation can ship. Run before any draft leaves your hands, it converts "I am fairly sure that quote is right" into "the extractor found it in the PDF."

**How to invoke.**
```bash
bash scripts/verbatim-audit.sh             # all sources; first run builds the PDF text cache, re-runs are fast
bash scripts/verbatim-audit.sh "Author 2024"   # spot-check at ingest: only matching source pages
```
Dependencies: bash, python3 (on PATH), and `pdftotext` from poppler (shipped in Git Bash's `mingw64/bin`). Exit 0 = every resolved quote found; exit 1 = a quote is missing from its own PDF; exit 2 = `pdftotext` not found.

---

## 4. The six-script audit suite

The session-end protocol runs six scripts in order. Together they catch count drift, dead links, unanchored citations, fabricated quotes, stale confidence, metadata lag, and un-ingested backlog. All six source `scripts/lib.sh` for the vault paths and shared helpers, print to stdout, and are safe to run at any time. Common dependencies: bash for all six; python3 and poppler/`pdftotext` for the verbatim audit only.

### 4.1 lint.sh — drift, phantom links, anchor coverage, decay

**Checks.** Filesystem-versus-index count drift (sources, entities, concepts, synthesis: the footer counts in `index.md` must match the actual files); phantom wikilinks in `index.md` (every `[[link]]` must resolve to a real file by basename); unanchored cited pages (every `(p.N)` outside a Quotes section must have a matching `(p.N)` inside it); and sources whose `last_confirmed` is more than 90 days old.

**Why it matters.** It is the fast, all-in-one health gate. Count drift means the index lies about how much you have; phantom links mean a page you reference does not exist; unanchored pages mean a citation with no evidence behind it.

**Run.** `bash scripts/lint.sh` (add `--quiet` to suppress clean-state output, used by the session-start hook). Exit 0 = clean, 1 = issues.

### 4.2 quote-audit.sh — dedicated anchor coverage

**Checks.** A focused version of the lint anchor check across all source pages. Every `(p.N)` or `(pp.N)` cited in Key Points, Connections, or Gaps must have a matching quote in that page's Quotes section. It excludes the full-citation line from the scan so the source's own bibliographic page numbers do not register as claims.

**Why it matters.** This is the dedicated enforcement of the quote-anchoring rule (section 2). Run it before any draft to confirm zero unanchored citations across the whole corpus.

**Run.** `bash scripts/quote-audit.sh`. Exit 0 = all source pages clean, 1 = unanchored citations found. It never opens the PDF; it checks coverage only.

### 4.3 verbatim-audit.sh — quote-is-real check

**Checks.** Re-extracts each cited PDF and confirms every anchored quote is genuinely present. This is the only audit that opens the PDF. Full detail in section 3.

**Why it matters.** Coverage audits (4.1, 4.2) confirm a quote line exists; this confirms the quote is not fabricated or stitched. It is the guard on the batch-ingest blind spot.

**Run.** `bash scripts/verbatim-audit.sh [name filter]`. Needs python3 and `pdftotext`. Exit 0 clean, 1 a quote is missing from its source PDF.

### 4.4 decay.sh — confidence-decay report (sources)

**Checks.** Lists source pages whose `last_confirmed` is older than N days (default 90). Report only; it changes nothing.

**Why it matters.** Confidence is supposed to decay when a source has not been re-verified in a while. This surfaces which sources are due for a re-read before you lean on them again in drafting.

**Run.** `bash scripts/decay.sh [days]` (for example `bash scripts/decay.sh 60`). Always exits 0.

### 4.5 new-drop.sh — un-ingested backlog

**Checks.** Any PDF sitting at the top level of `raw/` (a "new drop" not yet sorted into a topic subfolder) and the count of PDFs in `raw/99-unclassified/`.

**Why it matters.** It is the inbox check. A PDF you dropped but never ingested is invisible to the wiki; this makes the backlog visible at session start and session end so nothing falls through.

**Run.** `bash scripts/new-drop.sh`. Exit 0 = clean, 1 = new drops found. The `99-unclassified` count is a standing flag, not a failure.

### 4.6 freshness.sh — metadata freshness (the two checks the others miss)

**Checks.** Two narrow, deterministic checks. First, updated-lag: a page edited in the last few days (default 7) whose frontmatter `updated:` is still older than the file's modification time beyond a grace window (default 3 days). This is the "I edited it this session but forgot to bump `updated:`" signal, and it is fixable. Second, confirm-decay on non-source pages (entities, concepts, synthesis) whose `last_confirmed` is older than N days (default 90), extending decay coverage beyond sources into the synthesis and planning layer where live drift accumulates. The recent-window restriction exists because the vault syncs through OneDrive, and a bulk re-sync resets many file mtimes at once; comparing across all history would flag the whole corpus.

**Why it matters.** Stale `updated:` dates make the log untrustworthy and hide which pages actually changed. The non-source confirm-decay catches drift in exactly the pages (methodology, planning, synthesis) that drive your drafting decisions.

**Run.** `bash scripts/freshness.sh` to report; `bash scripts/freshness.sh --fix` to bump the lagging `updated:` fields to today. It is the only script that writes the `updated:` field, and it never touches `last_confirmed` or `confidence`. Exit 0 clean, 1 issues.

**Supporting scripts (not part of the six, but part of the toolkit).**
- `scripts/lib.sh` — shared library (vault paths, count helpers, date math, colour output); sourced by every script, not run directly.
- `scripts/sort-pdf.sh <pdf> <topic>` — moves a top-level `raw/*.pdf` into a topic subfolder; the final step of INGEST.
- `scripts/session-start.sh` and `scripts/session-stop.sh` — hook orchestrators (section 5) that auto-fire `new-drop.sh`, `lint.sh`, and `freshness.sh` and only speak up when something is wrong.
- `scripts/extract_office.py` — pulls plain text from `.docx` and `.pptx` (zip-of-XML) without pandoc, for ingesting non-PDF sources.

---

## 5. Session protocols: /bootup and /wrapup

The agent cannot reliably self-detect a fresh session, so two user-invoked slash commands wrap the start and end routines. Run `/bootup` first thing and `/wrapup` last thing.

### 5.1 /bootup — session start

**What it is.** A nine-step boot routine. It reads the disposition and rule files in order (`soul.md` for stance, `CLAUDE.md` for schema, `rules.md` for drafting rules, `index.md` for the catalog), reads the tail of `log.md` (the last few operations plus the most recent **Carried forward** punch list) and confirms the cross-session memory is in view, scans `raw/` recursively for un-ingested PDFs and the top level for new drops, runs a lint-freshness check (if the last LINT was 7 or more days ago, it runs a LINT pass before doing anything else), and greets with a one-line status: source/entity/concept/synthesis counts, total pages, most recent operation, any un-ingested files, and the carried-forward punch list.

**Why it matters.** It guarantees the agent has actually read its rules this session rather than assuming it has, surfaces the open-items list so you resume where you stopped, and enforces a weekly health-check cadence without you having to remember it. It also carries a hard caveat worth keeping: the Glob tool ignores its `path` argument and matches from the session working directory, so raw-folder scans must use an absolute pattern or they silently return "all clean" when nothing was scanned.

**How to invoke.** Type `/bootup` at the start of every session. If work starts without it, run the nine steps before the first substantive action.

### 5.2 /wrapup — session end

**What it is.** A four-step close-out. It runs all six audit scripts (`lint.sh`, `quote-audit.sh`, `verbatim-audit.sh`, `decay.sh 90`, `new-drop.sh`, `freshness.sh`); auto-fixes surfaced problems in the same pass (count drift, phantom wikilinks, unanchored quotes, miscitations, stale citations), with quote-anchor fixes obeying the non-negotiable rule (re-read the PDF, anchor a verbatim quote, no paraphrase, no "within range" fallback) and confirmation reserved only for destructive actions like deletion or archiving; prepends a session-end entry to the top of `log.md` (`## [YYYY-MM-DD] review | session end ...`) recording the operations, the six-script result, and a fresh **Carried forward** list of every open item; then reports the summary and the carried-forward list.

**Why it matters.** It is the discipline that keeps the vault audit-clean across sessions and never loses an open thread. The carried-forward list is the bridge between sessions: every unresolved decision and flagged problem is written down so the next `/bootup` shows it.

**How to invoke.** Type `/wrapup` (or "end the session", "wrap up", "log all and end session"). A known legacy backlog of flagged quotes can make the verbatim audit non-clean; treat new failures from the current session as the actionable ones and carry the legacy backlog forward for triage.

---

## 6. The INGEST, QUERY, LINT, and CRYSTALLIZE workflows

Four named workflows in `CLAUDE.md` cover the full lifecycle of a source, from PDF to cited claim. Each ends by updating `index.md` and prepending a line to `log.md`.

### 6.1 INGEST — adding a new source

Read the PDF from its topic subfolder (or `raw/` top level for a new drop). Discuss the key takeaways before writing. Write `wiki/sources/Author Year - Short Title.md` with `tier: episodic` and a confidence score set by the Source Tier Rubric (section 8). Quote-anchor every citation. Update or create the entity and concept pages it touches, bumping `sources:` counters and `last_confirmed`. Check for supersession against existing claims. Update `index.md`. Prepend `## [YYYY-MM-DD] ingest | Source Title` to `log.md`. Sort the PDF into its topic subfolder (or `99-unclassified` if no topic fits). Run `lint.sh --quiet` to confirm no drift. Report what was created, updated, flagged, and where the PDF was filed. **Why it matters:** it turns a raw PDF into a fully cross-referenced, anchored, indexed node in one pass, so the corpus never accumulates half-ingested sources. **Invoke:** "ingest X", or the `/diss-ingest` skill (section 9).

### 6.2 QUERY — answering a question

Read `index.md` to find the relevant pages, read them, synthesise an answer with inline `[[citations]]` and typed relationships. If the answer is non-trivial (more than two paragraphs, a novel connection, or likely to recur), offer to file it as a synthesis page. If filed, write to `wiki/synthesis/`, set `tier: episodic`, add to `index.md`. Prepend a `query` line to `log.md`. **Why it matters:** it keeps answers grounded in the wiki rather than model memory, and converts good answers into reusable pages instead of throwaway chat. **Invoke:** just ask a question of the vault.

### 6.3 LINT — health check

Find and fix or flag: contradictions between pages, stale claims, orphan pages, concepts mentioned without their own page, missing cross-references, episodic pages that qualify for promotion, confidence scores to update, and gaps in theoretical coverage. The bundled source-reliability scan also checks metadata completeness, quote-anchor coverage, confidence decay, bibliographic integrity, and orphans. Prepend a `lint` line to `log.md`. **Why it matters:** it is the routine that keeps the whole vault internally consistent as it grows, and the standing rule is to auto-fix surfaced problems in the same pass rather than just reporting them. **Invoke:** "lint", "check drift", or `/diss-lint`.

### 6.4 CRYSTALLIZE — distilling a thread

After a substantial research thread, if the synthesis targets a chapter or section of the dissertation, read `rules.md` first so the output satisfies your drafting rules (argument shape, chapter tests, page-number rule, banned words, word allocation). Write a synthesis page (question, approach, findings, entities and concepts involved, lessons). Extract standalone facts to strengthen the pages the thread touched. Update confidence scores on corroborated or challenged pages. Promote pages that now qualify for a higher tier. Prepend a `crystallize` line to `log.md`. **Why it matters:** it captures the analytical work of a session as a durable, citable page instead of letting it evaporate, and it is where wiki maintenance meets actual drafting. **Invoke:** "crystallize X", "synthesise the evidence on Y", or `/diss-crystallize`.

---

## 7. The knowledge lifecycle: supersession, contradiction, decay, retention, tiers

The vault treats knowledge as something that ages, conflicts, and consolidates, not a static pile of notes. Five mechanisms manage that.

**Supersession.** When a new source makes an existing claim obsolete, both pages are flagged, never silently overwritten. On the new page: `> [!info] Supersedes: [[Old Page]] (YYYY-MM-DD)`. On the old page: `> [!warning] Superseded by: [[New Page]] as of YYYY-MM-DD`, with confidence revised downward. The old claim stands as a historical record, annotated. **Why it matters:** an examiner can see how your understanding moved, and you never quietly lose the earlier position.

**Contradiction.** When two sources disagree and both stay credible, a callout goes on both pages naming the claim, the rival claim, and the higher-confidence side, flagged for resolution. At lint, resolution prefers the higher-confidence, more recent, better-sourced claim. **Why it matters:** contradictions are often where the original contribution sits, so the vault surfaces them rather than burying them. (The full protocol is section 8.2.)

**Confidence decay.** Confidence is honest, not decorative. If `last_confirmed` is more than 90 days old, the score drops by 0.1 at the next lint. `decay.sh` and `freshness.sh` report what is due. **Why it matters:** it stops old, unverified claims from masquerading as settled, and it tells you what to re-read before you cite it again.

**Retention.** At lint, pages with `last_confirmed` older than 180 days and confidence under 0.5 get a `> [!note] Stale:` flag and are deprioritised in synthesis. Nothing is deleted without asking. **Why it matters:** weak, ageing material is quarantined rather than silently driving conclusions.

**Consolidation tiers.** Each page carries a `tier:` reflecting how settled it is. **episodic** is a fresh observation, close to raw, not yet cross-referenced (the default for new pages). **semantic** is cross-referenced and confirmed by two or more sources (promote at 2+ inbound links and confidence 0.6 or higher). **procedural** is a recurring pattern or framework (promote when it recurs across 3+ independent sessions or analyses). **Why it matters:** the tier tells you at a glance whether a page is a single-source jotting or a load-bearing, multiply-confirmed fact, and tiers are never promoted without meeting the criteria.

---

## 8. The methodology toolkit

Two dedicated methodology pages turn the lifecycle rules into operational rubrics. Both are topic-neutral and reusable.

### 8.1 Source Tier Rubric

**What it is.** A five-tier mapping from the numeric `confidence:` field to a written standard, so scoring is consistent across ingests and defensible under audit. T1 (0.90-1.0): primary empirical study directly relevant to your thesis, peer-reviewed, methodology visible, citable as load-bearing. T2 (0.75-0.89): strong expert analysis, peer-reviewed theory or framework, authoritative books, sound qualitative studies, cite as supporting. T3 (0.60-0.74): informed commentary or tangential-but-useful (working papers, cited long-form journalism, reference chapters). T4 (0.40-0.59): general-interest sources, popular science, think-tank reports with unclear funding, for orientation only. T5 (0.0-0.39): social or anecdotal (posts, blog rants), usable as signal that people are discussing something, never as evidence.

It includes red flags that downgrade a source one tier (no visible methodology or sources, author with a financial stake in the conclusion, publisher with a known agenda, cherry-picked timeframes, correlation sold as causation, emotional language doing data's job) and rare upgrade triggers (independent replication, a stronger revision, supportive longitudinal follow-up). Scoring during ingest: start from the source type's tier, apply red flags, then pick the number within the band by dissertation relevance rather than general quality, and when uncertain between two tiers pick the lower one.

**Why it matters.** It stops confidence scores from being arbitrary, which is what makes the whole decay-and-retention machinery trustworthy. In a viva, "I scored this 0.85 because it is a peer-reviewed empirical study directly addressing my research question" is defensible; a number with no rubric behind it is not.

**How to use.** During INGEST, follow the four scoring steps and record `confidence:` in frontmatter. Read it whenever you are unsure how to score a source or how to weigh two disagreeing ones. (Note: the rubric's worked examples in the source vault are field-specific; re-anchor them to your own corpus.)

### 8.2 Contradiction Protocol

**What it is.** A procedure for handling disagreement between sources without resolving it silently. It first distinguishes supersession (a newer source replaces an older one) from live contradiction (both remain credible and the disagreement is itself a finding). For live contradictions it runs four steps: (1) rule out trivial explanations (scope mismatch, timeframe mismatch, definitional mismatch, data-source mismatch), and if one applies, record it as a scope distinction rather than a contradiction; (2) classify the root of genuine disagreement (data, interpretation, mechanism, or incentive); (3) write a contradiction synthesis page stating each position, the likely root, the conditions under which each probably holds, the dissertation's stance or declared agnosticism, and what evidence would settle it; (4) if unresolvable, promote it to an open-questions page so it is visible when the lit review is drafted. It also lists when to suspect a hidden contradiction (suspicious unanimity, a high-confidence page with only two sources, or the user pushing back on a wiki-supported claim).

**Why it matters.** An honestly declared and well-scoped open question is stronger than a silently chosen position, and examiners reward the former. Contradictions are frequently where a dissertation's contribution lives, so the protocol makes you mine them rather than smooth them over.

**How to use.** When two sources clash, work the four steps. For supersession, set the `supersedes` / `superseded_by` frontmatter fields and annotate any synthesis page that cited the old claim. Pair it with the Source Tier Rubric: an incentive-driven contradiction often resolves once the conflicted source is downgraded a tier.

---

## 9. Project skills and automation

The vault ships a library of slash-command skills. Each is a packaged, repeatable run of a workflow above, plus a few that go beyond them. Invoke with the slash name shown.

**/diss-ingest.** Runs the nine-step INGEST workflow on a PDF: reads the source (using `pdftotext -layout`, flagging image-only PDFs), drafts the source page with full frontmatter, quote-anchors every citation with no "within range" fallback, updates or creates entity and concept pages, updates `index.md`, prepends a log line, sorts the PDF into its topic subfolder, and runs `lint.sh --quiet` to confirm no drift. It carries the confidence-scoring bands inline. **Use:** "ingest X" or when you drop a new PDF.

**/diss-lint.** Runs `lint.sh`, then acts on what it reports: fixes `index.md` footer counts to match the filesystem (filesystem is the source of truth, never the reverse), creates or removes phantom-linked pages, anchors missing quotes by re-reading the cited PDF, and bumps `last_confirmed` on stale sources whose claims still hold. Re-runs to confirm a clean exit and logs the fixes. **Use:** "lint", "check drift".

**/diss-quote-verify.** The strict enforcement of quote-anchoring. Runs `quote-audit.sh`, and for each violation opens the source PDF, reads the cited page, and either anchors a real verbatim quote that supports the claim or, if the page genuinely does not support it, fixes the citation to the correct page or removes the claim. It never invents a quote and never accepts "within range". It runs both a presence check (the quote is on the cited page) and a semantic-match check (the quote actually supports the claim). **Use:** "audit quotes", "verify anchors", and before submitting any draft.

**/diss-crystallize.** Builds a synthesis page that answers a load-bearing question across multiple sources: restates the question on one line, gathers and cites sources with anchored `(p.N)` citations, writes the analysis as numbered sub-claims, adds an evidence block and a caveats block, links related pages, sets frontmatter (including a source count and tier), files into the right synthesis subfolder, indexes it, and logs it. **Use:** "crystallize X", "synthesise the evidence on Y", or any cross-source analytical question that deserves a reusable page.

**/diss-weekly-review.** A scheduled health review. Runs `lint.sh`, `quote-audit.sh`, `decay.sh 90`, and `new-drop.sh`; summarises pass/fail per script, a numbered actions punch list, coverage gaps (themes with fewer than three sources, synthesis pages below 0.6 confidence), and a one-sentence next-week priority; auto-fixes fixable problems in the same pass; files a dated review page under `wiki/synthesis/audits and review/`; indexes and logs it. **Use:** "weekly review", "health check", or on a cadence. (An optional Windows Task Scheduler recipe in `scripts/README.md` can run the lint weekly and write the output to a log file.)

**/diss-archive.** Moves superseded or completed material into `wiki/synthesis/_archive/<phase>-<YYYY-MM>/` without breaking wikilinks (Obsidian resolves links by filename, so moves are safe), after confirming scope with you. It scans for backlinks to the archived pages, tags surviving references, updates `index.md` and its footer counts, logs the move, and lints. Archived pages stay readable; nothing is deleted. **Use:** when a drafting phase completes, or "archive the drafts".

**/diss-new-drop.** Detects un-ingested PDFs and queues them. Runs `new-drop.sh`, reads the first page of each top-level drop to identify author/year/title, proposes a target filename and topic subfolder, and confirms before running ingest. Reports the `99-unclassified` backlog. **Use:** "any new drops?", "scan raw", or at session start.

**/diss-council.** A structured decision review for genuine forks (a methodology choice, what to cut for word count, a framing decision, a plan that could fail in the viva, or a question that may rest on a false premise). Stage 0 verifies the premise against the wiki first and stops if the decision is already settled or the premise is false. Stage 1 answers the question through five committed lenses: the Examiner (where it loses a band against your drafting rules), the Methodologist (does the data-to-question-to-analysis chain hold?), the Skeptical Reader (where is a claim not quote-anchored?), the Supervisor (is it feasible in the time and word budget to your deadline?), and the Scope Hawk (the smallest version that still answers the research question). Stage 2 anonymises the five as shuffled Responses A-E and peer-reviews them (strongest, biggest blind spot, what all five missed). Stage 3 is the Chairman's plain-language verdict with one load-bearing reason, one concrete next step, and what the choice commits you to and rules out. **Why it matters:** it forces multi-perspective scrutiny on the handful of decisions that actually sink a dissertation, and Stage 0 stops it from dramatising a settled question. **Use:** sparingly, on real forks only. (The Supervisor lens and Examiner lens encode UK-MSc judging conventions; verify the deadline, word budget, and examiner expectations against your own programme handbook.)

**Field-note coding skills (digital-ethnography support).** For projects that collect their own observation-session screenshots, the vault ships a read-only `field-note-coder` subagent plus per-platform slash commands. The subagent (Read and Glob only, scoped to a fieldwork folder) transcribes and codes only the screenshot images you supply into anonymised, coded field-note table rows. Its hard rules are the reusable part: code only what is visible in a supplied image; never fetch, search, browse, scrape, or interpolate posts that are not shown; operate only on the current request's images with no cross-session memory; and apply a strict anonymisation rule (name an account only if it is a public figure by role or a named institution, paraphrase every ordinary user with no handle or searchable verbatim, strip incidental identifiers). The platform commands feed it a per-platform source-type schema and engagement fields, then append a project-specific code set and a tracked-hypothesis valence sub-code to each row, and remind you to paste the rows into your field-note template and fill the screenshot-reference and reflexive-note columns yourself. A companion hardening skill red-teams the coder against edge cases to keep it from confabulating. **Why it matters:** it gives reflexive thematic analysis a disciplined, auditable coding instrument that cannot quietly manufacture data or breach participant anonymity, with the researcher owning every code. **Use:** invoke the platform command on a screenshot set; substitute your own platforms, source-type schema, code set, and anonymisation threshold from your ethics approval. (The specific code set and re-identification clause in the source vault are tied to its study; replace them with your own approved scheme.)

---

## 10. The milestone semantic-drift audit (model-driven)

**What it is.** A model-driven audit that catches the one class of drift the bash scripts cannot. The scripts catch string, count, anchor, metadata, and quote drift. They cannot catch semantic drift: a live page asserting something about another page's contents that the other page no longer supports (a deleted clause a gloss still names, a strand reframed from "optional" to "realised", an eligibility line that moved, a section described as containing something it no longer does). Detecting that requires reading both pages and judging the claim, which is a model job, not a regex job.

The reusable audit lives at `.claude/workflows/drift-audit.js`. It reads each page in scope, cross-checks each page's outbound claims against the current contents of the pages it references, and adversarially verifies each finding before reporting. It reports only; it never auto-fixes. Scope is configurable: a single page and its dependents (cheap), a draft layer, the synthesis layer, or a full sweep (token-heavy).

**Why it matters.** The vault is append-only by design, which is honest but means a change to a heavily-referenced upstream page (methodology, lit review, schedule, ethics) can leave downstream pages quietly asserting the old version. This is the propagation step the append-only design otherwise leaves to chance, and the kind of internal inconsistency an examiner notices immediately. Because it adversarially verifies each finding before surfacing it, it does not flood you with false positives.

**How to invoke.** Run it as a milestone gate, not on a cadence: before anything goes to your supervisor, before opening or closing a fieldwork phase, and after editing a heavily-referenced upstream page. Invoke through the workflow runner, scoping it to the changed page for a cheap check or to the full vault for a heavy sweep:
```
Workflow({ name: 'drift-audit' })                                  # default: the planning layer (cheap)
Workflow({ name: 'drift-audit', args: { scope: 'page', target: 'wiki/.../Some Page.md' } })
Workflow({ name: 'drift-audit', args: { scope: 'all' } })          # full sweep, token-heavy
```
Prefer `scope: 'page'` for a single changed page and its dependents; reserve `scope: 'all'` for pre-submission sweeps. (The workflow file name in the source vault is namespaced to that vault; rename it for your own.)

---

*This catalog documents 10 capability groups. Substitute every `<VAULT>`, `[your topic]`, and bracketed placeholder for your own project, and verify all institution-specific rules against your own programme handbook before relying on them.*
