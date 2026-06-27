from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AI_SCRIPT = REPO_ROOT / "bin" / "cli-ai"

MAX_TOKENS_PER_TEST = 5_000
MAX_TOKENS_SUITE = 500_000
RUN_TIMEOUT = 120

MINIMAL_PROMPT = "Reply with the single word OK"


def estimate_tokens(*parts: str) -> int:
    return sum(max(1, len(p) // 4) for p in parts if p)


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
    token_budget: TokenBudget
    track_tokens: bool = True

    def run(
        self,
        *args: str,
        input_text: str | None = None,
        env: dict[str, str] | None = None,
        track_tokens: bool | None = None,
    ) -> AiRunResult:
        run_env = {**os.environ}
        if env:
            run_env.update(env)

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
def live_env() -> dict[str, str | None]:
    return {
        "endpoint": os.environ.get("CLI_AI_ENDPOINT"),
        "model": os.environ.get("CLI_AI_MODEL"),
        "api_key": os.environ.get("CLI_AI_API_KEY"),
    }


@pytest.fixture(scope="session")
def token_budget() -> TokenBudget:
    return TokenBudget()


@pytest.fixture(scope="session")
def ai_runner(token_budget: TokenBudget) -> AiRunner:
    if not AI_SCRIPT.is_file():
        pytest.fail(f"ai script not found: {AI_SCRIPT}")
    return AiRunner(script=AI_SCRIPT, token_budget=token_budget)


@pytest.fixture
def run_ai(ai_runner: AiRunner):
    return ai_runner.run
