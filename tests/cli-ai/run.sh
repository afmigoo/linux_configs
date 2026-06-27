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

ENV_FILE="${CLI_AI_ENV_FILE:-$ROOT/bin/.env}"
if [[ -z "${CLI_AI_ENDPOINT:-}" && -f "$ENV_FILE" ]]; then
    # Fallback only when env is not already sourced (e.g. source bin/.env && ./run.sh)
    # shellcheck source=/dev/null
    set -a
    source "$ENV_FILE"
    set +a
fi

exec pytest "${ROOT}/tests/cli-ai/" -v "$@"
