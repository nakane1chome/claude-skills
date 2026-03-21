"""Shared test infrastructure for claude-skills E2E tests."""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk._errors import MessageParseError
from claude_agent_sdk import _internal as _sdk_internal

try:
    from pytest_html import extras as _html_extras
except ImportError:
    _html_extras = None

# ---------------------------------------------------------------------------
# Patch SDK message parser to skip unknown message types (e.g. rate_limit_event)
# instead of crashing the generator mid-stream.
# ---------------------------------------------------------------------------

_original_parse_message = _sdk_internal.message_parser.parse_message


def _patched_parse_message(data):
    try:
        return _original_parse_message(data)
    except MessageParseError:
        # Return a SystemMessage for unknown types so iteration continues
        from claude_agent_sdk import SystemMessage
        return SystemMessage(subtype=data.get("type", "unknown"), data=data)


_sdk_internal.message_parser.parse_message = _patched_parse_message
# Also patch the import in client.py which may have already cached the reference
import claude_agent_sdk._internal.client as _client_mod
_client_mod.parse_message = _patched_parse_message


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

MODEL_MAP = {
    "weakest": "claude-haiku-4-5-20251001",
    "mid": "claude-sonnet-4-6",
    "strongest": "claude-opus-4-6",
}


def pytest_addoption(parser):
    parser.addoption(
        "--model",
        choices=list(MODEL_MAP.keys()),
        default="weakest",
        help="Model tier to use for tests (default: weakest)",
    )


@pytest.fixture(scope="session")
def model(request):
    alias = request.config.getoption("--model")
    return MODEL_MAP[alias]


@pytest.fixture(scope="session")
def model_alias(request):
    return request.config.getoption("--model")


