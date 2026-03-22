"""Model tier selection — pytest CLI option and fixtures."""

from __future__ import annotations

import pytest

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
    parser.addoption(
        "--repo-root",
        default=None,
        help="Path to the claude-skills repo root (default: parent of CWD)",
    )


@pytest.fixture(scope="session")
def model(request):
    alias = request.config.getoption("--model")
    return MODEL_MAP[alias]


@pytest.fixture(scope="session")
def model_alias(request):
    return request.config.getoption("--model")
