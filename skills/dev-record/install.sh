#!/bin/bash
# Install dev-record hooks into the current project.
# Run from the project root, or set CLAUDE_PROJECT_DIR.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dev-record into $PROJECT_DIR"

# Prerequisites
if ! command -v jq &>/dev/null; then
  echo "Error: jq is required but not installed." >&2
  exit 1
fi

# Step 1 — Copy hook scripts
HOOK_DIR="$PROJECT_DIR/.claude/hooks/dev-record"
mkdir -p "$HOOK_DIR"
cp "$SKILL_DIR/hooks/record-prompt.sh" "$HOOK_DIR/"
cp "$SKILL_DIR/hooks/record-tool-call.sh" "$HOOK_DIR/"
cp "$SKILL_DIR/hooks/record-tool-result.sh" "$HOOK_DIR/"
cp "$SKILL_DIR/hooks/finalize-session.sh" "$HOOK_DIR/"
chmod +x "$HOOK_DIR"/*.sh
echo "  Copied 4 hook scripts to $HOOK_DIR"

# Step 2 — Configure hooks in settings
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"
HOOKS_CONFIG='{
  "UserPromptSubmit": [
    {"matcher": "", "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/record-prompt.sh\""}]}
  ],
  "PreToolUse": [
    {"matcher": ".*", "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/record-tool-call.sh\""}]}
  ],
  "PostToolUse": [
    {"matcher": ".*", "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/record-tool-result.sh\""}]}
  ],
  "SessionEnd": [
    {"matcher": "", "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/dev-record/finalize-session.sh\""}]}
  ]
}'

if [ -f "$SETTINGS_FILE" ]; then
  # Merge hooks into existing settings — append to each event's array
  EXISTING=$(cat "$SETTINGS_FILE")
  echo "$EXISTING" | jq --argjson new_hooks "$HOOKS_CONFIG" '
    .hooks = (
      (.hooks // {}) as $existing |
      $new_hooks | to_entries | reduce .[] as $entry ($existing;
        .[$entry.key] = ((.[$entry.key] // []) + $entry.value)
      )
    )
  ' > "$SETTINGS_FILE"
else
  mkdir -p "$(dirname "$SETTINGS_FILE")"
  jq -n --argjson hooks "$HOOKS_CONFIG" '{hooks: $hooks}' > "$SETTINGS_FILE"
fi
echo "  Updated $SETTINGS_FILE"

# Step 3 — Add audit/ops_record/ to .gitignore
GITIGNORE="$PROJECT_DIR/.gitignore"
if [ -f "$GITIGNORE" ]; then
  if ! grep -qF 'audit/ops_record/' "$GITIGNORE"; then
    echo 'audit/ops_record/' >> "$GITIGNORE"
    echo "  Added audit/ops_record/ to .gitignore"
  else
    echo "  audit/ops_record/ already in .gitignore"
  fi
else
  echo 'audit/ops_record/' > "$GITIGNORE"
  echo "  Created .gitignore with audit/ops_record/"
fi

# Step 4 — Add self-reporting guidance to CLAUDE.md
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD" ] && grep -qF 'Dev Record' "$CLAUDE_MD"; then
  echo "  CLAUDE.md already contains Dev Record section — skipped"
else
  cat >> "$CLAUDE_MD" << 'SNIPPET'

## Dev Record — Agent Self-Reporting

You MUST append a JSONL line to the current session's event log when any of
the following occur. The log file is in `audit/ops_record/` and matches the
pattern `*-<session-id>.jsonl`. These events are extracted to `audit/dev_record/`
at session end as permanent project artifacts. Failure to report is itself a deviation.

- **Plan stated**: You commit to an approach — especially when implementing from a design document or spec. Record the plan before executing it.
- **Plan deviation**: You make a decision that differs from the committed plan.
- **Declined as difficult**: You decline work because it would be difficult.
- **Ignored prior failure**: You discover a prior failure and choose not to resolve it.

Format (one JSON object per line — shown pretty-printed for readability):
{"timestamp":"ISO8601","session_id":"SESSION_ID","type":"agent_report","content":{"event":"plan_stated|plan_deviation|declined_difficult|ignored_prior_failure","detail":"brief description"}}
SNIPPET
  echo "  Appended Dev Record section to $CLAUDE_MD"
fi

# Create output directories
mkdir -p "$PROJECT_DIR/audit/ops_record"
mkdir -p "$PROJECT_DIR/audit/dev_record"

echo "Done. dev-record is installed."