# ---------------------------------------------------------------------------
# Repo root (for install.sh)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# sandbox_project fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def sandbox_project(tmp_path, monkeypatch):
    """Create an isolated project directory with git and all skills installed."""
    real_home = Path.home()

    # Check for auth: API key, OAuth token, or local credentials
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    has_oauth = (real_home / ".claude" / ".credentials.json").is_file()
    if not api_key and not oauth_token and not has_oauth:
        pytest.skip("No auth: set ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, or log in with `claude`")

    project = tmp_path / "project"
    project.mkdir()

    # Isolate HOME so ~/.claude/ config doesn't leak from the host
    monkeypatch.setenv("HOME", str(tmp_path))

    # Clear XDG vars to prevent config discovery
    for var in list(os.environ):
        if var.startswith("XDG_"):
            monkeypatch.delenv(var, raising=False)

    # Allow nested CLI launch (we're running inside Claude Code)
    monkeypatch.delenv("CLAUDECODE", raising=False)

    # Copy auth files into sandbox HOME so the CLI can authenticate
    if api_key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    if has_oauth:
        sandbox_claude_dir = tmp_path / ".claude"
        sandbox_claude_dir.mkdir(exist_ok=True)

        # Copy credentials
        src_creds = real_home / ".claude" / ".credentials.json"
        shutil.copy2(src_creds, sandbox_claude_dir / ".credentials.json")

        # Copy main config (contains oauthAccount needed for auth)
        src_config = real_home / ".claude.json"
        if src_config.is_file():
            shutil.copy2(src_config, tmp_path / ".claude.json")

    # git init with an empty initial commit
    subprocess.run(
        ["git", "init"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    # Run install.sh to copy all skills into the project
    # The script is interactive: option 2 = project install, "a" = all skills
    install_script = REPO_ROOT / "install.sh"
    subprocess.run(
        ["bash", str(install_script)],
        input="2\na\n",
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )

    yield project


# ---------------------------------------------------------------------------
# claude_query fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def claude_query(sandbox_project, model):
    """Return an async callable that wraps claude_agent_sdk.query() with sandbox defaults."""

    async def _query(prompt: str, **overrides) -> list:
        opts = {
            "cwd": str(sandbox_project),
            "model": model,
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "max_turns": overrides.pop("max_turns", 10),
        }
        opts.update(overrides)
        options = ClaudeAgentOptions(**opts)

        messages = []
        async for msg in query(prompt=prompt, options=options):
            messages.append(msg)
        return messages

    return _query


@pytest.fixture
def claude_conversation(sandbox_project, model):
    """Return a factory for multi-turn conversations using ClaudeSDKClient.

    Usage:
        async with conversation(plugins=[...]) as conv:
            msgs = await conv.say("initial prompt")
            msgs += await conv.say("follow-up")
    """

    def _factory(**overrides):
        opts = {
            "cwd": str(sandbox_project),
            "model": model,
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "max_turns": overrides.pop("max_turns", 15),
        }
        opts.update(overrides)
        return _Conversation(ClaudeAgentOptions(**opts))

    return _factory


class _Conversation:
    """Async context manager wrapping ClaudeSDKClient for multi-turn tests."""

    def __init__(self, options: ClaudeAgentOptions):
        self._options = options
        self._client: ClaudeSDKClient | None = None
        self.messages: list = []

    async def __aenter__(self):
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.__aexit__(*exc)
        self._client = None

    async def say(self, prompt: str) -> list:
        """Send a message and collect all response messages."""
        await self._client.query(prompt)
        turn_msgs = []
        async for msg in self._client.receive_response():
            turn_msgs.append(msg)
            self.messages.append(msg)
        return turn_msgs


# ---------------------------------------------------------------------------
# sdk helper namespace
# ---------------------------------------------------------------------------


@dataclass
class _SDKHelpers:
    """Static helpers for extracting data from SDK message lists."""

    @staticmethod
    def session_id(messages: list) -> str | None:
        for msg in messages:
            if isinstance(msg, ResultMessage):
                return msg.session_id
        return None

    @staticmethod
    def result(messages: list) -> ResultMessage | None:
        for msg in messages:
            if isinstance(msg, ResultMessage):
                return msg
        return None

    @staticmethod
    def text(messages: list) -> str:
        parts = []
        for msg in messages:
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "\n".join(parts)

    @staticmethod
    def metrics(messages: list) -> dict:
        """Extract session metrics from ResultMessage for report generation."""
        for msg in messages:
            if isinstance(msg, ResultMessage):
                return {
                    "num_turns": msg.num_turns,
                    "duration_ms": msg.duration_ms,
                    "duration_api_ms": msg.duration_api_ms,
                    "total_cost_usd": msg.total_cost_usd,
                    "usage": msg.usage or {},
                }
        return {}

    def log_phase(self, phase: str, messages: list, project_dir: Path) -> None:
        """Print a compact phase summary for CI log visibility.

        Outputs session info, metrics, tool calls (from ops events if
        available), project file listing, and response tail.
        """
        result = self.result(messages)
        m = self.metrics(messages)
        usage = m.get("usage", {})
        dur = m.get("duration_ms", 0)
        turns = m.get("num_turns", 0)
        cost = m.get("total_cost_usd")

        print(f"\n{'='*60}")
        print(f"Phase: {phase}")
        print(f"  session: {result.session_id if result else '?'}")
        print(f"  turns: {turns}  duration: {dur/1000:.1f}s  cost: ${cost:.4f}" if cost else
              f"  turns: {turns}  duration: {dur/1000:.1f}s")
        print(f"  tokens: {usage.get('input_tokens', 0):,} in / {usage.get('output_tokens', 0):,} out")

        # Summarize tool calls from ops events (if audit dir exists)
        sid = result.session_id if result else None
        ops_dir = project_dir / "audit" / "ops_record"
        if sid and ops_dir.is_dir():
            ops_files = list(ops_dir.glob(f"*-{sid}.jsonl"))
            if ops_files:
                tool_calls = []
                for line in ops_files[0].read_text().strip().splitlines():
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "tool_call":
                        tool = ev["content"]["tool"]
                        inp = ev["content"].get("input", {})
                        if tool in ("Write", "Edit"):
                            detail = inp.get("file_path", "?")
                        elif tool == "Bash":
                            cmd = inp.get("command", "")
                            detail = cmd[:80] + ("..." if len(cmd) > 80 else "")
                        else:
                            detail = ""
                        tool_calls.append(f"{tool}({detail})" if detail else tool)
                if tool_calls:
                    print(f"  tools: {', '.join(tool_calls)}")

        # Show project files (excluding internals)
        exclude = {".git", ".claude", "__pycache__", ".pytest_cache", "audit"}
        files = sorted(
            str(p.relative_to(project_dir))
            for p in project_dir.rglob("*")
            if p.is_file() and not any(part in exclude for part in p.relative_to(project_dir).parts)
        )
        if files:
            print(f"  project files: {', '.join(files)}")
        else:
            print("  project files: (none)")

        # Show last 300 chars of model response
        text = self.text(messages)
        if text:
            snippet = text[-300:].strip()
            if len(text) > 300:
                snippet = "..." + snippet
            print(f"  response tail: {snippet}")
        print(f"{'='*60}")


@pytest.fixture(scope="session")
def sdk():
    return _SDKHelpers()


# ---------------------------------------------------------------------------
# report fixture — collects session metrics, generates JSON/MD/HTML reports
# ---------------------------------------------------------------------------


class _ReportCollector:
    """Collects session metrics during a test, generates report on finalize.

    Always produces JSON + Markdown summary reports.  HTML audit reports are
    optional — call ``set_html_generator`` to enable them (e.g. from
    dev-record's conftest which has access to audit data).
    """

    def __init__(self):
        self.session_metrics: dict[str, dict] = {}
        self.report_paths: dict[str, Path] = {}
        self._sessions: list[dict] = []  # ordered list with phase labels
        self._custom: dict[str, dict] = {}
        self._project_dir: Path | None = None
        self._model: str | None = None
        self._model_alias: str | None = None
        self._title: str | None = None
        self._test_file: Path | None = None
        self._sandbox_dir: str | None = None
        self._html_generator = None

    def configure(self, *, project_dir: Path, model: str, model_alias: str,
                  title: str, test_file: Path) -> None:
        self._project_dir = project_dir
        self._model = model
        self._model_alias = model_alias
        self._title = title
        self._test_file = test_file
        # Derive sandbox dir from the actual pytest tmp_path name (which may
        # be truncated for long test names, e.g. "test_review_preserves_vocabula0")
        self._sandbox_dir = project_dir.parent.name

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
        """Attach domain-specific metrics under *key*.

        Multiple calls with different keys accumulate; same key overwrites.
        """
        self._custom[key] = data

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

        # HTML report — custom generator (e.g. dev-record audit) or default
        stable_html = reports_dir / f"{stem}.html"
        # Sandbox prefix: on Pages, sandbox files live at sandbox/{tmp_dir_name}/
        sandbox_prefix = f"sandbox/{self._sandbox_dir}/" if self._sandbox_dir else ""

        if self._html_generator:
            report_path = self._project_dir / "test-report.html"
            self._html_generator(
                self._project_dir, report_path,
                model=self._model, title=self._title,
                session_metrics=self.session_metrics,
                custom=self._custom,
                sandbox_prefix=sandbox_prefix,
            )
            shutil.copy2(report_path, stable_html)
        else:
            self._write_default_html(stable_html, metrics)

        # Track generated report paths for pytest-html linking
        self.report_paths["json"] = json_path
        self.report_paths["report"] = stable_html

        return stable_html

    def _build_metrics(self) -> dict:
        """Build the structured metrics payload from collected sessions."""
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
        """Write JSON metrics file for cross-model aggregation in CI."""
        json_path = reports_dir / f"{stem}.json"
        json_path.write_text(json.dumps(metrics, indent=2) + "\n")
        return json_path

    def _write_summary_md(self, reports_dir: Path, stem: str, metrics: dict) -> Path:
        """Write a Markdown summary snippet for the CI job summary step."""
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

        # Render custom metric sections
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
        """Generate a default HTML report from session metrics and custom data."""
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
  .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
           font-size: 13px; }}
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

        # Summary stats
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

        # Sessions table
        parts.append("<h2>Sessions</h2>")
        parts.append("<table><tr>")
        parts.append("<th>#</th><th>Phase</th><th>Session ID</th>"
                     "<th>Turns</th><th>In Tokens</th><th>Out Tokens</th>"
                     "<th>Cost</th><th>Duration</th>")
        parts.append("</tr>")
        for i, s in enumerate(sessions, 1):
            cost_str = f"${s['cost_usd']:.4f}" if s["cost_usd"] else "$0"
            parts.append(f"""<tr>
<td>{i}</td>
<td>{h(s.get('phase') or '-')}</td>
<td class="mono">{h(s['session_id'][:12])}</td>
<td>{s['num_turns']}</td>
<td class="mono">{s['input_tokens']:,}</td>
<td class="mono">{s['output_tokens']:,}</td>
<td class="mono">{cost_str}</td>
<td class="mono">{s['duration_s']}s</td>
</tr>""")
        parts.append("</table>")

        # Custom sections
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
    collector = _ReportCollector()
    request.node._report_collector = collector
    yield collector
    path = collector.finalize()
    if path:
        print(f"\nReport: {path}")


# ---------------------------------------------------------------------------
# pytest-html integration — link custom reports from pytest-html rows
# ---------------------------------------------------------------------------


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
