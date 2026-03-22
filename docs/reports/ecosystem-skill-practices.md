# Ecosystem Skill Authoring Practices

Research report from a survey of Claude Code skill repositories listed on [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code), conducted to identify best practices for integration into the review-skill checklist.

Date: 2026-03-01

## Objective & Method

**Objective:** Identify recurring skill authoring patterns across the Claude Code ecosystem that the review-skill doesn't currently check for, and determine which are worth generalizing into new checklist items.

**Selection criteria:** ~10 repos spanning different categories (domain-specific, large collections, workflows, single-purpose, plugins), with meaningful SKILL.md files (not just CLAUDE.md instructions or hook configs).

**Inspection rubric** applied to each repo:

- Frontmatter fields used (standard and non-standard)
- Prompt structure (stages, stop pattern, Stage 0)
- Responsibility model (agent vs developer, explicit or implicit)
- Safety controls (tool restrictions, invocation control, side-effect guards)
- Argument handling (hints, validation, missing-arg behavior)
- Output specification (what artifacts, what format)
- Error/edge-case handling
- Supporting files and how they're referenced
- Novel patterns not in our current conventions

**Official baseline:** Anthropic's own documentation (Claude Code Skills docs, Platform Best Practices, official skills repo) used as ground truth for what's canonical vs. ecosystem convention.

---

## Repos Inspected

