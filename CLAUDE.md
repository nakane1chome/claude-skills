# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Scaffolding for repeatable, deterministic agent-driven development. Two kinds of components:

- **Skills** — structured prompts (`SKILL.md` + optional `responsibilities.md`) that guide multi-step workflows with developer checkpoints
- **Plugins** — hook-based components (`plugin.json` + `hooks/hooks.json`) loaded via `--plugin-dir` for passive session instrumentation

## Component Structure

Each component lives in `skills/<name>/` and contains:
- `SKILL.md` — Skill definition with YAML frontmatter (`name`, `description`) and the prompt body
- `responsibilities.md` — (optional) Agent vs developer ownership matrix for each stage
- `plugin.json` — (plugins only) Plugin manifest for Claude Code auto-loading
- `hooks/hooks.json` — (plugins only) Declarative hook registration using `${CLAUDE_PLUGIN_ROOT}` paths

## Document Curation Skills

| Skill | Purpose | Use When |
|-------|---------|----------|
| **review-steps** | Structured review for polish — language, clarity, structure | Draft with typos, incomplete sentences, or needing a final check |
| **flesh-out** | Generate structure from raw notes or bullet points | Raw notes, bullet points, stream of consciousness |
| **strong-edit** | Critical editorial analysis — challenges argument and structure | Complete draft needing substantive critique |
| **agent-optimize** | Optimize docs for AI agent consumption | Verbose prose that agents will need to parse |
| **sdlc-cross-review** | Completeness + parent document consistency via V-model | Document that needs checking against its SDLC hierarchy |

## Traceability

| Component | Type | Purpose |
|-----------|------|---------|
| **dev-record** | Plugin | Passive session recording — plans, input, decisions, deviations |
| **review-skill** | Skill | Review a SKILL.md for quality and convention alignment |

## Conventions

- Document curation skills use a **stop-after-each-stage** pattern — the agent pauses for developer review between stages
- Plugins use a **declarative hook** model — `hooks/hooks.json` registers hooks, no settings.json merge needed
- Infrastructure skills (e.g. dev-record) use an **action-dispatch** pattern — the user specifies an action to run
- Skills with a `responsibilities.md` define which stages the agent leads vs assists on
- Skills are composable: `flesh-out` a skeleton, then `review-steps` the result, then `strong-edit` the final draft

## License

Unlicense (public domain)
