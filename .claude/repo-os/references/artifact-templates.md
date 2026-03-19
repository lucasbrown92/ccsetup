# Artifact Templates

These filenames are defaults, not rigid requirements. Reuse the repo's existing planning, state, and scripting layout when it is coherent, and create new homes only when no better durable home exists.

Resolved homes:

- `<planning_doc_home>`
- `<state_doc_home>`
- `<task_spec_home>`
- `<script_home>`

## Contents

- root `CLAUDE.md`
- `<state_doc_home>/repo-operating-profile.yaml`
- optional `<state_doc_home>/MEMORY.md`
- root `CLAUDE.md` compatibility shim when an external adapter is active
- `<planning_doc_home>/agent-system-migration.md`
- optional `<planning_doc_home>/capability-map.md`
- `<state_doc_home>/docs-index.md`
- `<state_doc_home>/project-state.md`
- `<state_doc_home>/SYSTEM_STATE_INDEX.md`
- `<state_doc_home>/tool-registry.md`
- `<state_doc_home>/improvement-ledger.md`
- `<state_doc_home>/playbook-registry.md`
- optional `<state_doc_home>/surface-map.yaml`
- optional `<state_doc_home>/artifact-health.md`
- `<planning_doc_home>/starters.md`
- `<planning_doc_home>/task-routing-index.md`
- `<planning_doc_home>/invariants.md`
- `<planning_doc_home>/architecture-decisions.md` or `<state_doc_home>/architecture-decisions.md`
- shared `~/.claude/memory/repo-operating-system/operator-profile.yaml`

## Root `CLAUDE.md`

Keep this file to roughly one screen. Store only high-value operational state and gating information.

```md
# CLAUDE.md

## Mission
- Objective:
- Success criteria:

## Execution Rules
- Do not harden scaffolding until these are approved or explicitly waived:
  - `<artifact_locations.tooling_survey>`
  - `<artifact_locations.module_system>`
  - `<artifact_locations.mvp_spec>`
  - `<artifact_locations.milestones_ledger>`
- Do not rely on chat history for durable project memory.

## Constraints & Assumptions
- ...
- UNCONFIRMED: ...

## Decisions
- ...

## State
- Phase:
- Current milestone:
- Creator mode:
- Active packs:
- Active roles:
- Done:
- Now:
- Next:
- Drift status:
- Next handoff owner:

## Active Working Set
- Branch or worktree:
- Key files:
- Sanity-check command:

## Boot Path
1. `<artifact_locations.control_plane>`
2. `<artifact_locations.memory_hub>` if present
3. `<artifact_locations.project_state>`
4. `<artifact_locations.system_state_index>`
5. `<artifact_locations.starters>`
6. `<artifact_locations.tool_registry>` if scripts or shortcuts exist
7. `<artifact_locations.improvement_ledger>` or `<artifact_locations.playbook_registry>` when the control plane shows open candidates or active playbooks
8. `<artifact_locations.artifact_health_report>` when drift signals are open or repair-drift is active

Do not turn this file into a generic summary of the repo.
```

## `<state_doc_home>/repo-operating-profile.yaml`

Use [.claude/repo-os/references/control-plane-template.md](control-plane-template.md) for the full schema. Keep the file terse and machine-readable.

