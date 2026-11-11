#!/usr/bin/env bash
# Move a top-level raw/*.pdf into a raw/<NN-topic>/ subfolder.
# Usage: bash scripts/sort-pdf.sh <pdf_filename> <topic_folder>
# Topics: any raw/<NN-topic>/ folder you created, e.g. 01-<topic>, 02-<topic>, or 99-unclassified

. "$(dirname "$0")/lib.sh"

pdf="${1:-}"
topic="${2:-}"

if [ -z "$pdf" ] || [ -z "$topic" ]; then
  echo "usage: $0 <pdf_filename> <topic_folder>" >&2
  exit 2
fi

src="$RAW_DIR/$pdf"
dst="$RAW_DIR/$topic/$pdf"

if [ ! -f "$src" ]; then
  color_red "source not found: $src"
  exit 1
fi
if [ ! -d "$RAW_DIR/$topic" ]; then
  color_red "topic folder not found: $RAW_DIR/$topic"
  exit 1
fi

mv "$src" "$dst"
color_green "moved: $pdf -> $topic/"
