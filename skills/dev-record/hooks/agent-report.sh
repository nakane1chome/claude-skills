#!/bin/bash
# Agent self-reporting helper.
# Usage: bash audit/agent-report.sh <session_id> <event_type> <detail>
#
# Called directly by the agent to log agent_report events.
# Accepts plain arguments so the agent's bash command contains no $() substitution,
# which avoids triggering the Claude Code sandbox permission prompt.

set -euo pipefail

SESSION_ID="${1:?Usage: agent-report.sh <session_id> <event_type> <detail>}"
EVENT_TYPE="${2:?event_type required (plan_stated|plan_deviation|declined_difficult|ignored_prior_failure)}"
DETAIL="${3:?detail required}"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/ops_record"
mkdir -p "$LOG_DIR"

LOG_FILE=$(find "$LOG_DIR" -maxdepth 1 -name "*-${SESSION_ID}.jsonl" -print -quit 2>/dev/null)
if [ -z "$LOG_FILE" ]; then
  FILE_TS=$(date -u +%Y%m%dT%H%M%SZ)
  LOG_FILE="$LOG_DIR/${FILE_TS}-${SESSION_ID}.jsonl"
fi

jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg evt "$EVENT_TYPE" --arg detail "$DETAIL" \
  '{timestamp: $ts, session_id: $sid, type: "agent_report", content: {event: $evt, detail: $detail}}' \
  >> "$LOG_FILE"
