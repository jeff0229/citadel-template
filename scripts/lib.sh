#!/usr/bin/env bash
# Shared helpers for the Citadel audit scripts.
# Source this file: . "$(dirname "$0")/lib.sh"

set -u

# Git Bash on Windows defaults to a non-UTF-8 locale that breaks grep -P.
# C.utf8 is always available on mingw; forcing it fixes PCRE lookbehind in greps.
export LC_ALL=C.utf8

# Optional: add a Python scripts folder to PATH by setting PY_SCRIPTS before running.
if [ -n "${PY_SCRIPTS:-}" ] && [ -d "$PY_SCRIPTS" ]; then PATH="$PATH:$PY_SCRIPTS"; export PATH; fi

# The vault root defaults to the folder that holds scripts/. Override with VAULT_ROOT=/path/to/vault.
VAULT_ROOT="${VAULT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SOURCES_DIR="$VAULT_ROOT/wiki/sources"
ENTITIES_DIR="$VAULT_ROOT/wiki/entities"
CONCEPTS_DIR="$VAULT_ROOT/wiki/concepts"
SYNTHESIS_DIR="$VAULT_ROOT/wiki/synthesis"
NOTES_DIR="$VAULT_ROOT/wiki/notes"
RAW_DIR="$VAULT_ROOT/raw"
ARCHIVE_DIR="$VAULT_ROOT/archive"
INBOX_DIR="$VAULT_ROOT/inbox"
INDEX_FILE="$VAULT_ROOT/index.md"
LOG_FILE="$VAULT_ROOT/log.md"
CLAUDE_FILE="$VAULT_ROOT/CLAUDE.md"

count_md() {
  # Count .md files in a directory, ignoring errors if dir missing.
  local d="$1"
  if [ -d "$d" ]; then
    find "$d" -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' '
  else
    echo 0
  fi
}

count_synthesis() {
  # Synthesis pages, excluding index.md style files and _archive/ subfolders.
  if [ -d "$SYNTHESIS_DIR" ]; then
    find "$SYNTHESIS_DIR" -type f -name '*.md' ! -name 'index.md' ! -path '*/_archive/*' 2>/dev/null | wc -l | tr -d ' '
  else
    echo 0
  fi
}

count_notes() {
  # Note pages, recursive (notes may nest by domain), excluding _archive/.
  if [ -d "$NOTES_DIR" ]; then
    find "$NOTES_DIR" -type f -name '*.md' ! -name 'index.md' ! -path '*/_archive/*' 2>/dev/null | wc -l | tr -d ' '
  else
    echo 0
  fi
}

index_counts() {
  # Returns "sources entities concepts synthesis notes" from index.md footer.
  #
  # 2026-09-04: a fifth count joined the footer. The Notes count is optional in
  # the regex on purpose -- an older footer still parses -- but a missing count
  # returns "-" rather than 0, because 0 would compare equal to an empty
  # wiki/notes and print green over a footer that never mentioned notes at all.
  if [ ! -f "$INDEX_FILE" ]; then
    echo "0 0 0 0 -"
    return
  fi
  local footer notes
  footer=$(grep -oP 'Sources: [0-9]+ \| Entities: [0-9]+ \| Concepts: [0-9]+ \| Synthesis: [0-9]+' "$INDEX_FILE" | tail -1)
  if [ -z "$footer" ]; then
    echo "? ? ? ? ?"
    return
  fi
  notes=$(grep -oP 'Synthesis: [0-9]+ \| Notes: \K[0-9]+' "$INDEX_FILE" | tail -1)
  [ -z "$notes" ] && notes="-"
  printf '%s %s\n' "$(echo "$footer" | grep -oP '[0-9]+' | tr '\n' ' ')" "$notes"
}

new_drops() {
  # PDFs at raw/ top level (not in any subfolder). Prints file paths.
  find "$RAW_DIR" -maxdepth 1 -type f -name '*.pdf' 2>/dev/null
}

unclassified_count() {
  find "$RAW_DIR/99-unclassified" -maxdepth 1 -type f -name '*.pdf' 2>/dev/null | wc -l | tr -d ' '
}

