#!/bin/bash
# Hook: PostToolUse
# Records tool outcomes. Detects plan mode exits for plan snapshots.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_RESPONSE=$(echo "$INPUT" | jq '.tool_response // {}')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
CONTENT=$(echo "$TOOL_RESPONSE" | jq -r '.content // ""')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/ops_record"
mkdir -p "$LOG_DIR"

# Find existing log file for this session, or create one with timestamp prefix
LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

# Record the tool result
SUCCESS=$(echo "$TOOL_RESPONSE" | jq -r 'if .success == false then "false" else "true" end')

jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg tool "$TOOL_NAME" --arg ok "$SUCCESS" \
  '{timestamp: $ts, session_id: $sid, type: "tool_result", content: {tool: $tool, success: ($ok == "true")}}' \
  >> "$LOG_FILE"

# --- Anomaly detections ---

# hallucinated_path: Bash output contains ENOENT ("No such file or directory")
if [ "$TOOL_NAME" = "Bash" ]; then
  if echo "$CONTENT" | grep -qF "No such file or directory"; then
    jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" \
      '{timestamp:$ts,session_id:$sid,type:"agent_report",
        content:{event:"hallucinated_path",detail:"Bash output contained ENOENT — agent may have referenced a non-existent path"}}' \
      >> "$LOG_FILE"
  fi
fi

# repeated_failure: same Bash command denied twice in a row.
# Note: success=false means the user *denied* the tool, not that the command
# exited non-zero. This detects repeated permission denials, not exec failures.
if [ "$TOOL_NAME" = "Bash" ]; then
  LAST_CMD_FILE="$LOG_DIR/.last_cmd_${SESSION_ID}"
  LAST_OK_FILE="$LOG_DIR/.last_ok_${SESSION_ID}"
  if [ -f "$LAST_CMD_FILE" ] && [ "$(cat "$LAST_CMD_FILE")" = "$COMMAND" ] \
     && [ "$(cat "$LAST_OK_FILE")" = "false" ] && [ "$SUCCESS" = "false" ]; then
    jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg cmd "$COMMAND" \
      '{timestamp:$ts,session_id:$sid,type:"agent_report",
        content:{event:"repeated_failure",detail:("agent retried a denied command: "+$cmd)}}' \
      >> "$LOG_FILE"
  fi
  printf '%s' "$COMMAND" > "$LAST_CMD_FILE"
  printf '%s' "$SUCCESS" > "$LAST_OK_FILE"
fi

# regression_unlabelled: Bash denied after a Write/Edit (agent wrote code then
# a test/run command was denied — possible regression introduced without label).
# Note: same caveat as repeated_failure — success=false is a permission denial.
EDIT_FLAG="$LOG_DIR/.edited_${SESSION_ID}"
if [ "$TOOL_NAME" = "Bash" ] && [ -f "$EDIT_FLAG" ]; then
  rm -f "$EDIT_FLAG"
  if [ "$SUCCESS" = "false" ]; then
    jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" \
      '{timestamp:$ts,session_id:$sid,type:"agent_report",
        content:{event:"regression_unlabelled",detail:"Bash denied after Write/Edit — possible unlabelled regression"}}' \
      >> "$LOG_FILE"
  fi
fi
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
  touch "$EDIT_FLAG"
fi

exit 0
