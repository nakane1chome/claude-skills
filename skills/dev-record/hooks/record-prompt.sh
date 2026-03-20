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

jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg p "$PROMPT" \
  '{timestamp: $ts, session_id: $sid, type: "user_prompt", content: {prompt: $p}}' \
  >> "$LOG_FILE"

# Stop-word detection: set flag if prompt contains a stop-word so the next
# tool call hook can detect if the agent proceeded despite the user saying stop.
STOP_WORDS=("wait" "stop" "pause" "hold on" "don't" "dont" "no," "no." "cancel")
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')
FLAG_FILE="$LOG_DIR/.stop_flag_${SESSION_ID}"
rm -f "$FLAG_FILE"                          # always clear prior flag
for word in "${STOP_WORDS[@]}"; do
  if echo "$PROMPT_LOWER" | grep -qF "$word"; then
    touch "$FLAG_FILE"; break
  fi
done

exit 0
