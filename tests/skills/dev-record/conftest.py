"""Dev-record specific fixtures: installed project and audit helpers."""

from __future__ import annotations

import html
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# installed_project fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def installed_project(sandbox_project, claude_query):
    """Sandbox project with dev-record fully installed via install.sh (direct subprocess)."""
    project = sandbox_project

    # Run the dev-record install.sh directly (not via the agent) for reliability.
    # The agent would need to interpret the SKILL.md and run the script, which is
    # unreliable with weaker models and wastes API tokens for setup.
    install_script = project / ".claude" / "skills" / "dev-record" / "install.sh"
    assert install_script.is_file(), f"install.sh not found at {install_script}"

    subprocess.run(
        ["bash", str(install_script)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        env={
            **dict(os.environ),
            "CLAUDE_PROJECT_DIR": str(project),
        },
    )

    # Verify the install produced expected artifacts
    hooks_dir = project / ".claude" / "hooks" / "dev-record"
    assert hooks_dir.is_dir(), f"hooks dir missing: {hooks_dir}"
    expected_scripts = [
        "record-prompt.sh",
        "record-tool-call.sh",
        "record-tool-result.sh",
        "finalize-session.sh",
    ]
    for script in expected_scripts:
        assert (hooks_dir / script).is_file(), f"missing hook: {script}"

    settings = project / ".claude" / "settings.json"
    assert settings.is_file(), "settings.json missing after install"

    assert (project / "audit" / "dev_record").is_dir(), "audit/dev_record/ missing"
    assert (project / "audit" / "ops_record").is_dir(), "audit/ops_record/ missing"

    yield project, claude_query


# ---------------------------------------------------------------------------
# audit helper namespace
# ---------------------------------------------------------------------------


@dataclass
class _AuditHelpers:
    """Helpers for inspecting dev-record audit output."""

    @staticmethod
    def finalize(project_dir: Path, session_id: str) -> None:
        """Manually invoke finalize-session.sh for a given session."""
        script = project_dir / ".claude" / "hooks" / "dev-record" / "finalize-session.sh"
        if not script.is_file():
            raise FileNotFoundError(f"finalize script not found: {script}")

        stdin_data = json.dumps({"session_id": session_id})
        subprocess.run(
            ["bash", str(script)],
            input=stdin_data,
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
            env={
                **dict(__import__("os").environ),
                "CLAUDE_PROJECT_DIR": str(project_dir),
            },
        )

    @staticmethod
    def assert_common(project_dir: Path) -> None:
        """Common Check 1: verify audit directories have content."""
        dev_dir = project_dir / "audit" / "dev_record"
        ops_dir = project_dir / "audit" / "ops_record"

        assert dev_dir.is_dir(), "audit/dev_record/ does not exist"
        assert ops_dir.is_dir(), "audit/ops_record/ does not exist"

        summaries = list(dev_dir.glob("*.json"))
        assert len(summaries) >= 1, (
            f"Expected at least one session summary in {dev_dir}, found {len(summaries)}"
        )

        logs = list(ops_dir.glob("*.jsonl"))
        assert len(logs) >= 1, (
            f"Expected at least one event log in {ops_dir}, found {len(logs)}"
        )

    @staticmethod
    def read_summary(project_dir: Path, session_id: str) -> dict:
        """Find and parse the session summary JSON for a given session_id."""
        dev_dir = project_dir / "audit" / "dev_record"
        matches = list(dev_dir.glob(f"*-{session_id}.json"))
        assert len(matches) == 1, (
            f"Expected exactly 1 summary for session {session_id}, "
            f"found {len(matches)}: {[m.name for m in matches]}"
        )
        return json.loads(matches[0].read_text())

    @staticmethod
    def _parse_jsonl(path: Path) -> list[dict]:
        """Parse a JSONL file, skipping malformed lines."""
        events = []
        for line in path.read_text().strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # Hook scripts may produce truncated lines for very large tool inputs
                continue
        return events

    @staticmethod
    def read_ops_events(project_dir: Path, session_id: str) -> list[dict]:
        """Parse the JSONL event log for a given session_id."""
        ops_dir = project_dir / "audit" / "ops_record"
        matches = list(ops_dir.glob(f"*-{session_id}.jsonl"))
        if not matches:
            return []
        assert len(matches) == 1, (
            f"Expected 0 or 1 ops log for session {session_id}, "
            f"found {len(matches)}: {[m.name for m in matches]}"
        )
        return _AuditHelpers._parse_jsonl(matches[0])

    @staticmethod
    def read_dev_events(project_dir: Path, session_id: str) -> list[dict]:
        """Parse extracted events JSONL for a given session_id."""
        dev_dir = project_dir / "audit" / "dev_record"
        matches = list(dev_dir.glob(f"*-{session_id}-events.jsonl"))
        if not matches:
            return []
        assert len(matches) == 1, (
            f"Expected 0 or 1 events file for session {session_id}, "
            f"found {len(matches)}: {[m.name for m in matches]}"
        )
        return _AuditHelpers._parse_jsonl(matches[0])

    @staticmethod
    def generate_report(
        project_dir: Path,
        output_path: Path,
        *,
        title: str | None = None,
        model: str | None = None,
    ) -> Path:
        """Generate a self-contained HTML session report from audit data.

        Auto-discovers all sessions from audit/dev_record/*.json.
        Returns the output_path for convenience.
        """
        title = title or "Dev-Record Session Report"
        dev_dir = project_dir / "audit" / "dev_record"
        ops_dir = project_dir / "audit" / "ops_record"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # --- Discover sessions (sorted by filename = chronological) ---
        summary_files = sorted(dev_dir.glob("*.json"))
        # Exclude event JSONL files that also live in dev_dir
        summary_files = [f for f in summary_files if f.suffix == ".json"
                         and "-events" not in f.stem]

        sessions: list[dict] = []
        for sf in summary_files:
            summary = json.loads(sf.read_text())
            sid = summary.get("session_id", sf.stem.split("-", 1)[-1] if "-" in sf.stem else sf.stem)
            # Find matching ops log
            ops_matches = list(ops_dir.glob(f"*-{sid}.jsonl"))
            ops_events = _AuditHelpers._parse_jsonl(ops_matches[0]) if ops_matches else []
            sessions.append({
                "session_id": sid,
                "summary": summary,
                "ops_events": ops_events,
            })

        # --- Aggregate stats ---
        total_events = sum(len(s["ops_events"]) for s in sessions)
        tool_usage: dict[str, int] = {}
        success_count = 0
        failure_count = 0
        for s in sessions:
            for ev in s["ops_events"]:
                if ev.get("type") == "tool_call":
                    tool_name = ev.get("content", {}).get("tool", "unknown")
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                elif ev.get("type") == "tool_result":
                    if ev.get("content", {}).get("is_error"):
                        failure_count += 1
                    else:
                        success_count += 1

        # --- Scan project files ---
        exclude_dirs = {".git", "__pycache__", ".pytest_cache"}
        project_files: list[str] = []
        for p in sorted(project_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(project_dir)
                if not any(part in exclude_dirs for part in rel.parts):
                    project_files.append(str(rel))

        # --- Build HTML ---
        h = html.escape

        def _parse_ts(ts_str: str) -> datetime | None:
            if not ts_str:
                return None
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        def _relative_ts(ts_str: str, base: datetime | None) -> str:
            ts = _parse_ts(ts_str)
            if ts is None or base is None:
                return ts_str
            delta = (ts - base).total_seconds()
            if delta < 0:
                return f"-{abs(delta):.1f}s"
            return f"+{delta:.1f}s"

        def _truncate(text: str, limit: int = 120) -> str:
            """Return HTML with click-to-expand if text exceeds limit."""
            if len(text) <= limit:
                return h(text)
            short = h(text[:limit])
            full = h(text)
            return (f'<span class="trunc-wrap">'
                    f'<span class="trunc-short">{short}<span class="trunc-toggle" '
                    f'onclick="var w=this.closest(\'.trunc-wrap\');'
                    f"w.classList.toggle('expanded')\">"
                    f'\u2026</span></span>'
                    f'<span class="trunc-full">{full}<span class="trunc-toggle" '
                    f'onclick="var w=this.closest(\'.trunc-wrap\');'
                    f"w.classList.toggle('expanded')\">"
                    f'\u25B4</span></span></span>')

        _EVENT_COLORS = {
            "user_prompt": "#2563eb",      # blue
            "tool_call": "#16a34a",        # green
            "tool_result_ok": "#6b7280",   # gray
            "tool_result_err": "#dc2626",  # red
            "agent_report": "#ea580c",     # orange
            "plan_snapshot": "#9333ea",     # purple
        }

        def _event_color(ev: dict) -> str:
            t = ev.get("type", "")
            if t == "tool_result":
                return _EVENT_COLORS["tool_result_err"] if ev.get("content", {}).get("is_error") else _EVENT_COLORS["tool_result_ok"]
            return _EVENT_COLORS.get(t, "#374151")

        def _event_label(ev: dict) -> str:
            t = ev.get("type", "")
            c = ev.get("content", {})
            if t == "tool_call":
                tool = c.get("tool", "?")
                inp = json.dumps(c.get("input", ""), ensure_ascii=False)
                return f"tool_call: {h(tool)}  {_truncate(inp)}"
            if t == "tool_result":
                status = "ERROR" if c.get("is_error") else "ok"
                return f"tool_result: [{status}]"
            if t == "user_prompt":
                prompt = c.get("prompt", c.get("message", ""))
                if isinstance(prompt, str):
                    return f"user_prompt: {_truncate(prompt, 80)}"
                return "user_prompt"
            if t == "agent_report":
                event_name = c.get("event", "")
                detail = c.get("detail", "")
                return f"agent_report: {h(event_name)}  {_truncate(str(detail), 80)}"
            if t == "plan_snapshot":
                plan_file = c.get("plan_file", "")
                if plan_file:
                    return f'plan_snapshot: <a href="file://{h(plan_file)}">{h(Path(plan_file).name)}</a>'
                return "plan_snapshot"
            return h(t)

        parts: list[str] = []
        parts.append(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{h(title)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 24px; color: #1f2937; }}
  h1 {{ border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }}
  h2 {{ margin-top: 32px; color: #374151; }}
  h3 {{ margin-top: 24px; color: #4b5563; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 14px; }}
  th {{ background: #f3f4f6; font-weight: 600; }}
  tr:nth-child(even) {{ background: #f9fafb; }}
  .meta {{ color: #6b7280; font-size: 13px; }}
  .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 13px; }}
  .event-row td {{ vertical-align: top; }}
  .event-type {{ display: inline-block; padding: 1px 6px; border-radius: 3px;
                  color: #fff; font-size: 12px; font-weight: 600; white-space: nowrap; }}
  .event-detail {{ word-break: break-word; }}
  .result-ok {{ display: none; }}
  .show-ok .result-ok {{ display: table-row; }}
  .toggle-ok {{ font-size: 13px; cursor: pointer; margin-left: 12px;
                color: #2563eb; text-decoration: underline; user-select: none; }}
  .trunc-wrap .trunc-full {{ display: none; }}
  .trunc-wrap.expanded .trunc-short {{ display: none; }}
  .trunc-wrap.expanded .trunc-full {{ display: inline; }}
  .trunc-toggle {{ cursor: pointer; color: #2563eb; padding: 0 2px; user-select: none; }}
  .delta {{ color: #9ca3af; font-size: 11px; }}
  .file-list {{ column-count: 2; font-size: 13px; }}
  .file-list li {{ margin-bottom: 2px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                 gap: 12px; margin: 12px 0; }}
  .stat-card {{ background: #f3f4f6; border-radius: 8px; padding: 12px 16px; }}
  .stat-card .label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
  .stat-card .value {{ font-size: 24px; font-weight: 700; }}
  .session-stats {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }}
  .session-stat {{ display: inline-block; padding: 3px 10px; border-radius: 4px;
                   font-size: 13px; background: #f3f4f6; border: 1px solid #e5e7eb; }}
  .session-stat .stat-name {{ color: #6b7280; }}
  .session-stat .stat-val {{ font-weight: 600; color: #1f2937; }}
</style></head><body>
<h1>{h(title)}</h1>
<p class="meta">Generated: {h(now)}{f'  |  Model: {h(model)}' if model else ''}
   |  Sessions: {len(sessions)}</p>
""")

        # --- Summary table ---
        parts.append("<h2>Session Summary</h2>\n<table><tr>")
        for col in ["#", "Session ID", "Started", "Ended", "Tools", "Rejected", "Prompts", "Plans", "Agent Reports"]:
            parts.append(f"<th>{col}</th>")
        parts.append("</tr>")
        for i, s in enumerate(sessions, 1):
            sm = s["summary"]
            sid_short = s["session_id"][:12]
            parts.append(f"""<tr>
<td>{i}</td>
<td class="mono">{h(sid_short)}</td>
<td class="mono">{h(sm.get('started', '—'))}</td>
<td class="mono">{h(sm.get('ended', '—'))}</td>
<td>{sm.get('tool_attempts', 0)}</td>
<td>{sm.get('tool_rejections', 0)}</td>
<td>{sm.get('user_prompts', 0)}</td>
<td>{sm.get('plan_snapshots', 0)}</td>
<td>{len(sm['agent_reports']) if isinstance(sm.get('agent_reports'), list) else sm.get('agent_reports', 0)}</td>
</tr>""")
        parts.append("</table>")

        # --- Per-session detail ---
        parts.append("<h2>Session Details</h2>")
        for i, s in enumerate(sessions, 1):
            sm = s["summary"]
            sid_short = s["session_id"][:12]
            parts.append(f'<h3>Session {i}: <span class="mono">{h(sid_short)}</span></h3>')
            ar = sm.get('agent_reports')
            ar_count = len(ar) if isinstance(ar, list) else (ar or 0)
            stat_items = [
                ("tools", sm.get('tool_attempts', 0)),
                ("rejected", sm.get('tool_rejections', 0)),
                ("prompts", sm.get('user_prompts', 0)),
                ("plans", sm.get('plan_snapshots', 0)),
                ("agent reports", ar_count),
            ]
            chips = "".join(
                f'<span class="session-stat">'
                f'<span class="stat-name">{name}</span> '
                f'<span class="stat-val">{val}</span></span>'
                for name, val in stat_items
            )
            parts.append(f'<div class="session-stats">{chips}</div>')
            events = s["ops_events"]
            if events:
                # Compute base timestamp from first event
                base_ts = _parse_ts(events[0].get("timestamp", ""))
                if base_ts:
                    parts.append(f'<p class="meta mono">started {h(events[0].get("timestamp", ""))}</p>')
                ok_count = sum(1 for ev in events if ev.get("type") == "tool_result"
                               and not ev.get("content", {}).get("is_error"))
                tbl_id = f"session-{i}"
                parts.append(
                    f'<table id="{tbl_id}"><tr><th style="width:40px">#</th>'
                    '<th style="width:80px">Time</th>'
                    '<th style="width:110px">Type</th>'
                    f'<th>Detail <span class="toggle-ok" '
                    f"""onclick="var t=this.closest('table');t.classList.toggle('show-ok');"""
                    f"""this.textContent=t.classList.contains('show-ok')?'hide {ok_count} ok results':'show {ok_count} ok results'">"""
                    f'show {ok_count} ok results</span></th></tr>')
                prev_ts = base_ts
                for j, ev in enumerate(events, 1):
                    color = _event_color(ev)
                    etype = ev.get("type", "?")
                    cur_ts = _parse_ts(ev.get("timestamp", ""))
                    rel = _relative_ts(ev.get("timestamp", ""), base_ts)
                    # Delta from previous event
                    delta = ""
                    if cur_ts and prev_ts:
                        d = (cur_ts - prev_ts).total_seconds()
                        delta = f' <span class="delta">[+{d:.1f}s]</span>'
                    prev_ts = cur_ts or prev_ts
                    label = _event_label(ev)
                    is_ok = (ev.get("type") == "tool_result"
                             and not ev.get("content", {}).get("is_error"))
                    row_class = "event-row result-ok" if is_ok else "event-row"
                    parts.append(f"""<tr class="{row_class}">
<td>{j}</td>
<td class="mono">{h(rel)}{delta}</td>
<td><span class="event-type" style="background:{color}">{h(etype)}</span></td>
<td class="event-detail mono">{label}</td>
</tr>""")
                parts.append("</table>")
            else:
                parts.append("<p class='meta'>No ops events recorded for this session.</p>")

        # --- Files created (tree view) ---
        parts.append("<h2>Project Files</h2>")
        if project_files:
            parts.append(f"<p>{len(project_files)} file(s) in project (excluding .git, __pycache__):</p>")
            # Build tree dict: nested dicts for dirs, str path for leaf files
            tree: dict = {}
            for f in project_files:
                node = tree
                file_path = Path(f)
                for part in file_path.parts[:-1]:
                    node = node.setdefault(part, {})
                node[file_path.name] = f  # leaf = relative path string

            def _render_tree(node: dict, prefix: str = "") -> list[str]:
                lines = []
                entries = sorted(node.keys(), key=lambda k: (isinstance(node[k], str), k))
                for idx, name in enumerate(entries):
                    is_last = idx == len(entries) - 1
                    connector = "\u2514\u2500 " if is_last else "\u251c\u2500 "
                    child = node[name]
                    if isinstance(child, str):
                        # Leaf file
                        abs_path = (project_dir / child).resolve()
                        lines.append(
                            f'{h(prefix)}{connector}'
                            f'<a href="file://{abs_path}">{h(name)}</a>'
                        )
                    else:
                        # Directory
                        lines.append(f'{h(prefix)}{connector}{h(name)}/')
                        extension = "\u2502  " if not is_last else "   "
                        lines.extend(_render_tree(child, prefix + extension))
                return lines

            tree_lines = _render_tree(tree)
            parts.append(f'<pre class="mono" style="line-height:1.5">{chr(10).join(tree_lines)}</pre>')
        else:
            parts.append("<p class='meta'>No project files found.</p>")

        # --- Aggregate stats ---
        parts.append("<h2>Aggregate Statistics</h2>")
        parts.append('<div class="stat-grid">')
        parts.append(f'<div class="stat-card"><div class="label">Total Events</div><div class="value">{total_events}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Tool Successes</div><div class="value">{success_count}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Tool Failures</div><div class="value">{failure_count}</div></div>')
        parts.append(f'<div class="stat-card"><div class="label">Sessions</div><div class="value">{len(sessions)}</div></div>')
        parts.append("</div>")

        if tool_usage:
            parts.append("<h3>Tool Usage Breakdown</h3><table><tr><th>Tool</th><th>Calls</th></tr>")
            for tool_name, count in sorted(tool_usage.items(), key=lambda x: -x[1]):
                parts.append(f"<tr><td>{h(tool_name)}</td><td>{count}</td></tr>")
            parts.append("</table>")

        parts.append("</body></html>")

        output_path.write_text("\n".join(parts))
        return output_path


@pytest.fixture(scope="session")
def audit():
    return _AuditHelpers()
