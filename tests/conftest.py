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

    # Check for auth: either ANTHROPIC_API_KEY or OAuth credentials
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    has_oauth = (real_home / ".claude" / ".credentials.json").is_file()
    if not api_key and not has_oauth:
        pytest.skip("No auth: set ANTHROPIC_API_KEY or log in with `claude`")

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


@pytest.fixture(scope="session")
def sdk():
    return _SDKHelpers()
