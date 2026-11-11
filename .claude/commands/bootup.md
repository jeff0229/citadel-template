---
description: Boot the Citadel knowledge library (read the disposition and rule books, the log tail, scan inbox and raw, check lint freshness, greet with status)
---
Boot the Citadel knowledge library. The vault is the folder that holds `CLAUDE.md` (the current working directory). Run this before anything else this session. Do not skip a step because it "looks done": the point is to have read these files this session.

**1. Read the disposition and rule books, in this order:**
- `soul.md`, the stance (finish the loop, ship the complete thing, anchoring is non-negotiable, honest confidence, no trailing summaries).
- `CLAUDE.md`, the schema, the three layers, the intake rules and the page types.
- `index.md`, the page catalog.
- `rules.md`, only when the session touches a thesis domain. It is that domain's drafting rule book, not a library-wide rule set.

**2. Read the recent log.** Read only the tail of `log.md`: the last 5 `## [date] operation` entries and the most recent **Carried forward** list. The log is prepend-only, newest first.

**3. Scans.**
- **Inbox:** list everything in `inbox/` except `README.md`. The inbox is a drop zone, never storage. Report what is there; do not auto-triage.
- **Raw:** run `bash scripts/new-drop.sh`. It reports top-level drops, the `99-unclassified` backlog, and every PDF under `raw/` that no source page claims (content-based). Do not auto-ingest. For a top-level drop, read its first page, propose a source filename and a `raw/<NN-topic>/` folder, and ingest only when asked.
- On Windows the Glob tool may ignore its `path` argument and match from the session's working directory. If a scan returns nothing, re-run it with an absolute pattern before reporting it as clean.

**4. Lint freshness.** Find the most recent `## [date] lint` or session-end `review` entry in `log.md`. If it is 7 or more days old, run the audits from `/wrapup` step 1 before handling the first request, auto-fix per `/wrapup` step 2, and prepend `## [YYYY-MM-DD] lint | weekly health check — <pass/fail>`. Always take the page counts from `lint.sh`.

**5. Optional extra steps.** Add your own standing boot steps here (for example a read-only email scan for application replies, archiving a newsletter, or restarting a long-running job). Keep them read-only unless a step is meant to write.

**6. Greet with a one-line status, then stop and wait:**
- page counts (sources / entities / concepts / synthesis / notes) and the total;
- anything in `inbox/` and any un-ingested `raw/` files;
- the most recent operation and its date;
- the Carried forward list from the latest session-end entry, filtered: drop anything a later entry closed or marked settled. One line per item, verb first, with its date, ordered by date. No background or history; the log holds those.
