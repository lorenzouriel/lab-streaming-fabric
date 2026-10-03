---
name: project-docs
description: |
  Scaffolds and maintains a project's PMBOK-lite documentation set — a six-folder structure
  (terms-and-charter, stakeholders, planning, execution pointer, communication, closing) — by
  delegating the substantive drafting to the project-docs-manager agent. Use when the user starts
  a new project with no documentation trail, asks for a charter, stakeholder matrix, project plan,
  communication plan, progress report, risk report, or closure document, or wants an existing
  project's docs reconciled with reality. Do not use for a software feature spec — use sdd-workflow
  — for a daily standup message — use standup-report — or for a generic meeting summary that isn't
  being filed into a project's doc set — use meeting-analysis directly.
---

# Project Docs

Keep one project's documentation honest and current: who it's for, what it's trying to do, who's
affected, how it's tracked, and how it ends. This skill orients — the actual drafting is the
`project-docs-manager` agent's job; the KB at `.claude/kb/project-management/` is the source of
truth for the structure and cadence.

## When to Use

- A project is starting and nothing is documented yet.
- The user asks for any of: understanding-context, project-charter, stakeholder matrix,
  kickoff-minutes, project-plan, communication-plan, a progress report, a risk report, or a
  closure document.
- An existing `project-docs/` tree looks out of sync with the real state of the project.

## Skip If

- The ask is a software feature that needs building, not documenting — route to `sdd-workflow`
  instead; this skill's KB (`patterns/sdd-integration.md`) explains the handoff.
- The ask is a daily standup message — use `standup-report`.
- The ask is a one-off meeting summary that isn't being filed into a project's `05-communication/`
  folder — use `meeting-analysis` directly. When it IS going into a project's doc set, still start
  here so the filing location and any triggered updates (risk-reports, plan) are handled.

## Process

### 1. Locate or scaffold `project-docs/`

Check whether `project-docs/` already exists at the project's root. If not, this is Initiating —
delegate to `project-docs-manager` for Capability 1 (scaffold). If it exists, skip to step 2.

### 2. Identify the one document the request belongs to

Read `.claude/kb/project-management/concepts/document-purposes.md` if the mapping isn't obvious.
A single request maps to a single document — resist the urge to update three files for one ask.

### 3. Delegate to `project-docs-manager`

Hand off the request with:
- which document (or "scaffold" for a brand-new project),
- everything the user has already stated (names, dates, scope, approvals) — the agent must not
  invent what it isn't given,
- whether this is a create or an update, per `.claude/kb/project-management/patterns/document-lifecycle.md`.

### 4. Route meeting minutes through `meeting-analysis`

If the request is "write up this meeting" and it belongs in a project's record, invoke
`meeting-analysis` for the extraction, then hand its output to `project-docs-manager` to file at
`05-communication/meeting-minutes/<date>-<topic>.md` and check whether it triggers a risk-report
or plan update. Never re-extract a transcript inline here.

### 5. Route software-shaped scope to SDD

If drafting the plan or a progress report surfaces an epic that is really a build (a pipeline, a
feature, a migration), don't write a design doc inside `project-docs/`. Point the user at
`/brainstorm` or `/define` for that piece, and have `project-plan.md` link to the resulting
`.claude/sdd/features/` artifact instead of restating it. See
`.claude/kb/project-management/patterns/sdd-integration.md`.

## Quality rules

| # | Rule | Why |
|---|------|-----|
| 1 | Never invent a stakeholder, date, budget figure, or approval. | Fabricated content misdirects real decisions — the entire point of this doc set is to prevent that. |
| 2 | Recurring documents (progress-reports, risk-reports, meeting-minutes) always get a new dated file. | Editing a prior period destroys the historical record the doc set exists to keep. |
| 3 | One request, one document. | Spreading one update across several files is how doc sets rot — nobody knows which one is authoritative. |
| 4 | The five process groups overlap — don't gate progress on "finishing" one before starting the next. | Planning and Monitoring & Controlling run throughout; see `concepts/phases.md`. |
| 5 | `04-execution/` never gets generated documents — only a pointer to the real tracker. | Duplicating task-level detail into markdown creates two sources of truth that drift apart. |

## Delivery

Confirm the file path written or updated, and — for anything at IMPORTANT or CRITICAL impact
(charter, plan, stakeholder matrix, closure) — show what changed before treating it as final, the
same way a diff would be shown for any other durable record.
