# Sandbox Template Placeholders

Exhaustive list of placeholders used by `skills/sandbox/templates/**`. The agent substitutes each at Stage 2 of the skill.

## Contents

- Overview — runtime-resolved vs substituted
- Substituted placeholders
- Stanza markers
- Runtime-resolved values (no placeholder needed)

## Overview

There are two kinds of "variables" in the templates:

1. **Substituted at render time** — `{{VAR}}` tokens the agent replaces with literal values before writing the file.
2. **Resolved at runtime** — values the *rendered script* computes from `$(pwd)`, env vars, or `${BASH_SOURCE[0]}` when it executes on the developer's machine.

The runtime-resolved approach is preferred for anything path-shaped (repo location, session dir name, host username). This keeps the rendered harness portable across clones, rename operations, and different hosts without re-running the skill.

## Substituted placeholders

| Placeholder | Files it appears in | Source | Example |
|---|---|---|---|
| `{{REPO_NAME}}` | none (derived at runtime via `basename $(pwd)`) | basename of target dir | `my-project` |

*Design note: after Stage 1 rewrites, `{{REPO_NAME}}` is **not** baked into the templates as a literal token — the rendered scripts compute it with `$(basename "$REPO_PATH")`. This column is kept for future stanzas that need a render-time value (e.g. container name annotations in compose labels).*

## Stanza markers

Stanzas are full blocks of code inserted into a template at a marker line. The marker line itself is consumed (removed) at render time.

| Marker | Template | Selection rule | Stanza files |
|---|---|---|---|
| `# @@STANZA:DOCKERFILE_LANG@@` | `docker/Dockerfile.tmpl` | language detection (0..3 stanzas) | `python.dockerfile`, `cmake.dockerfile`, `node.dockerfile` |
| `# @@STANZA:ENTRYPOINT_LANG@@` | `docker/entrypoint.sh.tmpl` | language detection (0..3 stanzas) | `python.entrypoint`, `cmake.entrypoint`, `node.entrypoint`, `minimal.entrypoint` |
| `# @@STANZA:SAFE_DIRS@@` | `docker/entrypoint.sh.tmpl` | one line per submodule path, or empty | inline (see detection.md) |
| `# @@STANZA:FRESH_CLEANUP@@` | `run-sandbox.sh.tmpl` | matches build-dir isolation choice | `python.fresh`, `cmake.fresh`, `node.fresh`, `minimal.fresh` |

### Stanza rules

- When multiple stanzas apply, concatenate them in the order **cmake → node → python** and separate with a blank line. Reasoning: compilers first so later stages can link native bindings; Node before Python so `pip` lands last (pip wheels sometimes shell out to `npm`-managed tooling during build).
- If no stanza applies to a marker, **remove the marker line entirely**. Do not leave an empty comment.
- Stanzas in `stanzas/` are plain text fragments — not templated. Any values they need come from runtime env, not from Stage 1 substitution.

## Runtime-resolved values

These are **not** placeholders in the templates. The rendered scripts compute them at invocation time. Listed here so developers understand what *not* to hardcode if they hand-edit the rendered harness later.

| Value | How it's resolved | Where |
|---|---|---|
| Repo path | `REPO_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` | `run-sandbox.sh` |
| Repo name | `REPO_NAME="$(basename "$REPO_PATH")"` | `run-sandbox.sh` |
| Session dir name | `"$(printf '%s' "$REPO_PATH" | tr / -)"` (matches Claude Code's cwd-based naming) | `run-sandbox.sh` |
| Host UID/GID | `$(id -u)` / `$(id -g)` | `run-sandbox.sh` → Docker build args |
| Host repo path (in container) | `HOST_REPO_PATH` env var from compose | `docker/entrypoint.sh` |

## Why no `{{REPO_PATH}}`

An earlier design baked the repo's absolute path into `run-sandbox.sh` and the Dockerfile symlink. This broke under three realistic scenarios:

1. Developer renames/moves the checkout (`mv ~/github/foo ~/work/foo`).
2. Two developers share the repo but keep checkouts at different paths.
3. CI clones to a different base path (`/home/runner/work/...`) than the developer's local checkout.

Resolving at runtime costs one `cd`+`pwd` call at launch and eliminates all three cases.
