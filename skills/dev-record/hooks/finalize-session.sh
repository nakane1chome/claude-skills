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

# ---------------------------------------------------------------------------
# Plan-vs-actual file diff detection
# ---------------------------------------------------------------------------
# If a plan snapshot exists for this session, compare the plan's file list
# against actual git changes. Emit unrecorded_deviation events for mismatches.

PLAN_DIR="${CLAUDE_PROJECT_DIR:-.}/audit/plans"
# Find the latest sequenced plan file; fall back to old naming convention
PLAN_FILE=$(find "$PLAN_DIR" -maxdepth 1 -name "*-${SESSION_ID}-plan-*.md" 2>/dev/null | sort | tail -1 || true)
if [ -z "$PLAN_FILE" ]; then
  PLAN_FILE=$(find "$PLAN_DIR" -maxdepth 1 -name "*-${SESSION_ID}.md" -print -quit 2>/dev/null || true)
fi

if [ -n "$PLAN_FILE" ] && [ -f "$PLAN_FILE" ]; then
  # Extract planned files from markdown table: | `path` | Action |
  # Matches lines like: | `src/bus/bus.hpp` | Modify |
  # Also matches lines like: | src/bus/bus.hpp | Modify |
  PLANNED_FILES=$(grep -E '^\|[^|]+\|[^|]*(Create|Modify|Update|Change|Delete|Regenerate)' "$PLAN_FILE" \
    | sed -E 's/^\|[[:space:]]*`?([^`|]+)`?[[:space:]]*\|.*/\1/' \
    | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
    | grep -v '^File$' \
    | grep -v '^\-' \
    | sort -u 2>/dev/null || true)

  if [ -n "$PLANNED_FILES" ]; then
    # Get files actually changed during session (staged + unstaged + untracked new files)
    PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
    ACTUAL_FILES=$(cd "$PROJECT_DIR" && {
      git diff --name-only HEAD 2>/dev/null
      git diff --name-only --cached 2>/dev/null
      git ls-files --others --exclude-standard 2>/dev/null
    } | sort -u 2>/dev/null || true)

    # Check for agent_report plan_deviation events already logged for this session
    EXISTING_DEVIATIONS=$(jq -s '[.[] | select(.type == "agent_report" and .content.event == "plan_deviation")] | length' "$LOG_FILE" 2>/dev/null || echo "0")

    # Planned files not touched
    while IFS= read -r planned; do
      [ -z "$planned" ] && continue
      # Substring match: planned path may be relative (e.g. src/bus/bus.hpp)
      if ! echo "$ACTUAL_FILES" | grep -qF "$planned"; then
        jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg file "$planned" \
          '{timestamp:$ts,session_id:$sid,type:"agent_report",
            content:{event:"unrecorded_deviation",detail:("planned file not touched: "+$file)}}' \
          >> "$LOG_FILE"
      fi
    done <<< "$PLANNED_FILES"

    # Unplanned files touched (exclude common non-source paths)
    while IFS= read -r actual; do
      [ -z "$actual" ] && continue
      # Skip audit/, .claude/, build/, and plan files themselves
      case "$actual" in
        audit/*|.claude/*|build/*|*.md) continue ;;
      esac
      # Check if any planned path is a substring of this actual path
      FOUND=false
      while IFS= read -r planned; do
        [ -z "$planned" ] && continue
        if echo "$actual" | grep -qF "$planned"; then
          FOUND=true
          break
        fi
      done <<< "$PLANNED_FILES"
      if [ "$FOUND" = false ]; then
        jq -cn --arg ts "$TIMESTAMP" --arg sid "$SESSION_ID" --arg file "$actual" \
          '{timestamp:$ts,session_id:$sid,type:"agent_report",
            content:{event:"unrecorded_deviation",detail:("unplanned file touched: "+$file)}}' \
          >> "$LOG_FILE"
      fi
    done <<< "$ACTUAL_FILES"
  fi
fi

# Re-read agent reports after plan-diff events may have been appended
AGENT_REPORTS=$(jq -s '[.[] | select(.type == "agent_report") | .content]' "$LOG_FILE")

# Update summary with final agent reports
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
