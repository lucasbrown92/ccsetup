# Capability Discovery

Use this reference whenever the repo or current task may be better served by adopting an existing tool, library, service, or platform component instead of building it from scratch.

## Goal

Continuously detect build-vs-buy opportunities from repo shape, docs, code, and task context. This is not a one-time greenfield survey. It should be available during `resume`, `plan`, `build`, `implement`, `review`, `sync`, and explicit research prompts.

## Triggers

Run capability discovery when any of these are true:

- the next task touches a commodity capability
- the repo lacks an obvious solution for a common cross-cutting concern
- custom implementation would recreate a mature ecosystem tool
- the repo is selecting or reconsidering core stack pieces
- the user explicitly asks to research tools, libraries, services, or existing solutions
- the current implementation looks brittle because a mature maintained option likely exists

## First Principle

Do not blindly install libraries. Do not blindly reinvent them either.

Infer the repo's actual needs first, inspect what already exists second, research live options third, ask targeted clarification questions fourth, and only then recommend adoption, deferment, or custom build.

## Capability Classes To Consider

Check only the classes relevant to the repo and task, but think broadly enough to avoid tunnel vision:

- runtime, framework, compiler, transpiler, bundler, parser
- schema, validation, contracts, API typing
- auth, identity, RBAC, session management
- routing, forms, state management, UI primitives, component systems, design tokens
- accessibility, i18n, localization workflows
- CMS, content editing, markdown or MDX, docs sites
- database, ORM, query builders, migrations, search, cache
- queueing, jobs, workflow engines, schedulers
- realtime, events, streams, WebSocket infrastructure
- files, blob storage, media processing
- analytics, observability, feature flags, error tracking
- payments, notifications, email, messaging
- admin tooling, internal ops, release tooling
- infra, deployment, secrets, containerization, local dev environments
- testing, linting, formatting, type safety, quality gates

## Workflow

### 1. Infer What the Repo Actually Needs

- Read the minimum docs and code needed to understand the active surface.
- Inspect manifests, lockfiles, CI, deploy configs, environment files, routing, schemas, tests, and UI or data flows.
- Determine which capability classes are present, missing, partially solved, or likely to emerge next.

### 2. Audit Existing Coverage

- Check whether the repo already has a tool or library covering the capability.
- Check whether the platform or framework already provides a native solution.
- Check whether a shared service or infra layer already exists elsewhere in the repo or organization.
- Avoid recommending a second overlapping abstraction unless the current one is clearly insufficient.

### 3. Research Live Options

- Use web search for current recommendations and compatibility-sensitive choices.
- Prefer primary sources:
  - official docs
  - official package registries such as npm, PyPI, crates.io, RubyGems, Maven Central, or equivalent
  - maintainer docs and release notes
  - official vendor pages when managed services are in play
- Use tertiary sources only to generate candidate names, then validate them against primary sources.

### 4. Evaluate Candidates

For each serious candidate, evaluate:

- fit to the repo's capability need
- runtime or framework compatibility
- maturity and maintenance activity
- docs and ecosystem quality
- operational complexity
- migration cost
- lock-in and exit path
- licensing and commercial constraints
- self-hosted versus managed tradeoffs
- accessibility, i18n, performance, compliance, or platform constraints when relevant

### 5. Ask Targeted Clarification Questions

Ask questions when the repo cannot reveal the answer. Focus on the smallest set of questions that unlock the decision.

Follow the repo's current decision policy:

- act when the repo and current constraints make the choice clear
- ask when the choice is medium-risk and the repo cannot reveal key tradeoffs
- require confirmation when the choice creates destructive, security, compliance, lock-in, or externally visible consequences

Common question types:

- Is managed infrastructure acceptable, or must this remain self-hosted?
- Are there banned vendors, licenses, or hosting models?
- Is faster delivery more important than long-term control?
- Are there compliance, privacy, or data residency constraints?
- Is there existing team familiarity that should bias the choice?
- Is multi-tenant scale, offline mode, accessibility, localization, or white-labeling required?
- Is the choice reversible later, or does it create deep lock-in?

### 6. Decide and Record

- Prefer adoption when the capability is commodity and mature options fit the constraints.
- Prefer custom build when the capability is strategic, tightly domain-specific, or the ecosystem options create more risk than they remove.
- Prefer deferment when the capability is plausible but not justified within the current milestone horizon.
- Record the decision, alternatives, sources, open questions, and revisit trigger in the tooling survey or capability map.
- If the research process itself reveals a reusable evaluation shortcut, question set, or decision heuristic, emit an improvement candidate into `improvement-ledger.md`.
- If the heuristic becomes stable and multi-step, promote it into `playbook-registry.md`.

## Output Artifacts

Use or update:

- `<planning_doc_home>/tooling-survey.md` for major stack and category decisions
- `<planning_doc_home>/capability-map.md` for ongoing capability discovery and unresolved opportunities
- `<state_doc_home>/repo-operating-profile.yaml` for capability-discovery status and open questions
- `<state_doc_home>/improvement-ledger.md` when the research process teaches the repo a reusable heuristic
- `CLAUDE.md` only for the current next action or blocking unresolved tool choice

## Anti-Patterns

- building an auth system, queue, CMS, design system, parser, or validation layer from scratch without first checking whether the problem is already solved well enough
- installing a library just because it is popular without checking fit and operational cost
- recommending stale or abandoned packages from memory alone
- using blog-roundup recommendations without validating them on primary sources
- hiding critical unresolved tool choices inside implementation work instead of surfacing them early
