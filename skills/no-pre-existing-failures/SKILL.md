---
name: no-pre-existing-failures
description: >
  Test accountability policy. All failures belong to the current changeset.
  Commits must include test results. No failures on main.
user-invocable: false
---

1. **Every test failure is caused by your changes.** There are no "pre-existing," "known," "flaky," or "unrelated" failures. If a test fails, you broke it. Fix it before proceeding.

2. **Every git commit must include a test summary.** On `main`, all tests must pass — no exceptions. On branches, failures are permitted only if explicitly noted in the commit message with the failure name and reason.
