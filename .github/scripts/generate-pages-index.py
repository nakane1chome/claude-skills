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


def _label_from_json(model_dir: Path, stem: str) -> str | None:
    """Try to read a structured label from the companion JSON metrics file."""
    json_path = model_dir / f"{stem}.json"
    if not json_path.is_file():
        return None
    try:
        data = json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    skill = data.get("skill")
    test_name = data.get("test_name")
    if skill and test_name:
        # Strip test_ prefix and parametrize brackets for display
        clean = test_name.removeprefix("test_").replace("[", "-").replace("]", "")
        return f"{skill}/{clean}"
    return None


def _label_from_filename(stem: str) -> str:
    """Derive label by parsing the report filename (legacy fallback)."""
    remainder = stem.removeprefix("skills-")
    parts = remainder.rsplit("-", 1)
    if len(parts) == 2:
        skill_parts = parts[0].rsplit("-", 1)
        return "/".join(skill_parts) if len(skill_parts) == 2 else parts[0]
    return remainder


def _find_reports(model_dir: Path) -> list[dict]:
    """Find all non-pytest HTML reports with derived labels.

    Reads label from companion JSON metadata when available,
    falls back to filename parsing for backward compatibility.
    """
    reports = []
    for f in sorted(model_dir.glob("skills-*.html")):
        stem = f.stem
        label = _label_from_json(model_dir, stem) or _label_from_filename(stem)
        reports.append({"filename": f.name, "label": label})
    return reports


def _find_pytest_report(model_dir: Path) -> str | None:
    """Find the single pytest HTML report file."""
    for f in model_dir.glob("pytest-*.html"):
        return f.name
    return None


def _metrics_for_stem(all_metrics: list[dict], stem: str) -> dict | None:
    """Find metrics matching a specific report stem."""
    for entry in all_metrics:
        if entry["stem"] == stem:
            return entry["metrics"].get("totals", {})
    return None


def _scores_for_stem(all_metrics: list[dict], stem: str) -> dict | None:
    """Find scores matching a specific report stem."""
    for entry in all_metrics:
        if entry["stem"] == stem:
            return entry["metrics"].get("scores")
    return None


def _model_id(all_metrics: list[dict]) -> str | None:
    """Extract the actual model ID from metrics data."""
    for entry in all_metrics:
        model = entry["metrics"].get("model")
        if model:
            return model
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


def _fmt_metrics(totals: dict) -> str:
    """Format totals as a compact string."""
    cost = f"${totals['cost_usd']:.4f}"
    dur = f"{totals['duration_s']:.0f}s"
    turns = f"{totals['num_turns']}t"
    return f"{cost} &middot; {dur} &middot; {turns}"


