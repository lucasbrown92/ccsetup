# Validation Scenario Matrix

Use this reference to mentally dry-run the skill or review whether the operating model chosen for a repo is coherent.

## Acceptance Rule

The skill should choose the right profile, artifact locations, active families, and boot path without forcing irrelevant files.

## Scenario 1: Greenfield App With No Docs

- Expected profile: `app`
- Expected locations:
  - `planning_doc_home`: `docs`
  - `state_doc_home`: `memory`
  - `task_spec_home`: `docs/tasks`
  - `script_home`: `scripts`
- Expected families: planning, operating, hardening
- Expected boot path: root `CLAUDE.md`, control plane, project-state, system-state, starters
- Expected interop: inactive
- Expected taxonomy: inferred hot or warm or cold

## Scenario 2: Brownfield Library With Root Docs

- Expected profile: `library`
- Expected locations:
  - planning docs remain at root when that is coherent
  - `state_doc_home` reuses `memory/` if present, otherwise creates it
  - task specs live in a minimal root-adjacent or planning-doc path
- Expected families: operating, targeted planning, maintenance
- Expected boot path: root ledger plus smallest current state files and release-path docs
- Expected interop: inactive unless foreign-agent files exist
- Expected taxonomy: inferred unless the repo already defines explicit buckets

## Scenario 3: Monorepo With `plans/`

- Expected profile: `monorepo`
- Expected locations:
  - `planning_doc_home`: `plans`
  - `state_doc_home`: reuse existing ops folder or create `memory`
  - `task_spec_home`: `plans/tasks` or existing task-spec home
  - `script_home`: reuse `scripts` or `tools`
- Expected families: planning, operating, maintenance, optional migration
- Expected boot path: root ledger, control plane, project-state, routing, active-surface milestone docs
- Expected interop: inactive unless foreign-agent files exist
- Expected taxonomy: inferred hot or warm or cold unless explicit

## Scenario 4: Sparse Infra Repo

- Expected profile: `infra`
- Expected locations:
  - planning docs may stay minimal or root-based
  - `state_doc_home`: `memory`
  - `script_home`: existing `tools` or `scripts`
- Expected families: operating, hardening, targeted planning
- Expected boot path: root ledger, control plane, system-state, fragility routing, env or plan verification docs
- Expected interop: inactive
- Expected taxonomy: inferred

## Scenario 5: Mixed-Agent Claude Repo

- Expected profile: chosen from actual repo kind, not automatically `mixed`
- Expected locations: preserve coherent existing planning and state layout
- Expected families: operating, migration, maintenance, plus relevant profile families
- Expected boot path: root ledger, control plane, shared state files, optional `CLAUDE.md` overlay after shared files
- Expected interop: Claude adapter active
- Expected taxonomy: preserve explicit canonical or supplemental or foundations buckets when present

## Scenario 6: Already-Initialized Repo With Stale State

- Expected profile: preserve existing selected profile unless repo shape materially changed
- Expected locations: reuse existing homes
- Expected families: maintenance plus any affected family only
- Expected boot path: preserved and refreshed, not reinvented
- Expected interop: unchanged unless foreign-agent story changed
- Expected taxonomy: preserved if explicit, inferred otherwise

## Scenario 7: Repeated Workaround During Normal Development

- Expected families: improvement plus maintenance
- Expected result: repeated workaround enters `improvement-ledger.md`
- Expected promotion: if validated, becomes a tool or playbook in the correct target artifact
- Expected control-plane effect: `open_candidates` or `active_playbooks` updated

## Scenario 8: Failed Verification at Milestone Handoff

- Expected families: improvement, maintenance
- Expected result: mandatory retrospective runs
- Expected promotion: recovery procedure becomes a playbook when multi-step
- Expected handoff: next session sees the playbook and the failure lesson without rereading old logs

## Scenario 9: Portable Local Pattern Reused Across Repos

- Expected local result: validated local pattern passes portability review
- Expected shared result: pattern enters the global catalog as `provisional`
- Expected future repo behavior: matching repo sees it as a suggestion; only `validated` entries may shape defaults automatically

