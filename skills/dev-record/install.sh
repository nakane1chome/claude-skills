#!/bin/bash
# Initialize a project for dev-record: .gitignore, CLAUDE.md, audit dirs.
# Hooks are registered via the plugin model (plugin.json + hooks/hooks.json),
# so this script only handles project-level setup.
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

You MUST call the self-reporting helper when any of the following occur. These
events are extracted to `audit/dev_record/` at session end as permanent project
artifacts. Failure to report is itself a deviation.

- **Plan stated**: You commit to an approach — especially when implementing from a design document or spec. Record the plan before executing it.
- **Plan deviation**: You make a decision that differs from the committed plan.
- **Declined as difficult**: You decline work because it would be difficult.
- **Ignored prior failure**: You discover a prior failure and choose not to resolve it.

Run this command, substituting the actual values:

```bash
bash audit/agent-report.sh "SESSION_ID" "plan_stated|plan_deviation|declined_difficult|ignored_prior_failure" "brief description"
```
SNIPPET
  echo "  Appended Dev Record section to $CLAUDE_MD"
fi

# Create output directories and install agent-report helper
mkdir -p "$PROJECT_DIR/audit/ops_record"
mkdir -p "$PROJECT_DIR/audit/dev_record"
cp "$SCRIPT_DIR/hooks/agent-report.sh" "$PROJECT_DIR/audit/agent-report.sh"
chmod +x "$PROJECT_DIR/audit/agent-report.sh"
echo "  Installed audit/agent-report.sh"

echo "Done. Project initialized for dev-record."
