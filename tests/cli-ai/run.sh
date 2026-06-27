#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$ROOT/.venv-tests"

cd "$ROOT"

if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install -q -r "${ROOT}/tests/cli-ai/requirements.txt"
exec pytest "${ROOT}/tests/cli-ai/" -v "$@"
