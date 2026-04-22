"""Test: sandbox skill scaffolds a Docker YOLO harness into a polyglot target repo.

The target repo has both ``pyproject.toml`` and ``CMakeLists.txt``, so detection
should select the python + cmake stanzas (both included, cmake-first per the
ordering rule in skills/sandbox/reference/placeholders.md).

The test mirrors the skill's stop-after-each-stage pattern with three turns:
Stage 0 (detect), Stage 1 (propose vars), Stage 2 (render files). Stages 3
(Docker verify) and 4 (tidy-up) are out of scope.
"""

from __future__ import annotations

import re
from pathlib import Path

from claude_agent_sdk.types import ResultMessage


PROMPT_DETECT = """\
Use the sandbox skill to scaffold a Docker YOLO-mode harness into the current
directory.

Start with **Stage 0** — detect the build system in this directory. Report
which languages you detect, flag any collisions with existing sandbox files,
and stop for review.
"""

PROMPT_PROPOSE = """\
The detection looks right. Proceed to **Stage 1**: propose the template
variables (`{{REPO_NAME}}`, language stanzas, build-dir isolation choice,
extra safe dirs). Then stop for approval.
"""

PROMPT_RENDER = """\
The proposed values are approved. Proceed through **Stage 2**: render each
template and write all four harness files:

- run-sandbox.sh
- docker-compose.yml
- docker/Dockerfile
- docker/entrypoint.sh

Include both language stanzas (python AND cmake) since this is a polyglot repo.
Make run-sandbox.sh and docker/entrypoint.sh executable.

Do not proceed to Stage 3 (Docker verification) or Stage 4 (.gitignore tidy-up)
— those are out of scope for this test.
"""


async def test_sandbox_scaffolds_polyglot_target(
    polyglot_target, steps, sdk, model, model_alias, report, audit,
):
    """Sandbox skill produces a correct four-file harness for a polyglot repo."""
    project_dir, claude_query = polyglot_target

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    async with claude_query.conversation(max_turns=30) as conv:
        # Stage 0 — detection
        detect_messages = await conv.say(PROMPT_DETECT)
        detect_results = [m for m in detect_messages if isinstance(m, ResultMessage)]
        if detect_results:
            report.add(detect_results[-1].session_id,
                       sdk.metrics(detect_messages), phase="Detect")
        sdk.log_phase("Detect", detect_messages, project_dir)

        # Stage 1 — propose variables
        propose_messages = await conv.say(PROMPT_PROPOSE)
        propose_results = [m for m in propose_messages if isinstance(m, ResultMessage)]
        if propose_results:
            report.add(propose_results[-1].session_id,
                       sdk.metrics(propose_messages), phase="Propose")
        sdk.log_phase("Propose", propose_messages, project_dir)

        # Stage 2 — render and write files
        render_messages = await conv.say(PROMPT_RENDER)

    all_messages = conv.messages
    result = steps.require_session_ok(all_messages, phase="Render")
    session_id = result.session_id

    audit.finalize(project_dir, session_id)
    report.add(session_id, sdk.metrics(render_messages), phase="Render")
    sdk.log_phase("Render", render_messages, project_dir)

    _check_harness_files(steps, project_dir, session_id)
    _check_permissions_and_syntax(steps, project_dir, session_id)
    _check_stanza_content(steps, project_dir, session_id)
    _check_runtime_resolution(steps, project_dir, session_id)
    _check_no_host_paths(steps, project_dir, session_id)
    _check_stanza_ordering(steps, project_dir, session_id)


# -- Check helpers -------------------------------------------------------------

def _check_harness_files(steps, project_dir, session_id):
    """All four harness files present at their expected paths."""
    steps.expect_files_exist(project_dir, ["run-sandbox.sh"],
                             session_id=session_id, phase="Artifacts")
    steps.expect_files_exist(project_dir, ["docker-compose.yml"],
                             session_id=session_id, phase="Artifacts")
    steps.expect_files_exist(project_dir, ["docker/Dockerfile"],
                             session_id=session_id, phase="Artifacts")
    steps.expect_files_exist(project_dir, ["docker/entrypoint.sh"],
                             session_id=session_id, phase="Artifacts")


