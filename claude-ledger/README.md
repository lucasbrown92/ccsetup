# claude-ledger

> **v1.0.1**

**Live capability map for Claude Code.** Converts the static `.claude/tool-ledger.md` into a live, queryable MCP server.

Instead of reading a stale markdown file at session start, call `ledger_context()` to get real-time health + active investigation state + recommended next tools in one call. Call `ledger_query("task")` to get an opinionated routing recommendation for any task.

## Tools

| Tool | Params | Purpose |
|------|--------|---------|
| `ledger_context` | *(none)* | Session-start briefing: health + active state + next steps |
| `ledger_query` | `task, healthy_only?` | Opinionated tool routing for any task — ordered call sequence |
| `ledger_mode` | `mode?` | Get or set token priority mode: `economy` \| `balanced` \| `performance` |
| `ledger_available` | `layer?, healthy_only?` | List all configured tools by layer with health status |
| `ledger_health` | `tool?` | Real-time health check (rechecks binary/file/hook existence now) |
| `ledger_diagnose` | `tool?` | Full prerequisite diagnosis — root cause + fix steps for degraded tools |
| `ledger_fix` | `tool` | Auto-apply fixable issues: missing hooks, env vars, Serena language drift |
| `ledger_workflows` | `tag?` | Canonical workflow patterns (debug, visual, investigation, agent-spawn…) |
| `ledger_catalog` | `mcp_key?, configured_only?` | Full tool signatures for one or all MCP servers |
| `ledger_rules` | `section?` | Operational playbook: anti-patterns, mandatory gates, priority chains, token habits |
| `ledger_preflight` | `change, files?, change_type?` | Pre-change synthesis across charter + mind + witness + retina → CLEAR/CAUTION/BLOCKED |
| `ledger_correlate` | `query, scope?` | Unified cross-tool search — everything known about a topic across all cognitive tools |

## Session Start

Replace reading `tool-ledger.md` with:

```
1. ledger_context()    → health + active state + recommended next tools
2. Follow RECOMMENDED NEXT steps from the output
```

Example output:
```
Ledger context (2026-03-17 14:32):

CONFIGURED TOOLS: 9 (8 healthy, 1 degraded)
  Degraded: leann-server — binary leann_mcp not found

ACTIVE STATE:
  claude-mind:    Investigation 'open' — "debug auth regression" (12 nodes, 3 open)
  claude-charter: 8 active entries (3 invariants, 2 constraints, 3 goals)
  claude-witness: 3 recent runs (last: 09:11, 2 failures)
  claude-retina:  4 captures, 2 baselines (homepage-desktop, login-dark)

RECOMMENDED NEXT:
  1. mind_summary()      → open investigation needs attention
  2. witness_hotspots()  → 2 recent test failures
  3. charter_summary()   → review project constraints

MISSING (run ccsetup to add):
  - claude-ledger: live capability map (run: ccsetup . --from-layer 5)
```

## Routing

```python
ledger_query("debug failing test")
# → 1. claude-witness (0.85) — Execution memory: what actually ran, exceptions
# → 2. claude-mind (0.42) — Reasoning board for multi-session investigation
# → 3. serena (0.21) — Semantic navigation to find relevant symbols

ledger_query("check what the UI looks like")
# → 1. claude-retina (0.91) — Visual browser automation: screenshots, diffs
# → 2. serena (0.15) — Find HTML/CSS symbols in the codebase
```

## Storage

No persistent state. Reads from CWD at runtime:
- `.mcp.json` — configured servers
- `.claude/mind.json` — investigation state
- `.claude/charter.json` — project constitution
- `.claude/witness/` — test run records
- `.claude/retina/retina.json` — visual capture history

## Installation

```bash
# Installed by ccsetup / bash install.sh to:
# ~/.local/share/ccsetup/claude-ledger/server.py

# No additional deps — stdlib only
```

## Relationship to tool-ledger.md

`tool-ledger.md` is kept as a human-readable static snapshot (audit artifact). claude-ledger is the live, queryable version. When claude-ledger is configured, it replaces the need to read `tool-ledger.md` at session start.