```yaml
version: 1
operator_profile_ref: ~/.claude/memory/repo-operating-system/operator-profile.yaml
repo_fingerprint:
  repo_kind: app
  secondary_traits: []
  maturity_state: partially_initialized
  taxonomy_mode: inferred
layout_strategy:
  planning_doc_home: docs
  state_doc_home: memory
  task_spec_home: docs/tasks
  script_home: scripts
reality_model:
  repo_root: .
  workspace_boundaries:
    child_repos: []
  entrypoints:
    - src/index.ts
  owned_surfaces:
    - auth
  key_commands:
    install: npm install
    sanity: npm test -- --runInBand smoke
artifact_health:
  status_by_artifact:
    control_plane: healthy
    docs_index: stale
  lifecycle:
    required:
      - CLAUDE.md
      - memory/repo-operating-profile.yaml
    active:
      - memory/project-state.md
    dormant: []
    stale:
      - memory/docs-index.md
    archived: []
drift_signals:
  - surface: auth
    mismatch: docs and code disagree
    action: activate repair-drift
    status: open
artifact_locations:
  control_plane: memory/repo-operating-profile.yaml
  memory_hub: memory/MEMORY.md
  project_state: memory/project-state.md
  system_state_index: memory/SYSTEM_STATE_INDEX.md
  tool_registry: memory/tool-registry.md
  improvement_ledger: memory/improvement-ledger.md
  playbook_registry: memory/playbook-registry.md
  surface_map: memory/surface-map.yaml
  artifact_health_report: memory/artifact-health.md
  starters: docs/starters.md
  capability_map: docs/capability-map.md
profile:
  selected: app
  activated_families:
    - planning
    - operating
boot_path:
  hot:
    - CLAUDE.md
    - memory/repo-operating-profile.yaml
    - memory/MEMORY.md
    - memory/project-state.md
quality_gates:
  sanity_check: npm test -- --runInBand smoke
  sanity_expected: "0 failed"
capability_discovery:
  mode: continuous
  unresolved_capabilities:
    - auth
  open_questions:
    - Is managed auth acceptable?
improvement_system:
  mode: assertive
  local_artifacts:
    improvement_ledger: memory/improvement-ledger.md
    playbook_registry: memory/playbook-registry.md
  global_catalog: ~/.claude/memory/repo-operating-system/global-pattern-catalog.md
  open_candidates:
    - wake-up acceleration
  active_playbooks:
    - release-recovery
  promotion_thresholds:
    wakeup_or_verification: one successful validation
    general: two observations or one successful use with clear repeatable benefit
    global: local validation plus portability pass
  last_retrospective: 2026-03-09
  global_catalog_mode: suggestion_only
collaboration_architecture:
  creator_strengths:
    - structural thinking
    - conceptual generation
  recurring_bottlenecks:
    - narrowing
    - sequencing
    - completion
  current_creator_mode: dense_idea_drop
  active_roles:
    - Interpreter-Architect
    - Critical Counterweight
    - Scope Governor
    - Implementation Strategist
  role_pipeline:
    - Interpreter-Architect
    - Critical Counterweight
    - Scope Governor
    - Implementation Strategist
  pending_role_handoffs:
    - from: Implementation Strategist
      to: Finisher-Operator
      trigger: artifact is ready to finish
  active_build_layer: current milestone implementation
  preserved_future_layer: future architecture notes
  role_routing_notes:
    - convert dense input into scoped, sequenced, finished artifacts
decision_policy:
  autonomy_level: assertive
  confidence_floor: medium
  ask_vs_act:
    low: act
    medium: ask when constraints are unresolved
    high: require confirmation
operation_packs:
  active:
    - resume
    - capability-discovery
  dormant:
    - repair-drift
skill_routing:
  preferred_by_task:
    repo_governance: repo-operating-system
  fallback_behavior: handle internally
improvement_metrics:
  reuse_count: 4
  verification_success_rate: 0.83
  estimated_time_saved: moderate
  failures_avoided: 2
maintenance:
  orientation_command: bash scripts/session_start.sh
  next_action: ...
```

## `<state_doc_home>/MEMORY.md`

Use this only when the repo has enough ongoing state that a lean landing page reduces startup cost. It should be shorter than `project-state.md`.

```md
# Project Memory

## What This Repo Is
- One-sentence identity:
- What it is not:

## Current Status
- Current milestone:
- Current phase:
- Current next gate:
- Creator mode:
- Active roles:
- Next handoff owner:
- Active build layer:
- Preserved future layer:

## Session Start Protocol
- Say `resume` or run `<orientation command if one exists>`
- Read this file, then `<artifact_locations.project_state>`
- Read the shared operator profile when the control plane references it
- Scan `<artifact_locations.tool_registry>`
- Read `<artifact_locations.improvement_ledger>` or `<artifact_locations.playbook_registry>` when the control plane shows open candidates or active playbooks
- Read `<artifact_locations.artifact_health_report>` when drift signals are open
- Run the sanity-check command before writing code when safe

## Key Non-Negotiables
1. ...
2. ...
3. ...

## Repo Key Facts
- Primary runtime or package:
- Entry point:
- Test location:
- Package manager:
- Sanity-check command:

## Linked Memory Files
- `<artifact_locations.docs_index>`: task-to-doc routing
- `<artifact_locations.project_state>`: current progress and blockers
- `<artifact_locations.system_state_index>`: fragility map, why-not graveyard, routing
- `<artifact_locations.tool_registry>`: commands, scripts, gates, pipelines
- `<artifact_locations.improvement_ledger>`: raw lessons, candidates, validation status
- `<artifact_locations.playbook_registry>`: promoted heuristics, recovery flows, procedures
- `<artifact_locations.artifact_health_report>`: contradiction status and artifact freshness
- `architecture decisions`: why the architecture is shaped this way
- `invariants`: unbreakable rules

## Starter Summary
- `resume`: continue the active work safely
- `status`: report state only
- `plan [task]`: design first
- dense idea handling: extract the core thesis, translate it technically, preserve later-phase consequences, then recommend the smallest buildable step
- `build [thing]` or `implement [task]`: direct execution on a specific target
- `tool scan [capability]`: research existing ecosystem solutions before custom build
- `repair drift`: repair contradictions before trusting stale state
- `forge` or `retrospect`: convert friction or wins into durable upgrades
- `test`: run verification only
```

