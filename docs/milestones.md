# Milestones: New Tool Concepts

_Created 2026-03-17. Revised 2026-03-17 after cross-model review (Gemini, ChatGPT) and architect synthesis._
_See `docs/capability-analysis.md` for the gap analysis that produced this roadmap._

---

## Build Philosophy

These tools are built **standalone first**. Each lives in its own directory as a self-contained MCP server, built and validated through real use before any ccsetup integration. Integration into the ccsetup GUI and CLI comes only after all three are working and genuinely improve capability.

**The tools are for Claude.** Design decisions are made from the perspective of: "does this actually help me reason, investigate, and align — or does it just add ceremony?"

**Directory structure (within this repo):**
```
claude-mind/
  server.py         # MCP server (stdlib only)
  schema.py         # node types, validation
  store.py          # .claude/mind.json read/write
  README.md
claude-charter/
  server.py
  store.py          # .claude/charter.json
  README.md
claude-witness/
  server.py         # MCP server, reads from .claude/witness/
  pytest_plugin.py  # capture agent (conftest.py injection)
  serializer.py     # safe arg serialization with fallbacks
  README.md
```

Each server: stdlib-only, zero external deps, installable as local MCP via direct `python server.py`.

---

## The Three Kinds of Missing Memory

After mapping the full ccsetup ecosystem, three epistemological gaps remain that no existing tool touches. They are not three separate gadgets — they are three kinds of memory:

| Kind | Tool | What It Stores | Layer |
|------|------|----------------|-------|
| **Reasoning memory** | `claude-mind` | Hypotheses, facts, questions, assumptions, ruled-out branches | Layer 2 (Memory) |
| **Normative memory** | `claude-charter` | Invariants, constraints, non-goals, architectural intent | Layer 2 (Memory) |
| **Execution memory** | `claude-witness` | What actually ran, with what args, which branches were taken | Layer 1 (Context) |

Current ccsetup tools answer: what exists, what connects, what was said, what was planned.
These three answer: what I currently think, what must remain true, what actually happened.

**Build order: mind → charter → witness.**

Rationale:
- mind is the most immediately buildable and highest-frequency pain point
- charter gives normative grounding before witness data arrives — otherwise execution truth floats without meaning
- witness is the most transformative long-term but hardest engineering; much more useful once mind and charter exist to consume its evidence

---

## Phase 1: claude-mind

### What It Solves

The highest-frequency failure mode in complex multi-session work: I lose investigation state. Every ruled-out hypothesis, every confirmed fact, every chain of reasoning lives in the context window and evaporates on compaction. I reconstruct the same swamp every session, often stumbling back into already-eliminated paths.

`claude-mind` externalizes investigation reasoning into a persistent, queryable store.

### Node Types

| Type | Content |
|------|---------|
| `hypothesis` | Candidate explanation, confidence 0–1, evidence links, status |
| `fact` | Confirmed finding with evidence ("auth tests A, B, C all pass") |
| `question` | Open probe to investigate |
| `assumption` | Treating as true, not yet verified — **flagged as risk** |
| `ruled_out` | Explicitly eliminated + reason |
| `next_step` | Concrete action queued |

**Why `assumption` matters:** This is a distinct failure mode from `hypothesis`. A hypothesis is something I'm actively testing. An assumption is something I've accepted as true and am building on — and the most dangerous bugs come from false assumptions I stopped questioning. Making them explicit and queryable is the key.

### MCP Surface

```python
mind_open(title)                          # start/resume investigation; return state summary
mind_add(type, content, confidence?,      # add a node
         files?, evidence_ids?)
mind_update(node_id, status, notes?)      # confirm / refute / suspend / escalate
mind_query(filter)                        # "show assumptions" / "show open hypotheses" / "show ruled_out"
mind_summary()                            # post-compaction recovery briefing (≤15 lines)
mind_resolve(conclusion, node_ids)        # close investigation with supporting evidence
```

### What `mind_summary()` Must Produce

