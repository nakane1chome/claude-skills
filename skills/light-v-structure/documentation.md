# Documentation Structure

Design documentation is in the `docs/` folder. This is to be maintained as part of the code, and is just as important as the code and the tests.

## Contents

- [V-Model to Documentation Mapping](#v-model-to-documentation-mapping)
  - [Cross-Validation Pairs](#cross-validation-pairs)
  - [Sideband Model](#sideband-model)
- [Folder Structure](#folder-structure)
  - [Supporting Files](#supporting-files)
- [Versioning and Status](#versioning-and-status)
- [Document Types](#document-types)
  - [Paradigm](#paradigm-docsparadigmmd)
  - [Sideband Documents](#sideband-documents)
    - [Architecture Decision Records](#architecture-decision-records-docsadr)
    - [Evaluation Research](#evaluation-research-docsevaluation)
  - [V-Model Levels](#v-model-levels)
    - [Architecture](#architecture-docsarch)
    - [Design](#design-docsdesign)
    - [Test Plans](#test-plans-docstest)

## V-Model to Documentation Mapping

```
    SIDEBAND                            LEFT (Decomposition)                    RIGHT (Integration)

Project Initialization                                                    Project Completion
        │                                                                                 ▲
        ▼                                                                                 │
   paradigm.md                                                                            │
        │                                                                                 │
        ├───────────────────────────────────●──────────────────────────────────────────── ●
        │                                   │                                             ▲
        ▼                                   ▼                                             │
  docs/adr/* ──────────────►●◄──────► Developer ◄─────────────────────────────────────► User Validation
        ▲                   │               │                                             ▲
        │                   │               ▼                                             │
        │                   ● ◄──────► docs/arch/* ◄──────── validates ──────────► docs/test/system/*
  docs/adr/qa.md ◄──────────●               │                                             ▲
                            │               │                                             │
                            ● ◄──────► docs/design/* ◄──────validates─────────► docs/test/unit/*
  docs/evaluation/* ◄──────►●               │                                             ▲
                                            ▼                                             │
                                          src/* ◄────────────verifies ────────────────► test/*
```

### Cross-Validation Pairs

| Left Side (What) | Right Side (Validates) | Checkpoint |
|------------------|------------------------|------------|
| Developer intent | User accepts solution | Release |
| `docs/arch/*` | `docs/test/system/*` | System test pass |
| `docs/design/*` | `docs/test/unit/*` | Unit test pass |
| `src/*` | `test/*` | All tests pass |

**Exempt from traceability:** Evaluation docs (`docs/evaluation/`) have no required right-side counterpart. Cross-cutting constraint docs (coding standards, format specs) do not require matching unit test plans. Infrastructure/tooling commits and hot-fix sprints do not require design-doc updates unless they reveal an architectural gap.

### Sideband Model

The sideband is a parallel track that runs alongside the V. It provides the research context and decision record that supports the V's documents without belonging to any single V level and without being subject to V-model traceability rules.

**Why it exists.** Some information doesn't fit a single level — research that informed three decisions, or an architectural decision that constrained both arch and design simultaneously. The sideband holds this cross-cutting material. It short-circuits into the V at the relevant junction. The connections are bidirectional — the V also informs sideband updates as implementation reveals new information.

**Initialization.** `paradigm.md` initializes the project and connects directly to the Developer position at the top of the V and to the sideband.

**Checkpoint.** The sideband has its own right-side output: `docs/adr/qa.md` reviews ADRs post-acceptance. Evaluation documents are validated against industry knowledge and general understanding — not by a test suite. ADRs are the actionable output of the sideband; evaluation is the evidence base behind them.

| Sideband Document | Evaluated Against | Checkpoint |
|-------------------|-------------------|------------|
| `docs/adr/*.md` | `docs/*paradigm*.md` | `docs/adr/qa.md` |
| `docs/evaluation/*.md` | Industry and general knowledge | Referenced by all documents that used them |

## Folder Structure

```
docs/
├── README.md                      # Navigation hub and cross-reference matrix
├── *paradigm*.md                  # Developer's principles (proxy for developer)
├── glossary.md                    # Project terminology
├── references.md                  # External links and specs
├── <other docs>.md                # Other documents, such as PoC information
│
├── assets/                        # Visual artifacts (diagrams, drawio, SVGs) — optional
│
├── evaluation/                    # Supporting research (no right-side counterpart)
│   ├── README.md                  # Index of evaluations
│   └── NN-<topic>.md              # Per-topic evaluation
│
├── adr/                           # Architecture Decision Records
│   ├── README.md                  # Index of ADRs
│   ├── xx-template.md             # ADR template
│   ├── 01-<decision-name>.md      # Numbered decisions
│   └── 02-<decision-name>.md      # ...
│
├── arch/                          # System architecture
│   ├── README.md                  # Index
│   ├── xx-template.md             # Architecture doc template
│   ├── 00-principles.md           # The architecture model and inviolates
│   ├── 01-user-archetypes.md      # Who uses the system
│   ├── 02-system-archetypes.md    # What the system is
│   ├── 03-use-cases.md            # What the system does, written using the user and system archetypes
│   ├── 04-logical.md              # Functional components, responsibilities, interfaces, and data flows — independent of deployment
│   ├── 04-physical.md             # How logical components map to deployable units, modules, and hardware
│   └── 04-directory-structure.md  # Source and test directory layout
│
├── design/                        # Component designs
│   ├── README.md                  # Index
│   ├── template.md                # Design doc template
│   ├── 01-coding-style.md         # Coding style guidelines
│   └── <component-name>.md        # Per-component design
│
└── test/                          # Test plans (not test code)
    ├── README.md                  # Index
    ├── system/                    # System test plans
    │   └── <use-case>.md          # Per use-case test plan
    └── unit/                      # Unit test plans
        └── <component>.md         # Per-component test plan
```

Note: *paradigm*.md may be a single document or many. It may have other names.

### Supporting Files

Each folder should contain a `README.md` (index of documents) and a `template.md` (common format for docs in that folder, where applicable).

Cross-cutting files at the `docs/` root:

- `docs/README.md` — Navigation hub linking to all doc sections; may include a cross-reference matrix mapping paradigm principles to supporting documents with coverage status (✅/⚠️/📝).
- `docs/glossary.md` — Terms that need clarification.
- `docs/references.md` — Third-party specifications, projects, etc. Projects with binary reference materials (PDFs, specs) may use a `references/` folder alongside or instead of `references.md`.
- `docs/assets/` — Visual artifacts: diagrams, drawio source files, SVGs. No required structure; add a `README.md` index if the folder grows large.

**`CLAUDE.md`** is a valid location for agent-operational guidance: build commands, sandbox setup, dev record rules, and quick-reference conventions. It is **not** a substitute for design-level documentation. Conventions in CLAUDE.md that constrain implementation (API contracts, error handling patterns, validation rules) should have corresponding entries in `docs/design/`.

## Versioning and Status

Documents should **not** include:
- Explicit version numbers or revision history (use git)
- Metadata blocks with dates, authors, or change logs (use git)
- Status fields like "Draft", "Approved", "Final" (use the V-model)
- `Status:` fields in ADRs (Proposed/Accepted/Superseded) — whether a decision is active is tracked by git history and superseding ADRs, not by a field in the document

The prohibition covers metadata that git captures. Semantic/alignment metadata not in git is **allowed**: cross-document coverage status, paradigm alignment indicators, and planning status in cross-reference matrices (e.g. ✅ Covered / ⚠️ Partial / 📝 Planned in `docs/README.md`).

Reason: Git already tracks who changed what and when. Adding metadata to documents creates toil.

**Approval is validation**: A document is "approved" when its corresponding right-side V-model activity succeeds. Architecture is approved when validated. Design is approved when tested. The goal is reaching the right side of the V as quickly as possible, not accumulating sign-offs.

## Document Types

The developer is the ultimate authority. Every document in this structure is a proxy capturing developer intent so it doesn't need to be repeated in every conversation. The agent takes guidance from these documents, but the developer can always override — when documents conflict with developer direction, the developer wins.

### Paradigm (`docs/*paradigm*.md`)

A persistent capture of the developer's strong opinions and foundational principles — the rationale for this project and the constraints all decisions must respect. The developer shouldn't need to repeat core beliefs in every session; this document encodes that intent and makes it available to every subsequent stage.

- Very opinionated (that's the point)
- Changes rarely
- All ADRs must evaluate against this
- **Not** the ultimate authority — the developer is

Projects with multiple distinct stakeholder concerns may use multiple paradigm files. Named variants are valid when the concerns are genuinely separate; the default is a single `paradigm.md`.

### Sideband Documents

See [Sideband Model](#sideband-model) in the mapping section for the structural description. Sideband documents short-circuit into the V without being V levels — they are not subject to cross-validation traceability rules and have their own internal checkpoint mechanism.

#### Architecture Decision Records (`docs/adr/`)

Significant architectural decisions evaluated against the paradigm.

Each ADR contains:
- Context (problem space and technical considerations)
- Options considered
- Decision and rationale (evaluated vs paradigm)
- Consequences: Positive / Negative / Neutral (what must be captured in arch/design/test)

When an ADR evaluates multiple options, the Context should list numbered Technical Requirements and the Decision should include a **Paradigm Assessment** — explicitly marking each requirement as Met ✅ / Partial ⚠️ / Not Met ❌. An option comparison summary table (rows = requirements, columns = options) placed before the option prose makes the tradeoff legible at a glance.

Use template `docs/adr/xx-template.md`. Name as `NN-<short-description>.md` (e.g., `01-data-model-language.md`).

These are opinionated. The developer drafts the rationale and decision — the agent applies the template and uses document editing skills to flesh out and refine.

**Q&A (`docs/adr/qa.md`):** Post-acceptance review instrument. The agent drafts numbered questions surfacing gaps, inconsistencies with adjacent ADRs, or concerns not visible when the ADR was written. Developer responds inline as `(DEVELOPER: ...)`. Unresolved entries feed ADR amendments or new ADRs. This is the sideband's right-side output — the mechanism for closing the loop on architectural decisions.

#### Evaluation Research (`docs/evaluation/`)

Empirical and comparative research supporting any V level. Evaluation documents survey alternatives, assess tradeoffs, and gather evidence before a decision is committed. Update them as implementation reveals new information.

- Not subject to V-model traceability rules — no required right-side counterpart
- Should be referenced by any documents that used them in their decision rationale
- Use evaluation reports to avoid unnecessary detail in ADR, arch, and design docs
- Numbering: `NN-<topic>.md` (e.g., `01-data-model-options.md`)

### V-Model Levels

#### Architecture (`docs/arch/`)

How the paradigm, ADRs, and developer intent are incorporated into the system.

Must include:
- Core principles (the architecture model and inviolates)
- User archetypes (who uses the system)
- System archetypes (what the system is)
- Use cases (what the system does)

For larger projects, also include:
- Detailed requirements
- Architectural characteristics (NFRs — Non-Functional Requirements)

Optional depending on complexity:
- Logical architecture: Functional components, responsibilities, interfaces, and data flows — independent of deployment
- Physical architecture: How logical components map to deployable units, modules, processes, or hardware — the structure that code and build artifacts reflect.

Cross-validates with: `docs/test/system/*`

#### Design (`docs/design/`)

How architecture will be implemented per component.

Design documents should be **minimal**:
- Focus on what is NOT obvious from reading the code
    - No source code
    - No detailed function interfaces or prototypes
- Explain how code meets architecture and interfaces to other units

Naming: `<component-name>.md` matching source structure. Cross-cutting design docs (coding style, format conventions) may live alongside component designs — name them to distinguish (e.g., `01-coding-style.md`).

Design components reflect and define the physical architecture — even when no explicit physical architecture doc exists. For simple projects where logical and physical architecture coincide, a separate physical architecture doc may not be needed.

Cross-validates with: `docs/test/unit/*`

#### Test Plans (`docs/test/`)

How implementation validates against architecture and design.

Test plans should **never** include:
- Test steps or procedures
- Test source code (mock classes, fixtures, helper implementations)
- Expected results or output values

Test plans should **always** describe:
- The "Why?" of each test
- How tests ensure earlier-stage documents are met
- System tests → validate architecture
- Unit tests → validate design

Split into:
- `system/` — Use case and archetype focused
- `unit/` — Component focused, mirrors source hierarchy
