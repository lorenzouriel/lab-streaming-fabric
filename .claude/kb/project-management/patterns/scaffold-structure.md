# Scaffold Structure

> **Purpose**: The exact `project-docs/` folder tree to create, and when to create it
> **MCP Validated**: not applicable — house convention, not MCP-fed

## When to Use

- A new project starts and no `project-docs/` folder exists yet.
- The user asks to "set up project docs", "start a new project", or "structure this project from the start".
- An existing project has partial documentation scattered across chat/notes and needs consolidating into the standard shape.

## Implementation

```text
project-docs/
├── 01-terms-and-charter/
│   ├── understanding-context.md
│   └── project-charter.md
├── 02-stakeholders/
│   ├── matrix.md
│   └── kickoff-minutes.md
├── 03-planning/
│   ├── project-plan.md
│   └── communication-plan.md
├── 04-execution/
│   └── README.md            # pointer to the task tracker in use — no generated docs here
├── 05-communication/
│   ├── meeting-minutes/
│   ├── progress-reports/
│   └── risk-reports/
└── 06-closing/
    └── closure-document.md
```

Notes on the scaffold:

- Format is Markdown, not `.docx`/`.xlsx` — this repo's documents stay diffable and git-friendly. Convert to `.docx` at hand-off time only if a stakeholder needs it in that format (use the `formats` skill family if this repo has one, or plain pandoc).
- `04-execution/README.md` names the actual tracker (Azure Boards, Jira, Linear, GitHub Projects) and a link — the epics/phases in `project-plan.md` map to tasks there; do not duplicate task-level detail into markdown.
- `05-communication/` subfolders start empty; the first file lands the first time each artifact type is produced.
- Where the project lives inside a larger repo (not its own top-level folder), place `project-docs/` at the project's own root, not the monorepo root, so it travels with the project if it's ever extracted.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| File format | `.md` | Keep source-controlled docs in Markdown; export on demand |
| Filename dates | `YYYY-MM-DD` | Every recurring file under `05-communication/` is named by date |
| Location | `<project-root>/project-docs/` | Not the monorepo root when the project is one of several |

## Example Usage

```text
User: "Start a new project for the customer-churn model rebuild."

1. Confirm the project root (existing folder, or create one).
2. Create the tree above under <root>/project-docs/.
3. Interview for 01-terms-and-charter/ content — see document-lifecycle.md
   for what's asked at Initiating.
4. Leave 02-06 empty until their triggering event happens (kickoff meeting,
   first planning session, first status cycle, project end).
```

## See Also

- [document-lifecycle](document-lifecycle.md)
- [document-purposes](../concepts/document-purposes.md)
- [sdd-integration](sdd-integration.md)
