#!/bin/bash
set -e

# HOST_REPO_PATH and REPO_NAME come from docker-compose.yml env,
# which run-sandbox.sh exports before invoking `docker compose run`.
: "${HOST_REPO_PATH:?HOST_REPO_PATH not set (expected from docker-compose env)}"
: "${REPO_NAME:?REPO_NAME not set (expected from docker-compose env)}"

AGENT_UID=$(id -u agent)
AGENT_GID=$(id -g agent)

# Ensure working directories exist
gosu agent mkdir -p audit/ops_record 2>/dev/null || true

# Create the host-path symlink at runtime (not build time) so the image stays
# generic. Claude Code names session dirs after cwd at launch; cd'ing into the
# symlinked host path keeps session IDs aligned between host and container.
mkdir -p "$(dirname "$HOST_REPO_PATH")"
if [ ! -e "$HOST_REPO_PATH" ]; then
    ln -s /workspace "$HOST_REPO_PATH"
    chown -h "$AGENT_UID:$AGENT_GID" "$HOST_REPO_PATH"
fi

# Git safe.directory for workspace (both paths resolve to the same tree)
gosu agent git config --global --add safe.directory /workspace
gosu agent git config --global --add safe.directory "$HOST_REPO_PATH"

# Set default git identity if none configured
if ! gosu agent git config --global user.name >/dev/null 2>&1; then
    gosu agent git config --global user.name "Claude Code Agent"
    gosu agent git config --global user.email "claude-agent@sandbox.local"
fi

# Python: route pytest cache to a sandbox-only dir so host and container don't
# clobber each other. Developer can override by unsetting PYTEST_ADDOPTS.
export PYTEST_ADDOPTS="-o cache_dir=.pytest_cache.sandbox ${PYTEST_ADDOPTS:-}"

# Install the in-workspace test_fw package editable on first launch, guarded
# by a sentinel file. /workspace isn't bind-mounted at image-build time so
# this can't move to the Dockerfile.
if [ -f /workspace/test_fw/pyproject.toml ] && [ ! -f /home/agent/.test_fw_installed ]; then
    gosu agent pip3 install --break-system-packages --user -e /workspace/test_fw \
        && touch /home/agent/.test_fw_installed \
        || echo "test_fw install deferred (pip failed non-fatally)"
fi

# Launch from the symlinked host path so session IDs match the host.
cd "$HOST_REPO_PATH"

exec gosu agent claude --dangerously-skip-permissions "$@"
