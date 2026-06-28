#!/usr/bin/env bash
# LINT: drift check + phantom-entity check + quote-anchor audit.
# Usage: bash scripts/lint.sh [--quiet]
# Exit: 0 = clean, 1 = drift detected.

. "$(dirname "$0")/lib.sh"

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

fail=0

fs_s=$(count_md "$SOURCES_DIR")
fs_e=$(count_md "$ENTITIES_DIR")
fs_c=$(count_md "$CONCEPTS_DIR")
fs_y=$(count_synthesis)

read -r idx_s idx_e idx_c idx_y <<< "$(index_counts)"

drift=0
[ "$fs_s" != "$idx_s" ] && drift=1
[ "$fs_e" != "$idx_e" ] && drift=1
[ "$fs_c" != "$idx_c" ] && drift=1
[ "$fs_y" != "$idx_y" ] && drift=1

if [ $drift -eq 1 ]; then
  color_red "[LINT] DRIFT: filesystem vs index.md footer"
  printf '  sources:   fs=%s  index=%s\n' "$fs_s" "$idx_s"
  printf '  entities:  fs=%s  index=%s\n' "$fs_e" "$idx_e"
  printf '  concepts:  fs=%s  index=%s\n' "$fs_c" "$idx_c"
  printf '  synthesis: fs=%s  index=%s\n' "$fs_y" "$idx_y"
  fail=1
else
  [ $QUIET -eq 0 ] && color_green "[LINT] counts ok: S=$fs_s E=$fs_e C=$fs_c Y=$fs_y"
fi

# Phantom wikilink check: resolve each [[link]] against any wiki/**/*.md by basename.
# Supports both [[Flat Name]] and [[subfolder/Name]] forms; Obsidian resolves by
# filename so subfolder prefix is cosmetic.
phantom=0
if [ -f "$INDEX_FILE" ]; then
  while IFS= read -r link; do
    [ -z "$link" ] && continue
    raw="${link//[\[\]]/}"
    base="${raw##*/}"
    if ! find "$VAULT_ROOT/wiki" -type f -name "${base}.md" 2>/dev/null | grep -q .; then
      [ $phantom -eq 0 ] && color_yellow "[LINT] Phantom wikilinks in index.md (target file missing):"
      printf '  - [[%s]]\n' "$raw"
      phantom=$((phantom+1))
      fail=1
    fi
  done < <(grep -oP '\[\[[^\]|#]+\]\]' "$INDEX_FILE" | sort -u)
fi

# Quote-anchor audit: find (p.N) citations in sources without matching quote.
missing=0
for f in "$SOURCES_DIR"/*.md; do
  [ -f "$f" ] || continue
  # Cited pages from Key Points / Connections / Gaps (not Quotes section).
  pages_cited=$(awk '/^## Quotes/{q=1; next} /^## /{q=0} !q {print}' "$f" | grep -oP '\(p\.\s*\K[0-9]+' | sort -u)
  pages_quoted=$(awk '/^## Quotes/{q=1; next} /^## /{q=0} q {print}' "$f" | grep -oP '\(p\.\s*\K[0-9]+' | sort -u)
  for p in $pages_cited; do
    if ! echo "$pages_quoted" | grep -q "^${p}$"; then
      [ $missing -eq 0 ] && color_yellow "[LINT] Cited pages without quote anchors:"
      printf '  %s  p.%s\n' "$(basename "$f")" "$p"
      missing=$((missing+1))
      fail=1
    fi
  done
done

# Stale sources (>90 days since last_confirmed).
stale_out=$(stale_sources 90)
if [ -n "$stale_out" ]; then
  color_yellow "[LINT] Sources with last_confirmed > 90 days old:"
  echo "$stale_out" | while IFS=$'\t' read -r d n; do
    printf '  %s  %s\n' "$d" "$n"
  done
fi

if [ $fail -eq 0 ] && [ $QUIET -eq 0 ]; then
  color_green "[LINT] clean."
fi

exit $fail
