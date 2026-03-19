# claude-afe — Agentic Field Engine

Cognitive compiler for Claude Code. Transforms task descriptions into precisely-tuned agent specifications using the AFE operator matrix (9 coins, 8 functions, 4 animals, 3 regimes).

**Version:** 1.0.0 | **Stdlib only** | **stdio MCP transport**

---

## What It Does

When Claude receives a complex task, AFE answers: *what kind of agent should exist for this work?*

- **Reads** the task, consults mind/charter/witness for cross-tool context
- **Selects** a function bundle (Se/Si/Ne/Ni/Te/Ti/Fe/Fi with M/F modality)
- **Sequences** animal workflow phases (Consume → Blast → Play → Sleep)
- **Guards** against distortion (ahrimanic = over-compression, luciferic = over-expansion)
- **Produces** a system prompt fragment ready to inject when spawning the Agent tool

Claude is the intelligence. AFE is the compiler. The split is intentional.

---

## Quick Start

```bash
# Add to .mcp.json (see below), then in any Claude session:

afe_context()                           # see mind/charter/witness state
afe_templates(domain: "CoreLogic")      # browse templates
afe_compile(task: "debug auth middleware")   # compile a spec
afe_validate(spec_id: "abc123")         # check against charter
# use spec's system_prompt_fragment when spawning Agent tool
```

For multi-phase work:
```bash
afe_ecology(task: "full feature build for user profiles")
# → 4-phase agent chain: explore → plan → implement → review
```

---

## .mcp.json Entry

```json
{
  "mcpServers": {
    "claude-afe": {
      "type": "stdio",
      "command": "python3",
      "args": ["/absolute/path/to/claude-afe/server.py"],
      "env": {}
    }
  }
}
```

Environment override: `CLAUDE_AFE_DIR` (default: `.claude`)

---

## 7 Tools

| Tool | Purpose | Key Params |
|------|---------|------------|
| **`afe_compile`** | Core compiler: task → agent spec | `task` (req), `regime`, `template`, `domain`, `locus`, `modality` |
| **`afe_templates`** | Browse/search template registry | `regime`, `domain`, `filter` |
| **`afe_inspect`** | Full detail of a spec or template | `id` (req) |
| **`afe_validate`** | Check spec against charter + coherence | `spec_id` (req) |
| **`afe_ecology`** | Multi-agent task → sequenced chain | `task` (req), `phases` |
| **`afe_context`** | Context from mind/charter/witness | `include` (array) |
| **`afe_history`** | List past compilations | `limit`, `filter` |

---

## Template Registry (11 templates)

**Synthetic (impossible types — engineered for tasks):**
- `planner` — Full NT (Te-M, Ni-M, Ti-F, Ne-F) | Sleep→Consume→Blast | MM — architecture, system design
- `module_writer` — Full ST (Te-M, Si-M, Ti-M, Se-F) | Blast→Sleep | MM — implementation to spec
- `interface_agent` — Full SF (Fe-F, Se-M, Fi-F, Ne-F) | Play→Consume→Blast | FM — UI/UX review
- `narrative_agent` — Full NF (Ne-F, Fe-F, Ni-M, Fi-F) | Consume→Blast | FF — documentation
- `groundwork_agent` — Full ST (Te-M, Se-M, Ti-M, Si-M) | Play→Blast→Sleep | MM — infrastructure
- `systems_refactorer` — NT discernment (Ti-M, Ni-F, Te-F, Ne-F) | Consume→Sleep→Blast | MF — refactoring

**Orchestration (meta-level):**
- `orchestrator` — (Ni-M, Te-M, Ne-F, Ti-F) | Consume→Sleep→Blast | MM

**Canonical (human-natural 512):**
- `canonical_explorer` — FF-Ne/Fi | Consume→Blast — ideation, territory mapping
- `canonical_enforcer` — MM-Te/Si | Blast→Sleep — standards enforcement
- `canonical_diplomat` — FM-Fe/Ni | Play→Sleep — API contracts, interfaces
- `canonical_debugger` — MF-Ti/Se | Sleep→Play — debugging, root cause analysis

---

## Compiler Pipeline (11 stages)

```
Task Intake → Context Read (mind/charter/witness)
    → Locus ID (Awareness/Intention/Capability/Energy)
    → Domain × Channel
    → Regime Selection (canonical/synthetic/orchestration)
    → Function Bundle (template match or custom)
    → Animal Order (from locus + template)
    → Modality (MM/MF/FM/FF)
    → Distortion Guards (template + charter prohibitions)
    → System Prompt Fragment
    → Tool Scoping (per animal phase)
```

### Auto-detection

If you don't pass `regime`, `template`, `domain`, `locus`, or `modality`, the compiler detects from task keywords:

| Keywords | Detected |
|----------|---------|
| "why", "understand", "debug" | Locus: Awareness |
| "design", "plan", "architect" | Locus: Intention |
| "implement", "write", "build" | Locus: Capability |
| "review", "refactor", "test" | Locus: Energy |
| "infrastructure", "docker", "ci" | Domain: Infrastructure |
| "ui", "ux", "frontend" | Domain: Interface |
| "api", "auth", "middleware" | Domain: Integration |

---

## Cross-Tool Integration

Evidence labeling: `[A]afe:<spec_id>` — consistent with `[W]witness:...`, `[C]charter:...`, `[M]mind:...`

**Feed-forward:**
- Charter prohibitions → injected as `scope_limit` in distortion guards
- Mind assumptions → flagged in `evidence_ids` as unverified dependencies
- Witness failures → influence domain classification

**Typical flow:**
```
afe_context()          # see active investigation, constraints, test state
afe_compile(task)      # compile spec (auto-reads cross-tool context)
afe_validate(spec_id)  # check against charter
→ use system_prompt_fragment when spawning Agent tool
```

---

## Storage

`.claude/afe.json`:
```json
{
  "specs":     [],   // max 50, FIFO eviction to history
  "ecologies": [],   // max 20
  "history":   []    // max 100
}
```

---

## ccsetup Integration

**Layer:** 5 (Orchestration) — alongside seu-claude, Switchboard

**Health states:** `healthy | configured_only | missing_binary | not_configured | skipped`

**Health check:** `python3 claude-afe/server.py` responds to `initialize`

---

## Files

```
claude-afe/
    server.py     — MCP transport, tool dispatch, TOOLS schema
    schema.py     — Enums, make_spec(), coin derivation, formatting
    store.py      — Atomic load/save to .claude/afe.json
    templates.py  — 11 template definitions + matching logic
    compiler.py   — 11-stage pipeline + ecology compilation
    README.md     — This file
```

---

## Verification

```bash
# 1. Server responds to initialize
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | python3 claude-afe/server.py

# 2. Tools list returns 7 tools
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 claude-afe/server.py

# 3. Compile a spec
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"afe_compile","arguments":{"task":"debug the auth middleware"}}}' \
  | python3 claude-afe/server.py

# 4. Browse templates
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"afe_templates","arguments":{}}}' \
  | python3 claude-afe/server.py
```
