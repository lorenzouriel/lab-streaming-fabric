#!/usr/bin/env bash
# PreToolUse hook (matcher: Read). Blocks whole-file reads above SHUNT_MIN_LINES lines.
# Targeted reads (offset or limit set) always pass, as in Spotify's shunt.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
command -v jq >/dev/null 2>&1 || exit 0
input=$(cat)
[ "${SHUNT_BYPASS:-0}" = 1 ] && exit 0
shunt_bypass_active && exit 0

[ "$(jq -r '.tool_name // empty' <<<"$input")" = Read ] || exit 0
path=$(jq -r '.tool_input.file_path // empty' <<<"$input")
offset=$(jq -r '.tool_input.offset // empty' <<<"$input")
limit=$(jq -r '.tool_input.limit // empty' <<<"$input")
[ -n "$path" ] || exit 0
if [ -n "$offset" ] || [ -n "$limit" ]; then exit 0; fi

p=$(shunt_unix_path "$path")
[ -f "$p" ] || exit 0
case "${p,,}" in *.png|*.jpg|*.jpeg|*.gif|*.webp|*.pdf|*.ipynb|*.svg) exit 0;; esac
shunt_allowed "$p" && exit 0
lines=$(wc -l < "$p")
[ "$lines" -gt "$SHUNT_MIN_LINES" ] || exit 0
# sensitive files are never sent to the worker; let Claude read them directly
shunt_denied "$p" && exit 0

shunt_log block "$path" "$(wc -c < "$p")" 0
cat >&2 <<MSG
BLOCKED by token-shunt: $path has $lines lines (limit $SHUNT_MIN_LINES).
To understand or search it, delegate:
  bash "\$CLAUDE_PROJECT_DIR/.claude/shunt/bulk-read.sh" "<specific question>" $path [more files]
To edit a region, Read it with offset and limit instead.
MSG
exit 2
