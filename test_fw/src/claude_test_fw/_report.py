"""Report collector — generates JSON, Markdown, and HTML reports from test sessions."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import pytest

try:
    from pytest_html import extras as _html_extras
except ImportError:
    _html_extras = None


class ReportCollector:
    """Collects session metrics during a test, generates report on finalize.

    Always produces JSON + Markdown summary reports.  HTML audit reports are
    optional — call ``set_html_generator`` to enable them (e.g. from
    dev-record's conftest which has access to audit data).
    """

    def __init__(self):
        self.session_metrics: dict[str, dict] = {}
        self.report_paths: dict[str, Path] = {}
        self._sessions: list[dict] = []
        self._custom: dict[str, dict] = {}
        self._checks: list[dict] = []
        self._project_dir: Path | None = None
        self._model: str | None = None
        self._model_alias: str | None = None
        self._title: str | None = None
        self._test_file: Path | None = None
        self._sandbox_dir: str | None = None
        self._html_generator = None
        self._test_name: str | None = None
        self._test_description: str | None = None
        self._skill_under_test: str | None = None

    def configure(self, *, project_dir: Path, model: str, model_alias: str,
                  test_file: Path,
                  title: str | None = None,
                  test_name: str | None = None,
                  test_description: str | None = None) -> None:
        self._project_dir = project_dir
        self._model = model
        self._model_alias = model_alias
        self._test_file = test_file
        self._sandbox_dir = project_dir.parent.name
        self._test_name = test_name
        self._test_description = test_description

        # Auto-derive skill under test from test file path:
        # tests/skills/<skill-name>/test_*.py → <skill-name>
        self._skill_under_test = self._derive_skill(test_file)

        # Auto-generate title if not provided
        skill = self._skill_under_test or "unknown"
        test = self._test_name or test_file.stem.removeprefix("test_")
        self._title = title or f"{skill} / {test}"

    @staticmethod
    def _derive_skill(test_file: Path) -> str | None:
        """Derive the skill name from the test file path."""
        parts = test_file.resolve().parts
        try:
            idx = parts.index("skills")
            if idx + 1 < len(parts) - 1:
                return parts[idx + 1]
        except ValueError:
            pass
        return None

    def set_html_generator(self, fn) -> None:
        """Set an optional HTML report generator.

        Signature: fn(project_dir, output_path, *, model, title, session_metrics)
        """
        self._html_generator = fn

    def add(self, session_id: str, metrics: dict, *, phase: str | None = None) -> None:
        self.session_metrics[session_id] = metrics
        self._sessions.append({
            "session_id": session_id,
            "phase": phase,
            "metrics": metrics,
        })

    def add_custom(self, key: str, data: dict) -> None:
        """Attach domain-specific metrics under *key*."""
        self._custom[key] = data

    def check(self, name: str, passed: bool, *,
              detail: str | None = None,
              session_id: str | None = None,
              phase: str | None = None) -> None:
        """Record a test checkpoint (assertion result).

        Args:
            name: Short description of what was checked.
            passed: Whether the check passed.
            detail: Optional detail (e.g. actual vs expected).
            session_id: Tie this check to a specific session.
            phase: Tie this check to a named phase.
        """
        self._checks.append({
            "name": name,
            "passed": passed,
            "detail": detail,
            "session_id": session_id,
            "phase": phase,
        })

    def finalize(self) -> Path | None:
        if self._project_dir is None or self._test_file is None:
            return None

        # Compute stable output paths
        test_dir = self._test_file.resolve().parent.relative_to(
            self._test_file.resolve().parent.parent.parent
        )
        test_name = self._test_file.stem.removeprefix("test_")
        reports_dir = self._test_file.resolve().parent.parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        stem = f"{test_dir.as_posix().replace('/', '-')}-{test_name}-{self._model_alias}"

        # JSON + Markdown metrics (always generated)
        metrics = self._build_metrics()
        json_path = self._write_json(reports_dir, stem, metrics)
        self._write_summary_md(reports_dir, stem, metrics)

        # HTML report
        stable_html = reports_dir / f"{stem}.html"
        sandbox_prefix = f"sandbox/{self._sandbox_dir}/" if self._sandbox_dir else ""

        if self._html_generator:
            report_path = self._project_dir / "test-report.html"
            self._html_generator(
                self._project_dir, report_path,
                model=self._model, title=self._title,
                session_metrics=self.session_metrics,
                custom=self._custom,
                sandbox_prefix=sandbox_prefix,
                test_name=self._test_name,
                test_description=self._test_description,
                skill_under_test=self._skill_under_test,
                checks=self._checks,
            )
            shutil.copy2(report_path, stable_html)
        else:
            self._write_default_html(stable_html, metrics)

        self.report_paths["json"] = json_path
        self.report_paths["report"] = stable_html

        return stable_html

    def _build_metrics(self) -> dict:
        sessions_json = []
        for s in self._sessions:
            m = s["metrics"]
            usage = m.get("usage", {})
            sessions_json.append({
                "phase": s["phase"],
                "session_id": s["session_id"],
                "num_turns": m.get("num_turns", 0),
                "duration_s": round(m.get("duration_ms", 0) / 1000, 1),
                "cost_usd": m.get("total_cost_usd", 0) or 0,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            })

        totals = {
            "num_turns": sum(s["num_turns"] for s in sessions_json),
            "duration_s": round(sum(s["duration_s"] for s in sessions_json), 1),
            "cost_usd": round(sum(s["cost_usd"] for s in sessions_json), 4),
            "input_tokens": sum(s["input_tokens"] for s in sessions_json),
            "output_tokens": sum(s["output_tokens"] for s in sessions_json),
        }

        out = {
            "model": self._model,
            "model_alias": self._model_alias,
            "sessions": sessions_json,
            "totals": totals,
        }
        if self._custom:
            out["custom"] = dict(self._custom)
        return out

    def _write_json(self, reports_dir: Path, stem: str, metrics: dict) -> Path:
        json_path = reports_dir / f"{stem}.json"
        json_path.write_text(json.dumps(metrics, indent=2) + "\n")
        return json_path

    def _write_summary_md(self, reports_dir: Path, stem: str, metrics: dict) -> Path:
        alias = metrics["model_alias"]
        totals = metrics["totals"]
        sessions = metrics["sessions"]

        lines = [
            f"## `{alias}` ({totals['duration_s']}s, ${totals['cost_usd']})",
            "",
            "| Phase | Turns | In Tokens | Out Tokens | Cost | Duration |",
            "|-------|-------|-----------|------------|------|----------|",
        ]
        for s in sessions:
            cost_str = f"${s['cost_usd']:.4f}" if s["cost_usd"] else "$0"
            lines.append(
                f"| {s['phase']} | {s['num_turns']} "
                f"| {s['input_tokens']:,} | {s['output_tokens']:,} "
                f"| {cost_str} | {s['duration_s']}s |"
            )

        for section_key, section_data in metrics.get("custom", {}).items():
            lines.append("")
            lines.append(f"### {section_key.replace('_', ' ').title()}")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            for k, v in section_data.items():
                lines.append(f"| {k} | {v} |")

        md_path = reports_dir / f"{stem}.summary.md"
        md_path.write_text("\n".join(lines) + "\n")
        return md_path

    def _write_default_html(self, output_path: Path, metrics: dict) -> None:
        from datetime import datetime, timezone

        h = html.escape
        title = self._title or "Test Report"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        sessions = metrics["sessions"]
        totals = metrics["totals"]

        parts: list[str] = []
        parts.append(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{h(title)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 24px; color: #1f2937; }}
  h1 {{ border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }}
  h2 {{ margin-top: 32px; color: #374151; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 14px; }}
  th {{ background: #f3f4f6; font-weight: 600; }}
  tr:nth-child(even) {{ background: #f9fafb; }}
  .meta {{ color: #6b7280; font-size: 13px; }}
  .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 13px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
               gap: 12px; margin: 16px 0; }}
  .stat-card {{ background: #f3f4f6; border-radius: 8px; padding: 12px 16px; }}
  .stat-card .label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
  .stat-card .value {{ font-size: 24px; font-weight: 700; }}
</style></head><body>
<h1>{h(title)}</h1>
<p class="meta">Generated: {h(now)}
  | Model: {h(self._model or '?')} ({h(self._model_alias or '?')})
  | Sessions: {len(sessions)}</p>
""")

        parts.append('<div class="stat-grid">')
        parts.append(f'<div class="stat-card"><div class="label">Total Turns</div>'
                     f'<div class="value">{totals["num_turns"]}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Duration</div>'
                     f'<div class="value">{totals["duration_s"]}s</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Cost</div>'
                     f'<div class="value">${totals["cost_usd"]:.4f}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Input Tokens</div>'
                     f'<div class="value">{totals["input_tokens"]:,}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Output Tokens</div>'
                     f'<div class="value">{totals["output_tokens"]:,}</div></div>')
        parts.append('</div>')

        parts.append("<h2>Sessions</h2><table><tr>")
        parts.append("<th>#</th><th>Phase</th><th>Session ID</th>"
                     "<th>Turns</th><th>In Tokens</th><th>Out Tokens</th>"
                     "<th>Cost</th><th>Duration</th></tr>")
        for i, s in enumerate(sessions, 1):
            cost_str = f"${s['cost_usd']:.4f}" if s["cost_usd"] else "$0"
            parts.append(f"""<tr>
<td>{i}</td><td>{h(s.get('phase') or '-')}</td>
<td class="mono">{h(s['session_id'][:12])}</td>
<td>{s['num_turns']}</td><td class="mono">{s['input_tokens']:,}</td>
<td class="mono">{s['output_tokens']:,}</td>
<td class="mono">{cost_str}</td><td class="mono">{s['duration_s']}s</td></tr>""")
        parts.append("</table>")

        for section_key, section_data in metrics.get("custom", {}).items():
            section_title = section_key.replace("_", " ").title()
            parts.append(f"<h2>{h(section_title)}</h2>")
            parts.append("<table><tr><th>Metric</th><th>Value</th></tr>")
            for k, v in section_data.items():
                parts.append(f"<tr><td>{h(str(k))}</td><td class='mono'>{h(str(v))}</td></tr>")
            parts.append("</table>")

        parts.append("</body></html>")
        output_path.write_text("\n".join(parts))


@pytest.fixture
def report(request):
    collector = ReportCollector()
    # Auto-extract test name, docstring, and skill from the pytest node
    test_func = request.node.obj if hasattr(request.node, "obj") else None
    if test_func is not None:
        collector._test_name = request.node.name
        doc = getattr(test_func, "__doc__", None)
        if doc:
            collector._test_description = doc.strip().split("\n")[0]
    # Derive skill from test file path
    test_path = Path(request.node.fspath) if hasattr(request.node, "fspath") else None
    if test_path:
        collector._skill_under_test = ReportCollector._derive_skill(test_path)
    request.node._report_collector = collector
    yield collector
    path = collector.finalize()
    if path:
        skill = collector._skill_under_test or "?"
        print(f"\n[{skill}] Report: {path}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if _html_extras is None:
        return
    report = outcome.get_result()
    if report.when != "teardown":
        return
    collector = getattr(item, "_report_collector", None)
    if collector is None or not collector.report_paths:
        return
    extra = getattr(report, "extras", [])
    for label, path in collector.report_paths.items():
        extra.append(_html_extras.url(path.name, name=label))
    report.extras = extra
