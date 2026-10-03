---
description: Show and drive the SDD task board — show columns, pick next unblocked task, move status, check dependencies, export HTML
argument-hint: <show|next|move|check|html|list> [feature-name] [task-id] [status]
allowed-tools: Read, Glob, Bash(python .claude/skills/sdd-board/board.py:*)
---

# /workflow:board

Load `.claude/skills/sdd-board/SKILL.md` and follow it.

Args: `$ARGUMENTS`

| Input | Action |
|-------|--------|
| *(empty)* or `list` | `board.py list`; then ask which feature to show |
| `show <feature>` | `board.py show <feature>` |
| `next <feature>` | `board.py next <feature>` — print unblocked tasks; if several, note they can run in parallel |
| `move <feature> <id> <status> [--note ...]` | `board.py move ...` — relay the script's error verbatim on refusal; never retry with `--force` unless the user says so |
| `check <feature>` | `board.py check <feature>` |
| `html <feature>` | `board.py html <feature>`, then print the file path |

Read-only except `move`. To create tasks use `/workflow:breakdown`; to execute them use `/workflow:build`.
