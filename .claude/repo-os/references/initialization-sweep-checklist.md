# Initialization Sweep Checklist

Use this checklist before declaring a repo fully initialized. Create only what the current repo type and milestone actually require.

## Core Repo Surfaces

- root commands for run, build, test, lint, typecheck
- env example files and secret-handling pattern
- package manager lockfile and install path
- CI or local quality-gate entry points

## Data and Persistence

If the repo has a data layer, check:

- schema definitions
- migrations
- seeds or fixtures
- local dev bootstrap path
- rollback or reset strategy

## Application and Platform Config

Check for missing but required:

- base config files
- runtime config
- local developer config
- deployment or release config
- observability or logging defaults

## Scripts and Shortcuts

- Turn repeatable setup or diagnosis steps into scripts when worthwhile.
- Put scripts in an obvious repo location.
- Log every new script or shortcut in the resolved tool registry immediately.

## Docs and State Preservation

Before finishing, confirm:

- root `CLAUDE.md`
- `<state_doc_home>/repo-operating-profile.yaml`
- ADR and invariants in the resolved durable doc or state location
- docs index in the resolved state location
- project-state in the resolved state location
- system-state in the resolved state location
- improvement-ledger and playbook-registry in the resolved state location when the self-improvement layer is active
- starters in the resolved planning location
- task-routing in the resolved planning location

## Code-Level Breadcrumbs

When bootstrap creates foundational utilities, edge-case-heavy logic, or non-obvious core configs:

- add focused comments or docstrings for data flow
- explain failure modes and edge cases
- avoid generic comments that restate the obvious

## Final Wake-Up Check

- record one sanity-check command
- record the current milestone and next action
- record fragility points and rejected paths
- confirm the boot path is sufficient for a fresh session
- confirm the control plane and human-readable state agree
- confirm open improvement candidates and active playbooks are exposed correctly if present