## Root `CLAUDE.md` Compatibility Shim

Use this only for merged dual-agent repos or a temporary compatibility phase.

```md
# CLAUDE.md

## Compatibility Note
This repository uses shared agent-operating files.

Read in order:
1. `CLAUDE.md`
2. `<artifact_locations.control_plane>`
3. `<artifact_locations.memory_hub>` if present
4. `<artifact_locations.project_state>`
5. `<artifact_locations.starters>`

## Claude-Specific Notes
- Add only Claude-specific deltas here.
- Do not duplicate the full repository protocol.
```

## `<planning_doc_home>/agent-system-migration.md`

```md
# Agent System Migration

## Selected Mode
- `codex-only conversion | merged dual-agent repo | Claude-preserving Claude Code overlay`

## Detected Artifacts
| Path | Type | Current role | Keep, merge, archive, or replace |
| --- | --- | --- | --- |

## Shared Durable Truth
- `CLAUDE.md`
- `<artifact_locations.control_plane>`
- `<artifact_locations.memory_hub>` if present
- `<artifact_locations.docs_index>`
- `<artifact_locations.project_state>`
- `<artifact_locations.system_state_index>`

## Adapter Status
- Primary agent:
- Foreign adapters enabled:
- Claude mode:

## Claude-Specific Overlay
- `CLAUDE.md` role:
- Additional Claude-only files:

## Mapping Decisions
| Source artifact | Mapped into | Notes |
| --- | --- | --- |

## Approval Status
- User approved mode:
- User approved file changes:
- Follow-up required:
```

## `<planning_doc_home>/capability-map.md`

Use this when the repo needs a living record of ongoing tool and library discovery outside a single initial survey.

```md
# Capability Map

## Current Focus
- Capability classes currently under review:
- Why they matter now:

## Capability Opportunities
| Capability Class | Current Coverage | Candidate Tools or Services | Recommendation | Open Questions | Status |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## Questions For The User
- ...
- ...

## Adopted Decisions
| Capability | Choice | Why | Recorded in |
| --- | --- | --- | --- |
|  |  |  |  |

## Deferred or Rejected Options
| Capability | Option | Why deferred or rejected | Revisit trigger |
| --- | --- | --- | --- |
|  |  |  |  |
```

## `<state_doc_home>/docs-index.md`

```md
# Docs Index

## Quick Task -> Doc Map
| Task | Read |
| --- | --- |
| Understand the repo | `<path>` |
| Build order | `<path>` |
| Invariants | `<artifact_locations.invariants>` |
| Decisions | `<artifact_locations.architecture_decisions>` |

## Preferred Ingestion Order
- Canonical:
- Supplemental or legacy:
- Foundations or historical:

## Boot Path
1. `path/to/file` - why this file belongs in the boot path
2. `path/to/file` - what it answers quickly

## Session Start Files
- Always read:
- Read only for milestone:
- Read only for subsystem:

## Canonical
| Path | Scope | Why canonical | Notes |
| --- | --- | --- | --- |

## Supplemental or Legacy
| Path | When to read | Risk if treated as truth |
| --- | --- | --- |

## Foundational, Speculative, or Historical
| Path | Use when | Notes |
| --- | --- | --- |

## Conflicts To Watch
- `file-a` vs `file-b`: short explanation and tie-breaker

## Search Hints
- Intent:
  - Prefer:
  - Search hint:
  - Stop after:

## Closed Decisions To Respect
| Decision | Resolution |
| --- | --- |
| Example | Already settled; do not re-open without new evidence |

## Review Log
- Last reviewed:
- Reviewed by:
- Open questions:
```

