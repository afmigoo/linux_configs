from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AI_SCRIPT = REPO_ROOT / "bin" / "cli-ai"
ENV_FILE = REPO_ROOT / "bin" / ".env"

MAX_TOKENS_PER_TEST = 5_000
MAX_TOKENS_SUITE = 500_000
RUN_TIMEOUT = 120

MINIMAL_PROMPT = "Reply with the single word OK"


def estimate_tokens(*parts: str) -> int:
    return sum(max(1, len(p) // 4) for p in parts if p)


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


@dataclass
class TokenBudget:
    used: int = 0

    def record(self, prompt: str, stdout: str, stderr: str) -> None:
        tokens = estimate_tokens(prompt, stdout, stderr)
        if tokens > MAX_TOKENS_PER_TEST:
            pytest.fail(
                f"Test exceeded per-run token cap ({tokens} > {MAX_TOKENS_PER_TEST})"
            )
        self.used += tokens
        if self.used > MAX_TOKENS_SUITE:
            pytest.fail(
                f"Suite exceeded token cap ({self.used} > {MAX_TOKENS_SUITE})"
            )


@dataclass
class AiRunResult:
    returncode: int
    stdout: str
    stderr: str
    prompt: str


@dataclass
class AiRunner:
    script: Path
    base_env: dict[str, str]
    token_budget: TokenBudget
    track_tokens: bool = True

    def run(
        self,
        *args: str,
        input_text: str | None = None,
        env: dict[str, str] | None = None,
        track_tokens: bool | None = None,
    ) -> AiRunResult:
        run_env = {**os.environ, **self.base_env}
        if env:
            run_env.update(env)
        if "CLI_API_KEY" in run_env and run_env["CLI_API_KEY"] == "":
            run_env.pop("CLI_API_KEY", None)

        prompt = args[-1] if args else ""
        should_track = self.track_tokens if track_tokens is None else track_tokens

        proc = subprocess.run(
            [str(self.script), *args],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT,
            env=run_env,
        )
        result = AiRunResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            prompt=prompt,
        )
        if should_track:
            self.token_budget.record(result.prompt, result.stdout, result.stderr)
        return result


@pytest.fixture(scope="session")
def api_key() -> str | None:
    env = load_env_file(ENV_FILE)
    return env.get("CLI_API_KEY") or os.environ.get("CLI_API_KEY")


@pytest.fixture(scope="session")
def token_budget() -> TokenBudget:
    return TokenBudget()


@pytest.fixture(scope="session")
def ai_runner(token_budget: TokenBudget) -> AiRunner:
    if not AI_SCRIPT.is_file():
        pytest.fail(f"ai script not found: {AI_SCRIPT}")
    base_env = load_env_file(ENV_FILE)
    return AiRunner(script=AI_SCRIPT, base_env=base_env, token_budget=token_budget)


@pytest.fixture
def run_ai(ai_runner: AiRunner):
    return ai_runner.run
