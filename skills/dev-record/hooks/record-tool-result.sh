#!/bin/bash
# Hook: PostToolUse
# Records tool outcomes. Detects plan mode exits for plan snapshots.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_RESPONSE=$(echo "$INPUT" | jq '.tool_response // {}')
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/dev_record"
mkdir -p "$LOG_DIR"

# Find existing log file for this session, or create one with timestamp prefix
LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

# Record the tool result
SUCCESS=$(echo "$TOOL_RESPONSE" | jq -r 'if .success == false then "false" else "true" end')

jq -n --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tool "$TOOL_NAME" --arg ok "$SUCCESS" \
  '{timestamp: $ts, session_id: $sid, type: "tool_result", content: {tool: $tool, success: ($ok == "true")}}' \
  >> "$LOG_FILE"

# If this was a plan mode exit, record a plan snapshot
if [ "$TOOL_NAME" = "ExitPlanMode" ] && [ -n "$TRANSCRIPT_PATH" ]; then
  jq -n --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tp "$TRANSCRIPT_PATH" \
    '{timestamp: $ts, session_id: $sid, type: "plan_snapshot", content: {transcript_path: $tp}}' \
    >> "$LOG_FILE"
fi

exit 0
