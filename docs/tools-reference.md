# ccsetup Tool Reference

Tool-by-tool guide for deciding what to enable. Each entry covers what the tool does,
when to include it, when to skip it, and any architectural notes.

Use this when building a new repo profile or when Claude needs to reason about tool selection.

---

## Layer 0 — Foundation (always-on)

### Serena
**What:** IDE-like semantic understanding of the codebase via LSP. Symbol-aware navigation,
project-based workflows, structured code retrieval and editing.

**Include when:** The project is large enough that "grep and pray" becomes expensive.
Refactors, tracing definitions/usages, understanding cross-file structure.

**Skip when:** The project is small enough that normal search covers it, or you don't
intend to lean into its project workflow (it works best as a first-class tool, not a hood ornament).

**Note:** Always-on in ccsetup. Configured unconditionally in `.mcp.json`.

---

### GrapeRoot (dgc)
**What:** Builds a precomputed dual graph of the codebase (files, functions, imports, calls)
and pre-injects relevant context before you start thinking. Tracks session memory so
follow-up turns route faster and cheaper.

**Include when:** Cost, speed, and "stop rereading the repo every turn" matter.
Most valuable on medium-to-large projects with clear import/call structure.

**Skip when:** The project is tiny or the codebase structure is too dynamic/generated for
a static graph to be meaningful.

**Note:** Always-on. Launched via `dgc .` at the end of setup.

---

## Layer 1 — Context Intelligence

### LEANN
**What:** Local-first semantic code search via MCP. AST-aware chunking, automatic language
detection, no cloud dependencies. Retrieves code by meaning, not exact text.

**Include when:** Keyword search isn't enough and you need conceptual retrieval across a
large or messy codebase. Best when you want privacy and don't want cloud API keys.

**Skip when:** Serena plus normal navigation already covers your retrieval needs, or the
repo is small enough that `grep` does the job.

**Architectural note:** Default choice over Claude Context. Local-first is the right default
for most workflows. Add at user scope when possible so it indexes all repos.

---

### Claude Context
**What:** Semantic search over the whole codebase via Zilliz Cloud vector DB.
Similar in spirit to LEANN but cloud-hosted with external embedding models.

**Include when:** Very large repos where you want enterprise-scale semantic retrieval
and you're comfortable with cloud infrastructure and the associated API keys.

**Skip when:** LEANN already meets your needs, or data residency / privacy matters.
Requires `ZILLIZ_CLOUD_URI`, `ZILLIZ_CLOUD_API_KEY`, and `EMBEDDING_API_KEY`.

**Architectural note:** Do not run both LEANN and Claude Context — redundant retrieval
layers don't compound value, they just confuse routing.

---

### Context7
**What:** Injects live, version-accurate library/framework documentation into Claude's context
via MCP. Eliminates hallucinations from stale post-training-cutoff API knowledge.

**Include when:** The task depends on external libraries — React, Next.js, obscure SDKs,
anything where the model's training data might be behind the current API surface.

**Skip when:** Work is almost entirely internal code reasoning with no external API surface.

**Usage:** Trigger with `use context7` or `@<libname>` in prompts.

---

## Layer 2 — Memory & Continuity

### claude-session-mcp
**What:** Lossless session clone, archive, and restore. Fork sessions, resume exact state,
archive project snapshots, transfer sessions across machines.

**Include when:** Continuity matters and you don't want important work trapped inside one
fragile terminal session. Long-running projects, multi-machine workflows.

**Skip when:** Your workflow is short-lived, disposable, or covered by another memory system.

**Architectural note:** Choose ONE primary session memory tool — claude-session-mcp,
smart-fork, or seu-claude. Stacking all three creates competing memory strata.
Best added at user scope so it works across all repos.

---

### context-mode
**What:** Virtualizes tool outputs — runs tools normally but only compressed/filtered
outputs enter the model's context. Keeps raw data out of the context window, indexes
locally, allows on-demand search. Preserves token budget during tool-heavy sessions.

**Include when:** Your sessions are long, tool-heavy, and prone to context bloat from
huge outputs, large files, fetched docs, or repeated searches.

**Skip when:** Sessions are short or your tool outputs are typically small. Adds
operational overhead that only pays off with heavy usage.

