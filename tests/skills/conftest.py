"""Wire up HTML audit reports for all skill tests."""

import pytest
from claude_test_fw._audit import AuditHelpers


@pytest.fixture(autouse=True)
def _configure_report_html(report):
    """Enable HTML audit reports for all skill tests."""
    report.set_html_generator(AuditHelpers.generate_report)
