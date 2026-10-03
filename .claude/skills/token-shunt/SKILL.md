---
name: token-shunt
description: |
  Cuts Claude Code token usage by routing bulk I/O to a cheap worker model (Gemini Flash via
  OpenRouter, Gemini API, or local Ollama), modeled on Spotify's Shunt plugin. PreToolUse hooks
  block whole-file Read and cat/head/tail on files over 350 lines; Claude then delegates with
  bulk-read.sh (files in, bullets with file:line out) or code-write.sh (spec in, file on disk out,
  code never enters context). Use to set up or operate the shunt: "reduce token usage", "cut Claude
  Code cost", "install token-shunt", "shunt status", "delegate large file reads", or when a hook
  message says BLOCKED by token-shunt. Works under the SDD workflow. Do not use for editing,
  debugging or reasoning tasks, and do not use on repositories whose contents must not leave the machine unless the backend is local Ollama.
---

# Token Shunt

Most agent work is I/O, not reasoning. Reading a 1,800-line file costs ~22k tokens that are then re-sent every turn. The shunt sends bulk reads and boilerplate writes to a cheap model and returns only a short summary or a file path.

## Commands

| Command | Action |
|---|---|
| `/token-shunt setup` | Install into the current project (below) |
| `/token-shunt status` | Run `bash .claude/shunt/status.sh` and report the numbers |
| `/token-shunt off` | `touch .claude/shunt/bypass` disables the hooks for 10 min. To remove entirely, delete the two `/shunt/` entries under `hooks.PreToolUse` in `.claude/settings.json` |

## Setup flow

1. Confirm the working directory is the project to instrument (not the lab repo root, whose `.claude/` holds only local settings).
2. Ask the user (AskUserQuestion) for the backend:
   - `claude-plan` (headless `claude -p` on the user's logged-in plan: Haiku reads, Sonnet writes code; no key, data stays with Anthropic; consumes plan usage)
   - `openrouter` (reuses `OPENROUTER_API_KEY`, same as the `judge` skill)
   - `gemini` (direct Gemini API, `GEMINI_API_KEY`)
   - `ollama` (local; nothing leaves the machine)
3. Warn once: file contents are sent to the chosen backend (for `claude-plan`, to Anthropic, as in normal use). Sensitive names (`.env`, `*.pem`, `*secret*`, `*credential*`, `*.tfstate`, `*.tfvars`) are excluded automatically. For confidential client code, recommend `ollama`.
4. Run `bash <skill-dir>/scripts/setup.sh --backend <choice> --project "$PWD"`. Add `--no-sdd-allow` only if the user wants SDD documents shunted too.
5. For key-based backends, tell the user to add the API key to `.env` themselves. Never ask for, echo, or write the key. `claude-plan` needs nothing.
6. Tell the user to start a new session (hooks load at session start; in VS Code, reload the window or open a new chat).
7. Smoke test in the new session: read any file over 350 lines, expect a BLOCKED message, follow it with `bulk-read.sh`, then run `/token-shunt status`.

`setup.sh` is idempotent. It copies scripts to `.claude/shunt/`, merges `env` and two `PreToolUse` hooks into `.claude/settings.json` without touching existing entries, and gitignores the log, bypass file and `.env`. Requires `jq` and `curl` (Git Bash on Windows; keep scripts LF-ended, e.g. `*.sh text eol=lf` in `.gitattributes`).

## Operating rules (when a hook blocks you)

- **Understand or search a big file** → `bash "$CLAUDE_PROJECT_DIR/.claude/shunt/bulk-read.sh" "<specific question>" file1 file2 ...`. Ask narrow questions; see `references/worker-prompts.md`.
- **Edit a big file** → summaries lack reliable line numbers. Read only the region with `Read` (`offset` and `limit`), then `Edit`. Any read with `offset` or `limit` passes the hook.
- **Boilerplate** (tests, DTOs, scaffolds, config) → `bash "$CLAUDE_PROJECT_DIR/.claude/shunt/code-write.sh" --spec "..." --ref <similar file> --out <path>`. Never use it for logic the DESIGN specifies. Run tests/linters afterwards and read only failures.
- **Reasoning, debugging, architecture** → do it yourself; do not delegate.
- **Worker failed** → the script re-enables direct reads for 10 minutes and says so. Read the file directly.

## SDD integration

The hooks are tool-level, so `/workflow:*` phases and their subagents get the shunt without changes.

- `.claude/sdd/`, `.claude/kb/`, skills, agents, commands, `CLAUDE.md` are allowlisted (`SHUNT_ALLOW_PATHS`). Phase documents must be read verbatim.
- Design phase: use `bulk-read` for codebase pattern exploration across many files.
- Build phase: `code-write` for mechanical boilerplate only; logic stays with the specialist agents named in DESIGN.

## Configuration (`.claude/settings.json` → `env`)

| Variable | Default | Purpose |
|---|---|---|
| `SHUNT_MIN_LINES` | 350 | Read/cat threshold |
| `SHUNT_BACKEND` | `http` | `http` (OpenAI-compatible) or `claude-plan` |
| `SHUNT_BASE_URL` / `SHUNT_MODEL` / `SHUNT_KEY_VAR` | per backend | `http` only: endpoint, model, name of the env var holding the key |
| `SHUNT_READER_MODEL` | `haiku` (`claude-plan`); else `SHUNT_MODEL` | Model for `bulk-read` |
| `SHUNT_WRITER_MODEL` | `sonnet` (`claude-plan`); else `SHUNT_MODEL` | Model for `code-write` (code quality matters more than for summaries) |
| `SHUNT_TIMEOUT` | 30 (60 for `claude-plan`) | Seconds per delegation |
| `SHUNT_ALLOW_PATHS` | SDD, KB, skills, agents, commands | Comma-separated globs never blocked |
| `SHUNT_DENY_PATTERNS` | secrets list | Never sent to the worker |
| `SHUNT_BYPASS=1` | unset | Disable hooks for a session |

## Limits

Each delegation is a network round-trip of roughly 10–30 s, so it only pays off for large or multi-file reads. Savings quoted by Spotify (~90% on bulk reads) come from a Java monorepo; measure yours with `/token-shunt status`. Worker output is a summary and can miss details: re-ask narrower or read a range before acting on it.
