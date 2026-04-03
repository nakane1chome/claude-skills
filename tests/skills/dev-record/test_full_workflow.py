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

- Create `state_machine.py` in the current working directory with a StateMachine class
- States: English ("hello world"), Spanish ("hola mundo")
- The machine cycles through languages in order
- Create `test_state_machine.py` in the current working directory with pytest tests verifying each language output
- Run pytest to verify the tests pass

Create both files in the current directory (not /tmp or any other location) and run the tests.
"""

EXTEND_PROMPT = """\
Add Japanese as a third language to the state machine:

1. Add a Japanese state that outputs "こんにちは世界" to `state_machine.py` in the current directory
2. Add a test for the Japanese output in `test_state_machine.py` in the current directory
3. Run all tests with pytest and summarize the results

Important: Do not fix any pre-existing test failures. Only add the new language and its test.
"""


async def test_full_workflow(installed_project, steps, sdk, audit, model, model_alias, request, report):
    project_dir, claude_query = installed_project

    report.configure(project_dir=project_dir, model=model, model_alias=model_alias,
                     test_file=Path(__file__))

    session_ids = []

    # ------------------------------------------------------------------
    # Phase 1a — Plan mode
    # ------------------------------------------------------------------
    plan_messages = await claude_query(
        PLAN_PROMPT,
        permission_mode="plan",
        max_turns=5,
    )
    plan_session_id = steps.require_session_id(plan_messages, phase="Plan")
    session_ids.append(plan_session_id)
    report.add(plan_session_id, sdk.metrics(plan_messages), phase="Plan")
    sdk.log_phase("Plan", plan_messages, project_dir)

    # ------------------------------------------------------------------
    # Phase 1b — Implement (fresh session, cleared context)
    # ------------------------------------------------------------------
    impl_messages = await claude_query(
        IMPLEMENT_PROMPT,
        max_turns=20,
    )
    impl_result = steps.require_session_ok(impl_messages, phase="Implement")
    impl_session_id = impl_result.session_id
    session_ids.append(impl_session_id)
    report.add(impl_session_id, sdk.metrics(impl_messages), phase="Implement")
    sdk.log_phase("Implement", impl_messages, project_dir)

    # expect_: prompt asked to create test files
    test_files = list(project_dir.glob("**/test_*.py"))
    steps.expect("test file created", len(test_files) >= 1,
                 session_id=impl_session_id, phase="Implement",
                 detail=f"found {len(test_files)} test file(s)")

    # ------------------------------------------------------------------
    # Phase 2 — External modification (break a test)
    # ------------------------------------------------------------------
    modified = False
    for test_file in test_files:
        content = test_file.read_text()
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
    report.add(extend_session_id, sdk.metrics(extend_messages), phase="Extend")
    sdk.log_phase("Extend", extend_messages, project_dir)

    # ------------------------------------------------------------------
    # Audit verification
    # ------------------------------------------------------------------
    audit.assert_common(project_dir)

    # Collect ops events across all sessions
    all_events = []
    for sid in session_ids:
        all_events.extend(audit.read_ops_events(project_dir, sid))

    # expect_: audit should capture events from all phases
    user_prompts = [e for e in all_events if e["type"] == "user_prompt"]
    steps.expect_min_count(">= 3 user_prompt events", len(user_prompts), 3,
                           phase="Audit")

    tool_calls = [e for e in all_events if e["type"] == "tool_call"]
    tool_names = {e["content"]["tool"] for e in tool_calls}
    has_write_or_edit = bool(tool_names & {"Write", "Edit"})
    steps.expect("Write or Edit in tool calls", has_write_or_edit,
                 phase="Audit",
                 detail=f"tools: {', '.join(sorted(tool_names))}")
    steps.expect("Bash in tool calls", "Bash" in tool_names,
                 phase="Audit",
                 detail=f"tools: {', '.join(sorted(tool_names))}")

    # achieve_: plan snapshots depend on model behavior
    plan_snapshots = [e for e in all_events if e["type"] == "plan_snapshot"]
    steps.achieve("plan_snapshot events", len(plan_snapshots) > 0,
                  difficulty="challenging", phase="Audit",
                  detail=f"found {len(plan_snapshots)}")

    # expect_: phase 3 should have no plan snapshots
    phase3_summary = audit.read_summary(project_dir, extend_session_id)
    steps.expect("phase 3: no plan_snapshots",
                 phase3_summary["plan_snapshots"] == 0,
                 session_id=extend_session_id, phase="Extend",
                 detail=f"got {phase3_summary['plan_snapshots']}")

    # achieve_: agent self-reporting (model-dependent behavior)
    agent_reports = [e for e in all_events if e["type"] == "agent_report"]
    ignored_failures = [
        e for e in agent_reports
        if e.get("content", {}).get("event") == "ignored_prior_failure"
    ]
    steps.achieve("agent_report: ignored_prior_failure",
                  len(ignored_failures) > 0,
                  difficulty="aspirational", phase="Audit",
                  detail=f"found {len(ignored_failures)}")

    # achieve_: session metrics (environment-dependent)
    impl_summary = audit.read_summary(project_dir, impl_session_id)
    has_tokens = impl_summary.get("token_usage") is not None
    steps.achieve("token_usage present", has_tokens,
                  difficulty="expected",
                  session_id=impl_session_id, phase="Metrics")
    if has_tokens:
        steps.achieve("input_tokens > 0",
                      impl_summary["token_usage"].get("input_tokens", 0) > 0,
                      difficulty="expected",
                      session_id=impl_session_id, phase="Metrics",
                      detail=f'{impl_summary["token_usage"].get("input_tokens", 0):,}')
        steps.achieve("output_tokens > 0",
                      impl_summary["token_usage"].get("output_tokens", 0) > 0,
                      difficulty="expected",
                      session_id=impl_session_id, phase="Metrics",
                      detail=f'{impl_summary["token_usage"].get("output_tokens", 0):,}')
    steps.achieve("model present", impl_summary.get("model") is not None,
                  difficulty="expected",
                  session_id=impl_session_id, phase="Metrics",
                  detail=impl_summary.get("model", "?"))
    steps.achieve("estimated_cost_usd present",
                  impl_summary.get("estimated_cost_usd") is not None,
                  difficulty="expected",
                  session_id=impl_session_id, phase="Metrics",
                  detail=f'${impl_summary.get("estimated_cost_usd") or 0:.4f}')
    steps.achieve("compactions field present",
                  impl_summary.get("compactions") is not None,
                  difficulty="expected",
                  session_id=impl_session_id, phase="Metrics")
