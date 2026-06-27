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
def require_api_key(api_key: str | None):
    if not api_key:
        pytest.skip("CLI_API_KEY not in bin/.env")


class TestLiveApi:
    def test_returns_content(self, run_ai, require_api_key):
        result = run_ai(MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

    def test_verbose_prints_thinking_and_response(self, run_ai, require_api_key):
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

    def test_default_no_thinking_markers(self, run_ai, require_api_key):
        result = run_ai(MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)
        assert START_THINKING not in result.stdout

    def test_stdin_context(self, run_ai, require_api_key):
        result = run_ai(
            "What is the value of foo?",
            input_text="foo=bar\n",
        )
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

    def test_input_file_context(self, run_ai, require_api_key, tmp_path: Path):
        context_file = tmp_path / "context.txt"
        context_file.write_text("color=blue\n")
        result = run_ai("-i", str(context_file), "What color is set?")
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        _assert_has_content(result.stdout)

    def test_verbose_logs_to_stderr(self, run_ai, require_api_key):
        result = run_ai("-v", MINIMAL_PROMPT)
        assert result.returncode == 0
        _assert_no_error(result.stderr)
        assert "sending request" in result.stderr.lower()


class TestOfflineErrors:
    def test_missing_api_key(self, ai_runner):
        result = ai_runner.run(
            MINIMAL_PROMPT,
            env={"CLI_API_KEY": ""},
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "CLI_API_KEY" in result.stderr

    def test_missing_question(self, ai_runner):
        result = ai_runner.run(track_tokens=False)
        assert result.returncode != 0

    def test_missing_input_file(self, ai_runner):
        result = ai_runner.run(
            "-i",
            "/nonexistent/file/for/ai/tests",
            MINIMAL_PROMPT,
            track_tokens=False,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()
