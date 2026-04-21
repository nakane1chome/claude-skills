# Node.js toolchain (NodeSource 22 LTS; bundles npm)
ARG NODE_MAJOR=22
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# TypeScript projects typically install `typescript` and `ts-node` as devDeps
# via npm — no Dockerfile addition needed. If the target repo uses pnpm or
# yarn, add `npm install -g pnpm` / `yarn` below.
