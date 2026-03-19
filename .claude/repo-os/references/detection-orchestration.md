# Detection and Orchestration

Use this reference before selecting file locations, repo profiles, or artifact families.

## Goal

Scan the repo first, classify it accurately enough to avoid template overreach, then run only the relevant parts of the skill. Do not assume a Velm-style `docs/` tree, a `memory/` folder, or canonical versus supplemental versus foundations folders unless the repo actually uses them.

## Orchestration Pipeline

Run this sequence in order:

1. detect repo shape and fingerprint
2. build the reality layer and workspace-boundary model
3. choose the layout strategy
4. choose the repo-type profile
5. activate artifact families and operation packs
6. set decision policy and skill-routing rules
7. create or refresh only the minimum relevant files
8. record the chosen operating model in both root `CLAUDE.md` and `<state_doc_home>/repo-operating-profile.yaml`

## Build the Repo Fingerprint

Inspect the smallest useful set of signals:

- top-level folders such as `docs/`, `memory/`, `specs/`, `plans/`, `scripts/`, `tools/`, `apps/`, `packages/`, `services/`, `jobs/`
- root files such as `README*`, `MILESTONES*`, `CLAUDE.md`, `CLAUDE.md`, `MEMORY.md`, workspace manifests, release configs, and major package manifests
- build, package, pipeline, deployment, and test files
- existing task, plan, architecture, or runbook docs

Record:

- `repo_kind`
- `secondary_traits`
- `maturity_state`
- `taxonomy_mode`
- whether foreign-agent artifacts exist
- whether existing operating artifacts are current, stale, partial, or missing
- whether the current directory is the true repo root or an umbrella folder
- whether existing artifact lifecycle states are active, dormant, stale, or archived

## Reality Layer

Capture only the facts that improve routing and contradiction detection:

- repo root and workspace boundaries
- child repos or isolated worktrees
- likely entrypoints
- owned surfaces or subsystem boundaries
- key commands such as install, sanity, and build
- active integrations that affect verification or routing

Create a machine-readable `surface-map.yaml` only when the repo is large or structurally complex enough that these facts would otherwise be rediscovered repeatedly.

## Repo Kind Heuristics

Select one primary `repo_kind`, then record secondary traits separately.

### `monorepo`

Prefer when multiple apps, packages, services, or workspaces are first-class and share a root task runner or workspace manager.

### `data`

Prefer when pipelines, notebooks, dbt, job runners, datasets, or transform graphs dominate the repo's purpose.

### `infra`

Prefer when infrastructure-as-code, deployment systems, platform automation, or environment operations dominate the repo's purpose.

### `library`

Prefer when the main output is a package, SDK, component set, or reusable contract surface rather than a deployable end-user runtime.

### `app`

Prefer when the main output is a deployable product, API, site, service, desktop app, or mobile app for end users or internal users.

## Maturity-State Heuristics

- `greenfield`: little or no executable surface, no durable planning or state system yet
- `brownfield_with_docs`: meaningful code and meaningful docs already exist
- `brownfield_sparse`: meaningful code exists but docs are thin or scattered
- `partially_initialized`: planning or state artifacts exist, but the operating system is incomplete
- `operating`: the repo already has a coherent ledger, state artifacts, and routing system

## Layout Strategy

Prefer existing conventions over imposing new ones.

### Planning docs

Choose `planning_doc_home` in this order:

1. existing coherent `docs/`
2. existing coherent `specs/` or `plans/`
3. root-level markdown if the repo already keeps major docs at root
4. create `docs/` only when no better durable home exists

### State docs

Choose `state_doc_home` in this order:

1. existing `memory/`
2. existing lightweight operational folder if clearly intended for state
3. create `memory/` when no better durable home exists

### State hub

Detect whether the repo already uses a concise state-hub file such as `MEMORY.md` or `memory.md`.

- Preserve it when it is coherent and already part of the boot story.
- Create one only when the repo has enough state artifacts that a lean hub will reduce wake-up cost.
- Keep it concise: mission, current status, non-negotiables, linked state files, starter summary, and one-command orientation when available.

### Task specs

Choose `task_spec_home` in this order:

1. existing task-spec folder
2. `<planning_doc_home>/tasks`
3. create a small task-spec folder only when narrow reusable specs will reduce future rereads

### Reusable tooling

Choose `script_home` in this order:

1. existing `scripts/`
2. existing `tools/`
3. create `scripts/` when no better durable home exists

## Context Tiers

Model repo context as:

- `hot`: wake-up files required on resume
- `warm`: milestone, subsystem, and routing files often needed after boot
- `cold`: archival, foundational, speculative, or historical files

If the repo already has explicit canonical, supplemental or legacy, and foundations or historical buckets, preserve them and map them into hot or warm or cold only as an overlay. If not, infer practical equivalents and label them as inferred.

## Artifact Families

Only create the families the repo and request actually need.

### Planning family

Use when the repo needs architecture or delivery decisions:

- capability map
- tooling survey
- module system
- MVP spec
- milestones
- task specs

### Operating family

Use when the repo needs durable session continuity:

- root `CLAUDE.md`
- control plane
- optional `MEMORY.md` state hub
- docs index
- project state
- system state index
- tool registry
- starters
- task routing

### Improvement family

Use when the repo should learn from its own work:

- improvement ledger
- playbook registry
- active playbook exposure through the control plane
- shared global catalog suggestions

### Governance family

Use when the repo needs active behavioral control:

- decision policy
- operation-pack selection
- skill-routing and delegation
- artifact-health and drift tracking

### Migration or Adapter family

Use when Claude or other foreign-agent artifacts are present:

- migration plan
- compatibility shim
- precedence notes
- adapter status in the control plane

### Hardening family

Use when the repo needs actual initialization work:

- config files
- schema or migrations
- seeds or fixtures
- CI or quality gates
- scripts and shortcuts
- invariants and ADRs

### Maintenance family

Use when the repo already operates but state is stale:

- stale-artifact refresh
- contradiction or drift repair
- routing repair
- boot-path repair
- next-action repair
- memory-hub repair when its links or summary drift from reality
- capability-decision refresh when the next task reopens an unresolved tooling choice
- improvement-ledger or playbook-registry refresh when lessons were learned, promoted, or retired
- artifact lifecycle pruning so dormant or archived surfaces leave the hot path

## Operation Packs

Operation packs are the compositional runtime of the repo OS. Activate only the packs the current request and repo state actually require.

Common packs:

- `bootstrap`
- `resume`
- `repair-drift`
- `capability-discovery`
- `scaffold-foundations`
- `harden`
- `retro-forge`
- `migrate-agent-system`
- `prepare-handoff`

The active pack set belongs in the control plane so later sessions can continue the same operating mode cheaply.

## Skill Routing

The repo operating system should detect available specialist skills and route narrow execution to them when useful, while keeping boot, state, guardrails, and handoff centralized.

Routing rules:

- prefer repo OS for sensing, control-plane updates, state repair, and handoff
- prefer a specialist skill for narrow domain execution only when it is clearly better suited
- fall back to internal handling when no specialist skill is available

## Profile Selection Rule

Load only the selected profile from `.claude/repo-os/references/profiles/`. Do not load every profile pack into context. Record the selected profile and any secondary traits in the control plane so future sessions do not repeat this selection.

## Flexible Classification Rule

If the repo has explicit canonical, supplemental, and foundations buckets, preserve them.

If not:

- infer practical equivalents
- label the inference explicitly
- do not invent a fake taxonomy just to satisfy the template
