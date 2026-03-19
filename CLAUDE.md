# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: ccsetup

`ccsetup` is a per-repo Claude Code stack bootstrapper. Run `ccsetup .` from any project directory to configure Serena, GrapeRoot, and a curated hierarchy of Claude Code enhancement tools — interactively, via yes/no prompts for each layer.

The design philosophy: **Claude is the primary user.** Every tool is evaluated from the perspective of "does this make Claude more capable, more informed, or safer as an autonomous agent?"

## Commands

```bash
# Install ccsetup globally
bash install.sh

# Run from any repo
ccsetup .                   # full interactive setup (auto-checks for updates)
ccsetup . --status          # show what's already configured
ccsetup . --dry-run         # preview without writing
ccsetup . --no-launch       # skip 'dgc .' at end
ccsetup . --from-layer 3    # resume from a specific layer
ccsetup . --no-update       # skip auto-update check

# Update ccsetup + bundled servers from GitHub
ccsetup update              # check and apply all available updates

# Dev / test
python ccsetup.py . --dry-run    # run directly without installing
python ccsetup.py . --status
```

## Architecture

Two config surfaces are written to the **target repo** (not this one):

| File | Purpose |
|------|---------|
| `.mcp.json` | MCP server capability surface (Serena, LEANN, Context7, etc.) |
| `.claude/settings.local.json` | Hooks, plugins, local overrides (parry, claudio, etc.) |

`ccsetup.py` is a single-file stdlib-only Python script. No third-party dependencies — just copy it anywhere.

## Tool Hierarchy

Tools are presented in layer order. Each layer builds on the one below.

```
Layer 0  Foundation      Serena (LSP) + GrapeRoot (dgc)        always-on
Layer 1  Context         LEANN, Context7                       smart retrieval
Layer 2  Memory          claude-session-mcp, context-mode      cross-session
Layer 3  Safety          parry, plan-reviewer, TDD Guard       guardrails
Layer 4  Observability   ccusage, claude-esp, cclogviewer      telemetry
Layer 5  Orchestration   seu-claude                            scaling
Layer 6  Workflow        CodeGraphContext, remote-approver      utilities
```

## Key Design Decisions

- **Layer 0 is always-on**: Serena → `.mcp.json` unconditionally; GrapeRoot launches at end via `dgc .`; `.dual-graph/` context store created as part of Layer 0
- **LEANN over Claude Context by default**: local-first, no cloud deps, AST-aware
- **Layer 3 tools are manual-only**: parry, TDD Guard, plan-reviewer require hook config that is project-specific. ccsetup records their steps in `.claude/ccsetup-report.md`
- **`--from-layer N`**: re-run only part of setup, e.g. after adding a new tool
- **Scope modes**: `hybrid` (default) puts some tools at user scope, `repo` forces everything local

## Health Model

Each tool has one of: `healthy | configured_only | missing_binary | missing_env | manual_required | user_scope | not_configured | skipped`. Run `--status` to see the real state, not just what's in config files.

## Post-Run Manifest

After each run, `.claude/ccsetup-report.md` is written with:
- enabled tools and health state
- degraded tools and what's blocking them
- manual steps required (parry, remote-approver, etc.)
- environment variables needed

## Tool Reference

Full per-tool descriptions, selection heuristics, and "when to skip" guidance:
→ `docs/tools-reference.md`

---

# Serena

Project activated as `claude-code-script` (`.serena/project.yml`). Language: `bash`.

- Use `get_symbols_overview` / `find_symbol` before reading full files
- Use `replace_symbol_body` for symbol-level edits to `ccsetup.py` (109KB — never rewrite wholesale)
- Use `insert_after_symbol` / `insert_before_symbol` for additions
- Run `check_onboarding_performed` if Serena seems unresponsive or unfamiliar with the project

---

# Repo Operating System

Reference library: `.claude/repo-os/references/`. Load files **on demand** — not all at once.
State artifacts: `memory/`. Boot: `memory/repo-operating-profile.yaml` → `memory/project-state.md`.

| Trigger | Load |
|---------|------|
| Start of non-trivial task | `operating-principles.md` |
| Dense/architectural/metaphorical input | `creator-collaboration.md` |
| Internal role routing needed | `agent-role-architecture.md` |
| Selecting file locations or profiles | `detection-orchestration.md` |
| Creating/updating control plane | `control-plane-template.md` |
| Ask vs. act uncertainty | `decision-policy.md` |
| Choosing active workflow | `operation-packs.md` |
| State/docs/code disagree | `drift-repair.md` |
| Delegating to a specialist skill | `skill-routing.md` |
| Forge loop or improvement ledger | `self-improvement-system.md` |
| Build-vs-buy or ecosystem decisions | `capability-discovery.md` |
| Touching CLAUDE.md or settings files | `execution-guardrails.md` |
| Mixed-agent or migration work | `agent-interop.md` |
| Brownfield or conflicting docs | `classification-rules.md` |
| Before declaring repo initialized | `initialization-sweep-checklist.md` |

