"""Instrumented project fixture — sandbox with dev-record plugin injected."""

from __future__ import annotations

import os
import subprocess

import pytest


@pytest.fixture
async def instrumented_project(sandbox_project, claude_query, claude_conversation):
    """Sandbox project with dev-record plugin installed and injected.

    Yields (project_dir, query_fn) where query_fn wraps claude_query
    with the dev-record plugin automatically injected.

    query_fn also has a .conversation(**overrides) method that returns
    a multi-turn conversation context manager with the plugin injected.
    """
    project = sandbox_project

    # Run dev-record install.sh for project init (audit dirs, .gitignore)
    install_script = project / ".claude" / "skills" / "dev-record" / "install.sh"
    assert install_script.is_file(), f"install.sh not found at {install_script}"

    subprocess.run(
        ["bash", str(install_script)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        env={
            **dict(os.environ),
            "CLAUDE_PROJECT_DIR": str(project),
        },
    )

    # Verify project init artifacts
    assert (project / "audit" / "dev_record").is_dir(), "audit/dev_record/ missing"
    assert (project / "audit" / "ops_record").is_dir(), "audit/ops_record/ missing"

    # Verify plugin structure exists
    plugin_dir = project / ".claude" / "skills" / "dev-record"
    assert (plugin_dir / "plugin.json").is_file(), "plugin.json missing"
    assert (plugin_dir / "hooks" / "hooks.json").is_file(), "hooks/hooks.json missing"

    plugin_spec = [{"type": "local", "path": str(plugin_dir)}]

    # Wrap claude_query to inject plugin
    async def _query_with_plugin(prompt, **overrides):
        overrides.setdefault("plugins", plugin_spec)
        return await claude_query(prompt, **overrides)

    # Attach conversation factory for multi-turn tests
    def _conversation(**overrides):
        overrides.setdefault("plugins", plugin_spec)
        return claude_conversation(**overrides)

    _query_with_plugin.conversation = _conversation

    yield project, _query_with_plugin
