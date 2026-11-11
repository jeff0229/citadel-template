#!/usr/bin/env bash
# LINT: drift check + phantom-entity check + quote-anchor audit.
# Usage: bash scripts/lint.sh [--quiet]
# Exit: 0 = clean, 1 = drift detected.

. "$(dirname "$0")/lib.sh"

require_vault

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

fail=0

fs_s=$(count_md "$SOURCES_DIR")
fs_e=$(count_md "$ENTITIES_DIR")
fs_c=$(count_md "$CONCEPTS_DIR")
fs_y=$(count_synthesis)
fs_n=$(count_notes)

read -r idx_s idx_e idx_c idx_y idx_n <<< "$(index_counts)"

drift=0
[ "$fs_s" != "$idx_s" ] && drift=1
[ "$fs_e" != "$idx_e" ] && drift=1
[ "$fs_c" != "$idx_c" ] && drift=1
[ "$fs_y" != "$idx_y" ] && drift=1
[ "$fs_n" != "$idx_n" ] && drift=1

if [ $drift -eq 1 ]; then
  color_red "[LINT] DRIFT: filesystem vs index.md footer"
  printf '  sources:   fs=%s  index=%s\n' "$fs_s" "$idx_s"
  printf '  entities:  fs=%s  index=%s\n' "$fs_e" "$idx_e"
  printf '  concepts:  fs=%s  index=%s\n' "$fs_c" "$idx_c"
  printf '  synthesis: fs=%s  index=%s\n' "$fs_y" "$idx_y"
  printf '  notes:     fs=%s  index=%s\n' "$fs_n" "$idx_n"
  fail=1
else
  [ $QUIET -eq 0 ] && color_green "[LINT] counts ok: S=$fs_s E=$fs_e C=$fs_c Y=$fs_y N=$fs_n"
fi

# Phantom wikilink check -- VAULT-WIDE.
#
# 2026-07-09: this block used to read $INDEX_FILE and nothing else, while its
# comment claimed it resolved links "against any wiki/**/*.md". So "[LINT] clean"
# only ever meant "index.md has no dead links". Nine broken source citations had
# accumulated on other pages behind that green line. The scan now covers every
# page under wiki/, skips code spans and embeds, and fails only on broken
# *source* citations (a [[target]] carrying a year) found on non-immutable pages.
phantom_args=(--vault "$VAULT_ROOT")
[ $QUIET -eq 1 ] && phantom_args+=(--quiet)
if ! python "$(dirname "$0")/phantom_audit.py" "${phantom_args[@]}"; then
  fail=1
fi

# Quote-anchor audit (source pages, inward direction).
#
# This used to be a second, divergent copy of the check in quote-audit.sh. Its
# regex matched `(p.N)` only, so every `(pp....)` citation was skipped outright,
# while quote-audit.sh's copy read only the first page of a comma list. Two
# copies of one check, each wrong in a different way, both printing green.
# Single implementation now lives in quote_audit.py.
qa_args=(--vault "$VAULT_ROOT")
[ $QUIET -eq 1 ] && qa_args+=(--quiet)
python "$(dirname "$0")/quote_audit.py" "${qa_args[@]}" || fail=1

# Stale sources (>90 days since last_confirmed). Closed domains are exempt;
# the exemption is reported, not hidden.
stale_out=$(stale_sources 90)
stale_closed=$(stale_closed_count)
if [ -n "$stale_out" ]; then
  color_yellow "[LINT] Sources with last_confirmed > 90 days old:"
  echo "$stale_out" | while IFS=$'\t' read -r d n; do
    printf '  %s  %s\n' "$d" "$n"
  done
fi
if [ $QUIET -eq 0 ] && [ "$stale_closed" != "0" ]; then
  printf '[LINT] decay exempt: %s source pages in closed domain "dissertation"\n' "$stale_closed"
fi

if [ $fail -eq 0 ] && [ $QUIET -eq 0 ]; then
  color_green "[LINT] clean."
fi

exit $fail
