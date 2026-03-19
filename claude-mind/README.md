# claude-mind

Persistent investigation reasoning board for Claude.

## What it is

An MCP server that externalizes investigation reasoning into a queryable store.
When debugging a complex problem across multiple sessions, `claude-mind` preserves
your hypotheses, confirmed facts, ruled-out paths, and flagged assumptions — so you
don't reconstruct the same state after every context compaction.

The key insight: the most dangerous bugs come from **assumptions** you stopped
questioning. `claude-mind` makes them explicit, flags them, and tracks whether
they've been verified.

## Install

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "claude-mind": {
      "command": "python",
      "args": ["/absolute/path/to/claude-mind/server.py"]
    }
  }
}
```

Restart Claude Code. The 7 `mind_*` tools will appear in the tool list.

## Tools

| Tool | Description |
|------|-------------|
| `mind_open(title)` | Start or resume an investigation |
| `mind_add(type, content, ...)` | Add a reasoning node |
| `mind_update(node_id, status, notes?)` | Update a node's status |
| `mind_query(filter)` | Query nodes by type, status, or text |
| `mind_summary()` | ≤15-line recovery briefing |
| `mind_resolve(conclusion, node_ids?)` | Close investigation with conclusion |
| `mind_import_witness(fn_name, run_id?)` | Import witness trace as a FACT node |

### Cross-tool evidence references

`mind_add` and `mind_import_witness` support structured evidence IDs:

```python
# Reference a specific witness call
mind_add("fact", "process() raises ValueError when x=None",
         evidence_ids=["witness:20260317_081903_cae3bf:c00001"])

# Reference a charter entry
mind_add("constraint", "this change is blocked by stdlib constraint",
         evidence_ids=["charter:bbb00002"])
```

These are displayed with `[W]` (witness) and `[C]` (charter) labels in `mind_query` output.

### Node types

| Type | When to use |
|------|-------------|
| `hypothesis` | Candidate explanation — set `confidence` 0–1 |
| `fact` | Confirmed finding with evidence |
| `question` | Open probe to investigate |
| `assumption` | ⚠ Treating as true, **unverified** — flagged as risk |
| `ruled_out` | Explicitly eliminated path + reason |
| `next_step` | Concrete action queued |

### `mind_query` filter options

- Type name: `hypothesis`, `assumptions`, `facts`, `ruled_out`, `next_steps`, etc.
- Status: `open`, `confirmed`, `refuted`, `suspended`, `escalated`
- `all` — everything
- Free text — searches content and notes

## Storage

State lives in `.claude/mind.json` in your project root. Human-readable JSON;
safe to inspect by hand. Override the directory:

```bash
CLAUDE_MIND_DIR=.mydir python server.py
```

## Example workflow

```python
mind_open("payment bug — amount=None on some carts")

mind_add("assumption", "amount=None only happens on empty carts", files=["checkout.py"])
mind_add("hypothesis", "checkout.finalize() doesn't guard None before process_payment",
         confidence=0.7)
mind_add("next_step", "Add logging in process_payment to capture amount at entry")

# After investigating:
mind_update("a1b2c3d4", "confirmed",
            notes="confirmed via witness trace: 2/47 runs hit this path")
mind_update("e5f6g7h8", "refuted",
            notes="empty cart guard is in place at line 88")

mind_add("fact", "amount=None originates in checkout.finalize() when shipping address is unset")

mind_resolve(
    "root cause: missing None guard in checkout.finalize() for unset shipping address",
    node_ids=["a1b2c3d4"]
)
```

### After context compaction

```python
mind_summary()
# ═══ MIND SUMMARY ═══
# Investigation: payment bug — amount=None on some carts
# Opened: 2026-03-17  |  Nodes: 6 total
#
# HYPOTHESES — open (1):
#   [e5f6g7h8] [70%] checkout.finalize() doesn't guard None before process_payment
#
# ⚠  ASSUMPTIONS — unverified risks (1):
#   [a1b2c3d4] amount=None only happens on empty carts
#
# NEXT STEPS (1):
#   [c3d4e5f6] Add logging in process_payment to capture amount at entry
```

## Full trifecta workflow

```python
# 1. Open investigation
mind_open("payment bug — amount=None on some carts")
mind_add("assumption", "amount=None only on empty cart",
         files=["checkout.py"])

# 2. Run tests
#    $ pytest --witness

# 3. Query execution evidence
# witness_traces("process_payment", status="exception")
# → confirms: x=None called from checkout.finalize() in 2 tests

# 4. Import witness evidence into mind
mind_import_witness("process_payment")
# → creates FACT [abc12345]: witness:run_id — process_payment called 47x; 2 raised exception

# 5. Check proposed fix against charter
# charter_check("add None guard in process_payment before amount * rate")
# → no conflicts

# 6. Update assumption with confirmed evidence
mind_update("assumption_id", "confirmed",
            notes="witness run confirmed: 2/47 runs hit this path")

# 7. Recover after compaction
mind_summary()
# ═══ MIND SUMMARY ═══  (full state in <15 lines)
```

## Design notes

- **stdlib only** — no external deps; copy anywhere
- **stdio MCP** — simplest transport, no HTTP server needed
- **≤6 node types** — no ontology creep; stays useful
- **One active investigation** — focused; old ones archive to history in `mind.json`
- **`assumption` is a distinct type** from `hypothesis` — it's something you're
  already building on, not something you're testing. The highest-risk category.
