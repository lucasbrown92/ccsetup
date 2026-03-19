# claude-charter

> **v1.0.1**

Normative project constitution store — standalone MCP server.

## What It Does

Tracks invariants, constraints, non-goals, contracts, and goals for a project. The primary usage pattern is `charter_check`: before making a structural change, call it with a plain-language description and get back any conflicts with active charter entries.

```python
charter_check("remove stdlib constraint, add httpx for cleaner HTTP",
              change_type="add_dependency")
# → CONFLICTS (1):
#   [a1b2c3d4] CONSTRAINT: stdlib only, no third-party deps — rationale: copy-anywhere portability
```

## Tools

| Tool | Description |
|------|-------------|
| `charter_add(type, content, notes?, scope?, expires_at?, deadline?)` | Add an invariant, constraint, non_goal, contract, or goal. `expires_at` and `deadline` accept ISO datetimes for time-bounded entries. |
| `charter_update(id, status?, content?, notes?)` | Modify or archive an entry |
| `charter_query(filter)` | Show entries — by type, status, keyword, or `"all"` |
| `charter_summary()` | Full project constitution — use at session start |
| `charter_check(change_description, file_path?, change_type?)` | Conflict-check a proposed change. `change_type` (add_dependency \| remove_feature \| change_interface \| refactor) boosts relevant entry types 2× for sharper detection. |
| `charter_audit()` | Health report: gaps, imbalances, prohibited patterns, expired entries, past-deadline goals |

## Entry Types

| Type | Meaning |
|------|---------|
| `invariant` | Must always be true: `"auth layer never calls DB directly"` |
| `constraint` | Implementation rule: `"stdlib only, no third-party deps"` |
| `non_goal` | Explicitly out of scope: `"no client-side state management"` |
| `contract` | API/interface guarantee: `"GET /health returns 200 within 50ms"` |
| `goal` | Active objective: `"ship v5 claude-charter MCP by 2026-03-17"` |

## Storage

`.claude/charter.json` in the target project directory. Override with `CLAUDE_CHARTER_DIR` env var. Human-readable JSON — safe to inspect and edit directly.

## Install

Add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "claude-charter": {
      "command": "python",
      "args": ["/path/to/claude-charter/server.py"],
      "env": {}
    }
  }
}
```

Or with a relative path if running from the same repo:

```json
{
  "claude-charter": {
    "command": "python",
    "args": ["claude-charter/server.py"]
  }
}
```

## Usage Pattern

```python
# Session start
charter_summary()

# Before any structural change — pass change_type for 2× scoring boost
charter_check("switch from JSON config to TOML", change_type="change_interface")

# Adding entries
charter_add("invariant", "config files are human-editable without tooling")
charter_add("constraint", "stdlib only — no third-party deps", notes="copy-anywhere portability")
charter_add("non_goal", "multi-user or networked deployment")

# Time-bounded entries
charter_add("goal", "ship v2 API by end of sprint",
            deadline="2026-04-01T00:00:00Z")
charter_add("constraint", "no breaking changes until migration window",
            expires_at="2026-06-01T00:00:00Z")

# Archiving a completed goal
charter_update("abc12345", status="archived")

# Periodic health check — shows expired entries and past-deadline goals
charter_audit()
```

## Stdlib Only

Zero external dependencies. Python 3.8+. Works anywhere Python runs.
