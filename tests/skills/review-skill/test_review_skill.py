"""Test: review-skill identifies seeded issues in a deliberately flawed SKILL.md."""

import re
import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "review_skill"

REVIEW_PROMPT = """\
/review-skill flawed-skill

Complete all review stages (0 through 5) without stopping between stages.
Do NOT apply any fixes — just report findings for every stage, then provide the final summary.
When you would normally stop for developer review, instead continue immediately to the next stage.
"""


async def test_review_finds_seeded_issues(sandbox_project, claude_query, sdk):
    """Invoke review-skill on a flawed fixture and verify seeded issues are found."""
    # Copy flawed fixture into the sandbox project root (where review-skill can find it)
    dest = sandbox_project / "flawed-skill"
    shutil.copytree(FIXTURES_DIR / "flawed-skill", dest)

    messages = await claude_query(
        REVIEW_PROMPT,
        max_turns=25,
    )

    result = sdk.result(messages)
    assert result is not None, "No ResultMessage returned"
    assert not result.is_error, (
        f"Review session ended with error: {sdk.text(messages)[-500:]}"
    )

    text = sdk.text(messages).lower()
    assert len(text) > 100, (
        f"Response too short ({len(text)} chars) — review likely did not run"
    )

    sdk.log_phase("review-skill", messages, sandbox_project)

    # Each seeded issue maps to keyword checks on the full response.
    # We collect which issues were detected, then assert a minimum threshold.
    checks = {
        "name-kebab": bool(re.search(r"kebab|camel.?case|naming", text)),
        "description-vague": bool(re.search(r"vague|broad|generic|specific|trigger", text)),
        "argument-hint-missing": bool(re.search(r"argument.?hint", text)),
        "stop-after-stage": bool(re.search(r"stop.after|pause|stage.by.stage|between.stage|developer.review", text)),
        "no-stage-0": bool(re.search(r"stage.?0|understand|confirm.before|read.and.understand", text)),
        "unreferenced-file": bool(re.search(r"unreferenc|unused|not.referenc|orphan", text)),
    }

    found = [name for name, detected in checks.items() if detected]
    missed = [name for name, detected in checks.items() if not detected]

    # Require at least 4 of 6 — allows for model variation across tiers
    assert len(found) >= 4, (
        f"Expected review-skill to catch >= 4 of 6 seeded issues, "
        f"but only found {len(found)}: {found}. "
        f"Missed: {missed}. "
        f"Response length: {len(text)} chars"
    )
