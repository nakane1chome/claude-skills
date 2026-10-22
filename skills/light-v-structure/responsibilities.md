# Responsibilities

## Shared Responsibilities

- Document everything in this project in text-based files, following the principle of "[docs as code](https://www.writethedocs.org/guide/docs-as-code/)"
- Cross-reference code and tests to documentation
- Cross-validate at regular checkpoints:
  - Atomic checkpoints that capture at least 2 levels of the V
  - Automated testing cross-validates implementation updates
  - A checkpoint should have passing tests and implemented features
- Make all context available with documentation; focus on the big picture in one repo:
  - Integrate everything into your workspace
  - Consider the architectural quanta (independently deployable units), but within each quantum go mono-repo

## Agent Responsibilities

- Follow this guide
- Ask the developer to document basic instructions
- Plan according to docs as defined in this skill, then confirm with the developer

See also:
- [Claude Code Skills](https://code.claude.com/docs/en/skills) - the skills format this project uses
- [AGENTS.md](https://agents.md/) - an emerging open format for guiding coding agents

## Developer Responsibilities

- Review the output of the agent
  - Develop the skill of reading code, as it will become dominant over writing code
- Ensure basic instructions are documented according to this skill
- Repeat yourself; agents need reinforcement, so make expectations explicit
  - Don't waste context repeating verbally - write it down in `docs/`
- Use prompts for refining and clarifying

**Know and control the sources of noise:**

- **Stochastic noise** - random changes in implementation decisions
  - e.g., Check if the same document flow gives the same results
- **Quantization noise** - alignment jumps across layered decisions
  - e.g., Recognize a test case written to the lowest layer to stimulate business logic that avoids the API it is intended to test; the model has "quantized" to the wrong abstraction boundary
