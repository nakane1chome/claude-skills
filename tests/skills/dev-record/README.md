# dev-record Skill Tests

The [dev-record](../../../skills/dev-record/SKILL.md) skill captures session statistics (tool calls, user prompts, plan snapshots, agent self-reported events) and saves them as JSONL/JSON to `audit/dev_record/` and `audit/ops_record/`.

This folder contains pytest end-to-end tests for the skill. This README serves as both the test plan and developer documentation. It should move to a separate document once tests cover more skills.

## Prerequisites

- `ANTHROPIC_API_KEY` set in the environment (tests make real API calls)
- `jq` installed (required by the skill's install script)
- Python dependencies declared in [`tests/pyproject.toml`](../../pyproject.toml):

```
cd tests/
pip install .
```

## Test Infrastructure

### Sandbox Fixtures (`conftest.py`)

Tests use `claude-agent-sdk` to interact with Claude Code programmatically. Sandbox isolation is achieved with pytest's `tmp_path` and `monkeypatch` fixtures.

#### `sandbox_project`

Creates an isolated project directory with no configuration leakage from the host:

- Sets `HOME` to `tmp_path` via `monkeypatch.setenv`
- Clears all `XDG_*` environment variables to prevent config discovery
- Passes `ANTHROPIC_API_KEY` through from the real environment
- Uses `setting_sources=None` in the SDK to skip loading `~/.claude/` config
- Runs `install.sh` to copy the skill files and hook scripts into the sandbox project

#### `claude_query`

Thin helper that wraps `claude_agent_sdk.query()` with sandbox defaults:

| Raw note helper | SDK equivalent |
|-----------------|----------------|
| Create a sandbox project | `tmp_path` + `monkeypatch` + `install.sh` (the `sandbox_project` fixture) |
| Launch claude with model | `query(prompt, options=ClaudeAgentOptions(cwd=..., model=...))` |
| Run claude command | `query(prompt="/command", ...)` |
| Inject claude prompt | `query(prompt="...", ...)` or `--resume` for multi-turn |
| Capture claude output | Async iteration over `query()` messages |
| Inspect files in sandbox | `pathlib.Path` operations on `tmp_path` |
| Add/delete/modify files | `pathlib.Path` operations on `tmp_path` |

### Model Selection

Model aliases are defined as a pytest fixture in `conftest.py` and can be selected via `--model` or parametrized:

| Alias | Purpose |
|-------|---------|
| `weakest` | Cheapest model; fast feedback on fixture/harness issues |
| `mid` | Balance of cost and capability |
| `strongest` | Full capability; use for tests that require planning or complex tool use |

Tests that require planning or multi-step reasoning should use `strongest`. Tests that only verify install mechanics can use `weakest`.

## Test Patterns

### Common Setup 1

Reusable setup sequence for tests that need a fully installed dev-record skill:

1. Create sandbox project (`sandbox_project` fixture — includes running `install.sh`)
2. `git init` the repository
3. Launch Claude via `query()`
4. Run `/dev-record install` to configure hooks and create audit directories

After this setup, the project has:
- `.claude/hooks/dev-record/` with all four hook scripts
- `.claude/settings.json` with hook registrations
- `audit/dev_record/` and `audit/ops_record/` directories
- `CLAUDE.md` with agent self-reporting guidance

### Common Check 1

Reusable assertions to run after any test that exercises the skill:

1. Verify `audit/dev_record/` directory exists
2. Verify `audit/ops_record/` directory exists
3. Verify at least one session summary (`.json`) exists in `audit/dev_record/`
4. Verify at least one event log (`.jsonl`) exists in `audit/ops_record/`

## Test Cases

### Test 1: Bare Install

Verifies that installing and immediately exiting produces valid (empty) audit records.

**Setup**: Common Setup 1

**Test body**:
- Exit claude (end the session immediately after install)

**Expected results**:
- Common Check 1 passes
- Session summary in `audit/dev_record/` contains:
  - `tool_attempts`: 0 (no tool use beyond the install session)
  - `user_prompts`: 0
  - `plan_snapshots`: 0
  - `agent_reports`: empty array
- Event log in `audit/ops_record/` is empty or contains only the session boundary

### Test 2: Full Workflow

Verifies that a multi-phase development session produces a complete audit trail, including agent self-reported events.

**Setup**: Common Setup 1

**Phase 1 — Plan and implement**:
1. Enter plan mode
2. Ask Claude to create a plan for a multilingual hello-world state machine in Python with 2 languages (English and one of Claude's choice), with unit tests for each language
3. Exit plan mode and execute the plan with cleared context
4. Assert that Claude runs the tests and they pass
5. Exit the session

**Phase 2 — External modification**:
1. Outside of Claude, modify the unit test to change the expected `"hello world"` string (introducing a failing test)

**Phase 3 — Extend and observe failure handling**:
1. Launch a new Claude session (using `--resume` or a fresh `query()`)
2. Ask Claude to add a third language and run the tests
3. Ask Claude for a summary of the test results
4. Exit the session

**Expected audit output**:

Common Check 1 passes. Additionally:

| Event type | Expected in ops_record log |
|------------|---------------------------|
| `user_prompt` | Multiple entries across both sessions |
| `tool_call` | `Write`, `Bash` (for creating files and running tests) |
| `tool_result` | Mix of `success: true` and `success: false` (failing tests) |
| `plan_snapshot` | At least 1 (from exiting plan mode in Phase 1) |
| `agent_report` | `plan_stated` (Phase 1) |
| `agent_report` | `ignored_prior_failure` (Phase 3 — Claude encounters the externally broken test and proceeds) |

Session summary in `audit/dev_record/` for the Phase 3 session should show:
- `tool_rejections` > 0 (failed test runs)
- `agent_reports` array containing `ignored_prior_failure`
- `plan_snapshots`: 0 (no plan mode in Phase 3)
