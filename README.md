# ccsetup

**Per-repo Claude Code stack bootstrapper.** Run `ccsetup .` from any project directory to configure a curated hierarchy of Claude Code enhancement tools — interactively, via yes/no prompts for each layer.

Design philosophy: **Claude is the primary user.** Every tool is evaluated from the perspective of "does this make Claude more capable, more informed, or safer as an autonomous agent?"

---

## Install

```bash
git clone https://github.com/lucasbrown92/ccsetup
cd ccsetup
bash install.sh
```

`install.sh` copies `ccsetup` to `~/.local/bin` and bundles all MCP servers to `~/.local/share/ccsetup/`. It will offer to add `~/.local/bin` to your PATH if needed.

**Requirements:** Python 3.9+, [uv](https://docs.astral.sh/uv/) (for Serena), Node.js / npx (for several tools)

---

## Usage

```bash
ccsetup .                          # interactive setup, then launch Claude Code
ccsetup . --status                 # health-aware status report
ccsetup . --dry-run                # preview without writing anything
ccsetup . --preset minimal         # Layer 0 only (Serena + GrapeRoot)
ccsetup . --preset recommended     # Layers 0–2 + ccusage + cship
ccsetup . --preset maximal         # all stable layers
ccsetup . --experimental           # also enable experimental tools (see below)
ccsetup . --preset maximal --experimental   # everything
ccsetup . --from-layer 3           # resume from a specific layer
ccsetup . --setup                  # force re-run even if already configured
ccsetup . --continue               # launch Claude with --continue (passed through)
```

---

## Tool Layers

### Layer 0 — Foundation *(always-on)*

| Tool | What it does | Repo |
|------|-------------|------|
| **Serena** | IDE-like semantic codebase navigation via LSP — symbol search, definition/usage tracing, structured edits | [oraios/serena](https://github.com/oraios/serena) |
| **GrapeRoot** (`dgc`) | Precomputed dual graph of files, functions, imports, and calls. Pre-injects relevant context before Claude starts thinking | [kunal12203/Codex-CLI-Compact](https://github.com/kunal12203/Codex-CLI-Compact) |

---

### Layer 1 — Context Intelligence

| Tool | What it does | Repo |
|------|-------------|------|
| **dual-graph MCP** | Local context store with graph-aware retrieval and cross-session memory. `graph_continue` runs at session start and routes straight to relevant files | bundled with GrapeRoot |
| **LEANN** | Local-first semantic code search — AST-aware chunking, no cloud keys, retrieves code by meaning not exact text | `uv tool install leann-core --with leann` |
| **Context7** | Injects live, version-accurate library docs into context. Eliminates hallucinations from stale post-training API knowledge | [upstash/context7](https://github.com/upstash/context7) |
| **Claude Context** | Semantic search via Zilliz Cloud vector DB — enterprise-scale retrieval for very large repos | `npx @zilliz/claude-context-mcp@latest` |
| **claude-witness** ⚗️ | Runtime execution trace capture via `sys.settrace`. Queryable by function name, run, status, and cross-run diff | [bundled ↗](https://github.com/lucasbrown92/ccsetup/tree/main/claude-witness) |

---

### Layer 2 — Memory & Continuity

| Tool | What it does | Repo |
|------|-------------|------|
| **claude-session-mcp** | Lossless session clone, archive, restore, and cross-machine transfer | [chrisguillory/claude-session-mcp](https://github.com/chrisguillory/claude-session-mcp) |
| **context-mode** | Virtualizes tool outputs — keeps raw data out of context window, indexes locally for on-demand search | `npx -y context-mode` |
| **claude-mind** ⚗️ | Persistent investigation reasoning board — hypotheses, facts, ruled-out paths that survive context compaction | [bundled ↗](https://github.com/lucasbrown92/ccsetup/tree/main/claude-mind) |
| **claude-charter** ⚗️ | Project constitution store — invariants, constraints, non-goals. `charter_check()` flags violations before changes | [bundled ↗](https://github.com/lucasbrown92/ccsetup/tree/main/claude-charter) |

---

### Layer 3 — Safety & Guardrails *(manual setup)*

| Tool | What it does | Repo |
|------|-------------|------|
| **parry** | Prompt injection + data exfiltration scanner via PreToolUse hook. Blocks secret leakage from `~/.ssh`, `.env`, etc. | [anthropics/parry](https://github.com/anthropics/parry) |
| **claude-plan-reviewer** | Intercepts Claude's plan and sends it to a rival model (GPT-4, Gemini) for critique before execution | [anthropics/claude-plan-reviewer](https://github.com/anthropics/claude-plan-reviewer) |
| **TDD Guard** | Blocks file writes unless a failing test exists first. Hard-enforces Red-Green-Refactor | [anthropics/tdd-guard](https://github.com/anthropics/tdd-guard) |

---

### Layer 4 — Observability & Telemetry

| Tool | What it does | Repo |
|------|-------------|------|
| **ccusage** | Terminal dashboard for token usage and costs. Parses `~/.claude/*.jsonl` locally, zero cloud exfiltration | [ryoppippi/ccusage](https://github.com/ryoppippi/ccusage) |
| **claude-esp** | Streams Claude's hidden thinking blocks, tool calls, and subagent comms to a separate terminal in real time | [anthropics/claude-esp](https://github.com/anthropics/claude-esp) |
| **cclogviewer** | Converts Claude Code session logs into interactive HTML with nested task views and full tool-call chain transparency | [brads3290/cclogviewer](https://github.com/brads3290/cclogviewer) |
| **claudio** | Plays macOS system sounds on tool start/end — ambient awareness that a long task finished without watching the terminal | hooks only, no binary |
| **cship** | Live Claude Code metrics in your shell prompt — cost, context %, model name. Integrates with Starship | [cship.dev](https://cship.dev) |
| **claude-retina** ⚗️ | Visual browser automation via Playwright — screenshots, pixel diffs, accessibility trees, visual regression testing | [bundled ↗](https://github.com/lucasbrown92/ccsetup/tree/main/claude-retina) |

---

### Layer 5 — Orchestration & Scaling

| Tool | What it does | Repo |
|------|-------------|------|
| **seu-claude** | Persistent memory + task tracking + sandboxed execution + multi-agent orchestration | `npm install -g seu-claude` |
| **claude-ledger** ⚗️ | Live capability map — `ledger_context()` replaces static tool-ledger.md at session start with opinionated routing | [bundled ↗](https://github.com/lucasbrown92/ccsetup/tree/main/claude-ledger) |

---

### Layer 6 — Workflow Utilities

| Tool | What it does | Repo |
|------|-------------|------|
| **CodeGraphContext** | Indexes code into a knowledge graph for explicit relationship queries — callers, callees, call chains | `pip install codegraphcontext` |
| **claude-remote-approver** | Forwards tool approval prompts to your phone via ntfy.sh. Approve or deny commands remotely | [anthropics/claude-remote-approver](https://github.com/anthropics/claude-remote-approver) |
| **Smart Fork** | Semantic search across past Claude Code session transcripts. Turns session history into a knowledge base | [recursive-vibe/smart-fork](https://github.com/recursive-vibe/smart-fork) |
| **clui-cc** | Voice + TTS interface for Claude Code — speak prompts, hear responses | [lcoutodemos/clui-cc](https://github.com/lcoutodemos/clui-cc) |

---

## Experimental Tools ⚗️

Six bundled MCP servers are marked experimental — built and working but not yet broadly validated across diverse projects. Enable with `--experimental`:

```bash
ccsetup . --preset maximal --experimental   # everything
ccsetup . --experimental                    # just the experimental tools, interactively
```

In interactive mode they appear as normal opt-in prompts, labelled `[experimental]`. In `--status` output they're annotated in yellow. They're not auto-enabled by any preset.

All six are stdlib-only Python, no pip install required (except Playwright for retina). They're installed to `~/.local/share/ccsetup/` by `install.sh`.

---

## What gets written

Two config files are written to the **target repo** (not this one):

| File | Purpose |
|------|---------|
| `.mcp.json` | MCP server capability surface |
| `.claude/settings.local.json` | Hooks and local overrides |
| `.claude/ccsetup-report.md` | Post-run health manifest |

---

## Architecture

`ccsetup.py` is a **single-file, stdlib-only Python script**. No pip install required — copy it anywhere and run it.

---

## Development

```bash
pip install pytest
python -m pytest tests/ -v

python ccsetup.py . --dry-run
python ccsetup.py . --status
```

See `docs/tools-reference.md` for per-tool selection heuristics and architectural notes.
