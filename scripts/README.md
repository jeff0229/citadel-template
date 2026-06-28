# scripts/

Automation for the dissertation wiki. Mostly shell. `verbatim-audit.sh` (via `verbatim_audit.py`) and `extract_office.py` use Python 3, and `verbatim-audit.sh` also needs `pdftotext` (from the `poppler` package — `brew install poppler` on macOS). The shell scripts use GNU `grep`/`date`/`sed`; on macOS install them with `brew install coreutils grep gnu-sed` (`lib.sh` auto-prepends them to PATH).

## Scripts

| Script | Purpose | Exit |
|---|---|---|
| `lib.sh` | shared helpers (sourced, not executed) | — |
| `lint.sh` | drift + phantom-link + quote-anchor + decay audit | 0 clean / 1 issues |
| `new-drop.sh` | scan `raw/` top level + 99-unclassified backlog | 0 clean / 1 drops found |
| `quote-audit.sh` | dedicated quote-anchor check (anchoring coverage; never opens the PDF) | 0 clean / 1 issues |
| `verbatim-audit.sh [filter]` | re-extract each cited PDF, confirm every anchored quote is actually present (the only audit that opens the PDF) | 0 clean / 1 missing |
| `decay.sh [days]` | stale `last_confirmed` report, sources only (default 90d) | 0 always |
| `freshness.sh [--fix]` | metadata freshness: recent `updated:`-lag (fixable) + non-source confirm-decay | 0 clean / 1 issues |
| `sort-pdf.sh <pdf> <topic>` | move top-level PDF into subfolder | 0 moved / 1 missing |
| `session-start.sh` | SessionStart hook orchestrator | 0 always |
| `session-stop.sh` | Stop hook orchestrator | 0 always |

## Conventions

- All scripts source `lib.sh` for `VAULT_ROOT` and count helpers.
- All scripts print to stdout; hooks capture and inject into Claude's context.
- `--quiet` flag on `lint.sh` suppresses clean-state output (used by hooks to avoid spam).
- `VAULT_ROOT` auto-detects as the parent of `scripts/`; override it in `lib.sh` (or via the environment) if you run the scripts from elsewhere.

## Invocation

Direct:

```bash
bash scripts/lint.sh
bash scripts/quote-audit.sh
bash scripts/verbatim-audit.sh             # all sources; first run builds the PDF text cache
bash scripts/verbatim-audit.sh "Smith"     # spot-check at ingest: only matching source pages
bash scripts/decay.sh 60
bash scripts/new-drop.sh
bash scripts/freshness.sh        # report
bash scripts/freshness.sh --fix  # bump stale `updated:` fields on recently-edited pages
```

Via Claude skills: `/diss-lint`, `/diss-quote-verify`, `/diss-new-drop`.

Via hooks: auto-fire on SessionStart and Stop (see `.claude/settings.json`). The Stop hook runs `lint.sh` and `freshness.sh` and surfaces any drift.

## Verbatim audit (what it does and doesn't check)

`lint.sh` and `quote-audit.sh` check *anchoring coverage* — every cited `(p.N)` has a matching quote line — but never open the PDF, so they cannot tell whether a quote is real. `verbatim-audit.sh` does: for every quote it re-extracts the source PDF and confirms the text is present.

- **Resolution is automatic.** Each source page is matched to the raw PDF that contains the most of its quotes (gated on its longest quote). No frontmatter pointer or page-offset config — the cache lives in `scripts/.cache/verbatim/` and re-extracts only changed PDFs.
- **Tolerant by design.** Everything is reduced to a lowercase a–z string, so line-wraps, hyphenation, dropped/glyph fi-fl-ff ligatures, accents, smart quotes, footnote superscript digits, single-vs-double quote style, and an early quote-end all pass. A page-break footnote block dropped into a cross-page quote is tolerated by a one-gap forward fallback.
- **Still has teeth.** A fabricated, corrupted, or reversed-stitch quote fails — its letters are not present in order. (Validated against deliberately corrupted fragments.)
- **Out of scope.** Page accuracy (right quote, wrong page) and numbers inside a quote (years, page refs — digits are dropped). Page-offset correctness stays the human/ingest discipline recorded in each source page's `[!note]` callout.
- **Outputs.** `unresolved` = no raw PDF matched (external/preview source, e.g. a SAGE preview not in `raw/`) — reported, not fatal. `too short to verify` = quote under ~16 letters. Only a quote missing from a resolved PDF is a failure (exit 1).

## Semantic-drift audit (milestone gate)

The bash scripts catch string, anchor, and metadata drift. They do NOT catch *semantic* drift: a page making a claim about another page's contents that the other page no longer supports (for example, a gloss still naming a lit-review clause that has since been deleted, or a strand reframed from "optional" to "realised"). That needs a model.

The reusable audit lives as a drift-audit workflow under `.claude/workflows/`. It reads each page in scope, cross-checks its outbound claims against the current contents of the pages it references, and adversarially verifies each finding before reporting. It reports only; it never auto-fixes. (The workflow `.js` itself is project-specific and is not bundled in this pack — the FEATURE-CATALOG describes the pattern so your Claude Code can build one.)

```
# default scope: the dissertation-planning layer (cheap)
Workflow({ name: '<your-drift-audit>' })
# scope a single page + its dependencies
Workflow({ name: '<your-drift-audit>', args: { scope: 'page', target: 'wiki/synthesis/dissertation-planning/<some-page>.md' } })
# heavy full sweep
Workflow({ name: '<your-drift-audit>', args: { scope: 'all' } })
```

Run it before sending to the supervisor, before opening or closing a fieldwork phase, or after editing a heavily-referenced upstream page (methodology, lit review, schedule, ethics).

## Optional weekly LINT (macOS cron)

To run the lint automatically once a week, add a cron entry with `crontab -e` (replace the path with your vault):

```bash
0 9 * * 0 cd "$HOME/Dissertation/Vault" && bash scripts/lint.sh > scripts/last-lint.log 2>&1
```
