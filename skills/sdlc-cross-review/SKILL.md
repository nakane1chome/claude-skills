---
name: sdlc-cross-review
description: Review a document against its SDLC lifecycle context — assess completeness and check consistency with parent documents in the document hierarchy.
---

Review the target document against its SDLC lifecycle context.

**Stop after each stage and have changes reviewed with user.**

> **Note**: The developer holds final authority for judgment calls in both stages. Discuss scope and approach before making changes.

1. **Assess completeness**
   - Is this a skeleton that needs **fleshing out**, or a draft that needs **polishing**?
   - Skeletons need generative work (structure, diagrams, missing sections) — pause and discuss scope with developer
   - Drafts can proceed to review and refinement
   - If fleshing out is needed, that's a different task than review — agree on approach before continuing

2. **Identify the document's position in the hierarchy**
   - Determine where the target document sits in the project's SDLC structure
   - Identify the parent document(s) that constrain this document (left side, decomposition)
   - Identify the corresponding validation artifact (right side, integration)
   - If the project defines its own hierarchy, use that; otherwise ask the developer to clarify

3. **Review vs parent document**
   - Check that the target document is consistent with decisions and constraints in its parent(s)
   - Flag any contradictions or gaps between the target and its parent documents
   - Verify that the target document traces back to requirements or decisions in the parent

4. **Cross-validate against the right side**
   - Identify the validation pair for this document
   - Check that validation artifacts exist and cover what the document specifies
   - Flag anything specified in the document that has no corresponding validation

## V-Model Context

The [V-model](https://en.wikipedia.org/wiki/V-model_(software_development)) pairs each definition stage with a corresponding testing stage. The left side decomposes requirements; the right side validates them. Each level on the right validates the corresponding level on the left.

```
Requirements Analysis ◄──────────────────► Acceptance Testing
     │                                              ▲
     │ constrains                                   │ validates
     ▼                                              │
System Design ◄────────────────────────────► System Testing
     │                                              ▲
     │ constrains                                   │ validates
     ▼                                              │
Architecture Design ◄──────────────────────► Integration Testing
     │                                              ▲
     │ constrains                                   │ validates
     ▼                                              │
Module Design ◄────────────────────────────► Unit Testing
     │                                              ▲
     │ constrains                                   │ validates
     ▼                                              │
              Implementation
```

### Standard Cross-Validation Pairs

| Left Side (Definition) | Right Side (Validation) |
|------------------------|-------------------------|
| Requirements analysis | Acceptance testing |
| System design | System testing |
| Architecture design | Integration testing |
| Module design | Unit testing |

Not every project will use all levels. Identify which levels the project uses and apply the relevant checks.

## References

- [V-model (software development) - Wikipedia](https://en.wikipedia.org/wiki/V-model_(software_development))
- [The V-model explained - IAPM](https://www.iapm.net/en/blog/v-model/)
- [What Is the V-Model in Software Development? - Built In](https://builtin.com/software-engineering-perspectives/v-model)
