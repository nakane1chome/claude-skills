# Light-V and Spec-Driven Development

How this skill relates to **Spec-Driven Development (SDD)** — the mainstream 2026 movement for agentic coding — and why its differences are deliberate.

## What SDD is

Spec-Driven Development treats the specification as the primary artifact and code as its build output: the spec is written, reviewed, and kept as living ground truth, and an agent generates code from it. By 2026 it ships as a tool for every editor — GitHub Spec Kit, AWS Kiro, OpenSpec, BMAD, Tessl, and others — typically as a CLI plus templates and slash commands that drive a `spec → plan → tasks → implement` flow.

Light-V reaches a similar goal (human intent up front, agent implementation below) from a systems-engineering lineage rather than a web-development one. The two are siblings, not rivals — but they differ in form and emphasis.

## Points of difference

| Dimension | Spec-Driven Development | Light-V |
|-----------|------------------------|---------|
| Form | A tool/CLI plus templates and slash commands | A portable doc structure + always-on agent discipline (no tooling) |
| Primary artifact | The natural-language spec; code is the build output | A hierarchy: paradigm → ADR → architecture → design → test → source |
| Flow | `spec → plan → tasks → implement` (largely linear) | Bidirectional tri-axis gradient, explicitly not stage-gated |
| Verification | "Write testable requirements" | V&V traceability, audited — every right-side artifact must validate a left-side one |
| Decision capture | The living spec | Architecture Decision Records (ADRs) governed by a paradigm document |
| Orientation | Often retrofitting onto an existing codebase | Greenfield — building new ideas from scratch |
| Decomposition | A flat spec authored by a human | Two-speed: human-dominated top of the V, agent-dominated bottom |

## Why the differences are deliberate

Three distinctions are the point of Light-V, not incidental:

1. **No tooling.** Light-V is a structure and a discipline, not an executable. It is portable across any agent and carries no vendor lock-in. There is no CLI to adopt — only conventions to follow (see [documentation.md](documentation.md)) and an always-active planning mode (see [SKILL.md](SKILL.md)).
2. **Traceability-first.** The V-model's signature is that the right side *validates* the left: tests verify design, validation verifies architecture. The `check` mode audits these pairs as a first-class activity. Most SDD pipelines assert "testable requirements" but do not systematically pair and audit verification against decisions.
3. **Greenfield.** Light-V is built to grow structure from nothing. When an upstream document is missing it bootstraps one rather than assuming an existing spec; it suits building a new idea from scratch more than retrofitting a spec onto code that already exists.

## When to reach for which

- Use **SDD tooling** when working inside a supported editor on feature work where a natural-language spec and a linear generate-and-iterate loop are enough.
- Use **Light-V** when the work needs a durable document hierarchy, auditable V&V traceability, and decision memory (ADRs) — especially when bootstrapping a new system from scratch, or when the project mixes software and formal system models.

The two can coexist: an SDD spec can serve as a Light-V proposal or architecture artifact, provided its right-side counterpart (test or validation) is created and traced.

## References

- [Spec-Driven Development: The Definitive 2026 Guide](https://thebcms.com/blog/spec-driven-development) - BCMS overview of SDD
- [GitHub Spec Kit](https://github.com/github/spec-kit) - Reference SDD toolkit and CLI
- [What Is Spec-Driven Development?](https://www.augmentcode.com/guides/what-is-spec-driven-development) - Augment Code guide
