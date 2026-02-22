#!/bin/bash
# Hook: PreToolUse
# Records every tool call the agent attempts.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq '.tool_input')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/ops_record"
mkdir -p "$LOG_DIR"

# Find existing log file for this session, or create one with timestamp prefix
LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tool "$TOOL_NAME" --argjson input "$TOOL_INPUT" \
  '{timestamp: $ts, session_id: $sid, type: "tool_call", content: {tool: $tool, input: $input}}' \
  >> "$LOG_FILE"

# If this is ExitPlanMode, save the plan content as a snapshot file and log the event.
# We capture here (PreToolUse) because PostToolUse may not fire if the session ends.
# Skip if a plan for this session already exists (model sometimes calls ExitPlanMode twice).
if [ "$TOOL_NAME" = "ExitPlanMode" ]; then
  PLAN_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/plans"
  EXISTING=$(find "$PLAN_DIR" -maxdepth 1 -name "*-${SESSION_ID}.md" -print -quit 2>/dev/null || true)
  if [ -z "$EXISTING" ]; then
    PLAN_CONTENT=$(echo "$TOOL_INPUT" | jq -r '.plan // empty')
    if [ -n "$PLAN_CONTENT" ]; then
      mkdir -p "$PLAN_DIR"
      PLAN_FILE="$PLAN_DIR/${TIMESTAMP}-${SESSION_ID}.md"
      echo "$PLAN_CONTENT" > "$PLAN_FILE"
      jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg pf "$PLAN_FILE" \
        '{timestamp: $ts, session_id: $sid, type: "plan_snapshot", content: {plan_file: $pf}}' \
        >> "$LOG_FILE"
    fi
  fi
fi

exit 0
