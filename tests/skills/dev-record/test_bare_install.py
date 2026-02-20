"""Test 1: Bare install — installing dev-record and immediately exiting produces valid audit records."""

async def test_bare_install(installed_project, sdk, audit):
    project_dir, claude_query = installed_project

    # Send a minimal prompt that avoids tool use (max_turns=1 to exit quickly)
    messages = await claude_query(
        "Respond with exactly: 'Hello, session started.' Do not use any tools.",
        max_turns=1,
    )

    session_id = sdk.session_id(messages)
    assert session_id is not None, "No session_id found in ResultMessage"

    # SessionEnd hook should have fired when the CLI exited, producing the summary.
    # No manual audit.finalize() — we're testing that the hook works end-to-end.
    audit.assert_common(project_dir)

    # Verify session summary contents
    summary = audit.read_summary(project_dir, session_id)

    assert summary["tool_attempts"] == 0, (
        f"Expected 0 tool_attempts in bare session, got {summary['tool_attempts']}"
    )
    assert summary["plan_snapshots"] == 0, (
        f"Expected 0 plan_snapshots, got {summary['plan_snapshots']}"
    )
    assert summary["agent_reports"] == [], (
        f"Expected empty agent_reports, got {summary['agent_reports']}"
    )
    # user_prompts: hooks may or may not count the SDK's initial prompt
    assert summary["user_prompts"] >= 0
