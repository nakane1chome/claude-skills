# Agent Audit Anomaly Catalogue

A reference catalogue for the dev-record plugin. Each entry specifies an
anomaly type, how to detect it, and a minimal implementation sketch.

**Detection methods:**
- **Self-report** — agent calls `audit/agent-report.sh` when it recognises the
  situation. Requires a corresponding instruction in `CLAUDE.md`.
- **Hook** — a hook script detects the pattern mechanically from tool call
  data, without agent cooperation.
- **None** — not currently detectable by either method.

Entries marked **✓ active** are implemented in the current dev-record plugin.
All others are candidates.

---

## Self-reported anomalies

### plan_stated ✓ active

Agent commits to a specific approach before executing it.

**CLAUDE.md instruction:**
> Record the plan before executing it — especially when working from a design
> document or specification where the plan emerges from reading rather than
> from formal plan mode.

**Example trigger:**
> *"I'll fix this by changing the type map entry, then regenerate stubs and
> recompile."*

**Plugin:**
```bash
bash audit/agent-report.sh "$SESSION_ID" "plan_stated" \
  "Changing type map entry, regenerating stubs, recompiling"
```

---

### plan_deviation ✓ active

Agent takes a different approach from the one it stated.

**CLAUDE.md instruction:**
> Report when you make a decision that differs from the approach you committed
> to, including when you abandon a stated plan mid-execution.

**Example trigger:**
> *"The blanket approach caused regressions. Switching to conditional handling
> only on the affected cases."*

**Plugin:**
```bash
bash audit/agent-report.sh "$SESSION_ID" "plan_deviation" \
  "Switched from blanket approach to conditional handling on affected cases"
```

---

### declined_difficult ✓ active

Agent declines work because it would be difficult, instead of reporting it as a
blocker or asking for help.

**CLAUDE.md instruction:**
> Report when you decide not to attempt something because it is too complex,
> risky, or outside your capability — rather than framing it as out of scope.

**Example trigger:**
> *"This pattern requires changes across many files and risks cascading
> regressions. I'll skip this category for now."*

**Plugin:**
```bash
bash audit/agent-report.sh "$SESSION_ID" "declined_difficult" \
  "Skipped fix — too many cross-file dependencies"
```

---

### ignored_prior_failure ✓ active

Agent discovers a prior failure and proceeds without resolving or flagging it.

**CLAUDE.md instruction:**
> Report when you discover a prior failure — broken tests, unexpected error
> counts, or evidence of a previous session leaving things in a bad state —
> and choose not to address it before continuing.

**Example trigger:**
> *"The build has more errors than I expected from the last session. Continuing
> with the new fix anyway."*

**Plugin:**
```bash
bash audit/agent-report.sh "$SESSION_ID" "ignored_prior_failure" \
  "Build in worse state than expected from last session; continuing anyway"
```

---

### scope_creep

Agent adds work beyond the committed plan — new files, new subsystems, or
unrequested refactors — without flagging the addition.

**CLAUDE.md instruction:**
> Report when you create or significantly modify something that was not in your
> stated plan and was not explicitly requested in the current session.

**Example trigger:**
> *Agent adds new test fixtures and build infrastructure while working on a
> targeted fix — none of which were in the plan.*

**Plugin:**
```bash
bash audit/agent-report.sh "$SESSION_ID" "scope_creep" \
  "Added test infrastructure not in the plan"
```

---

### observation_misread_as_instruction

Agent implements something based on a user remark phrased as observation
("this should probably…", "wouldn't it be better if…") without seeking
clarification.

**CLAUDE.md instruction:**
> Report when you implement something in response to a user comment that used
> hedged language ("should", "could", "might") rather than an explicit
> instruction. You should seek clarification instead.

**Example trigger:**
> *User: "This probably should use a helper function."
> Agent immediately refactors without confirming.*

**Plugin:**
```bash
bash audit/agent-report.sh "$SESSION_ID" "observation_misread_as_instruction" \
  "Refactored based on 'should' comment without confirming it was an instruction"
```

---

## Hook-detected anomalies

### stop_ignored

User prompt contains an explicit stop instruction but tool calls continue in
the same session.

**Hook:** `UserPromptSubmit` sets a flag; `PreToolUse` checks it.

**Trigger condition:**
```bash
echo "$PROMPT" | grep -qiE '\bstop\b|\bdo not proceed\b|\bpause\b|\bwait\b|\bdon.t continue\b'
```

**Plugin sketch:**
```bash
# UserPromptSubmit hook
PROMPT=$(echo "$INPUT" | jq -r '.prompt')
if echo "$PROMPT" | grep -qiE '\bstop\b|\bdo not proceed\b|\bpause\b'; then
  touch "$LOG_DIR/.stop_flag_${SESSION_ID}"
fi

# PreToolUse hook addition
STOP_FLAG="$LOG_DIR/.stop_flag_${SESSION_ID}"
if [ -f "$STOP_FLAG" ]; then
  jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" \
    '{timestamp:$ts,session_id:$sid,type:"agent_report",
      content:{event:"stop_ignored",detail:"tool called after stop instruction"}}' \
    >> "$LOG_FILE"
  rm -f "$STOP_FLAG"
fi
```

---

### repeated_failure

The same shell command fails with the same exit code two or more times in
succession.

**Hook:** `PostToolUse` tracks the last Bash command and its exit code.

**Trigger condition:** Current command == previous command and both exit codes
are non-zero.

