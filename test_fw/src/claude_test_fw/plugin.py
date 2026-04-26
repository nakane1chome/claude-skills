"""pytest plugin — registers all framework fixtures and hooks.

Auto-discovered via the ``pytest11`` entry point when ``claude-test-fw``
is installed.
"""

# Apply SDK patch (side-effect import)
import claude_test_fw._patch  # noqa: F401

# pytest hooks
from claude_test_fw._models import pytest_addoption  # noqa: F401
from claude_test_fw._report import pytest_runtest_makereport  # noqa: F401

# Fixtures
from claude_test_fw._models import model, model_alias  # noqa: F401
from claude_test_fw._sandbox import sandbox_project  # noqa: F401
from claude_test_fw._query import claude_query, claude_conversation  # noqa: F401
from claude_test_fw._sdk_helpers import sdk  # noqa: F401
from claude_test_fw._report import report  # noqa: F401
from claude_test_fw._instrumented import instrumented_project  # noqa: F401
from claude_test_fw._audit import audit  # noqa: F401
from claude_test_fw._steps import steps  # noqa: F401

# MCP server support
from claude_test_fw._mcp import pytest_configure  # noqa: F401
from claude_test_fw._mcp import pytest_collection_modifyitems  # noqa: F401
from claude_test_fw._mcp import mcp_servers, mempalace_mcp  # noqa: F401
