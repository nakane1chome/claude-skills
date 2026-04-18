"""Opt-in Docker E2E: the rendered harness at the repo root actually builds.

Run locally with:  pytest -m docker tests/skills/sandbox/test_sandbox_docker.py

Skipped by default in CI via `-m "not docker"` (see .github/workflows/e2e-tests.yml).
The test does not exercise the skill; it validates that the already-rendered
four-file harness committed at the repo root produces a buildable image and a
launchable container.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(shutil.which("docker") is None,
                       reason="docker CLI not available"),
]


@pytest.fixture
def repo_root():
    """Path to the claude-skills repo root (where the rendered harness lives)."""
    # tests/skills/sandbox/test_sandbox_docker.py  ->  repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def _run(cmd, cwd, env_extra=None, check=True):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(cmd, cwd=cwd, env=env, check=check,
                          capture_output=True, text=True)


def test_compose_config_parses(repo_root):
    """`docker compose config` must parse the rendered compose YAML cleanly."""
    # HOST_REPO_PATH / REPO_NAME are normally exported by run-sandbox.sh.
    # Supply them directly so compose doesn't warn about missing env vars.
    env = {
        "HOST_REPO_PATH": str(repo_root),
        "REPO_NAME": repo_root.name,
        "HOST_UID": str(os.getuid()),
        "HOST_GID": str(os.getgid()),
    }
    proc = _run(["docker", "compose", "config"], cwd=repo_root, env_extra=env)
    assert proc.returncode == 0, proc.stderr
    assert "claude-sandbox" in proc.stdout


def test_image_builds_and_claude_cli_launches(repo_root):
    """`docker compose build` succeeds and the built image runs `claude --version`."""
    env = {
        "HOST_REPO_PATH": str(repo_root),
        "REPO_NAME": repo_root.name,
        "HOST_UID": str(os.getuid()),
        "HOST_GID": str(os.getgid()),
    }

    build = _run(["docker", "compose", "build", "claude-sandbox"],
                 cwd=repo_root, env_extra=env, check=False)
    assert build.returncode == 0, (
        f"docker compose build failed:\n{build.stdout[-2000:]}\n{build.stderr[-2000:]}"
    )

    # Smoke test: override the entrypoint so we skip the full bootstrap and just
    # confirm the Claude CLI was installed in the image.
    smoke = _run(
        ["docker", "compose", "run", "--rm", "--no-TTY",
         "--entrypoint", "claude",
         "claude-sandbox", "--version"],
        cwd=repo_root, env_extra=env, check=False,
    )
    assert smoke.returncode == 0, (
        f"claude --version failed inside container:\n{smoke.stdout}\n{smoke.stderr}"
    )
    # Claude Code prints its version to stdout; accept any non-empty output.
    assert smoke.stdout.strip(), "claude --version produced no output"
