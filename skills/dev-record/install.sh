#!/bin/bash
# Initialize a project for dev-record: .gitignore, CLAUDE.md, audit dirs, settings.json hooks.
# Run from the project root, or set CLAUDE_PROJECT_DIR.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

echo "Setting up dev-record in $PROJECT_DIR"

# Add audit/ops_record/ to .gitignore
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

# Add self-reporting guidance to CLAUDE.md
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD" ] && grep -qF 'Dev Record' "$CLAUDE_MD"; then
  echo "  CLAUDE.md already contains Dev Record section — skipped"
else
  cat >> "$CLAUDE_MD" << 'SNIPPET'

## Dev Record — Agent Self-Reporting

You MUST log self-report events using the helper script. These events are
extracted to `audit/dev_record/` at session end as permanent project artifacts.
Failure to report is itself a deviation.

**When to report — log BEFORE proceeding, not after:**

- **Plan stated**: You commit to an approach. Log BEFORE you start implementing.
- **Plan deviation**: You decide to skip, change, or add a step. Log BEFORE making the change.
- **Declined as difficult**: You decline work because it would be difficult.
- **Ignored prior failure**: You discover a prior failure and choose not to resolve it.
- **Scope creep**: You perform work not requested and not part of the committed plan.
- **Observation misread as instruction**: You acted on something stated as observation as if it were a directive.

**How to report:**

```bash
bash audit/agent-report.sh "SESSION_ID" "EVENT_TYPE" "brief description"
```

Where EVENT_TYPE is one of: `plan_stated`, `plan_deviation`, `declined_difficult`, `ignored_prior_failure`, `scope_creep`, `observation_misread_as_instruction`

**Decision-point triggers** — if you are about to do any of these, FIRST log a `plan_deviation`:
- Skip a file listed in the plan
- Create a file not listed in the plan
- Use a different approach than what the plan describes
- Change the interface or API from what was planned
SNIPPET
  echo "  Appended Dev Record section to $CLAUDE_MD"
fi

# Create output directories and install agent-report helper
mkdir -p "$PROJECT_DIR/audit/ops_record"
mkdir -p "$PROJECT_DIR/audit/dev_record"
cp "$SCRIPT_DIR/hooks/agent-report.sh" "$PROJECT_DIR/audit/agent-report.sh"
chmod +x "$PROJECT_DIR/audit/agent-report.sh"
echo "  Installed audit/agent-report.sh"

# Register hooks in .claude/settings.json so they fire automatically
# without requiring --plugin-dir on every invocation.
SETTINGS="$PROJECT_DIR/.claude/settings.json"
mkdir -p "$PROJECT_DIR/.claude"

if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

if grep -qF "record-prompt.sh" "$SETTINGS" 2>/dev/null; then
  echo "  Hooks already registered in .claude/settings.json — skipped"
else
  HOOKS_DIR="$SCRIPT_DIR/hooks"
  jq --arg hd "$HOOKS_DIR" '
    .hooks |= (. // {}) |
    .hooks.UserPromptSubmit |= (. // []) + [
      {"matcher": "", "hooks": [{"type": "command", "command": ("bash \"" + $hd + "/record-prompt.sh\"")}]}
    ] |
    .hooks.PreToolUse |= (. // []) + [
      {"matcher": ".*", "hooks": [{"type": "command", "command": ("bash \"" + $hd + "/record-tool-call.sh\"")}]}
    ] |
    .hooks.PostToolUse |= (. // []) + [
      {"matcher": ".*", "hooks": [{"type": "command", "command": ("bash \"" + $hd + "/record-tool-result.sh\"")}]}
    ] |
    .hooks.SessionEnd |= (. // []) + [
      {"matcher": "", "hooks": [{"type": "command", "command": ("bash \"" + $hd + "/finalize-session.sh\"")}]}
    ]
  ' "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"
  echo "  Registered hooks in .claude/settings.json (hooks dir: $HOOKS_DIR)"
fi

echo "Done. Project initialized for dev-record."
