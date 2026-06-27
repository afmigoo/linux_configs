from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MINIMAL_PROMPT


def _assert_no_error(stderr: str) -> None:
    assert "error:" not in stderr.lower()


def _assert_has_content(stdout: str) -> None:
    assert stdout.strip(), "expected non-empty AI response on stdout"


START_THINKING = "--- start thinking ---"
END_THINKING = "--- end thinking ---"


@pytest.fixture
def require_live_env(live_env: dict[str, str | None]):
    required = ("endpoint", "model")
    missing = [k for k in required if not live_env.get(k)]
    if missing:
        pytest.skip(f"missing in environment (source your env file before running tests): {', '.join(missing)}")


class TestLiveApi:
    def test_returns_content(self, run_ai, require_live_env):
        result = run_ai(MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

    def test_verbose_prints_thinking_and_response(self, run_ai, require_live_env):
        result = run_ai("-T", "-v", MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

        assert START_THINKING in result.stdout
        assert END_THINKING in result.stdout

        pattern = re.compile(
            rf"{re.escape(START_THINKING)}\n(?P<thinking>.*?)\n{re.escape(END_THINKING)}\n(?P<response>.*)",
            re.DOTALL,
        )
        match = pattern.search(result.stdout)
        assert match, "stdout missing thinking block structure"
        assert match.group("thinking").strip(), "expected non-empty thinking output"
        assert match.group("response").strip(), "expected non-empty response after thinking"

    def test_default_no_thinking_markers(self, run_ai, require_live_env):
        result = run_ai(MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)
        assert START_THINKING not in result.stdout

    def test_stdin_context(self, run_ai, require_live_env):
        result = run_ai(
            "What is the value of foo?",
            input_text="foo=bar\n",
        )
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

    def test_input_file_context(self, run_ai, require_live_env, tmp_path: Path):
        context_file = tmp_path / "context.txt"
        context_file.write_text("color=blue\n")
        result = run_ai("-i", str(context_file), "What color is set?")
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

    def test_verbose_logs_to_stderr(self, run_ai, require_live_env):
        result = run_ai("-v", MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        assert "sending request" in result.stderr.lower()


class TestOfflineErrors:
    def test_help_exits_zero(self, ai_runner):
        result = ai_runner.run("-h", track_tokens=False)
        assert result.returncode == 0
        assert "Usage:" in result.stderr

    def test_missing_endpoint(self, ai_runner):
        result = ai_runner.run(
            MINIMAL_PROMPT,
            env={"CLI_AI_ENDPOINT": ""},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "CLI_AI_ENDPOINT" in result.stderr

    def test_missing_model(self, ai_runner):
        result = ai_runner.run(
            "-e", "http://127.0.0.1:19999",
            MINIMAL_PROMPT,
            env={"CLI_AI_MODEL": ""},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "CLI_AI_MODEL" in result.stderr

    def test_missing_input_file(self, ai_runner):
        result = ai_runner.run(
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            "-i", "/nonexistent/file/for/ai/tests",
            MINIMAL_PROMPT,
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_invalid_api_endpoint(self, ai_runner):
        result = ai_runner.run(
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            MINIMAL_PROMPT,
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "error:" in result.stderr.lower()

    def test_context_limit_exceeded(self, ai_runner):
        large_input = ("line\n" * 501).rstrip("\n")
        result = ai_runner.run(
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            MINIMAL_PROMPT,
            input_text=large_input,
            env={"CLI_AI_API_KEY": "fake-test-key"},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "exceeds" in result.stderr.lower()

    def test_exec_flag_requires_arg(self, ai_runner):
        result = ai_runner.run(
            "-x",
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "exec" in result.stderr.lower()

    def test_exec_flag_accepted(self, ai_runner):
        result = ai_runner.run(
            "-x", "echo hello",
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            MINIMAL_PROMPT,
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "error:" in result.stderr.lower()

    def test_nonexistent_model_api_error(self, ai_runner):
        result = ai_runner.run(
            "-e", "http://127.0.0.1:11434/v1",
            "-m", "nonexistent-model-xyz",
            MINIMAL_PROMPT,
            env={"CLI_AI_API_KEY": ""},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "model" in result.stderr.lower()
        assert "not found" in result.stderr.lower()

    def test_continue_latest_no_conversations(self, ai_runner, tmp_path):
        result = ai_runner.run(
            "-c",
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            MINIMAL_PROMPT,
            env={"CLI_AI_API_KEY": "", "HOME": str(tmp_path)},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "no previous conversations" in result.stderr.lower()

    def test_continue_nonexistent_hash(self, ai_runner):
        result = ai_runner.run(
            "-c", "deadbeef",
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            MINIMAL_PROMPT,
            env={"CLI_AI_API_KEY": ""},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_continue_invalid_hash(self, ai_runner):
        result = ai_runner.run(
            "-c", "notahex00",
            "-e", "http://127.0.0.1:19999",
            "-m", "dummy",
            MINIMAL_PROMPT,
            env={"CLI_AI_API_KEY": ""},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "invalid conversation hash" in result.stderr.lower()
