# Review-Skill Responsibilities

This skill reviews and fixes other skills. The agent checks against conventions and best practices; the developer approves fixes before they're applied.

## Stage Ownership

| Stage | Agent | Developer | Notes |
|-------|-------|-----------|-------|
| 0. Read and understand | Proposes | **Confirms** | Agent must understand the skill before reviewing |
| 1. Frontmatter review | **Reviews and fixes** | Approves | Agent checks conventions; developer approves changes |
| 2. Prompt structure review | **Reviews and fixes** | Approves | Agent checks structure; developer approves changes |
| 3. Effectiveness review | **Reviews and fixes** | Approves | Agent checks practical issues; developer approves changes |
| 4. Alignment review | **Reviews and fixes** | Approves | Agent checks repo consistency; developer approves changes |
| 5. Summary and recommendations | **Leads** | Decides | Agent summarizes; developer decides next steps |

**Stage 0 is critical**: The agent must understand what the skill does and how it's intended to work before reviewing. A finding may be valid convention-wise but wrong for the skill's purpose.

## Agent Responsibilities

- **Understand before reviewing** — confirm the skill's intent at Stage 0
- Be specific — "frontmatter is wrong" is unhelpful; "`name` is camelCase, should be kebab-case" is useful
- Report findings as pass / issue / suggestion before fixing
- Apply fixes only after developer approval
- Stop after each stage for review
- Reference `AUTHORING.md` conventions when available

## Developer Responsibilities

- Confirm the agent understood the skill's purpose
- Judge which findings matter and which are acceptable tradeoffs
- Approve or reject proposed fixes at each stage
- Provide context the agent may lack (intended audience, constraints, etc.)
- Final authority on what the skill should do

## Why This Split?

**Agent strengths:**
- Pattern matching against conventions and checklists
- Spotting inconsistencies across files
- Checking completeness systematically
- Applying mechanical fixes (formatting, field names)

**Agent limitations:**
- May not understand why a convention was broken intentionally
- Lacks context on the skill author's constraints
- May over-standardize, removing intentional variation
- Can miss domain-specific requirements

**The critical handoff**: Stage 0 -> Stage 1. If the agent misunderstands the skill's purpose, review findings may be misguided.
