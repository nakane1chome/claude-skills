# claude-skills

A library of generic, reusable [Claude Code](https://claude.ai/code) skills for document authoring and review workflows.

## Skills

| Skill | Description |
|-------|-------------|
| [review-steps](skills/review-steps/) | Structured review process for polishing drafts — language, clarity, structure, and industry best practice |
| [flesh-out](skills/flesh-out/) | Transform raw notes and skeletons into structured documents through guided generative expansion |
| [strong-edit](skills/strong-edit/) | Critical editorial analysis — challenges structure, argument, relevance, and readability |
| [agent-optimize](skills/agent-optimize/) | Restructure verbose prose into formats that AI agents parse efficiently |
| [sdlc-cross-review](skills/sdlc-cross-review/) | Review a document against its SDLC lifecycle context using V-model cross-validation |

## Installation

Copy a skill directory into your project or global Claude Code skills folder:

```bash
# Per-project
cp -r skills/review-steps /path/to/project/.claude/skills/

# Global (available in all projects)
cp -r skills/review-steps ~/.claude/skills/
```

## How Skills Work

Each skill is a `SKILL.md` file with YAML frontmatter and a structured prompt. When invoked, Claude Code follows the steps defined in the skill.

All skills in this library use a **stop-after-each-stage** pattern — the agent pauses for developer review between stages. Some skills include a `responsibilities.md` that defines which stages the agent leads vs assists on.

### Choosing the Right Skill

| Document State | Use |
|----------------|-----|
| Raw notes, bullet points, stream of consciousness | **flesh-out** |
| Draft with typos, incomplete sentences | **review-steps** |
| Complete draft needing critical evaluation | **strong-edit** |
| Polished draft, final check | **review-steps** |
| Verbose docs that agents will consume | **agent-optimize** |
| Document that should align with a parent spec | **sdlc-cross-review** |

Skills are composable: **flesh-out** a skeleton, then **review-steps** the result, then **strong-edit** the final draft.

## License

[Unlicense](LICENSE) (public domain)
