# Scaffold Templates

Stub templates for each file type in the canonical project structure. Uses `%...%` for placeholder text. The agent reads these stubs when executing the `scaffold` mode and creates matching files in the project.

See [documentation.md](documentation.md) for the canonical folder structure and cross-validation pairs.

## Stub Index

| Stub | File |
|------|------|
| [docs/README.md](#-docsreadmemd) | Navigation hub |
| [docs/paradigm.md](#-docsparadigmmd) | Developer principles |
| [docs/glossary.md](#-docsglossarymd) | Terminology |
| [docs/references.md](#-docsreferencesmd) | External links |
| [docs/evaluation/README.md](#-docsevaluationreadmemd) | Evaluations index |
| [docs/adr/README.md](#-docsadrreadmemd) | ADR index |
| [docs/adr/xx-template.md](#-docsadrxx-templatemd) | ADR template |
| [docs/adr/qa.md](#-docsadrqamd) | ADR Q&A |
| [docs/arch/README.md](#-docsarchreadmemd) | Architecture index |
| [docs/arch/xx-template.md](#-docsarchxx-templatemd) | Architecture doc template |
| [docs/arch/00-principles.md](#-docsarch00-principlesmd) | Architecture principles |
| [docs/arch/01-user-archetypes.md](#-docsarch01-user-archetypesmd) | User archetypes |
| [docs/arch/02-system-archetypes.md](#-docsarch02-system-archetypesmd) | System archetypes |
| [docs/arch/03-use-cases.md](#-docsarch03-use-casesmd) | Use cases |
| [docs/arch/04-logical.md](#-docsarch04-logicalmd) | Logical architecture |
| [docs/arch/04-physical.md](#-docsarch04-physicalmd) | Physical architecture |
| [docs/arch/04-directory-structure.md](#-docsarch04-directory-structuremd) | Directory structure |
| [docs/design/README.md](#-docsdesignreadmemd) | Design index |
| [docs/design/template.md](#-docsdesigntemplatemd) | Design doc template |
| [docs/test/README.md](#-docstestreadmemd) | Test plans index |
| [docs/test/system/README.md](#-docstestsystemreadmemd) | System test plans index |
| [docs/test/unit/README.md](#-docstestunitreadmemd) | Unit test plans index |
| [docs/assets/README.md](#-docsassetsreadmemd) | Assets index |

---

## `docs/README.md`

```markdown
# Documentation

## Structure

- [paradigm.md](paradigm.md) — foundational principles
- [adr/](adr/README.md) — architecture decision records
- [arch/](arch/README.md) — system architecture
- [design/](design/README.md) — component designs
- [test/](test/README.md) — test plans

## Cross-Reference

<!-- Coverage status: ✅ Covered / ⚠️ Partial / 📝 Planned / ❌ Gap -->

| Paradigm Principle | Supporting Documents | Coverage |
|-------------------|---------------------|----------|
| % principle %     | % link %            | ✅       |
```

---

## `docs/paradigm.md`

```markdown
# Paradigm

% One-sentence description of what this project does. %

## Problem

% Why this problem needs solving — fragmentation, gaps, pain points. %

## Scope

% What this project covers and what it explicitly does not. %

## Approach

% High-level technical strategy. %

## Core Principles

Core principals form the requirements for decisions.

% List the principles that all ADRs must evaluate against. %
```

---

## `docs/glossary.md`

```markdown
# Glossary

| Term | Definition |
|------|------------|
| % term % | % definition % |
```

---

## `docs/references.md`

```markdown
# References

% Organize by category. Each entry: [Title](url) — one-line description. %
```

---

## `docs/evaluation/README.md`

```markdown
# Evaluations

Architecture and design-space research. Evaluations inform documents but are not subject to V-model traceability rules.

## Index

| Evaluation | Topic |
|------------|-------|
```

---

## `docs/adr/README.md`

```markdown
# Architecture Decision Records

Significant architectural decisions evaluated against [paradigm.md](../paradigm.md).

## Index

| ADR | Decision |
|-----|----------|

## Template

Use [xx-template.md](xx-template.md) for new ADRs.

## Review

See [qa.md](qa.md) for post-acceptance questions and challenges.
```

---

## `docs/adr/xx-template.md`

```markdown
# ADRXXXX - Title

<!-- NOT included: status, date, author — captured in git. See documentation.md Versioning and Status. -->
<!-- NOTE - this should be limited to 150 lines -->

## Context

### Problem Space Considerations

% Why this decision needs to be made in terms of constraints in building a solution. %

### Technical Considerations

% Why this decision needs to be made in terms of the technical constraints of building the system. %

## Options Considered

% Brief list with external links if available. %

#### Summary Table (when ≥2 options and requirements are defined)

| # | Requirement | Option A | Option B |
|---|-------------|----------|----------|
| 1 | % req %     | Yes      | Partial  |

## Decision

### Rationale

% Why the choice is taken. Include evaluation vs [paradigm](../paradigm.md): %

- Software Composability
- Control and Data Flow Composability
- Runtime Composability
- Re-Use of Common Interfaces
- Re-Use of Common Patterns

### Paradigm Core Principles Assessment

% For each Core Principles: ✅ Met / ⚠️ Partial / ❌ Not Met. Omit if no requirements listed. %

**Met:**
- ✅ % Requirement 1: why satisfied %

**Partial:**
- ⚠️ % Requirement N: what gap remains %

**Risk Mitigation:**
% How partial requirements will be addressed in arch/design/test. %

### Details

% Break down the concepts that must be defined as part of this choice. %

### Consequences

% Limit to direct consequences on architecture, design, and testing. %

#### Positive
- % ... %

#### Negative
- % ... %

#### Neutral
- % ... %

## See Also

% Link to relevant standards and third-party resources. %
```

---

## `docs/adr/qa.md`

```markdown
# ADR Q&A

Post-acceptance questions and challenges against ADRs. Each entry may prompt an ADR revision or a new ADR.

Agent drafts questions surfacing gaps, inconsistencies with adjacent ADRs, or concerns not visible when the ADR was written.
Developer responds inline as `(DEVELOPER: ...)`.

---

**Q1: [question about a decision or gap between ADRs]**
ADR: [link to relevant ADR]

A: [agent analysis — use ✅/⚠️/❌ where helpful]

(DEVELOPER: )

---
```

---

## `docs/arch/README.md`

```markdown
# Architecture

How [paradigm](../paradigm.md) and [ADRs](../adr/README.md) are incorporated into the system.

## Index

| Doc | Description |
|-----|-------------|
| [00](00-principles.md) | Architecture principles and inviolates |
| [01](01-user-archetypes.md) | User archetypes |
| [02](02-system-archetypes.md) | System archetypes |
| [03](03-use-cases.md) | Use cases |
| [04-logical](04-logical.md) | Logical architecture |
| [04-physical](04-physical.md) | Physical architecture |
| [04-dir](04-directory-structure.md) | Directory structure |

## Cross-validates with

- [docs/test/system/](../test/system/) - System test plans
```

---

## `docs/arch/xx-template.md`

```markdown
# Architecture Document Template

## Overview

% Brief description of what this document covers. %

## Context

% How this relates to paradigm and ADRs. %

## Details

% Main content. %

## Cross-references

- Related ADRs:
- Related architecture docs:
- Validated by: `docs/test/system/`

### ADR & Architecture principles Assessment

% For ADR: ✅ Met / ⚠️ Partial / ❌ Not Met. Omit if no requirements listed. %


```

---

---

## `docs/arch/00-principles.md`

```markdown
#Architecture Principles

The inviolable constraints and architectural model for this system. All design decisions must respect these principles.

## Principles

% List the principles that constrain the architecture. %

1. % Principle 1: statement and rationale %

## Cross-references

- Paradigm: [../paradigm.md](../paradigm.md)
- Validated by: `docs/test/system/`

### Core Principles & ADR Assessment

The Architecture Principles alone are assessed against the Core Principles in [../paradigm.md]. Following architecture and design docs are assesed against the principles in this document.

% For Core Principles & ADR: ✅ Met / ⚠️ Partial / ❌ Not Met. Omit if no requirements listed. %


```

---

## `docs/arch/01-user-archetypes.md`

```markdown
# User Archetypes

## Overview

% Who uses the system and how. %

## Context

% How user needs constrain the architecture. %

## Details

% Per-archetype: name, goals, key interactions. %

## Cross-references

- Related ADRs:
- Validated by: `docs/test/system/`
```

---

## `docs/arch/02-system-archetypes.md`

```markdown
# System Archetypes

## Overview

% The canonical structural units the system models. %

## Context

% How archetypes emerge from paradigm and ADRs. %

## Details

% Per-archetype: name, definition, key properties, examples. %

## Cross-references

- Related ADRs:
- Validated by: `docs/test/system/`
```

---

## `docs/arch/03-use-cases.md`

```markdown
# Use Cases

## Overview

Use cases must be expressed in terms of the user archetypes and system archetypes.

% What the system does — the operations it supports. %

## Context

% How use cases implement user archetypes and system archetypes. %

## Details

% Per use case: name, actor, preconditions, flow, postconditions. %

## Cross-references

- Related ADRs:
- Validated by: `docs/test/system/`
```

---

## `docs/arch/04-logical.md`

```markdown
# Logical Architecture

## Overview

% Functional components, responsibilities, interfaces, and data flows — independent of deployment. %

## Context

% How this decomposition follows from ADRs and use cases. %

## Details

% Per component: name, responsibility, key interfaces, data flows, dependencies. %

## Cross-references

- Related ADRs:
- Validated by: `docs/test/system/`
```

---

## `docs/arch/04-physical.md`

```markdown
# Physical Architecture

## Overview

% How logical components map to deployable units, modules, processes, or hardware — the structure that code and build artifacts reflect. %

## Context

% Constraints driving the physical decomposition. %

## Details

% Per unit: name, logical components it hosts, runtime dependencies, build artifact. %

## Cross-references

- Related ADRs:
- Validated by: `docs/test/system/`
```

## `docs/arch/04-directory-structure.md`

```markdown
# Directory and Module Structure

## Overview

% How source, test, and generated artifacts are organized. %

## Context

% Architectural decisions that drive the structure. %

## Details

% Folder tree with purpose annotations. %

## Cross-references

- Related ADRs:
- Validated by: `docs/test/system/`
```

---

## `docs/design/README.md`

```markdown
# Design

Component designs showing how [architecture](../arch/README.md) will be implemented.

## Index

| Component | Design |
|-----------|--------|

## Cross-validates with

- [docs/test/unit/](../test/unit/) - Unit test plans
```

---

## `docs/design/template.md`

```markdown
# Design Document Template

<!--
Design documents should be minimal:
- No source code
- No detailed function interfaces or prototypes
- Focus on what is NOT obvious from reading the code
-->

## Overview

% What component/unit this design covers. %

## Architecture Context

% How this implements the architecture. %

### Assessment against Architecture core princlple

[../arch/00-principles.md]

## Design

% Key design decisions — what's not obvious from the code. %

## Interfaces

% How this component interfaces with others. %

## Cross-references

- Architecture doc: `docs/arch/`
- Validated by: `docs/test/unit/`
```

---

## `docs/test/README.md`

```markdown
# Test Plans

Test plans describing the "Why?" of tests — not test steps or code.

## Structure

- [system/](system/) - System tests validating architecture
- [unit/](unit/) - Unit tests validating design

## Index

| Plan | Validates |
|------|-----------|
```

---

## `docs/test/system/README.md`

```markdown
# System Test Plans

Test plans for system-level validation against [architecture](../../arch/README.md).

Organized by use cases and system archetypes.

## Index

| Test Plan | Defines |
|-----------|---------|
```

---

## `docs/test/unit/README.md`

```markdown
# Unit Test Plans

Test plans for unit-level validation against [design](../../design/README.md).

## Index

| Test Plan | Defines |
|-----------|---------|
```

---

## `docs/assets/README.md`

```markdown
# Assets

Visual artifacts: diagrams, drawio source files, SVGs.

| File | Description |
|------|-------------|
```
