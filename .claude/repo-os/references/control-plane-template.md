# Control Plane Template

Use this reference when creating or refreshing `<state_doc_home>/repo-operating-profile.yaml`.

## Purpose

This file is the machine-readable control plane for the repository operating system. Keep it terse, factual, and synchronized with root `CLAUDE.md` and the human-facing state artifacts.

## Rules

- Prefer stable keys over prose.
- Record paths exactly as they exist in the target repo.
- Do not dump broad repo summaries here.
- Update this file whenever the boot path, profile, milestone, next action, adapter mode, decision policy, active pack set, artifact health, or drift status changes.
- Update this file whenever creator mode, active roles, role handoffs, or build-layer preservation changes.
- If the repo already has a coherent machine-readable operations file, extend it rather than creating a competing source of truth.

## Suggested Schema

```yaml
version: 1

operator_profile_ref: ~/.claude/memory/repo-operating-system/operator-profile.yaml

repo_fingerprint:
  repo_kind: app
  secondary_traits:
    - mixed-agent
  maturity_state: partially_initialized
  taxonomy_mode: explicit
  taxonomy:
    hot:
      mode: preserved
      sources:
        - CLAUDE.md
        - memory/project-state.md
    warm:
      mode: inferred
      sources:
        - docs/task-routing-index.md
        - MILESTONES.md
    cold:
      mode: preserved
      sources:
        - foundations/

layout_strategy:
  planning_doc_home: docs
  state_doc_home: memory
  task_spec_home: docs/tasks
  script_home: scripts

reality_model:
  repo_root: .
  umbrella_root: /Users/lucasbrown/Projects
  workspace_boundaries:
    child_repos: []
    isolated_worktrees: []
  entrypoints:
    - apps/web/src/main.tsx
    - packages/api/src/index.ts
  owned_surfaces:
    - auth
    - billing
  key_commands:
    install: pnpm install
    sanity: pnpm test -- --runInBand smoke
    build: pnpm build
  integrations:
    - github
    - playwright

artifact_locations:
  agents_ledger: CLAUDE.md
  control_plane: memory/repo-operating-profile.yaml
  memory_hub: memory/MEMORY.md
  docs_index: memory/docs-index.md
  project_state: memory/project-state.md
  system_state_index: memory/SYSTEM_STATE_INDEX.md
  tool_registry: memory/tool-registry.md
  improvement_ledger: memory/improvement-ledger.md
  playbook_registry: memory/playbook-registry.md
  surface_map: memory/surface-map.yaml
  artifact_health_report: memory/artifact-health.md
  starters: docs/starters.md
  task_routing: docs/task-routing-index.md
  capability_map: docs/capability-map.md
  invariants: docs/invariants.md
  architecture_decisions: docs/architecture-decisions.md
  tooling_survey: docs/tooling-survey.md
  module_system: docs/module-system.md
  mvp_spec: docs/mvp_spec.md
  milestones_ledger: MILESTONES.md
  milestone_details_home: docs/milestones
  agent_migration: docs/agent-system-migration.md

profile:
  selected: app
  activated_families:
    - planning
    - operating
    - hardening
  task_spec_required_when:
    - non-trivial active slice
    - work crosses multiple modules

boot_path:
  hot:
    - CLAUDE.md
    - memory/repo-operating-profile.yaml
    - memory/MEMORY.md
    - memory/project-state.md
    - memory/SYSTEM_STATE_INDEX.md
  warm:
    - docs/task-routing-index.md
    - MILESTONES.md
    - docs/starters.md
  cold:
    - docs/legacy-notes.md

artifact_health:
  status_by_artifact:
    agents_ledger: healthy
    control_plane: healthy
    memory_hub: active
    docs_index: stale
    surface_map: missing
  lifecycle:
    required:
      - CLAUDE.md
      - memory/repo-operating-profile.yaml
    active:
      - memory/project-state.md
      - docs/starters.md
    dormant:
      - docs/legacy-notes.md
    stale:
      - memory/docs-index.md
    archived: []

drift_signals:
  - surface: auth
    mismatch: docs mention JWT; code uses session cookies
    sources:
      - docs/architecture-decisions.md
      - packages/api/src/auth.ts
    action: activate repair-drift before implementation
    status: open

quality_gates:
  sanity_check: npm test -- --runInBand smoke
  sanity_expected: "0 failed"
  defaults:
    - lint
    - typecheck
    - test

capability_discovery:
  mode: continuous
  current_focus:
    - auth
  unresolved_capabilities:
    - queueing
  open_questions:
    - Is managed infrastructure acceptable for background jobs?
  research_standard:
    - official docs
    - package registry
    - release notes
  decision_artifacts:
    tooling_survey: docs/tooling-survey.md
    capability_map: docs/capability-map.md

improvement_system:
  mode: assertive
  local_artifacts:
    improvement_ledger: memory/improvement-ledger.md
    playbook_registry: memory/playbook-registry.md
  global_catalog: ~/.claude/memory/repo-operating-system/global-pattern-catalog.md
  open_candidates:
    - wake-up acceleration
  promotion_thresholds:
    wakeup_or_verification: one successful validation
    general: two observations or one successful use with clear repeatable benefit
    global: local validation plus portability pass
  last_retrospective: 2026-03-09
  active_playbooks:
    - release-recovery
  global_catalog_mode: suggestion_only

collaboration_architecture:
  creator_strengths:
    - structural thinking
    - cross-domain translation
    - conceptual generation
  recurring_bottlenecks:
    - narrowing
    - sequencing
    - completion
    - continuity
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
      trigger: when the current artifact is implementation-ready
  active_build_layer: current milestone implementation
  preserved_future_layer: future architecture notes
  role_routing_notes:
    - Do what the creator cannot reliably sustain alone.
    - Preserve signal, then convert it into constraints and finished artifacts.

decision_policy:
  autonomy_level: assertive
  confidence_floor: medium
  blast_radius:
    low: reversible local changes
    medium: architecture or tooling decisions within repo boundaries
    high: destructive, external, security, compliance, or lock-in changes
  ask_vs_act:
    low: act
    medium: ask when constraints or tradeoffs remain unresolved
    high: require confirmation
  reversible_actions:
    - ledger refresh
    - routing repair
    - tool promotion
  irreversible_actions:
    - destructive migration
    - vendor lock-in
    - public API break

operation_packs:
  active:
    - resume
    - capability-discovery
    - prepare-handoff
  dormant:
    - repair-drift
  last_completed:
    - retro-forge

skill_routing:
  preferred_by_task:
    repo_governance: repo-operating-system
    skill_authoring: skill-creator
  fallback_behavior: handle internally when no specialist skill is available
  delegation_rules:
    - Repo operating system keeps boot, state, guardrails, and handoff centralized.
    - Specialist skills may own narrow execution slices only after routing is recorded.

improvement_metrics:
  reuse_count: 4
  verification_success_rate: 0.83
  estimated_time_saved: moderate
  failures_avoided: 2
  stale_upgrades:
    - old-release-playbook
  net_negative_patterns: []

agent_adapters:
  codex:
    enabled: true
    role: primary
  claude:
    enabled: true
    mode: merged-dual-agent
    shim_path: CLAUDE.md
    migration_doc: docs/agent-system-migration.md

maintenance:
  active_pack: resume
  stale_surfaces:
    - auth
  changed_surfaces:
    - docs
  last_drift_check: 2026-03-09
  orientation_command: bash scripts/session_start.sh
  last_refreshed: 2026-03-09
  next_action: verify auth routing and refresh task spec
```

## Minimum Required Keys

- `repo_fingerprint`
- `layout_strategy`
- `reality_model`
- `artifact_locations`
- `artifact_health`
- `drift_signals`
- `collaboration_architecture`
- `profile.selected`
- `profile.activated_families`
- `boot_path.hot`
- `quality_gates.sanity_check`
- `capability_discovery`
- `improvement_system`
- `decision_policy`
- `operation_packs`
- `skill_routing`
- `improvement_metrics`
- `agent_adapters`
- `maintenance.next_action`

## Sync Contract

These values must match the human-readable state files:

- repo kind
- active milestone
- next action
- boot path
- adapter mode
- sanity-check command
- active playbooks
- open candidates
- drift status
- active packs
- decision policy
- creator mode
- active roles
- pending handoffs
