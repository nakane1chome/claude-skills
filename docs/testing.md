# Testing Skills

Skills are different to normal software. Testing of skills is more like characterization than traditional software testing.

- Testing should be repeatable. As models evolve and skills are refined a baseline capability should be maintained.
- Testing should be done across a range of models.
- Some outcomes are objectively testable.
- Some outcomes are testable but require some intelligence in the loop.
- Some outcomes are subjective.
- The case of not using the skill should be tested — what are the outcomes when using minimal or ad-hoc prompts?

It should be acknowledged that some key goals can't be tested:
- User experience

The tests here use pytest with the `claude-test-fw` framework.


## Check Classes

Every test assertion belongs to one of three classes. The class determines what happens on failure and how the result is reported.

### require

**Prefix:** `steps.require_`
**On failure:** Aborts the test.
**Terminology:** PASS / FAIL

Use for infrastructure prerequisites that the test cannot continue without. If a session returns an error or no result message, there is nothing to evaluate — the test must stop.

Examples:
- Session completed without error
- ResultMessage exists
- Session ID returned

### expect

**Prefix:** `steps.expect_`
**On failure:** Records FAIL, test continues.
**Terminology:** PASS / FAIL

Use for prompted deliverables — things the prompt explicitly asked the model to produce. Not achieving these is a failure, but the test should still run remaining checks to collect the full picture.

Examples:
- "Create library.py" → library.py exists
- "Create a database" → .db file exists
- "Run pytest" → test files exist
- ">= 4 of 6 seeded issues found" (prompt asked for review)

### achieve

**Prefix:** `steps.achieve_`
**On failure:** Records NOT ACHIEVED, test continues.
**Terminology:** ACHIEVED / NOT ACHIEVED
**Weighted by:** difficulty tier

Use for quality and approach indicators — how well the model followed the skill's guidance, not just whether it produced output. These are scored with difficulty weights and rolled up into an achievement percentage.

Examples:
- Used DBML as data model format (skill recommended it)
- Jinja2 import found in generator code
- Individual seeded issue detected (review quality)
- No generator artifacts in baseline (approach purity)


## Difficulty Tiers

Difficulty tiers weight achieve checks to produce a meaningful achievement score. A test that achieves all "expected" checks but misses "aspirational" ones should score higher than one that achieves some of each randomly.

| Tier | Weight | Meaning |
|------|--------|---------|
| `"expected"` | 1.0 | All model tiers should achieve this |
| `"challenging"` | 0.5 | Mid-tier and above expected; weak tier may miss |
| `"aspirational"` | 0.25 | Only strongest tier expected; bonus for weaker tiers |

The achievement percentage is: `sum(weights of achieved) / sum(all weights) * 100`.


## Scoring

Every test reports two scores:

1. **Hard: PASS/FAIL (n/m)** — require + expect checks. All must pass for PASS.
2. **Achievement: X%** — weighted achieve checks. Higher is better.

These appear in:
- pytest console output (via report teardown)
- JSON report (`scores` field)
- Markdown summary (header line)
- HTML audit report (banner)
- Index page (per-test cell)


## When to Use Each Class

| Situation | Class | Reasoning |
|-----------|-------|-----------|
| Session crashed | `require_` | Can't evaluate anything else |
| Prompt said "create X" and X doesn't exist | `expect_` | Explicit deliverable not met — failure, but check other things |
| Prompt said "create X" and X exists | `expect_` | PASS |
| Skill recommended approach Y but model used Z | `achieve_` | Quality of approach, not a hard requirement |
| Model detected 3 of 6 issues | `achieve_` per issue | Each is a quality indicator |
| Model detected >= 4 of 6 issues (threshold) | `expect_` | The prompt asked for a thorough review |
| Baseline has no skill artifacts | `achieve_` | Approach purity — nice to confirm |
| Audit events exist | `expect_` | The instrumentation should capture data |
| Token metrics present | `achieve_` | Environment-dependent — not always available |


## MCP Servers in Tests

Tests can optionally inject MCP servers into Claude sessions. The framework provides two mechanisms: a marker for arbitrary servers and a convenience fixture for mempalace.

### Using the marker

Declare MCP servers a test requires with `@pytest.mark.mcp`. Tests are automatically skipped if any declared server is unavailable (command not on PATH or module not installed).

```python
@pytest.mark.mcp(servers={
    "myserver": {"command": "python", "args": ["-m", "myserver"]},
})
async def test_with_custom_mcp(instrumented_project, mcp_servers, steps):
    project, query_fn = instrumented_project
    msgs = await query_fn("do something", mcp_servers=mcp_servers)
```

The `mcp_servers` fixture reads the marker and returns the dict, ready to pass as an override to `query_fn` or `query_fn.conversation()`. For mempalace specifically, prefer the `mempalace_mcp` fixture which handles data isolation automatically.

### Mempalace convenience fixture

For the common case of mempalace, use the `mempalace_mcp` fixture directly — no marker needed:

```python
async def test_with_mempalace(instrumented_project, mempalace_mcp, steps):
    project, query_fn = instrumented_project
    msgs = await query_fn("do work", mcp_servers=mempalace_mcp)
```

Skips automatically if mempalace is not installed. Each test gets its own isolated ChromaDB and knowledge graph in `tmp_path/mempalace/`.

### Adding other MCP servers

To add a new convenience fixture for another MCP server:

1. Define a config builder in `_mcp.py` (follow the `_mempalace_config()` pattern)
2. Add a fixture that checks availability and returns the config
3. Register the fixture in `plugin.py`
4. If the server has persistent state, point it at `tmp_path` for isolation

### Server lifecycle and isolation

**Transport:** MCP servers use stdio (stdin/stdout pipes) — no ports, no conflicts. The Claude SDK spawns a fresh server process per session. Each `query_fn()` call or `conversation()` context manager creates a new session, so servers start and stop automatically. No manual cleanup is needed.

**Data isolation:** The `mempalace_mcp` fixture points the server at `tmp_path/mempalace/` via the `--palace` CLI flag. Each test gets its own ChromaDB database and SQLite knowledge graph. Tests never share memory state.

**Config isolation:** The test sandbox uses `setting_sources=["project"]`, which excludes user-level MCP servers from `~/.claude/settings.json`. Only servers explicitly passed via the `mcp_servers` override are available. The host system's MCP configuration does not leak into tests.
