---
name: sync-stack
description: |
  Update a project's copied .claude/ commands and skills from the master-claude GitHub repo
  (engineer/.claude) — fetches upstream, diffs against the local copy, and applies only what
  changed without clobbering local edits or items removed by prune-stack. Use inside a project
  that holds a copy of engineer/.claude when the user says "sync the stack", "update my
  .claude from master-claude", "pull latest skills/commands", or "my stack is outdated".
  Do not use inside the master-claude repo itself (it is the source).
---

# Sync Stack

Pulls upstream changes of `skills/` and `commands/` from `https://github.com/lorenzouriel/master-claude` (`engineer/.claude`) into the current project's `.claude/`. Scope is fixed to `skills/` and `commands/`; agents, KB, SDD artifacts and settings are never touched.

Run from the **project root** (the folder containing `.claude/`). Requires `git` and `python`.

## Flow

1. **Plan (read-only)**:
   ```bash
   python .claude/skills/sync-stack/scripts/sync.py
   ```
   Clones upstream to a temp dir and prints: NEW, UPDATE, CONFLICT, KEEP, REMOVED, SKIPPED, plus upstream commits since last sync.
2. Summarize the plan to the user. Ask before writing.
3. **Apply safe changes** (NEW + UPDATE only):
   ```bash
   python .claude/skills/sync-stack/scripts/sync.py --apply
   ```
4. **Conflicts** (local edited AND upstream changed): never overwrite silently. For each, run `--diff PATH`, show the user, then ask: keep local / take upstream / merge by hand.
   - take upstream: `--take PATH` (old version saved under `.claude/_sync-backup/<ts>/`)
   - keep local permanently: add a path glob to `ignore` in `.claude/.master-claude-sync.json`
   - merge by hand: edit the file, then `--take` is not needed; it stays listed as a conflict until upstream equals local or it is ignored
5. Files removed upstream are only listed. Delete unmodified ones with `--apply --prune` if the user agrees.

## Rules

- Change detection is 3-way: `.claude/.master-claude-sync.json` stores the upstream hash per file at last sync. `local == stored` → safe update; `local != stored` and upstream changed → conflict; local-only edits are kept.
- **First sync** (no manifest): files equal to any historical upstream version are safe updates; files matching none are conflicts. Files missing locally are NOT installed (they may be pruned) unless `--add-new`.
- Files missing locally but known from a previous sync, or present in `.claude/_archive/` (prune-stack), are skipped — never re-added.
- Local-only files (not upstream) are never touched.
- Commit `.claude/.master-claude-sync.json` with the project so the base is shared.

## Options

| Flag | Effect |
|---|---|
| `--apply` | write NEW + UPDATE, record commit |
| `--add-new` | first sync: also install files missing locally |
| `--prune` | with `--apply`, delete unmodified files removed upstream |
| `--take PATH...` | overwrite conflicted files with upstream (backed up) |
| `--diff PATH...` | unified diff local → upstream |
| `--ref REF` | branch/tag/commit (default remote HEAD) |
| `--repo URL` | fork/alternate source (or env `MASTER_CLAUDE_REPO`) |

Paths are relative to `.claude/`, e.g. `skills/create-skill/SKILL.md`.
