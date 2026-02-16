---
name: dev-record
description: Record agent activity during Claude Code sessions. Captures plans, human input, agent decisions, and deviations via hooks and agent self-reporting.
disable-model-invocation: true
argument-hint: install|status
---

# Dev Record

Run the action specified by `$ARGUMENTS` (either `install` or `status`).

Passive recording of agent activity during Claude Code sessions. Captures what happened, what was decided, and where the agent deviated from the plan.

> **Note**: This is a record-only skill — it stores raw data but does not compute trends or analysis. Consumers (other skills, scripts, or humans) interpret the records.

## Actions

### `install`

Set up passive recording in the current project. Confirm each step with the user before proceeding.

**Prerequisites:**
- Verify `jq` is installed (hooks depend on it)

**Step 1 — Copy hook scripts:**
- Locate this skill's `hooks/` directory (search for `skills/dev-record/hooks/` under the project or `~/.claude/skills/`)
- Copy the 4 scripts to `.claude/hooks/dev-record/` in the project
- Make them executable

**Step 2 — Configure hooks in settings:**
- Read `.claude/settings.json` (create if it doesn't exist)
- Merge the hook configuration below into the `hooks` key
- If a `hooks` key already exists, append to each event's array — do not overwrite existing hooks

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/record-prompt.sh\""}]
      }
    ],
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/record-tool-call.sh\""}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/record-tool-result.sh\""}]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/finalize-session.sh\""}]
      }
    ]
  }
}
```

**Step 3 — Add self-reporting guidance to CLAUDE.md:**
- Read the project's `CLAUDE.md`
- Append the snippet from the "CLAUDE.md Snippet" section below
- If a "Dev Record" section already exists, skip this step

### `status`

Report the current state of dev-record in the project.

1. Check `.claude/settings.json` for dev-record hook entries — report whether hooks are installed
2. Check `.claude/hooks/dev-record/` — report whether all 4 scripts are present
3. Count `.json` summary files in `audit/dev_record/` — report number of recorded sessions
4. Read the most recent `.json` summary file (by filename sort) and display it

---

## Reference

### What Gets Recorded

**Primary records** (captured by hooks):

| Record | Hook Event | What it captures |
|--------|------------|------------------|
| Human input | `UserPromptSubmit` | Every user prompt verbatim |
| Agent decisions | `PreToolUse` | Every tool call the agent attempts |
| Decision outcomes | `PostToolUse` | Whether each tool call succeeded or was denied |
| Plan snapshots | `PostToolUse` | Transcript path captured when agent exits plan mode |
| Session boundaries | `SessionEnd` | Session summary with raw counts |

**Secondary metrics** (derived from primary records — raw counts, not computed rates):

| Metric | Source |
|--------|--------|
| `tool_attempts` | Count of `PreToolUse` events |
| `tool_rejections` | Count of tool calls denied by the user |
| `corrections` | User prompts that immediately follow a tool rejection (estimated — may overcount after benign failures and undercount approach-level corrections) |
| `user_prompts` | Total human inputs in the session |

**Agent self-reported** (hooks cannot detect intent — the agent must self-report):

| Event | When to report |
|-------|----------------|
| `plan_stated` | Agent commits to an approach — especially when implementing from a design document or specification, where the plan emerges from reading rather than from formal plan mode |
| `plan_deviation` | Agent makes a decision that differs from the committed plan |
| `declined_difficult` | Agent declines work because it would be difficult |
| `ignored_prior_failure` | Agent discovers a prior failure and chooses not to resolve it |

> **Limitation**: Self-reporting is least reliable for the exact situations it's designed to capture. An agent that declines difficult work may rationalize it as "out of scope" rather than flag it. Treat self-reported events as a lower bound, not a complete record. The developer should review sessions and append additional `agent_report` entries for events the agent missed.

### Data Schema

**Event log** — one JSONL file per session at `audit/dev_record/<timestamp>-<session-id>.jsonl`. Filenames use a `YYYYMMDDTHHMMSSZ` prefix for chronological sorting.

```json
{"timestamp": "ISO8601", "session_id": "str", "type": "user_prompt", "content": {"prompt": "..."}}
{"timestamp": "ISO8601", "session_id": "str", "type": "tool_call", "content": {"tool": "Edit", "input": {}}}
{"timestamp": "ISO8601", "session_id": "str", "type": "tool_result", "content": {"tool": "Edit", "success": true}}
{"timestamp": "ISO8601", "session_id": "str", "type": "plan_snapshot", "content": {"transcript_path": "..."}}
{"timestamp": "ISO8601", "session_id": "str", "type": "agent_report", "content": {"event": "plan_stated", "detail": "..."}}
{"timestamp": "ISO8601", "session_id": "str", "type": "agent_report", "content": {"event": "plan_deviation", "detail": "..."}}
```

**Session summary** — written at session end to `audit/dev_record/<timestamp>-<session-id>.json` (same prefix as the JSONL).

```json
{
  "session_id": "string",
  "started": "ISO8601",
  "ended": "ISO8601",
  "tool_attempts": 0,
  "tool_rejections": 0,
  "corrections": 0,
  "user_prompts": 0,
  "agent_reports": [],
  "plan_snapshots": 0
}
```

### CLAUDE.md Snippet

The install action appends the following to the project's CLAUDE.md. This instructs the agent to self-report events that hooks cannot detect.

```markdown
## Dev Record — Agent Self-Reporting

You MUST append a JSONL line to the session's event log in `audit/dev_record/`
when any of the following occur. Failure to report is itself a deviation.

- **Plan stated**: You commit to an approach — especially when implementing from a design document or spec. Record the plan before executing it.
- **Plan deviation**: You make a decision that differs from the committed plan.
- **Declined as difficult**: You decline work because it would be difficult.
- **Ignored prior failure**: You discover a prior failure and choose not to resolve it.

Format (one JSON object per line):
{
  "timestamp": "ISO8601",
  "session_id": "SESSION_ID",
  "type": "agent_report",
  "content": {
    "event": "plan_stated|plan_deviation|declined_difficult|ignored_prior_failure",
    "detail": "brief description"
  }
}
```

### Hook Scripts

Source scripts are in the `hooks/` directory within this skill.

| Script | Hook Event | Purpose |
|--------|------------|---------|
| `record-prompt.sh` | `UserPromptSubmit` | Log human input |
| `record-tool-call.sh` | `PreToolUse` | Log agent tool decisions |
| `record-tool-result.sh` | `PostToolUse` | Log outcomes, detect plan exits |
| `finalize-session.sh` | `SessionEnd` | Compute session summary from event log |

All scripts require `jq`. Each script exits 0 (non-blocking) and appends to JSONL, so concurrent sessions write to separate files without conflict.

### When to Use This vs Other Tools

| Goal | Use |
|------|-----|
| Record raw session data (plans, input, decisions) | **dev-record** |
| Analyze trends and measure agent improvement | A project-specific retrospective skill consuming dev-record data |
| Review a document for quality | **review-steps**, **strong-edit** |
