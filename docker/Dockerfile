FROM ubuntu:24.04

ARG HOST_UID=1000
ARG HOST_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
# Agent's local bin on PATH for all stages; installer creates the dir below.
ENV PATH=/home/agent/.local/bin:$PATH

# Base system packages. Claude Code's native installer has zero runtime deps,
# so there is no Node.js install here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    curl ca-certificates jq openssh-client gnupg gosu \
    && rm -rf /var/lib/apt/lists/*

# Python toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

# Core Python deps for the test framework (test_fw/pyproject.toml). These are
# installed at build time for speed; the editable install of test_fw itself
# happens in the entrypoint since /workspace is only available at runtime.
RUN pip3 install --break-system-packages \
    claude-agent-sdk \
    'click>=8.0' \
    'marko>=2.0' \
    'numpy>=1.24' \
    'pytest>=8,<9' \
    pytest-asyncio \
    pytest-html \
    'pyyaml>=6.0' \
    'rich>=13.0' \
    'scikit-learn>=1.3'

# Create agent user matching host UID/GID BEFORE installing Claude Code so
# the install path (~agent/.local/bin) is owned by agent and auto-update works.
RUN if getent passwd ${HOST_UID} >/dev/null 2>&1; then \
        EXISTING=$(getent passwd ${HOST_UID} | cut -d: -f1); \
        usermod -l agent -d /home/agent -m "$EXISTING"; \
    else \
        groupadd -g ${HOST_GID} agent 2>/dev/null || true; \
        useradd -m -u ${HOST_UID} -g ${HOST_GID} -s /bin/bash agent; \
    fi

# Install Claude Code native binary as the agent user. /tmp cwd avoids the
# filesystem scanning hang the installer hits when run from / in Docker.
USER agent
WORKDIR /tmp
RUN curl -fsSL https://claude.ai/install.sh | bash

# Back to root so the entrypoint can be copied and made executable.
USER root
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run entrypoint as root; it fixes volume ownership then drops to agent via gosu
WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh"]
