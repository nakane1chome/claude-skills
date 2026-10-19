"""Sandbox project fixture — isolated git repo with all skills installed."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
async def sandbox_project(tmp_path, monkeypatch, request):
    """Create an isolated project directory with git and all skills installed."""
    real_home = Path.home()

    # Determine repo root: --repo-root option, or parent of CWD
    repo_root_opt = request.config.getoption("--repo-root", default=None)
    if repo_root_opt:
        repo_root = Path(repo_root_opt).resolve()
    else:
        repo_root = Path.cwd().parent

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
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=project, check=True, capture_output=True)

    # Run install.sh to copy all skills into the project
    install_script = repo_root / "install.sh"
    subprocess.run(
        ["bash", str(install_script)],
        input="2\na\nn\n",
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )

    yield project
