# SDD Integration

> **Purpose**: How the PMBOK-lite document structure relates to the SDD 5-phase workflow instead of duplicating it
> **MCP Validated**: not applicable — house convention, not MCP-fed

## When to Use

- A "project" turns out to be, or contains, a software feature that needs building.
- Deciding whether a request belongs to `project-docs-manager` or to `sdd-workflow`.
- A project has both non-technical deliverables (a launch, a client engagement) and a software component.

## Implementation

These are different altitudes, not competing systems:

```text
project-docs/                          .claude/sdd/
(this KB — the surrounding             (sdd-workflow skill — the
 project: people, scope,                implementation of one
 comms, closure)                        piece of software)

01-terms-and-charter/          ─┐
02-stakeholders/                 │  answers: why does this
03-planning/                     │  project exist, who cares,
                                 ─┘  how do we run it

04-execution/  ──────────────────── epics/phases here map to
                                     BRAINSTORM → DEFINE → DESIGN →
                                     BUILD → SHIP documents in
                                     .claude/sdd/features/ for any
                                     epic that is itself a build

05-communication/  ─────────────── meeting-minutes, progress-reports,
                                    risk-reports keep running the
                                    whole time SDD phases execute

06-closing/  ────────────────────── closure-document references the
                                     SHIPPED_*.md archive entries as
                                     evidence of what was delivered
```

A `project-plan.md` epic that is a discrete software deliverable does not get its own markdown design doc inside `project-docs/` — it gets handed to `/brainstorm` or `/define`, and `project-plan.md` links to the resulting `.claude/sdd/features/DEFINE_*.md` instead of re-describing it.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Handoff point | Planning → Execution | The moment an epic is clearly a software build, route it to SDD before Execution starts, not after |
| Cross-reference | Link, don't copy | `project-plan.md` links to SDD artifacts by path; never re-inline DEFINE/DESIGN content |

## Example Usage

```text
User: "This project includes rebuilding the churn model pipeline."

1. project-docs-manager keeps owning the surrounding project: charter,
   stakeholders, plan, comms, closure.
2. The pipeline rebuild itself is handed to sdd-workflow:
   /brainstorm "rebuild the churn model pipeline" → ... → /ship
3. project-plan.md gets one line: "Pipeline rebuild — see
   .claude/sdd/features/DEFINE_CHURN_PIPELINE.md" — not a restated scope.
4. Progress reports mention SDD phase progress as one line item among
   others, not a full re-narration of the SDD artifacts.
```

## See Also

- [scaffold-structure](scaffold-structure.md)
- [document-lifecycle](document-lifecycle.md)