| # | Repo | Category | Stars | Summary |
|---|------|----------|-------|---------|
| 1 | [Trail of Bits Security Skills](https://github.com/trailofbits/skills) | Domain-specific | — | 34 security-focused plugins with real vulnerability discoveries |
| 2 | [Jeffallan Fullstack Dev Skills](https://github.com/Jeffallan/claude-skills) | Large collection | 4k | 66 skills across 12 categories, 357 reference files |
| 3 | [Context Engineering Kit](https://github.com/NeoLabHQ/context-engineering-kit) | Advanced | 553 | 12+ plugins organized by domain, spec-driven development |
| 4 | [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) | Plugin | 9.7k | 26 specialized agents, 4-stage cyclical workflow |
| 5 | [SuperClaude Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) | Framework | 21k | 30 commands, 16 agents, 7 behavioral modes |
| 6 | [RIPER Workflow](https://github.com/tony/claude-code-riper-5) | Workflow | 69 | 5-phase workflow with strict mode-based capability gating |
| 7 | [TACHES Claude Code Resources](https://github.com/glittercowboy/taches-cc-resources) | Collection | — | 27 commands, 9 skills, 3 agents with router architecture |
| 8 | [Web Asset Generator](https://github.com/alonw0/web-asset-generator) | Single skill | — | Favicon/icon/OG image generation with validation |
| 9 | [AB Method](https://github.com/ayoubben18/ab-method) | Workflow | — | Spec-driven workflow with mission-type classification |
| 10 | [Codex Skill](https://github.com/skills-directory/skill-codex) | Single skill | — | Delegates prompts to OpenAI Codex CLI |

**Official sources:**
- [Claude Code Skills docs](https://code.claude.com/docs/en/skills)
- [Anthropic Platform Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Anthropic official skills repo](https://github.com/anthropics/skills)

---

## Per-Repo Findings

### 1. Trail of Bits Security Skills

**Frontmatter:** Standard fields only (`name`, `description`). Gerund naming preferred (`analyzing-contracts`). No `allowed-tools` or invocation control fields observed.

**Prompt structure:** Progressive disclosure with decision trees. SKILL.md provides overview + navigation table; methodology and phases in separate files. No explicit stop-after-each-stage, but modular architecture achieves a similar effect.

**Responsibility model:** Implicit. Agent navigates decision tree and chooses audit phase; developer validates findings.

**Safety controls:** Tight. "Rationalizations to Reject" section teaches Claude to catch shortcuts and false reasoning in security analysis. Scripts must handle errors, not punt to Claude ("solve, don't punt").

**Arguments:** Uses `{baseDir}` path variables. No `argument-hint` observed.

**Output specification:** Modular markdown reports. Vulnerability findings with blast radius assessment.

**Error handling:** Explicit validation loops before destructive changes. Scripts solve problems rather than asking Claude to recover.

**Supporting files:** Domain-organized (`references/`, `workflows/`, `scripts/`). One-level-deep reference constraint from SKILL.md (documented in contribution guide). Named descriptively.

**Novel:** "Rationalizations to Reject" — an anti-pattern awareness section that teaches Claude what shortcuts to refuse. Trophy case documenting real vulnerabilities found by these skills.

---

### 2. Jeffallan Fullstack Dev Skills

**Frontmatter:** Standard fields. Context-aware activation implied through description specificity.

**Prompt structure:** ~80-line skill cores with routing tables to detailed references. Reports 50% token reduction vs. verbose skills.

**Responsibility model:** Implicit. "Expert pair programmer" positioning — agent executes, developer validates.

**Safety controls:** Context-aware activation prevents inappropriate triggers. Multi-skill orchestration ensures related expertise activates together.

**Arguments:** Keyword-based routing to reference files. "JWT authentication in NestJS" triggers NestJS skill with auth references.

**Output specification:** Varies by domain — code generation, architecture decision trees, API endpoint specs, deployment checklists.

**Error handling:** Multi-skill pipeline includes validation stages. Test Master skill integration for quality gates.

**Supporting files:** 357 reference files organized by domain. TOC headers in large files for Claude navigation. Progressive disclosure — Claude reads only what's needed.

**Novel:** "Common Ground" command surfaces hidden assumptions before work begins. Multi-skill orchestration pipeline (Feature Forge -> Architecture Designer -> Test Master -> DevOps).

---

### 3. Context Engineering Kit

**Frontmatter:** Standard fields only. Strict adherence to core Anthropic conventions.

**Prompt structure:** Stage-gated with implicit developer checkpoints. Commands are discrete (`/sdd:add-task`, `/sdd:plan`, `/sdd:implement`), each requiring deliberate invocation.

**Responsibility model:** Implicit. Agent plans and implements; developer reviews after each stage.

**Safety controls:** `disable-model-invocation: true` for high-impact operations. Commands prioritized over skills to minimize context window pollution. Quality gates in SDD workflow prevent low-quality specifications from reaching implementation.

**Arguments:** Standard `$ARGUMENTS` support. Task specifications validated against Arc42 standard before advancing.

**Output specification:** Structured specification files at `.specs/tasks/[domain]/[feature].feature.md`. Arc42-compatible format.

**Error handling:** Implicit via stages — specification phase catches requirement gaps, refinement phase catches planning issues. Reflexion plugin adds verification layer.

**Supporting files:** Progressive disclosure model. SKILL.md under 500 lines. Reference docs over 300 lines include TOC. Large specs stored in `.specs/` with path references.

**Novel:** Arc42 specification standard as contract between planning and implementation. Token-conscious design — explicit preference for commands over skills to avoid context pollution. "External memory" pattern where skill content acts as persistent knowledge base.

---

### 4. Compound Engineering Plugin

**Frontmatter:** Standard fields plus extended Claude Code fields (`context: fork`, `agent`, `hooks`, `model`, `allowed-tools`).

**Prompt structure:** Four-stage cyclical workflow: Brainstorm -> Plan -> Work -> Review -> Compound. Time allocation: 80% planning and review, 20% coding. Each stage produces artifacts that inform the next.

**Responsibility model:** Explicit. 26 specialized agents documented in AGENTS.md. Developer sets requirements, reviews stage outputs, makes decisions. 50/50 split philosophy: half time shipping features, half improving systems.

**Safety controls:** 12 parallel specialized reviewers during review phase (Security-Sentinel, Performance-Oracle, Data-Integrity-Guardian, etc.). Planning-heavy approach catches issues before code generation.

**Arguments:** Standard support. `/workflows:plan [feature description]` converts natural language to structured plans.

**Output specification:** Multi-stage artifacts with clear lineage — Plan output -> Work output -> Review output (structured feedback from 12 reviewers) -> Compound output (encoded in AGENTS.md).

**Error handling:** Hierarchical validation across all stages. Developer can halt at any stage, request modifications, restart from that point.

**Supporting files:** `AGENTS.md` as mutable system registry updated after each `/workflows:compound` invocation. Plans stored in `plans/` directory.

**Novel:** Compound methodology — each unit of work compounds into the next via AGENTS.md updates. 26-agent specialization registry. 12-parallel reviewer synthesis. Multi-platform plugin transpilation to other AI coding tools.

---

### 5. SuperClaude Framework

**Frontmatter:** Metadata-light. No rigid YAML; uses operational metadata like confidence scores and weighted criteria instead.

**Prompt structure:** Five-point assessment framework with sequential checks and early-exit gates rather than stop-after-each-stage. Designed for pre-work validation (confidence-first).

**Responsibility model:** Implicit. 16 specialized agents auto-routed by keyword triggers (`"security/auth"` -> `@agent-security`). No explicit matrix.

**Safety controls:** Behavioral rather than structural. Confidence thresholds: >= 0.90 proceed, 0.70-0.89 present alternatives, < 0.70 stop and request context. "Four Questions" anti-hallucination pattern (Are tests passing? Do deliverables meet requirements? Is everything verified? Where's the evidence?).

**Arguments:** `/sc:[command] [--modifiers] [description]` pattern. Auto-routing based on keywords when arguments are ambiguous.

**Output specification:** Varies by command — expert discussion transcripts, structured research reports with confidence scoring, code artifacts. Token efficiency mode compresses output 30-50%.

**Error handling:** Three-level confidence response. Graceful degradation — if confidence can't be established, requests explicit user guidance rather than proceeding.

**Supporting files:** `PLANNING.md` (architecture + rules), `KNOWLEDGE.md` (insights + anti-patterns), `TASK.md` (priorities). Optional MCP server integrations for extended capabilities.

**Novel:** Wave -> Checkpoint -> Wave batch execution (3.5x speedup). Confidence-first ROI ("spend 100-200 tokens to save 5,000-50,000 tokens on wrong-direction work"). PM agent as meta-layer documenting lessons across sessions.

---

### 6. RIPER Workflow

**Frontmatter:** Mode declarations as first line of every response (`[MODE: PLAN]`, `[SUBMODE: RESEARCH]`) for runtime validation.

**Prompt structure:** Five explicit phases: Research (read-only) -> Innovate (read-only) -> Plan (read + memory-write) -> Execute (full access) -> Review (read + test). Mandatory approval gate after Plan before Execute.

**Responsibility model:** Explicit via three consolidated agents: research-innovate, plan-execute, review. Universal constraints: cannot write outside assigned directories, must validate context before mode transitions.

**Safety controls:** Mode-based capability gating — each phase has specific tool access. Violation blocking with standardized message: `ACTION BLOCKED: Currently in [MODE] - this action requires [DIFFERENT_MODE]`. Review mode explicitly forbids fix attempts.

**Arguments:** `/riper:execute [step-number]` for partial execution. Missing context auto-located via git history checks.

**Output specification:** Deterministic memory bank locations: `.claude/memory-bank/[branch]/plans/[feature].md` and `reviews/[feature]-review.md`. Plans must use absolute repository paths (from `git rev-parse --show-toplevel`).

**Error handling:** Three categories: mode violation (blocking response), missing context (auto-locate via git), deviation detected (flagged with severity: critical/warning/info, no auto-fix).

**Supporting files:** `.claude/memory-bank/` for persistent session memory organized by branch. `project-info.md` as fill-in-the-blank template for project context.

**Novel:** Sub-mode duality (single agent operates in two modes to minimize context). Absolute path requirement for reproducibility across sessions. Ruthless review constraints — review mode cannot fix, only report.

---

### 7. TACHES Claude Code Resources

**Frontmatter:** Standard fields only. Descriptions are verbose (~200 chars) but specific about use case, output, and scope.

**Prompt structure:** Router architecture — SKILL.md acts as dispatcher to workflow files based on context scan and user intent. Uses XML tags (`<principle>`, `<intake>`, `<routing>`) instead of markdown headings. Context scan runs automatically on every invocation before presenting options.

**Responsibility model:** Explicit via `<user_gates>` sections specifying mandatory confirmation points. Deviation rules: auto-fix bugs, auto-add missing critical, auto-fix blockers, ask about architectural changes, log enhancements.

**Safety controls:** Context budget awareness with explicit rules: 25% remaining = mention it, 15% = pause and offer handoff, 10% = auto-create handoff and stop. Never start large operations below 15% without confirmation.

**Arguments:** Domain expertise inference with graceful degradation — detects domain from keywords, loads relevant expertise, works fine without it.

**Output specification:** Hierarchical artifacts with specific file structures and naming conventions. `PLAN.md IS the prompt` — plans are executable specifications. Lexicographic sorting with phase/plan numbering (01-01, 01-02).

**Error handling:** Handoff mechanism for context overflow (creates `.continue-here.md` with full state). No-git detection offers to initialize. Aggressive atomicity: 2-3 tasks per plan max to maintain quality.

**Supporting files:** `workflows/` (procedures), `references/` (domain knowledge), `templates/` (output structures). SKILL.md contains index sections pointing to these. Workflows specify `<required_reading>` sections listing which files to load.

**Novel:** XML tag structure instead of markdown headings for parsing clarity. Automatic deviation handling with 5 embedded rules. Context overflow handoff pattern. "Aggressive atomicity" limiting tasks per plan based on quality degradation curve.

---

### 8. Web Asset Generator

**Frontmatter:** Standard fields. Description is action-oriented and platform-specific (~220 chars).

**Prompt structure:** Task-execution model (not router-based). Quick start -> question patterns -> best practices -> validation -> common requests -> dependencies. 766 lines (over the 500-line guideline).

**Responsibility model:** Implicit. Agent asks questions, processes, runs scripts; user confirms and provides material.

**Safety controls:** Dependency validation via `check_dependencies.py`. File isolation (generated assets to `/mnt/user-data/outputs/`). Framework detection before code integration. WCAG accessibility validation built in.

**Arguments:** 8 documented AskUserQuestion patterns for structured interaction. Always uses AskUserQuestion instead of free-form text. Graceful degradation: "no" to code integration -> provides manual instructions.

**Output specification:** Explicit: generated files by type and size (favicons 16-96px, PWA icons 180-512px, social images 1200x630). Auto-generated HTML meta tags. Framework-aware code insertion.

**Error handling:** Validation as quality gate with severity levels (green/yellow/red). File size validation per platform. Dimension and aspect ratio checks. WCAG contrast ratio validation. Optional validation offer after generation.

**Supporting files:** `scripts/` (Python generators, validators, emoji utils), `references/specifications.md` (platform specs). `CLAUDE.md` for skill maintainers (not loaded during execution).

**Novel:** Question Pattern Library — 8 reusable, documented AskUserQuestion patterns. Explicit "why AskUserQuestion over plain text" rationale. Dynamic font sizing algorithm. Testing links to platform debuggers.

---

### 9. AB Method

**Frontmatter:** Implicit — metadata tracked in `.ab-method/structure/index.yaml` rather than per-skill YAML frontmatter.

**Prompt structure:** Multi-stage with explicit validation checkpoint after mission planning (Step 6 in create-mission) before execution begins.

**Responsibility model:** Explicit per mission type. Backend Architect + Backend Developer agents for backend missions. UX Expert + Frontend Developer for frontend. Research + Architecture agents for planning. Developer validates at gates.

**Safety controls:** Approval gates + audit trails via progress-tracker.md. Documentation requirement: all agent work must include "Architecture Plan" and "Files Modified" sections before status advancement.

**Arguments:** Minimal over-questioning principle: "If user provides clear requirements -> follow them exactly, don't ask unnecessary questions." Reference lookup via `index.yaml` for missing context.

**Output specification:** Structured artifacts in documented locations. Task files with progress-tracker.md. Mission documents numbered sequentially. Agent outputs in `sub-agents-outputs/` folder. Status markers (checkmark = completed, hourglass = in progress).

**Error handling:** Checkpoint-based recovery. Tasks stored with full state snapshots. Status progression guards prevent skipping phases. Blocker handling: review notes and seek clarification.

**Supporting files:** Central structure index (`index.yaml`) maps all workflows to documentation locations. Architecture docs loaded by mission type. Backend-first philosophy: frontend missions import types from completed backend work.

**Novel:** Structure Index pattern — central routing file preventing hardcoded paths. Mission Type Classification (Backend/Frontend/Planning) with delegated utils per type. Backend-first sequencing for full-stack work. Real-time status markers in documentation.

---

### 10. Codex Skill

**Frontmatter:** Plugin manifest via `plugin.json` (name, version, description, license, keywords). Minimal SKILL.md.

**Prompt structure:** Linear 4-step workflow without checkpoints: model selection -> reasoning effort -> sandbox mode -> execute. No stop pattern.

**Responsibility model:** Minimal. Agent executes Codex CLI; developer evaluates. "Treat Codex as a colleague, not an authority."

**Safety controls:** Default to read-only sandbox. Explicit permission required for `--full-auto` or `danger-full-access`. Stderr suppression by default to avoid context bloat. Non-zero exit: stop and report (no retry).

**Arguments:** Required parameters (model, reasoning_effort) with typed options. Optional parameters with sensible defaults (sandbox=read-only, thinking_tokens=suppressed).

**Output specification:** Pass-through — raw Codex CLI output. No formatting added by the skill itself.

**Error handling:** Minimal. Non-zero exit: report and stop. Knowledge cutoff disagreements: "research independently." No automatic retry.

**Supporting files:** None. Single isolated SKILL.md. Plugin manifest for distribution metadata only.

**Novel:** Parameter bundling (collect all params in one prompt to avoid sequential clarifications). Critical evaluation principle ("colleague, not authority"). Context preservation via `resume --last`. Deliberate minimal scaffolding.

---

## Official Anthropic Guidance

Key points from three official sources that go beyond basic frontmatter documentation:

### Discovery-first design
The `description` field is treated as critical infrastructure. It's the mechanism Claude uses to decide when to load a skill from potentially 100+ available. Guidance: write in third person (for system prompt injection), include specific key terms, cover both what it does AND when to use it.

### Progressive disclosure architecture
The foundational pattern. Three layers: metadata pre-loads at startup (name + description only), SKILL.md loads when relevant, referenced files load only as needed. This minimizes token cost while enabling comprehensive documentation.

### Evaluation-driven development
Build evaluations BEFORE writing extensive docs. Run Claude without the skill, document specific failures. Create 3+ scenarios testing identified gaps. Write minimal instructions to pass evaluations. Iterate based on real Claude behavior, not assumptions.

### Reference depth constraint
Reference files at most one level deep from SKILL.md. No file->file->file chains. Files over 100 lines should include a table of contents so Claude sees their full scope.

### Degrees of freedom
Match instruction specificity to the task: high freedom (text instructions) for context-dependent decisions, medium freedom (pseudocode) for preferred patterns with acceptable variation, low freedom (specific scripts) for fragile operations.

### Cross-model testing
Test with Haiku, Sonnet, and Opus. What works for Opus may need more explicit detail for Haiku. Instructions should be unambiguous enough for the smallest model tier you plan to support.

### Anti-patterns (official)
- Deeply nested file references
- Inconsistent terminology
- Time-sensitive instructions
- Vague naming (`helper`, `utils`)
- Unjustified constants in scripts
- Offering too many options without a default

---

## Pattern Tally

Cross-repo frequency of practices. "Current" indicates whether review-skill already checks for this.

| Practice | Repos | Official | Current |
|----------|-------|----------|---------|
| Description includes "when to use" | 10/10 | Yes | Checked |
| Stage-based workflow structure | 8/10 | Yes | Checked |
| Stop/checkpoint between stages | 5/10 | Yes | Checked |
| Stage 0 understanding-before-work | 5/10 | Yes | Checked |
| Tool restrictions scoped to need | 4/10 | Yes | Checked |
| Kebab-case naming | 10/10 | Yes | Checked |
| Under 500 lines | 8/10 | Yes | Checked |
| Supporting files referenced from SKILL.md | 8/10 | Yes | Checked |
| **Output format specification** | **8/10** | **Yes** | **Not checked** |
| **Error/edge-case handling** | **7/10** | **Yes** | **Not checked** |
| **Argument validation + missing-arg handling** | **6/10** | **Yes** | **Partial** |
| **One-level-deep reference constraint** | **2/10** | **Yes (explicit)** | **Not checked** |
| **Description in third person** | **1/10** | **Yes (explicit)** | **Not checked** |
| **TOC in large reference files** | **2/10** | **Yes** | **Not checked** |
| **argument-hint when using $ARGUMENTS** | **3/10** | **Yes** | **Not checked** |
| Gerund naming preference | 2/10 | Yes | Not checked |
| Structured questions (AskUserQuestion) | 3/10 | No | Not checked |
| Context budget awareness | 2/10 | No | Not checked |
| Resume/recovery mechanism | 4/10 | No | Not checked |
| Anti-pattern awareness section | 2/10 | No | Not checked |

---

## Gap Analysis

Gaps ranked by impact — frequency across repos combined with how likely the gap is to cause real problems.

### HIGH impact

**1. Output format specification** (8/10 + official)

Skills that don't specify what they produce lead to unclear or inconsistent results. Nearly every substantial repo documents output artifacts, locations, and formats. Examples: Compound Engineering defines multi-stage artifact lineage; TACHES specifies file hierarchy with naming conventions; Web Asset Generator documents exact file sizes and HTML meta tag format; RIPER uses deterministic memory bank locations.

**2. Error/edge-case handling** (7/10 + official)

Skills without error handling fail silently or behave unpredictably. The ecosystem shows several patterns: validation with severity levels (Web Asset), mode violation blocking (RIPER), confidence thresholds (SuperClaude), context overflow handoff (TACHES), checkpoint-based recovery (AB Method), "solve don't punt" scripts (Trail of Bits).

**3. Argument validation and missing-arg handling** (6/10 + official)

Review-skill currently checks whether `$ARGUMENTS` syntax is used correctly, but not whether the skill handles the case where arguments are missing, invalid, or ambiguous. Ecosystem patterns: structured question prompts (Web Asset, TACHES), graceful degradation (TACHES domain inference), "don't ask unnecessary questions" (AB Method), sensible defaults (Codex).

### MEDIUM impact

**4. One-level-deep reference constraint** (2/10 + official explicit)

Anthropic explicitly recommends that referenced files link at most one level deep from SKILL.md. Trail of Bits documents this as a contribution guideline. Deeply nested file chains cause Claude to partially read or miss content.

**5. Description in third person** (official explicit)

Descriptions are injected into the system prompt alongside other skill metadata. Third person reads naturally in that context ("Extracts text from PDFs" not "Extract text from PDFs"). Only a few ecosystem repos follow this consistently, but Anthropic's guidance is explicit.

**6. argument-hint presence** (3/10 + official)

When a skill uses `$ARGUMENTS`, the `argument-hint` field should be present to show users what to pass during autocomplete. Currently not checked.

**7. TOC in large reference files** (2/10 + official)

Anthropic recommends that reference files over 100 lines include a table of contents so Claude can see their full scope without reading every line. Jeffallan and CEK both follow this pattern.

### LOW impact

**8. Gerund naming** (2/10 + official) — Convention preference, not a functional issue. Trail of Bits and Anthropic prefer `analyzing-contracts` over `contract-analyzer`, but this repo uses noun forms consistently and it works fine.

**9. Structured questions** (3/10) — Better UX but situational. Not all skills need interactive questioning.

---

## Recommendations

### Additions to review-skill SKILL.md

**Stage 1 (Frontmatter) — 2 new checks:**
- Is `argument-hint` present when the skill uses `$ARGUMENTS`?
- Is the `description` written in third person?

**Stage 2 (Prompt structure) — 2 new checks:**
- Does the skill specify what artifacts or outputs it produces and in what format?
- Are file references at most one level deep from SKILL.md?

**Stage 3 (Effectiveness) — 3 new checks + 1 anti-pattern:**
- Does the skill handle missing or invalid arguments gracefully?
- What happens when the skill encounters an error or unexpected state?
- Do reference files over 100 lines include a table of contents?
- Anti-pattern: deeply nested file references

**Stage 5 (Summary) — 1 note:**
- Flag whether instructions are explicit enough for smaller model tiers if the skill will be used across Haiku/Sonnet/Opus.

### Additions to AUTHORING.md

Ecosystem-derived conventions to add as authoritative reference:
- Description voice (third person)
- Output specification guidance
- Reference depth constraint (one level deep)
- TOC for large reference files
- Argument hygiene (argument-hint + missing-arg handling)
- Error handling expectations

---

## Sources

### Repos inspected
- [Trail of Bits Security Skills](https://github.com/trailofbits/skills)
- [Jeffallan Fullstack Dev Skills](https://github.com/Jeffallan/claude-skills)
- [Context Engineering Kit](https://github.com/NeoLabHQ/context-engineering-kit)
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin)
- [SuperClaude Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework)
- [RIPER Workflow](https://github.com/tony/claude-code-riper-5)
- [TACHES Claude Code Resources](https://github.com/glittercowboy/taches-cc-resources)
- [Web Asset Generator](https://github.com/alonw0/web-asset-generator)
- [AB Method](https://github.com/ayoubben18/ab-method)
- [Codex Skill](https://github.com/skills-directory/skill-codex)

### Official documentation
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Anthropic Platform Skills Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Anthropic official skills repo](https://github.com/anthropics/skills)

### Aggregator
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
