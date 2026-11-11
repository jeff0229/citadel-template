#!/usr/bin/env bash
# TRANSCRIPT-AUDIT: check every participant quotation in the dissertation against
# the interview transcript it claims to come from.
#
# THE GAP THIS CLOSES. lint/quote-audit check that a cited page HAS an anchored
# quote. verbatim-audit checks that an anchored quote IS in its source PDF. None
# of them has ever opened `interviews/`, which sits outside `wiki/`. On
# 2026-07-26, after six consecutive "clean" six-script audits, a quotation
# attributed to a participant was found to appear nowhere in his record, along
# with four fidelity defects (unmarked elisions, a stitch, a reordering, and a
# dropped word that changed which conflict a quote was about). Anchor-level
# audits cannot see what a quotation does to its source. This can.
#
# Usage: bash scripts/transcript-audit.sh [--lenient] [TARGET ...]
#   With no TARGET it audits the current submission docx (if present) and the
#   dissertation-draft pages in wiki/synthesis/dissertation-drafts/.
#   --lenient downgrades unmarked-elision/altered to warnings (fabrication and
#   wrong-speaker always fail).
# Exit: 0 = clean; 1 = defect; 2 = cannot run.

. "$(dirname "$0")/lib.sh"

require_vault

PY_ENGINE="$(dirname "$0")/transcript_audit.py"
INTERVIEWS="$VAULT_ROOT/interviews"
DRAFTS="$VAULT_ROOT/wiki/synthesis/dissertation-drafts"
SUBMISSION="${SUBMISSION_DOCX:-$VAULT_ROOT/submission/dissertation.docx}"

if [ ! -d "$INTERVIEWS" ]; then
  color_red "[TRANSCRIPT-AUDIT] interviews/ not found at $INTERVIEWS; cannot run."
  exit 2
fi

LENIENT=""
TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --lenient) LENIENT="--lenient" ;;
    *) TARGETS+=("$arg") ;;
  esac
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  if [ -f "$SUBMISSION" ]; then
    TARGETS+=("$SUBMISSION")
  else
    # 2026-08-10: this path was stale for an unknown number of sessions and the
    # submission docx was silently dropped from every default-scope run, leaving
    # only the stale wiki mirrors to fail on. A missing submission target is now
    # loud. Override with SUBMISSION_DOCX=<path>.
    color_red "[TRANSCRIPT-AUDIT] submission docx NOT FOUND at: $SUBMISSION"
    color_red "[TRANSCRIPT-AUDIT] the file being submitted was NOT audited. Fix the path or pass it as an argument."
  fi
  if [ -d "$DRAFTS" ]; then
    while IFS= read -r f; do TARGETS+=("$f"); done < <(find "$DRAFTS" -maxdepth 1 -name '*.md' | sort)
  fi
fi

if [ ${#TARGETS[@]} -eq 0 ]; then
  color_red "[TRANSCRIPT-AUDIT] no targets found."
  exit 2
fi

python "$PY_ENGINE" --interviews "$INTERVIEWS" $LENIENT "${TARGETS[@]}"
rc=$?
if [ $rc -eq 0 ]; then
  color_green "[TRANSCRIPT-AUDIT] clean."
else
  color_red "[TRANSCRIPT-AUDIT] defects found (exit $rc)."
fi
exit $rc