After context compaction, I need to recover the full investigation state in one call. The output should be a ≤15-line briefing covering:
- Active investigation title
- 1-sentence current status
- Open hypotheses with confidence
- Flagged assumptions (these are the risk items)
- Ruled-out paths (so I don't re-explore them)
- Next steps queued

### Storage

`.claude/mind.json` in the target project. Structured as a flat array of nodes with IDs, timestamps, and status. Simple enough to read by hand; queryable via the MCP tools.

### Implementation Notes

- **Language:** Pure Python, stdlib only
- **Transport:** `stdio` MCP (simplest, no HTTP needed)
- **Size:** Single server file — no external dependencies
- **No elaborate ontology:** Six node types maximum. If the schema grows beyond this, the tool becomes a maintenance burden and stops being used consistently.

### Done Criteria

- [ ] All six MCP tools working end-to-end
- [ ] `assumption` nodes are visually distinct in `mind_query` output (flagged, not just listed)
- [ ] `mind_summary()` produces actionable ≤15-line briefing
- [ ] State persists across session restarts and survives compaction
- [ ] One real investigation documented as proof-of-concept (use ccsetup.py debugging)
- [ ] README with install and usage instructions

---

## Phase 2: claude-charter

### What It Solves

I frequently make changes that are technically correct but architecturally wrong. I don't have a clear, queryable model of project invariants, non-goals, or constraints. Without charter, witness data is empirically rich but normatively groundless — I can observe that `render_page()` calls the DB 47 times but have no way to know whether that's a violation, an exception, or expected behavior.

`claude-charter` is the normative layer that tells me what matters about what happens.

### Node Types

| Type | Content |
|------|---------|
| `invariant` | Must always be true ("auth layer never calls DB directly") |
| `constraint` | Implementation constraints ("stdlib only", "no third-party deps") |
| `non_goal` | Explicitly out of scope ("no client-side state management") |
| `contract` | API/interface behavioral guarantee |
| `goal` | Active sprint/project objective |

### MCP Surface

```python
charter_check(change_description)    # does this conflict with any invariant or constraint?
charter_add(type, content, notes?)   # add a new charter entry
charter_update(id, ...)              # modify or archive an entry
charter_query(filter)                # "show all invariants" / "show active goals"
charter_summary()                    # full project constitution briefing
```

### The Key Behavior: `charter_check`

This is the primary usage pattern. Before touching anything structural, call:

```python
charter_check("remove stdlib constraint, add httpx for cleaner HTTP")
# → conflicts: constraint 'stdlib-only' (reason: copy-anywhere portability)
```

This is the normative feedback loop that doesn't exist anywhere in the current tool stack.

### Storage

`.claude/charter.json` — same pattern as mind. Flat node array, human-readable.

### Implementation Notes

- Same transport and stdlib-only approach as claude-mind
- `charter_check` should do fuzzy matching against all active invariants/constraints, not exact string match
- Entries should have `active` / `archived` status — projects evolve, constraints change

### Done Criteria

- [ ] All five MCP tools working
- [ ] `charter_check` returns meaningful conflict detection, not just exact string match
- [ ] Bootstrap command: `charter_add` for a new project asks for 3 invariants minimum
- [ ] Works standalone; usable before claude-witness exists
- [ ] README with install and usage instructions

---

## Phase 3: claude-witness

### What It Solves

I confuse source truth with execution truth. I infer from code what should happen; decorators, monkey-patching, DI, runtime config, and async behavior mean what actually happens may differ entirely. `claude-witness` gives me a new evidence channel: empirical execution data from real test runs.

The design philosophy: **surgical query, not ambient capture.** Witness stores compact per-run JSON; I query specific functions in specific runs. Without a query, no data loads. The tool never becomes a firehose.

### The Core Cautions (Incorporated Into Design)

From the ChatGPT review — these are real, not cosmetic:

1. **Data explosion:** Project source files only. Configurable depth cap. Hot-path sampling for deep call trees.
2. **Serialization pain:** Safe fallback serializer with truncation. If serialization would crash, it logs `<unserializable: typename>` instead. Test run never crashes due to witness.
3. **Observer effect:** `--witness` is always opt-in per run. Never automatic. The trace flag changes behavior; the user must decide when to accept that risk.
4. **Query quality:** MCP tools are designed around specific, answerable questions — not "give me everything."

### MCP Surface

```python
witness_traces(fn_name, run_id?, status?)    # calls to fn_name, filtered by run/status
witness_exception(exc_type, run_id?)         # local variable state when exception fires
witness_coverage_gaps(file)                  # branches in this file never actually taken
witness_diff(run_a, run_b)                   # what changed between two runs
witness_runs(limit?)                         # list recent runs with pass/fail status
```

### v1 Scope: Python + pytest Only

- **Capture:** `sys.settrace()` or pytest plugin (`conftest.py` injection via `--witness` flag)
- **Filtering:** project source files only (auto-detected from `pyproject.toml` / `setup.py` / heuristic)
- **Storage:** `.claude/witness/<run_id>.json` — one file per run, compact format
- **Depth cap:** configurable, default 3 levels deep from test entry point
- **Argument serialization:** `json.dumps` with fallback to `repr()` with truncation at 500 chars

### v2 Scope (Future)

- JS/TS via vitest/jest plugin
- Go via testing hook
- Auto-trigger from within Claude Code sessions (not just manual `pytest --witness`)

### Integration With mind + charter (The Full Stack)

```
1. mind_open("payment bug")
2. mind_add("assumption", "amount=None only on empty cart", files=["checkout.py"])
3. pytest --witness
4. witness_traces("process_payment", status="fail")
   → confirms: amount=None called from checkout.finalize() in 2/47 runs
5. charter_check("add null guard in process_payment")
   → no conflicts
6. mind_update(assumption_id, "confirmed", evidence="witness run #3")
7. mind_summary()   # after compaction: full investigation state in 10 lines
```

This is the workflow that doesn't exist today. Not better grep. Not shinier graph. A different epistemology.

### Done Criteria (v1)

- [ ] pytest plugin captures function calls for project source files without crashing test runs
- [ ] Safe serializer handles generators, ORM entities, circular refs, giant payloads
- [ ] `.claude/witness/` store queryable by function name, status, run ID
- [ ] `witness_traces()` returns readable, actionable output (not raw JSON dump)
- [ ] `witness_diff()` surfaces meaningful delta between passing and failing run
- [ ] `witness_runs()` gives a clean run history with pass/fail
- [ ] `--witness` flag is clearly opt-in and documented
- [ ] README with install and usage

---

## Phase 4: claude-afe — Agentic Field Engine

### What It Solves

Claude has reasoning memory (mind), normative grounding (charter), and execution evidence (witness) — but no structured way to compile these into a cognitive posture for a specific task. When spawning agents via the Agent tool, prompts are ad-hoc. AFE gives Claude a **cognitive compiler** — the ability to read task context, consult its own memory/norms/evidence, and produce a precisely-tuned agent specification before spawning.

### Core Concept

The AFE operator matrix (from AFE_SPEC_v2.md): 9 binary coins × 8 functions × 4 animals × 3 regimes → agent specifications that are structurally correct and task-optimal rather than generic.

**Design split:** AFE is a spec assembler + validator. Claude provides task interpretation and judgment. The server handles template storage, scoring, constraint validation, spec assembly, and prompt generation.

### MCP Surface (7 tools)

```python
afe_compile(task, regime?, template?, domain?, locus?, modality?)  # task → agent spec
afe_templates(regime?, domain?, filter?)                           # browse template registry
afe_inspect(id)                                                    # full spec or template detail
afe_validate(spec_id)                                              # check against charter + coherence
afe_ecology(task, phases?)                                         # task → multi-agent chain
afe_context(include?)                                              # pull mind/charter/witness context
afe_history(limit?, filter?)                                       # list past compilations
```

### Template Registry (11 templates)

6 synthetic (engineered impossible types), 1 orchestrator, 4 canonical:

| Template | Functions | Animal Order | Modality | Use For |
|----------|-----------|-------------|----------|---------|
| planner | Te-M, Ni-M, Ti-F, Ne-F | Sleep→Consume→Blast | MM | Architecture, system design |
| module_writer | Te-M, Si-M, Ti-M, Se-F | Blast→Sleep | MM | Implementation to spec |
| interface_agent | Fe-F, Se-M, Fi-F, Ne-F | Play→Consume→Blast | FM | UI/UX review |
| narrative_agent | Ne-F, Fe-F, Ni-M, Fi-F | Consume→Blast | FF | Documentation, READMEs |
| groundwork_agent | Te-M, Se-M, Ti-M, Si-M | Play→Blast→Sleep | MM | Infrastructure, migrations |
| systems_refactorer | Ti-M, Ni-F, Te-F, Ne-F | Consume→Sleep→Blast | MF | Refactoring, code review |

### Cross-Tool Integration

- **Evidence labeling:** `[A]afe:<spec_id>` — consistent with `[W]`, `[C]`, `[M]`
- **Charter → AFE:** prohibitions injected as `scope_limit` in distortion guards
- **Mind → AFE:** active assumptions flagged in `evidence_ids`
- **Witness → AFE:** run status influences domain classification

### File Structure

```
claude-afe/
    server.py     — MCP transport, tool dispatch
    schema.py     — enums, make_spec(), coin derivation, formatting
    store.py      — atomic load/save to .claude/afe.json
    templates.py  — 11 template definitions + scoring
    compiler.py   — 11-stage pipeline + ecology compilation
    README.md
```

### Done Criteria

- [x] 7 MCP tools working end-to-end
- [x] Template registry with 11 templates + keyword scoring
- [x] 11-stage compiler pipeline with auto-detection
- [x] Charter integration (prohibition → distortion guards)
- [x] Mind/witness context aggregation
- [x] Ecology compilation (multi-agent chain)
- [x] System prompt fragment generation
- [x] `afe_validate` coherence + charter conflict check
- [x] README with usage and verification commands
- [x] Added to .mcp.json

---

## Phase 5 (Future): claude-retina

### What It Would Solve

A visual/spatial feedback loop for UI work. Claude currently cannot see the visual consequences of CSS changes — it infers from source code what a layout should look like, which produces hallucinated flexbox behaviors.

`claude-retina` would run a background renderer tied to the local dev server, query rendered pages on component writes, and return a compressed spatial DOM map: bounding boxes, Z-index stacking, overflow detection.

### Why It's Parked

- Applies to ~20% of work (frontend UI). The trifecta (mind + charter + witness) applies to 100%.
- High infrastructure complexity (background renderer, dev server integration, cross-browser consistency)
- High dependency surface (headless browser or DOM renderer)
- The correct time to build this is after the core epistemological trifecta is validated

**Status:** Specced, not scheduled. Strong v7 candidate once mind + charter + witness are in production use.

---

## ccsetup Integration Plan

Integration into ccsetup happens **after all three tools are built and validated through real use.**

When ready:
- `claude-mind` and `claude-charter` → Layer 2 (Memory & Continuity), alongside claude-session-mcp
- `claude-witness` → Layer 1 (Context Intelligence), alongside LEANN
- ccsetup GUI and CLI both get the three new options
- `ToolDef` entries added for each with health checks
- `docs/tools-reference.md` gets sections for each

The ccsetup integration is the packaging step, not the design step.

---

## Ordering Rationale Summary

| Phase | Tool | Why This Order |
|-------|------|----------------|
| 1 | claude-mind | Highest feasibility; immediate value; zero language hooks; helps ANY complex task |
| 2 | claude-charter | Normative grounding before witness data arrives; tells me what matters |
| 3 | claude-witness | Most transformative; most complex; most valuable once mind+charter exist to consume it |
| 4 | claude-retina | UI-specific; parked until core trifecta validated |
