#!/bin/bash
# Hook: PreToolUse
# Records every tool call the agent attempts.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq '.tool_input')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/dev_record"
mkdir -p "$LOG_DIR"

# Find existing log file for this session, or create one with timestamp prefix
LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

jq -n --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tool "$TOOL_NAME" --argjson input "$TOOL_INPUT" \
  '{timestamp: $ts, session_id: $sid, type: "tool_call", content: {tool: $tool, input: $input}}' \
  >> "$LOG_FILE"

exit 0
