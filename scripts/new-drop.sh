#!/usr/bin/env bash
# What is pending ingest?
#   1. New PDFs sitting at raw/ top level (a fresh drop).
#   2. The 99-unclassified backlog.
#   3. Any PDF anywhere under raw/ that NO source page claims.
#
# (3) is new on 2026-07-09 and is the reason this file changed. The boot scan
# only ever diffed raw/01-* .. raw/09-*, so raw/10-PHD-application -- 108 PDFs --
# was never checked against wiki/sources. Nine book reviews sat filed and
# un-ingested for weeks, and a prep page came to claim an ingest that never ran.
# The check is content-based (see uningested_audit.py): a source page claims the
# PDF containing its longest quote. Filename matching was tried twice and lied
# both times.
#
# Usage: bash scripts/new-drop.sh [--no-uningested]
# Exit: 0 = clean, 1 = new top-level drops found (the un-ingested sweep reports
#       but does not gate, since "not yet ingested" is a decision, not a defect).

. "$(dirname "$0")/lib.sh"

require_vault

SKIP_UNINGESTED=0
[ "${1:-}" = "--no-uningested" ] && SKIP_UNINGESTED=1

drops=$(new_drops)
u=$(unclassified_count)

# 2026-09-07: the inbox was invisible to this script. `new_drops` only looks at
# raw/*.pdf, so anything dropped into inbox/ in any other format was reported
# nowhere, and both bootup and wrapup called this script believing it covered
# intake. A drop zone nothing scans is a drop zone that silently fills up.
inbox_items=$(find "$INBOX_DIR" -type f ! -name 'README.md' 2>/dev/null)
if [ -n "$inbox_items" ]; then
  color_cyan "[NEW-DROP] inbox/ awaiting triage:"
  echo "$inbox_items" | while IFS= read -r f; do
    printf '  - %s\n' "${f#"$INBOX_DIR"/}"
  done
  printf '  Triage into archive/ (or raw/ for PDFs) before ingesting. The inbox is not storage.\n'
fi

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

if [ $SKIP_UNINGESTED -eq 0 ]; then
  PDFTOTEXT="$(command -v pdftotext || true)"
  if [ -z "$PDFTOTEXT" ]; then
    color_yellow "[NEW-DROP] pdftotext not on PATH; skipping the un-ingested sweep."
  else
    python "$(cygpath -m "$(dirname "$0")/uningested_audit.py")" \
      --sources "$(cygpath -m "$SOURCES_DIR")" \
      --raw "$(cygpath -m "$RAW_DIR")" \
      --pdftotext "$(cygpath -m "$PDFTOTEXT")" \
      --cache "$(cygpath -m "$(dirname "$0")/.cache/verbatim")" \
      --quiet
  fi
fi

[ -n "$drops" ] && exit 1 || exit 0
