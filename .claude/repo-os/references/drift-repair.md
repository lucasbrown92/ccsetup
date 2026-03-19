# Drift Repair

Use this reference when the repo's documented state may no longer match reality.

## Goal

Detect contradictions early, repair only the affected surfaces, and avoid building on stale assumptions.

## Contradiction Sources

Compare these sources of truth:

- root `CLAUDE.md`
- control plane
- `project-state.md`
- `SYSTEM_STATE_INDEX.md`
- docs index or task-routing artifacts
- manifests, configs, schemas, tests, and current code

## Artifact Health States

Use these states in the control plane and optional drift artifacts:

- `healthy`
- `stale`
- `missing`
- `conflicting`
- `archived`

Lifecycle states remain separate:

- `required`
- `active`
- `dormant`
- `stale`
- `archived`

## Detection Rules

- Favor executable truth when prose and code disagree.
- Treat failed sanity checks as drift signals until proven otherwise.
- Treat missing boot-path files as control-plane drift, not just missing docs.
- If the current directory is an umbrella folder, verify workspace boundaries before touching repo-local state.

## Repair Flow

1. inventory conflicting surfaces
2. choose the smallest trustworthy source of truth
3. update only the affected artifacts
4. mark artifact-health states explicitly
5. refresh the boot path if needed
6. leave one next action if full repair is out of scope

## Optional Artifacts

Create only when they reduce future confusion:

- `surface-map.yaml` for large or structurally complex repos
- `artifact-health.md` for human-readable drift and freshness status

Keep both lean and operational.
