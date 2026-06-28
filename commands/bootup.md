---
description: Run the Citadel session-start boot routine (read soul/schema/rules/index/log, scan raw, check lint freshness, greet with status)
argument-hint: (no args needed; optionally name a focus for the session)
---
Boot the Citadel dissertation wiki. The vault is at `<VAULT_ROOT>` — replace this with your own vault path (for example `~/Dissertation/Vault`), and keep it consistent with the `VAULT_ROOT` you set in `scripts/lib.sh`. Run this BEFORE anything else this session. Do not skip a step because it "looks done" — the point is that these files have actually been read this session.

**1. Read the disposition and rule books (in this order):**
- `soul.md` — the stance (finish the loop, ship the complete thing, quote-anchoring non-negotiable, brutal honesty, no trailing summaries).
- `CLAUDE.md` — the wiki schema and workflows (auto-injected, but re-read so it is fresh).
- `rules.md` — the binding dissertation drafting rules (argument shape, chapter tests, banned-word list, prose mechanics).
- `index.md` — the page catalog.

**2. Read the recent log and memory:**
- `log.md` — read only the tail: the last ~5 `## [date] operation` entries AND the most recent **Carried forward** list. Do NOT read the whole file (it is large).
- Claude Code auto-memory (`MEMORY.md`) — auto-injected when present; confirm any feedback/project entries are in view.

**3. Scans (per the Session Start Protocol):**

> [!warning] Glob-tool caveat (read before scanning). The Glob *tool* ignores its `path` argument and matches the pattern from the **session cwd**. That cwd is the vault only when Claude Code was launched from inside the vault folder; when it is launched from elsewhere (e.g. your home directory), a bare `raw/**/*.pdf` silently returns nothing — a false "all clean". So enumerate with an **absolute pattern**, which works from any cwd: Glob `<VAULT_ROOT>/raw/**/*.pdf` (forward slashes), or run `find "<VAULT_ROOT>/raw" -name '*.pdf'` on the absolute vault path. Grep's `path` argument is honored; only Glob is affected. A scan that returns nothing must be re-run with the absolute form before it is reported as clean.

- Raw-folder scan: enumerate every `raw/**/*.pdf` under the absolute vault path (per the caveat) and diff against `wiki/sources/`. List any PDF inside a numbered topic subfolder with no matching source page as an un-ingested candidate (filename + subfolder). Exclude any `raw/00-…` scratch/craft subfolder (your own drafts and craft material — never ingest) and `raw/99-unclassified/` (untriaged backlog — flag only if you ask for triage). Do not auto-ingest.
- New-drop scan: list any PDF sitting at the top level of `raw/` (`raw/*.pdf`). Flag as new drops.

**4. Lint-freshness check:**
- Find the most recent `## [date] lint` entry in `log.md`. If it is ≥168 hours (7 days) old, run a LINT pass (`bash scripts/lint.sh` etc.) BEFORE handling the first request. Otherwise note the date and move on.

**5. Greet with a one-line status** (then stop and wait):
- sources / entities / concepts / synthesis counts, total pages, most recent operation and date;
- any un-ingested raw files and new drops;
- the **Carried forward** punch list from the most recent session-end entry, so the open items are visible.

If $ARGUMENTS names a focus for the session, note it but still run the full boot first.
