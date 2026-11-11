#!/usr/bin/env bash
# DOCX-XREF: every in-text page citation in the SUBMISSION DOCX is anchored in
# the source page it cites.
#
# THE GAP THIS CLOSES. verbatim_audit.py runs wiki source page -> PDF; xref_audit.py
# runs wiki synthesis -> wiki source page. Both walk `wiki/`. The dissertation master
# is a .docx outside the vault, so until 2026-08-10 nothing checked that ITS citations
# were anchored. The gap was masked while the chapter mirrors in
# `wiki/synthesis/dissertation-drafts/` tracked the master; since 2026-07-25 every
# drafting session has edited the docx alone and the mirrors lag by the whole
# v14 -> v29 sequence, so auditing the proxy stopped being a proxy for auditing it.
#
# The engine (`docx_xref_audit.py`) was written and run by hand on 2026-08-10, then
# by hand again on 08-13 and at that session's wrapup. This wrapper is the ninth
# entry point in the session-end contract, so it stops depending on somebody
# remembering the flag.
#
# Usage: bash scripts/docx-xref.sh [--quiet] [DOCX]
#   With no DOCX it audits the current submission master. Override the default with
#   the SUBMISSION_DOCX environment variable.
# Exit: 0 = every citation group anchored; 1 = unanchored or unresolvable; 2 = cannot run.

. "$(dirname "$0")/lib.sh"

require_vault

PY_ENGINE="$(dirname "$0")/docx_xref_audit.py"
SUBMISSION="${SUBMISSION_DOCX:-$VAULT_ROOT/submission/dissertation.docx}"

QUIET=""
DOCX=""
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET="--quiet" ;;
    *) DOCX="$arg" ;;
  esac
done
[ -n "$DOCX" ] || DOCX="$SUBMISSION"

if [ ! -f "$PY_ENGINE" ]; then
  color_red "[DOCX-XREF] engine not found at $PY_ENGINE; cannot run."
  exit 2
fi

if [ ! -f "$DOCX" ]; then
  color_red "[DOCX-XREF] docx not found at $DOCX; cannot run."
  color_yellow "  set SUBMISSION_DOCX or pass the path as an argument."
  exit 2
fi

python "$PY_ENGINE" --docx "$DOCX" --vault "$VAULT_ROOT" $QUIET
exit $?
