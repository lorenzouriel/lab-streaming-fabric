# Project Management Quick Reference

> Fast lookup tables. For the full method, see linked files.

## The six folders

| Folder | Holds |
|--------|-------|
| `01-terms-and-charter/` | understanding-context, project-charter |
| `02-stakeholders/` | matrix, kickoff-minutes |
| `03-planning/` | project-plan, communication-plan |
| `04-execution/` | pointer to the task tracker — no generated docs |
| `05-communication/` | meeting-minutes/, progress-reports/, risk-reports/ |
| `06-closing/` | closure-document |

## Process group → typical document

| Process group | Document created |
|----------------|-------------------|
| Initiating | understanding-context, project-charter |
| Planning | stakeholder matrix, kickoff-minutes, project-plan, communication-plan |
| Execution | none generated — tracked in the task tool |
| Monitoring & Controlling | progress-reports, risk-reports (recurring) |
| Closing | closure-document |

## Decision Matrix

| Situation | Do this |
|-----------|---------|
| Brand-new project, no `project-docs/` yet | Scaffold via `patterns/scaffold-structure.md`, start with charter |
| A meeting just happened | Delegate to `meeting-analysis`, file the result under `05-communication/meeting-minutes/` |
| Stakeholder list feels stale | Re-run the matrix — interest and influence drift over the project's life |
| The "project" is really a software feature to build | Hand off to the SDD workflow (`sdd-workflow` skill) — this KB is for the surrounding documentation, not implementation |
| Project is ending | Draft closure only from verifiable deliverables/approvals already in the workspace |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Start execution with no charter or plan | Initiating and Planning first — even briefly |
| Treat the phases as strictly sequential | Expect Planning and Execution to overlap; Monitoring runs throughout |
| Invent stakeholders, budgets, or approvals | Ask the user; leave a placeholder instead of guessing |
| Duplicate meeting-analysis inside this KB | Delegate to it; only the filing location changes |

## Related Documentation

| Topic | Path |
|-------|------|
| Six-phase document lifecycle | `patterns/document-lifecycle.md` |
| SDD relationship | `patterns/sdd-integration.md` |
| Full Index | `index.md` |
