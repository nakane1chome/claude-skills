"""Shared inventory + assertion helpers for light-v-structure tests.

Reusable across the scaffold / check / explain test families:

* ``CANONICAL_DIRS`` / ``CANONICAL_FILES_*`` — single source of truth for
  what the canonical V-model project structure looks like, derived from
  ``skills/light-v-structure/{documentation,scaffold}.md``.
* ``PARTIAL_SEEDS`` — sentinel-bearing files used by the partial-state
  fixture variant to verify "do not overwrite" behavior.
* assertion helpers operate on ``project_dir`` + the ``steps`` fixture.
"""

from __future__ import annotations

from pathlib import Path


# Canonical directories scaffold should create.
# Derived from skills/light-v-structure/documentation.md "Folder Structure".
CANONICAL_DIRS = (
    "docs",
    "docs/adr",
    "docs/arch",
    "docs/design",
    "docs/evaluation",
    "docs/test",
    "docs/test/system",
    "docs/test/unit",
)

# Canonical files scaffold should create — core set (expect_).
# Derived from skills/light-v-structure/scaffold.md "Stub Index".
CANONICAL_FILES_CORE = (
    "docs/README.md",
    "docs/paradigm.md",
    "docs/glossary.md",
    "docs/references.md",
    "docs/evaluation/README.md",
    "docs/adr/README.md",
    "docs/adr/xx-template.md",
    "docs/adr/qa.md",
    "docs/arch/README.md",
    "docs/arch/xx-template.md",
    "docs/arch/00-principles.md",
    "docs/arch/01-user-archetypes.md",
    "docs/arch/02-system-archetypes.md",
    "docs/arch/03-use-cases.md",
    "docs/arch/04-directory-structure.md",
    "docs/design/README.md",
    "docs/design/template.md",
    "docs/test/README.md",
    "docs/test/system/README.md",
    "docs/test/unit/README.md",
)

# SKILL.md marks logical / physical architecture as "optional depending on
# complexity". The assets/ README is similarly optional. Treat as achieve_
# at "challenging" difficulty, not a hard expectation.
CANONICAL_FILES_OPTIONAL = (
    "docs/arch/04-logical.md",
    "docs/arch/04-physical.md",
    "docs/assets/README.md",
)

# Sentinel-bearing files for the "partial" starting state. Each marker is
# unique; the test asserts it still appears in the file after scaffold runs.
PARTIAL_SEEDS = {
    "docs/paradigm.md": (
        "# Pre-existing Paradigm\n\n"
        "SENTINEL-PARADIGM-DO-NOT-OVERWRITE\n\n"
        "## Core Principles\n\n1. Existing principle that must survive scaffold.\n"
    ),
    "docs/adr/01-existing-decision.md": (
        "# ADR0001 - Existing decision\n\n"
        "SENTINEL-ADR-DO-NOT-OVERWRITE\n\n"
        "## Context\n\nThis ADR existed before scaffold ran.\n"
    ),
}


# -- Assertion helpers ---------------------------------------------------------

def assert_canonical_dirs_exist(steps, project_dir, session_id):
    """Each canonical directory should exist as a real directory."""
    project_dir = Path(project_dir)
    missing = [d for d in CANONICAL_DIRS if not (project_dir / d).is_dir()]
    steps.expect(
        "canonical directories present",
        passed=(len(missing) == 0),
        detail=("all present" if not missing else f"missing: {missing}"),
        session_id=session_id, phase="Structure",
    )


def assert_canonical_files_exist(steps, project_dir, session_id):
    """Core files are expect_; optional files are achieve_ (challenging)."""
    project_dir = Path(project_dir)

    missing_core = [f for f in CANONICAL_FILES_CORE
                    if not (project_dir / f).is_file()]
    steps.expect(
        "canonical core files present",
        passed=(len(missing_core) == 0),
        detail=(f"{len(CANONICAL_FILES_CORE)} present" if not missing_core
                else f"missing: {missing_core}"),
        session_id=session_id, phase="Structure",
    )

    missing_opt = [f for f in CANONICAL_FILES_OPTIONAL
                   if not (project_dir / f).is_file()]
    steps.achieve(
        "optional canonical files present",
        passed=(len(missing_opt) == 0),
        difficulty="challenging",
        detail=(f"all {len(CANONICAL_FILES_OPTIONAL)} present"
                if not missing_opt else f"missing: {missing_opt}"),
        session_id=session_id, phase="Structure",
    )


def assert_preserved(steps, project_dir, preserved_files, session_id):
    """Pre-seeded files should still contain their sentinel markers.

    No-op when ``preserved_files`` is empty (empty start state).
    """
    if not preserved_files:
        return
    project_dir = Path(project_dir)
    clobbered = []
    for relpath, original in preserved_files.items():
        path = project_dir / relpath
        if not path.is_file():
            clobbered.append(f"{relpath} (deleted)")
            continue
        current = path.read_text(encoding="utf-8")
        # Each seed contains a unique SENTINEL-* token — check it survived.
        sentinel = next(
            (tok for tok in original.split() if tok.startswith("SENTINEL-")),
            None,
        )
        if sentinel and sentinel not in current:
            clobbered.append(f"{relpath} (sentinel missing)")
    steps.expect(
        "pre-existing files preserved (not overwritten)",
        passed=(len(clobbered) == 0),
        detail=("all preserved" if not clobbered
                else f"clobbered: {clobbered}"),
        session_id=session_id, phase="Preservation",
    )


def assert_minimal_content_sanity(steps, project_dir, session_id):
    """Spot-check that key scaffolded files have the expected shape.

    Deliberately shallow — strict template fidelity is a follow-up test.
    """
    steps.expect_file_contains(
        project_dir, "docs/README.md", r"#\s+Documentation",
        session_id=session_id, phase="Content",
    )
    steps.expect_file_contains(
        project_dir, "docs/paradigm.md", r"[Pp]aradigm",
        session_id=session_id, phase="Content",
    )
    steps.expect_file_contains(
        project_dir, "docs/adr/xx-template.md", r"##\s+Context",
        session_id=session_id, phase="Content",
    )
    steps.expect_file_contains(
        project_dir, "docs/adr/xx-template.md", r"##\s+Decision",
        session_id=session_id, phase="Content",
    )


def docs_files_written(project_dir, preserved_files):
    """Files under ``docs/`` that weren't part of the pre-seeded set.

    Used to verify the propose stage didn't create the scaffold yet.
    """
    project_dir = Path(project_dir)
    docs = project_dir / "docs"
    if not docs.is_dir():
        return []
    preserved_paths = {(project_dir / p).resolve() for p in preserved_files}
    written = []
    for p in docs.rglob("*"):
        if not p.is_file():
            continue
        if p.resolve() in preserved_paths:
            continue
        written.append(str(p.relative_to(project_dir)))
    return written
