# Document Purposes

> **Purpose**: What each document in the six-folder structure is for, and who reads it
> **Confidence**: 0.85
> **MCP Validated**: not applicable — house distillation, not MCP-fed

## Overview

Every document below exists to answer one recurring failure mode: work starting with no record of why, no shared understanding of scope, and no trail of what changed. Each has one job — do not let two documents grow to cover the same ground.

## The Concept

```text
01-terms-and-charter/
  understanding-context   — private brainstorm: current state vs. desired state, for the
                             author only, never shared with stakeholders
  project-charter          — formal authorization: business justification, objectives,
                             scope, stakeholders, assumptions; the alignment reference
                             everyone points back to when scope is disputed

02-stakeholders/
  matrix                   — every stakeholder, their influence, their interest, and the
                             engagement strategy that follows from that quadrant
  kickoff-minutes           — record of the kickoff: roles, initial scope, key dates,
                             agreements; also the moment to state success criteria out loud

03-planning/
  project-plan              — how the project will run: scope, schedule, responsibilities,
                             resources, risks, deliverables, success criteria
  communication-plan         — who receives what information, how often, through which
                             channel, in what format

04-execution/
  (no document)              — tracked in the task tool (Azure Boards, Jira, Linear, or
                             equivalent); the plan is epics/phases, the tracker is tasks

05-communication/
  meeting-minutes/            — official record of decisions and alignments per meeting
  progress-reports/            — periodic delivery status, deadline adherence, next steps
  risk-reports/                  — risk description, preventive action, plan, owner

06-closing/
  closure-document               — completed deliverables, final validations, stakeholder
                             approvals, lessons learned
```

## Quick Reference

| Document | Audience | Written once or recurring |
|----------|----------|---------------------------|
| understanding-context | Author only | Once, early |
| project-charter | All stakeholders | Once, revised rarely |
| matrix | Project owner | Once, revisited periodically |
| kickoff-minutes | All attendees | Once |
| project-plan | All stakeholders | Once, revised on major scope change |
| communication-plan | All stakeholders | Once, revised rarely |
| meeting-minutes | Attendees + absent stakeholders | Recurring, one per meeting |
| progress-reports | Stakeholders | Recurring, fixed cadence |
| risk-reports | Stakeholders | Recurring, fixed cadence |
| closure-document | All stakeholders | Once, at the end |

## Common Mistakes

### Wrong

Writing a status update inside `project-plan` instead of a new dated `progress-reports/` entry — the plan should describe the approach, not today's state.

### Correct

The plan stays a stable reference; state and status live in the recurring `05-communication/` documents, one file per period.

## Related

- [phases](phases.md)
- [document-lifecycle](../patterns/document-lifecycle.md)
- [scaffold-structure](../patterns/scaffold-structure.md)
