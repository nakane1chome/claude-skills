#!/bin/bash
# Hook: UserPromptSubmit
# Records every user prompt to the session event log.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
PROMPT=$(echo "$INPUT" | jq -r '.prompt')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/ops_record"
mkdir -p "$LOG_DIR"

# Find existing log file for this session, or create one with timestamp prefix
LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

jq -n --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg p "$PROMPT" \
  '{timestamp: $ts, session_id: $sid, type: "user_prompt", content: {prompt: $p}}' \
  >> "$LOG_FILE"

exit 0
