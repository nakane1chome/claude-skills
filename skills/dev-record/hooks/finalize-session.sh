#!/bin/bash
# Hook: SessionEnd
# Reads the session event log from ops_record and writes project artifacts
# (session summary + agent reports) to dev_record.

set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

OPS_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/ops_record"
DEV_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/dev_record"

# Find the JSONL log file for this session
LOG_FILE=$(find "$OPS_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)

# Nothing to summarize if no events were recorded
if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
  exit 0
fi

mkdir -p "$DEV_DIR"

# Derive filenames from the JSONL filename (same timestamp prefix)
BASENAME=$(basename "$LOG_FILE" .jsonl)
SUMMARY_FILE="$DEV_DIR/${BASENAME}.json"

# Count events by type
TOOL_ATTEMPTS=$(jq -s '[.[] | select(.type == "tool_call")] | length' "$LOG_FILE")
TOOL_REJECTIONS=$(jq -s '[.[] | select(.type == "tool_result" and .content.success == false)] | length' "$LOG_FILE")
USER_PROMPTS=$(jq -s '[.[] | select(.type == "user_prompt")] | length' "$LOG_FILE")
PLAN_SNAPSHOTS=$(jq -s '[.[] | select(.type == "plan_snapshot")] | length' "$LOG_FILE")
AGENT_REPORTS=$(jq -s '[.[] | select(.type == "agent_report") | .content]' "$LOG_FILE")

# Estimate corrections: count user_prompt events that appear after a tool_result
# with success=false. This is an approximation — a prompt following a rejection
# is likely a correction, but could also be an unrelated follow-up.
CORRECTIONS=$(jq -s '
  reduce range(1; length) as $i (0;
    if .[$i].type == "user_prompt" and .[$i-1].type == "tool_result" and .[$i-1].content.success == false
    then . + 1 else . end
  )
' "$LOG_FILE" 2>/dev/null || echo "0")

# Get first event timestamp as session start
STARTED=$(jq -s '.[0].timestamp // empty' "$LOG_FILE")

# Write session summary to dev_record (project artifact)
jq -n \
  --arg sid "$SESSION_ID" \
  --argjson started "${STARTED:-\"$TIMESTAMP\"}" \
  --arg ended "$TIMESTAMP" \
  --argjson attempts "$TOOL_ATTEMPTS" \
  --argjson rejections "$TOOL_REJECTIONS" \
  --argjson corrections "$CORRECTIONS" \
  --argjson prompts "$USER_PROMPTS" \
  --argjson reports "$AGENT_REPORTS" \
  --argjson snapshots "$PLAN_SNAPSHOTS" \
  '{
    session_id: $sid,
    started: $started,
    ended: $ended,
    tool_attempts: $attempts,
    tool_rejections: $rejections,
    corrections: $corrections,
    user_prompts: $prompts,
    agent_reports: $reports,
    plan_snapshots: $snapshots
  }' > "$SUMMARY_FILE"

# Extract agent_report and plan_snapshot events to dev_record (project artifacts)
jq -c 'select(.type == "agent_report" or .type == "plan_snapshot")' "$LOG_FILE" \
  > "$DEV_DIR/${BASENAME}-events.jsonl" 2>/dev/null || true

# Remove empty events file if no agent reports or plan snapshots existed
if [ ! -s "$DEV_DIR/${BASENAME}-events.jsonl" ]; then
  rm -f "$DEV_DIR/${BASENAME}-events.jsonl"
fi

exit 0
