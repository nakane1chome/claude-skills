# Authoring Claude Code Skills

Best practices for writing effective Claude Code skills for this repo and beyond.

## Directory Layout

```
skills/
  my-skill/
    SKILL.md              # Required — skill definition
    responsibilities.md   # Optional — agent vs developer ownership matrix
    templates/            # Optional — templates, examples, reference material
```

- Use **kebab-case** for skill directory names
- Keep `SKILL.md` under **500 lines** — move reference material, templates, and examples to separate files
- The `_template/` directory provides a starting point: copy it, rename, and customize

## How Skills Are Loaded

1. **Descriptions are always in context.** Claude sees every skill's `name` and `description` from frontmatter, so it knows what's available.
2. **Full content loads on invocation.** The prompt body of `SKILL.md` only loads when the skill is invoked — either by the user (`/skill-name`) or by Claude via the Skill tool.
3. **Skills don't run passively.** They are always explicitly invoked, never silently active in the background.
4. **Exception: subagents.** Agent definitions can preload skill content via the `skills` field in agent frontmatter.

This means the `description` field is critical — it's what Claude uses to decide whether to invoke the skill.

## Frontmatter

```yaml
---
name: my-skill
description: >
  What this skill does and when to use it.
---
```

### Required fields

| Field | Purpose |
|-------|---------|
| `name` | Kebab-case identifier, must match directory name |
| `description` | What the skill does and when to use it — Claude reads this to decide invocation |

### Description tips

- Be specific about **when** to use the skill, not just what it does
- Include trigger phrases users would naturally say
- Too broad = triggers too often. Too narrow = never triggers.
- Good: `"Critical editorial analysis of articles. Use for substantive editing - challenging what's said and how, not just polish."`
- Bad: `"Helps with documents"` (too broad) or `"Reviews Q3 marketing briefs"` (too narrow)

### Optional fields

| Field | Default | Purpose |
|-------|---------|---------|
| `disable-model-invocation` | `false` | Set `true` to prevent Claude from invoking automatically — user must type `/skill-name` |
| `user-invocable` | `true` | Set `false` to hide from the `/` menu — skill becomes background knowledge only |
| `allowed-tools` | all tools | Comma-separated list of tools the skill can use (e.g., `Read, Grep, Glob`) |
| `context` | main conversation | Set `fork` to run in an isolated subagent (loses conversation history) |
| `agent` | none | Subagent type when `context: fork` (e.g., `Explore`) |
| `argument-hint` | none | Shown during autocomplete (e.g., `[filename]`, `[url]`) |

### Invocation control patterns

| Pattern | Fields | Use when |
|---------|--------|----------|
| Normal (default) | — | Both user and Claude can invoke |
| Slash-command only | `disable-model-invocation: true` | Side-effect workflows where unintended invocation is risky |
| Background knowledge | `user-invocable: false` | Claude should know about it but users shouldn't invoke directly |
| Isolated execution | `context: fork` | Long-running or context-heavy tasks that shouldn't pollute the main conversation |

## Prompt Body

### Stage-based workflows

Skills in this repo use a **stop-after-each-stage** pattern for human-in-the-loop review:

```markdown
**Stop after each stage and have changes reviewed with the user.**

## Stage 0 — Understand (agent proposes, developer confirms)
- Read the input and summarize understanding
- Confirm intent before proceeding

## Stage 1 — [Action] (agent leads)
- Step-by-step instructions
- Use questions to guide analysis

## Stage N — Tidy up
- Final cleanup
```

### Guidelines

- **Stage 0 for understanding.** Always start by reading and confirming intent before doing work.
- **Use questions, not just imperatives.** "Does each section serve the argument?" is better than "Check sections."
- **Be explicit about responsibilities.** Annotate each stage: `(agent leads)`, `(developer confirms)`, `(agent proposes, developer approves)`.
- **Include "When to use this vs other skills"** if the skill overlaps with others in the same family. Use a comparison table.
- **Philosophy notes** go in blockquotes at the top of the skill.

### Formatting conventions (this repo)

| Element | Format |
|---------|--------|
| Philosophy/context notes | Blockquote (`>`) |
| Stage titles | Bold with numbering (`## Stage 1 — Title`) |
| Comparisons | Tables |
| Stop instruction | Bold, before first stage |

## Arguments and Dynamic Context

### Arguments

Users can pass arguments when invoking a skill: `/my-skill some-file.md`

Access them in the prompt body:

| Variable | Contains |
|----------|----------|
| `$ARGUMENTS` | The full argument string |
| `$0` | First positional argument |
| `$1` | Second positional argument |

### Dynamic context

Inject shell output into the prompt before it reaches Claude:

```markdown
The current branch is: !`git branch --show-current`
Files in scope: !`ls src/`
```

The shell command runs first; its output replaces the `` !`command` `` expression in the prompt text.

## Supporting Files

- **`responsibilities.md`** — Agent vs developer ownership matrix for multi-stage workflows with mixed ownership
- **Templates and examples** — Put in subdirectories, reference from `SKILL.md` so Claude knows when to load them
- **Reference material** — Large lookup tables, checklists, or standards that would bloat `SKILL.md`

Always reference supporting files from `SKILL.md`. Unreferenced files in the skill directory are invisible to Claude.

## Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| Overly broad description | Triggers on unrelated tasks | Add "Use when..." and "Not for..." specifics |
| Overly narrow description | Never triggers | Broaden to cover the category of task |
| No review pauses | User loses control of multi-stage workflow | Add stop-after-each-stage instruction |
| Unreferenced supporting files | Claude doesn't know they exist | Reference from `SKILL.md` with instructions on when to read them |
| All stages batched | Large changes without checkpoints | Break into stages with review pauses |
| Ambient task instructions | Skill with no `context: fork` and no clear action becomes confusing background noise | Give the skill a clear invocation trigger or use `context: fork` |
| Inlining everything | `SKILL.md` becomes too long to maintain | Extract reference material to supporting files |

## Composition

Skills are designed to be composable. A typical document workflow:

1. **flesh-out** — Generate structure from raw notes
2. **review-steps** — Polish the draft
3. **strong-edit** — Critical evaluation of the result
4. **agent-optimize** — Optimize for AI consumption (if needed)
5. **review-skill** — Review a skill itself for quality (meta)

When authoring a new skill, consider where it fits in this chain and document the handoff points.
