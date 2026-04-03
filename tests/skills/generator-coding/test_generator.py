"""Test: generator-coding skill steers toward template-based generation vs direct SQL.

Two parametrized variants with the same task (SQLite book library):
- with_skill: should adopt DBML data model + Jinja2 templates + generator pipeline
- baseline: should write SQL DDL directly in Python (no DBML, no templates)

Each variant uses a multi-turn conversation: plan first, then implement in the
same session so the plan context carries over.
"""

import re
from pathlib import Path

import pytest
from claude_agent_sdk.types import ResultMessage


# -- Prompts per variant -------------------------------------------------------

TASK_BODY = """\
Create a small SQLite book-library system with these tables:

- **authors** (id, name, birth_year)
- **books** (id, title, isbn, author_id FK)
- **borrowers** (id, name, email)
- **loans** (id, book_id FK, borrower_id FK, loan_date, return_date nullable)

Then create a Python program `library.py` that:
- Creates the database and tables
- Inserts 3 sample authors, 5 books, and 2 borrowers
- Records 2 loans (one returned, one active)
- Prints a report of all active loans with book title and borrower name
"""

PLAN_SKILL = f"""\
Use the generator-coding skill to approach this task.

Use DBML as the data model format and Jinja2 as the template engine.
Write a generator that reads the DBML and produces the Python SQLite code.

{TASK_BODY}
Create a plan for this.
"""

PLAN_BASELINE = f"""\
{TASK_BODY}
Create a plan for this.
"""

IMPL_SKILL = """\
Now implement your plan.

Use DBML as the data model and Jinja2 templates to generate the Python SQLite code.
Follow the generator-coding skill: data model -> parser -> helpers -> templates -> output.

Create all files in the current directory and run the final library.py to verify it works.
"""

IMPL_BASELINE = """\
Now implement your plan.

Create all files in the current directory and run library.py to verify it works.
"""

VARIANTS = {
    True: {
        "plan_prompt": PLAN_SKILL,
        "impl_prompt": IMPL_SKILL,
    },
    False: {
        "plan_prompt": PLAN_BASELINE,
        "impl_prompt": IMPL_BASELINE,
    },
}


# -- Test ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "project_env",
    [True, False],
    ids=["with_skill", "baseline"],
    indirect=True,
)
async def test_library_generator(
    project_env, steps, sdk, model, model_alias, report, audit,
):
    """Generator-coding skill vs baseline: SQLite book-library task."""
    project_dir, claude_query = project_env
    has_skill = (project_dir / ".claude" / "skills" / "generator-coding").is_dir()
    variant = VARIANTS[has_skill]

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    # Multi-turn conversation: plan then implement in the same session
    async with claude_query.conversation(max_turns=30) as conv:
        # ---- Phase 1: Plan ----
        plan_messages = await conv.say(variant["plan_prompt"])

        plan_results = [m for m in plan_messages if isinstance(m, ResultMessage)]
        if plan_results:
            plan_session_id = plan_results[-1].session_id
            report.add(plan_session_id, sdk.metrics(plan_messages), phase="Plan")
        sdk.log_phase("Plan", plan_messages, project_dir)

        # ---- Phase 2: Implement ----
        impl_messages = await conv.say(variant["impl_prompt"])

    all_messages = conv.messages
    results = [m for m in all_messages if isinstance(m, ResultMessage)]
    result = results[-1] if results else None

    # require_: session must complete — abort if not
    steps.require_session_ok(all_messages, phase="Implement")

    session_id = result.session_id
    label = "with skill" if has_skill else "baseline"

    # Finalize audit and record metrics
    audit.finalize(project_dir, session_id)
    report.add(session_id, sdk.metrics(impl_messages), phase="Implement")
    sdk.log_phase(f"Implement ({label})", impl_messages, project_dir)

    # ---- Check artifacts ----
    if has_skill:
        _check_generator_artifacts(steps, project_dir, session_id)
    else:
        _check_baseline_artifacts(steps, project_dir, session_id)


# -- Check helpers -------------------------------------------------------------

def _check_generator_artifacts(steps, project_dir, session_id):
    """With skill: expect DBML + Jinja2, achieve generator quality."""
    # expect_: prompt asked to use DBML and Jinja2
    steps.expect_files_exist(project_dir, ["*.dbml"],
                             session_id=session_id, phase="Artifacts")
    steps.expect_files_exist(project_dir, ["*.jinja2", "*.j2", "*.jinja"],
                             session_id=session_id, phase="Artifacts")

    # achieve_: quality of generator approach
    all_files = [
        str(p.relative_to(project_dir))
        for p in project_dir.rglob("*")
        if p.is_file() and ".git" not in p.parts and ".claude" not in p.parts
    ]
    gen_files = [f for f in all_files if re.search(r"gen", f, re.IGNORECASE)]
    steps.achieve("generator script present", len(gen_files) > 0,
                  difficulty="challenging", session_id=session_id, phase="Artifacts",
                  detail=f"generator files: {gen_files}")

    has_library = any("library" in f.lower() for f in all_files)
    steps.achieve("library output present", has_library,
                  difficulty="expected", session_id=session_id, phase="Artifacts")

    steps.achieve_file_contains(project_dir, "*.py", r"jinja2|from jinja",
                                difficulty="challenging",
                                flags=re.IGNORECASE,
                                session_id=session_id, phase="Artifacts")


def _check_baseline_artifacts(steps, project_dir, session_id):
    """Without skill: expect library.py with inline SQL."""
    # expect_: prompt asked for library.py
    steps.expect_files_exist(project_dir, ["library.py"],
                             session_id=session_id, phase="Artifacts")
    steps.expect_file_contains(project_dir, "*.py", r"CREATE\s+TABLE",
                               flags=re.IGNORECASE,
                               session_id=session_id, phase="Artifacts")

    # achieve_: baseline should not have generator artifacts
    steps.achieve_files_absent(project_dir, ["*.dbml"],
                               difficulty="expected",
                               session_id=session_id, phase="Artifacts")
    steps.achieve_files_absent(project_dir, ["*.jinja2", "*.j2", "*.jinja"],
                               difficulty="expected",
                               session_id=session_id, phase="Artifacts")
