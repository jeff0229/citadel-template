#!/usr/bin/env bash
# Scan for new PDFs at raw/ top level + count 99-unclassified backlog.
# Exit: 0 = clean, 1 = new drops found.

. "$(dirname "$0")/lib.sh"

drops=$(new_drops)
u=$(unclassified_count)

if [ -n "$drops" ]; then
  color_cyan "[NEW-DROP] un-ingested PDFs at raw/ top level:"
  echo "$drops" | while IFS= read -r f; do
    printf '  - %s\n' "$(basename "$f")"
  done
  echo
fi

if [ "$u" -gt 0 ]; then
  color_yellow "[NEW-DROP] 99-unclassified backlog: $u PDF(s)"
fi

[ -n "$drops" ] && exit 1 || exit 0