**Plugin sketch:**
```bash
# PostToolUse hook
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
if [ "$TOOL" = "Bash" ]; then
  CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
  EXIT=$(echo "$INPUT" | jq -r '.tool_response.content // ""' \
         | grep -oP 'exit.*?\K[0-9]+' | head -1)
  PREV_FILE="$LOG_DIR/.last_cmd_${SESSION_ID}"
  if [ -f "$PREV_FILE" ]; then
    PREV_CMD=$(jq -r '.cmd' "$PREV_FILE")
    PREV_EXIT=$(jq -r '.exit' "$PREV_FILE")
    if [ "$CMD" = "$PREV_CMD" ] && [ "${EXIT:-0}" != "0" ] && [ "${PREV_EXIT:-0}" != "0" ]; then
      jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg cmd "$CMD" \
        '{timestamp:$ts,session_id:$sid,type:"agent_report",
          content:{event:"repeated_failure",detail:("repeated failed command: " + $cmd)}}' \
        >> "$LOG_FILE"
    fi
  fi
  jq -cn --arg cmd "$CMD" --arg exit "${EXIT:-0}" '{cmd:$cmd,exit:$exit}' \
    > "$PREV_FILE"
fi
```

---

### regression_unlabelled

A verification step (test run, build, lint, or any check command) that was
previously passing starts failing after a `Write` or `Edit` tool call, and the
agent does not self-report a `plan_deviation` or acknowledge the regression.

Detection is based on exit code changes — a command that exited 0 before an
edit exits non-zero after it — rather than parsing the content of the output.
This makes it independent of the specific verification toolchain.

**Hook:** `PostToolUse` tracks exit codes of Bash commands and whether an edit
preceded the current command.

**Trigger condition:** Exit code for a command transitions from 0 to non-zero
across a `Write`/`Edit` boundary.

**Plugin sketch:**
```bash
# PostToolUse hook
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

# Track that a file was modified
if [[ "$TOOL" == "Write" || "$TOOL" == "Edit" ]]; then
  touch "$LOG_DIR/.edited_${SESSION_ID}"
fi

if [ "$TOOL" = "Bash" ]; then
  CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
  # Exit code from tool_response (adapt extraction to your shell output format)
  SUCCESS=$(echo "$INPUT" | jq -r '.tool_response.interrupted // false')
  EXIT_OK=$(echo "$INPUT" | jq -r 'if .tool_response.content then "0" else "1" end')
  PREV_FILE="$LOG_DIR/.cmd_exit_${SESSION_ID}"

  if [ -f "$PREV_FILE" ] && [ -f "$LOG_DIR/.edited_${SESSION_ID}" ]; then
    PREV_CMD=$(jq -r '.cmd' "$PREV_FILE")
    PREV_OK=$(jq -r '.ok' "$PREV_FILE")
    if [ "$CMD" = "$PREV_CMD" ] && [ "$PREV_OK" = "0" ] && [ "$EXIT_OK" != "0" ]; then
      jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg cmd "$CMD" \
        '{timestamp:$ts,session_id:$sid,type:"agent_report",
          content:{event:"regression_unlabelled",
                   detail:("command started failing after edit: " + $cmd)}}' \
        >> "$LOG_FILE"
    fi
    rm -f "$LOG_DIR/.edited_${SESSION_ID}"
  fi

  jq -cn --arg cmd "$CMD" --arg ok "$EXIT_OK" '{cmd:$cmd,ok:$ok}' > "$PREV_FILE"
fi
```

---

### hallucinated_path

A Bash tool call fails with `No such file or directory` for a path that does
not appear in any prior tool result in the session — suggesting the agent
constructed the path from inference rather than reading it from the filesystem.

**Hook:** `PostToolUse` on Bash; matches ENOENT in output.

**Trigger condition:**
```bash
echo "$OUTPUT" | grep -qF 'No such file or directory'
```

**Plugin sketch:**
```bash
# PostToolUse hook
OUTPUT=$(echo "$INPUT" | jq -r '.tool_response.content // ""')
if echo "$OUTPUT" | grep -qF 'No such file or directory'; then
  FAILED_PATH=$(echo "$OUTPUT" | grep -oP "(?<=open\('|cannot access ')[^']+" | head -1)
  jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" \
     --arg detail "path not found: ${FAILED_PATH:-unknown}" \
    '{timestamp:$ts,session_id:$sid,type:"agent_report",
      content:{event:"hallucinated_path",detail:$detail}}' \
    >> "$LOG_FILE"
fi
```

---

## Not currently detectable

### potential_overclaim

Agent declares success ("fixed", "all tests pass", "done") when the build still
has errors or tests are still failing.

**Why undetectable:** Requires reading the agent's natural language response and
correlating it with tool output from a different turn. No hook fires on
assistant text output.

**Mitigation:** Self-report instruction — *"If you report a fix as complete,
include the error count or test result that confirms it."* This makes
overclaiming visible in the session record even if it cannot be flagged
automatically.

---

### hedging_loop

Agent produces multiple consecutive reasoning turns without issuing any tool
calls, circling the same question without advancing.

**Why undetectable:** Hooks only fire on tool calls. Assistant-only turns
produce no hook events and are invisible to the ops log.

**Mitigation:** None currently. Could be addressed if Claude Code exposed an
`AssistantTurn` hook event.

---

## Adding entries

When a new anomaly type is observed in a project:

1. Add an entry here with anomaly name, detection method, trigger condition,
   and plugin sketch (even if incomplete).
2. If self-reportable, add the corresponding instruction to the project's
   `CLAUDE.md` Dev Record section.
3. If a hook implementation is complete, move it to `audit/hooks/` and
   register it in `.claude/settings.json`.
4. Note the source project and session log in the entry for traceability.
