# Module System Template

Use this template for the module-system artifact in the resolved planning-doc location.

## Architecture Choice

- Chosen structure: `<monorepo | multi-repo | single package with internal modules | service + shared packages | library + examples>`
- Why this structure fits the product:
- Why alternatives were rejected:
- Brownfield migration notes, if any:

## Module Map

| Module | Responsibility | Owns Data or State | Public API | Depends On |
| --- | --- | --- | --- | --- |
| `core` |  |  |  |  |
| `domain/*` |  |  |  |  |
| `infra/*` |  |  |  |  |
| `apps/*` |  |  |  |  |

Replace the placeholder rows with the repo's actual shape.

## Dependency Rules

- State allowed dependency directions explicitly.
- Disallow circular dependencies.
- Define which modules may expose public contracts and which may only consume them.
- Add lint, graph, or review checks that enforce these boundaries when practical.

## Interface and Contract Strategy

- Contract format: `<TypeScript types | OpenAPI | GraphQL schema | events | language-native interfaces>`
- Backward compatibility policy:
- Versioning policy:
- Deprecation policy:

## Data and Persistence Boundaries

- Source of truth:
- Write paths:
- Read models:
- Migration strategy:

## Error, Logging, and Observability

- Error contract standard:
- Logging standard:
- Metrics or trace strategy:
- Alert thresholds for MVP:

## Testing Strategy by Layer

- Unit:
- Contract:
- Integration:
- End-to-end:
- Performance or security smoke:

## Initial Package Layout

```text
apps/
packages/
docs/
```

Replace with the selected module tree before scaffold hardening.

## Quality Gates

- `lint`
- `typecheck`
- `test`
- `build`
- optional: `e2e`, `perf`, `a11y`, `contract`

Define exact commands and owners per gate.