def _check_permissions_and_syntax(steps, project_dir, session_id):
    """Shell scripts must be executable AND pass `bash -n`."""
    steps.expect_executable(project_dir, ["run-sandbox.sh", "docker/entrypoint.sh"],
                            session_id=session_id, phase="Permissions")
    steps.expect_shell_syntax_valid(project_dir,
                                    ["run-sandbox.sh", "docker/entrypoint.sh"],
                                    session_id=session_id, phase="Syntax")


def _check_stanza_content(steps, project_dir, session_id):
    """Both language stanzas (python + cmake) appear in Dockerfile and entrypoint."""
    steps.expect_file_contains(project_dir, "docker/Dockerfile",
                               r"g\+\+-13|gcc-13|cmake",
                               session_id=session_id, phase="Content")
    steps.expect_file_contains(project_dir, "docker/Dockerfile",
                               r"python3-pip|python3",
                               session_id=session_id, phase="Content")
    steps.expect_file_contains(project_dir, "docker/entrypoint.sh",
                               r"BUILD_DIR=build\.sandbox",
                               session_id=session_id, phase="Content")
    steps.expect_file_contains(project_dir, "docker/entrypoint.sh",
                               r"pytest_cache\.sandbox",
                               session_id=session_id, phase="Content")


def _check_runtime_resolution(steps, project_dir, session_id):
    """run-sandbox.sh should resolve repo path dynamically, not hardcode it."""
    steps.expect_file_contains(project_dir, "run-sandbox.sh",
                               r'dirname.*BASH_SOURCE',
                               session_id=session_id, phase="Portability")


def _check_no_host_paths(steps, project_dir, session_id):
    """No absolute host-user /home/<user>/ paths should leak into the harness.

    Exemptions:
    - `/home/agent/` is the in-container user's home — correct and portable.
    - Comment-only references (lines starting with `#` after whitespace) are
      informational and don't affect runtime behavior.
    """
    project_dir = Path(project_dir)
    # Match /home/<user>/ where <user> is NOT `agent`. Require 2+ chars to skip
    # example fragments like `/home/a/b`.
    pattern = re.compile(r"/home/(?!agent/)[a-zA-Z0-9_-]{2,}/")
    offenders = []
    for rel in ("run-sandbox.sh", "docker-compose.yml",
                "docker/Dockerfile", "docker/entrypoint.sh"):
        f = project_dir / rel
        if not f.is_file():
            continue
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue  # comment-only reference is fine
            if pattern.search(line):
                offenders.append(f"{rel}:{lineno}")
    steps.achieve(
        "no hardcoded host /home/<user>/ paths in rendered harness",
        passed=(len(offenders) == 0),
        difficulty="expected",
        detail=f"offenders: {offenders[:5]}" if offenders else "clean",
        session_id=session_id, phase="Portability",
    )


def _check_stanza_ordering(steps, project_dir, session_id):
    """Per placeholders.md: cmake stanza should precede python stanza in Dockerfile.

    Reasoning: Python pip may pull native extensions that need the C++ toolchain.
    """
    dockerfile = project_dir / "docker" / "Dockerfile"
    if not dockerfile.is_file():
        steps.achieve("stanza ordering (cmake before python)", False,
                      difficulty="challenging",
                      detail="Dockerfile missing",
                      session_id=session_id, phase="Content")
        return
    text = dockerfile.read_text()
    cmake_match = re.search(r"g\+\+-13|gcc-13|cmake", text)
    python_match = re.search(r"python3-pip|python3", text)
    if cmake_match and python_match:
        ordered = cmake_match.start() < python_match.start()
    else:
        ordered = False
    steps.achieve(
        "stanza ordering (cmake before python)",
        passed=ordered,
        difficulty="challenging",
        detail=(f"cmake@{cmake_match.start() if cmake_match else 'missing'}, "
                f"python@{python_match.start() if python_match else 'missing'}"),
        session_id=session_id, phase="Content",
    )
