"""Unit tests for hook-based anomaly detection in dev-record.

Tests invoke hook scripts directly via subprocess — no LLM calls required.
Each test creates an isolated tmp_path with the audit/ops_record/ directory
structure that the hooks expect.
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
RECORD_PROMPT = SKILLS_DIR / "record-prompt.sh"
RECORD_TOOL_CALL = SKILLS_DIR / "record-tool-call.sh"
RECORD_TOOL_RESULT = SKILLS_DIR / "record-tool-result.sh"


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


def _prompt_payload(session_id: str, prompt: str) -> dict:
    return {"session_id": session_id, "prompt": prompt}


def _tool_call_payload(session_id: str, tool_name: str, tool_input: dict | None = None) -> dict:
    return {"session_id": session_id, "tool_name": tool_name, "tool_input": tool_input or {}}


def _tool_result_payload(
    session_id: str,
    tool_name: str,
    success: bool = True,
    content: str = "",
    command: str = "",
) -> dict:
    return {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_response": {"success": success, "content": content},
        "tool_input": {"command": command},
    }


# ---------------------------------------------------------------------------
# TestStopIgnored
# ---------------------------------------------------------------------------


class TestStopIgnored:
    """Stop-word in prompt → flag; tool call after flag → stop_ignored event."""

    SESSION = "stop-test-001"

    def test_stop_word_sets_flag(self, tmp_path):
        project, _ = _setup_project(tmp_path, self.SESSION)
        result = _run_hook(RECORD_PROMPT, _prompt_payload(self.SESSION, "Wait, don't do that yet"), project)
        assert result.returncode == 0, result.stderr
        flag = project / "audit" / "ops_record" / f".stop_flag_{self.SESSION}"
        assert flag.exists(), "Flag file should be created after stop-word prompt"

    def test_tool_call_after_flag_logs_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        # Set flag manually (simulating a prior stop-word prompt)
        flag = project / "audit" / "ops_record" / f".stop_flag_{self.SESSION}"
        flag.touch()

        result = _run_hook(RECORD_TOOL_CALL, _tool_call_payload(self.SESSION, "Bash"), project)
        assert result.returncode == 0, result.stderr

        # Flag should be consumed
        assert not flag.exists(), "Flag should be removed after tool call"

        events = _read_events(log_file)
        agent_events = [e for e in events if e.get("type") == "agent_report"]
        assert any(
            e["content"]["event"] == "stop_ignored" for e in agent_events
        ), f"Expected stop_ignored event, got: {agent_events}"

    def test_normal_prompt_has_no_flag(self, tmp_path):
        project, _ = _setup_project(tmp_path, self.SESSION)
        result = _run_hook(RECORD_PROMPT, _prompt_payload(self.SESSION, "Please proceed with the implementation"), project)
        assert result.returncode == 0, result.stderr
        flag = project / "audit" / "ops_record" / f".stop_flag_{self.SESSION}"
        assert not flag.exists(), "Flag should NOT be created for a normal prompt"

    def test_tool_call_without_flag_logs_nothing_extra(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        # No flag file — ensure no stop_ignored event is logged
        result = _run_hook(RECORD_TOOL_CALL, _tool_call_payload(self.SESSION, "Read"), project)
        assert result.returncode == 0, result.stderr

        events = _read_events(log_file)
        agent_events = [e for e in events if e.get("type") == "agent_report"]
        stop_events = [e for e in agent_events if e["content"]["event"] == "stop_ignored"]
        assert not stop_events, f"Expected no stop_ignored event, got: {stop_events}"


# ---------------------------------------------------------------------------
# TestHallucinatedPath
# ---------------------------------------------------------------------------


class TestHallucinatedPath:
    """ENOENT in Bash output → hallucinated_path event."""

    SESSION = "halluc-test-001"

    def test_enoent_in_output_logs_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        payload = _tool_result_payload(
            self.SESSION, "Bash", success=True,
            content="bash: line 1: foo/bar.txt: No such file or directory"
        )
        result = _run_hook(RECORD_TOOL_RESULT, payload, project)
        assert result.returncode == 0, result.stderr

        events = _read_events(log_file)
        agent_events = [e for e in events if e.get("type") == "agent_report"]
        assert any(
            e["content"]["event"] == "hallucinated_path" for e in agent_events
        ), f"Expected hallucinated_path event, got: {agent_events}"

    def test_clean_output_does_not_log_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        payload = _tool_result_payload(
            self.SESSION, "Bash", success=True,
            content="all files found successfully"
        )
        result = _run_hook(RECORD_TOOL_RESULT, payload, project)
        assert result.returncode == 0, result.stderr

        events = _read_events(log_file)
        agent_events = [e for e in events if e.get("type") == "agent_report"]
        halluc_events = [e for e in agent_events if e["content"]["event"] == "hallucinated_path"]
        assert not halluc_events, f"Expected no hallucinated_path event, got: {halluc_events}"

    def test_non_bash_tool_does_not_log_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        # Read tool returning ENOENT-like text should not trigger detection
        payload = _tool_result_payload(
            self.SESSION, "Read", success=False,
            content="No such file or directory"
        )
        result = _run_hook(RECORD_TOOL_RESULT, payload, project)
        assert result.returncode == 0, result.stderr

        events = _read_events(log_file)
        agent_events = [e for e in events if e.get("type") == "agent_report"]
        halluc_events = [e for e in agent_events if e["content"]["event"] == "hallucinated_path"]
        assert not halluc_events, f"Non-Bash tool should not trigger hallucinated_path, got: {halluc_events}"


# ---------------------------------------------------------------------------
# TestRepeatedFailure
# ---------------------------------------------------------------------------


class TestRepeatedFailure:
    """Same Bash command denied twice in a row → repeated_failure event."""

    SESSION = "repeat-test-001"
    CMD = "pytest tests/"

    def test_same_command_denied_twice_logs_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # First denial — sets the state files
        payload1 = _tool_result_payload(self.SESSION, "Bash", success=False, command=self.CMD)
        r1 = _run_hook(RECORD_TOOL_RESULT, payload1, project)
        assert r1.returncode == 0, r1.stderr

        events_after_first = _read_events(log_file)
        repeat_events = [e for e in events_after_first if e.get("type") == "agent_report"
                         and e["content"]["event"] == "repeated_failure"]
        assert not repeat_events, "Should not log repeated_failure after first denial"

        # Second denial of the same command
        payload2 = _tool_result_payload(self.SESSION, "Bash", success=False, command=self.CMD)
        r2 = _run_hook(RECORD_TOOL_RESULT, payload2, project)
        assert r2.returncode == 0, r2.stderr

        events = _read_events(log_file)
        repeat_events = [e for e in events if e.get("type") == "agent_report"
                         and e["content"]["event"] == "repeated_failure"]
        assert repeat_events, f"Expected repeated_failure event after second denial, got: {events}"

    def test_denied_once_logs_nothing(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)
        payload = _tool_result_payload(self.SESSION, "Bash", success=False, command=self.CMD)
        r = _run_hook(RECORD_TOOL_RESULT, payload, project)
        assert r.returncode == 0, r.stderr

        events = _read_events(log_file)
        repeat_events = [e for e in events if e.get("type") == "agent_report"
                         and e["content"]["event"] == "repeated_failure"]
        assert not repeat_events, f"Should not log repeated_failure after one denial: {events}"

    def test_different_commands_no_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        r1 = _run_hook(RECORD_TOOL_RESULT, _tool_result_payload(self.SESSION, "Bash", success=False, command="cmd_a"), project)
        assert r1.returncode == 0, r1.stderr

        r2 = _run_hook(RECORD_TOOL_RESULT, _tool_result_payload(self.SESSION, "Bash", success=False, command="cmd_b"), project)
        assert r2.returncode == 0, r2.stderr

        events = _read_events(log_file)
        repeat_events = [e for e in events if e.get("type") == "agent_report"
                         and e["content"]["event"] == "repeated_failure"]
        assert not repeat_events, f"Different commands should not trigger repeated_failure: {events}"

    def test_denied_then_allowed_no_event_on_next_denial(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # First denial
        r1 = _run_hook(RECORD_TOOL_RESULT, _tool_result_payload(self.SESSION, "Bash", success=False, command=self.CMD), project)
        assert r1.returncode == 0, r1.stderr

        # Allowed (breaks the consecutive-denial streak)
        r2 = _run_hook(RECORD_TOOL_RESULT, _tool_result_payload(self.SESSION, "Bash", success=True, command=self.CMD), project)
        assert r2.returncode == 0, r2.stderr

        # Another denial — should NOT trigger because last was allowed
        r3 = _run_hook(RECORD_TOOL_RESULT, _tool_result_payload(self.SESSION, "Bash", success=False, command=self.CMD), project)
        assert r3.returncode == 0, r3.stderr

        events = _read_events(log_file)
        repeat_events = [e for e in events if e.get("type") == "agent_report"
                         and e["content"]["event"] == "repeated_failure"]
        assert not repeat_events, f"Allowed call should reset denial streak: {events}"


# ---------------------------------------------------------------------------
# TestRegressionUnlabelled
# ---------------------------------------------------------------------------


class TestRegressionUnlabelled:
    """Bash denied after Write/Edit → regression_unlabelled event."""

    SESSION = "regr-test-001"

    def _write_result(self, session_id: str) -> dict:
        return _tool_result_payload(session_id, "Write", success=True)

    def _edit_result(self, session_id: str) -> dict:
        return _tool_result_payload(session_id, "Edit", success=True)

    def _bash_denied(self, session_id: str) -> dict:
        return _tool_result_payload(session_id, "Bash", success=False, command="pytest")

    def test_bash_denied_after_write_logs_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        r1 = _run_hook(RECORD_TOOL_RESULT, self._write_result(self.SESSION), project)
        assert r1.returncode == 0, r1.stderr

        r2 = _run_hook(RECORD_TOOL_RESULT, self._bash_denied(self.SESSION), project)
        assert r2.returncode == 0, r2.stderr

        events = _read_events(log_file)
        regr_events = [e for e in events if e.get("type") == "agent_report"
                       and e["content"]["event"] == "regression_unlabelled"]
        assert regr_events, f"Expected regression_unlabelled after Write→Bash-denied, got: {events}"

    def test_bash_denied_after_edit_logs_event(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        r1 = _run_hook(RECORD_TOOL_RESULT, self._edit_result(self.SESSION), project)
        assert r1.returncode == 0, r1.stderr

        r2 = _run_hook(RECORD_TOOL_RESULT, self._bash_denied(self.SESSION), project)
        assert r2.returncode == 0, r2.stderr

        events = _read_events(log_file)
        regr_events = [e for e in events if e.get("type") == "agent_report"
                       and e["content"]["event"] == "regression_unlabelled"]
        assert regr_events, f"Expected regression_unlabelled after Edit→Bash-denied, got: {events}"

    def test_edit_flag_cleared_after_any_bash(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        # Write sets flag
        r1 = _run_hook(RECORD_TOOL_RESULT, self._write_result(self.SESSION), project)
        assert r1.returncode == 0, r1.stderr

        edit_flag = project / "audit" / "ops_record" / f".edited_{self.SESSION}"
        assert edit_flag.exists(), "Edit flag should be set after Write"

        # Allowed Bash clears flag (no regression event since success=True)
        bash_allowed = _tool_result_payload(self.SESSION, "Bash", success=True, command="echo ok")
        r2 = _run_hook(RECORD_TOOL_RESULT, bash_allowed, project)
        assert r2.returncode == 0, r2.stderr

        assert not edit_flag.exists(), "Edit flag should be cleared after any Bash call"

        # Another denied Bash — flag is gone, no regression event
        r3 = _run_hook(RECORD_TOOL_RESULT, self._bash_denied(self.SESSION), project)
        assert r3.returncode == 0, r3.stderr

        events = _read_events(log_file)
        regr_events = [e for e in events if e.get("type") == "agent_report"
                       and e["content"]["event"] == "regression_unlabelled"]
        assert not regr_events, f"Second denied Bash without prior edit should not trigger: {events}"

    def test_bash_denied_without_prior_edit_logs_nothing(self, tmp_path):
        project, log_file = _setup_project(tmp_path, self.SESSION)

        r = _run_hook(RECORD_TOOL_RESULT, self._bash_denied(self.SESSION), project)
        assert r.returncode == 0, r.stderr

        events = _read_events(log_file)
        regr_events = [e for e in events if e.get("type") == "agent_report"
                       and e["content"]["event"] == "regression_unlabelled"]
        assert not regr_events, f"Denied Bash without prior edit should not trigger: {events}"
