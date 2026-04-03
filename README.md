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

## Code Generation

| Skill | Use When |
|-------|----------|
| [generator-coding](skills/generator-coding/) | Building template-based code generators — data model + templates + helpers producing repetitive interface code (register maps, serialization, schema-driven output) |

## Traceability

Components for recording and auditing agent activity across sessions.

| Component | Type | Purpose |
|-----------|------|---------|
| [dev-record](skills/dev-record/) | Plugin | Passive session recording — captures plans, human input, agent decisions, and deviations via hooks. Load with `--plugin-dir skills/dev-record` |
| [review-skill](skills/review-skill/) | Skill | Review a SKILL.md for quality, correctness, and alignment with Claude Code conventions before committing |
| [no-pre-existing-failures](skills/no-pre-existing-failures/) | Skill | Test accountability policy — all failures belong to the current changeset; commits must include test results |

dev-record produces two tiers of audit data: **project artifacts** (`audit/dev_record/` — session summaries, agent reports, plan snapshots) that you commit to version control, and **operational detail** (`audit/ops_record/` — full event logs) that stays gitignored.

Key dev-record capabilities:
- **Hook-detected anomalies** — flags stop-word misuse, hallucinated paths, repeated tool failures, and unplanned file changes
- **Agent self-reporting** — agents can log plan deviations, scope creep, and declined-difficult decisions via a helper script
- **Plan-vs-actual diffing** — session finalization compares planned files against actual git changes and emits deviation events

## Testing

A multi-model E2E test framework for validating skills and plugins against real Claude sessions.

```bash
make test          # Run skill tests across model tiers (weakest, mid, strongest)
make test-fw       # Run framework unit tests
make test-all      # Run everything
make open          # View HTML test report in browser
```

The framework lives in [`test_fw/`](test_fw/) as an installable Python package and provides:

- **Claude SDK integration** — multi-turn conversation fixtures via pytest
- **Audit inspection** — helpers for reading dev-record session summaries and event logs
- **Ablation detection** — semantic analysis (TF-IDF embeddings, concept matching) to verify agents preserve meaning while transforming documents
- **Multi-format reporting** — per-model JSON, Markdown, and HTML reports aggregated to `site/`

CI runs via [`.github/workflows/e2e-tests.yml`](.github/workflows/e2e-tests.yml). Regression results are published to [shincbm.com/claude-skills](https://www.shincbm.com/claude-skills/).

### Check classes

Skill testing is more like characterization than traditional software testing — some outcomes are objectively verifiable, others depend on model capability. Tests use three check classes to distinguish between hard requirements and quality indicators:

| Class | On failure | Terminology | Use when |
|-------|-----------|-------------|----------|
| **require** | Aborts test | PASS / FAIL | Infrastructure prerequisites — session completed, no errors. The test cannot continue without this. |
| **expect** | Records failure, test continues | PASS / FAIL | Prompted deliverables — the prompt explicitly asked the model to produce this (e.g. "create library.py"). Not producing it is a failure. |
| **achieve** | Records result, test continues | ACHIEVED / NOT ACHIEVED | Quality indicators — how well the model followed the skill's guidance. Weighted by difficulty and rolled up to an ability percentage. |

Every test reports two scores:

- **Hard: PASS/FAIL** — all require + expect checks must pass
- **Ability: X%** — weighted percentage of achieve checks, where difficulty tiers (`expected` 1.0, `challenging` 0.5, `aspirational` 0.25) reflect model-tier expectations

See [`docs/testing.md`](docs/testing.md) for the full guide on choosing check classes and difficulty tiers.

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

## Authoring Skills

See [AUTHORING.md](AUTHORING.md) for conventions on writing new skills — directory layout, frontmatter fields, the stop-after-each-stage pattern, and description best practices.

## Related

- [claude-devtools](https://www.claude-dev.tools/) — free desktop app that visualizes Claude Code session logs from `~/.claude/`. Provides token attribution, tool call inspection, subagent trees, and notification triggers. Complementary to dev-record: claude-devtools gives you rich visual replay of *what happened*; dev-record captures *agent intent* (plans, deviations, scope creep) and produces committable audit artifacts that claude-devtools doesn't
- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) — curated list of Claude Code skills, hooks, commands, and tools
- [Claude Skill: Document Review Pipeline](https://www.shincbm.com/agentic-code/2026/02/15/claude-skill-document-review.html) — blog post on the design of these skills

## License

[Unlicense](LICENSE) (public domain)
