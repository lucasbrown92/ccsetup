# App Profile

Use this profile when the repo primarily delivers a deployable user-facing product or service.

## Signals

- web, mobile, desktop, or API runtime is the main output
- product flows matter more than package publishing
- deployment and user-facing quality gates are first-class

## Default Planning Artifacts

- tooling survey
- module system
- MVP spec
- milestone ledger
- task specs for non-trivial slices

## Milestone Archetypes

- foundations and decisions
- first proved user flow
- MVP completion
- hardening and release readiness
- post-MVP follow-up

## Hardening Priorities

- runtime config and env examples
- auth and secret boundaries
- schema or migrations if data-backed
- CI gates
- observability basics

## Verification Defaults

- lint
- typecheck
- unit tests
- build smoke test
- one user-flow or API smoke path

## Tooling-Survey Categories

- app framework or runtime
- compiler or bundler layer
- validation and contracts
- UI primitives or design system
- forms, routing, and state
- auth or identity
- accessibility
- i18n or content workflows
- persistence or cache
- queueing, jobs, search, or realtime
- observability
- analytics or feature flags
- browser, native, or UI verification

## Task-Spec Threshold

Require a task spec when work crosses multiple modules, adds a new user flow, changes data boundaries, or touches release-critical infrastructure.
