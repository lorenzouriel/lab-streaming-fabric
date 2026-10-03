#!/usr/bin/env bash
# Shared helpers for token-shunt scripts. Sourced, never executed.

SHUNT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
SHUNT_DIR="$SHUNT_ROOT/.claude/shunt"
SHUNT_LOG="$SHUNT_DIR/shunt.log"

: "${SHUNT_MIN_LINES:=350}"
: "${SHUNT_BASE_URL:=https://openrouter.ai/api/v1}"
: "${SHUNT_MODEL:=google/gemini-2.5-flash}"
: "${SHUNT_KEY_VAR=OPENROUTER_API_KEY}"   # no colon: an empty value means "no key" (Ollama)
: "${SHUNT_BACKEND:=http}"                 # http (OpenAI-compatible) | claude-plan (headless claude -p)
: "${SHUNT_READER_MODEL:=}"               # per-role model for bulk-read (claude-plan default: haiku)
: "${SHUNT_WRITER_MODEL:=}"               # per-role model for code-write (claude-plan default: sonnet)
: "${SHUNT_TIMEOUT:=30}"
: "${SHUNT_TEMPERATURE:=0.2}"
: "${SHUNT_MAX_BYTES:=800000}"
: "${SHUNT_BYPASS_MINUTES:=10}"
: "${SHUNT_ALLOW_PATHS:=*/.claude/sdd/*,*/.claude/kb/*,*/.claude/skills/*,*/.claude/agents/*,*/.claude/commands/*,*/CLAUDE.md,*/SKILL.md}"
: "${SHUNT_DENY_PATTERNS:=.env,.env.*,*.pem,*.key,*.pfx,*.p12,id_rsa*,*secret*,*credential*,*.tfstate,*.tfvars}"

shunt_unix_path() {
  local p="${1//\\//}"
  if command -v cygpath >/dev/null 2>&1; then cygpath -u "$p" 2>/dev/null || printf '%s' "$p"; else printf '%s' "$p"; fi
}

shunt_norm_path() { printf '%s' "${1//\\//}"; }

# shunt_env NAME -> value from environment, else from project .env
shunt_env() {
  local key="$1" val="${!1:-}"
  if [ -z "$val" ] && [ -f "$SHUNT_ROOT/.env" ]; then
    val=$(grep -E "^${key}=" "$SHUNT_ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '\r' | sed -e 's/^["'"'"']//' -e 's/["'"'"']$//')
  fi
  printf '%s' "$val"
}

shunt_log() { # event file bytes_in bytes_out
  mkdir -p "$SHUNT_DIR" 2>/dev/null || return 0
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$1" "${2:-}" "${3:-0}" "${4:-0}" >> "$SHUNT_LOG" 2>/dev/null || true
}

# glob list match: shunt_match_list "<comma list>" "<path>"
shunt_match_list() {
  local list="$1" path base pat
  path=$(shunt_norm_path "$2"); base="${path##*/}"
  local IFS=,
  for pat in $list; do
    [ -n "$pat" ] || continue
    # shellcheck disable=SC2254
    case "$path" in $pat) return 0;; esac
    # shellcheck disable=SC2254
    case "$base" in $pat) return 0;; esac
  done
  return 1
}

shunt_allowed() { shunt_match_list "$SHUNT_ALLOW_PATHS" "$1"; }
shunt_denied()  { shunt_match_list "$SHUNT_DENY_PATTERNS" "$1"; }

shunt_bypass_active() {
  local f="$SHUNT_DIR/bypass"
  [ -f "$f" ] || return 1
  [ -n "$(find "$f" -mmin "-$SHUNT_BYPASS_MINUTES" 2>/dev/null)" ]
}

shunt_fail() {
  mkdir -p "$SHUNT_DIR" 2>/dev/null && : > "$SHUNT_DIR/bypass"
  shunt_log fail "" 0 0
  echo "shunt failed: $1" >&2
  echo "Direct reads are re-enabled for ${SHUNT_BYPASS_MINUTES} minutes. Read the file(s) with the Read tool." >&2
  exit 1
}

