# Getting Started (macOS)

This guide sets up Citadel on a MacBook from scratch. It assumes you have Claude Code installed and that you are comfortable copying files in Finder and pasting a few commands into Terminal. You do not need to know how to code. Take it one step at a time; nothing here can damage your sources, because the system never edits your PDFs.

A quick mental model first: your **vault** is one folder on your Mac that holds everything — your PDFs go in `raw/`, and the assistant builds a wiki of notes in `wiki/`. Three setup files (`CLAUDE.md`, `soul.md`, `rules.md`) tell the assistant how to behave. The `scripts/` folder is the self-checking automation. That is the whole system.

---

## Step 1 — Create your vault folder

Pick a home for the project and make the folder. In Finder, or in Terminal:

```bash
mkdir -p ~/Dissertation/Vault
```

`~/Dissertation/Vault` is just an example. Anywhere in your home folder is fine. Whatever you choose, this is your **vault path** — you will reuse it in Step 5. Avoid moving it later, because the scripts point at it.

## Step 2 — Drop the three setup files at the vault root

From this pack, copy `CLAUDE.md`, `soul.md`, and `rules.md` into the **top level** of your vault folder (not into a subfolder):

```bash
cp CLAUDE.md soul.md rules.md ~/Dissertation/Vault/
```

- `CLAUDE.md` is the operating manual: the schema, the page types, and the workflows. Claude Code reads it automatically every session.
- `soul.md` is the disposition: how the assistant should behave (finish the job, anchor every citation, be honest).
- `rules.md` is the dissertation drafting rule book: argument shape, chapter tests, prose rules.

> [!important] Verify the rules against your own programme. `rules.md` was written for one UK MSc programme. Anything institution-specific — the **word count**, the **named ethics committee or ethics level**, **submission deadlines**, **referencing style**, and any **handbook specifics** — must be checked against your own programme handbook and your supervisor's guidance, and edited in `rules.md` to match. The reusable craft (how a literature review synthesises rather than lists, how a methodology justifies its design, how to open and close a chapter, the prose-mechanics list) carries across programmes; the hard numbers and committee names do not.

## Step 3 — Create the folder structure

Make the `raw/` folder (where your PDFs go) and the four `wiki/` subfolders (where the assistant writes its notes):

```bash
mkdir -p ~/Dissertation/Vault/raw
mkdir -p ~/Dissertation/Vault/wiki/sources
mkdir -p ~/Dissertation/Vault/wiki/entities
mkdir -p ~/Dissertation/Vault/wiki/concepts
mkdir -p ~/Dissertation/Vault/wiki/synthesis
```

What each one holds:
- `raw/` — your source PDFs. Drop new ones straight in here; the assistant files them into topic subfolders for you. You can later group them into numbered topic subfolders (for example `raw/01-…`, `raw/02-…`); a `raw/00-…` folder is the conventional place for your own drafts and scratch material that should never be ingested.
- `wiki/sources/` — one summary page per PDF you ingest, with the anchored quotes.
- `wiki/entities/` — people, platforms, organisations, datasets.
- `wiki/concepts/` — theories, frameworks, and debates.
- `wiki/synthesis/` — answers and analyses that pull several sources together.

You can also create empty `index.md` and `log.md` files at the vault root now, or simply let the assistant create them on the first ingest.

## Step 4 — Install the dependencies (Homebrew)

The audit scripts need: `bash` (a shell), `python3`, `pdftotext` (part of the `poppler` package — it lets the verbatim audit re-open your PDFs to check quotes), and the **GNU command-line tools** (`coreutils`, `grep`, `gnu-sed`), because the scripts use GNU options that macOS's built-in BSD versions lack. The easiest way to get all of them is [Homebrew](https://brew.sh). `lib.sh` automatically puts the GNU tools first on its PATH once they are installed, so there is nothing else to configure.

If you do not have Homebrew yet, paste this into Terminal and follow the prompts:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install the dependencies:

