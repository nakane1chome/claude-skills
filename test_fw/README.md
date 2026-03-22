# claude-test-fw

Reusable pytest framework for running E2E tests against real Claude Code sessions.

## Install

```bash
pip install -e .
```

## Modules

| Module | Purpose |
|--------|---------|
| `_sandbox.py` | Isolated test project directory management |
| `_sdk_helpers.py` | Claude SDK helpers for multi-turn conversations |
| `_query.py` | Message query utilities |
| `_models.py` | Model tier definitions (weakest, mid, strongest) |
| `_patch.py` | Pytest fixture patching |
| `_instrumented.py` | Session instrumentation hooks |
| `_audit.py` | Dev-record output inspection — session summaries, event logs, plan snapshots |
| `_report.py` | Multi-format report collection (JSON, Markdown, HTML) |
| `plugin.py` | Pytest plugin entry point (registered via `pytest11`) |

## Ablation detection

The `ablation` subpackage detects whether an agent preserved meaning while transforming a document. It uses TF-IDF embeddings and concept matching to score output against expected-good and expected-ablated baselines.

```bash
# CLI
ablation compare input.md output.md expected-good.md

# As a module
python -m claude_test_fw.ablation compare input.md output.md expected-good.md
```

Test fixtures live in `src/claude_test_fw/ablation/fixtures/` with `manifest.yaml` metadata.

## Unit tests

```bash
make test-fw        # from repo root
# or
cd test_fw && pytest tests/ -v
```
