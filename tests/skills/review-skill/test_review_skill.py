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
    review_skill_project, steps, sdk, model, model_alias, report, audit,
):
    """Invoke review-skill on a flawed fixture and verify seeded issues are found."""
    project_dir, query_fn = review_skill_project

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    # Multi-turn: send initial prompt, then respond with approvals
    async with query_fn.conversation(max_turns=25) as conv:
        await conv.say(REVIEW_PROMPT)

        for _ in range(MAX_FOLLOW_UPS):
            await conv.say(CONTINUE_PROMPT)

    all_messages = conv.messages
    results = [m for m in all_messages if isinstance(m, ResultMessage)]
    result = results[-1] if results else None

    # require_: session must complete
    steps.require_session_ok(all_messages, phase="Review")

    session_id = result.session_id

    # Finalize audit
    audit.finalize(project_dir, session_id)

    report.add(session_id, sdk.metrics(all_messages), phase="Review")
    sdk.log_phase("review-skill", all_messages, project_dir)

    text = sdk.text(all_messages).lower()

    # expect_: response should be substantial
    steps.expect_text_length(text, 100, session_id=session_id, phase="Review")

    # Seeded issue patterns
    issue_patterns = {
        "name-kebab": r"kebab|camel.?case|naming",
        "description-vague": r"vague|broad|generic|specific|trigger",
        "argument-hint-missing": r"argument.?hint",
        "stop-after-stage": r"stop.after|pause|stage.by.stage|between.stage|developer.review",
        "no-stage-0": r"stage.?0|understand|confirm.before|read.and.understand",
        "unreferenced-file": r"unreferenc|unused|not.referenc|orphan",
    }

    # achieve_: each individual issue is a quality indicator
    found, missed = steps.achieve_seeded_issues(
        text, issue_patterns, min_found=4,
        difficulty="challenging", session_id=session_id, phase="Verification",
    )

    # expect_: prompt asked for thorough review — threshold must be met
    steps.expect(f">= 4 of 6 seeded issues found", len(found) >= 4,
                 phase="Verification",
                 detail=f"found {len(found)}/6: {', '.join(found)}")
