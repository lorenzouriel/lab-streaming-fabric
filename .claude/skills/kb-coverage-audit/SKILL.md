---
name: kb-coverage-audit
description: |
  Scans a project's real technology footprint (container images, Dockerfiles,
  dependency manifests, IaC providers, CI config, top-level infra folders) and diffs
  it against the KB domains registered in .claude/kb/_index.yaml, reporting which
  tools and resources actually in use have no corresponding KB domain, including
  near-misses where an existing domain sounds related but its description does not
  actually cover the tool. Works generically on any project's stack, not tied to a
  fixed tool list. Use when the user asks what is missing from the knowledge base,
  whether the KB covers the real stack, wants a gap report before building new KB
  domains, or asks something like "what are we using that has no KB." Do not use for
  auditing the internal health of existing KB content such as staleness, file-size
  limits, or orphaned concepts -- that is kb-architect; do not use to build a KB
  domain once a gap is identified -- that is kb-build / /create-kb.
---

# KB Coverage Audit

Read-only gap analysis: what does this project actually run, and which of that has
no KB domain backing it. Produces a ranked report, never edits `.claude/kb/`.

## When to use vs. neighbors

| Ask | Skill |
|---|---|
| "What tools have no KB coverage?" / "Does the KB match our real stack?" | this skill |
| "Is the KB well organized / any stale or oversized files?" | `kb-architect` agent |
| "Build the missing domain" | `kb-build` skill / `/create-kb` command |

## Procedure

### 1. Inventory the project's real stack

Scan the repository root, excluding `.claude/`, `.git/`, and dependency/build output
directories (`node_modules/`, `vendor/`, `dist/`, `.venv/`, `target/`, etc.). Look for
the signal sources in `references/detection-signals.md` — container/infra files,
language dependency manifests, IaC provider blocks, CI config, and top-level
folder/README naming. Don't assume the signal list there is exhaustive; if the
project uses a manifest format not listed, still read and normalize it.

For each tool or resource found, record: **name**, **where it appears** (file path),
and **category** (database, orchestration, observability, storage, query engine,
language/runtime, cloud service, IaC, CI, etc.).

### 2. Filter for materiality

Not everything in a manifest deserves its own KB domain. Keep a tool only if it meets
at least one:

- It has a dedicated top-level directory, config folder, or its own README in the repo.
- It is a primary service in a compose/orchestration file (has its own container,
  is addressed by other services), not a disposable sidecar.
- The user's own request named it.

Drop or de-prioritize: base/utility images (`alpine`, `busybox`), one-off exporters,
test-only or dev-only dependencies, transitive libraries pulled in by a framework
rather than chosen deliberately. When unsure whether something is material, keep it
but rank it last rather than silently dropping it — let the user see the judgment
call.

### 3. Read the KB registry as source of truth

Read `.claude/kb/_index.yaml`. For each domain, take its `description` field, not
just its folder name — folder names undersell or oversell scope. If the file is
large, the domain list plus descriptions is what matters; skip reading individual KB
markdown files unless a match is genuinely ambiguous.

### 4. Match stack items against domains, two ways

For every material tool from step 2:

1. **Direct hit** — a domain's name or description literally names the tool or its
   category. Coverage confirmed, no further action.
2. **Near-miss check** — a domain sounds adjacent (same broad category) but read its
   description scope carefully before crediting it. Common false-positives to check
   for explicitly:
   - A cross-dialect/generic SQL domain (query syntax) does not cover a specific
     RDBMS product's administration, HA/replication, or vendor-specific ops.
   - A managed cloud-vendor domain (e.g. a hosted product's own KB) does not cover a
     self-hosted or open-source alternative in the same category, even if both are
     "S3-compatible" or "Postgres-based."
   - A framework/language domain does not cover the infrastructure that framework
     happens to run on top of.
   - An orchestration domain covering the scheduler's DAG/task patterns does not
     automatically cover the scheduler's own backing services (its broker, metadata
     DB) when those are deployed as distinct, separately-configured components.
   If a domain fails the near-miss check, treat the tool as **not covered** and state
   the one-line reason why the near-miss doesn't count — this is the part manual
   skimming gets wrong, so make the reasoning explicit rather than crediting on
   category-name resemblance alone.

Anything that is neither a direct hit nor survives the near-miss check is a gap.

### 5. Cross-check against agents (optional corroboration, not required for a gap)

If `.claude/skills/agent-router/routing.json` exists, check whether any agent's
`kb_domains` references the tool, and whether any agent's description/name targets
it. This doesn't change step 4's verdict — a tool can lack an owning agent while
still having KB coverage, or vice versa — but note it when an entire category (KB
domain *and* agent) is absent together, since that's the strongest signal of a real
blind spot rather than a naming gap.

### 6. Report

Rank by materiality and blast radius, most significant first:

- Lead with the single biggest gap: a whole infra/category with zero coverage
  (no domain, ideally call out if also no agent) beats several small partial gaps.
- For each gap, give: tool, where it's used, closest existing domain (or "none"),
  and — for near-misses — the specific reason that domain doesn't count.
- Keep low-materiality items out of the main table; mention them in one line at the
  end if at all.
- Close with a recommended next step naming the highest-priority domain to build,
  pointing at `kb-build` / `/create-kb --validated` — but do not build it yourself
  unless asked. This skill only reports; it never writes to `.claude/kb/`.

## Guardrails

- **Read-only.** Never create, edit, or scaffold KB files, agents, or skills as part
  of this audit.
- **Generalistic.** Do not hardcode tool names, folder paths, or a fixed stack list
  from any one project. Every tool in the report must come from something actually
  found in this run's scan, not from memory of a previous project.
- **Empty/minimal project.** If the scan finds no material stack signals (e.g. a
  brand-new or docs-only repo), say so plainly instead of forcing a report.
- **Registry is the source of truth, not folder names.** A KB folder existing on disk
  without a matching, accurate `_index.yaml` description should not be credited as
  coverage — flag the mismatch instead.

## References

| Resource | When to read |
|---|---|
| `references/detection-signals.md` | Step 1 — the per-ecosystem list of files/patterns that reveal real tool usage |
| `.claude/kb/_index.yaml` | Step 3 — always, it's the coverage source of truth |
| `.claude/skills/kb-build/SKILL.md` | Handing off a confirmed gap to get a domain built |
| `.claude/agents/architect/kb-architect.md` | The neighboring "is the KB healthy" audit, not "does it cover the stack" |
