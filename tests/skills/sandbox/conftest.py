"""Sandbox skill test fixtures."""

from __future__ import annotations

import shutil

import pytest


@pytest.fixture
async def polyglot_target(instrumented_project):
    """Instrumented project dressed up as a polyglot repo (Python + CMake).

    Drops minimal `pyproject.toml`, `CMakeLists.txt`, and `requirements.txt`
    into the project root so the sandbox skill's language-detection rules
    should select both python and cmake stanzas.

    Also removes any pre-existing harness files that top-level `install.sh`
    copied in for project installs that include sandbox — the test needs a
    clean slate so the skill's Stage 0 doesn't trip its collision detection.
    """
    project, query_fn = instrumented_project

    for name in ("run-sandbox.sh", "docker-compose.yml"):
        f = project / name
        if f.is_file():
            f.unlink()
    docker_dir = project / "docker"
    if docker_dir.is_dir():
        shutil.rmtree(docker_dir)

    (project / "pyproject.toml").write_text(
        '[project]\nname = "polyglot-example"\nversion = "0.0.0"\n'
        'requires-python = ">=3.10"\n'
    )
    (project / "requirements.txt").write_text("")
    (project / "CMakeLists.txt").write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(polyglot_example)\n'
    )

    yield project, query_fn
