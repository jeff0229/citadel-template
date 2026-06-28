#!/usr/bin/env bash
# Dedicated quote-anchor audit. Every (p.N) citation in Key Points /
# Connections / Gaps must have a matching (p.N) quote in the Quotes section.

. "$(dirname "$0")/lib.sh"

issues=0
total=0

for f in "$SOURCES_DIR"/*.md; do
  [ -f "$f" ] || continue
  total=$((total+1))
  pages_cited=$(awk '/^## Quotes/{q=1; next} /^## /{q=0} /Full citation:/ {next} !q {print}' "$f" | grep -oP '\(pp?\.\s*\K[0-9]+(?:[-–][0-9]+)?' | sort -u)
  pages_quoted=$(awk '/^## Quotes/{q=1; next} /^## /{q=0} q {print}' "$f" | grep -oP '\(pp?\.\s*\K[0-9]+(?:[-–][0-9]+)?' | sort -u)

  bad=""
  for p in $pages_cited; do
    if ! echo "$pages_quoted" | grep -qxF "$p"; then
      bad="$bad $p"
    fi
  done
  if [ -n "$bad" ]; then
    issues=$((issues+1))
    printf '%s\n  cited but not quoted:%s\n' "$(basename "$f")" "$bad"
  fi
done

echo
if [ $issues -eq 0 ]; then
  color_green "[QUOTE-AUDIT] all $total source pages clean."
else
  color_red "[QUOTE-AUDIT] $issues of $total source pages have unanchored citations."
  exit 1
fi
