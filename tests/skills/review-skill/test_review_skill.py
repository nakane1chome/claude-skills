"""Test: review-skill identifies seeded issues in a deliberately flawed SKILL.md.

Uses multi-turn conversation to respond to the skill's stop-after-each-stage
pattern with approval messages, mimicking a real developer interaction.
"""

import re
from pathlib import Path

import pytest
from claude_agent_sdk.types import ResultMessage


REVIEW_PROMPT = """\
/review-skill flawed-skill

Complete all review stages (0 through 5).
Report findings for every stage, then provide the final summary.
"""

CONTINUE_PROMPT = "Please proceed as suggested."

MAX_FOLLOW_UPS = 8


async def test_review_finds_seeded_issues(
    review_skill_project, sdk, model, model_alias, report, audit,
):
    """Invoke review-skill on a flawed fixture and verify seeded issues are found."""
    project_dir, query_fn = review_skill_project

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    # Multi-turn: send initial prompt, then respond with approvals
    # when the skill pauses for developer review between stages
    async with query_fn.conversation(max_turns=25) as conv:
        await conv.say(REVIEW_PROMPT)

        for _ in range(MAX_FOLLOW_UPS):
            await conv.say(CONTINUE_PROMPT)

    all_messages = conv.messages
    # With multi-turn, use the last ResultMessage (final session state)
    results = [m for m in all_messages if isinstance(m, ResultMessage)]
    result = results[-1] if results else None
    assert result is not None, "No ResultMessage returned"
    assert not result.is_error, (
        f"Review session ended with error: {sdk.text(all_messages)[-500:]}"
    )

    session_id = result.session_id
    report.check("no error", not result.is_error, session_id=session_id, phase="Review")

    # ClaudeSDKClient may not trigger SessionEnd hook — finalize manually
    audit.finalize(project_dir, session_id)

    report.add(session_id, sdk.metrics(all_messages), phase="Review")
    sdk.log_phase("review-skill", all_messages, project_dir)

    text = sdk.text(all_messages).lower()
    report.check("response length > 100", len(text) > 100,
                 session_id=session_id, phase="Review",
                 detail=f"{len(text)} chars")
    assert len(text) > 100, (
        f"Response too short ({len(text)} chars) — review likely did not run"
    )

    # Each seeded issue maps to keyword checks on the full response.
    # We collect which issues were detected, then assert a minimum threshold.
    issue_checks = {
        "name-kebab": bool(re.search(r"kebab|camel.?case|naming", text)),
        "description-vague": bool(re.search(r"vague|broad|generic|specific|trigger", text)),
        "argument-hint-missing": bool(re.search(r"argument.?hint", text)),
        "stop-after-stage": bool(re.search(r"stop.after|pause|stage.by.stage|between.stage|developer.review", text)),
        "no-stage-0": bool(re.search(r"stage.?0|understand|confirm.before|read.and.understand", text)),
        "unreferenced-file": bool(re.search(r"unreferenc|unused|not.referenc|orphan", text)),
    }

    found = [name for name, detected in issue_checks.items() if detected]
    missed = [name for name, detected in issue_checks.items() if not detected]

    # Record each seeded issue as a check
    for name, detected in issue_checks.items():
        report.check(f"seeded issue: {name}", detected, phase="Verification")

    report.check(f">= 4 of 6 seeded issues found", len(found) >= 4,
                 phase="Verification",
                 detail=f"found {len(found)}/6: {', '.join(found)}")

    # Require at least 4 of 6 — allows for model variation across tiers
    assert len(found) >= 4, (
        f"Expected review-skill to catch >= 4 of 6 seeded issues, "
        f"but only found {len(found)}: {found}. "
        f"Missed: {missed}. "
        f"Response length: {len(text)} chars"
    )
