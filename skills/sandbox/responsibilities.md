# Sandbox Skill Responsibilities

This skill scaffolds a Docker sandbox harness into a target repo. The agent handles detection, rendering, and write-out; the developer approves key decisions (language variant, build-dir isolation, collisions) and runs the end-to-end verification.

## Stage Ownership

| Stage | Agent | Developer | Notes |
|-------|-------|-----------|-------|
| 0. Understand target repo | Proposes | **Confirms** | Wrong detection here cascades — developer must verify |
| 1. Confirm template variables | Proposes | **Approves** | Developer owns the language + isolation choices |
| 2. Render and write harness | **Leads** | Reviews writes | Agent does the substitution; developer sanity-checks paths |
| 3. Verify end-to-end | Proposes commands | **Runs** | Build/launch requires docker on the developer's machine |
| 4. Tidy up | **Leads** | Approves | Agent proposes .gitignore + commit guidance |

**Stage 0 is critical**: If the agent misdetects the build system, Stage 2 writes the wrong Dockerfile/entrypoint stanza. If the agent overlooks a collision, Stage 2 silently clobbers the developer's existing setup.

## Agent Responsibilities

- Detect language/build system from filesystem markers (see `reference/detection.md`). Do not infer from repo name or README.
- Never hardcode host-absolute paths into the rendered harness — all paths resolve at runtime from `$(pwd)` or bind-mount locations. See the "Open items" section of the original plan.
- Substitute placeholders faithfully. If a placeholder's value is empty (e.g. no submodules), leave the rendered file without the stanza rather than inserting an empty block.
- Report every file written in Stage 2 with absolute paths.
- In Stage 3, interpret verification failures diagnostically — do not retry a failing command.

## Developer Responsibilities

- Confirm language detection in Stage 0. Override if the agent guessed wrong (e.g. a Rust repo with a token `pyproject.toml` for tooling).
- Approve any collision-overwrite decision in Stage 0 before Stage 2 begins.
- Approve the proposed values in Stage 1's table. Pay attention to `{{BUILD_DIR_ISOLATION}}` — this determines whether host and container can safely run tests in parallel.
- Run Docker in Stage 3. Report outcomes to the agent; the agent cannot observe the verification itself.
- Decide whether to commit the harness or leave it per-developer (usually commit).

## Why This Split?

**Agent strengths:**
- Detecting language markers, parsing `.gitmodules`, computing basenames
- Consistent template substitution across four interrelated files
- Diagnosing failure modes by reading error output

**Agent limitations:**
- Cannot run Docker or observe container output directly
- May misdetect build systems in polyglot repos
- Cannot judge repo-level conventions that aren't visible in the filesystem

**The critical handoff**: Stage 0 → Stage 1. If the agent misdetects or misses a collision, the developer must catch it before Stage 2 writes files.
