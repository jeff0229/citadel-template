#!/usr/bin/env bash
# Metadata-freshness report. Two narrow, deterministic checks the existing
# scripts miss:
#
#   1. updated-lag  : a page edited in the last RECENT days whose frontmatter
#                     `updated:` is still older than the file mtime by more than
#                     the grace window. This is the "I edited it this session but
#                     forgot to bump `updated:`" signal -> fixable (--fix).
#   2. confirm-decay: `last_confirmed:` older than N days on NON-source pages
#                     (entities, concepts, synthesis). lint.sh/decay.sh already
#                     cover sources; this extends the coverage to the synthesis
#                     and planning layer, where most live drift accumulates.
#
# Why the RECENT window: a vault in a cloud-synced folder, and a bulk re-sync resets
# many file mtimes at once (e.g. the 2026-05-14 cluster). Comparing `updated:`
# against mtime across all history would flag the whole corpus. Restricting to
# files actually touched in the last few days isolates genuine session edits.
#
# `updated:` is the ONLY field this script ever writes. It never touches
# `last_confirmed` or `confidence`; those drive decay and stay human/agent-set.
# Semantic drift (a claim about another page's contents going stale) is NOT
# detectable here -> that is the milestone audit's job
# (.claude/workflows/citadel-drift-audit.js).
#
# Usage: bash scripts/freshness.sh [--fix] [--quiet] [--recent N] [--grace N] [--decay-days N]
# Exit:  0 clean / 1 issues found.

. "$(dirname "$0")/lib.sh"

require_vault

fix=0; quiet=0; recent=7; grace=3; decay_days=90
while [ $# -gt 0 ]; do
  case "$1" in
    --fix)        fix=1 ;;
    --quiet)      quiet=1 ;;
    --recent)     shift; recent="${1:-7}" ;;
    --grace)      shift; grace="${1:-3}" ;;
    --decay-days) shift; decay_days="${1:-90}" ;;
  esac
  shift
done

today=$(date +%Y-%m-%d)
lag_hits=0; decay_hits=0; fixed=0
lag_report=""; decay_report=""

while IFS= read -r f; do
  [ -f "$f" ] || continue
  rel="${f#"$VAULT_ROOT"/}"
  upd=$(fm_field "$f" updated)
  lc=$(fm_field "$f" last_confirmed)
  mt=$(file_mtime_date "$f")

  # Check 1: updated-lag, but only for files actually touched recently.
  if [ -n "$upd" ] && [ -n "$mt" ]; then
    mt_age=$(days_between "$mt" "$today" 2>/dev/null || echo 999)
    if [ "${mt_age:-999}" -le "$recent" ]; then
      gap=$(days_between "$upd" "$mt" 2>/dev/null || echo 0)
      if [ "${gap:-0}" -gt "$grace" ]; then
        lag_hits=$((lag_hits+1))
        lag_report+="  $upd -> $mt (${gap}d)  $rel"$'\n'
        if [ "$fix" -eq 1 ]; then
          # Stamp today: writing the field resets mtime to now, so stamping the
          # old mtime would re-flag on the next run. "Last touched = today" holds.
          sed -i "s/^updated:.*/updated: $today/" "$f" && fixed=$((fixed+1))
        fi
      fi
    fi
  fi

  # Check 2: confirm-decay on non-source pages (sources covered by lint/decay).
  #
  # 2026-09-06: closed domains are exempt. Confirm-decay asks whether a page has
  # been re-verified against its evidence lately; a domain that closed on
  # 2026-08-13 cannot drift, so this was reporting the same frozen planning pages
  # at an ever-growing age every run. Third instance of this pattern today, after
  # lint.sh and decay.sh. The count is printed rather than swallowed, because an
  # exemption nobody sees is indistinguishable from a check that never ran.
  if [ -n "$lc" ] && [[ "$f" != "$SOURCES_DIR"/* ]] && grep -qP '^domain:\s*dissertation\s*$' "$f"; then
    closed_exempt=$((${closed_exempt:-0}+1))
  elif [ -n "$lc" ] && [[ "$f" != "$SOURCES_DIR"/* ]]; then
    age=$(days_between "$lc" "$today" 2>/dev/null || echo 0)
    if [ "${age:-0}" -gt "$decay_days" ]; then
      decay_hits=$((decay_hits+1))
      decay_report+="  $lc (${age}d)  $rel"$'\n'
    fi
  fi
done < <(all_wiki_pages)

if [ "$quiet" -ne 1 ] && [ "${closed_exempt:-0}" -gt 0 ]; then
  printf '[FRESH] confirm-decay exempt: %s page(s) in closed domain "dissertation"\n' "${closed_exempt:-0}"
fi

if [ $((lag_hits + decay_hits)) -eq 0 ]; then
  [ "$quiet" -eq 1 ] || color_green "[FRESH] clean: no recent updated-lag, no non-source confirm-decay > ${decay_days}d."
  exit 0
fi

if [ "$lag_hits" -gt 0 ]; then
  if [ "$fix" -eq 1 ]; then
    color_yellow "[FRESH] updated-lag fixed on $fixed page(s) edited in the last ${recent}d (bumped to $today):"
  else
    color_yellow "[FRESH] updated-lag: edited in the last ${recent}d but \`updated:\` not bumped (run --fix):"
  fi
  printf '%s' "$lag_report"
fi

if [ "$decay_hits" -gt 0 ]; then
  color_yellow "[FRESH] confirm-decay: non-source pages with last_confirmed > ${decay_days}d (re-verify; report only):"
  printf '%s' "$decay_report"
fi

exit 1
