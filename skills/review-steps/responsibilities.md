# Review Responsibilities

This skill uses a human-in-the-loop approach. Research shows this achieves higher accuracy than fully automated or fully manual reviews.

## Stage Ownership

| Stage | Agent | Developer | Notes |
|-------|-------|-----------|-------|
| 1. Language & consistency | **Leads** | Approves | Agent excels at mechanical checks |
| 2. Conceptual clarity | **Leads** | Approves | Agent identifies gaps; human validates explanations |
| 3. Relevant structure | **Leads** | Approves | Agent checks compliance; human judges exceptions |
| 4. Industry best practice | Assists | **Leads** | Agent researches; human judges relevance and fit |
| 5. Tidy up | **Leads** | Approves | Agent executes; human approves final updates |
| 6. Verify links & claims | **Leads** | Approves | Agent fetches URLs, checks sources; human decides action on failures |

## Agent Responsibilities

- Execute mechanical checks (spelling, grammar, formatting, structural compliance)
- Research industry practices via web search
- Identify potential issues and gaps
- Propose changes and wait for approval
- **Stop after each stage** - never batch multiple stages without review

## Developer Responsibilities

- Hold final authority on all changes
- Validate that suggestions align with project intent
- Make judgment calls on architectural and business logic matters
- Approve or reject proposed changes at each stage
- Provide context the agent lacks (project history, future plans, unstated constraints)

## Why This Split?

**Agent strengths:**
- Consistent application of rules (no fatigue or bias)
- Fast at pattern matching and compliance checks
- Can search and synthesize external information

**Agent limitations:**
- Lacks full project context and history
- Cannot judge "does this align with our intent?"
- May miss nuance in business logic or architectural decisions
- Context window limits understanding of large codebases
- Can fabricate plausible URLs and references that survive structural review

**Human-in-the-loop achieves 22% higher accuracy** than fully automated or fully manual approaches. The stop-after-each-stage pattern implements this.

## References

- [AI Code Review Best Practices (Qodo)](https://www.qodo.ai/blog/best-ai-code-review-tools-2026/)
- [Why AI will never replace human code review (Graphite)](https://graphite.com/blog/ai-wont-replace-human-code-review)
- [Demystifying evals for AI agents (Anthropic)](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
