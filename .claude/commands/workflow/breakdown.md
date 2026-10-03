---
description: Decompose an approved feature (brainstorm + define + design) into implementation-ready stories with Description, Actual Plan, Architecture, and Acceptance Criteria
argument-hint: [feature-name]
allowed-tools: Read, Write, Grep, Glob, Bash(git log:*), Bash(git diff:*), Bash(python .claude/skills/sdd-board/board.py:*)
---

# /workflow:breakdown

You are running the **breakdown** phase of the SDD workflow:

`/workflow:brainstorm → define → design → breakdown → build → ship`

Breakdown converts the approved design into a dependency-ordered set of stories, written as **task files on the SDD board** (`.claude/skills/sdd-board/SKILL.md` owns the file contract, statuses, and script). Each story must be independently implementable, independently mergeable, and specific enough that `/workflow:build` can execute it without re-reading the design doc.

## Inputs

Feature: `$ARGUMENTS` (if empty, ask which feature under `sdd/features/` to break down).

1. Read, in order:
   - `sdd/features/$ARGUMENTS/brainstorm.md`
   - `sdd/features/$ARGUMENTS/define.md` (PRD — sections, open questions, decisions)
   - `sdd/features/$ARGUMENTS/design.md`
2. **Read the actual source files the design touches.** This is mandatory, not optional. Every plan step must cite real file paths and real line numbers (`consumer/src/index.ts:247`), verified against the current working tree — never against your memory of the design doc. If the design references code that has since moved, cite the current location and note the drift.
3. If `define.md` or `design.md` is missing or has unresolved blocking questions, STOP and tell the user to complete that phase first. Do not invent answers to fill the gap.

## Preconditions check

Before writing any story, verify:

- [ ] Design doc has an approved architecture (not "Option A vs Option B" still open)
- [ ] All open questions in define.md are either resolved or explicitly deferrable
- [ ] The codebase areas the design touches actually exist as described

Deferrable open questions do NOT block breakdown — they get flagged inside the affected story (see Open Question Handling below).

## Story sizing and ordering rules

- **One story = one mergeable PR.** If a story can't ship alone without breaking main, it's sized wrong — split or merge.
- **Dependency-ordered.** Story 1 is the foundation everything else calls into (shared module, schema change, interface change). Later stories name their prerequisites explicitly: *"This story is a prerequisite for Story 5's EndToEndLatency."*
- **Group by seam, not by layer.** A story owns a behavior end-to-end (instrumentation point + its tests), not "all the tests" or "all the types."
- **Every story that adds behavior adds or extends a test file.** Name the test file, name the framework, and match the existing test idiom in the repo (e.g., "vitest, matching the describe/it/expect style in `consumer/src/tests/serializer.test.ts`"). If no test file exists for the touched module, the story creates one and says so.
- **Respect existing conventions.** If the repo logs via `console.log` only, the story says so and conforms. New patterns (new dependencies, new taxonomies, new idioms) require an explicit design-doc citation — otherwise reuse what exists: *"reason strings derived 1:1 from the existing 'DROPPED ...' log text — no new taxonomy invented."*
- Typical feature: 3–8 stories. If you produce more than 10, the feature was under-scoped at `/define` — flag it instead of writing 15 stories.

## Open Question Handling

When a plan step depends on an unresolved open question from `define.md`:

1. Propose a concrete default inline (never leave a blank).
2. Tag it back to the source: *"(proposed `Panopto/CaliperPublisher` per Open Question #1 — confirm at /define before hardcoding)"*.
3. Pick the default that keeps the system observable/safe (e.g., emit `0` rather than skip emission, fail loud rather than silently degrade).

## Output format

Write **one task file per story** to `sdd/board/$ARGUMENTS/S{NN}-{slug}.md` (there is no `stories.md`; the board is the source of truth). Each file starts with board frontmatter, then exactly the four sections below.

Frontmatter (flat `key: value`, per the `sdd-board` skill):

```yaml
---
id: S01
feature: $ARGUMENTS
title: "<short imperative title>"
status: ready        # ready when depends_on is empty, else backlog
depends_on: []       # e.g. [S01, S03] — must mirror the prose dependencies
agent: <specialist from the DESIGN file manifest, or empty>
files: [<primary files touched>]
updated: <today, YYYY-MM-DD>
---
```

For **each** story, the body is exactly these four sections (the `## Story N:` heading is replaced by the frontmatter `title`):

```markdown
## Story N: <short imperative title> (<primary files touched>)

**Description:** 2–4 sentences. What this story delivers, why it exists,
and its position in the dependency chain ("This is the foundation — no
other story can land before this one merges." / "Prerequisite for Story 5").

**Actual Plan**

- Numbered or bulleted concrete steps. Each step names the exact file,
  function, and line range it touches (`enrichment.ts:85-88`).
- Call out exact function signatures being added or changed, including
  every call site that must be updated (list them by file:line).
- Name constants, metric names, slugs, env vars verbatim.
- Include the test-file step with the specific cases it must cover.
- Flag open-question defaults per Open Question Handling.

**Architecture**

ASCII flow diagram of this story's slice only — data/control flow through
the touched components, annotated with the new behavior in brackets:
[EventsConsumed++], → EventsDropped{reason=empty-message}. Keep it under
~15 lines. No boxes-and-arrows art for trivial one-file changes; a 3-line
call chain is fine.

**Acceptance Criteria**

- [ ] Checkboxes only. Each one independently verifiable by a reviewer.
- [ ] Include positive criteria (behavior exists, fires exactly once)
- [ ] Include negative criteria (no double-counting, zero new npm
      dependencies, existing log text unchanged)
- [ ] Include the test-coverage criterion naming the test file
```

### Quality bar for Acceptance Criteria

Bad: "Metrics work correctly."
Good: "`EventsDropped` fires exactly once per dropped invocation, using one of the 7 documented reason values."

Every criterion must be falsifiable by reading a diff or running the test suite. "Exactly once" semantics, unchanged-behavior guarantees, and dependency constraints are first-class criteria, not afterthoughts.

## After writing

1. Run `python .claude/skills/sdd-board/board.py check $ARGUMENTS`. It must print `ok` — fix cycles, unknown ids, or dependency mismatches before continuing.
2. Run `board.py show $ARGUMENTS` and print it, plus a one-line summary table: story id, title, files touched, depends-on.
3. List every open-question flag embedded in the stories so the user can resolve them at `/define` in one pass.
4. Ask whether to proceed to `/workflow:build` (it starts from `board.py next`) or revise.

Do NOT start implementing. Breakdown ends with a passing board. If a board already exists for the feature, do not overwrite tasks that are past `backlog`/`ready`: reconcile — add new tasks, and mark stale ones `blocked` with `--note`.