---

## Layer 3 — Safety & Quality Guardrails

### parry
**What:** Hook-based prompt injection and data exfiltration scanner. Uses Aho-Corasick for
known jailbreak patterns, optional DeBERTa ML for semantic classification, and Tree-sitter
AST analysis to block secret leakage from `~/.ssh`, `.env`, etc. Sub-10ms latency.

**Include when:** Untrusted text, tool outputs, web content, tickets, or logs enter the
workflow. Essential for autonomous overnight operation.

**Skip when:** The workflow is fully trusted, developer-only, with no external input.

**Status:** Manual setup. Requires `parry serve` daemon + PreToolUse hook configuration.

---

### claude-plan-reviewer
**What:** Intercepts Claude's plan before execution and sends it to a rival model (GPT-4,
Gemini) for critique. Feeds the review back, forcing revision. Reduces hallucinated
architectures and "mushy ask" failures.

**Include when:** Planning quality matters more than speed, and you're comfortable with
plan contents being sent to an external model.

**Skip when:** Privacy concerns, latency sensitivity, or the workflow is already well-constrained.

**Note:** Sends plan contents externally. Requires `OPENAI_API_KEY` or `GOOGLE_API_KEY`.
The repo itself flags this privacy tradeoff.

---

### TDD Guard
**What:** Blocks file writes (Write/Edit/MultiEdit) unless a failing test exists first.
Hard-enforces Red-Green-Refactor. Monitors Vitest, Pytest, Go test, PHPUnit via PreToolUse hook.

**Include when:** The repo culture genuinely values TDD and you want the tool to enforce it.

**Skip when:** You don't follow strict TDD, or the overhead of enforcement outweighs the
discipline benefit. Real-world friction is real — see the issue tracker.

---

## Layer 4 — Observability & Telemetry

### ccusage
**What:** Terminal dashboard for token usage and costs. Parses `~/.claude/*.jsonl` locally.
Daily, weekly, monthly, and per-session breakdowns. Zero cloud exfiltration.

**Include when:** You care about burn rate or want visibility into where tokens go.
Strongly recommended for any production or long-running workflow.

**Skip when:** Cost is irrelevant and you don't want another dashboard tool.

---

### claude-esp
**What:** Streams Claude's hidden thinking blocks, tool calls, and subagent communications
to a separate terminal window. Real-time logic debugging without cluttering the main chat.

**Include when:** Debugging, trust-building, or understanding why Claude made a particular
decision. Useful for auditing autonomous operation.

**Skip when:** You just want to ship and don't need to inspect reasoning.

---

### cclogviewer
**What:** Converts Claude Code's `.jsonl` session logs into interactive HTML. Nested task
views, complete tool-call chain transparency, shareable audit artifacts.

**Include when:** After-the-fact review, audits, retrospectives, or sharing session traces.

**Skip when:** ccusage already covers the questions you care about, or you rarely inspect logs.

---

### claudio
**What:** Plays macOS system sounds on PreToolUse and PostToolUse events. Ambient awareness
that a long background task has finished without watching the terminal.

**Include when:** You run long tasks and want non-intrusive ambient feedback.

**Skip when:** You find audio feedback distracting, or you're not on macOS.

---

### claude-retina
**What:** Visual browser automation via headless Chromium (Playwright). Gives Claude eyes on the
running UI. Tools: screenshot any URL or CSS selector, pixel-level diff before/after, inspect
accessibility trees, capture JS console errors, run click/type/scroll interaction sequences,
and do visual regression testing against named baselines.

**Include when:** The project has a frontend UI that matters visually. You want to verify that
CSS changes actually look correct, catch visual regressions before users do, or diagnose JS
errors that don't surface in the source code.

**Skip when:** Backend-only work with no UI surface. When Playwright adds unwanted deps.

**Presets:** `maximal`

**Install:**
```bash
pip install playwright Pillow
playwright install chromium
```
Both deps are optional — each tool degrades gracefully with a clear install instruction if
missing (Pillow fallback: PNG header comparison instead of pixel diff).

