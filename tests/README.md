# Skill E2E tests

End-to-end tests that validate skills and plugins against real Claude Code sessions. Depends on [`claude-test-fw`](../test_fw/).

## Install

```bash
pip install -e ../test_fw && pip install -e .
```

## Run

```bash
make test                    # all model tiers (weakest, mid, strongest)
MODELS="mid" make test       # single tier
```

## Structure

```
skills/
  dev-record/          # dev-record plugin tests
    test_bare_install    — plugin installs cleanly
    test_double_install  — idempotent reinstall
    test_full_workflow   — full session recording E2E
    test_hook_detection  — anomaly detection hooks
    test_plan_update     — plan-vs-actual file diffing
  review-skill/        # review-skill tests
    test_review_skill    — multi-stage skill review E2E
  review-steps/        # review-steps skill tests
    test_review          — document review E2E
    test_ablation_fixtures — ablation detection baselines
  fixtures/            # shared test fixtures
```

Reports are written to `reports/` per model tier and aggregated to `site/` by `make test`.
