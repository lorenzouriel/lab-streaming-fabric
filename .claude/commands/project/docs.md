---
name: docs
description: Scaffold or update a project's PMBOK-lite documentation set (charter, stakeholders, plan, communication, closing)
---

# /project:docs Command

> Typed entry point for the `project-docs` skill — keeps a project's documentation set honest and current.

## Usage

```bash
/project:docs <request>
```

## Examples

```bash
/project:docs scaffold a new project called Notification Revamp
/project:docs write the charter
/project:docs stakeholder matrix for the migration project
/project:docs progress report
/project:docs reconcile project-docs/ with where things actually stand
```

## What Happens

Load `.claude/skills/project-docs/SKILL.md` and follow it as written. The skill
orients (locate-or-scaffold, map the request to one document) and delegates the
actual drafting to the `project-docs-manager` agent — this command adds no
methodology of its own.

1. **Locate or scaffold** — check for an existing `project-docs/` tree; scaffold
   the six-folder structure if this is a brand-new project.
2. **Identify the one document** the request maps to (see
   `.claude/kb/project-management/concepts/document-purposes.md`).
3. **Delegate to `project-docs-manager`** with everything already known — never
   invent stakeholders, dates, budget figures, or approvals.
4. **Route meeting minutes** through `meeting-analysis` first when the request
   is "write up this meeting."
5. **Route software-shaped scope** (a pipeline, feature, migration surfaced
   while drafting) to `/brainstorm` or `/define` instead of documenting it here.

## Not For

- A software feature spec — use `/brainstorm` or `/define` (SDD workflow).
- A daily standup message — use `/standup-report`-equivalent (`standup-report` skill).
- A one-off meeting summary that isn't being filed into a project's doc set —
  invoke `meeting-analysis` directly.

## References

- Skill (methodology + routing): `.claude/skills/project-docs/SKILL.md`
- Agent (drafting): `project-docs-manager`
- KB: `.claude/kb/project-management/`
