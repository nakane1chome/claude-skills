#!/bin/bash
set -e

# Docker sandbox launcher for Claude Code (YOLO mode).
# Resolves repo path dynamically so this script is portable across checkouts.

REPO_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_NAME="$(basename "$REPO_PATH")"

# Claude Code names session dirs after the cwd at launch: /home/a/b -> -home-a-b
SESSION_DIR_NAME="$(printf '%s' "$REPO_PATH" | tr / -)"
SESSION_DIR="$HOME/.claude/projects/$SESSION_DIR_NAME"

COMPOSE_ARGS=()
EXTRA_ARGS=()
DO_BUILD=false
DO_FRESH=false
DO_CONTINUE=false
RESUME_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)   DO_BUILD=true; shift ;;
        --fresh)   DO_FRESH=true; shift ;;
        --resume)  RESUME_ID="$2"; shift 2 ;;
        -c)        DO_CONTINUE=true; shift ;;
        *)         EXTRA_ARGS+=("$1"); shift ;;
    esac
done

# Resolve -c: find most recent sandbox session in the repo's session dir
if $DO_CONTINUE; then
    if [ ! -d "$SESSION_DIR" ]; then
        echo "Error: no sessions found at $SESSION_DIR" >&2
        exit 1
    fi
    RESUME_ID=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1 | xargs -I{} basename {} .jsonl)
    if [ -z "$RESUME_ID" ]; then
        echo "Error: no sessions found in $SESSION_DIR" >&2
        exit 1
    fi
    echo "Resuming session: $RESUME_ID"
fi

if [ -n "$RESUME_ID" ]; then
    EXTRA_ARGS+=(--resume "$RESUME_ID")
fi

# Auth: Claude Code uses ~/.claude/.credentials.json (from `claude login`)
# which is bind-mounted into the container. ANTHROPIC_API_KEY is optional.
# ~/.claude.json must exist on the host or the bind-mount will fail.
touch "$HOME/.claude.json"

export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export HOST_REPO_PATH="$REPO_PATH"
export REPO_NAME

# --fresh: remove sandbox-only build/cache dirs so next run starts clean
if $DO_FRESH; then
    echo "Removing sandbox build/cache dirs..."
    find . -type d -name '.pytest_cache.sandbox' -exec rm -rf {} + 2>/dev/null || true
fi

if $DO_BUILD; then
    COMPOSE_ARGS+=(--build)
fi

exec docker compose run --rm "${COMPOSE_ARGS[@]}" claude-sandbox "${EXTRA_ARGS[@]}"
