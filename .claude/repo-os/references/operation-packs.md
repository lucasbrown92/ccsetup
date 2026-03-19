# Operation Packs

Use this reference when selecting the active workflow the repo operating system should run.

## Goal

Break the repo OS into composable operating packs so it can activate only the behavior the current repo state and request actually need.

## Selection Rules

- Activate the smallest pack set that satisfies the request.
- Keep sensing, control-plane updates, guardrails, and handoff under repo OS control even when a specialist pack or skill is active.
- Record the active pack set in the control plane.
- Retire a pack from the active set once its exit condition is met.

## Common Packs

### `bootstrap`

Use when the repo lacks core planning or operating artifacts.

- Inputs: repo fingerprint, layout strategy, selected profile
- Outputs: first-pass ledgers, control plane, routing, starter flow

### `resume`

Use when the repo already operates and the next task is to continue safely.

- Inputs: ledgers, control plane, hot boot path
- Outputs: reconstructed state, next action, refreshed stale artifacts

### `repair-drift`

Use when docs, state artifacts, and repo signals disagree.

- Inputs: control plane, project-state, system-state, code or config or test signals
- Outputs: drift findings, repaired state artifacts, updated artifact-health states

### `capability-discovery`

Use when the next task may be better served by an existing tool, library, service, or platform component.

- Inputs: repo surface, current task, unresolved capability classes
- Outputs: tool recommendation, open questions, decision artifact updates

### `scaffold-foundations`

Use when the repo needs minimum viable config, schema, scripts, seeds, or quality-gate entry points.

- Inputs: approved planning artifacts and current milestone
- Outputs: thin scaffold tied to immediate milestone needs

### `harden`

Use after planning gates are approved or explicitly waived.

- Inputs: approved planning artifacts, verification defaults, current scaffold
- Outputs: stronger boundaries, scripts, config, and verification

### `retro-forge`

Use when friction, failures, wins, or repeated workarounds should become durable upgrades.

- Inputs: improvement ledger, playbook registry, verification outcomes
- Outputs: promoted tools, playbooks, or routing improvements

### `migrate-agent-system`

Use when Claude or another foreign-agent system must be converted, merged, or overlaid.

- Inputs: detected foreign-agent artifacts, approved migration mode
- Outputs: migration doc, compatibility shim, adapter state

### `prepare-handoff`

Use before ending major work or when the next session must resume cheaply.

- Inputs: current state, changed surfaces, active packs
- Outputs: refreshed ledgers, control plane, next action, cheap boot path

## Role and Overlay Mapping

Default internal role ownership:

- `bootstrap` -> Implementation Strategist + Finisher-Operator + Continuity Steward
- `resume` -> Continuity Steward + the role chain implied by current creator mode
- `repair-drift` -> Critical Counterweight + Continuity Steward
- `capability-discovery` -> Research Scout overlay plus Interpreter-Architect when translation is needed
- `scaffold-foundations` -> Implementation Strategist + Finisher-Operator
- `harden` -> Scope Governor + Implementation Strategist + Finisher-Operator
- `retro-forge` -> Ritualizer overlay + Continuity Steward
- `migrate-agent-system` -> Interface Translator + Continuity Steward
- `prepare-handoff` -> Finisher-Operator + Continuity Steward

Situational overlays:

- Research Scout -> live ecosystem and best-practice discovery
- Systems Modeler -> schema, ontology, protocol, and state-model work
- Prototype Builder -> fast proof or spike artifacts
- Ritualizer -> repeated workflow capture into starters, checklists, playbooks, or rituals

## Composition Rules

- `resume` may activate `repair-drift`, `capability-discovery`, or `retro-forge`.
- `bootstrap` often activates `capability-discovery`, `scaffold-foundations`, and `prepare-handoff`.
- `repair-drift` should block broad implementation when contradictions are material.
- `harden` should not activate until planning gates are approved or explicitly waived.
- `retro-forge` may run after any pack that revealed reusable learning.

## Exit Rule

Leave one explicit next action and an updated active-pack set in the control plane before ending the task.
