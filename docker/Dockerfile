FROM ubuntu:24.04

ARG HOST_UID=1000
ARG HOST_GID=1000
ARG NODE_MAJOR=22

ENV DEBIAN_FRONTEND=noninteractive

# Base system packages (compilers, build tools, OS utilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    curl ca-certificates jq openssh-client gnupg gosu \
    && rm -rf /var/lib/apt/lists/*

# Node.js (for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

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

# Create agent user matching host UID/GID (handle pre-existing UID)
RUN if getent passwd ${HOST_UID} >/dev/null 2>&1; then \
        EXISTING=$(getent passwd ${HOST_UID} | cut -d: -f1); \
        usermod -l agent -d /home/agent -m "$EXISTING"; \
    else \
        groupadd -g ${HOST_GID} agent 2>/dev/null || true; \
        useradd -m -u ${HOST_UID} -g ${HOST_GID} -s /bin/bash agent; \
    fi

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run entrypoint as root; it fixes volume ownership then drops to agent via gosu
WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh"]