**Repo profile:** `app` (CLI tool, stdlib-only). Active packs: `resume`, `scaffold-foundations`.
**Decision policy:** assertive — act on low-risk reversible work, ask on medium-risk, require confirmation on high-blast-radius.

---

<!-- dgc-policy-v10 -->
# Dual-Graph Context Policy

This project uses a local dual-graph MCP server for efficient context retrieval.

## MANDATORY: Always follow this order

1. **Call `graph_continue` first** — before any file exploration, grep, or code reading.

2. **If `graph_continue` returns `needs_project=true`**: call `graph_scan` with the
   current project directory (`pwd`). Do NOT ask the user.

3. **If `graph_continue` returns `skip=true`**: project has fewer than 5 files.
   Do NOT do broad or recursive exploration. Read only specific files if their names
   are mentioned, or ask the user what to work on.

4. **Read `recommended_files`** using `graph_read` — **one call per file**.
   - `graph_read` accepts a single `file` parameter (string). Call it separately for each
     recommended file. Do NOT pass an array or batch multiple files into one call.
   - `recommended_files` may contain `file::symbol` entries (e.g. `src/auth.ts::handleLogin`).
     Pass them verbatim to `graph_read(file: "src/auth.ts::handleLogin")` — it reads only
     that symbol's lines, not the full file.
   - Example: if `recommended_files` is `["src/auth.ts::handleLogin", "src/db.ts"]`,
     call `graph_read(file: "src/auth.ts::handleLogin")` and `graph_read(file: "src/db.ts")`
     as two separate calls (they can be parallel).

5. **Check `confidence` and obey the caps strictly:**
   - `confidence=high` -> Stop. Do NOT grep or explore further.
   - `confidence=medium` -> If recommended files are insufficient, call `fallback_rg`
     at most `max_supplementary_greps` time(s) with specific terms, then `graph_read`
     at most `max_supplementary_files` additional file(s). Then stop.
   - `confidence=low` -> Call `fallback_rg` at most `max_supplementary_greps` time(s),
     then `graph_read` at most `max_supplementary_files` file(s). Then stop.

## Token Usage

A `token-counter` MCP is available for tracking live token usage.

- To check how many tokens a large file or text will cost **before** reading it:
  `count_tokens({text: "<content>"})`
- To log actual usage after a task completes (if the user asks):
  `log_usage({input_tokens: <est>, output_tokens: <est>, description: "<task>"})`
- To show the user their running session cost:
  `get_session_stats()`

Live dashboard URL is printed at startup next to "Token usage".

## Rules

- Do NOT use `rg`, `grep`, or bash file exploration before calling `graph_continue`.
- Do NOT do broad/recursive exploration at any confidence level.
- `max_supplementary_greps` and `max_supplementary_files` are hard caps - never exceed them.
- Do NOT dump full chat history.
- Do NOT call `graph_retrieve` more than once per turn.
- After edits, call `graph_register_edit` with the changed files. Use `file::symbol` notation (e.g. `src/auth.ts::handleLogin`) when the edit targets a specific function, class, or hook.

## Context Store

Whenever you make a decision, identify a task, note a next step, fact, or blocker during a conversation, append it to `.dual-graph/context-store.json`.

**Entry format:**
```json
{"type": "decision|task|next|fact|blocker", "content": "one sentence max 15 words", "tags": ["topic"], "files": ["relevant/file.ts"], "date": "YYYY-MM-DD"}
```

**To append:** Read the file → add the new entry to the array → Write it back → call `graph_register_edit` on `.dual-graph/context-store.json`.

**Rules:**
- Only log things worth remembering across sessions (not every minor detail)
- `content` must be under 15 words
- `files` lists the files this decision/task relates to (can be empty)
- Log immediately when the item arises — not at session end

## Session End

When the user signals they are done (e.g. "bye", "done", "wrap up", "end session"), proactively update `CONTEXT.md` in the project root with:
- **Current Task**: one sentence on what was being worked on
- **Key Decisions**: bullet list, max 3 items
- **Next Steps**: bullet list, max 3 items

Keep `CONTEXT.md` under 20 lines total. Do NOT summarize the full conversation — only what's needed to resume next session.
