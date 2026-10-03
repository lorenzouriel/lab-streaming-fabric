---
name: prune-stack
description: Archive agents/kb/skills/commands not relevant to the project's actual tech stack, keeping only what's used
---

# Prune Stack Command

> Keeps `.claude/` lean: computes which agents, KB domains, skills, and commands are actually relevant to the
> project's declared or detected tech stack, and archives (never hard-deletes on first run) everything else.

## Usage

```bash
/prune-stack [tech1,tech2,...] [--apply] [--restore] [--purge]
```

**Examples**: `/prune-stack sql,python,terraform`, `/prune-stack` (auto-detect), `/prune-stack --apply`, `/prune-stack --restore`

- No args → dry-run using auto-detected stack, prints the keep/archive plan only.
- `<tech list>` → dry-run using the given stack instead of auto-detection.
- `--apply` → actually move archived items into `.claude/_archive/<timestamp>/` (must follow a dry-run the user confirmed).
- `--restore` → move everything back from the most recent `.claude/_archive/<timestamp>/` and delete the archive folder.
- `--purge` → permanently delete a named archive folder (`.claude/_archive/<timestamp>/`). Requires explicit user confirmation — this is irreversible.

## What Happens

### 1. Determine the stack

If tech names were passed as arguments, use those. Otherwise auto-detect by scanning the project root (not `.claude/`) for:

- `*.tf`, `*.tfvars`, `.terraform/` → terraform
- `requirements.txt`, `pyproject.toml`, `*.py`, `Pipfile` → python
- `*.sql`, `dbt_project.yml`, `models/**/*.sql` → sql (+ dbt if `dbt_project.yml` present)
- `package.json`, `*.ts`, `*.tsx`, `*.js` → javascript
- `*.parquet` + Spark/Databricks config, `databricks.yml` → spark / lakeflow
- `docker-compose.yml`, `Dockerfile`, `.github/workflows/*` → ci-cd
- cloud SDK imports/config (`boto3`, `google-cloud-*`, Azure SDKs) → aws / gcp / fabric

Show the detected (or given) stack list to the user before proceeding. If nothing is detected, ask the user directly rather than guessing.

### 2. Map stack → KB domains (keep-set)

| Stack keyword | KB domains to keep |
|---|---|
| sql | sql-patterns, data-modeling |
| python | python, pydantic, testing |
| terraform | terraform, cloud-platforms |
| dbt | dbt, sql-patterns, data-quality |
| spark | spark, lakehouse |
| lakeflow / databricks | lakeflow, lakehouse, medallion, spark |
| airflow | airflow, data-quality |
| aws | aws, terraform, cloud-platforms |
| gcp | gcp, terraform, cloud-platforms |
| fabric | microsoft-fabric |
| streaming / kafka | streaming, spark |
| genai / rag / llm | genai, prompt-engineering, ai-data-engineering, pydantic |
| supabase | supabase, ai-data-engineering, data-modeling |
| project-management | project-management |

Always keep regardless of stack: `shared/` and `_templates/` (referenced by every agent).

Build the actual keep-set by reading `.claude/kb/_index.yaml`'s domain registry (source of truth) rather than
hardcoding beyond this table — if a domain isn't in the table above, ask the user whether to keep it instead of
silently archiving it.

### 3. Compute keep-set for agents

For every file under `.claude/agents/**/*.md` (excluding `_template.md` and `README.md`):

1. Read the `kb_domains:` frontmatter field.
2. If empty (`[]`) → **keep** (utility/orchestrator agents — workflow phase agents, `the-planner`, `kb-architect`,
   `codebase-explorer`, `meeting-analyst`, `shell-script-specialist`, `prompt-crafter` — have no stack dependency).
3. If any listed domain intersects the keep-set from Step 2 → **keep**.
4. Otherwise → **archive**.

### 4. Compute keep-set for commands

For every file under `.claude/commands/**/*.md` (excluding `README.md`):

1. Read the command body for agent names it delegates to (e.g. `sql-review.md` invokes `sql-optimizer` +
   `code-reviewer`) and skill names it loads.
2. If every agent/skill it depends on was archived in Step 3 → **archive** the command too.
3. Always keep `core/`, `workflow/`, `review/` category commands — these are stack-agnostic entrypoints.

### 5. Compute keep-set for skills

Skills are mostly stack-agnostic authoring/process tools (sdd-*, create-agent, create-skill, component-model,
outcome-brief, session-checkpoint, sycophancy, standup-report, meeting-analysis, project-docs, kb-build,
agent-router) — **keep all of these by default**. Only archive a skill if it is tightly bound to an archived
domain with no generic use (e.g. `de-design-patterns` when no data-engineering stack is kept, `aws-diagrams`
when AWS isn't in the stack, `dataviz`/`diagram-design`/`excalidraw-diagram`/`visual-explainer` only if the user
explicitly wants a minimal footprint — ask before archiving these, since they're broadly useful).

### 6. Present the plan

Print a table: `KEEP` / `ARCHIVE` per agent, KB domain, command, and skill, with a one-line reason each
(e.g. "archived — kb_domains: [gcp, microsoft-fabric] have no overlap with keep-set {sql-patterns, python,
pydantic, testing, terraform, cloud-platforms}"). Total counts before/after. **Do not move anything yet.**

### 7. Apply (only with `--apply`, only after the user has seen and confirmed the plan)

- Create `.claude/_archive/<YYYYMMDD-HHMMSS>/` mirroring the original folder structure (`agents/`, `kb/`,
  `commands/`, `skills/`).
- `git mv` (if inside a git repo) or plain move each archived file/folder there — never delete outright.
- Write `.claude/_archive/<timestamp>/MANIFEST.md` listing what was archived, why, and the exact stack used for
  the decision, so `--restore` and future audits are self-explanatory.
- Update `.claude/kb/_index.yaml` to remove archived domains from the registry (keep a backup of the prior file
  in the archive folder).
- Report final counts and remind the user `--restore` undoes this.

### 8. Restore / purge

- `--restore`: find the most recent `.claude/_archive/*/`, move every file back to its original path per
  `MANIFEST.md`, restore `_index.yaml` from the backup, then delete the now-empty archive folder.
- `--purge <timestamp>`: confirm with the user explicitly (irreversible), then `rm -rf` that one archive folder
  only — never touch active `.claude/` content.

## Constraints

- Never archive `_template.md`, `README.md`, `_templates/`, `shared/`, or `settings.json` — these are structural,
  not stack-specific.
- Never delete anything on a first pass — archive only. Hard delete requires `--purge` and explicit confirmation.
- If a command or skill depends on an agent slated for archive, either archive them together or ask the user —
  never leave a dangling reference.
- Re-running `/prune-stack --apply` with a wider stack list should pull items back out of the most recent
  archive rather than creating overlapping archives — check `.claude/_archive/` first.

## See Also

- **Agent frontmatter schema**: `.claude/agents/README.md`
- **KB registry**: `.claude/kb/_index.yaml`
- **Component layering**: `.claude/skills/component-model/SKILL.md`
