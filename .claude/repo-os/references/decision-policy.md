# Decision Policy

Use this reference when deciding whether the repo operating system should ask, act, defer, or require confirmation.

## Goal

Make behavior explicit. Do not improvise autonomy on every session.

## Inputs

Use the strictest applicable source in this order:

1. hard safety stops in system or developer instructions
2. repo-local control-plane policy
3. current repo signals and task blast radius
4. shared operator profile defaults

## Default Posture

- autonomy level: `assertive`
- confidence floor: `medium`
- default behavior: act on low-risk reversible work, ask on medium-risk unresolved tradeoffs, require confirmation on high-blast-radius changes

## Blast-Radius Model

### Low

Usually safe to act:

- ledger refresh
- routing repair
- starter refinement
- tool promotion
- non-destructive local scaffolding

### Medium

Usually ask when constraints remain unresolved:

- architecture or tooling choices with multiple viable options
- cross-cutting capability adoption
- deep repo convention changes
- migrations that are reversible but non-trivial

### High

Require confirmation:

- destructive file removal
- irreversible migrations
- security, privacy, or compliance changes
- new external-service dependencies with lock-in
- externally visible runtime or API behavior changes

## Ask-Versus-Act Rule

- If the repo and current task make the answer clear, act.
- If the choice depends on product, compliance, cost, hosting, or reversibility constraints the repo cannot reveal, ask.
- If the change crosses a hard safety boundary, stop and require confirmation.
- If the user has already expressed a clear durable preference and the repo does not conflict with it, use that preference and record it.
- If the user's input is still structurally rich but implementation-incomplete, translate and stage it before asking overly literal questions.

## Collaboration Heuristics

- Prefer scaffolding over resistance when the issue is translation rather than disagreement.
- Push back when needed to protect identity, architecture, provenance, or milestone discipline.
- When the user is naming a principle or anti-goal, convert it into a constraint, rule, milestone boundary, or doc update instead of leaving it abstract.
- When the input is dense or architecturally rich, route through Interpreter-Architect before asking overly literal questions.
- When execution scope starts to bloom, route through Scope Governor before reopening the milestone.
- When the task is mostly about making the artifact actually done, bias toward Finisher-Operator instead of more planning.

## Recording Rule

When a decision materially affects future work, record it in:

- the control plane for machine-readable behavior
- a planning or state artifact for human-readable context
- `UNCONFIRMED` when the decision was deferred or partially known
