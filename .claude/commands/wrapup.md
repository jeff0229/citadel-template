---
description: Close a Citadel session (run the audits, auto-fix, prepend a session-end log entry with a Carried forward list, report)
argument-hint: (no args; add "full" to force the thesis-domain audits as well)
---
Close the Citadel session. The vault is the folder that holds `CLAUDE.md`. Run this when the human ends the session ("wrap up", "end the session", or any equivalent). Do not skip a step.

The audits split into two classes. Which ones you run depends on what the session touched; say which class you ran.

**1a. Library-wide audits, always** (`bash scripts/<name>` from the vault root):
- `lint.sh`: filesystem vs index counts, phantom wikilinks, unanchored cited pages, stale sources.
- `quote-audit.sh`: anchoring in both directions. Pass 2 skips pages declaring `rigour: personal` and reports the skipped count.
- `verbatim-audit.sh`: re-extracts each cited artefact and confirms every anchored quote is present. Text-backed pages must pin `verbatim-text:` or they report as an unresolved coverage gap, which is honest but unchecked.
- `decay.sh 90`: sources with `last_confirmed` older than 90 days, closed domains excluded.
- `new-drop.sh`: drops, the 99-unclassified backlog, and un-ingested PDFs. It does not see `inbox/`, so check the inbox separately.
- `freshness.sh`: edited pages whose `updated:` was not bumped (`--fix` bumps them).

**1b. Thesis-domain audits,** when the session touched a thesis domain or the human says "full":
- `transcript-audit.sh`: every participant quotation in the submission is found in its transcript. NOT-IN-CORPUS is a hard fail.
- `redundancy_audit.py <file.docx>`: near-duplicate claims across chapters (advisory).
- `docx-xref.sh`: every page citation in the submission docx is anchored. Set `SUBMISSION_DOCX`.

**2. Auto-fix what the audits surface** in the same pass: count drift, phantom wikilinks, unanchored quotes, miscitations, stale citations. Anchoring fixes obey the non-negotiable rule: re-read the source, anchor a verbatim quote, no paraphrase, no "within range". Repair only; ask before deleting or archiving anything. Re-run the script to confirm.
- Counts: the filesystem is the truth. Fix drift by correcting the `index.md` footer to the `lint.sh` counts.
- No supporting sentence at the cited locator: do not invent one and do not fall back to a nearby page. Re-point the citation or cut the claim.

**3. Prepend a session-end entry to `log.md`:** `## [YYYY-MM-DD] review | session end — <pass/fail summary>`. Record the session's operations, which audit class ran and its result, and a **Carried forward** list of every open item, unresolved decision and flagged problem.

**4. Report** the summary and the Carried forward list. Say which audit class ran.
