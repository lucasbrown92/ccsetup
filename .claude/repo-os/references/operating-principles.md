# Operating Principles

Use this as the default operating philosophy while applying the skill.

## Working Model

- Treat the agent as a task-completion system, not autocomplete.
- Define the task and acceptance criteria before broad edits.
- Separate exploration, planning, implementation, and verification.
- Prefer durable repo artifacts over repeated prompting.

## Planning-First Discipline

- Capture product intent and constraints before hardening scaffold.
- Survey existing ecosystem tools before proposing custom modules.
- Define module boundaries and contracts before generating broad file structures.
- Define MVP scope and milestone exits before implementation-heavy work.
- Treat non-trivial scaffold hardening as gated work that normally needs approval.

## Collaboration Discipline

- When the user thinks structurally, respond structurally before dropping to code detail.
- Treat metaphor as possible architecture and translate it into boundaries, constraints, or subsystem behavior.
- Extract signal from dense high-context input instead of flattening it into a shallow summary.
- Prefer directness, fidelity, and useful translation over hype or filler.
- Optimize early product and workflow decisions for genuine creator usefulness before generic market drift.
- Apply delta labor: do not duplicate the creator's generative surplus; absorb the narrowing, sequencing, finishing, continuity, and operational follow-through the creator is least likely to sustain alone.

## Role-Architecture Discipline

- Treat internal collaboration roles as functionally distinct, not as one generic assistant with shifting vibes.
- Prefer the minimum active role chain that preserves interpretation quality, scope discipline, execution sequence, closure, continuity, and audience fidelity.
- Do not let every role collapse into poetic strategy or endless architecture talk.
- When the user's current mode is clear, activate the matching role pipeline explicitly and record it in state.
- Reserve external specialist skills for narrow domain execution; keep creator-aligned role work inside the repo operating system.

## Translation Discipline

- Use the ladder `whole -> subsystem -> mechanism -> detail` when explaining or planning.
- Produce multiple renderings of the same idea when useful: conceptual, technical, implementation, and milestone or task versions.
- For dense idea drops, separate core thesis, architectural consequences, doc updates, immediate implementation consequences, later-phase consequences, and next action.

## Ambiguity Discipline

- Preserve ambiguity while the idea is still forming.
- Name which parts are settled, exploratory, or blocked on implementation.
- Force crispness only at the point where implementation or verification actually requires a cut.

## State Discipline

- Keep root `CLAUDE.md` terse and operational.
- Store richer state in resolved state and planning artifacts, not in chat history.
- Record only non-inferable details, constraints, arbitrary human decisions, and current operational state.
- Keep the boot path small, usually three to seven files.
- Maintain both human-readable state and a machine-readable control plane.
- The control plane and the human-readable state must agree on repo kind, boot path, adapter mode, active milestone, and next action.
- When the repo has enough state surface to justify it, keep a concise `MEMORY.md`-style hub in the state location as the landing page for non-negotiables, linked memory files, and starter summary.

## Reality Discipline

- Trust documented state only after checking whether it still matches executable repo signals.
- Keep a small reality layer in the control plane: workspace boundaries, entrypoints, owned surfaces, key commands, and integrations.
- Use drift signals and artifact-health states to decide whether the boot path is trustworthy or needs repair first.

## Decision-Policy Discipline

- Make ask-versus-act behavior explicit instead of improvising it every session.
- Act automatically for low-blast-radius reversible improvements.
- Ask targeted questions for medium-risk architecture or tooling choices when constraints remain unresolved.
- Require confirmation for destructive, externally visible, security, compliance, or lock-in changes.
- Let repo-local policy override the shared operator profile when the repo has stricter needs.

## Operation-Pack Discipline

- Treat the repo OS as a compositor of small operating packs, not one giant monolithic workflow.
- Activate only the packs the current request and repo state require.
- Record the active pack set in the control plane so later sessions continue the same operating mode cheaply.
- Prefer `repair-drift` before implementation when contradictions are open.

## Adaptive Layout Discipline

- Reuse coherent repo conventions before creating `docs/`, `memory/`, or `scripts/`.
- Resolve `planning_doc_home`, `state_doc_home`, `task_spec_home`, and `script_home` before generating artifacts.
- Treat explicit canonical or supplemental or foundations taxonomies as first-class when they exist; otherwise infer hot or warm or cold tiers instead of forcing a fake taxonomy.

## Repo-Profile Discipline

- Select one primary repo profile and record secondary traits separately.
- Load only the relevant profile guidance for the current repo.
- Let the selected profile shape milestone archetypes, verification defaults, tooling categories, and task-spec thresholds.

## Fresh-Context Discipline

- Separate exploration from execution when practical.
- Prefer one thread for repo discovery or one implementation slice, not one endless session for everything.
- After file discovery, broad planning, or task completion, prefer a fresh thread and restart with a starter phrase.
- Keep boot artifacts good enough that a single phrase like `resume` or `what next` is sufficient to restart safely.
- Prefer a wake-up stack that goes from terse ledger to control plane to optional memory hub to only the exact docs needed for the active task.

## Multi-Agent Discipline

