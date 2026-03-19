# Milestones Template

Use this template for `MILESTONES.md` and milestone detail files.

## Delivery Principles

- Keep each milestone independently valuable.
- Use measurable exits, not vague completion language.
- Keep risk-heavy work early.
- Keep polish and optimization after capability proof.
- Tailor milestone count and naming to the repo type.

## Suggested Sequence

Treat this as a starting pattern, not a rigid mandate.

| Milestone | Default Title | Goal | Typical Exit Criteria |
| --- | --- | --- | --- |
| `A` | Foundations and Decisions | Finalize stack, architecture, and operating rules | Tooling survey approved; module system approved; MVP scope approved; operating ledger in place |
| `B` | First Proved Capability | Deliver one representative slice or release path | One meaningful flow, package, or service path works with tests and observability |
| `C` | MVP Completion | Finish in-scope MVP capabilities | MVP scope complete with passing quality gates |
| `D` | Hardening and Readiness | Close reliability, performance, accessibility, or migration gaps | Launch or release checklist complete; rollback or migration path validated |
| `E` | Post-MVP Track | Prioritize the next wave of work | Post-MVP roadmap or follow-up backlog approved |

Rename, split, merge, or drop milestones when the repo shape demands it.

## Repo-Type Notes

- Product app repos often use a vertical-slice milestone early.
- Libraries or SDKs may replace the vertical slice with a first release path, contract proof, or compatibility matrix.
- Platform or infra repos may center milestones around environment proof, service bring-up, migration safety, or operational readiness.

## Milestone Ledger

```md
# Milestones

| Milestone | Title | Goal | Exit Criteria | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `A` |  |  |  | Planned |  |
```

## File Layout

Store milestone detail files at:

```text
<planning_doc_home>/milestones/A.md
<planning_doc_home>/milestones/B.md
<planning_doc_home>/milestones/C.md
```

Create only the files that the plan actually needs.

The selected repo profile may rename, merge, or drop milestones. Preserve the repo's established milestone style when it is already coherent.

## Per-Milestone Template

Use this body for each `<planning_doc_home>/milestones/<X>.md` file:

```md
# Milestone <X>: <Title>

## Objective

## Scope
- Included:
- Excluded:

## Dependencies
- Upstream:
- External:

## Work Items
- [ ] Item 1
- [ ] Item 2
- [ ] Item 3

## Quality Gates
- [ ] lint
- [ ] typecheck
- [ ] test
- [ ] build
- [ ] milestone-specific gate

## Exit Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Evidence
- Verification output:
- Demo or release proof:
- Docs updated:

## Risks and Mitigations
| Risk | Mitigation | Owner |
| --- | --- | --- |
|  |  |  |

## State Updates Required
- Update `CLAUDE.md`
- Update the control plane
- Update the resolved project-state artifact
- Update the resolved system-state artifact
- Update `MILESTONES.md`
- Update the resolved tool registry if new tooling was created

## Notes
```

## Planning Gate

Do not start implementation-heavy work until the planning artifacts that shape the milestone are approved or explicitly waived.
