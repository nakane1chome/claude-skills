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

## Code Generation

| Skill | Purpose | Use When |
|-------|---------|----------|
| **generator-coding** | Template-based code generation pattern | Building generators that use data models + templates + helpers to produce repetitive interface code |

## Traceability

| Component | Type | Purpose |
|-----------|------|---------|
| **dev-record** | Plugin | Passive session recording — plans, input, decisions, deviations, anomaly detection, agent self-reporting |
| **review-skill** | Skill | Review a SKILL.md for quality and convention alignment |

## Testing

E2E tests validate skills and plugins against real Claude sessions across model tiers.

- `test_fw/` — reusable pytest framework (Claude SDK integration, audit inspection, ablation detection, test steps)
- `tests/` — per-skill E2E tests that depend on `test_fw`
- `make test` runs skill tests across model tiers; `make test-fw` runs framework unit tests; `make test-all` runs both
- CI: `.github/workflows/e2e-tests.yml` publishes HTML reports to GitHub Pages
- See `docs/testing.md` for the full test framework guide

### Test Steps

Tests use the `steps` fixture (`TestSteps` class) with three check classes:

| Class | Prefix | On failure | Use when |
|-------|--------|-----------|----------|
| **require** | `steps.require_` | Aborts test | Infrastructure prerequisites (session health, no errors) |
| **expect** | `steps.expect_` | Records FAIL, continues | Prompted deliverables the model was asked to produce |
| **achieve** | `steps.achieve_` | Records NOT ACHIEVED, continues | Quality/approach indicators, weighted by difficulty |

Every test reports two scores: **Hard: PASS/FAIL** (require + expect) and **Ability: X%** (weighted achieve checks). Difficulty tiers: `expected` (1.0), `challenging` (0.5), `aspirational` (0.25).

## Test Failures

**Every test failure is a real bug. Fix it.** There is no such thing as a "pre-existing failure," a "known flaky test," or an "unrelated issue." If a test fails, it is broken and you must fix it before moving on. Do not dismiss, skip, or rationalize away any failure. Do not label failures as "pre-existing" to avoid responsibility. If you broke it, fix it. If it was already broken, fix it anyway — you are looking at it now and that makes it your problem.

## Conventions

- Document curation skills use a **stop-after-each-stage** pattern — the agent pauses for developer review between stages
- Plugins use a **declarative hook** model — `hooks/hooks.json` registers hooks, no settings.json merge needed
- Infrastructure skills (e.g. dev-record) use an **action-dispatch** pattern — the user specifies an action to run
- Skills with a `responsibilities.md` define which stages the agent leads vs assists on
- Skills are composable: `flesh-out` a skeleton, then `review-steps` the result, then `strong-edit` the final draft
- See `AUTHORING.md` for the full style guide on writing new skills (directory layout, frontmatter, description conventions)

## License

Unlicense (public domain)
