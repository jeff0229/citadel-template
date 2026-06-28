#!/usr/bin/env bash
# Shared helpers for diss-wiki automation.
# Source this file: . "$(dirname "$0")/lib.sh"

set -u

# The audit scripts use GNU tools (grep -P/-o, date -d, sed). On macOS these are
# BSD by default; prefer Homebrew's GNU builds when present. Install them with
# `brew install coreutils grep gnu-sed`, and this shim puts them first on PATH so
# `grep`/`date`/`sed` resolve to the GNU versions the scripts expect.
for _gnubin in \
  "$(brew --prefix 2>/dev/null)/opt/coreutils/libexec/gnubin" \
  "$(brew --prefix 2>/dev/null)/opt/grep/libexec/gnubin" \
  "$(brew --prefix 2>/dev/null)/opt/gnu-sed/libexec/gnubin"; do
  [ -d "$_gnubin" ] && case ":$PATH:" in *":$_gnubin:"*) ;; *) PATH="$_gnubin:$PATH" ;; esac
done
unset _gnubin
export PATH

# A UTF-8 locale keeps GNU grep -P happy (C.UTF-8 on Linux/Git-Bash, en_US.UTF-8 on macOS).
if locale -a 2>/dev/null | grep -qiE 'c\.utf-?8'; then export LC_ALL=C.UTF-8
elif locale -a 2>/dev/null | grep -qiE 'en_us\.utf-?8'; then export LC_ALL=en_US.UTF-8
fi

# Optional extra dir for Python console scripts. Set PY_SCRIPTS=/path if you need it.
PY_SCRIPTS="${PY_SCRIPTS:-}"
[ -n "$PY_SCRIPTS" ] && [ -d "$PY_SCRIPTS" ] && case ":$PATH:" in *":$PY_SCRIPTS:"*) ;; *) PATH="$PATH:$PY_SCRIPTS" ;; esac
export PATH

# Vault root auto-detects as the parent of this scripts/ folder. Override with
# VAULT_ROOT=/path/to/your/vault if you run these scripts from outside the vault.
VAULT_ROOT="${VAULT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)}"
SOURCES_DIR="$VAULT_ROOT/wiki/sources"
ENTITIES_DIR="$VAULT_ROOT/wiki/entities"
CONCEPTS_DIR="$VAULT_ROOT/wiki/concepts"
SYNTHESIS_DIR="$VAULT_ROOT/wiki/synthesis"
RAW_DIR="$VAULT_ROOT/raw"
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

index_counts() {
  # Returns "sources entities concepts synthesis" from index.md footer.
  if [ ! -f "$INDEX_FILE" ]; then
    echo "0 0 0 0"
    return
  fi
  local footer
  footer=$(grep -oP 'Sources: [0-9]+ \| Entities: [0-9]+ \| Concepts: [0-9]+ \| Synthesis: [0-9]+' "$INDEX_FILE" | tail -1)
  if [ -z "$footer" ]; then
    echo "? ? ? ?"
    return
  fi
  echo "$footer" | grep -oP '[0-9]+' | tr '\n' ' '
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
  local days="${1:-90}"
  local cutoff
  cutoff=$(date -d "$days days ago" +%Y-%m-%d 2>/dev/null || python -c "from datetime import date, timedelta; print((date.today() - timedelta(days=$days)).isoformat())")
  if [ ! -d "$SOURCES_DIR" ]; then return; fi
  for f in "$SOURCES_DIR"/*.md; do
    [ -f "$f" ] || continue
    local lc
    lc=$(grep -oP '^last_confirmed:\s*\K[0-9]{4}-[0-9]{2}-[0-9]{2}' "$f" | head -1)
    [ -z "$lc" ] && continue
    if [[ "$lc" < "$cutoff" ]]; then
      printf '%s\t%s\n' "$lc" "$(basename "$f")"
    fi
  done
}

all_wiki_pages() {
  # All wiki .md pages across sources/entities/concepts/synthesis,
  # excluding index.md and archived material.
  find "$SOURCES_DIR" "$ENTITIES_DIR" "$CONCEPTS_DIR" "$SYNTHESIS_DIR" \
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
