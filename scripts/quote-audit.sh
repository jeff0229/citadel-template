#!/usr/bin/env bash
# Quote-anchor audit, both directions.
#
#   PASS 1 (inward)  every (p.N) cited on a source page has a quote anchored at
#                    that page in the same page's Quotes section.
#   PASS 2 (outward) every (p.N) cited by a synthesis / concept / entity page is
#                    anchored in the SOURCE page it cites. This is the direction
#                    CLAUDE.md calls non-negotiable, and until 2026-07-09 no
#                    script checked it at all.
#
# The bash greps that used to live here mis-parsed comma page lists: `(pp.97, 98)`
# only ever had page 97 checked. Parsing now lives in quote_audit.py / xref_audit.py.
#
# Usage: bash scripts/quote-audit.sh [--quiet] [--xref-only] [--strict]
#   --strict  also fail on cross-page unanchored citations (default: report them,
#             exit on PASS 1 only, so the existing wrapup contract is preserved)

. "$(dirname "$0")/lib.sh"

require_vault

QUIET=0; XREF_ONLY=0; STRICT=0
for a in "$@"; do
  case "$a" in
    --quiet) QUIET=1 ;;
    --xref-only) XREF_ONLY=1 ;;
    --strict) STRICT=1 ;;
  esac
done

rc=0

if [ $XREF_ONLY -eq 0 ]; then
  qa_args=(--vault "$VAULT_ROOT")
  [ $QUIET -eq 1 ] && qa_args+=(--quiet)
  python "$(dirname "$0")/quote_audit.py" "${qa_args[@]}" || rc=1
fi

echo
python "$(dirname "$0")/xref_audit.py" --vault "$VAULT_ROOT"
xrc=$?
if [ $STRICT -eq 1 ] && [ $xrc -ne 0 ]; then
  rc=1
fi

exit $rc
