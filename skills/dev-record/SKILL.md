---
name: dev-record
description: Record agent activity during Claude Code sessions. Captures plans, human input, agent decisions, and deviations via hooks and agent self-reporting.
disable-model-invocation: true
argument-hint: setup|status
---

# Dev Record

Run the action specified by `$ARGUMENTS` (either `setup` or `status`).

Passive recording of agent activity during Claude Code sessions. Captures what was planned, what happened, what was decided, and where the agent deviated.

> **Note**: This is a record-only skill — it stores raw data but does not compute trends or analysis. Consumers (other skills, scripts, or humans) interpret the records.

> **Auto-loaded hooks**: Running `setup` registers hooks directly in the project's `.claude/settings.json`. No `--plugin-dir` flag required — hooks fire automatically for every session in the project.

## Actions

### `setup`

Initialize the current project for dev-record.

Run `./install.sh` from this skill's directory.

The script:
1. Adds `audit/ops_record/` to `.gitignore`
2. Appends agent self-reporting guidance to `CLAUDE.md`
3. Creates `audit/ops_record/` and `audit/dev_record/` directories
4. Installs `audit/agent-report.sh` helper for agent self-reporting
5. Registers hooks in `.claude/settings.json` — hooks fire automatically from this point on, no `--plugin-dir` needed

### `status`

Report the current state of dev-record in the project.

1. Check `.gitignore` includes `audit/ops_record/`
2. Count `.json` summary files in `audit/dev_record/` — report number of recorded sessions
3. Read the most recent `.json` summary file (by filename sort) and display it

---

## Reference

### What Gets Recorded

**Primary records** (captured automatically by hooks):

