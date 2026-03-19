# Classification Rules

## Document Classes

### Canonical

Treat a source as canonical when it governs current behavior or active workflow. Typical examples are current specs, maintained runbooks, migration plans in force, approved milestone plans, agent-migration plans in force, and docs explicitly linked from the boot path.

### Supplemental or Legacy

Treat a source as supplemental or legacy when it still has context value but should not drive present-tense decisions without corroboration. Typical examples are old milestone plans, superseded design notes, and outdated checklists.

### Foundational, Speculative, or Historical

Treat a source as foundational, speculative, or historical when it explains intent, research, or earlier reasoning but does not define the current operating state. Typical examples are explorations, long-range vision docs, and old postmortems.

## Conflict Resolution

1. Prefer executable truth from code, tests, schemas, and config when prose conflicts.
2. If multiple docs disagree, prefer the one most recently maintained and closest to the active surface.
3. Record unresolved conflicts in the resolved docs-index artifact instead of silently choosing one.
4. Mark uncertain classifications as provisional.
5. Do not add generic code summaries unless the repo is genuinely underdocumented and the summary adds non-inferable signal.
6. If `CLAUDE.md` and `CLAUDE.md` disagree in a merged repo, record the conflict and resolve it through the chosen migration mode rather than silently favoring one.

## Boot Path Selection

- Keep the boot path small, usually three to seven files.
- Put `CLAUDE.md`, the control plane, and state or routing artifacts ahead of broad narrative docs.
- Add subsystem-specific files only when they are active for the next task.
- Remove stale entries when they stop reducing startup cost.
- Use hot or warm or cold tiers when the repo does not already define an explicit doc taxonomy.

## Routing Heuristics

- Route by task and subsystem, not by folder dump.
- For each route, identify the first file to read, the second file if needed, and the verification step.
- Stop adding files when the next action is clear.
- Prefer routing to the smallest authoritative file over routing to large overview documents.

## Milestone Horizon

Scaffold only what is needed for the current milestone and the immediate next handoff. Do not create placeholder systems for speculative future phases unless the user explicitly asks for them.
