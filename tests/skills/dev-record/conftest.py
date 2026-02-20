"""Dev-record specific fixtures: installed project and audit helpers."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# installed_project fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def installed_project(sandbox_project, claude_query):
    """Sandbox project with dev-record fully installed via install.sh (direct subprocess)."""
    project = sandbox_project

    # Run the dev-record install.sh directly (not via the agent) for reliability.
    # The agent would need to interpret the SKILL.md and run the script, which is
    # unreliable with weaker models and wastes API tokens for setup.
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

    # Verify the install produced expected artifacts
    hooks_dir = project / ".claude" / "hooks" / "dev-record"
    assert hooks_dir.is_dir(), f"hooks dir missing: {hooks_dir}"
    expected_scripts = [
        "record-prompt.sh",
        "record-tool-call.sh",
        "record-tool-result.sh",
        "finalize-session.sh",
    ]
    for script in expected_scripts:
        assert (hooks_dir / script).is_file(), f"missing hook: {script}"

    settings = project / ".claude" / "settings.json"
    assert settings.is_file(), "settings.json missing after install"

    assert (project / "audit" / "dev_record").is_dir(), "audit/dev_record/ missing"
    assert (project / "audit" / "ops_record").is_dir(), "audit/ops_record/ missing"

    yield project, claude_query


# ---------------------------------------------------------------------------
# audit helper namespace
# ---------------------------------------------------------------------------


@dataclass
class _AuditHelpers:
    """Helpers for inspecting dev-record audit output."""

    @staticmethod
    def finalize(project_dir: Path, session_id: str) -> None:
        """Manually invoke finalize-session.sh for a given session."""
        script = project_dir / ".claude" / "hooks" / "dev-record" / "finalize-session.sh"
        if not script.is_file():
            raise FileNotFoundError(f"finalize script not found: {script}")

        stdin_data = json.dumps({"session_id": session_id})
        subprocess.run(
            ["bash", str(script)],
            input=stdin_data,
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
            env={
                **dict(__import__("os").environ),
                "CLAUDE_PROJECT_DIR": str(project_dir),
            },
        )

    @staticmethod
    def assert_common(project_dir: Path) -> None:
        """Common Check 1: verify audit directories have content."""
        dev_dir = project_dir / "audit" / "dev_record"
        ops_dir = project_dir / "audit" / "ops_record"

        assert dev_dir.is_dir(), "audit/dev_record/ does not exist"
        assert ops_dir.is_dir(), "audit/ops_record/ does not exist"

        summaries = list(dev_dir.glob("*.json"))
        assert len(summaries) >= 1, (
            f"Expected at least one session summary in {dev_dir}, found {len(summaries)}"
        )

        logs = list(ops_dir.glob("*.jsonl"))
        assert len(logs) >= 1, (
            f"Expected at least one event log in {ops_dir}, found {len(logs)}"
        )

    @staticmethod
    def read_summary(project_dir: Path, session_id: str) -> dict:
        """Find and parse the session summary JSON for a given session_id."""
        dev_dir = project_dir / "audit" / "dev_record"
        matches = list(dev_dir.glob(f"*-{session_id}.json"))
        assert len(matches) == 1, (
            f"Expected exactly 1 summary for session {session_id}, "
            f"found {len(matches)}: {[m.name for m in matches]}"
        )
        return json.loads(matches[0].read_text())

    @staticmethod
    def _parse_jsonl(path: Path) -> list[dict]:
        """Parse a JSONL file, skipping malformed lines."""
        events = []
        for line in path.read_text().strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # Hook scripts may produce truncated lines for very large tool inputs
                continue
        return events

    @staticmethod
    def read_ops_events(project_dir: Path, session_id: str) -> list[dict]:
        """Parse the JSONL event log for a given session_id."""
        ops_dir = project_dir / "audit" / "ops_record"
        matches = list(ops_dir.glob(f"*-{session_id}.jsonl"))
        if not matches:
            return []
        assert len(matches) == 1, (
            f"Expected 0 or 1 ops log for session {session_id}, "
            f"found {len(matches)}: {[m.name for m in matches]}"
        )
        return _AuditHelpers._parse_jsonl(matches[0])

    @staticmethod
    def read_dev_events(project_dir: Path, session_id: str) -> list[dict]:
        """Parse extracted events JSONL for a given session_id."""
        dev_dir = project_dir / "audit" / "dev_record"
        matches = list(dev_dir.glob(f"*-{session_id}-events.jsonl"))
        if not matches:
            return []
        assert len(matches) == 1, (
            f"Expected 0 or 1 events file for session {session_id}, "
            f"found {len(matches)}: {[m.name for m in matches]}"
        )
        return _AuditHelpers._parse_jsonl(matches[0])


@pytest.fixture(scope="session")
def audit():
    return _AuditHelpers()