def generate_index(site_dir: Path) -> None:
    runs_dir = site_dir / "runs"
    if not runs_dir.is_dir():
        runs_dir.mkdir(parents=True, exist_ok=True)

    h = html.escape

    # Discover runs (newest first by directory name = run_id)
    run_dirs = sorted(runs_dir.iterdir(), key=lambda d: d.name, reverse=True)
    run_dirs = [d for d in run_dirs if d.is_dir()]

    # Collect all model names across runs for table columns
    _MODEL_ORDER = {"weakest": 0, "mid": 1, "strongest": 2}
    seen_models: set[str] = set()
    for rd in run_dirs:
        for md in sorted(rd.iterdir()):
            if md.is_dir():
                seen_models.add(md.name)
    all_models = sorted(seen_models, key=lambda m: _MODEL_ORDER.get(m, 99))

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

    # Collect all test labels across all runs for consistent rows
    all_test_labels: list[str] = []
    seen_labels: set[str] = set()
    for run in runs:
        for mdata in run["models"].values():
            for cr in mdata["custom_reports"]:
                if cr["label"] not in seen_labels:
                    seen_labels.add(cr["label"])
                    all_test_labels.append(cr["label"])

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
  .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 13px; }
  .meta { color: #6b7280; font-size: 13px; }
  a { color: #2563eb; text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  .model-header { text-align: center; }
  .na { color: #9ca3af; font-style: italic; }
  .test-name { font-weight: 500; }
  .test-name.pytest { color: #16a34a; }
  .metrics { color: #6b7280; font-size: 12px; display: block; margin-top: 2px; }
  .cell-link { font-size: 14px; }
  .cell-link a { font-size: 14px; }
  .model-id { color: #9ca3af; font-size: 11px; display: block; margin-top: 2px;
              font-family: "SFMono-Regular", Consolas, monospace; }
  .run-id { vertical-align: top; }
  .totals-row { border-top: 2px solid #9ca3af; }
  .totals-label { font-weight: 600; color: #374151; }
  .run-group { border-top: 3px solid #6b7280; }
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

        # Header row
        parts.append("<table><tr>")
        parts.append("<th>Run</th><th>Date</th><th>Test</th>")
        for model in all_models:
            parts.append(f'<th class="model-header">{h(model)}</th>')
        parts.append("</tr>")

        for run in runs:
            run_id = run["run_id"]
            ts = run["meta"].get("timestamp", "")
            date = ts[:16].replace("T", " ") if ts else run["meta"].get("date", "-")

            # Build rows: pytest + each test report + totals
            # Count rows for rowspan: pytest + test reports + totals
            has_pytest = any(
                run["models"].get(m, {}).get("pytest_report")
                for m in all_models
            )
            num_rows = len(all_test_labels) + (1 if has_pytest else 0) + 1  # +1 for totals
            first_row = True

            # pytest row
            if has_pytest:
                parts.append(f'<tr class="run-group">')
                if first_row:
                    parts.append(
                        f'<td class="mono run-id" rowspan="{num_rows}">{h(run_id)}</td>'
                        f'<td class="mono run-id" rowspan="{num_rows}">{h(date)}</td>'
                    )
                    first_row = False
                parts.append('<td class="test-name pytest">pytest</td>')
                for model in all_models:
                    mdata = run["models"].get(model)
                    if mdata and mdata["pytest_report"]:
                        base = f"runs/{run_id}/{model}"
                        href = f'{base}/{mdata["pytest_report"]}'
                        mid = _model_id(mdata["all_metrics"])
                        mid_str = f'<span class="model-id">{h(mid)}</span>' if mid else ""
                        parts.append(
                            f'<td class="cell-link">'
                            f'<a href="{href}">results</a>{mid_str}</td>'
                        )
                    else:
                        parts.append('<td class="na">\u2014</td>')
                parts.append("</tr>")

            # Test report rows
            for label in all_test_labels:
                row_class = ' class="run-group"' if first_row else ""
                parts.append(f"<tr{row_class}>")
                if first_row:
                    parts.append(
                        f'<td class="mono run-id" rowspan="{num_rows}">{h(run_id)}</td>'
                        f'<td class="mono run-id" rowspan="{num_rows}">{h(date)}</td>'
                    )
                    first_row = False
                parts.append(f'<td class="test-name">{h(label)}</td>')
                for model in all_models:
                    mdata = run["models"].get(model)
                    if mdata is None:
                        parts.append('<td class="na">\u2014</td>')
                        continue
                    # Find matching report and metrics
                    report = next(
                        (cr for cr in mdata["custom_reports"] if cr["label"] == label),
                        None,
                    )
                    if report:
                        base = f"runs/{run_id}/{model}"
                        href = f'{base}/{report["filename"]}'
                        # Find per-test metrics and scores
                        stem = report["filename"].removesuffix(".html")
                        totals = _metrics_for_stem(mdata["all_metrics"], stem)
                        scores = _scores_for_stem(mdata["all_metrics"], stem)
                        scores_str = ""
                        if scores and scores.get("hard_total", 0) > 0:
                            hp = scores.get("hard_pass", True)
                            label = "PASS" if hp else "FAIL"
                            color = "#16a34a" if hp else "#dc2626"
                            pct = scores.get("achievement_pct")
                            pct_str = (f', <span style="color:#2563eb;font-weight:700">'
                                       f'ABILITY: {pct}%</span>') if pct is not None else ""
                            scores_str = (
                                f'<span style="color:{color};font-weight:700">'
                                f'{label}</span>{pct_str}; '
                            )
                        metrics_str = ""
                        if totals:
                            cost = f"${totals.get('cost_usd', 0):.4f}"
                            dur = f"{totals.get('duration_s', 0):.0f}s"
                            turns = f"{totals.get('num_turns', 0)}t"
                            metrics_str = (
                                f'<span class="metrics">'
                                f'{scores_str}{cost} &middot; {dur} &middot; {turns}</span>'
                            )
                        parts.append(
                            f'<td class="cell-link">'
                            f'<a href="{href}">report</a>{metrics_str}</td>'
                        )
                    else:
                        parts.append('<td class="na">\u2014</td>')
                parts.append("</tr>")

            # Totals row
            parts.append("<tr class=\"totals-row\">")
            if first_row:
                parts.append(
                    f'<td class="mono run-id" rowspan="{num_rows}">{h(run_id)}</td>'
                    f'<td class="mono run-id" rowspan="{num_rows}">{h(date)}</td>'
                )
            parts.append('<td class="totals-label">total</td>')
            for model in all_models:
                mdata = run["models"].get(model)
                if mdata and mdata["all_metrics"]:
                    t = _aggregate_totals(mdata["all_metrics"])
                    parts.append(f'<td class="mono">{_fmt_metrics(t)}</td>')
                else:
                    parts.append('<td class="na">\u2014</td>')
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
