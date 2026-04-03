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
    project_env, sdk, model, model_alias, report, audit,
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
            report.check("plan session_id returned", True,
                         session_id=plan_session_id, phase="Plan")
            report.add(plan_session_id, sdk.metrics(plan_messages), phase="Plan")
        sdk.log_phase("Plan", plan_messages, project_dir)

        # ---- Phase 2: Implement ----
        impl_messages = await conv.say(variant["impl_prompt"])

    all_messages = conv.messages
    results = [m for m in all_messages if isinstance(m, ResultMessage)]
    result = results[-1] if results else None
    assert result is not None, "No ResultMessage returned"
    assert not result.is_error, (
        f"Session ended with error: {sdk.text(all_messages)[-500:]}"
    )

    session_id = result.session_id
    label = "with skill" if has_skill else "baseline"
    report.check("no error", not result.is_error,
                 session_id=session_id, phase="Implement")

    # ClaudeSDKClient may not trigger SessionEnd hook — finalize manually
    audit.finalize(project_dir, session_id)

    report.add(session_id, sdk.metrics(impl_messages), phase="Implement")
    sdk.log_phase(f"Implement ({label})", impl_messages, project_dir)

    # ---- Collect project files ----
    all_files = [
        str(p.relative_to(project_dir))
        for p in project_dir.rglob("*")
        if p.is_file() and ".git" not in p.parts and ".claude" not in p.parts
    ]
    all_files_lower = [f.lower() for f in all_files]
    all_files_str = "\n".join(all_files)

    if has_skill:
        _assert_generator_artifacts(report, session_id, project_dir,
                                    all_files, all_files_lower, all_files_str)
    else:
        _assert_baseline_artifacts(report, session_id,
                                   all_files, all_files_lower, project_dir)


# -- Assertion helpers ---------------------------------------------------------

def _assert_generator_artifacts(report, session_id, project_dir,
                                all_files, all_files_lower, all_files_str):
    """With skill: expect DBML + Jinja2 + generator script."""
    has_dbml = any(f.endswith(".dbml") for f in all_files_lower)
    report.check("DBML data model present", has_dbml,
                 session_id=session_id, phase="Artifacts",
                 detail=f"files: {all_files_str}")

    has_jinja = any(
        f.endswith(".jinja2") or f.endswith(".j2") or f.endswith(".jinja")
        for f in all_files_lower
    )
    report.check("Jinja2 template present", has_jinja,
                 session_id=session_id, phase="Artifacts",
                 detail=f"files: {all_files_str}")

    gen_files = [f for f in all_files if re.search(r"gen", f, re.IGNORECASE)]
    report.check("generator script present", len(gen_files) > 0,
                 session_id=session_id, phase="Artifacts",
                 detail=f"generator files: {gen_files}")

    has_library = any("library" in f.lower() for f in all_files)
    report.check("library output present", has_library,
                 session_id=session_id, phase="Artifacts",
                 detail=f"files: {all_files_str}")

    jinja_import_found = False
    for f in project_dir.rglob("*.py"):
        if ".git" in f.parts or ".claude" in f.parts:
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "jinja2" in content.lower() or "from jinja" in content.lower():
            jinja_import_found = True
            break
    report.check("Jinja2 used in Python code", jinja_import_found,
                 session_id=session_id, phase="Artifacts")

    assert has_dbml, (
        f"Expected a .dbml data model file with generator-coding skill. "
        f"Files: {all_files}"
    )
    assert has_jinja, (
        f"Expected a .jinja2 template file with generator-coding skill. "
        f"Files: {all_files}"
    )


def _assert_baseline_artifacts(report, session_id,
                                all_files, all_files_lower, project_dir):
    """Without skill: expect inline SQL, no DBML/templates."""
    has_library = any("library" in f.lower() and f.endswith(".py") for f in all_files)
    report.check("library.py present", has_library,
                 session_id=session_id, phase="Baseline Artifacts",
                 detail=f"files: {all_files}")

    sql_in_python = False
    for f in project_dir.rglob("*.py"):
        if ".git" in f.parts or ".claude" in f.parts:
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "sqlite3" in content and re.search(r"CREATE\s+TABLE", content, re.IGNORECASE):
            sql_in_python = True
            break
    report.check("inline SQL in Python", sql_in_python,
                 session_id=session_id, phase="Baseline Artifacts")

    has_dbml = any(f.endswith(".dbml") for f in all_files_lower)
    has_jinja = any(
        f.endswith(".jinja2") or f.endswith(".j2") or f.endswith(".jinja")
        for f in all_files_lower
    )
    report.check("no DBML (baseline)", not has_dbml,
                 session_id=session_id, phase="Baseline Artifacts",
                 detail="absent as expected" if not has_dbml else "unexpectedly present")
    report.check("no Jinja2 templates (baseline)", not has_jinja,
                 session_id=session_id, phase="Baseline Artifacts",
                 detail="absent as expected" if not has_jinja else "unexpectedly present")

    assert has_library, (
        f"Expected library.py in baseline output. Files: {all_files}"
    )
    assert sql_in_python, (
        f"Expected inline SQL (CREATE TABLE) with sqlite3 in baseline. "
        f"Files: {all_files}"
    )