## `<state_doc_home>/project-state.md`

```md
# Project State

## Snapshot
- Phase:
- Current milestone:
- Repo status:
- Last updated:
- Branch or worktree:
- Package manager:
- Agent-system mode:
- Active packs:
- Creator mode:
- Active roles:
- Next handoff owner:
- Decision posture:
- Drift status:
- Structural thesis of current work:

## Milestone Status
| Milestone | Status |
| --- | --- |
| A | |
| B | |

## Recent Progress
- ...

## Current Priorities
1. ...
2. ...

## Blockers
- ...

## Completion Map
- Fully implemented:
- Partially implemented:
- Stubbed or pending:
- Verification coverage:

## Next Likely Tasks
- ...

## Next Gate
- Exact next action:
- Gate or verification to pass:
- Future-layer consequence to preserve:

## Minimum Boot Path
1. `CLAUDE.md`
2. `<artifact_locations.control_plane>`
3. `<artifact_locations.memory_hub>` if present
4. `<artifact_locations.project_state>`
5. `<artifact_locations.system_state_index>`
6. `<artifact_locations.starters>`
7. `<artifact_locations.tool_registry>` if scripts or shortcuts exist
8. `<artifact_locations.improvement_ledger>` or `<artifact_locations.playbook_registry>` when the control plane shows open candidates or active playbooks
9. `<artifact_locations.artifact_health_report>` when the control plane shows open contradictions

## Sanity-Check Command
- `...`

## Planning Gate Status
- Tooling survey:
- Module system:
- MVP spec:
- Milestones:
- Agent migration, if applicable:

## Active Working Set
- Files:
- Commands or processes:
- Integrations in play:

## Fragility Map
- Surface:
  - Why fragile:
  - Verification to run:

## Verification Status
- Last run:
- Passed:
- Failed:

## Why-Not Graveyard Summary
- Rejected option:
  - Reason:
  - Revisit trigger:

## Improvement State
- Open candidates:
- Active playbooks:
- Last retrospective:
- Next validation target:

## Governance State
- Active operation packs:
- Skill routing:
- Artifact lifecycle notes:
- Contradiction repair status:
- Active role pipeline:
- Pending role handoffs:
- Active build layer:
- Preserved future layer:

## Session Work Log
- Session:
  - What changed:
  - What remains:

## Handoff Note
- Next action:
- First files to read next time:
- Later-phase architecture preserved:
```

## `<state_doc_home>/SYSTEM_STATE_INDEX.md`

~~~md
# System State Index

## Sanity-Check Command
```bash
<command>
```
- Expected output:
- If it fails:

## Current State
- Current milestone:
- Current phase:
- What is done:
- What is next:

## Fragility Map

### Critical
- Surface:
  - Why fragile:
  - Step carefully here:
  - Verification:

### Moderate
- Surface:
  - Why fragile:
  - Verification:

## Why-Not Graveyard
- Rejected path:
  - Reason:
  - Where recorded:

## Token-Optimized Routing
| Task or Surface | Read first | Then read | Why only these files |
| --- | --- | --- | --- |
| auth | `<path>` | `<path>` | |
| release | `<path>` | `<path>` | |

## Dependency Graph or Build Order
```text
Step A
  ↓
Step B
  ↓
Step C
```

## Environment Notes
- Runtime or interpreter:
- Venv or toolchain location:
- Install command:
- Known environment pitfalls:

## Contradictions or Drift
- Open contradictions:
- Surfaces under repair:
- Source of truth to prefer first:
~~~

## `<state_doc_home>/surface-map.yaml`

Use this only when the repo is large or structurally complex enough that machine-readable topology saves future sessions from broad rediscovery.

```yaml
version: 1
repo_root: .
workspace_boundaries:
  child_repos: []
  isolated_worktrees: []
entrypoints:
  - src/index.ts
owned_surfaces:
  - auth
  - billing
key_commands:
  install: npm install
  sanity: npm test -- --runInBand smoke
integrations:
  - github
```

## `<state_doc_home>/artifact-health.md`

Use this only when drift, contradiction repair, or artifact lifecycle management is active.

```md
# Artifact Health

## Current Drift Status
- Contradictions open:
- Active repair pack:
- Next repair action:

## Artifact Status
| Artifact | Health | Lifecycle | Notes |
| --- | --- | --- | --- |
| CLAUDE.md | healthy | required | |
| project-state.md | stale | active | |

## Boot Trust
- Safe to use current boot path:
- Artifacts to ignore until repaired:
```

