"""SDK helper utilities — extract data from message lists."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock


@dataclass
class SDKHelpers:
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

    def log_phase(self, phase: str, messages: list, project_dir: Path,
                  *, skill: str | None = None) -> None:
        """Print a compact phase summary for CI log visibility."""
        result = self.result(messages)
        m = self.metrics(messages)
        usage = m.get("usage", {})
        dur = m.get("duration_ms", 0)
        turns = m.get("num_turns", 0)
        cost = m.get("total_cost_usd")

        print(f"\n{'='*60}")
        if skill:
            print(f"Skill: {skill}  |  Phase: {phase}")
        else:
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
    return SDKHelpers()