**MCP tools:**
| Tool | Use When |
|------|----------|
| `retina_capture(url)` | See what the running UI looks like |
| `retina_diff(a, b)` | Verify a change didn't break the layout |
| `retina_inspect(url)` | Check accessibility/ARIA structure |
| `retina_console(url)` | Catch JS errors during page load |
| `retina_interact(url, actions)` | Verify an interaction flow works visually |
| `retina_baseline(name, url)` | Save a before-snapshot for regression testing |
| `retina_regress(name)` | PASS/FAIL comparison against a saved baseline |
| `retina_history()` | Find capture IDs for diff/regress |

**Storage:** `.claude/retina/retina.json`, captures in `.claude/retina/captures/`, baselines in `.claude/retina/baselines/`.

---

## Layer 5 — Orchestration & Scaling

### seu-claude
**What:** Persistent memory + task tracking + dependency analysis + sandboxed execution +
multi-agent orchestration in one package. Described as a "nervous system for the terminal."

**Include when:** Complex, multi-session projects where you need crash recovery, persistent
task state, and multi-agent coordination. Think of it as Claude's operating environment,
not just a helper tool.

**Skip when:** The project doesn't justify the overhead. This is powerful but heavy —
don't use it if normal sessions are sufficient.

---

## Layer 6 — Workflow Utilities

### CodeGraphContext
**What:** Indexes code into a knowledge graph for explicit relationship queries: callers,
callees, class hierarchies, call chains. Live updates, structural questions beyond text search.

**Include when:** You need explicit graph queries like "what calls this function?" or
"show me the full call chain from entry point X." Complements Serena's LSP.

**Skip when:** Serena or GrapeRoot already provide sufficient structural understanding.
Avoid graph-tool redundancy — don't pay three times for the same flashlight.

---

### claude-remote-approver
**What:** Forwards tool approval prompts to your phone via ntfy.sh. Approve or deny
commands remotely. Supports configurable timeouts and "Always Approve" lists.

**Include when:** You run long overnight pipelines and need to remain supervisor without
being physically present at the terminal.

**Skip when:** You prefer to be present for approvals, or you don't want another
operational service in the trust chain.

**Requirements:** Free ntfy.sh account, `NTFY_TOPIC` env var, ntfy mobile app.

---

### Smart Fork Detection
**What:** Semantic search over past Claude Code session transcripts. Index old sessions into
a vector database, search by meaning, resume the most relevant prior thread.

**Include when:** Session history has become a knowledge base and you need to recover prior
architectural context without manual archaeology.

**Skip when:** claude-session-mcp or seu-claude already cover your continuity needs.
Avoid stacking multiple memory systems unless you have a specific reason for each stratum.

---

### claude-afe
**Layer:** 5 — Orchestration
**What:** Cognitive compiler — takes a task description, consults mind/charter/witness context,
and compiles a complete agent specification: function bundle (8 functions × M/F modality), animal
workflow sequence, distortion guards, and a system prompt fragment ready to inject when spawning
the Agent tool.

**Why Claude wants it:** Without AFE, every agent spawn is an ad-hoc prompt. With it, Claude
compiles the right cognitive posture from its own memory/norms/evidence before spawning. The spec
is structurally guaranteed, not improvised. The ecology mode chains multiple agents across 4 phases
(explore→plan→implement→review) with typed handoff artifacts.

**Include when:** Complex multi-agent or multi-phase tasks. Before any autonomous Agent spawn on
non-trivial work.

**Skip when:** Task is simple and single-agent. AFE pays off on complex work; it's overhead on
one-shot prompts.

**Install:** Bundled — `bash install.sh` from the ccsetup source directory copies to
`~/.local/share/ccsetup/claude-afe/`.

**Tools:** `afe_compile`, `afe_templates`, `afe_inspect`, `afe_validate`, `afe_ecology`,
`afe_context`, `afe_history`

---

### claude-ledger
**Layer:** 5 — Orchestration
**What:** Live, queryable capability surface. Converts the static `tool-ledger.md` into a live
MCP server. Reads `.mcp.json` and `.claude/` state files at runtime. `ledger_context()` gives
a session-start briefing (health + active investigation + recommended next steps). `ledger_query("task")`
returns an opinionated tool routing recommendation.

**Why Claude wants it:** Instead of scanning a stale markdown file, Claude can ask "what should I
use for X?" and get a structured, context-aware answer. `ledger_context()` replaces the need to
read `tool-ledger.md` at session start — health, active state, and routing in one call.