## `<state_doc_home>/tool-registry.md`

Keep this registry scannable and command-only. When the repo has enough tooling, structure it like a HUD: sanity gates first, then reusable scripts, then discovered pipelines.

~~~md
# Tool Registry

## Sanity Gates

### Primary sanity gate
```bash
<command>
```
- Solves:
- Expected:
- Efficiency:

### Full verification
```bash
<command>
```
- Solves:
- Expected:

## Scripts

### `<script path>`
```bash
<command>
```
- Solves:
- When to use:
- Verification:
- Efficiency:

## Pipelines

### `<pipeline name>`
```bash
<command>
```
- Solves:
- Touched surfaces:
- Efficiency:

## Registry Maintenance Protocol
1. Create the reusable script or command entry in `<script_home>` when it will help future sessions.
2. Add the entry to this file immediately.
3. If the command implies a broader repeatable procedure, recovery flow, or heuristic, record it in `<artifact_locations.improvement_ledger>` or promote it into `<artifact_locations.playbook_registry>`.
4. If the tool changes architectural constraints, also update decisions or state artifacts.
5. Fix or remove stale commands instead of letting the registry drift.
~~~

## `<state_doc_home>/improvement-ledger.md`

Use this as the raw candidate queue for the Forge Loop. It tracks observed friction, wins, and repeatable patterns before promotion or retirement.

~~~md
# Improvement Ledger

## Open Candidates
| Candidate | Trigger | Type | Evidence | Status | Promotion Target | Next Validation | Portability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| wake-up acceleration | slow resume | starter upgrade | resume used twice with the same recovery detour | validating | starters.md | verify next two resumes | likely portable |

## Recently Promoted
| Candidate | Promoted to | Why now | Follow-up |
| --- | --- | --- | --- |
| verification triage loop | playbook-registry.md | stabilized after failed test recovery | re-check after next regression |

## Retired or Rejected
| Candidate | Reason | Retired to | Revisit trigger |
| --- | --- | --- | --- |
|  |  |  |  |

## Retrospectives

### <date or milestone>
- What slowed us down:
- What saved us time:
- What should become part of the suit:
- What should never be repeated:
- Compile target if this should become a pack or specialist skill:
~~~

## `<state_doc_home>/playbook-registry.md`

Use this for promoted multi-step procedures, failure recovery flows, decision heuristics, and routing intelligence. If it is a raw command, it belongs in the tool registry instead.

~~~md
# Playbook Registry

## Active Playbooks

### <Playbook Name>
- Trigger:
- Use when:
- Do not use when:
- First files to read:
- First commands to run:
- Steps:
  1. ...
  2. ...
  3. ...
- Verification:
- Expected benefit:
- Source candidate:

## Dormant or Archived Playbooks

### <Playbook Name>
- Why archived:
- Revisit trigger:
~~~

## `~/.claude/memory/repo-operating-system/global-pattern-catalog.md`

This is the shared portable catalog for patterns that have already survived a local validation pass and a portability scrub. It is not a skill source file.

~~~md
# Repo Operating System Global Pattern Catalog

## Rules
- Portable patterns only.
- No repo-specific secrets, paths, customer names, or assumptions.
- New entries start as `provisional`.
- Only `validated` entries may shape defaults automatically in future repos.

## Provisional Patterns

### <Pattern Name>
- Repo profiles:
- Trigger:
- Promotion target:
- Expected benefit:
- Contraindications:
- Source repo pattern:
- Status: provisional

## Validated Patterns

### <Pattern Name>
- Repo profiles:
- Trigger:
- Promotion target:
- Expected benefit:
- Contraindications:
- Status: validated
~~~

## `~/.claude/memory/repo-operating-system/operator-profile.yaml`

This is the shared user-level preference layer for how the repo operating system should behave by default across repos. Repo-local policy may override it.

