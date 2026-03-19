# Capability Analysis: ccsetup Tool Ecosystem

_Generated 2026-03-17. Written from Claude's perspective as the primary user of this toolchain._

---

## Purpose

This document maps every tool in the ccsetup ecosystem along three axes:
- **What it actually provides** (type of understanding, what it operates on)
- **What it explicitly does NOT do** (prevents overselling and mis-routing)
- **The gap** (what remains invisible even with this tool active)

The goal is to make coverage and white space explicit so that tool selection, routing, and roadmap decisions are grounded in reality.

---

## Layer-by-Layer Analysis

### Layer 0: Foundation (Always-On)

#### Serena (LSP)
- **Type of Understanding:** Structural/static analysis via Language Server Protocol
- **Provides:** Symbol-aware navigation, cross-file relationships, structured code retrieval and editing. IDE-like semantic intelligence.
- **Operates On:** Code structure (definitions, references, hover info, implementations)
- **Does NOT Do:**
  - Import-graph analysis (GrapeRoot)
  - Semantic meaning retrieval (LEANN/Context)
  - Real-time runtime behavior visibility
  - Session memory or continuity
- **Gap:** Navigation-first. Perfect for "find definition" but doesn't auto-inject context or answer "what's related to this?" without explicit queries.

#### GrapeRoot (dgc / dual-graph)
- **Type of Understanding:** Precomputed dependency graph + session context injection
- **Provides:** Dual-graph of files/functions/imports/calls. Pre-injects relevant context before you think. Tracks session memory for faster follow-up turns.
- **Operates On:** Code structure (calls, imports, file relationships)
- **Does NOT Do:**
  - Semantic meaning of code (doesn't understand what functions conceptually do)
  - Safety/injection scanning
  - External library documentation
  - Memory persistence across sessions (within-chat only)
- **Gap:** Static, file-centric. Great for routing to the right files, but doesn't read inside them or understand business logic.

---

### Layer 1: Context Intelligence (Retrieval)

#### LEANN
- **Type of Understanding:** AST-aware semantic code search
- **Provides:** Retrieves code by conceptual meaning (not exact text). Local-first, no cloud dependencies. Language-aware chunking.
- **Operates On:** Code text (semantic embeddings of code chunks)
- **Does NOT Do:**
  - Live documentation injection (Context7)
  - Call-graph analysis (CodeGraphContext or GrapeRoot)
  - Session continuity (claude-session-mcp)
  - Structural queries like "find all callers of X"
- **Gap:** Embeds code chunks semantically but doesn't answer structural questions or fetch external docs.

#### Claude Context (Cloud Alternative to LEANN)
- **Type of Understanding:** Semantic code search at scale
- **Provides:** Same as LEANN but cloud-hosted via Zilliz; better for very large repos
- **Operates On:** Code text (embeddings)
- **Does NOT Do:** Same as LEANN, plus adds cloud dependency and data residency concerns
- **Gap:** Same retrieval gaps as LEANN, plus privacy overhead.

#### Context7
- **Type of Understanding:** Live, version-accurate external library/framework documentation
- **Provides:** Injects current API surface of React, Next.js, etc. directly into context. Eliminates hallucination from stale post-training knowledge.
- **Operates On:** External documentation (library metadata, current API surfaces)
- **Does NOT Do:**
  - Internal code understanding
  - Call analysis
  - Session memory
  - Custom internal domains (only known libraries)
- **Gap:** Fills knowledge-cutoff gaps for external libs but doesn't help with internal code discovery or relationships.

---

### Layer 2: Memory & Continuity

#### claude-session-mcp
- **Type of Understanding:** Session state persistence (lossless clone/archive/restore)
- **Provides:** Fork sessions, resume exact state, archive snapshots, transfer sessions across machines. Persistent task state.
- **Operates On:** Conversation/session state
- **Does NOT Do:**
  - Cross-session learning or pattern extraction
  - Automatic task scheduling or coordination
  - Sandboxed execution (seu-claude)
  - Dependency analysis between tasks
- **Gap:** Preserves state but doesn't learn patterns or coordinate complex multi-task workflows.

#### context-mode
- **Type of Understanding:** Tool output virtualization (compression/filtering)
- **Provides:** Runs tools normally but only filtered outputs enter context. Indexes locally, allows on-demand search. Preserves token budget.
- **Operates On:** Tool output streams (post-execution)
- **Does NOT Do:**
  - Change what tools return — only what enters the model's context
  - Active filtering of sensitive data (parry)
  - Semantic prioritization of outputs (passive filtering only)
- **Gap:** Solves token bloat but doesn't make intelligent decisions about which outputs matter most.

---

### Layer 3: Safety & Quality Guardrails

#### parry
- **Type of Understanding:** Security scanning (prompt injection, data exfiltration, secrets)
- **Provides:** Hook-based scanning using Aho-Corasick patterns + optional DeBERTa ML + Tree-sitter AST. Blocks jailbreaks and secret leakage from `~/.ssh`, `.env`. Sub-10ms latency.
- **Operates On:** Tool outputs, untrusted inputs, code AST
- **Does NOT Do:**
  - Code-quality enforcement
  - Logical validation of plans
  - Runtime behavior monitoring
  - External input sanitization beyond pattern matching
- **Gap:** Defensive only. Stops bad inputs from entering; doesn't validate what Claude decides to do with them.

#### claude-plan-reviewer
- **Type of Understanding:** Plan critique via external model
- **Provides:** Intercepts Claude's plan, sends to GPT-4/Gemini for review, feeds critique back, forces revision. Reduces hallucinated architectures.
- **Operates On:** Conversation/plan state (sends plan text externally)
- **Does NOT Do:**
  - Code-level analysis
  - Execution validation
  - Continuous monitoring
  - Avoids third-party data transfer (external API required)
- **Gap:** Pre-execution critique only. Doesn't catch mistakes during execution or verify outcomes.

#### TDD Guard
- **Type of Understanding:** Process enforcement (Red-Green-Refactor)
- **Provides:** Blocks Write/Edit operations unless a failing test exists first. Monitors Vitest, Pytest, Go test, PHPUnit via PreToolUse hook.
- **Operates On:** File write operations (PreToolUse hook)
- **Does NOT Do:**
  - Test quality validation
  - Coverage analysis
  - Dead-code detection
  - Suggest tests (only blocks writes)
- **Gap:** Enforces process but doesn't validate quality of tests created or ensure coverage.

---

### Layer 4: Observability & Telemetry

#### ccusage
- **Type of Understanding:** Token cost tracking and visualization
- **Provides:** Terminal dashboard for token usage/cost. Parses `~/.claude/*.jsonl` locally. Daily/weekly/monthly/per-session breakdowns. Zero cloud exfiltration.
- **Operates On:** Session logs (token counts)
- **Does NOT Do:**
  - Cost optimization suggestions
  - Tool-call efficiency analysis
  - Context-window usage visualization
  - Predictive budgeting
- **Gap:** Observes cost but doesn't prescribe reductions or identify expensive patterns.

#### claude-esp
- **Type of Understanding:** Real-time reasoning transparency
- **Provides:** Streams Claude's thinking blocks, tool calls, subagent communications to separate terminal. Logic debugging without context clutter.
- **Operates On:** Conversation state (hidden thinking and tool calls)
- **Does NOT Do:**
  - Criticize reasoning
  - Automatic hypothesis testing
  - Alternative exploration
  - Anything beyond observation
- **Gap:** Observes reasoning but doesn't improve it or suggest alternatives.

#### cclogviewer
- **Type of Understanding:** Post-hoc session audit
- **Provides:** Converts `.jsonl` logs to interactive HTML. Nested task views, tool-call transparency, shareable audit artifacts.
- **Operates On:** Session logs (post-execution)
- **Does NOT Do:**
  - Real-time analysis
  - Pattern detection
  - Cost anomaly alerting
  - Inform current decisions
- **Gap:** Reviews past sessions but doesn't inform current decisions.

#### claudio
- **Type of Understanding:** Ambient feedback (macOS system sounds)
- **Provides:** Audio notification on PreToolUse/PostToolUse. Non-intrusive awareness that background tasks finished.
- **Operates On:** Tool execution events
- **Does NOT Do:** Almost everything — purely user-facing feedback
- **Gap:** Signals task completion but provides no code/process insights.

---

### Layer 5: Orchestration & Scaling

#### seu-claude
- **Type of Understanding:** Nervous system for multi-session orchestration
- **Provides:** Persistent memory + task tracking + dependency analysis + sandboxed execution + multi-agent coordination. Crash recovery. Task graphs with DAG dependencies.
- **Operates On:** Session state, task execution, process spawning
- **Does NOT Do:**
  - Code understanding (relies on other layers)
  - Safety scanning (parry)
  - Semantic retrieval (LEANN)
  - External library documentation
- **Gap:** Orchestrates execution but is agnostic to what's being executed or why it matters.

#### ContextKit (DEPRECATED)
- **Type of Understanding:** Auto-generated project guidance
- **Provides:** Generates CLAUDE.md by analyzing codebase.
- **Status:** Abandoned by maintainers. Flagged in ccsetup, not removed.
- **Gap:** Was intended to be "self-documenting" but maintainers abandoned it in favor of Claude's built-in plan mode.

#### Switchboard
- **Type of Understanding:** MCP aggregation and lazy loading
- **Provides:** Aggregates multiple MCPs behind single entrypoint. Lazy-loads on demand. Reduces tool-schema token overhead.
- **Operates On:** MCP server registry and configuration
- **Does NOT Do:**
  - Tool selection logic
  - Capability routing
  - Tool composition
  - Anything beyond aggregation; invasively rewrites `.mcp.json`
- **Gap:** Reduces token overhead but adds operational complexity and doesn't help choose which tools to use.

---

### Layer 6: Workflow Utilities

#### CodeGraphContext
- **Type of Understanding:** Explicit relationship queries (callers, callees, hierarchies, call chains)
- **Provides:** Knowledge graph of code relationships. Complements Serena's LSP. Live updates, structural questions beyond text search.
- **Operates On:** Code structure (call graph, inheritance)
- **Does NOT Do:**
  - Semantic meaning
  - Business logic understanding
  - External dependencies
  - (Potential tool overlap with GrapeRoot)
- **Gap:** Answers "what calls this?" but not "what does this do?" or "is this correct?"

#### claude-remote-approver
- **Type of Understanding:** Remote tool approval via mobile notification
- **Provides:** Forwards approval prompts to phone via ntfy.sh. Approve/deny remotely. Configurable timeouts and "Always Approve" lists.
- **Operates On:** Tool execution approvals (async user intervention)
- **Does NOT Do:**
  - Logic validation
  - Automated decision-making
  - Audit trail beyond logs
  - (Requires external service: ntfy.sh)
- **Gap:** Keeps you in the loop remotely but you still need to make intelligent approval decisions.

#### Smart Fork Detection
- **Type of Understanding:** Session history semantic search
- **Provides:** Indexes old Claude Code sessions into vector DB, searches by meaning, resumes most relevant prior thread.
- **Operates On:** Session transcripts (search and resume)
- **Does NOT Do:**
  - Automatic merging of findings
  - Cross-session learning
  - Pattern extraction
  - (Requires vector DB setup)
- **Gap:** Helps you find old conversations but doesn't synthesize learnings or prevent duplicate work.

---

## Capability Surface Map

| Dimension | Tools | Coverage Type | Gap |
|-----------|-------|--------------|-----|
| Code Structure | Serena (LSP), GrapeRoot (graph), CodeGraphContext | Comprehensive | Redundancy between GrapeRoot and CodeGraphContext |
| Code Semantics | LEANN (embeddings), Context7 (docs) | Partial | External libs strong; internal business logic and intent invisible |
| **Runtime Behavior** | **NONE** | **None** | **Complete whitespace: no profiling, tracing, execution analysis, or test results integration** |
| Session Memory | claude-session-mcp, seu-claude, Smart Fork | Good | No cross-session synthesis or pattern learning |
| Safety | parry (injection/exfiltration), TDD Guard (process), plan-reviewer (logic) | Defensive/process-focused | No validation of correctness, no performance analysis |
| Observability | ccusage, claude-esp, cclogviewer | Logging/audit focused | No real-time anomaly detection, no cost optimization suggestions |
| Orchestration | seu-claude, Switchboard | Task scheduling + MCP aggregation | No intelligent tool selection, no adaptive routing |

---

## Genuine White Space (The Gaps)

These are the areas where zero tools currently provide coverage:

### 1. Reasoning Memory — Investigation Continuity ⭐ Build first
No tool persists the epistemic structure of an active investigation. Hypotheses, ruled-out branches, confirmed facts, and open questions live in the context window and evaporate on compaction. The agent reconstructs the same investigation swamp every session.

Planned: **`claude-mind`** (Phase 1)

### 2. Normative Memory — Architectural Intent ⭐ Build second
Nothing makes project invariants, constraints, non-goals, and architectural intent queryable. Without this, execution truth (from witness) floats without meaning — I can observe facts but can't judge whether they matter.

Planned: **`claude-charter`** (Phase 2)

### 3. Execution Memory — Runtime Truth ⭐ Build third
No tool integrates test results, profiling data, or crash state. The entire tool surface is static analysis. I confuse source truth (what the code says) with execution truth (what the code does). Decorators, monkey-patching, DI, and runtime config mean actual behavior may differ from what any static tool reports.

Planned: **`claude-witness`** (Phase 3)

### 4. Correctness Validation
No post-execution verification loop. No tool says "I predicted this function would have 3 callers — there are actually 7; let me re-analyze."

### 5. Business Logic / Intent Understanding
LEANN and Context7 handle code text and external APIs, but nothing understands domain intent or internal architectural patterns.

### 6. Cost Optimization (Prescriptive)
`ccusage` shows burn rate but doesn't suggest "use cheaper retrieval here." No prescriptive cost control.

### 7. Adaptive Tool Routing
Switchboard aggregates MCPs but doesn't decide which tools to use for a given query. Tool selection is entirely manual.

**→ Partially addressed by `claude-afe`:** AFE provides structured agent spec compilation but not fully automatic runtime tool routing.

### 8. Cross-Session Learning
Smart Fork finds old sessions but doesn't extract patterns like "we always need X when doing Y."

---

## The Core Epistemological Problem

Every tool in ccsetup understands code by **reading** it. Nothing observes code by **running** it, nothing persists the structure of active investigations, and nothing makes architectural intent queryable.

Current tools answer:
- what exists (Serena, GrapeRoot, LEANN)
- what connects (CodeGraphContext, dual-graph)
- what was said (claude-session-mcp, Smart Fork)
- what was planned (cclogviewer, plan-reviewer)

They do not complete three fundamental loops:

| Loop | Missing Tool | What It Answers |
|------|-------------|-----------------|
| **Reasoning loop** | `claude-mind` | What have I hypothesized, ruled out, assumed, and confirmed? |
| **Meaning loop** | `claude-charter` | What matters in this project? What must remain true? |
| **Reality loop** | `claude-witness` | What actually executed, under what inputs, with what result? |

These are not incremental improvements to existing tools. They open new epistemological channels.

---

## Summary

The ccsetup ecosystem is heavily weighted toward **code structure and retrieval** (Serena, GrapeRoot, LEANN, CodeGraphContext) with strong guardrails for **safety and process** (parry, TDD Guard, plan-reviewer). It has excellent session management and observability.

**The four tools built to close the fundamental gaps:**

1. **`claude-mind`** — reasoning memory: persistent investigation structure across compaction events
2. **`claude-charter`** — normative memory: project invariants, constraints, and non-goals
3. **`claude-witness`** — execution memory: runtime truth from actual test runs
4. **`claude-afe`** — cognitive compiler: task → precisely-tuned agent spec

See `docs/milestones.md` for full design specs and implementation details.

---

## Layer 5 Addition: claude-afe (Agentic Field Engine)

- **Type of Understanding:** Task-to-agent compilation using the AFE operator matrix
- **Provides:** Given a task description, compiles a complete agent specification: function bundle (8 functions × 2 modalities), animal workflow order (4 animals), modality profile (MM/MF/FM/FF), distortion guards, and a ready-to-inject system prompt fragment. Consults mind/charter/witness for cross-tool context. Template registry with 11 templates (6 synthetic, 4 canonical, 1 orchestrator). Multi-agent ecology compilation for complex multi-phase tasks.
- **Operates On:** Task text (natural language), cross-tool stores (mind.json, charter.json, witness/*.json)
- **Does NOT Do:**
  - Execute agents — it compiles specs for Claude to use when spawning the Agent tool
  - Autonomous intelligence — compiler stages are deterministic; Claude provides task interpretation
  - Real-time tool routing — produces pre-compiled specs, not runtime adaptation
  - Replace mind/charter/witness — depends on them for context; is additive, not substitutive
- **Gap:** Compilation quality depends on template matching and keyword detection — complex tasks may need explicit `locus`, `template`, or `regime` overrides from Claude's judgment.

**Integration position:** Layer 5 (Orchestration) — after mind/charter/witness provide the epistemic context that makes compiled specs meaningful. The correct sequence is: `afe_context()` → `afe_compile()` → `afe_validate()` → spawn Agent with spec fragment.
