# Getting started

## 1. Install

- **Claude Code** (CLI): follow the install command for your operating system on claude.com, then run `claude` once to sign in.
- **Obsidian**: download it from obsidian.md.
- **Git Bash** (Windows only), which the audit scripts run in. macOS and Linux already have bash.
- **Python 3**, plus `pip install pypdf pillow python-docx openpyxl`.
- **Poppler** (`pdftotext`, `pdftoppm`), used by the verbatim audit and the CV checks.
- **wkhtmltopdf 0.12.6**, only if you use `cv-applier/`.

## 2. Make your vault

```
git clone https://github.com/<owner>/<this-repo>.git my-library
cd my-library
```

Then make the copy private: create a private repository of your own and point `origin` at it before you add anything personal.

Open the folder in Obsidian (Open folder as vault). Start Claude Code in the same folder:

```
cd my-library
claude
```

The commands in `.claude/commands/` and the skills in `.claude/skills/` load automatically for sessions started there.

## 3. Personalise

1. In `CLAUDE.md`, fill in **Purpose → Active fronts** and choose your `domain:` values.
2. Keep `soul.md` as it is or adjust the stance to taste.
3. If you are writing a thesis, keep `rules.md` and check every programme-specific rule in it against your own handbook. Otherwise delete it.
4. Make topic folders in `raw/` (`01-<topic>/`, `02-<topic>/` ...).
5. The scripts find the vault themselves (the folder above `scripts/`). To run them from elsewhere, set `VAULT_ROOT=/path/to/vault`.

## 4. The daily loop

- `/bootup` at the start of a session: reads the rule books and the log, scans the inbox and `raw/`, runs the weekly lint when due, and greets with the open items.
- Drop anything into `inbox/`. Ask for triage when you want it filed.
- `/ingest <file>` for a source worth a page. Ask questions; answers that will recur get filed as synthesis pages.
- `/crystallize` after a long thread.
- `/wrapup` at the end: the audits, auto-fixes, and a session-end log entry with a Carried forward list.

## 5. The sub-systems

- `cv-applier/`: copy `data/profile.example.json` to `data/profile.json`, fill in `data/verified_facts.md` and `data/master_cv.md`, then start a Claude Code session inside `cv-applier/` and paste a job description.
- `influencer-search/`: write the client's brief into its `CLAUDE.md`, choose a data source you are allowed to use, and start a session inside `influencer-search/`.

## Audits at a glance

```
bash scripts/lint.sh            # counts, phantom links, anchoring, stale sources
bash scripts/quote-audit.sh     # anchoring in both directions
bash scripts/verbatim-audit.sh  # quotes really present in the PDFs
bash scripts/new-drop.sh        # drops and un-ingested PDFs
bash scripts/decay.sh 90        # sources not confirmed in 90 days
bash scripts/freshness.sh       # edited pages with an old updated: date
```
