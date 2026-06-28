#!/usr/bin/env bash
# VERBATIM-AUDIT: re-extract each cited PDF and confirm every anchored quote
# is actually present (normalized match: ligatures, smart punctuation, and all
# whitespace folded, so line-wraps pass but fabrication/stitching fail).
#
# This is the one audit that opens the PDF. The bash/lint audits only check
# anchoring COVERAGE (every cited page has a quote line); they cannot catch a
# quote that was never in the source. This can.
#
# Page accuracy (right quote, wrong page) is out of scope by design -- see the
# header of verbatim_audit.py. Presence-in-the-source-PDF is the zero-config,
# high-leverage check that covers the batch-ingest blind spot.
#
# Usage: bash scripts/verbatim-audit.sh [NAME_FILTER ...]
#   NAME_FILTER restricts to source files whose name contains the string
#   (handy at ingest time: bash scripts/verbatim-audit.sh "Smith 2024").
# Exit: 0 = every resolved quote found; 1 = a quote is missing from its PDF.

. "$(dirname "$0")/lib.sh"

PY_ENGINE="$(dirname "$0")/verbatim_audit.py"
PDFTOTEXT="$(command -v pdftotext || true)"
if [ -z "$PDFTOTEXT" ]; then
  color_red "[VERBATIM-AUDIT] pdftotext not found on PATH; cannot run."
  exit 2
fi

python "$(cygpath -m "$PY_ENGINE")" \
  --sources "$(cygpath -m "$SOURCES_DIR")" \
  --raw "$(cygpath -m "$RAW_DIR")" \
  --pdftotext "$(cygpath -m "$PDFTOTEXT")" \
  --cache "$(cygpath -m "$(dirname "$0")/.cache/verbatim")" \
  "$@"
