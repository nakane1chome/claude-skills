"""Test: Double install — running install.sh twice produces no duplicate hooks or CLAUDE.md sections."""

import json
import os
import subprocess
from pathlib import Path


def _run_install(install_script: Path, project: Path) -> None:
    subprocess.run(
        ["bash", str(install_script)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        env={**dict(os.environ), "CLAUDE_PROJECT_DIR": str(project)},
    )


async def test_double_install(sandbox_project, claude_query, sdk, audit):
    project = sandbox_project
    install_script = project / ".claude" / "skills" / "dev-record" / "install.sh"
    assert install_script.is_file(), f"install.sh not found at {install_script}"

    # sandbox_project already ran root install.sh which invokes dev-record's install.sh.
    # Run it twice more to confirm idempotency regardless of how many times it's called.
    _run_install(install_script, project)
    _run_install(install_script, project)

    # --- settings.json: each hook event type must have exactly one dev-record entry ---
    settings_path = project / ".claude" / "settings.json"
    assert settings_path.is_file(), ".claude/settings.json missing"
    settings = json.loads(settings_path.read_text())
    hooks = settings.get("hooks", {})

    for event_type, script_name in [
        ("UserPromptSubmit", "record-prompt.sh"),
        ("PreToolUse", "record-tool-call.sh"),
        ("PostToolUse", "record-tool-result.sh"),
        ("SessionEnd", "finalize-session.sh"),
    ]:
        entries = [
            h for h in hooks.get(event_type, [])
            if any(script_name in cmd.get("command", "") for cmd in h.get("hooks", []))
        ]
        assert len(entries) == 1, (
            f"{event_type}: expected exactly 1 dev-record hook entry, got {len(entries)}"
        )

    # --- CLAUDE.md: self-reporting section must appear exactly once ---
    claude_md_text = (project / "CLAUDE.md").read_text()
    count = claude_md_text.count("## Dev Record")
    assert count == 1, (
        f"Expected exactly 1 '## Dev Record' section in CLAUDE.md, got {count}"
    )

    # --- Hooks must still fire correctly after repeated installs ---
    messages = await claude_query(
        "Respond with exactly: 'Hello, session started.' Do not use any tools.",
        max_turns=1,
    )
    session_id = sdk.session_id(messages)
    assert session_id is not None, "No session_id found in ResultMessage"

    # SDK may not trigger SessionEnd for short sessions — finalize manually as fallback
    dev_dir = project / "audit" / "dev_record"
    if not list(dev_dir.glob("*.json")):
        audit.finalize(project, session_id)

    audit.assert_common(project)
    summary = audit.read_summary(project, session_id)
    assert summary["tool_attempts"] == 0
    assert summary["agent_reports"] == []
