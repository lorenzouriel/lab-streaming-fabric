---
description: Validate stories against brainstorm/define/design (pre-build) or validate the built code against the stories (post-build). Produces a verdict report — never edits code or stories.
argument-hint: [feature-name] [--mode spec|build|auto]
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git diff:*), Bash(git show:*), Bash(npm test:*), Bash(npx vitest:*)
---

# /workflow:validate

You are running the **validate** phase of the SDD workflow:

`/workflow:brainstorm → define → design → breakdown → [validate] → build → [validate] → ship`

Validate is an **auditor, not a fixer**. It reads, checks, and produces a verdict report. It never edits stories, never edits code, never resolves open questions itself. Findings route back to the phase that owns them (`/define`, `/breakdown`, `/build`, or `/iterate`).

## Mode selection

Feature: first argument (if empty, ask which feature under `sdd/features/`).

- `--mode spec` → run Part A only (stories vs. brainstorm/define/design)
- `--mode build` → run Part B only (built code vs. stories)
- `--mode auto` (default) → inspect story status: if no story is marked done/merged, run spec mode; if some or all are done, run build mode for the done ones AND re-run spec mode for the not-yet-built ones (the design may have drifted since breakdown).

Inputs to read in every mode:
- `sdd/features/<feature>/brainstorm.md`
- `sdd/features/<feature>/define.md`
- `sdd/features/<feature>/design.md`
- `sdd/board/<feature>/S*.md` (the stories; task files are the source of truth, statuses via `board.py show <feature>`)
- The current working tree for every file the stories reference

---

## Part A — Spec fidelity (stories vs. brainstorm + define + design)

Goal: prove the stories are a complete, faithful, buildable decomposition of what was approved — nothing dropped, nothing invented.

### A1. Coverage — nothing dropped
For every requirement, behavior, metric, component, or decision in define.md and design.md, find the story that implements it. Build a traceability table:

| Spec item (source §) | Story | Covered? |
|---|---|---|

Any spec item with no story → **FAIL: dropped scope**. List them.

### A2. Provenance — nothing invented
For every story plan step, trace it back to a design/define section. Steps with no traceable source are either (a) legitimate implementation detail (fine — mark as such) or (b) invented scope: new features, new dependencies, new taxonomies, behavior changes the design never asked for → **FAIL: scope creep**. The test: would the design author be surprised by this step?

### A3. Reference accuracy — nothing stale
- Every `path:line` / `path:start-end` in the stories: file exists, range is in bounds, and the code at that location matches what the plan step claims is there (function name, log text, branch condition). Refs drift as main moves — verify against the tree NOW, not the doc's authoring date.
- Every named function signature, constant, metric name, env var: consistent across all stories and consistent with design.md (e.g., namespace spelled identically everywhere).

### A4. Dependency integrity
- depends-on forms a DAG; Story 1 has no dependencies; no reference to a nonexistent story.
- Data threaded between stories actually connects: if Story 3 says it "feeds Story 5," Story 5's plan must consume exactly what Story 3 produces (parameter names, shapes).

### A5. Open-question reconciliation
- Every open-question flag in stories maps to a real question in define.md.
- Flagged questions still open → surface as **BLOCKER for the affected story** (not the whole feature).
- Questions resolved in define.md since breakdown → check the story's proposed default matches the resolution; mismatch → **FAIL: stale default**.

### A6. Acceptance-criteria quality
- Every criterion falsifiable by reading a diff or running tests.
- Every story has ≥1 negative criterion (no double-counting, zero new deps, existing behavior unchanged) and ≥1 test-file criterion.
- Flag weasel criteria: "works correctly", "handles properly", "is performant" → **FAIL: unverifiable AC**.

---

## Part B — Build fidelity (built code vs. stories)

Goal: prove the implementation is exactly what the stories promised — each criterion verified against real code, not against the builder's summary.

Scope: tasks with `status: done` or `review` on the board (`board.py show <feature>`); also run `board.py check <feature>` and report any problem it prints as a finding. Use `git log`/`git diff` to locate the implementing commits when helpful, but the source of truth is the current tree.

### B1. Acceptance criteria, one by one
For every checkbox in every done story, verify it against the code and record a verdict with evidence:

| Story | Criterion | Verdict | Evidence (file:line / test name / diff) |
|---|---|---|---|

Verdicts: **PASS** / **FAIL** / **UNVERIFIABLE** (criterion can't be checked from the tree — that's an A6 failure that leaked through; say so).
- "Fires exactly once" claims: trace every code path to the call site and prove no path double-fires and no path skips.
- "Unchanged" claims: diff the relevant lines against pre-feature state (`git diff <base>...HEAD -- <file>`); any drift in supposedly-untouched text → **FAIL**.
- "Zero new dependencies": diff package.json / lockfile against base.

### B2. Plan conformance
Compare each story's Actual Plan step against the implementation. Deviations are not automatically failures — classify them:
- **Equivalent** — different mechanics, same behavior and constraints. Note it.
- **Improvement** — better than planned, still within design intent. Note it; suggest updating the story so the artifact stays truthful.
- **Violation** — breaks a design constraint, convention rule, or another story's contract → **FAIL**.

### B3. Tests
- Every test file the stories promised exists and covers the named cases (read the test file; don't trust its filename).
- Run the suite for touched modules if the environment allows (`npm test` / `npx vitest related`). Failures → **FAIL** with output.
- Check the tests actually assert the criteria (a test file that exists but asserts nothing meaningful is a FAIL, not a PASS).

### B4. Blast radius
- `git diff --stat <base>...HEAD`: every changed file must belong to some story's touched-files list. Changes outside story scope → **FAIL: undocumented change** (route to /iterate to either revert or amend the story).
- Conventions hold: logging idiom, naming, no stray debug code, no commented-out blocks.

---

## Output — the verdict report

Write `sdd/features/<feature>/validation-report.md` AND print a summary. Structure:

1. **Verdict line**: `READY FOR BUILD` / `READY FOR SHIP` / `BLOCKED` — with a one-sentence reason.
2. **Findings table**, ordered by severity:
   - **BLOCKER** — cannot proceed to next phase (dropped scope, failed AC, unresolved open question on an in-scope story)
   - **FAIL** — must fix, but scoped to one story
   - **WARN** — should fix (stale line ref that still points at the right code, weasel AC on a done story)
   - **NOTE** — equivalent/improvement deviations, suggestions
3. **Routing**: for each BLOCKER/FAIL, name the command that owns the fix — `/define` (open questions, scope decisions), `/breakdown` (story defects), `/build` or `/iterate` (code defects). Never fix it yourself.
4. **Traceability + AC verdict tables** as appendices.

Do not soften verdicts. A feature with one BLOCKER is BLOCKED — there is no "mostly ready." If everything passes, say so in one line and stop; do not manufacture findings to look thorough.