```bash
brew install poppler python3 bash coreutils grep gnu-sed
```

Quick check that `pdftotext` is available (this is the one people most often miss):

```bash
pdftotext -v
```

If that prints a version line, you are set. macOS already ships with `python3` and `bash`, so the Homebrew installs simply make sure you have current versions.

## Step 5 — Copy the scripts in and point them at your vault

Copy the whole `scripts/` folder from this pack into your vault:

```bash
cp -R scripts ~/Dissertation/Vault/
```

The scripts find your vault automatically: `VAULT_ROOT` defaults to the parent of the `scripts/` folder, so once `scripts/` lives inside your vault it just works — no editing needed. (If you ever want to run the scripts from somewhere else, open `~/Dissertation/Vault/scripts/lib.sh` and set `VAULT_ROOT="${VAULT_ROOT:-/Users/yourname/Dissertation/Vault}"` to your real path, written out in full because `~` does not expand inside the quotes.)

Finally, install the two slash commands so `/bootup` and `/wrapup` work inside Claude Code. Copy them into Claude Code's commands folder:

```bash
mkdir -p ~/.claude/commands
cp commands/bootup.md commands/wrapup.md ~/.claude/commands/
```

Open `~/.claude/commands/bootup.md` and `~/.claude/commands/wrapup.md` and replace the `<VAULT_ROOT>` placeholder near the top of each with your real vault path, so the routines know where to look.

## Step 6 — Open the vault in Claude Code and boot up

Open your vault folder in Claude Code (launch it from inside `~/Dissertation/Vault` so the tools default to the right place). Then run the boot routine by typing:

```
/bootup
```

This makes the assistant read `soul.md`, `CLAUDE.md`, `rules.md`, and the index and log, scan `raw/` for any un-filed PDFs, check whether a weekly lint is due, and greet you with a one-line status. Run it at the start of every working session. On a brand-new empty vault it will simply report that everything is empty and wait for your first source — that is the expected, healthy result.

---

## The daily loop

Once set up, the rhythm is short and repeatable:

1. **Start the session.** Type `/bootup`. Read the one-line status and the carried-forward punch list.
2. **Add a source.** Drag a PDF into the `raw/` folder, then tell the assistant: **"ingest it"** (or "ingest [filename]"). It reads the PDF, writes a source page with anchored quotes, updates the relevant concept and entity pages, updates the index, logs the operation, and files the PDF into a topic subfolder.
3. **Ask questions.** Ask anything about your sources in plain language — "what does the literature say about [your topic]?", "where do these two authors disagree?", "summarise the methodology debate". Answers come with citations that trace back to anchored quotes. If an answer is substantial, the assistant offers to save it as a synthesis page you can reuse.
4. **Lint weekly.** Once a week (the boot routine reminds you if it is overdue), type **"lint"** to run the health check: it finds drift, broken links, unanchored citations, and stale confidence scores, and fixes what it safely can.
5. **Wrap up at the end.** When you finish for the day, type **"wrap up"** (or `/wrapup`). It runs all six audit scripts, fixes what it can, and writes a session-end log entry with a carried-forward list, so next time `/bootup` shows you exactly where you left off.

That is the entire workflow. Drop a PDF, say "ingest it", ask your questions, lint weekly, wrap up at the end. Everything else — the schema, the cross-references, the citation checking, the log — the system maintains for you.

---

## A few things to remember

- **Your PDFs are never edited.** The system only reads them and, at most, moves them between folders. Your originals are safe.
- **The log is append-only.** It is an honest record of what happened, newest at the top. The assistant will not quietly rewrite history.
- **Citations are anchored to real quotes.** If the assistant cannot find a verbatim quote for a page, it will not cite that page. That is the point of the system, not a bug.
- **Verify the institution-specific rules.** Word count, ethics process, deadlines, and referencing style in `rules.md` reflect one programme. Confirm every one of them against your own handbook and supervisor before you rely on it.

Welcome to your second brain. Start by dropping in your first source.
