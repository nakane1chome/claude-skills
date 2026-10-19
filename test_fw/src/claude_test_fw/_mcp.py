"""MCP server fixtures for tests — optional per-test MCP server injection."""

from __future__ import annotations

import shutil
from importlib.util import find_spec
from pathlib import Path

import pytest


def _is_available(server_config: dict) -> bool:
    """Check if an MCP server's command is available."""
    command = server_config.get("command", "")
    args = server_config.get("args", [])

    # python -m module.name pattern
    if command == "python" and len(args) >= 2 and args[0] == "-m":
        try:
            return find_spec(args[1]) is not None
        except (ModuleNotFoundError, ValueError):
            return False

    # Bare command on PATH
    return shutil.which(command) is not None


def _mempalace_config(palace_dir: Path) -> dict:
    """Build a mempalace stdio server config with isolated data directory."""
    return {
        "command": "python",
        "args": ["-m", "mempalace.mcp_server", "--palace", str(palace_dir)],
    }


_MEMPALACE_AVAIL_CHECK = {"command": "python", "args": ["-m", "mempalace.mcp_server"]}


# ── marker hook ──────────────────────────────────────────────


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "mcp(servers): declare MCP servers this test requires. "
        "Tests are skipped if any declared server is unavailable.",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        marker = item.get_closest_marker("mcp")
        if marker is None:
            continue
        servers = marker.kwargs.get("servers", {})
        for name, cfg in servers.items():
            if not _is_available(cfg):
                item.add_marker(pytest.mark.skip(
                    reason=f"MCP server '{name}' not available",
                ))
                break


# ── fixtures ─────────────────────────────────────────────────


@pytest.fixture
def mcp_servers(request):
    """Build mcp_servers dict from the @pytest.mark.mcp marker.

    Returns the servers dict declared in the marker, ready to pass
    as an override to claude_query or claude_conversation.
    """
    marker = request.node.get_closest_marker("mcp")
    if marker is None:
        return {}
    return dict(marker.kwargs.get("servers", {}))


@pytest.fixture
def mempalace_mcp(tmp_path):
    """Mempalace MCP server config with isolated per-test data directory.

    Each test gets its own ChromaDB + knowledge graph in tmp_path/mempalace/.
    Skips if mempalace is not installed.

    Usage::

        async def test_foo(instrumented_project, mempalace_mcp):
            project, query_fn = instrumented_project
            msgs = await query_fn("prompt", mcp_servers=mempalace_mcp)
    """
    if not _is_available(_MEMPALACE_AVAIL_CHECK):
        pytest.skip("mempalace not installed")
    palace_dir = tmp_path / "mempalace"
    palace_dir.mkdir(exist_ok=True)
    return {"mempalace": _mempalace_config(palace_dir)}
