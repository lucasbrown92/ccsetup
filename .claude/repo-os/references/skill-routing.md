# Skill Routing

Use this reference when the repo operating system may delegate narrow execution to another installed skill.

## Goal

Treat repo OS as the executive layer and specialist skills as subordinate executors when they clearly improve the outcome.

## Discovering Available Skills

Prefer the current session's declared available-skill list when present. Otherwise inspect installed skills under `~/.claude/skills/` only as needed.

## Routing Rule

- Repo OS owns sensing, control-plane updates, guardrails, drift repair, and handoff.
- Internal creator-aligned roles own interpretation, scoping, sequencing, finishing, continuity, critique, and audience translation inside repo OS.
- Delegate only narrow task classes to specialist skills.
- Use a specialist skill only when its scope is clearly better than generic repo OS execution.
- Fall back to internal handling when no specialist skill is available or when delegation would fragment the state story.

## Good Delegation Targets

- skill authoring and skill maintenance
- highly specific platform or workflow skills
- specialist execution domains already covered by an installed skill

## Bad Delegation Targets

- deciding which repo files matter on wake-up
- repairing stale state artifacts
- managing decision policy or hard safety stops
- final handoff and next-action preparation

## Recording Rule

When routing materially affects future execution, record in the control plane:

- task class
- preferred skill
- fallback behavior
- delegation notes or limits
- active internal roles
- pending handoff target when the work is passing between internal roles
