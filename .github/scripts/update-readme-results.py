#!/usr/bin/env python3
"""Update README.md with the most recent test results table.

Reads JSON reports from site/runs/ and replaces content between
<!-- BEGIN TEST RESULTS --> and <!-- END TEST RESULTS --> markers in README.md.

Usage: python update-readme-results.py <site-dir> <readme-path>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


_MODEL_ORDER = {"weakest": 0, "mid": 1, "strongest": 2}
_MODEL_DISPLAY = {"weakest": "Haiku", "mid": "Sonnet", "strongest": "Opus"}

BEGIN_MARKER = "<!-- BEGIN TEST RESULTS -->"
END_MARKER = "<!-- END TEST RESULTS -->"


def _load_test_data(site_dir: Path) -> dict[str, dict[str, dict]]:
    """Load test results keyed by (label, model_alias).

    Returns {label: {model_alias: {hard_pass, achievement_pct, cost_usd, duration_s}}}.
    """
    runs_dir = site_dir / "runs"
    if not runs_dir.is_dir():
        return {}

    # Find the most recent run
    run_dirs = sorted(runs_dir.iterdir(), key=lambda d: d.name, reverse=True)
    run_dirs = [d for d in run_dirs if d.is_dir()]
    if not run_dirs:
        return {}

    run_dir = run_dirs[0]
    results: dict[str, dict[str, dict]] = {}

    for model_dir in sorted(run_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        alias = model_dir.name
        for f in sorted(model_dir.glob("skills-*.json")):
            try:
                data = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            scores = data.get("scores", {})
            totals = data.get("totals", {})
            skill = data.get("skill")
            test_name = data.get("test_name")

            if skill and test_name:
                clean = test_name.removeprefix("test_").replace("[", "-").replace("]", "")
                label = f"{skill}/{clean}"
            else:
                # Fallback: parse from filename
                stem = f.stem
                remainder = stem.removeprefix("skills-")
                parts = remainder.rsplit("-", 1)
                if len(parts) == 2:
                    skill_parts = parts[0].rsplit("-", 1)
                    label = "/".join(skill_parts) if len(skill_parts) == 2 else parts[0]
                else:
                    label = remainder

            results.setdefault(label, {})[alias] = {
                "hard_pass": scores.get("hard_pass", True),
                "achievement_pct": scores.get("achievement_pct"),
                "cost_usd": totals.get("cost_usd", 0),
                "duration_s": totals.get("duration_s", 0),
            }

    return results


def _format_hard(data: dict | None) -> str:
    """Format the hard pass/fail cell."""
    if data is None:
        return "—"
    return "PASS" if data["hard_pass"] else "FAIL"


def _format_ability(data: dict | None) -> str:
    """Format the ability percentage cell."""
    if data is None:
        return "—"
    pct = data.get("achievement_pct")
    if pct is None:
        return "—"
    return f"{pct}%"


def generate_table(site_dir: Path) -> str:
    """Generate a markdown results table."""
    results = _load_test_data(site_dir)
    if not results:
        return "*No test results available. Run `make test` to generate.*"

    # Determine which models have data
    all_models = set()
    for label_data in results.values():
        all_models.update(label_data.keys())
    models = sorted(all_models, key=lambda m: _MODEL_ORDER.get(m, 99))

    if not models:
        return "*No test results available.*"

    # Header: each model gets two columns (Hard, Ability)
    header_cols = []
    separator_cols = []
    for m in models:
        display = _MODEL_DISPLAY.get(m, m)
        header_cols.append(f"{display}")
        header_cols.append("Ability")
        separator_cols.append(":---:")
        separator_cols.append(":---:")

    lines = [
        f"| Test | {' | '.join(header_cols)} |",
        f"|------|{' | '.join(separator_cols)}|",
    ]

    # Rows
    for label in sorted(results.keys()):
        cells = []
        for m in models:
            d = results[label].get(m)
            cells.append(_format_hard(d))
            cells.append(_format_ability(d))
        lines.append(f"| {label} | {' | '.join(cells)} |")

    return "\n".join(lines)


def update_readme(readme_path: Path, table: str) -> bool:
    """Replace content between markers in README. Returns True if updated."""
    content = readme_path.read_text()

    begin_idx = content.find(BEGIN_MARKER)
    end_idx = content.find(END_MARKER)

    if begin_idx == -1 or end_idx == -1:
        print(f"Markers not found in {readme_path}", file=sys.stderr)
        return False

    new_content = (
        content[:begin_idx + len(BEGIN_MARKER)]
        + "\n"
        + table
        + "\n"
        + content[end_idx:]
    )

    if new_content == content:
        print("README already up to date")
        return False

    readme_path.write_text(new_content)
    print(f"Updated {readme_path}")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <site-dir> <readme-path>", file=sys.stderr)
        sys.exit(1)

    site_dir = Path(sys.argv[1])
    readme_path = Path(sys.argv[2])
    table = generate_table(site_dir)
    update_readme(readme_path, table)
