# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A library of generic, reusable Claude Code skills for document authoring and review workflows. These skills are designed to be copied into a project's `.claude/skills/` directory or into `~/.claude/skills/` for global use.

## Skill Structure

Each skill lives in `skills/<skill-name>/` and contains:
- `SKILL.md` — The skill definition with YAML frontmatter (`name`, `description`) and the prompt body
- `responsibilities.md` — (optional) Agent vs developer ownership matrix for each stage

## Skills

| Skill | Purpose | Use When |
|-------|---------|----------|
| **review-steps** | Structured review for polish | Draft with typos, incomplete sentences, or needing a final check |
| **flesh-out** | Generate structure from raw notes | Raw notes, bullet points, stream of consciousness |
| **strong-edit** | Critical editorial analysis | Complete draft needing substantive critique |
| **agent-optimize** | Optimize docs for AI agent consumption | Verbose prose that agents will need to parse |
| **sdlc-cross-review** | Completeness + parent document consistency | Document that needs checking against its SDLC hierarchy |
| **review-skill** | Review a SKILL.md for quality and conventions | New or existing skill that needs checking before use |
| **dev-record** | Record agent activity via hooks | Setting up passive session recording for audit |

## Conventions

- Document skills use a **stop-after-each-stage** pattern — the agent pauses for developer review between stages
- Infrastructure skills (e.g. dev-record) use an **action-dispatch** pattern — the user specifies an action to run
- Skills with a `responsibilities.md` define which stages the agent leads vs assists on
- Skills are meant to be composable: `flesh-out` a skeleton, then `review-steps` the result, then `strong-edit` the final draft

## License

Unlicense (public domain)
