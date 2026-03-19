# Monorepo Profile

Use this profile when the repo contains multiple apps, packages, services, or domains with a shared root and workspace tooling.

## Signals

- `apps/`, `packages/`, `services/`, or workspace manifests exist
- multiple deployable or publishable surfaces share one repo
- routing and ownership matter as much as implementation

## Default Planning Artifacts

- tooling survey
- module system with workspace topology
- MVP or release-path spec only for active surfaces
- milestone ledger
- task specs for cross-workspace work

## Milestone Archetypes

- workspace topology and standards
- first end-to-end path across surfaces
- active-surface MVP or release completion
- shared tooling and reliability hardening
- follow-up surface expansion

## Hardening Priorities

- workspace boundaries
- dependency direction
- shared tooling consistency
- selective verification commands
- surface-specific routing

## Verification Defaults

- root lint or typecheck
- targeted workspace tests
- one end-to-end or integration smoke path
- graph or boundary verification when available

## Tooling-Survey Categories

- workspace manager
- build graph or task runner
- shared contracts
- shared UI or component infrastructure
- package boundary enforcement
- release or deployment orchestration
- observability or cross-surface verification

## Task-Spec Threshold

Require a task spec whenever work crosses workspace boundaries, changes shared contracts, alters task-runner behavior, or touches multiple release surfaces.
