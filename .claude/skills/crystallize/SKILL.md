---
name: crystallize
description: Build a synthesis page in the Citadel knowledge library that distils a question across multiple sources, entities and concepts, in any domain. Writes to wiki/synthesis/ with confidence, sources, caveats and supersession-aware citations. Use when the user says "crystallize X", "synthesise the evidence on Y", or asks a cross-source analytical question that deserves a reusable page. Operates on the vault root (the folder that holds CLAUDE.md).
---

# crystallize

Produce a synthesis page that answers a load-bearing question using the wiki.

## Workflow

1. **Restate the question.** One sentence, on a single line. Goes into `## Question / Prompt`.
2. **Gather sources.** Grep the vault for relevant sources/entities/concepts. Check the Supervisor Draft and prior synthesis pages for adjacent work.
3. **Draft the answer.** Use `## Answer / Analysis` — the thesis, broken into numbered recommendations or sub-claims where helpful.
4. **Cite every claim.** Wikilinks `[[Author Year - Short Title]]` to source pages. Every page citation uses (p.N) and must be anchored in the source page (run `/diss-quote-verify` if uncertain).
5. **Evidence block.** `## Evidence` — empirical observations or direct quotes that underpin the answer.
6. **Caveats.** `## Caveats` — scope, assumptions, limits.
7. **Related pages.** `## Related Pages` — links to CLAUDE.md, rules.md, index.md, and sibling synthesis pages.
8. **Frontmatter.** Use:
   ```yaml
   ---
   type: synthesis
   tags: [...]
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   sources: <count-of-cited-source-pages>
   confidence: 0.0-1.0
   last_confirmed: YYYY-MM-DD
   tier: episodic | semantic
   ---
   ```
9. **File location.** Pick the right subfolder:
   - `wiki/synthesis/assignment-drafts/` — dissertation/assignment manuscript pieces
   - `wiki/synthesis/audits and review/` — audits, retrospectives, architecture notes
   - `wiki/synthesis/` root — general cross-source essays
10. **Index it.** Add a one-line entry to `index.md` under `## Synthesis` with a ≤120-char hook. Update footer synthesis count.
11. **Log.** Append to `log.md`:
    ```
    ## [YYYY-MM-DD] crystallize | <title> — <one-sentence outcome>
    ```
12. **Lint.** Run `bash scripts/lint.sh --quiet`.

## Supersession

If a new source supersedes an older claim, mark the claim as superseded and cite both. Prefer structured frontmatter `supersedes: [[OldSource]]` / `superseded_by: [[NewSource]]` over inline prose (per 2026-04-20 Wiki Architecture Recommendations §4).

## Style

- Active voice, no AI phrasing. Obey memory `feedback_writing_style`.
- Brutally honest advisor mode — no softening, no validation padding. Obey memory `feedback_advisor_mode`.
