---
name: extend-stack
description: Detect missing KB domains and agents for the project's actual tech stack, and build them using the same authoring patterns as the existing ones
---

# Extend Stack Command

> Companion to `/prune-stack`: instead of archiving what's unused, finds tools and resources the project
> actually runs that have no owning KB domain or agent yet, then builds them — reusing the detection method
> from `kb-coverage-audit` and the authoring methodology already codified in `kb-build` and `create-agent`.

## Usage

```bash
/extend-stack [--kb-only] [--agents-only] [--apply]
```

**Examples**: `/extend-stack` (dry-run, full report), `/extend-stack --apply` (build everything confirmed),
`/extend-stack --kb-only --apply`

- No flags → dry-run: detect gaps, print the build plan only, create nothing.
- `--kb-only` / `--agents-only` → limit detection and the plan to one half.
- `--apply` → after the user has seen and confirmed the plan, actually create the missing KB domains and agents.
  Must follow a dry-run the user confirmed — never the first call.

## What Happens

### 1. Detect the real stack and its KB gaps

Load the `kb-coverage-audit` skill and run its procedure unmodified — it already does the generalistic scan
(container images, dependency manifests, IaC, CI config, folder/README naming), the materiality filter, and the
near-miss-aware match against `.claude/kb/_index.yaml`. Take its output (covered tools, KB gaps, and the reason
any near-miss doesn't count) as this step's result. Don't re-implement stack detection here — one copy of that
method exists, in `kb-coverage-audit`.

Skip this step's KB half if `--agents-only` was passed.

### 2. Detect agent gaps

For every material tool `kb-coverage-audit` found (both KB-covered and KB-gap tools — a tool can have a KB
domain and still have no owning agent, or the reverse):

1. Read `.claude/skills/agent-router/routing.json`.
2. A tool is **agent-covered** if some agent's `name`, `description`, or `kb_domains` names the tool or its
   category.
3. Otherwise it's an **agent gap**.

Group agent gaps by category before proposing new agents — a whole observability stack (collector, metrics,
logs, traces, dashboards) typically needs one agent, not one per product inside it. Look at how existing agents
are scoped for the pattern (e.g. `fabric-logging-specialist` owns one platform's whole logging/monitoring
surface as a single agent, not five).

Skip this step if `--kb-only` was passed.

### 3. Present the combined plan

One table, most material gap first: `tool/category | KB status | agent status | proposed action`. KB status is
one of covered / gap / near-miss (with the one-line reason from step 1). Agent status is `covered by <name>` or
`gap`. Proposed action is `build KB domain <name>`, `build agent <name>`, both, or `skip (below materiality
threshold)`. **Create nothing yet.**

### 4. Apply (only with `--apply`, only after the user has confirmed the plan)

For each confirmed KB gap:
- Load the `kb-build` skill and follow it to produce a `--validated`, source-cited domain — match the rigor of
  the domains already in `.claude/kb/_index.yaml` (check a sibling domain's `mcp_validated` date and confidence
  scores as the bar to clear; this repo's existing domains are validated builds, not single-pass drafts).
- Register the new domain additively in `.claude/kb/_index.yaml`, per `kb-build`'s own registration step.

For each confirmed agent gap:
- Load the `create-agent` skill and follow its frontmatter contract (`name`, `description` with usage examples,
  `tier`, `model`, `tools`, `kb_domains` — pointing at the domain just built in this same run when applicable —
  `stop_conditions`, `escalation_rules`). Match the shape of the nearest existing agent in the same category
  (e.g. a new agent for a cloud-native tool should read like the sibling files in `.claude/agents/cloud/`, not
  invent a new frontmatter shape).
- Add the new agent to `.claude/skills/agent-router/routing.json` (`name`, `category`, `path`, `tier`, `model`,
  `description`, `kb_domains`, `escalates_to`). The router regenerates its behavior from this file — an agent
  with no entry here is invisible to routing regardless of the file existing on disk.

Report final counts (KB domains built, agents built, anything skipped and why) and remind the user that
`/prune-stack` is the inverse operation for anything that stops being relevant later.

## Constraints

- **Detect, don't guess.** Every proposed KB domain or agent must trace back to a tool `kb-coverage-audit`
  actually found in this run — never propose one from a category the project doesn't run.
- **Match existing rigor.** New KB domains follow `kb-build`'s validated methodology; don't take a shortcut a
  sibling domain didn't take.
- **Match existing shape.** New agents copy the frontmatter contract and tier/model conventions of the nearest
  existing agent in the same category.
- **One agent per category, not per tool**, unless the tools in a category are genuinely unrelated in practice —
  ask if unsure rather than guessing a split.
- **Never skip the dry-run.** `--apply` with no prior plan shown to the user is refused; run without flags
  first.
- **Registration is mandatory, not optional.** A KB domain not added to `_index.yaml`, or an agent not added to
  `routing.json`, does not count as done.

## See Also

- **Detection + KB gap method**: `.claude/skills/kb-coverage-audit/SKILL.md`
- **KB build methodology**: `.claude/skills/kb-build/SKILL.md`
- **Agent authoring conventions**: `.claude/skills/create-agent/SKILL.md`
- **Inverse operation**: `.claude/commands/core/prune-stack.md`
- **Agent registry**: `.claude/skills/agent-router/routing.json`
- **KB registry**: `.claude/kb/_index.yaml`
