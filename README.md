# ccsetup

**Per-repo Claude Code stack bootstrapper.** Run `ccsetup .` from any project directory to configure a curated hierarchy of Claude Code enhancement tools — interactively, via yes/no prompts for each layer.

Design philosophy: **Claude is the primary user.** Every tool is evaluated from the perspective of "does this make Claude more capable, more informed, or safer as an autonomous agent?"

---

## Install

```bash
git clone <this-repo>
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

Tools are presented in layer order. Each layer builds on the one below.

| Layer | Name | Tools | Notes |
|-------|------|-------|-------|
| 0 | Foundation | Serena (LSP), GrapeRoot (dgc) | Always-on |
| 1 | Context | dual-graph, LEANN, Context7 | Smart retrieval |
| 2 | Memory | claude-session-mcp, context-mode | Cross-session |
| 3 | Safety | parry, plan-reviewer, TDD Guard | Manual config |
| 4 | Observability | ccusage, cship, cclogviewer, claudio | Telemetry |
| 5 | Orchestration | seu-claude, ContextKit, Switchboard | Scaling |
| 6 | Workflow | CodeGraphContext, remote-approver | Utilities |

---

## Experimental Tools

Six bundled MCP servers are marked **experimental** — they're built and working but not yet broadly validated across diverse projects. Enable them with `--experimental`:

| Tool | What it does |
|------|-------------|
| `claude-mind` | Persistent investigation reasoning board — hypotheses, facts, ruled-out paths that survive context compaction |
| `claude-charter` | Project constitution store — invariants, constraints, non-goals; `charter_check()` flags violations |
| `claude-witness` | Runtime execution trace capture via `sys.settrace`; queryable from pytest runs |
| `claude-afe` | Agentic Field Engine — cognitive compiler that turns a task description into a precise agent spec |
| `claude-retina` | Visual browser automation via Playwright — screenshots, diffs, accessibility trees, visual regression |
| `claude-ledger` | Live capability map — `ledger_context()` replaces static tool-ledger.md at session start |

All six are bundled in the repo and installed to `~/.local/share/ccsetup/` by `install.sh`. They have no external dependencies beyond Python 3.9+ stdlib (plus Playwright for retina).

```bash
# Enable all experimental tools on top of maximal:
ccsetup . --preset maximal --experimental

# Or just the experimental tools, interactively:
ccsetup . --experimental
```

In interactive mode, these tools still appear as opt-in prompts — labelled `[experimental]` so you know what you're picking.

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

The bundled MCP servers (`claude-mind`, `claude-charter`, etc.) are also stdlib-only Python. After `bash install.sh`, they live at `~/.local/share/ccsetup/<server>/server.py` and are referenced by absolute path in `.mcp.json`.

---

## Development

```bash
# Run tests (requires pytest)
pip install pytest
python -m pytest tests/ -v

# Run without installing
python ccsetup.py . --dry-run
python ccsetup.py . --status
```

See `docs/tools-reference.md` for per-tool descriptions and selection heuristics.