**Include when:** You have multiple MCP tools configured and want Claude to make better routing
decisions. The more tools in `.mcp.json`, the more valuable ledger_query becomes.

**Skip when:** You prefer the static `tool-ledger.md` workflow. There's no real downside to
enabling it — no external deps, stdlib only.

**Presets:** `recommended`, `maximal`

**Install:** Bundled — `bash install.sh` from the ccsetup source directory copies to
`~/.local/share/ccsetup/claude-ledger/`. No additional dependencies.

**MCP tools:**
| Tool | Use When |
|------|----------|
| `ledger_context()` | Session start — replaces reading tool-ledger.md |
| `ledger_query("task")` | "What should I use for X?" — opinionated routing |
| `ledger_available()` | See all configured tools by layer |
| `ledger_health()` | Real-time health check (rechecks binary/file existence) |
| `ledger_workflows(tag?)` | Canonical workflow patterns for common tasks |
| `ledger_catalog(mcp_key?)` | Full tool signatures for one or all MCP servers |

**Relationship to tool-ledger.md:** `tool-ledger.md` is kept as a human-readable audit artifact.
claude-ledger is the live version. When enabled, it replaces the static file for session-start use.

---

### cship
**Layer:** 4 — Observability
**What:** Rust binary (<10ms) that renders real-time Claude Code session metrics inline in the
terminal prompt — cost, context window %, model name, API usage limits, sub-agent names. Integrates
with Starship. Wires into `~/.claude/settings.json` as the statusline provider.

**Why Claude wants it:** Ambient budget awareness without leaving the terminal. At a glance: how
much context is left, what the session costs, which sub-agents are running. Essential for
autonomous long-running sessions.

**Include when:** You want inline session metrics. Pairs well with ccusage (cship = inline,
ccusage = full dashboard).

**Skip when:** ccusage already covers your cost monitoring needs and you don't want the prompt
augmented.

**Install:** `curl -fsSL https://cship.dev/install.sh | bash` → installs to `~/.local/bin/cship`,
creates `~/.config/cship.toml`.

**Platform:** macOS + Linux.

**Conflicts:** Complements ccusage; no hard conflicts.

---

### clui-cc
**Layer:** 6 — Workflow
**What:** macOS-only Electron overlay app — floating pill window (Option+Space), multi-tab session
management, visual approve/deny workflow for tool calls, voice input (local Whisper, no cloud),
conversation history. Replaces terminal as the primary Claude Code interface.

**Why Claude wants it:** Visual approval workflow makes autonomous operation safer — pending tool
calls are visible and user can approve or deny from a readable UI rather than raw terminal prompts.
Multi-tab management keeps long autonomous sessions organized.

**Include when:** macOS 13+, you want a GUI-layer alternative to the raw terminal, and you prefer
visual approval over `--dangerously-skip-permissions`.

**Skip when:** Linux/Windows (macOS-only). Prefer terminal-native workflow. Find the floating
overlay more overhead than it's worth.

**Install:** Clone → `./install-app.command`. Requires Node.js 18+, Python 3.12, Whisper CLI.
`manual_only=True` — ccsetup records steps, does not automate install.

**Conflicts:** Replaces terminal session workflow. When used, you're in the Electron app, not
the terminal.

---

## Selection Heuristics

**Shortest sane rule set:**

1. Always include Serena + GrapeRoot (Layer 0 — no choice required)
2. Pick one semantic retrieval layer: LEANN (local) or Claude Context (cloud) — not both
3. Add Context7 if external library docs matter for the project
4. Add context-mode if tool-output bloat is killing session longevity
5. Pick ONE continuity tool: claude-session-mcp, smart-fork, or seu-claude
6. Add parry and/or TDD Guard when safety or process discipline outweighs speed
7. Add Switchboard only after MCP sprawl is a real, measured problem

**Preset equivalents:**
- `--preset minimal` → Layer 0 only
- `--preset recommended` → Layers 0–2 + ccusage + cship (good default for most projects)
- `--preset maximal` → Everything except invasive/manual/deprecated tools (includes claude-afe, cship, clui-cc steps)
