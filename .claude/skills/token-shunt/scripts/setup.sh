#!/usr/bin/env bash
# Usage: setup.sh [--backend openrouter|gemini|ollama] [--project DIR] [--min-lines N] [--no-sdd-allow]
# Installs token-shunt into a project: copies scripts to .claude/shunt/, merges hooks + env into
# .claude/settings.json (idempotent), and gitignores the log/bypass files. Never writes API keys.
set -eu

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend="openrouter"; project="$PWD"; min_lines=350; sdd_allow=1
while [ $# -gt 0 ]; do
  case "$1" in
    --backend)      backend="${2:-}"; shift 2;;
    --project)      project="${2:-}"; shift 2;;
    --min-lines)    min_lines="${2:-}"; shift 2;;
    --no-sdd-allow) sdd_allow=0; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
command -v jq >/dev/null 2>&1 || { echo "setup: jq is required" >&2; exit 1; }
if [ "$backend" = claude-plan ]; then
  command -v claude >/dev/null 2>&1 || { echo "setup: claude CLI is required for claude-plan" >&2; exit 1; }
else
  command -v curl >/dev/null 2>&1 || { echo "setup: curl is required" >&2; exit 1; }
fi

case "$backend" in
  openrouter) base="https://openrouter.ai/api/v1";                            model="google/gemini-2.5-flash"; keyvar="OPENROUTER_API_KEY";;
  gemini)     base="https://generativelanguage.googleapis.com/v1beta/openai"; model="gemini-2.5-flash";        keyvar="GEMINI_API_KEY";;
  ollama)     base="http://localhost:11434/v1";                               model="qwen2.5-coder";           keyvar="";;
  claude-plan) base=""; model="haiku"; keyvar="";;
  *) echo "setup: unknown backend '$backend'" >&2; exit 2;;
esac

dest="$project/.claude/shunt"
mkdir -p "$dest"
for f in _common.sh bulk-read.sh code-write.sh check-file-size.sh check-bash-read.sh status.sh; do
  [ -f "$src/$f" ] || { echo "setup: missing $src/$f" >&2; exit 1; }
  cp "$src/$f" "$dest/$f"
  chmod +x "$dest/$f"
done

settings="$project/.claude/settings.json"
[ -f "$settings" ] || echo '{}' > "$settings"
tmp=$(mktemp)
jq --arg backend "$backend" --arg base "$base" --arg model "$model" --arg keyvar "$keyvar" --arg min "$min_lines" \
   --argjson sdd "$sdd_allow" '
  def entry(matcher; script): {matcher: matcher, hooks: [{type: "command", command: ("bash \"$CLAUDE_PROJECT_DIR/.claude/shunt/" + script + "\"")}]};
  .env = (((.env // {}) | del(.SHUNT_BASE_URL, .SHUNT_MODEL, .SHUNT_KEY_VAR, .SHUNT_BACKEND, .SHUNT_WORKER_MODEL, .SHUNT_READER_MODEL, .SHUNT_WRITER_MODEL)) + (
      if $backend == "claude-plan" then
        {SHUNT_MIN_LINES: $min, SHUNT_BACKEND: "claude-plan", SHUNT_READER_MODEL: "haiku", SHUNT_WRITER_MODEL: "sonnet", SHUNT_TIMEOUT: "60"}
      else
        {SHUNT_MIN_LINES: $min, SHUNT_BACKEND: "http", SHUNT_BASE_URL: $base, SHUNT_MODEL: $model, SHUNT_KEY_VAR: $keyvar, SHUNT_TIMEOUT: "30"}
      end))
  | (if $sdd == 0 then .env.SHUNT_ALLOW_PATHS = "*/CLAUDE.md,*/SKILL.md" else . end)
  | .hooks.PreToolUse = (
      ((.hooks.PreToolUse // []) | map(select((.hooks // []) | any(.command | tostring | contains("/shunt/")) | not)))
      + [entry("Read"; "check-file-size.sh"), entry("Bash"; "check-bash-read.sh")]
    )' "$settings" > "$tmp"
mv "$tmp" "$settings"

gi="$project/.gitignore"
touch "$gi"
for line in ".claude/shunt/shunt.log" ".claude/shunt/bypass" ".env"; do
  grep -qxF "$line" "$gi" || echo "$line" >> "$gi"
done

echo "token-shunt installed in $project"
if [ "$backend" = claude-plan ]; then echo "  backend : claude-plan (reader: haiku, writer: sonnet)"; else echo "  backend : $backend ($model)"; fi
echo "  hooks   : Read + Bash in .claude/settings.json (threshold ${min_lines} lines)"
if [ "$backend" = claude-plan ]; then
  echo "  next    : nothing to configure (uses your logged-in Claude plan); start a new Claude session"
elif [ -n "$keyvar" ]; then
  echo "  next    : add ${keyvar}=<your key> to $project/.env (setup never writes keys), then start a new Claude session"
else
  echo "  next    : make sure Ollama is running with model '$model', then start a new Claude session"
fi
echo "  note    : file contents are sent to the backend; sensitive patterns (.env, *.pem, *secret*...) are excluded"
