---
name: archive
description: Archive superseded or completed material in the Citadel knowledge library into an _archive/ subfolder without breaking wikilinks. Use when a phase completes or the user says "archive X". Operates on the vault root (the folder that holds CLAUDE.md).
---

# archive

Move stale material into an archive subfolder while keeping Obsidian wikilinks intact.

## Workflow

1. **Confirm scope** with the user. Example: "archive wiki/synthesis/assignment-drafts/ after submission".
2. **Create the archive target**: `wiki/synthesis/_archive/<phase>-<YYYY-MM>/`.
3. **Move files** — NOT delete. Obsidian wikilinks resolve by filename, not path, so moves are safe.
4. **Scan for backlinks** that point to archived pages using Obsidian backlinks or a grep:
   ```bash
   grep -rn "\[\[<Archived Page Name>\]\]" wiki/
   ```
5. **Tag surviving references** — add `[archived]` suffix or a note that the target is now under `_archive/`.
6. **Update `index.md`** — decide whether the archived pages should remain in the index or be dropped from the main list. Typically: drop from main list, optionally keep a single "Archived material" link at the bottom.
7. **Log**:
   ```
   ## [YYYY-MM-DD] archive | <phase> — <N pages>
   ```
8. **Lint**.

## Rules

- Archived pages must remain readable. Never delete.
- Always update `index.md` footer counts to reflect what's now in the main vs. archive sections.
- If an archived page is cited by an active source, leave a redirect note at the old filename or update the active citation.
