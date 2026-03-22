# Semantic Ablation Detector

A CLI tool that compares two markdown files (before and after a skill run) and measures whether the edit preserved the author's vocabulary or systematically flattened it toward generic alternatives — the signature of [semantic ablation](https://www.theregister.com/2026/02/16/semantic_ablation_ai_writing/).

## Why this exists

The skills in this repo (flesh-out, strong-edit, review-steps, agent-optimize) all transform documents. They defend against ablation structurally — stop-after-each-stage, developer approval — but that's qualitative. This tool provides a quantitative check: did the skill preserve the author's words, or did it quietly replace "tombstone propagation" with "sending updates"?

## What it measures

| Metric | What it tells you |
|--------|-------------------|
| Concept coverage | Did every input idea survive in the output? |
| Lexical overlap | Did the author's specific words survive in matched concepts? |
| Frequency shift | Were distinctive terms replaced with more common alternatives? |
| Ablation risk | Composite score: meaning preserved + words flattened = ablation |

## Usage

```bash
# Compare input to output (default: preserve mode, terminal output)
python -m tests.tools.ablation input.md output.md

# Specify the skill's expected transformation mode
python -m tests.tools.ablation input.md output.md --mode expand    # flesh-out
python -m tests.tools.ablation input.md output.md --mode preserve  # strong-edit, review-steps
python -m tests.tools.ablation input.md output.md --mode compress  # agent-optimize

# Alternative output formats
python -m tests.tools.ablation input.md output.md --format json
python -m tests.tools.ablation input.md output.md --format markdown
```

Modes adjust coverage thresholds — `expand` expects new content, `compress` expects structural change, `preserve` expects minimal alteration.

## Running tests

```bash
pytest tests/tools/ablation/
```

## Dependencies

Listed in `tests/pyproject.toml`. Core: scikit-learn, numpy, click, rich, pyyaml, marko.
