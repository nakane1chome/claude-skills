"""TestSteps — reusable test step functions with require/expect/achieve semantics."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from claude_agent_sdk.types import ResultMessage


class TestSteps:
    """Shared test steps with three check classes.

    * ``require_`` — aborts test on failure (infrastructure / prerequisites)
    * ``expect_``  — records PASS/FAIL but continues (prompted deliverables)
    * ``achieve_`` — records ACHIEVED/NOT ACHIEVED with difficulty weighting (quality)
    """

    def __init__(self, report, sdk, audit):
        self.report = report
        self.sdk = sdk
        self.audit = audit

    # ------------------------------------------------------------------
    # require_: aborts test on failure
    # ------------------------------------------------------------------

    def require_session_ok(self, messages, *, phase="Session"):
        """Session completed without error. Aborts on failure.

        Returns the ResultMessage.
        """
        result = self.sdk.result(messages)
        self.report.check("result exists", result is not None,
                          kind="require", phase=phase)
        assert result is not None, "No ResultMessage returned"
        self.report.check("no error", not result.is_error,
                          kind="require", session_id=result.session_id, phase=phase)
        assert not result.is_error, (
            f"Session error: {self.sdk.text(messages)[-500:]}"
        )
        return result

    def require_session_id(self, messages, *, phase="Session"):
        """Session ID exists. Aborts on failure.

        Returns the session ID string.
        """
        session_id = self.sdk.session_id(messages)
        self.report.check("session_id exists", session_id is not None,
                          kind="require", phase=phase)
        assert session_id is not None, "No session_id from session"
        return session_id

    # ------------------------------------------------------------------
    # expect_: records failure but test continues
    # ------------------------------------------------------------------

    def expect(self, name, passed, *, detail=None, session_id=None, phase=None):
        """Generic expectation — PASS/FAIL, test continues."""
        self.report.check(name, passed, kind="expect", detail=detail,
                          session_id=session_id, phase=phase)
        return passed

    def expect_files_exist(self, project_dir, patterns, *,
                           session_id=None, phase="Files"):
        """Files matching at least one glob pattern should exist.

        ``patterns`` is a list of globs; passes if any pattern has matches.
        Returns the list of matched files.
        """
        project_dir = Path(project_dir)
        matches = []
        for pat in patterns:
            matches.extend(
                str(p.relative_to(project_dir))
                for p in project_dir.rglob(pat)
                if p.is_file() and ".git" not in p.parts and ".claude" not in p.parts
            )
        label = " | ".join(patterns)
        self.report.check(
            f"files exist: {label}", len(matches) > 0,
            kind="expect", session_id=session_id, phase=phase,
            detail=f"found {len(matches)}: {matches[:5]}" if matches else "none found",
        )
        return matches

    def expect_file_contains(self, project_dir, glob_pattern, regex, *,
                             flags=0, session_id=None, phase="Content"):
        """Files matching glob should contain regex pattern.

        Passes if at least one matching file contains the pattern.
        """
        project_dir = Path(project_dir)
        found = False
        for f in project_dir.rglob(glob_pattern):
            if ".git" in f.parts or ".claude" in f.parts:
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            if re.search(regex, content, flags):
                found = True
                break
        self.report.check(
            f"file contains /{regex}/ in {glob_pattern}", found,
            kind="expect", session_id=session_id, phase=phase,
        )
        return found

    def expect_text_length(self, text, min_length, *, session_id=None, phase="Content"):
        """Response text should be at least ``min_length`` characters."""
        passed = len(text) >= min_length
        self.report.check(
            f"response length >= {min_length}", passed,
            kind="expect", session_id=session_id, phase=phase,
            detail=f"{len(text)} chars",
        )
        return passed

    def expect_min_count(self, name, actual, minimum, *,
                         session_id=None, phase=None):
        """A count should be at least ``minimum``."""
        passed = actual >= minimum
        self.report.check(
            name, passed, kind="expect", session_id=session_id, phase=phase,
            detail=f"got {actual}, need >= {minimum}",
        )
        return passed

    # ------------------------------------------------------------------
    # achieve_: quality indicators with difficulty weighting
    # ------------------------------------------------------------------

    def achieve(self, name, passed, *, difficulty="expected", detail=None,
                session_id=None, phase=None):
        """Generic achievement check. Does not fail the test."""
        self.report.check(name, passed, kind="achieve", difficulty=difficulty,
                          detail=detail, session_id=session_id, phase=phase)
        return passed

    def achieve_files_exist(self, project_dir, patterns, *,
                            difficulty="expected", session_id=None, phase="Files"):
        """Quality check: files matching patterns exist."""
        project_dir = Path(project_dir)
        matches = []
        for pat in patterns:
            matches.extend(
                str(p.relative_to(project_dir))
                for p in project_dir.rglob(pat)
                if p.is_file() and ".git" not in p.parts and ".claude" not in p.parts
            )
        label = " | ".join(patterns)
        self.report.check(
            f"files exist: {label}", len(matches) > 0,
            kind="achieve", difficulty=difficulty,
            session_id=session_id, phase=phase,
            detail=f"found {len(matches)}" if matches else "none found",
        )
        return matches

    def achieve_file_contains(self, project_dir, glob_pattern, regex, *,
                              difficulty="challenging", flags=0,
                              session_id=None, phase="Content"):
        """Quality check: files matching glob contain regex."""
        project_dir = Path(project_dir)
        found = False
        for f in project_dir.rglob(glob_pattern):
            if ".git" in f.parts or ".claude" in f.parts:
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            if re.search(regex, content, flags):
                found = True
                break
        self.report.check(
            f"file contains /{regex}/ in {glob_pattern}", found,
            kind="achieve", difficulty=difficulty,
            session_id=session_id, phase=phase,
        )
        return found

    def achieve_files_absent(self, project_dir, patterns, *,
                             difficulty="expected", session_id=None, phase="Files"):
        """Quality check: no files match patterns."""
        project_dir = Path(project_dir)
        found = []
        for pat in patterns:
            found.extend(
                str(p.relative_to(project_dir))
                for p in project_dir.rglob(pat)
                if p.is_file() and ".git" not in p.parts and ".claude" not in p.parts
            )
        label = " | ".join(patterns)
        passed = len(found) == 0
        self.report.check(
            f"no files: {label}", passed,
            kind="achieve", difficulty=difficulty,
            session_id=session_id, phase=phase,
            detail="absent as expected" if passed else f"found: {found[:5]}",
        )
        return passed

    def achieve_seeded_issues(self, text, issue_patterns, min_found, *,
                              difficulty="challenging", session_id=None,
                              phase="Verification"):
        """Check which seeded issues (regex dict) were found in text.

        Records each issue as a separate achieve check, plus a threshold check.
        Returns (found_names, missed_names).
        """
        found = []
        missed = []
        for name, pattern in issue_patterns.items():
            detected = bool(re.search(pattern, text, re.IGNORECASE))
            self.report.check(
                f"seeded issue: {name}", detected,
                kind="achieve", difficulty=difficulty,
                session_id=session_id, phase=phase,
            )
            (found if detected else missed).append(name)
        return found, missed


@pytest.fixture
def steps(report, sdk, audit):
    """Shared test steps with require/expect/achieve semantics."""
    return TestSteps(report, sdk, audit)
