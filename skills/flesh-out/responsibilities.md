# Flesh-Out Responsibilities

This skill transforms raw content into structured documents. The developer's crude notes capture intent; the agent expands without distorting.

## Stage Ownership

| Stage | Agent | Developer | Notes |
|-------|-------|-----------|-------|
| 0. Extract core ideas | Assists | **Leads** | Agent interprets; developer confirms understanding |
| 1. Research and expand | **Leads** | Approves | Agent researches; developer decides what to include |
| 2. Structure content | **Leads** | Approves | Agent proposes structure; developer validates |
| 3. Polish language | **Leads** | Approves | Mechanical - agent excels here |
| 4. Tidy up | **Leads** | Approves | Agent executes; developer approves |

**Stage 0 is critical**: The agent must confirm it understands the developer's intent before expanding. Raw notes are ambiguous - assumptions compound into wrong directions.

## Agent Responsibilities

- **Preserve developer intent** - raw content is the source of truth for meaning
- Research and propose expansions, but don't assume inclusion
- Structure logically without changing what the developer meant
- Ask when uncertain - "Did you mean X or Y?"
- Stop after each stage for approval

## Developer Responsibilities

- Confirm the agent understood your raw notes correctly
- Approve or redirect expansions before they're written
- Provide context not captured in the notes
- Override structure decisions when they don't fit intent
- Final authority on what the document should say

## Why This Split?

**Agent strengths:**
- Research and synthesis
- Structuring content logically
- Consistent formatting and optimization
- Polishing language

**Agent limitations:**
- Cannot know what the developer *meant* to write
- May over-expand or under-expand based on misunderstanding
- Lacks context on why certain ideas were included
- May impose structure that doesn't fit the content

**The critical handoff**: Stage 0 -> Stage 1. If the agent misunderstands intent, everything that follows is wrong. Confirm understanding before expanding.

## Difference from Review

| Aspect | review-steps | flesh-out |
|--------|--------------|-----------|
| Input | Draft with structure | Raw notes/skeleton |
| Work type | Corrective | Generative |
| Risk | Polish errors | Meaning distortion |
| Critical stage | Stage 0 (is it complete?) | Stage 0 (do I understand?) |
