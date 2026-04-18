---
name: sandbox
description: >
  Scaffolds a Docker "sandbox" harness into a repo so Claude Code can run in
  `--dangerously-skip-permissions` (YOLO) mode inside an Ubuntu container, with
  the project bind-mounted at /workspace and the host's ~/.claude bind-mounted
  for auth and session continuity. Use when the developer wants an isolated
  filesystem for agent writes but still wants host-visible builds, logs, and
  session history.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
argument-hint: [target-dir]
---

This skill installs a four-file Docker harness into a target repo: `run-sandbox.sh` (launcher), `docker-compose.yml`, `docker/Dockerfile`, `docker/entrypoint.sh`. Once installed, `./run-sandbox.sh --build` launches Claude Code inside a container without permission prompts.

**Stop after each stage and have changes reviewed with the user.**

> **Philosophy**: The sandbox isolates *writes the agent makes to the working tree* (via an `agent` user matching host UID/GID, and via per-tool cache/build-dir duplication like `.pytest_cache.sandbox/` or `build.sandbox/`) but **intentionally shares** `~/.claude` and `~/.claude.json` with the host so auth, session history, and projects config persist across host ↔ container runs. This trade-off is what makes `--resume <id>` work across boundaries — and it's also why a misbehaving YOLO agent can corrupt host config. The developer should understand both sides before installing.

> See `responsibilities.md` for the full agent vs developer ownership matrix, `reference/placeholders.md` for the template-variable list, and `reference/detection.md` for language-detection rules.

## Stage 0 — Understand the target repo (agent proposes, developer confirms)

- Resolve the target directory: use `$ARGUMENTS` if set; otherwise default to `$(pwd)`. If `$ARGUMENTS` is set but the path doesn't exist or isn't a directory, stop and ask the user.
- Detect the repo's build system using the rules in `reference/detection.md`. Summarize: Python (`pyproject.toml`, `requirements.txt`), CMake (`CMakeLists.txt`), both, or neither.
- Check for collisions — does the target already have `run-sandbox.sh`, `docker-compose.yml`, `docker/Dockerfile`, or `docker/entrypoint.sh`? If so, list each and ask the user whether to overwrite, merge, or abort.
- Check for `.claude/settings.json` in the target — if it contains hardcoded absolute paths (e.g. hook commands using `/home/user/...`), flag this, because the entrypoint's host-path symlink needs to match.
- Confirm understanding with the developer before proceeding. A wrong language detection at Stage 0 causes the wrong Dockerfile stanza at Stage 2.

## Stage 1 — Confirm template variables (agent proposes, developer approves)

Propose values for each placeholder from `reference/placeholders.md`. Present as a table:

| Placeholder | Proposed value | Source |
|---|---|---|
| `{{REPO_NAME}}` | basename of target dir | e.g. `my-project` |
| `{{LANG_DOCKERFILE_STANZA}}` | `python` / `cmake` / both / `minimal` | Stage 0 detection |
| `{{LANG_ENTRYPOINT_STANZA}}` | matches above | Stage 0 detection |
| `{{BUILD_DIR_ISOLATION}}` | `pytest` / `cmake` / both / none | Developer choice |
| `{{EXTRA_SAFE_DIRS}}` | list of git submodule paths | `.gitmodules` in target, or empty |
| `{{EXTRA_PIP_PACKAGES}}` | extra pip installs | `requirements.txt` presence, or empty |

Note: there is intentionally no `{{REPO_PATH}}` or `{{SESSION_DIR_NAME}}` placeholder — both are resolved **at runtime** by the launcher and entrypoint, so the rendered harness is movable between hosts or across clones without re-running the skill.

Developer confirms or edits each value. If the developer overrides the detection, record the reason inline so Stage 2 knows what to do.

## Stage 2 — Render and write the harness (agent leads)

For each of the four template files in `templates/`:

1. Read the `.tmpl` file.
2. Substitute `{{VAR}}` placeholders with Stage 1 values.
3. Where the template contains a stanza marker (`# @@STANZA:<name>@@`), splice in the matching file from `templates/stanzas/` — or remove the marker line entirely if the stanza is `minimal` or not selected.
4. Write the rendered file to the target repo at its final path.

Write order:

- `<target>/run-sandbox.sh` — `chmod +x` after writing
- `<target>/docker-compose.yml`
- `<target>/docker/Dockerfile`
- `<target>/docker/entrypoint.sh` — `chmod +x` after writing

If `docker/` doesn't exist in the target, create it. Report the written paths back to the developer.

## Stage 3 — Verify end-to-end (agent proposes commands, developer runs)

The agent proposes a verification checklist; the developer executes each step and reports outcomes. The agent interprets failures and proposes fixes.

1. `touch ~/.claude.json` (no-op if it exists — launcher does this too, but confirm the host has a writable home).
2. `./run-sandbox.sh --build` — image builds, container launches, Claude prompt appears.
3. Inside the container, run the repo's canonical test or build command (`pytest`, `cmake --build build.sandbox`, etc.). Confirm it succeeds and writes to the sandbox build/cache dir — not the host's.
4. On the host, repeat the same command outside the container. Confirm the host build/cache dir (`.pytest_cache/`, `build/`) is unchanged.
5. Host-side: start a normal `claude` session in the repo, `/exit`, note the session ID. Then `./run-sandbox.sh --resume <id>` — transcript restored. Confirms host ↔ container session continuity via the symlinked path.
6. `./run-sandbox.sh -c` — auto-resumes the most recent session.
7. `./run-sandbox.sh --fresh --build` — sandbox build/cache dirs removed, image rebuilt clean.

If any step fails, the agent investigates based on the failure mode, not by retrying.

## Stage 4 — Tidy up (agent leads)

- Propose `.gitignore` entries for any sandbox-specific build/cache dirs (e.g. `.pytest_cache.sandbox/`, `build.sandbox/`). Apply with developer approval.
- Remind the developer: the harness is meant to be committed to the repo (so every collaborator gets the same sandbox), but `~/.claude` bind-mount means credentials live on the host — never commit those.
- If the target repo is a monorepo or has nested projects, note which subdirectories were *not* covered and whether they need their own sandbox.
- Offer a one-line summary of how to invoke the sandbox from now on.

## Output

The skill produces:

- Four files written into the target repo (`run-sandbox.sh`, `docker-compose.yml`, `docker/Dockerfile`, `docker/entrypoint.sh`).
- Optional `.gitignore` edits in the target.
- A verification report in the chat transcript (Stage 3 outcomes).
- No other artifacts.

## When to Use This vs Other Skills

| Goal | Use |
|------|-----|
| Install a Docker YOLO-mode sandbox into a repo | **sandbox** (this skill) |
| Record agent activity during a sandbox session | **dev-record** (plugin, complementary) |
| Generate repetitive interface code from a data model | **generator-coding** |
