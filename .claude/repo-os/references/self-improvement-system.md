# Self-Improvement System

Use this reference when the repo should learn from its own work and make future agent sessions faster, safer, and more capable.

## Goal

Turn friction, failures, wins, repeated workarounds, and verified speedups into durable operational upgrades. The self-improvement layer is agent-first: it improves the repo operating system before it tries to improve the app itself.

## Forge Loop

The self-improvement system runs this loop:

1. `observe`
2. `classify`
3. `validate`
4. `promote`
5. `expose`
6. `reuse`
7. `retire`

### Observe

Capture a candidate whenever any of these occur:

- failed verification
- repeated workaround
- slow wake-up or repeated reread
- manual recovery step
- capability-discovery decision
- verified speedup
- handoff pain or confusion

### Classify

Assign one improvement object type:

- `tool`
- `checklist`
- `routing optimization`
- `starter upgrade`
- `playbook`
- `capability decision`
- `guardrail`
- `architecture pattern`

### Validate

Attach the smallest evidence needed to justify promotion:

- number of times observed
- exact time or token savings when known
- verification step proving it works
- scope of applicability
- known contraindications

### Promote

Use fixed promotion targets:

| Type | Promotion target |
| --- | --- |
| `tool` | `script_home` plus `tool-registry.md` |
| `checklist` | `playbook-registry.md` |
| `routing optimization` | docs index or task-routing plus `playbook-registry.md` |
| `starter upgrade` | starters plus `MEMORY.md` |
| `playbook` | `playbook-registry.md` |
| `capability decision` | tooling survey or capability map |
| `guardrail` | invariants or `CLAUDE.md` |
| `architecture pattern` | ADR or module-system doc |

Keep anything unpromoted in `improvement-ledger.md`.

### Compile

Do not stop at promotion. Compile repeated learnings into the right durable layer:

- command -> `tool-registry.md`
- multi-step heuristic or recovery flow -> `playbook-registry.md`
- routing shortcut -> docs index or task-routing artifacts
- durable cross-repo pattern -> shared global catalog
- repeated domain workflow -> candidate operation pack or specialist-skill route

### Expose

After promotion:

- update the control plane
- update the relevant repo artifact
- add any active playbooks to the improvement system state
- make sure the next `resume` will see the result

### Reuse

On bootstrap and resume:

- consult local active playbooks first
- consult the shared global catalog second
- apply only relevant patterns filtered by repo profile, capability class, and trigger

### Retire

Retire patterns when:

- the repo architecture changed enough that the pattern no longer fits
- the pattern no longer produces measurable benefit
- a better local or global pattern supersedes it
- the pattern was provisional and failed validation

## Improvement Metrics

Track whether the system is actually getting smarter:

- reuse count
- verification success rate
- estimated time saved
- failures avoided
- stale upgrades
- net-negative patterns under review

Promotion should prefer evidence over intuition. Retirement should be first-class when a pattern stops paying for itself.

## Local Promotion Rules

- wake-up or verification improvements may auto-promote after one successful validation
- all other local improvements require either two observed uses or one successful use plus a clear repeatable benefit
- architecture, public API, product behavior, security, compliance, and external-service changes still require human confirmation

## Global Promotion Rules

Shared global catalog path:

- `~/.claude/memory/repo-operating-system/global-pattern-catalog.md`

Promotion rules:

- only portable patterns may be synced there
- a pattern must pass local validation first
- run a portability pass that strips repo-specific assumptions, secrets, paths, and names
- new entries start as `provisional`
- only `validated` entries may influence defaults automatically in future repos

## Mandatory Retrospective Triggers

Run a retrospective:

- after failed verification
- after repeated workaround detection
- at milestone handoff
- after a capability-discovery decision

Always ask:

- what slowed us down
- what saved us time
- what should become part of the suit
- what should never be repeated

## Artifact Responsibilities

- `tool-registry.md`: commands, scripts, and pipelines only
- `playbook-registry.md`: multi-step procedures, recovery flows, and heuristics
- `improvement-ledger.md`: raw candidates, evidence, status, and next validation step
- global catalog: portable cross-project patterns only
- control plane: active playbooks, metrics, candidate operation packs, and skill-routing consequences

## Global Catalog Usage

Use the shared catalog in suggestion mode:

- filter by repo profile
- filter by active capability class
- filter by current trigger such as wake-up, verification failure, handoff, or capability decision
- `validated` entries may shape defaults automatically
- `provisional` entries may only appear as candidates in the local improvement ledger or capability map

## Approval Boundaries

Do not auto-promote across these boundaries without human confirmation:

- architecture shifts
- public API changes
- product-facing behavior changes
- security, privacy, or compliance changes
- new external-service dependencies
- changes that would rewrite existing repo conventions instead of extending them
