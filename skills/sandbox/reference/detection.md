# Build-System Detection Rules

Rules the agent uses at Stage 0 of the sandbox skill to pick the right Dockerfile and entrypoint stanzas.

## Contents

- Detection priority
- Python detection
- CMake detection
- Node / TypeScript detection
- Submodules and extra safe dirs
- Polyglot handling
- When in doubt

## Detection priority

Detection is **additive, not mutually exclusive** — a repo can be Python + CMake, Node + Python, or any combination. Check each in turn and record every match:

1. Python — `pyproject.toml` OR `requirements.txt` at target root
2. CMake — `CMakeLists.txt` at target root
3. Node / TypeScript — `package.json` at target root
4. Submodules — `.gitmodules` at target root
5. Fallback — if none of 1–3 match, use the `minimal` stanza for the entrypoint and skip the Dockerfile language stanza entirely

Report every match to the developer at the end of Stage 0. Let the developer override at Stage 1 before Stage 2 writes files.

## Python detection

Match if any of these exist at target root:

- `pyproject.toml`
- `requirements.txt`
- `setup.py` (legacy — treat as Python match, but flag as old-style)
- `Pipfile`

Python stanza selection at Stage 1:

- `{{LANG_DOCKERFILE_STANZA}}` includes `python`
- `{{LANG_ENTRYPOINT_STANZA}}` includes `python`
- `{{BUILD_DIR_ISOLATION}}` defaults to `pytest` (route `.pytest_cache` to `.pytest_cache.sandbox`)

Additional checks:

- If `requirements.txt` does not exist but `pyproject.toml` does, the Dockerfile `COPY requirements.txt` line must be removed from the python stanza (or ask the developer to export one). Don't fail — ask.
- If the repo has a `test_fw/` or similar in-workspace package with its own `pyproject.toml`, flag it so Stage 2 can install it editable at runtime in the entrypoint.

## CMake detection

Match if `CMakeLists.txt` exists at target root.

CMake stanza selection at Stage 1:

- `{{LANG_DOCKERFILE_STANZA}}` includes `cmake`
- `{{LANG_ENTRYPOINT_STANZA}}` includes `cmake`
- `{{BUILD_DIR_ISOLATION}}` defaults to `cmake` (use `build.sandbox/` as the container build dir)

Additional checks:

- If `CMakePresets.json` exists, note its default preset to the developer — it may need overriding to honor `BUILD_DIR`.
- If the top-level `CMakeLists.txt` calls `add_subdirectory` with absolute paths, flag it: the symlink trick in `entrypoint.sh` normally handles this, but hardcoded paths beyond the repo root may not resolve.

## Node / TypeScript detection

Match if `package.json` exists at target root.

Node stanza selection at Stage 1:

- `{{LANG_DOCKERFILE_STANZA}}` includes `node`
- `{{LANG_ENTRYPOINT_STANZA}}` includes `node`
- `{{BUILD_DIR_ISOLATION}}` defaults to `node` (route `NPM_CONFIG_CACHE` to `/home/agent/.npm-sandbox`; leaves `node_modules/` shared with the host)

Additional checks:

- If `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock` exists, note which package manager the repo uses. The default stanza installs `npm` via NodeSource; pnpm/yarn require one extra `npm install -g <pm>` line appended to the node.dockerfile stanza.
- If `tsconfig.json` exists, the project is TypeScript. No Dockerfile change — `typescript` and `ts-node` are devDependencies installed via npm.
- If `.nvmrc` exists, prefer its Node major version over the stanza's default (22 LTS).

**`node_modules/` isolation is intentionally skipped.** Most JS toolchains (bundlers, Jest resolver, ts-node) assume `node_modules/` at the project root. Isolating it to `node_modules.sandbox/` breaks resolution. If host and container Node versions diverge and native modules break, the developer runs `rm -rf node_modules && npm ci` — or adds an `npm ci` line to their entrypoint. `run-sandbox.sh --fresh` wipes the npm cache (`~/.npm-sandbox/`) but deliberately leaves `node_modules/`.

## Submodules and extra safe dirs

Parse `.gitmodules` (if present) to collect submodule paths. Each becomes a line in the `SAFE_DIRS` stanza:

```bash
gosu agent git config --global --add safe.directory /workspace/<path>
```

If no `.gitmodules` exists, the stanza is empty (marker line is removed).

Also check for any `extern/` or `third_party/` or `vendor/` directory that contains a `.git` file (submodule marker) — add those too if they're not listed in `.gitmodules`.

## Polyglot handling

Multi-language repos get every matching stanza included. Ordering (see `placeholders.md`) is **cmake → node → python**: compilers first so native bindings can link, Node before Python so `pip` lands last (some pip wheels can shell out to `npm`-managed tooling during build). Entrypoint stanzas follow the same order.

Example combinations:

| Repo markers | Dockerfile stanzas | Entrypoint stanzas | FRESH_CLEANUP |
|---|---|---|---|
| `pyproject.toml` + `CMakeLists.txt` | cmake, python | cmake, python | `cmake.fresh` + `python.fresh` |
| `package.json` + `tsconfig.json` | node | node | `node.fresh` |
| `package.json` + `pyproject.toml` | node, python | node, python | `node.fresh` + `python.fresh` |
| `CMakeLists.txt` + `package.json` + `pyproject.toml` | cmake, node, python | cmake, node, python | all three `.fresh` |

## When in doubt

If detection is ambiguous (e.g. a `pyproject.toml` containing only linter config for a Rust repo), ask the developer at Stage 0 rather than guessing. A wrong stanza at Stage 2 is expensive to unwind; asking is cheap.

Do **not** use the repo name, the README, or the git remote URL to infer language — those are often stale or misleading.
