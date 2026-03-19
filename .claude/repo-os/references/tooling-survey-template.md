# Tooling Survey Template

Use this template for the tooling survey in the resolved planning-doc location. Treat it as a living build-vs-buy decision document, not a one-time greenfield artifact.

## Scan Scope

- Why this scan is running:
- Current repo phase:
- Current task or surface:
- Selected repo profile:
- Whether this is initial stack selection or an incremental capability scan:

## Architecture and Constraint Snapshot

- App or repo type:
- Existing runtime and framework:
- Deployment environment:
- Data and integration surfaces:
- Team size or skill profile:
- Compliance, privacy, or security constraints:
- Budget or licensing constraints:
- Managed vs self-hosted preference:
- Existing stack constraints:

## Capability Classes In Scope

List only the capability classes relevant to the repo or active task.

Examples:

- runtime, framework, compiler, bundler, parser
- validation, contracts, schemas
- auth or identity
- forms, routing, state, UI primitives, design system
- accessibility, i18n, CMS or content workflows
- database, cache, queue, search, realtime
- files or media
- analytics, observability, feature flags
- payments, notifications, admin tooling
- deployment, secrets, local dev environment
- testing, linting, formatting, docs tooling

## Existing Coverage Audit

| Capability Class | Current repo solution | Gaps or pain points | Keep, replace, extend, or research |
| --- | --- | --- | --- |
|  |  |  |  |

## Evaluation Criteria

Use consistent scoring (`1-5`) for:

- fit to requirements
- maturity and maintenance health
- ecosystem and docs quality
- compatibility with the current stack
- operational complexity
- migration or lock-in risk
- cost and licensing risk

## Candidate Research

For each relevant capability class, research current options using primary sources.

| Capability Class | Candidate | Source links | Fit | Maturity | Compatibility | Complexity | Lock-In | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |

## Common Capability Prompts

Use only the sections that matter.

### Validation and Contracts

Candidate examples:

- `zod`
- `valibot`
- `io-ts`
- framework-native schema tools

### UI Primitives and Design System

Candidate examples:

- `shadcn/ui`
- Radix primitives
- framework-native component systems
- headless component libraries

### Accessibility

Candidate examples:

- `axe-core`
- `eslint-plugin-jsx-a11y`
- `jest-axe`
- framework-native a11y tooling

### Internationalization and Content

Candidate examples:

- `i18next`
- `lingui`
- framework-native i18n
- CMS or content platforms when editing workflows matter

### Data, Cache, Queue, Search

Candidate examples:

- relational or document stores
- hosted vs local databases
- Redis or framework-native caches
- queueing or job tools
- search backends

### Cross-Cutting Capabilities

Examples:

- auth or identity
- observability
- analytics
- feature flags
- workflow engine
- realtime
- admin tooling
- payments
- notifications
- media pipeline

## Build vs Buy Decisions

| Capability | Chosen Approach | Why | Open questions | Revisit Trigger |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## User Decision Questions

Ask only the questions that materially affect the choice.

1. Are there banned vendors, licenses, or hosting models?
2. Is managed infrastructure acceptable for this capability?
3. Is faster delivery more important than deeper long-term control here?
4. Are there compliance, privacy, or data residency constraints?
5. Is there existing team familiarity or organization-standard tooling to prefer?
6. Which choices are reversible later and which create deep lock-in?

## Recommended Stack

- Primary recommendation:
- Secondary fallback:
- Deferred option:
- Known risks:
- Migration plan if assumptions fail:

## Approval Status

- Confirmed choices:
- Deferred choices:
- Rejected choices:
- Open capability questions:
- Waived by user:

## Research Notes

Document how candidates were validated:

- official docs reviewed
- package registry or official package index checked
- release cadence or changelog checked
- integration complexity in this architecture
- known operational pitfalls

Add links and evidence where possible.
