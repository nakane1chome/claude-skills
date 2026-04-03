---
name: generator-coding
description: Template-based code generation pattern using data models, templates, and helper functions to generate repetitive interface code.
---

# Template-Based Code Generation

Three inputs produce repetitive (typically interface) code:

- **Data model**: Standardized representation -- XML, Domain-Specific Language (DSL), or schema-enforced JSON/YAML.
- **Template**: Templating meta-language markup ([Jinja2](https://jinja.palletsprojects.com/), [ERB](https://docs.ruby-lang.org/en/master/ERB.html), etc.).
- **Helper functions**: Functions that reshape the data model for template consumption.

```
Data Model ──► Parser ──► Helpers ──► Template Engine ──► Generated Output
   (SVD,         (cmsis-svd,   (reshape,    (Jinja2,        (one file per
    IDL,          sqlparse)     filter)      ERB)            generation unit)
    DBML...)
```


## Terms

| Term | Definition |
|------|-----------|
| **Data Model** | Input describing the structure to replicate (e.g. SVD file for hardware registers). |
| **Helpers/Plugins** | Functions that transform/filter/restructure the data model for templates. |
| **Template(s)** | Defines output structure in the target language with template markup for variable parts. |
| **Target Language** | Language of the generated output (e.g. C++, Python, Verilog). |
| **Generated Output** | Files produced by the generator. Must never be hand-edited (see: Rules). |
| **Generation Unit** | Data model component a template operates on (e.g. peripheral, table, message). One output file per unit (see: Step 3). |
| **Data Bridge Template** | Template converting the data model into target-language compile-time representations (enums, constants, macros). Consumed by in-language meta-programming (see: Meta-Programming Rules). |


## Generator Types

| Type | Description | Template Location | Flexibility |
|------|-------------|-------------------|-------------|
| **Fixed function** | Template embedded in generator tool code | Inside the tool | Output format fixed; change requires modifying the tool |
| **Customizable template-based** | Template separated from tool | User-editable files | User can modify/replace templates freely |

**Directive**: Prefer customizable template-based generators for agent use. The agent can read, understand, and modify templates without understanding the tool's internals.


## Meta-Programming

| Type | Mechanism | When to use |
|------|-----------|-------------|
| **In-language** | C++ templates/`constexpr`/`consteval`, C preprocessor, Python decorators, Verilog `generate` | Data can be represented in target language compile-time constructs |
| **External template-based** | Jinja2/ERB generating source files | Data cannot be naturally represented in target language (e.g. register maps, protocol definitions) |

**Directive**: Prefer in-language meta-programming -- the target toolchain handles validation, error reporting, and IDE support. Combine with external generation using the layered approach (see: Meta-Programming Rules).


## Examples

### Generator Tools

| Tool | Type | Templating | Domain |
|------|------|-----------|--------|
| [Protobuf](https://protobuf.dev/) (`protoc`) | Fixed | Embedded | Serialization / RPC |
| [Cyclone DDS](https://cyclonedds.io/) (`idlc`) | Fixed | Embedded | DDS/OMG IDL interfaces |
| [SWIG](https://www.swig.org/) | Fixed | Embedded | Foreign Function Interface (FFI) wrappers |
| [Ruby on Rails](https://guides.rubyonrails.org/generators.html) | Template | ERB | Web scaffolding |
| [Cookiecutter](https://www.cookiecutter.io/) | Template | Jinja2 | Project scaffolding |
| [development-utils](https://github.com/nakane1chome/development-utils) | Template | Jinja2 | Hardware description (SVD, SystemRDL, DBML, Device Tree, IDL) |

### Data Model Formats

| Format | Domain | Type |
|--------|--------|------|
| SQL DDL | Databases | Data exchange |
| XML ([SVD](https://www.keil.com/pack/doc/CMSIS/SVD/html/index.html), ATML) | Hardware, general | Data exchange |
| JSON / YAML / TOML | General (schema required) | Data exchange |
| [IDL](https://www.omg.org/spec/IDL/) (Interface Definition Language) | Distributed systems (CORBA, DDS, Protobuf) | DSL |
| [SystemRDL](https://www.accellera.org/downloads/standards/systemrdl) | Register descriptions | DSL |
| [DBML](https://dbml.dbdiagram.io/) (Database Markup Language) | Database schemas | DSL |
| [AADL](https://www.aadl.info/) (Architecture Analysis and Design Language) | Safety-critical systems | DSL |
| [SysML](https://sysml.org/) | Systems modeling | DSL |
| [Device Tree](https://www.devicetree.org/) | Linux/embedded hardware | DSL |

### Templating Languages

| Language | Ecosystem | Logic | Strengths |
|----------|-----------|-------|-----------|
| [Jinja2](https://jinja.palletsprojects.com/) | Python | Full (loops, macros, filters) | Most expressive; `StrictUndefined`; dominant for standalone generators |
| [ERB](https://docs.ruby-lang.org/en/master/ERB.html) | Ruby | Full Ruby execution | Native to Rails |
| [Liquid](https://shopify.github.io/liquid/) | Ruby | Safe subset | Sandboxed; safe for user-supplied templates |
| [Mako](https://www.makotemplates.org/) | Python | Full Python execution | Fast; used by Alembic |
| [Mustache](https://mustache.github.io/)/[Handlebars](https://handlebarsjs.com/) | Language-agnostic | Logic-less | Forces logic into helpers |


## Process

### Step 1: Identify the Data Model

Use the user's existing data model. If none exists, select a domain standard:

| Domain | Standard formats |
|--------|-----------------|
| Hardware registers | SVD, SystemRDL, [IP-XACT](https://www.accellera.org/downloads/standards/ip-xact) (IEEE 1685) |
| Communication protocols | Protobuf, IDL, [ASN.1](https://www.itu.int/en/ITU-T/asn1/Pages/introduction.aspx) |
| Database schemas | SQL DDL, DBML |
| APIs | [OpenAPI](https://www.openapis.org/)/Swagger, [GraphQL](https://graphql.org/) |
| Hardware architecture | Device Tree, AADL |

### Step 2: Understand the Interface Boundary

Identify the specification-defined interface:

| Boundary | Examples |
|----------|---------|
| Persistent data | Database tables, file formats |
| Inter-Process Communication (IPC) | Shared memory, message queues, pub/sub |
| Hardware/software | Memory-Mapped I/O (MMIO) registers, Direct Memory Access (DMA) descriptors |
| Language interop | Java Native Interface (JNI), Python C extensions, FFI |
| Network protocols | RPC definitions, serialization formats |

### Step 3: Determine the Generation Granularity

| Granularity | Scope | Use case |
|-------------|-------|----------|
| **Component-level** | One output file per generation unit (peripheral, message, table) | Direct usage patterns; simpler templates |
| **System-level** | One output file covering all components | Cross-cutting concerns (dispatch tables, device maps, schema migrations) |

Split templates by granularity. A single system-wide template that includes all components is difficult to maintain.

### Step 4: Template Output Conventions

| Convention | Pattern | Example |
|------------|---------|---------|
| **Template naming** | `<generation_unit>_<output_name>.<target_ext>.jinja2` | `peripheral_regs.hpp.jinja2`, `table_model.py.jinja2` |
| **Output directory** | Separate from hand-written source: `generated/`, `gen/`, `build/gen/` | Never mix generated and hand-written files |
| **Version control** | Add output directories to `.gitignore` | Exception: version output if users lack the generator toolchain |

### Step 5: Write the Generator Pipeline

| Stage | Responsibility | Notes |
|-------|---------------|-------|
| **Parser** | Read and validate data model; produce in-memory representation | Reuse open-source parsers: [`cmsis-svd`](https://github.com/cmsis-svd/cmsis-svd), [`systemrdl-compiler`](https://github.com/SystemRDL/systemrdl-compiler), [`sqlparse`](https://github.com/andialbrecht/sqlparse). Custom parser = last resort. |
| **Helpers** | Reshape/filter parsed data for template consumption | Keep logic out of templates |
| **Templates** | Emit target-language constructs; read like target source code | Minimal control flow; iterate over data |
| **Driver script** | Connect parser + helpers + templates; write output files | Script or Makefile target |


## Rules for Using Generators

| # | Rule | Detail |
|---|------|--------|
| 1 | **Never edit generated output** | Fix the data model, template, or helper instead. If output is wrong, fix the input. |
| 2 | **Interface changes go in the data model** | New field/register/message = modify the data model source, not the template. |
| 3 | **Data reshaping goes in helpers** | Filtering, renaming, restructuring = helper functions. Keep templates simple. |
| 4 | **Templates read like target source code** | Template markup (`{% for %}`, `{{ }}`) is a thin layer over recognizable target code. |
| 5 | **Control whitespace explicitly** | Jinja2: enable `trim_blocks` + `lstrip_blocks`. Use `{%-`/`-%}` for fine-grained control. Verify output formatting. |
| 6 | **One concern per template** | Each template produces one logical output artifact. |


## Rules for Meta-Programming with Generators

When combining external generation with in-language meta-programming:

| # | Rule | Detail |
|---|------|--------|
| 1 | **Prefer target-language mechanisms** | C++ `constexpr`/`consteval`, Python metaclasses, Verilog `generate`, C macros. |
| 2 | **Data bridge template** | One template converts data model to target-language compile-time data (enums, constants, `constexpr` arrays). |
| 3 | **Separate runtime templates** | Consume compile-time data via target-language meta-programming (e.g. C++ template class parameterized by generated enum). |
| 4 | **Layering principle** | External generation = data declarations. In-language meta-programming = behavior. Each layer independently testable. |


## Testing Generators

| Strategy | What it catches | How |
|----------|----------------|-----|
| **Golden-file tests** | Unintended output changes | Store known-good output as reference; diff against current output |
| **Compilation tests** | Syntax errors, type mismatches | Compile (or lint) generated output after generation |
| **Round-trip tests** | Semantic correctness | Verify generated code represents the data model correctly (e.g. register access returns expected values) |
| **Sample data models** | Template edge cases | Maintain small test data exercising all control flow paths (optional fields, empty lists, single-element lists) |


## Build System Integration

| Concern | Approach |
|---------|----------|
| **Dependency tracking** | Makefile/script declares deps on data model + templates + helpers. Any input change triggers regeneration. |
| **Makefile pattern** | `generated/%.hpp: data/%.xml templates/peripheral_regs.hpp.jinja2 helpers.py` |
| **Incremental generation** | For large data models, regenerate only changed generation units. |
| **CI verification** | Run generator in CI; verify checked-in output (if versioned) matches generator output. |


## Post-Generation Hooks

| Hook | Purpose | Example |
|------|---------|---------|
| **Code formatters** | Match project style without burdening templates | [`clang-format`](https://clang.llvm.org/docs/ClangFormat.html) (C/C++), [`black`](https://black.readthedocs.io/) (Python), [`rustfmt`](https://github.com/rust-lang/rustfmt) (Rust) |
| **Linters** | Catch issues template engine cannot detect | Unused imports, naming violations |
| **Hook integration** | Run in driver script after rendering | `clang-format -i generated/*.hpp` |


## Error Handling

| Scenario | Action |
|----------|--------|
| **Malformed data model** | Validate against schema before rendering. Report errors with file location + field name. Do not render invalid data. |
| **Missing template fields** | Use strict undefined handling (Jinja2: [`undefined=StrictUndefined`](https://jinja.palletsprojects.com/en/3.1.x/api/#undefined-types)). Fail loudly. |
| **Non-deterministic output** | Same inputs must produce identical output. If not, there is a bug in the generator. |


## Example Generator Repository

[development-utils](https://github.com/nakane1chome/development-utils) demonstrates:

| Aspect | Details |
|--------|---------|
| **Parsers** | Python-based: SVD, SystemRDL, DBML, Device Tree, IDL |
| **Output** | C++17/C++20 MMIO register interfaces, SQLAlchemy/Pydantic models from DBML, RISC-V CSR access code (C/C++/Rust) |
| **Naming** | `<generation_unit>_<name>.<ext>.jinja2` |
| **Granularity** | Component-level (per peripheral) + system-level (device maps) |
