# Agent Migration Template

Use this template when converting a Claude-oriented repo to Claude Code or setting up merged-agent operation.

## `<planning_doc_home>/agent-system-migration.md`

```md
# Agent System Migration

## Selected Mode
- `codex-only conversion | merged dual-agent repo | Claude-preserving Claude Code overlay`

## Detected Artifacts
| Path | Type | Current role | Keep, merge, archive, or replace |
| --- | --- | --- | --- |

## Shared Durable Truth
- `CLAUDE.md`
- `<artifact_locations.control_plane>`
- `<artifact_locations.docs_index>`
- `<artifact_locations.project_state>`
- `<artifact_locations.system_state_index>`
- other shared docs:

## Adapter Status
- Primary agent:
- Foreign adapters enabled:
- Claude mode:

## Claude-Specific Overlay
- `CLAUDE.md` role:
- Additional Claude-only files:

## Mapping Decisions
| Source artifact | Mapped into | Notes |
| --- | --- | --- |

## Open Questions
- ...

## Approval Status
- User approved mode:
- User approved file changes:
- Follow-up required:
```

## `CLAUDE.md` Compatibility Shim

Use this only for merged dual-agent repos or a temporary compatibility phase.

```md
# CLAUDE.md

## Compatibility Note
This repository uses shared agent-operating files.

Read in order:
1. `CLAUDE.md`
2. `<artifact_locations.control_plane>`
3. `<artifact_locations.project_state>`
4. `<artifact_locations.starters>`

## Claude-Specific Notes
- Add only Claude-specific deltas here.
- Do not duplicate the full repository protocol.
- If this file conflicts with the shared operating files, document the reason explicitly.
```
