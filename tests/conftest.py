"""Shared test infrastructure for claude-skills E2E tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk._errors import MessageParseError
from claude_agent_sdk import _internal as _sdk_internal

# ---------------------------------------------------------------------------
# Patch SDK message parser to skip unknown message types (e.g. rate_limit_event)
# instead of crashing the generator mid-stream.
# ---------------------------------------------------------------------------

_original_parse_message = _sdk_internal.message_parser.parse_message


def _patched_parse_message(data):
    try:
        return _original_parse_message(data)
    except MessageParseError:
        # Return a SystemMessage for unknown types so iteration continues
        from claude_agent_sdk import SystemMessage
        return SystemMessage(subtype=data.get("type", "unknown"), data=data)


_sdk_internal.message_parser.parse_message = _patched_parse_message
# Also patch the import in client.py which may have already cached the reference
import claude_agent_sdk._internal.client as _client_mod
_client_mod.parse_message = _patched_parse_message


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

MODEL_MAP = {
    "weakest": "claude-haiku-4-5-20251001",
    "mid": "claude-sonnet-4-6",
    "strongest": "claude-opus-4-6",
}


def pytest_addoption(parser):
    parser.addoption(
        "--model",
        choices=list(MODEL_MAP.keys()),
        default="weakest",
        help="Model tier to use for tests (default: weakest)",
    )


@pytest.fixture(scope="session")
def model(request):
    alias = request.config.getoption("--model")
    return MODEL_MAP[alias]


@pytest.fixture(scope="session")
def model_alias(request):
    return request.config.getoption("--model")


# ---------------------------------------------------------------------------
# Repo root (for install.sh)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# sandbox_project fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def sandbox_project(tmp_path, monkeypatch):
    """Create an isolated project directory with git and all skills installed."""
    real_home = Path.home()

    # Check for auth: API key, OAuth token, or local credentials
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    has_oauth = (real_home / ".claude" / ".credentials.json").is_file()
    if not api_key and not oauth_token and not has_oauth:
        pytest.skip("No auth: set ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, or log in with `claude`")

    project = tmp_path / "project"
    project.mkdir()

    # Isolate HOME so ~/.claude/ config doesn't leak from the host
    monkeypatch.setenv("HOME", str(tmp_path))

    # Clear XDG vars to prevent config discovery
    for var in list(os.environ):
        if var.startswith("XDG_"):
            monkeypatch.delenv(var, raising=False)

    # Allow nested CLI launch (we're running inside Claude Code)
    monkeypatch.delenv("CLAUDECODE", raising=False)

    # Copy auth files into sandbox HOME so the CLI can authenticate
    if api_key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    if has_oauth:
        sandbox_claude_dir = tmp_path / ".claude"
        sandbox_claude_dir.mkdir(exist_ok=True)

        # Copy credentials
        src_creds = real_home / ".claude" / ".credentials.json"
        shutil.copy2(src_creds, sandbox_claude_dir / ".credentials.json")

        # Copy main config (contains oauthAccount needed for auth)
        src_config = real_home / ".claude.json"
        if src_config.is_file():
            shutil.copy2(src_config, tmp_path / ".claude.json")

    # git init with an empty initial commit
    subprocess.run(
        ["git", "init"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    # Run install.sh to copy all skills into the project
    # The script is interactive: option 2 = project install, "a" = all skills
    install_script = REPO_ROOT / "install.sh"
    subprocess.run(
        ["bash", str(install_script)],
        input="2\na\n",
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )

    yield project


# ---------------------------------------------------------------------------
# claude_query fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def claude_query(sandbox_project, model):
    """Return an async callable that wraps claude_agent_sdk.query() with sandbox defaults."""

    async def _query(prompt: str, **overrides) -> list:
        opts = {
            "cwd": str(sandbox_project),
            "model": model,
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "max_turns": overrides.pop("max_turns", 10),
        }
        opts.update(overrides)
        options = ClaudeAgentOptions(**opts)

        messages = []
        async for msg in query(prompt=prompt, options=options):
            messages.append(msg)
        return messages

    return _query


# ---------------------------------------------------------------------------
# sdk helper namespace
# ---------------------------------------------------------------------------


@dataclass
class _SDKHelpers:
    """Static helpers for extracting data from SDK message lists."""

    @staticmethod
    def session_id(messages: list) -> str | None:
        for msg in messages:
            if isinstance(msg, ResultMessage):
                return msg.session_id
        return None

    @staticmethod
    def result(messages: list) -> ResultMessage | None:
        for msg in messages:
            if isinstance(msg, ResultMessage):
                return msg
        return None

    @staticmethod
    def text(messages: list) -> str:
        parts = []
        for msg in messages:
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "\n".join(parts)

    @staticmethod
    def metrics(messages: list) -> dict:
        """Extract session metrics from ResultMessage for report generation."""
        for msg in messages:
            if isinstance(msg, ResultMessage):
                return {
                    "num_turns": msg.num_turns,
                    "duration_ms": msg.duration_ms,
                    "duration_api_ms": msg.duration_api_ms,
                    "total_cost_usd": msg.total_cost_usd,
                    "usage": msg.usage or {},
                }
        return {}

    def log_phase(self, phase: str, messages: list, project_dir: Path) -> None:
        """Print a compact phase summary for CI log visibility.

        Outputs session info, metrics, tool calls (from ops events if
        available), project file listing, and response tail.
        """
        result = self.result(messages)
        m = self.metrics(messages)
        usage = m.get("usage", {})
        dur = m.get("duration_ms", 0)
        turns = m.get("num_turns", 0)
        cost = m.get("total_cost_usd")

        print(f"\n{'='*60}")
        print(f"Phase: {phase}")
        print(f"  session: {result.session_id if result else '?'}")
        print(f"  turns: {turns}  duration: {dur/1000:.1f}s  cost: ${cost:.4f}" if cost else
              f"  turns: {turns}  duration: {dur/1000:.1f}s")
        print(f"  tokens: {usage.get('input_tokens', 0):,} in / {usage.get('output_tokens', 0):,} out")

        # Summarize tool calls from ops events (if audit dir exists)
        sid = result.session_id if result else None
        ops_dir = project_dir / "audit" / "ops_record"
        if sid and ops_dir.is_dir():
            ops_files = list(ops_dir.glob(f"*-{sid}.jsonl"))
            if ops_files:
                tool_calls = []
                for line in ops_files[0].read_text().strip().splitlines():
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "tool_call":
                        tool = ev["content"]["tool"]
                        inp = ev["content"].get("input", {})
                        if tool in ("Write", "Edit"):
                            detail = inp.get("file_path", "?")
                        elif tool == "Bash":
                            cmd = inp.get("command", "")
                            detail = cmd[:80] + ("..." if len(cmd) > 80 else "")
                        else:
                            detail = ""
                        tool_calls.append(f"{tool}({detail})" if detail else tool)
                if tool_calls:
                    print(f"  tools: {', '.join(tool_calls)}")

        # Show project files (excluding internals)
        exclude = {".git", ".claude", "__pycache__", ".pytest_cache", "audit"}
        files = sorted(
            str(p.relative_to(project_dir))
            for p in project_dir.rglob("*")
            if p.is_file() and not any(part in exclude for part in p.relative_to(project_dir).parts)
        )
        if files:
            print(f"  project files: {', '.join(files)}")
        else:
            print("  project files: (none)")

        # Show last 300 chars of model response
        text = self.text(messages)
        if text:
            snippet = text[-300:].strip()
            if len(text) > 300:
                snippet = "..." + snippet
            print(f"  response tail: {snippet}")
        print(f"{'='*60}")


@pytest.fixture(scope="session")
def sdk():
    return _SDKHelpers()
