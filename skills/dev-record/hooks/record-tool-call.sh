#!/bin/bash
# Hook: PreToolUse
# Records every tool call the agent attempts.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(printf '%s' "$INPUT" | jq '.tool_input')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/ops_record"
mkdir -p "$LOG_DIR"

# Find existing log file for this session, or create one with timestamp prefix
LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

# Atomic append: write to temp file, then use flock to serialize appends.
# Writes >PIPE_BUF (4096) to >> are not atomic and can interleave with
# concurrent hook invocations.
LOCK_FILE="$LOG_DIR/.lock_${SESSION_ID}"
TMP_FILE=$(mktemp "$LOG_DIR/.tmp.XXXXXX")
trap 'rm -f "$TMP_FILE"' EXIT

printf '%s' "$TOOL_INPUT" | jq -c --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tool "$TOOL_NAME" \
  '{timestamp: $ts, session_id: $sid, type: "tool_call", content: {tool: $tool, input: .}}' \
  > "$TMP_FILE"

# Stop-ignored detection: if a stop-word flag exists from the prior prompt,
# the agent proceeded with a tool call despite the user saying stop.
# Consume the flag once so it doesn't cascade across multiple tool calls.
FLAG_FILE="$LOG_DIR/.stop_flag_${SESSION_ID}"
if [ -f "$FLAG_FILE" ]; then
  rm -f "$FLAG_FILE"
  jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tool "$TOOL_NAME" \
    '{timestamp:$ts,session_id:$sid,type:"agent_report",
      content:{event:"stop_ignored",detail:("agent proceeded with tool "+$tool+" despite stop-word in prior prompt")}}' \
    >> "$TMP_FILE"
fi

# If this is ExitPlanMode, save the plan content as a snapshot file and log the event.
# We capture here (PreToolUse) because PostToolUse may not fire if the session ends.
if [ "$TOOL_NAME" = "ExitPlanMode" ]; then
  PLAN_CONTENT=$(printf '%s' "$TOOL_INPUT" | jq -r '.plan // empty')
  if [ -n "$PLAN_CONTENT" ]; then
    PLAN_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/plans"
    mkdir -p "$PLAN_DIR"
    EXISTING_COUNT=$(find "$PLAN_DIR" -maxdepth 1 -name "*-${SESSION_ID}-plan-*.md" 2>/dev/null | wc -l)
    SEQ=$(printf '%02d' $((EXISTING_COUNT + 1)))
    PLAN_FILE="$PLAN_DIR/${TIMESTAMP}-${SESSION_ID}-plan-${SEQ}.md"
    printf '%s\n' "$PLAN_CONTENT" > "$PLAN_FILE"
    jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg pf "$PLAN_FILE" --argjson seq "$((EXISTING_COUNT + 1))" \
      '{timestamp: $ts, session_id: $sid, type: "plan_snapshot", content: {plan_file: $pf, sequence: $seq}}' \
      >> "$TMP_FILE"
  fi
fi

# Serialize the append with flock to prevent interleaving
flock "$LOCK_FILE" cat "$TMP_FILE" >> "$LOG_FILE"

exit 0
