# Execution Guardrails

## Target Repo and Safety

- Confirm the target repo before scaffolding. If the current directory contains multiple repos, choose one target first.
- Check whether git is initialized, whether a safe checkpoint exists, and whether the working tree is clean enough for risky edits.
- Detect the existing package manager, lockfiles, and build or test entry points before adding new tooling.
- Check `.gitignore` and local env patterns before writing secrets, tokens, or machine-specific settings.

## Documentation Ingestion Order

- If the repo has explicit canonical, supplemental or legacy, and foundations or historical buckets, read them in that order.
- Build indexes that explain which files to read for which milestone, subsystem, or task.
- Prefer recording search hints and exact file routes over repeating large narrative summaries.

## Operational Ledger Pattern

- Keep root `CLAUDE.md` to roughly one screen.
- Store only operational state and non-inferable details: mission, constraints, decisions, phase, `Done`, `Now`, `Next`, `UNCONFIRMED`, active working set, and boot path.
- Update `CLAUDE.md` at the start of each major phase, after milestone changes, and before ending major work.
- Keep richer history, routing, and design reasoning in the resolved state and planning locations.
- Maintain a synchronized machine-readable control plane at `<state_doc_home>/repo-operating-profile.yaml`.
- If `<state_doc_home>/MEMORY.md` exists, keep it lean and hub-like. It should point to richer files, not duplicate them.
- Keep `tool-registry.md` command-only.
- Keep procedural heuristics and recovery flows in `playbook-registry.md`, and raw unpromoted lessons in `improvement-ledger.md`.
- Keep governance machine-readable in the control plane: reality model, decision policy, active packs, skill routing, artifact health, and drift signals.

## Decision Policy Guardrails

- Shared operator profile path: `~/.claude/memory/repo-operating-system/operator-profile.yaml`
- Use the shared operator profile only as a default bias layer. Repo-local control-plane policy wins when it is stricter.
- Do not let an aggressive autonomy preference bypass hard safety stops.
- Medium-risk architecture or tooling choices should trigger targeted user questions when the repo cannot resolve the tradeoff.

## Contradiction and Drift Guardrails

- On resume and handoff, compare root `CLAUDE.md`, the control plane, project-state, system-state, and current repo signals before trusting stale state.
- If contradictions are material, activate `repair-drift` before broad implementation.
- Keep optional drift artifacts such as `surface-map.yaml` and `artifact-health.md` lean and operational, not narrative.
- Archived or dormant artifacts must not stay in the hot boot path unless the current task touches them.

## External Agent Files

- Search for `CLAUDE.md`, `CLAUDE*.md`, `claude*.md`, and `.claude/` before bootstrapping agent-operating files.
- If Claude artifacts are detected and the migration mode is unspecified, ask the user whether to convert to Claude Code-only operation or maintain a merged repo.
- Never silently delete or overwrite Claude artifacts.
- When merged operation is selected, keep `CLAUDE.md` thin and shared truth elsewhere.

## Planning Gate

- Do not harden scaffolding until planning artifacts are approved or explicitly waived.
- Required planning artifacts for greenfield or major-architecture work are:
  - tooling survey in the resolved planning-doc location
  - module system in the resolved planning-doc location
  - MVP spec in the resolved planning-doc location
  - milestone ledger in the resolved milestone location
- If a major capability choice is still unresolved, include the capability map or equivalent decision artifact in the planning gate.
- Brownfield targeted refresh work may bypass the full planning gate only when architecture and tooling are materially unchanged.

## Worktree Conventions

- Use git worktrees for non-trivial, risky, or concurrent work once the repo has a stable checkpoint.
- Prefer sibling directories outside the main repo tree.
- Follow repo branch naming rules when present. Otherwise default to `codex/<task>`.
- Record the active branch and worktree path in `CLAUDE.md`, the control plane, and project-state.
- Remove or archive stale worktree references during handoff.

## Specialist Skill Delegation

- Repo operating system keeps boot, state, guardrails, drift repair, and handoff centralized.
- Delegate only narrow execution slices to specialist skills.
- Record delegated task-class routing in the control plane.
- Fall back to internal handling when no specialist skill is available or when delegation would fragment the state story.

## `.claude/settings.json` and Integrations

- Create or modify `.claude/settings.json` only when project-scoped approval defaults or integrations are necessary.
- Start with the minimum viable set of integrations.
- Common categories: docs, browser automation, design sources, source control, telemetry.
- Do not add integrations that require authentication unless the task requires them and credentials or login flow are available.
- Verify each integration with a client-visible status check or a small smoke test.

## Tool and Context Hygiene

- Prefer structured file operations and `rg` for file edits and search.
- Avoid brittle shell editing patterns when a patching tool or direct file edit is available.
- Parallelize independent searches and file reads where possible.
- Summarize signal, not raw package manager or build logs.
- Record blockers, failed checks, and next action instead of carrying noisy logs forward.
- Prefer fresh context after broad exploration or completed work slices when the client or workflow supports it.
- Scan the resolved tool registry before reinventing a script, shortcut, or diagnostic pipeline.
- If the repo has a `MEMORY.md` state hub, read it before deeper state files on wake-up.
- When evaluating external tools, libraries, or managed services, use web research and primary sources before recommending adoption.
- Do not trust stale memory for package health, compatibility, or current ecosystem fit.

## Shared Global Catalog Safety

- Shared global catalog path: `~/.claude/memory/repo-operating-system/global-pattern-catalog.md`
- Treat the catalog as portable cross-project memory, not as skill source.
- Never self-modify the skill to store learning.
- Never store repo-specific secrets, absolute repo paths, customer names, or non-portable assumptions in the catalog.
- New catalog entries must start as `provisional`.
- Only `validated` entries may influence defaults automatically in future repos.

## Max Auto With Hard Safety Stops

The skill may automatically create and refresh ledgers, planning docs, task specs, scripts, quality-gate entry points, initialization sweeps, and routing artifacts.

It must stop and ask before:

- destructive file removal
- secrets or auth setup requiring human input
- irreversible migrations
- externally visible runtime architecture pivots
- deleting or collapsing foreign-agent files
- high-blast-radius choices called out by the control-plane decision policy

## Maintenance Refresh

- On resume, read root `CLAUDE.md`, the control plane, the hot boot path, the tool registry, and any active drift artifacts before deciding what is stale.
- Check reality-model facts and artifact-health states before trusting older docs or ledgers.
- Refresh only the affected state files when the changed surfaces are known.
- If the boot path, profile, or adapter mode changes, update both human-readable and machine-readable state in the same pass.
- If improvement candidates or active playbooks changed, update the improvement ledger, playbook registry, and improvement-system control-plane state in the same pass.
- If active packs, decision policy, skill routing, or artifact lifecycle states changed, update them in the same pass.