stale_sources() {
  # Source pages with last_confirmed older than N days (default 90).
  #
  # 2026-09-04: closed domains are exempt. Confidence decay exists to catch a
  # live claim drifting away from its evidence; a dissertation submitted on
  # 2026-08-13 cannot drift, and printing 120 stale lines every run is how a
  # report teaches its reader to skip it. The exemption is by declared domain,
  # never by age, and the skipped count is printed so the exemption stays
  # visible rather than silent.
  local days="${1:-90}"
  local cutoff
  cutoff=$(date -d "$days days ago" +%Y-%m-%d 2>/dev/null || python -c "from datetime import date, timedelta; print((date.today() - timedelta(days=$days)).isoformat())")
  if [ ! -d "$SOURCES_DIR" ]; then return; fi
  for f in "$SOURCES_DIR"/*.md; do
    [ -f "$f" ] || continue
    local lc
    lc=$(grep -oP '^last_confirmed:\s*\K[0-9]{4}-[0-9]{2}-[0-9]{2}' "$f" | head -1)
    [ -z "$lc" ] && continue
    if grep -qP '^domain:\s*dissertation\s*$' "$f"; then
      STALE_SKIPPED_CLOSED=$((${STALE_SKIPPED_CLOSED:-0} + 1))
      continue
    fi
    if [[ "$lc" < "$cutoff" ]]; then
      printf '%s\t%s\n' "$lc" "$(basename "$f")"
    fi
  done
}

stale_closed_count() {
  # Source pages in a closed domain that stale_sources exempted on its last run.
  # Recomputed rather than exported, because stale_sources runs in a subshell
  # under command substitution and its variables do not survive.
  local n=0
  if [ -d "$SOURCES_DIR" ]; then
    n=$(grep -lP '^domain:\s*dissertation\s*$' "$SOURCES_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
  fi
  echo "$n"
}

all_wiki_pages() {
  # All wiki .md pages across sources/entities/concepts/synthesis/notes,
  # excluding index.md and archived material.
  find "$SOURCES_DIR" "$ENTITIES_DIR" "$CONCEPTS_DIR" "$SYNTHESIS_DIR" "$NOTES_DIR" \
    -type f -name '*.md' ! -name 'index.md' ! -path '*/_archive/*' 2>/dev/null
}

fm_field() {
  # Extract a frontmatter date field (YYYY-MM-DD). Args: file, field-name.
  grep -oP "^$2:\\s*\\K[0-9]{4}-[0-9]{2}-[0-9]{2}" "$1" 2>/dev/null | head -1
}

file_mtime_date() {
  # File modification time as YYYY-MM-DD.
  date -r "$1" +%Y-%m-%d 2>/dev/null
}

days_between() {
  # Whole days from $1 to $2 (negative if $1 is later). Args: date1, date2.
  local a b
  a=$(date -d "$1" +%s 2>/dev/null) || return 1
  b=$(date -d "$2" +%s 2>/dev/null) || return 1
  echo $(( (b - a) / 86400 ))
}

color_red()    { printf '\033[31m%s\033[0m\n' "$*"; }
color_green()  { printf '\033[32m%s\033[0m\n' "$*"; }
color_yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
color_cyan()   { printf '\033[36m%s\033[0m\n' "$*"; }

require_vault() {
  # 2026-08-10 -- the audit-the-auditors pass.
  #
  # Seven of the eight audit scripts printed FULL GREEN and exited 0 when
  # pointed at a vault that does not exist. The cause is that every helper in
  # this file degrades to empty on a missing directory: count_md returns 0,
  # index_counts returns "0 0 0 0", stale_sources returns nothing, new_drops
  # returns nothing. lint.sh then compares fs=0 against index=0, finds no
  # drift, and reports "[LINT] counts ok: S=0 E=0 C=0 Y=0" followed by
  # "[LINT] clean." Measured, not theorised:
  #
  #   VAULT_ROOT=/nonexistent bash scripts/lint.sh      -> "[LINT] clean."      exit 0
  #   VAULT_ROOT=/nonexistent bash scripts/decay.sh     -> "no sources older"   exit 0
  #   VAULT_ROOT=/nonexistent bash scripts/freshness.sh -> "[FRESH] clean"      exit 0
  #   VAULT_ROOT=/nonexistent bash scripts/quote-audit.sh -> "all 0 clean"      exit 0
  #   VAULT_ROOT=/nonexistent bash scripts/verbatim-audit.sh -> "clean: 0"      exit 0
  #   VAULT_ROOT=/nonexistent bash scripts/new-drop.sh  -> silent               exit 0
  #
  # transcript-audit.sh was the only one that failed loudly, and only because
  # its dead-default-path defect had already been repaired the same day. The
  # zeros are visible in the output, but the headline is green and the exit
  # code is 0, so any automated caller (session-start.sh, session-stop.sh,
  # the wrapup contract) reads success. A guard whose failure mode is silence
  # is not a guard.
  local missing=""
  [ -d "$VAULT_ROOT" ]  || missing="$missing VAULT_ROOT($VAULT_ROOT)"
  [ -d "$SOURCES_DIR" ] || missing="$missing wiki/sources"
  [ -d "$SYNTHESIS_DIR" ] || missing="$missing wiki/synthesis"
  [ -d "$NOTES_DIR" ]   || missing="$missing wiki/notes"
  [ -f "$INDEX_FILE" ]  || missing="$missing index.md"
  if [ -n "$missing" ]; then
    color_red "[GUARD] the vault was NOT found, so NOTHING WAS AUDITED."
    color_red "[GUARD] missing:$missing"
    color_red "[GUARD] this is not a clean result. Fix VAULT_ROOT or run from the vault."
    exit 2
  fi
}
