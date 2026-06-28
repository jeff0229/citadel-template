---
description: Run the Citadel session-end protocol (six-script audit, auto-fix, session-end log entry, report + carried-forward)
argument-hint: (no args needed)
---
Close the Citadel dissertation-wiki session. The vault is at `<VAULT_ROOT>` — replace this with your own vault path (for example `~/Dissertation/Vault`), and keep it consistent with the `VAULT_ROOT` you set in `scripts/lib.sh`. Run this when you end the session ("end the session", "wrap up", "log all and end session", or any equivalent). Do not skip a step.

**1. Run all six audit scripts** from the vault root (`bash scripts/<name>`):
- `lint.sh` — filesystem ↔ index counts, phantom wikilinks, unanchored cited pages, >90-day stale sources.
- `quote-audit.sh` — every `(p.N)` cited outside a Quotes section is anchored in that source page's Quotes section.
- `verbatim-audit.sh` — re-extracts each cited PDF and confirms every anchored quote is actually present (the only audit that opens the PDF; first run builds a text cache, re-runs are fast). If you have deliberately chosen to carry forward a backlog of pre-existing flagged quotes, those are noted in `log.md`; treat NEW failures (from this session's edits) as the actionable ones.
- `decay.sh 90` — sources with `last_confirmed` older than 90 days.
- `new-drop.sh` — top-level `raw/*.pdf` drops plus the `99-unclassified` backlog count.
- `freshness.sh` — recently-edited pages whose `updated:` field was not bumped (fixable with `freshness.sh --fix`), plus confirm-decay on non-source pages.

**2. Auto-fix surfaced problems in the same pass** — count drift, phantom wikilinks, unanchored quotes, miscitations, stale citations. Quote-anchor fixes obey the non-negotiable quote-anchoring rule (re-read the PDF, anchor a verbatim quote, no paraphrase, no "within range" fallback). Confirmation is reserved for destructive actions only (deleting or archiving pages or files). Re-run the relevant script to confirm clean. The `99-unclassified` backlog is a standing flag, not a repair item — leave it unless triage is requested.

**3. Prepend a session-end entry at the top of `log.md`** (newest first): `## [YYYY-MM-DD] review | session end — <pass/fail summary>`. Record the session's operations, the six-script result, and a **Carried forward** list of every open item, unresolved decision, and flagged problem, so the next session starts with the punch list visible. Prepend-only (newest at top); never edit past entries.

**4. Report** the session-end summary and the carried-forward list. No trailing fluff.
