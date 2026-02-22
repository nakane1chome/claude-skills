#!/usr/bin/env python3
"""Generate index.html for GitHub Pages from accumulated test run data.

Usage: python generate-pages-index.py site/
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path


def _load_metrics(model_dir: Path) -> dict | None:
    """Load the first JSON metrics file found in a model directory."""
    for f in model_dir.glob("*.json"):
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _find_report(model_dir: Path, prefix: str) -> str | None:
    """Find an HTML report file matching a prefix pattern."""
    for f in model_dir.glob(f"{prefix}*.html"):
        return f.name
    return None


def generate_index(site_dir: Path) -> None:
    runs_dir = site_dir / "runs"
    if not runs_dir.is_dir():
        runs_dir.mkdir(parents=True, exist_ok=True)

    h = html.escape

    # Discover runs (newest first by directory name = run_id)
    run_dirs = sorted(runs_dir.iterdir(), key=lambda d: d.name, reverse=True)
    run_dirs = [d for d in run_dirs if d.is_dir()]

    # Collect all model names across runs for table columns
    all_models: list[str] = []
    seen_models: set[str] = set()
    for rd in run_dirs:
        for md in sorted(rd.iterdir()):
            if md.is_dir() and md.name not in seen_models:
                all_models.append(md.name)
                seen_models.add(md.name)

    # Build run data
    runs = []
    for rd in run_dirs:
        run_id = rd.name
        models: dict[str, dict] = {}
        for model_name in all_models:
            model_dir = rd / model_name
            if not model_dir.is_dir():
                continue
            metrics = _load_metrics(model_dir)
            custom_report = _find_report(model_dir, "skills-")
            pytest_report = _find_report(model_dir, "pytest-")
            has_sandbox = (model_dir / "sandbox").is_dir()
            models[model_name] = {
                "metrics": metrics,
                "custom_report": custom_report,
                "pytest_report": pytest_report,
                "has_sandbox": has_sandbox,
            }
        runs.append({"run_id": run_id, "models": models})

    # Generate HTML
    parts: list[str] = []
    parts.append("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>E2E Test Results</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 1400px; margin: 0 auto; padding: 24px; color: #1f2937; }
  h1 { border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 14px; }
  th { background: #f3f4f6; font-weight: 600; }
  tr:nth-child(even) { background: #f9fafb; }
  .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 13px; }
  .meta { color: #6b7280; font-size: 13px; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .links { font-size: 12px; }
  .links a { margin-right: 8px; }
  .model-header { text-align: center; }
  .na { color: #9ca3af; font-style: italic; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
               gap: 12px; margin: 16px 0; }
  .stat-card { background: #f3f4f6; border-radius: 8px; padding: 12px 16px; }
  .stat-card .label { font-size: 12px; color: #6b7280; text-transform: uppercase; }
  .stat-card .value { font-size: 24px; font-weight: 700; }
</style></head><body>
<h1>E2E Test Results</h1>
""")

    parts.append(f'<p class="meta">{len(runs)} run(s) recorded</p>')

    if not runs:
        parts.append("<p>No test runs recorded yet.</p>")
    else:
        # Summary stats
        parts.append('<div class="stat-grid">')
        parts.append(f'<div class="stat-card"><div class="label">Total Runs</div>'
                     f'<div class="value">{len(runs)}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Model Tiers</div>'
                     f'<div class="value">{len(all_models)}</div></div>')
        parts.append('</div>')

        # Runs table
        parts.append("<table><tr>")
        parts.append("<th>Run ID</th>")
        for model in all_models:
            parts.append(f'<th class="model-header" colspan="2">{h(model)}</th>')
        parts.append("</tr>")

        # Sub-header row for metrics + links
        parts.append("<tr><th></th>")
        for _ in all_models:
            parts.append("<th>Metrics</th><th>Links</th>")
        parts.append("</tr>")

        for run in runs:
            run_id = run["run_id"]
            parts.append("<tr>")
            parts.append(f'<td class="mono">{h(run_id)}</td>')
            for model in all_models:
                mdata = run["models"].get(model)
                if mdata is None:
                    parts.append('<td class="na">-</td><td class="na">-</td>')
                    continue
                # Metrics cell
                metrics = mdata["metrics"]
                if metrics and "totals" in metrics:
                    t = metrics["totals"]
                    cost = f"${t.get('cost_usd', 0):.4f}"
                    dur = f"{t.get('duration_s', 0):.0f}s"
                    turns = t.get("num_turns", 0)
                    parts.append(
                        f'<td class="mono">{cost} &middot; {dur} &middot; '
                        f'{turns}t</td>'
                    )
                else:
                    parts.append('<td class="na">no metrics</td>')
                # Links cell
                links: list[str] = []
                base = f"runs/{run_id}/{model}"
                if mdata["custom_report"]:
                    links.append(f'<a href="{base}/{mdata["custom_report"]}">report</a>')
                if mdata["pytest_report"]:
                    links.append(f'<a href="{base}/{mdata["pytest_report"]}">pytest</a>')
                if mdata["has_sandbox"]:
                    links.append(f'<a href="{base}/sandbox/">sandbox</a>')
                parts.append(f'<td class="links">{" ".join(links) if links else "-"}</td>')
            parts.append("</tr>")
        parts.append("</table>")

    parts.append("</body></html>")

    index_path = site_dir / "index.html"
    index_path.write_text("\n".join(parts))
    print(f"Generated {index_path} ({len(runs)} runs)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <site-dir>", file=sys.stderr)
        sys.exit(1)
    generate_index(Path(sys.argv[1]))
