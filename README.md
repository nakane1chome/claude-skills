# claude-skills

Scaffolding for repeatable, deterministic agent-driven development with [Claude Code](https://claude.ai/code).

This repository provides two kinds of reusable components:

- **Skills** — structured prompts that guide Claude Code through multi-step workflows with developer checkpoints between stages
- **Plugins** — hook-based components that Claude Code loads via `--plugin-dir` to passively instrument sessions without touching project settings

Together they give you a controlled development loop: skills enforce *how* the agent works on your documents, and plugins record *what* happened so you can audit and improve the process.

## Document Curation

Skills for authoring, reviewing, and optimizing documents. They use a **stop-after-each-stage** pattern — the agent pauses for developer review between stages.

| Skill | Use When |
|-------|----------|
| [flesh-out](skills/flesh-out/) | Raw notes, bullet points, or stream of consciousness that needs generative expansion into structured content |
| [review-steps](skills/review-steps/) | A draft with typos, incomplete sentences, or needing a final polish pass for language, clarity, and structure |
| [strong-edit](skills/strong-edit/) | A complete draft that needs substantive critique — challenges structure, argument, relevance, and readability |
| [agent-optimize](skills/agent-optimize/) | Verbose prose that AI agents will need to parse — restructures for efficient machine consumption |
| [sdlc-cross-review](skills/sdlc-cross-review/) | A document that should align with its parent spec — completeness and consistency checking via V-model cross-validation |

Skills are composable: **flesh-out** a skeleton, then **review-steps** the result, then **strong-edit** the final draft.

## Traceability

Components for recording and auditing agent activity across sessions.

| Component | Type | Purpose |
|-----------|------|---------|
| [dev-record](skills/dev-record/) | Plugin | Passive session recording — captures plans, human input, agent decisions, and deviations via hooks. Load with `--plugin-dir skills/dev-record` |
| [review-skill](skills/review-skill/) | Skill | Review a SKILL.md for quality, correctness, and alignment with Claude Code conventions before committing |

dev-record produces two tiers of audit data: **project artifacts** (`audit/dev_record/` — session summaries, agent reports, plan snapshots) that you commit to version control, and **operational detail** (`audit/ops_record/` — full event logs) that stays gitignored.

## Installation

```bash
# Interactive installer — choose global or per-project, select which skills
bash install.sh

# Or copy individual components manually:
# Per-project skill
cp -r skills/review-steps /path/to/project/.claude/skills/

# Global skill (available in all projects)
cp -r skills/review-steps ~/.claude/skills/

# Plugin (load via CLI flag — no copy needed)
claude --plugin-dir /path/to/claude-skills/skills/dev-record
```

## Links

- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) — curated list of Claude Code skills, hooks, commands, and tools
- [Claude Skill: Document Review Pipeline](https://www.shincbm.com/agentic-code/2026/02/15/claude-skill-document-review.html) — blog post on the design of these skills

## License

[Unlicense](LICENSE) (public domain)
