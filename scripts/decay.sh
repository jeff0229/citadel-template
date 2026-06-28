#!/usr/bin/env bash
# Confidence decay report: source pages with last_confirmed > N days.
# Usage: bash scripts/decay.sh [days]  (default 90)

. "$(dirname "$0")/lib.sh"

days="${1:-90}"

out=$(stale_sources "$days")
if [ -z "$out" ]; then
  color_green "[DECAY] no sources older than $days days."
  exit 0
fi

color_yellow "[DECAY] sources with last_confirmed > $days days old:"
echo "$out" | while IFS=$'\t' read -r d n; do
  printf '  %s  %s\n' "$d" "$n"
done
exit 0
