"""Unit tests for plan snapshot sequencing in dev-record.

Verifies that multiple ExitPlanMode calls within a session produce
sequenced plan files (plan-01, plan-02, …) rather than silently
discarding updates after the first.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths to the hook scripts under test
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills" / "dev-record" / "hooks"
RECORD_TOOL_CALL = SKILLS_DIR / "record-tool-call.sh"
FINALIZE_SESSION = SKILLS_DIR / "finalize-session.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(script: Path, payload: dict, project_dir: Path) -> subprocess.CompletedProcess:
    """Run a hook script with JSON payload on stdin."""
    return subprocess.run(
        ["bash", str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)},
    )


def _setup_project(tmp_path: Path, session_id: str) -> tuple[Path, Path]:
    """Create audit dirs and a pre-existing JSONL log file. Return (project_dir, log_file)."""
    ops_dir = tmp_path / "audit" / "ops_record"
    ops_dir.mkdir(parents=True)
    log_file = ops_dir / f"20260101T000000Z-{session_id}.jsonl"
    log_file.touch()
    return tmp_path, log_file


def _read_events(log_file: Path) -> list[dict]:
    """Parse the JSONL log, skipping blank lines."""
    events = []
    for line in log_file.read_text().strip().splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _exit_plan_payload(session_id: str, plan: str) -> dict:
    return {"session_id": session_id, "tool_name": "ExitPlanMode", "tool_input": {"plan": plan}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPlanSnapshotSequencing:
    """Multiple ExitPlanMode calls produce sequenced plan files."""

    SESSION = "plan-seq-001"

    def test_first_plan_creates_seq_01(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        payload = _exit_plan_payload(self.SESSION, "# Plan v1\n- Step A")
        result = _run_hook(RECORD_TOOL_CALL, payload, project)
        assert result.returncode == 0, result.stderr

        plans_dir = project / "audit" / "plans"
        plan_files = sorted(plans_dir.glob(f"*-{self.SESSION}-plan-*.md"))
        assert len(plan_files) == 1, f"Expected 1 plan file, got {[f.name for f in plan_files]}"
        assert "-plan-01.md" in plan_files[0].name
        assert plan_files[0].read_text() == "# Plan v1\n- Step A\n"

        # Check event logged with sequence=1
        events = _read_events(log_file)
        snapshots = [e for e in events if e["type"] == "plan_snapshot"]
        assert len(snapshots) == 1
        assert snapshots[0]["content"]["sequence"] == 1

    def test_second_plan_creates_seq_02(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # First plan
        r1 = _run_hook(RECORD_TOOL_CALL, _exit_plan_payload(self.SESSION, "# Plan v1"), project)
        assert r1.returncode == 0, r1.stderr

        # Second plan (updated)
        r2 = _run_hook(RECORD_TOOL_CALL, _exit_plan_payload(self.SESSION, "# Plan v2\n- Step B added"), project)
        assert r2.returncode == 0, r2.stderr

        plans_dir = project / "audit" / "plans"
        plan_files = sorted(plans_dir.glob(f"*-{self.SESSION}-plan-*.md"))
        assert len(plan_files) == 2, f"Expected 2 plan files, got {[f.name for f in plan_files]}"
        assert "-plan-01.md" in plan_files[0].name
        assert "-plan-02.md" in plan_files[1].name

        # Content of second plan
        assert "Plan v2" in plan_files[1].read_text()

        # Events
        events = _read_events(log_file)
        snapshots = [e for e in events if e["type"] == "plan_snapshot"]
        assert len(snapshots) == 2
        assert snapshots[0]["content"]["sequence"] == 1
        assert snapshots[1]["content"]["sequence"] == 2

    def test_three_plans_all_saved(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        for i in range(1, 4):
            r = _run_hook(RECORD_TOOL_CALL, _exit_plan_payload(self.SESSION, f"# Plan v{i}"), project)
            assert r.returncode == 0, r.stderr

        plans_dir = project / "audit" / "plans"
        plan_files = sorted(plans_dir.glob(f"*-{self.SESSION}-plan-*.md"))
        assert len(plan_files) == 3, f"Expected 3 plan files, got {[f.name for f in plan_files]}"

        events = _read_events(log_file)
        snapshots = [e for e in events if e["type"] == "plan_snapshot"]
        assert len(snapshots) == 3
        assert [s["content"]["sequence"] for s in snapshots] == [1, 2, 3]

    def test_empty_plan_content_skipped(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # ExitPlanMode with no plan content
        payload = {"session_id": self.SESSION, "tool_name": "ExitPlanMode", "tool_input": {}}
        r = _run_hook(RECORD_TOOL_CALL, payload, project)
        assert r.returncode == 0, r.stderr

        plans_dir = project / "audit" / "plans"
        assert not plans_dir.exists() or not list(plans_dir.glob("*.md")), \
            "No plan file should be created for empty plan content"


class TestFinalizeUsesLatestPlan:
    """finalize-session.sh picks the latest sequenced plan for diff detection."""

    SESSION = "finalize-plan-001"

    def test_finalize_finds_latest_plan(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # Create two plans via the hook
        r1 = _run_hook(RECORD_TOOL_CALL, _exit_plan_payload(self.SESSION, "# Old plan\n| File | Action |\n| `old.py` | Create |"), project)
        assert r1.returncode == 0, r1.stderr
        r2 = _run_hook(RECORD_TOOL_CALL, _exit_plan_payload(self.SESSION, "# Latest plan\n| File | Action |\n| `new.py` | Create |"), project)
        assert r2.returncode == 0, r2.stderr

        # Verify both plans exist
        plans_dir = project / "audit" / "plans"
        assert len(list(plans_dir.glob(f"*-{self.SESSION}-plan-*.md"))) == 2

        # Initialize git so finalize-session.sh can run git diff
        subprocess.run(["git", "init"], cwd=project, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=project,
                       capture_output=True, env={**os.environ, "GIT_AUTHOR_NAME": "test",
                       "GIT_AUTHOR_EMAIL": "test@test", "GIT_COMMITTER_NAME": "test",
                       "GIT_COMMITTER_EMAIL": "test@test"})

        # Run finalize
        (project / "audit" / "dev_record").mkdir(parents=True, exist_ok=True)
        finalize_payload = {"session_id": self.SESSION}
        r = _run_hook(FINALIZE_SESSION, finalize_payload, project)
        assert r.returncode == 0, f"finalize failed: {r.stderr}"

        # The finalize script should have used the latest plan (plan-02).
        # Since new.py doesn't exist, it should log "planned file not touched: new.py"
        events = _read_events(log_file)
        deviation_events = [e for e in events if e.get("type") == "agent_report"
                            and e["content"].get("event") == "unrecorded_deviation"]
        deviation_details = [e["content"]["detail"] for e in deviation_events]
        assert any("new.py" in d for d in deviation_details), \
            f"Expected deviation for new.py (from latest plan), got: {deviation_details}"
        # old.py should NOT appear since the latest plan doesn't reference it
        assert not any("old.py" in d for d in deviation_details), \
            f"old.py should not appear in deviations (only latest plan used), got: {deviation_details}"

    def test_finalize_falls_back_to_old_naming(self, tmp_path):
        """Backward compat: finds plans with the old *-SESSION_ID.md naming."""
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # Create a plan using the OLD naming convention (no -plan-NN suffix)
        plans_dir = project / "audit" / "plans"
        plans_dir.mkdir(parents=True)
        old_plan = plans_dir / f"20260101T000000Z-{self.SESSION}.md"
        old_plan.write_text("# Legacy plan\n| File | Action |\n| `legacy.py` | Create |\n")

        # Initialize git
        subprocess.run(["git", "init"], cwd=project, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=project,
                       capture_output=True, env={**os.environ, "GIT_AUTHOR_NAME": "test",
                       "GIT_AUTHOR_EMAIL": "test@test", "GIT_COMMITTER_NAME": "test",
                       "GIT_COMMITTER_EMAIL": "test@test"})

        # Run finalize
        (project / "audit" / "dev_record").mkdir(parents=True, exist_ok=True)
        r = _run_hook(FINALIZE_SESSION, {"session_id": self.SESSION}, project)
        assert r.returncode == 0, f"finalize failed: {r.stderr}"

        events = _read_events(log_file)
        deviation_events = [e for e in events if e.get("type") == "agent_report"
                            and e["content"].get("event") == "unrecorded_deviation"]
        deviation_details = [e["content"]["detail"] for e in deviation_events]
        assert any("legacy.py" in d for d in deviation_details), \
            f"Expected deviation for legacy.py (old naming fallback), got: {deviation_details}"
