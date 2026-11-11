#!/usr/bin/env bash
# Confidence decay report: source pages with last_confirmed > N days.
# Usage: bash scripts/decay.sh [days]  (default 90)

. "$(dirname "$0")/lib.sh"

require_vault

days="${1:-90}"

out=$(stale_sources "$days")
# 2026-09-06: stale_sources exempts closed domains, and this script printed
# nothing about it. lint.sh reports the exempt count; run on its own, decay.sh
# passed silently over 138 dissertation pages and called it clean. An exemption
# nobody sees is indistinguishable from a check that never ran.
exempt=$(stale_closed_count)
[ "$exempt" != "0" ] && printf '[DECAY] exempt: %s source pages in closed domain "dissertation"\n' "$exempt"
if [ -z "$out" ]; then
  color_green "[DECAY] no sources older than $days days."
  exit 0
fi

color_yellow "[DECAY] sources with last_confirmed > $days days old:"
echo "$out" | while IFS=$'\t' read -r d n; do
  printf '  %s  %s\n' "$d" "$n"
done
exit 0