- Prefer shared durable truth over agent-specific duplication.
- When foreign-agent artifacts exist, inventory them before writing a new agent operating layer.
- In merged repos, keep `CLAUDE.md` as a thin compatibility overlay and keep shared rules in `CLAUDE.md`, the control plane, state artifacts, and shared docs.
- Do not silently delete or rewrite another agent system's files.

## Delegation Discipline

- The repo operating system owns sensing, routing, guardrails, state repair, and handoff.
- Delegate narrow execution slices to specialist skills only when they are available and clearly better suited.
- Record delegated routing in the control plane so future sessions do not rediscover the same handoff decision.
- Specialist skills should never become the sole source of repo state or safety policy.

## Library-First Discipline

- Prefer proven ecosystem tools when fit, maturity, docs quality, licensing, and operational complexity are acceptable.
- Build custom code only when requirements are unmet, integration risk is higher than custom implementation risk, or differentiation requires it.
- Record rejected options and revisit triggers explicitly.

## Capability-Discovery Discipline

- Treat tool and library discovery as a continuous operating capability, not just a greenfield setup step.
- When a task touches a likely commodity capability, inspect the repo and research the ecosystem before custom implementation.
- Use current web research and primary sources for compatibility-sensitive recommendations.
- Ask targeted clarification questions when the choice depends on constraints the repo cannot reveal.
- Preserve the result in a living artifact so later sessions do not re-run the same discovery from scratch.

## Execution Discipline

- Prefer structured file operations and `rg` for edits and search.
- Prefer narrow reads over repo-wide rereads.
- Keep one coherent thread or worktree per major task.
- Use isolated worktrees for parallel, risky, or experimental approaches once a stable checkpoint exists.

## Spec-Driven Discipline

- For non-trivial work, translate raw intent into a task spec before implementation-heavy changes.
- Use the task spec to drive the sequence: explore, plan, implement, verify.
- Keep task specs narrow, current, and tied to the exact files and verification steps that matter.
- When the horizon is materially larger than the current milestone, maintain both an active build layer and a preserved future architecture layer.
- Make task specs role-aware: primary role, supporting roles, preserved future consequences, and handoff chain.

## Self-Upgrading Tooling Discipline

- Treat every repeatable pain point as a chance to forge a reusable script, shortcut, or checklist.
- Promote an ad hoc workflow into a reusable tool when it is used twice, exceeds three repeatable steps, is part of wake-up or verification, or prevents broad rereads.
- Every new reusable tool must be logged in the resolved tool registry at creation time.
- Resume protocols should scan the tool registry before inventing a new one-off workflow.
- When the repo has enough reusable tooling, structure the registry like a HUD: sanity gates first, then scripts, then discovered pipelines.

## Forge-Loop Discipline

- Treat friction, failures, wins, repeated workarounds, and verified speedups as raw material for improvement.
- Run the Forge Loop: observe, classify, validate, promote, expose, reuse, retire.
- Keep raw candidates in an improvement ledger until they are validated enough to promote.
- Prefer a playbook-first promotion target for multi-step procedures, recovery flows, and decision heuristics; keep the tool registry command-only.
- Make the next agent session automatically see promoted learnings through the control plane, playbook registry, and starter flow.
- Compile repeated higher-order workflows into the right long-term target: tool, playbook, routing artifact, shared pattern, operation pack, or specialist-skill candidate.
- Measure whether upgrades are actually helping through reuse, verification success, estimated time saved, and stale-upgrade review.

## Shared-Catalog Discipline

- Repo-local learning is primary; cross-project learning is secondary and must be portable.
- Only portable patterns belong in the shared global catalog.
- Global patterns start as provisional, then become validated only after repeated evidence.
- Never let the shared catalog become a dump of repo-specific paths, names, or secrets.

## Verification Discipline

- Define quality gates early.
- Run the smallest relevant checks first, then broader checks when boundaries are crossed.
- Report exactly what was verified, what failed, and what remains unverified.
- Do not treat a task as done when docs, contracts, or migration notes are stale.

## Closure Discipline

- Completion is a first-class responsibility, not a nice-to-have.
- Prefer finished usable artifacts over outlines when the missing work is straightforward.
- Bias toward Finisher-Operator when the value now lies in polishing, filling gaps, packaging, or making the artifact resumable.

## Pushback Discipline

- Push back to protect the project, not to normalize it.
- Good reasons to push back: scope explosion, architecture contradiction, blob drift, identity loss, hidden provenance loss, or premature lock-in.
- When pushback is needed, preserve the underlying value and propose a safer current-layer version or later-phase slot.

## Handoff Discipline

- Leave the next session with a correct ledger, an explicit next action, and the minimum boot path.
- Summarize signal, not raw logs.
- Keep handoff artifacts cheap to reload and easy to trust.
- Make the next handoff owner explicit when a task is passing from interpretation to scoping, sequencing, finishing, continuity, or interface translation.

## Lifecycle Discipline

- Give artifacts lifecycle states: required, active, dormant, stale, or archived.
- Keep dormant and archived surfaces out of the hot boot path unless the task touches them.
- Retire stale or net-negative upgrades instead of endlessly carrying them forward.