```yaml
version: 1
defaults:
  build_vs_buy: prefer_proven
  managed_services: pragmatic
  risk_tolerance: medium
  ask_frequency: targeted
  artifact_depth: lean_durable
  verification_strictness: strict_core
decision_policy:
  autonomy_level: assertive
  confidence_floor: medium
  ask_vs_act:
    low: act
    medium: ask_when_constraints_are_unresolved
    high: require_confirmation
workflow:
  fresh_context_bias: high
  worktree_bias: prefer_for_risky_or_parallel
  shared_catalog_mode: suggestion_only
communication:
  style: direct_structural_translation
  filler_tolerance: low
  enthusiasm_style: restrained
  explanation_ladder:
    - whole
    - subsystem
    - mechanism
    - detail
collaboration:
  creator_strengths:
    - structural thinking
    - symbolic mapping
    - cross-domain linkage
    - conceptual generation
  creator_bottlenecks:
    - narrowing
    - decision freezing
    - sequencing
    - continuity
    - completion
  delta_labor_rule: do what the creator cannot reliably sustain alone
  metaphor_policy: translate_not_flatten
  dense_idea_protocol:
    - core_thesis
    - architectural_consequences
    - doc_or_spec_updates
    - immediate_implementation_consequences
    - later_phase_items_to_preserve
    - recommended_next_action
  ambiguity_policy: preserve_until_implementation_requires_cut
  pushback_style: protect_project_without_normalizing_it
  planning_bias: phased_decomposition
  product_bias: genuine_user_of_one_fit_first
  creator_mode_handling:
    vision_burst:
      - Interpreter-Architect
      - Critical Counterweight
      - Scope Governor
    milestone_shaping:
      - Scope Governor
      - Implementation Strategist
    technical_translation:
      - Interpreter-Architect
      - Implementation Strategist
      - Finisher-Operator
    identity_defense:
      - Critical Counterweight
      - Scope Governor
      - Interface Translator
    dense_idea_drop:
      - Interpreter-Architect
      - Critical Counterweight
      - Scope Governor
      - Implementation Strategist
  preferred_role_pipeline:
    - Interpreter-Architect
    - Critical Counterweight
    - Scope Governor
    - Implementation Strategist
    - Finisher-Operator
    - Continuity Steward
  finish_bias: high
  continuity_bias: high
  horizon_management:
    active_layer: build_now
    preserved_layer: future_architecture
```

## `<planning_doc_home>/starters.md`

Keep the phrases short. The phrases are the interface; the protocol is the repo operating system's job.