shunt_need() {
  command -v jq >/dev/null 2>&1 || { echo "shunt: jq is required" >&2; exit 1; }
  if [ "$SHUNT_BACKEND" = claude-plan ]; then
    command -v claude >/dev/null 2>&1 || { echo "shunt: claude CLI is required for the claude-plan backend" >&2; exit 1; }
  else
    command -v curl >/dev/null 2>&1 || { echo "shunt: curl is required" >&2; exit 1; }
  fi
}

# shunt_model ROLE (reader|writer) -> model for the active backend
shunt_model() {
  if [ "$SHUNT_BACKEND" = claude-plan ]; then
    case "$1" in
      writer) printf '%s' "${SHUNT_WRITER_MODEL:-sonnet}";;
      *)      printf '%s' "${SHUNT_READER_MODEL:-haiku}";;
    esac
  else
    case "$1" in
      writer) printf '%s' "${SHUNT_WRITER_MODEL:-$SHUNT_MODEL}";;
      *)      printf '%s' "${SHUNT_READER_MODEL:-$SHUNT_MODEL}";;
    esac
  fi
}

# shunt_chat SYSTEM_FILE USER_FILE ROLE -> worker reply on stdout
shunt_chat() {
  case "$SHUNT_BACKEND" in
    claude-plan) shunt_chat_claude "$@";;
    *)           shunt_chat_http "$@";;
  esac
}

# Worker = headless Claude Code on the user's plan. Runs from an empty temp dir so no project
# CLAUDE.md, settings or shunt hooks load into the worker; no tools, message arrives on stdin.
shunt_chat_claude() {
  local sys="$1" usr="$2" role="${3:-reader}" wd out rc tmo=() model
  model=$(shunt_model "$role")
  command -v timeout >/dev/null 2>&1 && tmo=(timeout "$SHUNT_TIMEOUT")
  wd=$(mktemp -d)
  out=$(cd "$wd" && SHUNT_BYPASS=1 "${tmo[@]}" claude -p --model "$model" \
    --system-prompt "$(cat "$sys")" --tools "" --disable-slash-commands \
    --strict-mcp-config --no-session-persistence < "$usr" 2>"$wd/err")
  rc=$?
  if [ "$rc" -ne 0 ]; then
    local msg; msg=$(head -c 200 "$wd/err" | tr '\n' ' ')
    rm -rf "$wd"
    shunt_fail "claude -p exited $rc ${msg}"
  fi
  rm -rf "$wd"
  [ -n "$out" ] || shunt_fail "empty worker reply"
  printf '%s\n' "$out"
}

shunt_chat_http() {
  local sys="$1" usr="$2" role="${3:-reader}" body resp code key auth=() model
  model=$(shunt_model "$role")
  body=$(mktemp); resp=$(mktemp)
  jq -n --arg model "$model" --argjson t "$SHUNT_TEMPERATURE" \
    --rawfile sys "$sys" --rawfile usr "$usr" \
    '{model:$model,temperature:$t,messages:[{role:"system",content:$sys},{role:"user",content:$usr}]}' > "$body"
  if [ -n "$SHUNT_KEY_VAR" ]; then
    key=$(shunt_env "$SHUNT_KEY_VAR")
    [ -n "$key" ] || { rm -f "$body" "$resp"; shunt_fail "$SHUNT_KEY_VAR not set (env or $SHUNT_ROOT/.env)"; }
    auth=(-H "Authorization: Bearer $key")
  fi
  code=$(curl -sS --max-time "$SHUNT_TIMEOUT" -o "$resp" -w '%{http_code}' \
    -H 'Content-Type: application/json' "${auth[@]}" \
    -d @"$body" "$SHUNT_BASE_URL/chat/completions" 2>/dev/null) || code=000
  if [ "$code" != 200 ]; then
    local msg; msg=$(jq -r '.error.message // .error // empty' "$resp" 2>/dev/null | head -c 200)
    rm -f "$body" "$resp"
    shunt_fail "worker HTTP $code ${msg}"
  fi
  local out; out=$(jq -r '.choices[0].message.content // empty' "$resp")
  rm -f "$body" "$resp"
  [ -n "$out" ] || shunt_fail "empty worker reply"
  printf '%s\n' "$out"
}
