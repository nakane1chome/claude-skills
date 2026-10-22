# light-v-structure

> **For human readers.** This file explains what the skill is for and how to navigate its files. The operative skill specification is in [SKILL.md](SKILL.md) — that file is primarily consumed by agents.

A lightweight V-model structure for projects developed by an agent and a single developer collaborating as a team.

## The V-model used here

Most V-model descriptions are waterfall-derived: stages complete in sequence, each gating the next. This is not that.

This skill uses the V as a **tri-axis gradient**:

```
User Problem ─────────────────────────── Working User Solution
     │              (User Journey)                │
     │                                            │
     │  Solution Proposal              Validated  │
     │  Implementation Proposal        Solution   │
     │                                            │
     │    Architecture        Validation          │
     │        Design        Test                  │
     └──────────► Implementation ◄────────────────┘
                  (Developer)
```

- **Top edge** — user journey: from problem statement to working solution
- **Left edge** — decomposition: proposal, architecture, design
- **Right edge** — integration: test, validation, user acceptance
- **Bottom** — implementation: source code, the concrete artifact

Stage boundaries are **bidirectional** — architecture informs design and design feeds back into architecture. The V shows what belongs where and what cross-validates what; it does not prescribe the order in which work happens.

This structure works with any development workflow: iterative, TDD, spike-and-stabilise, or whatever fits the increment.

## Purpose

This skill provides:

- A written record of project decisions and intent that the implementation does not capture
- Distinct stages of development with documented homes for non-implementation activity
- Documentation stored alongside code, referenceable by an agent at any stage
- Consistent increment discipline that advances a documented goal
- A shared vocabulary between developer and agent
- A research and reference tracking framework
- A traceability mechanism between requirements, architecture, design, and tests

## What this skill does not do

- Prescribe a development workflow or enforce stage-gate sequencing
- Inhibit iterative development — stage boundaries are bidirectional exchanges, not inputs-then-outputs
- Add cognitive burden or toil

## Similar methodologies

Light-V is similar in spirit to **[Spec-Driven Development](https://thebcms.com/blog/spec-driven-development)** (SDD): [GitHub Spec Kit](https://github.com/github/spec-kit), [AWS Kiro](https://kiro.dev/), [OpenSpec](https://github.com/Fission-AI/OpenSpec), and others. In both, a human states the intent up front and an agent implements it below. Light-V comes from a different lineage, though. It generalizes a [docs-as-code](https://www.writethedocs.org/guide/docs-as-code/) workflow used for embedded systems development, and it differs from SDD in three ways:

- **No tooling.** Light-V is a portable document structure and a way of working with the agent, not a CLI to adopt.
- **Traceability symmetry.** Every right-side artifact (test, validation) must verify a left-side one (design, architecture).
- **Greenfield.** It grows structure from nothing rather than retrofitting a spec onto an existing codebase.

| Dimension | Spec-Driven Development | Light-V |
|-----------|------------------------|---------|
| Form | A tool/CLI plus templates and slash commands | A portable doc structure + agent use discipline (no tooling) |
| Primary artifact | The natural-language spec (including semi-formal forms like [EARS](https://www.iaria.org/conferences2013/filesICCGI13/ICCGI_2013_Tutorial_Terzakis.pdf) or [Gherkin](https://cucumber.io/docs/gherkin/reference)) | A hierarchy of natural-language docs |
| Spec rigor | Spec-as-source, or spec-anchored code | Spec-as-source from design; spec-anchored for higher layers |
| Flow | `spec → plan → tasks → implement` (largely linear) | paradigm → ADR → architecture → design → source → test → validate (iterate) |
| Verification | "Write testable requirements" | Each right-side test verifies its left-side counterpart (design ↔ unit tests, architecture ↔ system tests) |
| Validation | Implicit: the spec is assumed to capture intent | An explicit human feedback loop at the top of the V: does the result meet the original intent? |
| Decision capture | The living spec | Architecture Decision Records (ADRs) governed by a paradigm document |
| Orientation | Often retrofitting onto existing code | Greenfield: building new ideas from scratch |

The rationale behind the split is cost. Validation (does it match intent?) is hard to make cheaper, but verification (does it match the spec?) gets cheaper with scaffolding and tests. Because cost(validation) ≫ cost(verification), the human owns the top of the V and the agent owns the bottom. Removing stage gating does not mean removing *release* gating. The accumulated record of what the system does and why supports stronger release gates.

The spec-rigor terms come from [the three levels of spec-driven development](https://www.rushis.com/spec-first-spec-anchored-spec-as-truth-the-three-levels-of-spec-driven-development/). See [sdd.md](sdd.md) for why the differences are deliberate and when to reach for which.

Further reading:

- [Spec-Driven Development: From Code to Contract in the Age of AI Coding Assistants](https://arxiv.org/abs/2602.00180) - arXiv, lightweight overview
- [How to write a good spec for AI agents](https://addyosmani.com/blog/good-spec/) - Addy Osmani
- [What Is Spec-Driven Development?](https://www.augmentcode.com/guides/what-is-spec-driven-development) - Augment Code guide
- [The Limits of Spec-Driven Development](https://isoform.ai/blog/the-limits-of-spec-driven-development) - Isoform, on SDD's failure modes
- [Building a Workflow](https://www.shincbm.com/agentic-code/2026/06/26/building-a-workflow.html) - background on how Light-V was developed and applied

## Files in this directory

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | Operative skill spec — modes, rules, steps (agent-primary) |
| [documentation.md](documentation.md) | Documentation hierarchy, folder conventions, cross-validation pairs |
| [scaffold.md](scaffold.md) | Stub templates for each file type |
| [code-structure.md](code-structure.md) | Source and test organisation conventions |
| [responsibilities.md](responsibilities.md) | Agent vs developer ownership matrix |
| [sdd.md](sdd.md) | Relationship to Spec-Driven Development |
| [glossary.md](glossary.md) | Terms used in this skill |
| [references.md](references.md) | External resources and specifications |
