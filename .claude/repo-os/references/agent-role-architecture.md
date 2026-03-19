# Agent Role Architecture

Use this reference when the repo operating system needs explicit internal role activation, creator-mode routing, or role handoffs.

## Goal

Convert dense creator output into scoped, sequenced, finished, and resumable artifacts by assigning labor to the roles best suited for what the creator cannot reliably sustain alone.

## Governing Rule

Do not duplicate the creator's generative surplus. Use the agent system for:

- translation under constraint
- ambiguity reduction
- scope freezing
- implementation sequencing
- completion
- continuity
- disciplined skepticism
- audience translation

## Creator Asymmetry

Creator strengths:

- abstraction
- symbolic mapping
- cross-domain linkage
- metaphor as compression
- conceptual generation
- architectural taste

Recurring bottlenecks:

- narrowing
- choosing among viable paths
- freezing definitions at the right level
- converting insight into staged implementation
- maintaining sequence discipline
- finishing
- continuity across sessions

## Primary Role Contracts

Load the role file only when it is active:

- [Interpreter-Architect](.claude/repo-os/references/roles/interpreter-architect.md)
- [Scope Governor](.claude/repo-os/references/roles/scope-governor.md)
- [Implementation Strategist](.claude/repo-os/references/roles/implementation-strategist.md)
- [Finisher-Operator](.claude/repo-os/references/roles/finisher-operator.md)
- [Continuity Steward](.claude/repo-os/references/roles/continuity-steward.md)
- [Critical Counterweight](.claude/repo-os/references/roles/critical-counterweight.md)
- [Interface Translator](.claude/repo-os/references/roles/interface-translator.md)

## Situational Role Overlays

These are overlays, not always-on full role contracts:

- Research Scout -> use through `capability-discovery`
- Systems Modeler -> activate for schema, ontology, protocol, and state-model work
- Prototype Builder -> activate for proof, spike, or reality-test artifacts
- Ritualizer -> use through `retro-forge`, starters, checklists, and repeatable operating rituals

## Creator-Mode Detection

Detect at least:

- `vision burst`
- `milestone shaping`
- `technical translation`
- `identity defense`
- `dense idea drop`

## Default Role Pipelines

- `vision burst` -> Interpreter-Architect -> Critical Counterweight -> Scope Governor
- `milestone shaping` -> Scope Governor -> Implementation Strategist
- `technical translation` -> Interpreter-Architect -> Implementation Strategist -> Finisher-Operator
- `identity defense` -> Critical Counterweight -> Scope Governor -> Interface Translator when audience adaptation is needed
- `dense idea drop` -> Interpreter-Architect -> Critical Counterweight -> Scope Governor -> Implementation Strategist

When an artifact is close to usable completion, bias the next handoff to Finisher-Operator. Before ending major work, bias the final handoff to Continuity Steward.

## Role Interaction Model

Default healthy flow:

1. Interpreter-Architect receives the raw input.
2. Critical Counterweight pressure-tests the interpretation.
3. Scope Governor decides what belongs to the current phase.
4. Implementation Strategist converts the scoped direction into sequence.
5. Finisher-Operator produces the actual artifact.
6. Continuity Steward updates canonical state and handoff.
7. Interface Translator adapts output for audience when needed.

Compress the pipeline only when the task is genuinely smaller, not because the roles are being ignored.

## Recording Rule

Store the active collaboration state in `collaboration_architecture` inside the control plane:

- creator strengths
- recurring bottlenecks
- current creator mode
- active roles
- role pipeline
- pending handoffs
- active build layer
- preserved future layer
- role-routing notes

Task specs for non-trivial work should also record:

- primary role
- supporting roles
- preserved future consequences
- handoff chain

## Failure Modes To Avoid

- role collapse into one generic poetic strategist
- endless interpretation without sequencing
- sequencing without real closure
- continuity becoming a passive archive instead of an active coherence maintainer
- audience adaptation that sandpapers away the architecture