## Scenario 10: Docs and Code Disagree on Resume

- Expected active pack: `repair-drift`
- Expected result: contradictions are surfaced before implementation
- Expected artifact effect: artifact-health states and drift signals update
- Expected boot behavior: stale artifacts are repaired or deprioritized before normal resume continues

## Scenario 11: Umbrella Folder With Multiple Child Repos

- Expected result: workspace boundaries are detected early
- Expected control-plane effect: reality model records true repo root and child repos
- Expected safety effect: repo OS does not treat the umbrella folder as one writable target

## Scenario 12: Medium-Risk Capability Choice

- Expected result: decision policy asks targeted questions when repo signals are insufficient
- Expected safety effect: no silent auto-commit on unresolved architecture or tooling tradeoffs
- Expected artifact effect: decision policy and open questions remain synchronized

## Scenario 13: Specialist Skill Available for a Narrow Task

- Expected result: repo OS keeps boot, state, guardrails, and handoff centralized
- Expected routing effect: control plane records the delegated task class and fallback behavior
- Expected fallback: internal handling continues if the specialist skill is unavailable or unsuitable

## Scenario 14: Dormant and Archived Surfaces Accumulate Over Time

- Expected result: dormant or archived artifacts leave the hot boot path
- Expected control-plane effect: artifact lifecycle states are current
- Expected handoff: next session reads only required or active surfaces unless the task explicitly touches dormant areas

## Scenario 15: Dense Idea Drop From the Creator

- Expected creator mode: `dense idea drop`
- Expected active roles: Interpreter-Architect -> Critical Counterweight -> Scope Governor -> Implementation Strategist
- Expected result: structural translation, scoped immediate action, preserved later-phase consequences
- Expected failure avoidance: no shallow paraphrase and no immediate scope bloom

## Scenario 16: Scope Bloom During Implementation

- Expected active roles: Scope Governor stays active and Finisher-Operator does not reopen future architecture
- Expected result: non-current ideas move to preserved future layer or backlog instead of entering the current milestone
- Expected control-plane effect: role pipeline and future-layer notes update

## Scenario 17: Artifact Near Completion But Not Finished

- Expected active roles: Finisher-Operator becomes the next handoff owner
- Expected result: artifact emerges actually usable, not left as a suggestive outline
- Expected control-plane effect: pending handoff points to finish, then continuity

## Scenario 18: Resume After Context Loss

- Expected active roles: Continuity Steward reconstructs current truth, frozen decisions, next action, and contradiction status
- Expected result: resume boot stays cheap and trustworthy
- Expected handoff: next role chain is explicit instead of rediscovered ad hoc

## Scenario 19: Audience Adaptation Needed

- Expected active roles: Interface Translator joins only when output must change register or audience
- Expected result: audience-facing output changes without architecture loss
- Expected safety effect: no corporate-mush rewrite of the underlying idea

## Scenario 20: Repeated Process Pain Should Become Ritual

- Expected overlay: Ritualizer through `retro-forge`
- Expected result: repeated friction becomes a checklist, starter, or playbook
- Expected handoff: next session sees the ritual instead of rediscovering the pain

## Review Questions

- Did the control plane and human-readable state agree on profile, boot path, next action, and adapter mode?
- Did the improvement ledger, playbook registry, control plane, and `CLAUDE.md` agree on open candidates, active playbooks, and improvement mode?
- Did the control plane and human-readable state agree on drift status, active packs, and decision policy?
- Did the skill preserve an existing coherent layout instead of forcing `docs/` or `memory/` unnecessarily?
- Did it avoid activating migration work when no foreign-agent artifacts existed?
- Did it activate `repair-drift` before broad implementation when contradictions were open?
- Did it detect workspace boundaries correctly and avoid broad edits at the wrong level?
- Did it route only the right task classes to specialist skills while keeping repo OS control centralized?
- Did active roles, creator mode, and pending handoffs stay synchronized across the control plane, human-readable state, and task specs?
- Did dense creator input route through interpretation and scoping before implementation?
- Did near-complete artifacts get finished rather than left suggestive?
- Did it keep the boot path small and task-oriented?