```md
# Starters

## Primary Wake Phrases
- `resume`: Read `CLAUDE.md`, the control plane, the shared operator profile when referenced, `<artifact_locations.memory_hub>` if present, the hot boot files, and the tool registry; read `<artifact_locations.improvement_ledger>` or `<artifact_locations.playbook_registry>` when the control plane shows open candidates or active playbooks; check `reality_model`, `artifact_health`, and `drift_signals` before trusting stale state; reconstruct creator mode, active roles, and pending role handoffs; activate `repair-drift` before broad implementation when contradictions are open; if the next task implies a commodity capability or unresolved stack choice, run capability discovery before coding; apply decision policy, the active internal role chain, and specialist-skill routing when relevant; run the sanity-check command if defined; read only the files needed for the next task; state the action; execute; update state artifacts.
- `continue`: Alias of `resume`.
- `what next`: Read the boot files and return only the next action, blockers, and first files to read.
- `next`: Faster alias of `what next`.
- `verify state`: Run the sanity-check command and report whether the repo still matches the documented state.
- `test`: Run the documented verification path and report results without writing code. If verification reveals a repeatable failure pattern or recovery path, record it in the improvement system.
- `refresh map`: Update docs index, routing, and state artifacts without broad implementation work.
- `repair drift`: Compare ledgers, control plane, project state, system state, and executable repo signals; repair only the conflicting surfaces; refresh artifact-health and the boot path.
- `resume [subsystem]`: Read the boot files plus the named subsystem route, then continue only within that surface.

## Execution Phrases
- `bootstrap`: Establish planning artifacts, the operational ledger, the boot path, and the smallest safe scaffold for the current milestone.
- `status`: Summarize phase, planning-gate status, milestone status, blockers, and the next action from the current state files. Do not start coding.
- `review`: Inspect the changed surface, identify risks or regressions, and update state artifacts if findings change the plan. Report before fixing.
- `sync`: Reconcile docs, code, and state files; record conflicts and resolve stale routing without broad feature work.
- `plan [task]`: Read only the relevant boot files and subsystem files, run capability discovery if the task touches unresolved tooling or a commodity capability, then propose the smallest safe execution slice. Do not implement until approved.
- `build [thing]`: Alias for targeted implementation when the target is already clear, but stop for capability discovery first if the target would recreate a mature external solution.
- `implement [task]`: Confirm the relevant state, run capability discovery first when needed, make the smallest viable change, verify it, and refresh state files.
- `explain [thing]`: Read only the relevant docs and code, then explain the subsystem or concept without changing files.
- `tool scan [capability]`: Inspect the repo surface, research live ecosystem options with web search and primary sources, ask only the questions that affect the choice, and update the capability map or tooling survey.
- `research [capability]`: Alias for `tool scan [capability]`.
- `forge`: Run a focused improvement pass. Read the control plane plus the improvement ledger and playbook registry, classify open candidates, promote safe wins, and expose new suit capabilities.
- `retrospect`: Run the mandatory retrospective questions against the current milestone, failure, workaround, or capability decision and record the result in the improvement ledger.
- `what did we learn`: Summarize promoted tools, active playbooks, open candidates, and any portable patterns ready for global sync.
- `verify`: Run the sanity-check command plus task-specific verification, record the result, and open an improvement candidate when verification exposes a repeatable pain point.
- `handoff`: Refresh project-state, system-state, routing, decisions, planning-gate status, tool registry, improvement ledger, playbook registry, artifact-health, creator mode, active roles, next handoff owner, active packs, skill-routing state, and shared global-pattern sync state so the next session can continue cheaply.
- `resume cautiously`: Reconstruct state without broad edits; verify assumptions before changing code.

## Phrase Summary
| Phrase | What It Does | Writes Code? |
| --- | --- | --- |
| `resume` | Pick up where work stopped and continue | Yes |
| `status` | Report current state only | No |
| `plan [task]` | Design first, present a plan | No |
| `build [thing]` | Execute on a specific target | Yes |
| `test` | Run verification only | No |
| `repair drift` | Repair contradictions before trusting stale state | No by default |
| `sync` | Update memory to match reality | No |
| `review` | Audit for risk or drift | No by default |
| `explain [thing]` | Explain a subsystem or concept | No |
| `tool scan [capability]` | Research ecosystem options and recommend a choice | No |
| `forge` | Promote safe improvements into durable repo capabilities | No by default |
| `retrospect` | Capture lessons and decide what should become part of the suit | No |
| `what did we learn` | Summarize current improvements and promoted capabilities | No |
| `next` | Return the next action only | No |

## Fresh-Context Workflow
1. Use one thread for exploration or one implementation slice.
2. End or reset the thread after broad exploration or task completion when practical.
3. Start fresh with a wake phrase and exact files or a task spec when known.
4. For non-trivial work, create or read `<task_spec_home>/<slug>.md` before implementation-heavy changes.

## Token Efficiency Notes
- `resume`, `next`, `status`, and `sync` should load only the boot stack and the exact state files they need.
- `repair drift` should load only the conflicting state files plus the smallest executable surfaces needed to resolve the contradiction.
- `plan [task]`, `build [thing]`, and `explain [thing]` should load only the boot stack plus the exact canonical docs for that surface.
- `tool scan [capability]` should read only the boot stack, the affected surface docs, and the current capability artifacts before researching live options.
- `forge`, `retrospect`, and `what did we learn` should read the control plane plus the improvement ledger and playbook registry before expanding to any broader repo surface.
- Foundations and supplemental docs stay cold unless the current task requires them.
```

## `<planning_doc_home>/task-routing-index.md`

```md
# Task Routing Index

| Task or Surface | Read first | Then read | Verify with | Notes |
| --- | --- | --- | --- | --- |
| auth | `<path>` | `<path>` | `<command>` | |
| release | `<path>` | `<path>` | `<command>` | |
```

## `<planning_doc_home>/invariants.md`

Use this format for rules that are genuinely unbreakable.

```md
# Invariants

## Invariant 1: <Rule Name>
- Rule:

### You are never allowed to:
- ...
- ...

### Enforcement locations:
- `<path>` - what enforces the rule
- `<path>` - secondary enforcement

### Tests that catch violation:
- `<test path or name>`
- `<test path or name>`
```

## `<planning_doc_home>/architecture-decisions.md` or `<state_doc_home>/architecture-decisions.md`

```md
# Architecture Decisions

## ADR-001: <Decision Title>
- Status:
- Decision:
- Why:
- Rejected alternatives:
- Consequences:
- Revisit trigger:
- Implementation implications:
```
