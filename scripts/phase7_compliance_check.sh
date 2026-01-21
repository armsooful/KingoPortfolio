#!/bin/bash
#
# Phase 7 준수 체크 (금지어 스캔 + Golden Test)
#
# 사용법:
#   ./scripts/phase7_compliance_check.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
PYTHON_BIN="python"

if [ -x "$VENV_PYTHON" ]; then
    PYTHON_BIN="$VENV_PYTHON"
fi

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp}"

echo "=== Phase 7 Compliance Check ==="
echo "- Forbidden terms scan"
"$SCRIPT_DIR/forbidden_terms_check.sh" "$PROJECT_ROOT/backend/app $PROJECT_ROOT/frontend/src"

echo ""
echo "- Golden Test v2"
"$PYTHON_BIN" -m pytest "$PROJECT_ROOT/docs/phase6/tests/test_golden_v2.py"
echo ""
echo "=== Done ==="
