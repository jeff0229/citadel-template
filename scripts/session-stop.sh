#!/usr/bin/env bash
# Stop hook: drift check + log-entry reminder.
# Silent on clean state to avoid spam.

. "$(dirname "$0")/lib.sh" 2>/dev/null || true

cwd=$(pwd)
if [[ "$cwd" != *"Citadel"* ]]; then
  exit 0
fi

# Drift check.
bash "$VAULT_ROOT/scripts/lint.sh" --quiet
lint_rc=$?

# Metadata-freshness check (updated-lag + confirm-decay across all page types).
fresh_out=$(bash "$VAULT_ROOT/scripts/freshness.sh" --quiet 2>/dev/null)
fresh_rc=$?

if [ $lint_rc -ne 0 ] || [ $fresh_rc -ne 0 ]; then
  echo "=== DISS-WIKI STOP-CHECK ==="
  [ $lint_rc -ne 0 ] && echo "[HOOK] Lint reported drift or missing anchors. Re-run: bash scripts/lint.sh"
  if [ $fresh_rc -ne 0 ]; then
    echo "[HOOK] Metadata-freshness drift:"
    echo "$fresh_out"
    echo "[HOOK] Auto-fix updated-lag: bash scripts/freshness.sh --fix"
  fi
  echo "============================="
fi

exit 0
