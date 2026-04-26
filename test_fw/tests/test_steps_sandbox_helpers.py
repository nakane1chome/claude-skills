"""Unit tests for expect_executable and expect_shell_syntax_valid on TestSteps."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field

from claude_test_fw._steps import TestSteps


@dataclass
class StubReport:
    checks: list = field(default_factory=list)

    def check(self, name, passed, **kwargs):
        self.checks.append({"name": name, "passed": passed, **kwargs})


def _make_steps():
    """TestSteps with only the report wired up — sdk/audit unused by these helpers."""
    return TestSteps(report=StubReport(), sdk=None, audit=None)


# ---------- expect_executable -------------------------------------------------

def test_expect_executable_pass(tmp_path):
    steps = _make_steps()
    p = tmp_path / "run.sh"
    p.write_text("#!/bin/bash\necho hi\n")
    os.chmod(p, p.stat().st_mode | stat.S_IXUSR)

    results = steps.expect_executable(tmp_path, ["*.sh"])

    assert len(results) == 1
    assert results[0] == ("run.sh", True)
    assert steps.report.checks[-1]["passed"] is True
    assert steps.report.checks[-1]["kind"] == "expect"


def test_expect_executable_fail_not_exec(tmp_path):
    steps = _make_steps()
    p = tmp_path / "run.sh"
    p.write_text("#!/bin/bash\necho hi\n")
    # Explicitly non-executable
    os.chmod(p, 0o644)

    results = steps.expect_executable(tmp_path, ["*.sh"])

    assert results == [("run.sh", False)]
    assert steps.report.checks[-1]["passed"] is False
    assert "not executable" in steps.report.checks[-1]["detail"]


def test_expect_executable_fail_no_match(tmp_path):
    steps = _make_steps()

    results = steps.expect_executable(tmp_path, ["*.sh"])

    assert results == []
    assert steps.report.checks[-1]["passed"] is False
    assert steps.report.checks[-1]["detail"] == "no files matched"


def test_expect_executable_skips_git_and_claude_dirs(tmp_path):
    steps = _make_steps()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hook.sh").write_text("#!/bin/bash\n")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "hook.sh").write_text("#!/bin/bash\n")
    # Visible script to avoid the no-match path
    p = tmp_path / "visible.sh"
    p.write_text("#!/bin/bash\n")
    os.chmod(p, p.stat().st_mode | stat.S_IXUSR)

    results = steps.expect_executable(tmp_path, ["*.sh"])

    assert [r for r, _ in results] == ["visible.sh"]


# ---------- expect_shell_syntax_valid -----------------------------------------

def test_expect_shell_syntax_valid_pass(tmp_path):
    steps = _make_steps()
    (tmp_path / "ok.sh").write_text("#!/bin/bash\nif [ 1 = 1 ]; then echo hi; fi\n")

    results = steps.expect_shell_syntax_valid(tmp_path, ["*.sh"])

    assert len(results) == 1
    path, rc, stderr = results[0]
    assert path == "ok.sh"
    assert rc == 0
    assert steps.report.checks[-1]["passed"] is True


def test_expect_shell_syntax_valid_fail_on_bad_script(tmp_path):
    steps = _make_steps()
    (tmp_path / "bad.sh").write_text("#!/bin/bash\nif [ ; then echo hi\n")

    results = steps.expect_shell_syntax_valid(tmp_path, ["*.sh"])

    assert len(results) == 1
    _, rc, stderr = results[0]
    assert rc != 0
    assert stderr  # bash emits a diagnostic
    assert steps.report.checks[-1]["passed"] is False


def test_expect_shell_syntax_valid_fail_no_match(tmp_path):
    steps = _make_steps()

    results = steps.expect_shell_syntax_valid(tmp_path, ["*.sh"])

    assert results == []
    assert steps.report.checks[-1]["passed"] is False
    assert steps.report.checks[-1]["detail"] == "no files matched"


def test_expect_shell_syntax_valid_many_files_all_pass(tmp_path):
    steps = _make_steps()
    (tmp_path / "a.sh").write_text("#!/bin/bash\necho a\n")
    (tmp_path / "b.sh").write_text("#!/bin/bash\necho b\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.sh").write_text("#!/bin/bash\necho c\n")

    results = steps.expect_shell_syntax_valid(tmp_path, ["*.sh"])

    assert len(results) == 3
    assert all(rc == 0 for _, rc, _ in results)
    assert steps.report.checks[-1]["passed"] is True
