# Agent Interop

Use this reference when the target repo already contains non-Claude Code agent instructions. Claude is the first supported external adapter.

## Adapter Model

Prefer a shared operating core plus thin agent-specific overlays.

- root `CLAUDE.md` is the terse human ledger
- `<state_doc_home>/repo-operating-profile.yaml` is the machine-readable control plane
- resolved state and planning artifacts are shared durable truth
- agent-specific files are overlays, not separate operating systems

Record adapter state in `agent_adapters` inside the control plane.

## Detect Claude Artifacts

Search for all of the following before writing new agent-operating files:

- `CLAUDE.md`
- `CLAUDE*.md`
- `claude*.md`
- `.claude/`

Inspect nested repos and subdirectories only when they are inside the target repo scope.

## Migration Modes

### 1. Claude Code-Only Conversion

Use when the user wants to fully convert the repo to Claude Code-centric operation.

- Migrate durable, non-inferable rules into `CLAUDE.md`, the control plane, and shared state and planning artifacts.
- Preserve migration notes in the resolved migration document.
- Remove, archive, or minimize Claude artifacts only with explicit user approval.

### 2. Merged Dual-Agent Repo

Use when the repo should remain workable for both Claude Code and Claude.

- Treat `CLAUDE.md`, the control plane, shared state files, and shared planning docs as the durable shared source of truth.
- Keep `CLAUDE.md` as a thin compatibility shim with only Claude-specific deltas and pointers to shared files.
- Avoid duplicating full protocols across both files.

### 3. Claude-Preserving Claude Code Overlay

Use when the repo already depends heavily on Claude workflows and the user wants Claude Code support without reauthoring the whole system.

- Keep Claude artifacts intact.
- Add Claude Code operational files beside them.
- Record the precedence and sync expectations explicitly in the migration document and control plane.

## Decision Rule

- If the user already stated the desired mode, use it.
- If Claude artifacts are detected and the mode is unspecified, ask the user which mode to use.
- If an answer cannot be obtained and work must continue, default to merged dual-agent repo because it is the least destructive.

## Shared Truth Hierarchy

In merged repos, prefer this hierarchy:

1. `CLAUDE.md`
2. `<state_doc_home>/repo-operating-profile.yaml`
3. shared state files and routing docs
4. shared design and planning docs
5. `CLAUDE.md` for Claude-only overlays

Do not let `CLAUDE.md` become a second monolithic instruction dump.

## Migration Checklist

- Inventory every foreign-agent artifact and its purpose.
- Separate durable rules from agent-specific ergonomics.
- Move shared durable guidance into `CLAUDE.md`, the control plane, shared state files, and shared planning docs.
- Create or update the migration document.
- Create or update a thin `CLAUDE.md` compatibility shim for merged mode.
- Record the chosen adapter mode in `CLAUDE.md`, the control plane, and project-state.