| Record | Hook Event | What it captures |
|--------|------------|------------------|
| Human input | `UserPromptSubmit` | Every user prompt verbatim |
| Agent decisions | `PreToolUse` | Every tool call the agent attempts |
| Decision outcomes | `PostToolUse` | Whether each tool call succeeded or was denied |
| Plan snapshots | `PostToolUse` | Transcript path captured when agent exits plan mode |
| Session boundaries | `SessionEnd` | Session summary with raw counts |
| Hook-detected anomalies | `PreToolUse` / `PostToolUse` | `stop_ignored`, `hallucinated_path`, `repeated_failure`, `regression_unlabelled` (see Limitations below) |
| Plan-vs-actual file diff | `SessionEnd` | `unrecorded_deviation` — files in plan but not touched, or files touched but not in plan (see [Plan File Diff Detection](#plan-file-diff-detection)) |

**Secondary metrics** (derived from primary records — raw counts, not computed rates):

| Metric | Source |
|--------|--------|
| `tool_attempts` | Count of `PreToolUse` events |
| `tool_rejections` | Count of tool calls denied by the user |
| `corrections` | User prompts that immediately follow a tool rejection * |
| `user_prompts` | Total human inputs in the session |

\* `corrections` is estimated. May overcount after benign failures (e.g. a grep with no results) and undercount approach-level corrections where the developer redirects without a tool rejection.

**Agent self-reported events** (hooks cannot detect intent — the agent must self-report):

| Event | When to report |
|-------|----------------|
| `plan_stated` | Agent commits to an approach — especially when implementing from a design document or specification, where the plan emerges from reading rather than from formal plan mode |
| `plan_deviation` | Agent makes a decision that differs from the committed plan |
| `declined_difficult` | Agent declines work because it would be difficult |
| `ignored_prior_failure` | Agent discovers a prior failure and chooses not to resolve it |
| `scope_creep` | Agent performs work not requested and not part of the committed plan |
| `observation_misread_as_instruction` | Agent acted on something stated as an observation as if it were a directive |

> **Limitation**: Self-reporting is least reliable for the exact situations it's designed to capture. An agent that declines difficult work may rationalize it as "out of scope" rather than flag it. Treat self-reported events as a lower bound, not a complete record. The developer should review sessions and append additional `agent_report` entries for events the agent missed.

> **Hook detection limitations**: Hook-detected anomaly events (`stop_ignored`, `repeated_failure`, `regression_unlabelled`) use `tool_response.success = false` to indicate a failed tool call. In practice, `success = false` means the user *denied* the tool call, not that the command exited with a non-zero status. These detectors therefore identify repeated permission denials, not execution failures. Stop-word matching (`stop_ignored`) uses a fixed word list and will produce false positives for prompts that use these words in a non-imperative context (e.g. "don't worry, proceed").

### Plan File Diff Detection

When a plan snapshot exists for the session, the `SessionEnd` hook automatically compares the plan's file list against actual git changes. This catches structural deviations the agent failed to self-report.

**How it works:**

1. The `ExitPlanMode` hook (in `record-tool-call.sh`) saves the plan content to `audit/plans/`
2. At session end, `finalize-session.sh` parses the plan for a markdown file table (`| File | Action |`)
3. It runs `git diff --name-only` to get the files actually changed during the session
4. It compares the two lists and emits `unrecorded_deviation` events for:
   - **Planned files not touched** — files listed in the plan with action Create/Modify that have no corresponding git change
   - **Unplanned files touched** — files changed in git that don't appear in the plan's file table
5. These events appear in the session summary's `agent_reports` array and in the `-events.jsonl` artifact

**Limitations:**
- Only detects file-level structural deviations, not intent-based ones ("I used a different algorithm")
- Requires a plan snapshot (sessions without `ExitPlanMode` are not checked)
- File path matching is substring-based (plan may use relative paths like `src/bus/bus.hpp` while git uses full paths)
- Files in `audit/`, `.claude/`, and common non-source paths are excluded from the unplanned check

### Retention

Dev-record produces two tiers of data, split across two directories:

| Tier | Directory | Contents | Retention |
|------|-----------|----------|-----------|
| **Project artifacts** | `audit/dev_record/` | Session summaries (`.json`), extracted agent reports and plan snapshots (`-events.jsonl`) | Permanent — commit to version control |
| **Operational detail** | `audit/ops_record/` | Full event logs (`.jsonl`) — individual tool calls, tool results, user prompts | Gitignored — subject to retention policy |

Project artifacts are the agent equivalent of design decision records (DDRs) and task conversations in human-led projects. They capture *why* decisions were made and should live alongside project documentation.

Operational detail is equivalent to ephemeral communication (chat messages, verbal discussions). Useful for debugging and review but not first-order project records. The install action adds `audit/ops_record/` to `.gitignore`.

### Data Schema

**Event log** (operational) — one JSONL file per session at `audit/ops_record/<timestamp>-<session-id>.jsonl` (e.g. `20260216T143022Z-abc123.jsonl`). The `YYYYMMDDTHHMMSSZ` prefix ensures chronological sorting.

```json
{"timestamp": "ISO8601", "session_id": "str", "type": "user_prompt", "content": {"prompt": "..."}}
{"timestamp": "ISO8601", "session_id": "str", "type": "tool_call", "content": {"tool": "Edit", "input": {}}}
{"timestamp": "ISO8601", "session_id": "str", "type": "tool_result", "content": {"tool": "Edit", "success": true}}
{"timestamp": "ISO8601", "session_id": "str", "type": "plan_snapshot", "content": {"transcript_path": "..."}}
{"timestamp": "ISO8601", "session_id": "str", "type": "agent_report", "content": {"event": "plan_stated", "detail": "..."}}
{"timestamp": "ISO8601", "session_id": "str", "type": "agent_report", "content": {"event": "plan_deviation", "detail": "..."}}
```

**Session summary** (project artifact) — written at session end to `audit/dev_record/<timestamp>-<session-id>.json`.

**Extracted events** (project artifact) — agent reports and plan snapshots extracted to `audit/dev_record/<timestamp>-<session-id>-events.jsonl`. Only created if the session contains agent reports or plan snapshots.

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

The install action appends the following to the project's CLAUDE.md. This instructs the agent to self-report events that hooks cannot detect. The key design principle is **log BEFORE proceeding** — anchoring the reporting requirement to the decision point rather than relying on the agent remembering to report after the fact.

```markdown
## Dev Record — Agent Self-Reporting

You MUST log self-report events using the helper script. These events are
extracted to `audit/dev_record/` at session end as permanent project artifacts.
Failure to report is itself a deviation.

**When to report — log BEFORE proceeding, not after:**

- **Plan stated**: You commit to an approach. Log BEFORE you start implementing.
- **Plan deviation**: You decide to skip, change, or add a step. Log BEFORE making the change.
- **Declined as difficult**: You decline work because it would be difficult.
- **Ignored prior failure**: You discover a prior failure and choose not to resolve it.
- **Scope creep**: You perform work not requested and not part of the committed plan.
- **Observation misread as instruction**: You acted on something stated as observation as if it were a directive.

**How to report:**

​```bash
bash audit/agent-report.sh "SESSION_ID" "EVENT_TYPE" "brief description"
​```

Where EVENT_TYPE is one of: `plan_stated`, `plan_deviation`, `declined_difficult`, `ignored_prior_failure`, `scope_creep`, `observation_misread_as_instruction`

**Decision-point triggers** — if you are about to do any of these, FIRST log a `plan_deviation`:
- Skip a file listed in the plan
- Create a file not listed in the plan
- Use a different approach than what the plan describes
- Change the interface or API from what was planned
```

### Hook Scripts

Scripts live in `hooks/` within this plugin directory. When loaded via `--plugin-dir`, Claude Code resolves `${CLAUDE_PLUGIN_ROOT}/hooks/` to find them — no copying into the project required.

| Script | Hook Event | Purpose |
|--------|------------|---------|
| `record-prompt.sh` | `UserPromptSubmit` | Log human input |
| `record-tool-call.sh` | `PreToolUse` | Log agent tool decisions |
| `record-tool-result.sh` | `PostToolUse` | Log outcomes, detect plan exits |
| `finalize-session.sh` | `SessionEnd` | Extract project artifacts from ops_record to dev_record; plan-vs-actual file diff detection |

All scripts require `jq`. Each script exits 0 (non-blocking) and appends to JSONL, so concurrent sessions write to separate files without conflict.

Hook paths are resolved at install time and written as absolute paths in `.claude/settings.json`. If you move the plugin directory, re-run `setup` to update the paths.

## When to Use This vs Other Tools

| Goal | Use |
|------|-----|
| Record raw session data (plans, input, decisions) | **dev-record** |
| Analyze trends and measure agent improvement | A project-specific retrospective skill consuming dev-record data |
| Review a document for quality | **review-steps**, **strong-edit** |
