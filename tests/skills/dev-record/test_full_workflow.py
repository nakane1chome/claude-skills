"""Test 2: Full workflow — multi-phase development session produces a complete audit trail."""

import re
from pathlib import Path

import pytest

PLAN_PROMPT = """\
I need you to plan a multilingual hello-world state machine in Python.

Requirements:
- A StateMachine class with states for 2 languages: English and Spanish
- Each state prints "hello world" in that language
- The machine cycles through languages in order
- Include pytest unit tests that verify each language output

Create a plan, then exit plan mode.
"""

IMPLEMENT_PROMPT = """\
Implement the multilingual hello-world state machine based on this specification:

- Create a file `state_machine.py` with a StateMachine class
- States: English ("hello world"), Spanish ("hola mundo")
- The machine cycles through languages in order
- Create `test_state_machine.py` with pytest tests verifying each language output
- Run pytest to verify the tests pass

Create the files and run the tests.
"""

EXTEND_PROMPT = """\
Add Japanese as a third language to the state machine:

1. Add a Japanese state that outputs "こんにちは世界" to `state_machine.py`
2. Add a test for the Japanese output in `test_state_machine.py`
3. Run all tests with pytest and summarize the results

Important: Do not fix any pre-existing test failures. Only add the new language and its test.
"""


async def test_full_workflow(installed_project, sdk, audit, model, model_alias, request, report):
    if "haiku" in model:
        request.node.add_marker(pytest.mark.xfail(
            reason="Haiku is too weak for reliable multi-step tool use"))

    project_dir, claude_query = installed_project

    report.configure(project_dir=project_dir, model=model, model_alias=model_alias,
                     title="Full Workflow Test Report", test_file=Path(__file__))

    session_ids = []

    # ------------------------------------------------------------------
    # Phase 1a — Plan mode
    # ------------------------------------------------------------------
    plan_messages = await claude_query(
        PLAN_PROMPT,
        permission_mode="plan",
        max_turns=5,
    )
    plan_session_id = sdk.session_id(plan_messages)
    assert plan_session_id is not None, "No session_id from plan phase"
    session_ids.append(plan_session_id)
    report.add(plan_session_id, sdk.metrics(plan_messages))

    # ------------------------------------------------------------------
    # Phase 1b — Implement (fresh session, cleared context)
    # ------------------------------------------------------------------
    impl_messages = await claude_query(
        IMPLEMENT_PROMPT,
        max_turns=20,
    )
    impl_result = sdk.result(impl_messages)
    assert impl_result is not None, "No ResultMessage from implement phase"
    assert not impl_result.is_error, (
        f"Implementation phase ended with error: {sdk.text(impl_messages)[-500:]}"
    )
    impl_session_id = impl_result.session_id
    session_ids.append(impl_session_id)
    report.add(impl_session_id, sdk.metrics(impl_messages))

    # Verify at least one test file was created
    test_files = list(project_dir.glob("**/test_*.py"))
    assert len(test_files) >= 1, "No test_*.py file created during implementation"

    # ------------------------------------------------------------------
    # Phase 2 — External modification (break a test)
    # ------------------------------------------------------------------
    modified = False
    for test_file in test_files:
        content = test_file.read_text()
        # Case-insensitive replacement of "hello world" with "WRONG STRING"
        new_content = re.sub(
            r"hello world", "WRONG STRING", content, flags=re.IGNORECASE
        )
        if new_content != content:
            test_file.write_text(new_content)
            modified = True
            break

    assert modified, (
        "Failed to modify any test file — could not find 'hello world' in test files"
    )

    # ------------------------------------------------------------------
    # Phase 3 — Extend and observe failure
    # ------------------------------------------------------------------
    extend_messages = await claude_query(
        EXTEND_PROMPT,
        max_turns=25,
    )
    extend_result = sdk.result(extend_messages)
    assert extend_result is not None, "No ResultMessage from extend phase"
    extend_session_id = extend_result.session_id
    session_ids.append(extend_session_id)
    report.add(extend_session_id, sdk.metrics(extend_messages))

    # ------------------------------------------------------------------
    # Audit verification
    # ------------------------------------------------------------------
    audit.assert_common(project_dir)

    # Collect ops events across all sessions
    all_events = []
    for sid in session_ids:
        all_events.extend(audit.read_ops_events(project_dir, sid))

    event_types = [e["type"] for e in all_events]

    # Assert user_prompt events exist (>= 3, one per phase)
    user_prompts = [e for e in all_events if e["type"] == "user_prompt"]
    assert len(user_prompts) >= 3, (
        f"Expected >= 3 user_prompt events across 3 sessions, got {len(user_prompts)}"
    )

    # Assert tool_call events include Write/Edit and Bash
    tool_calls = [e for e in all_events if e["type"] == "tool_call"]
    tool_names = {e["content"]["tool"] for e in tool_calls}
    has_write_or_edit = bool(tool_names & {"Write", "Edit"})
    assert has_write_or_edit, (
        f"Expected Write or Edit in tool calls, got tools: {tool_names}"
    )
    assert "Bash" in tool_names, (
        f"Expected Bash in tool calls (for pytest), got tools: {tool_names}"
    )

    # Soft-assert plan_snapshot: ExitPlanMode only fires when the model transitions
    # from plan to implementation within a single session. With separate query() calls
    # for plan and implement, the model stays in plan mode until the session ends.
    plan_snapshots = [e for e in all_events if e["type"] == "plan_snapshot"]
    if not plan_snapshots:
        import warnings
        warnings.warn(
            "No plan_snapshot events found. ExitPlanMode requires an in-session "
            "plan-to-implement transition (not separate query() calls).",
            stacklevel=1,
        )

    # Phase 3 summary should have plan_snapshots == 0 (no plan mode in phase 3)
    phase3_summary = audit.read_summary(project_dir, extend_session_id)
    assert phase3_summary["plan_snapshots"] == 0, (
        f"Phase 3 should have 0 plan_snapshots, got {phase3_summary['plan_snapshots']}"
    )

    # Soft-assert: check for agent_report with ignored_prior_failure
    # This depends on agent behavior, so we use a descriptive message rather than hard fail
    agent_reports = [e for e in all_events if e["type"] == "agent_report"]
    ignored_failures = [
        e for e in agent_reports
        if e.get("content", {}).get("event") == "ignored_prior_failure"
    ]
    if not ignored_failures:
        import warnings
        warnings.warn(
            "No 'ignored_prior_failure' agent_report found. "
            "This depends on agent self-reporting behavior and is not a hard failure. "
            f"Agent reports found: {[e.get('content', {}).get('event') for e in agent_reports]}",
            stacklevel=1,
        )

