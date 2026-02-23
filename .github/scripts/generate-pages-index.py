#!/usr/bin/env python3
"""Generate index.html for GitHub Pages from accumulated test run data.

Usage: python generate-pages-index.py site/
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path


def _load_meta(run_dir: Path) -> dict:
    """Read meta.json for run metadata (date, timestamp). Graceful fallback."""
    meta_path = run_dir / "meta.json"
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _load_all_metrics(model_dir: Path) -> list[dict]:
    """Load ALL JSON metrics files in a model directory.

    Returns a list of {stem, metrics} dicts.
    """
    results = []
    for f in sorted(model_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if "totals" in data:
            results.append({"stem": f.stem, "metrics": data})
    return results


def _find_reports(model_dir: Path) -> list[dict]:
    """Find all non-pytest HTML reports with derived labels.

    Label derivation: skills-dev-record-full_workflow-weakest -> dev-record/full_workflow
    Strip 'skills-' prefix and '-{model_alias}' suffix, join remainder with '/'.
    """
    reports = []
    for f in sorted(model_dir.glob("skills-*.html")):
        stem = f.stem  # e.g. skills-dev-record-full_workflow-weakest
        # Strip 'skills-' prefix
        remainder = stem.removeprefix("skills-")
        # Strip '-{model_alias}' suffix (last hyphen-separated segment)
        # Then split skill-dir from test-name at the rightmost hyphen
        parts = remainder.rsplit("-", 1)
        if len(parts) == 2:
            # parts[0] = 'dev-record-full_workflow', parts[1] = model alias
            # Now split skill name from test name at the last hyphen in parts[0]
            skill_parts = parts[0].rsplit("-", 1)
            label = "/".join(skill_parts) if len(skill_parts) == 2 else parts[0]
        else:
            label = remainder
        reports.append({"filename": f.name, "label": label})
    return reports


def _find_pytest_report(model_dir: Path) -> str | None:
    """Find the single pytest HTML report file."""
    for f in model_dir.glob("pytest-*.html"):
        return f.name
    return None


def _aggregate_totals(all_metrics: list[dict]) -> dict:
    """Sum totals across multiple metrics files for a single model."""
    agg = {"num_turns": 0, "duration_s": 0.0, "cost_usd": 0.0,
           "input_tokens": 0, "output_tokens": 0}
    for entry in all_metrics:
        t = entry["metrics"].get("totals", {})
        agg["num_turns"] += t.get("num_turns", 0)
        agg["duration_s"] += t.get("duration_s", 0)
        agg["cost_usd"] += t.get("cost_usd", 0)
        agg["input_tokens"] += t.get("input_tokens", 0)
        agg["output_tokens"] += t.get("output_tokens", 0)
    agg["duration_s"] = round(agg["duration_s"], 1)
    agg["cost_usd"] = round(agg["cost_usd"], 4)
    return agg


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
        meta = _load_meta(rd)
        models: dict[str, dict] = {}
        for model_name in all_models:
            model_dir = rd / model_name
            if not model_dir.is_dir():
                continue
            all_metrics = _load_all_metrics(model_dir)
            custom_reports = _find_reports(model_dir)
            pytest_report = _find_pytest_report(model_dir)
            models[model_name] = {
                "all_metrics": all_metrics,
                "custom_reports": custom_reports,
                "pytest_report": pytest_report,
            }
        runs.append({"run_id": run_id, "meta": meta, "models": models})

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
        parts.append("<th>Run ID</th><th>Date</th>")
        for model in all_models:
            parts.append(f'<th class="model-header" colspan="2">{h(model)}</th>')
        parts.append("</tr>")

        # Sub-header row for metrics + links
        parts.append("<tr><th></th><th></th>")
        for _ in all_models:
            parts.append("<th>Metrics</th><th>Links</th>")
        parts.append("</tr>")

        for run in runs:
            run_id = run["run_id"]
            ts = run["meta"].get("timestamp", "")
            date = ts[:16].replace("T", " ") if ts else run["meta"].get("date", "-")
            parts.append("<tr>")
            parts.append(f'<td class="mono">{h(run_id)}</td>')
            parts.append(f'<td class="mono">{h(date)}</td>')
            for model in all_models:
                mdata = run["models"].get(model)
                if mdata is None:
                    parts.append('<td class="na">-</td><td class="na">-</td>')
                    continue
                # Metrics cell — aggregate across all JSON files
                all_metrics = mdata["all_metrics"]
                if all_metrics:
                    t = _aggregate_totals(all_metrics)
                    cost = f"${t['cost_usd']:.4f}"
                    dur = f"{t['duration_s']:.0f}s"
                    turns = t["num_turns"]
                    parts.append(
                        f'<td class="mono">{cost} &middot; {dur} &middot; '
                        f'{turns}t</td>'
                    )
                else:
                    parts.append('<td class="na">no metrics</td>')
                # Links cell — one link per custom report + pytest
                links: list[str] = []
                base = f"runs/{run_id}/{model}"
                for cr in mdata["custom_reports"]:
                    links.append(
                        f'<a href="{base}/{cr["filename"]}">{h(cr["label"])}</a>'
                    )
                if mdata["pytest_report"]:
                    links.append(f'<a href="{base}/{mdata["pytest_report"]}">pytest</a>')
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
