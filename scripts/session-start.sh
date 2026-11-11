#!/usr/bin/env bash
# SessionStart orchestrator. Prints a compact status block for Claude.
# Called by Claude Code hook; output is injected into Claude's context.

. "$(dirname "$0")/lib.sh" 2>/dev/null || true

# Only fire when the diss vault is the CWD (avoids firing in other projects).
cwd=$(pwd)
if [[ "$cwd" != *"Citadel"* ]]; then
  exit 0
fi

echo "=== DISS-WIKI SESSION-START ==="

bash "$VAULT_ROOT/scripts/new-drop.sh" || true
bash "$VAULT_ROOT/scripts/lint.sh" --quiet || true

echo "================================="
exit 0
