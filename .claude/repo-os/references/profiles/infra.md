# Infra Profile

Use this profile when the repo primarily manages environments, infrastructure, deployment systems, internal platforms, or service operations.

## Signals

- IaC, deployment, or operational workflows dominate
- environment safety and migration safety are first-class
- the repo may have little traditional product UI or package surface

## Default Planning Artifacts

- tooling survey when stack choices are still open
- module system or topology doc
- milestone ledger
- task specs for risky migrations or environment changes

## Milestone Archetypes

- environment and topology decisions
- first environment bring-up
- baseline automation and safety proof
- migration or reliability hardening
- operating maturity follow-up

## Hardening Priorities

- secrets and config boundaries
- environment bootstrap
- rollback paths
- observability and alerting
- policy or access boundaries

## Verification Defaults

- format or lint
- validate or plan command
- environment smoke test
- deployment dry run or equivalent
- rollback proof when applicable

## Tooling-Survey Categories

- IaC framework
- CI or deployment system
- secrets management
- containerization or local dev environment
- observability and alerting
- background jobs or orchestration
- policy or access tooling

## Task-Spec Threshold

Require a task spec for any change touching production-like environments, migrations, network boundaries, auth policy, or rollback-sensitive automation.
