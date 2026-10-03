#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Blocks cat/head/tail/less/more dumping large files.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
command -v jq >/dev/null 2>&1 || exit 0
input=$(cat)
[ "${SHUNT_BYPASS:-0}" = 1 ] && exit 0
shunt_bypass_active && exit 0

[ "$(jq -r '.tool_name // empty' <<<"$input")" = Bash ] || exit 0
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
[[ "$cmd" =~ (^|[[:space:];\&\|\(])(cat|head|tail|less|more)[[:space:]] ]] || exit 0
# output is filtered or redirected -> not a context dump
case "$cmd" in *"|"*|*">"*) exit 0;; esac

read -ra toks <<<"$cmd"
cur=""; n=""; expect_n=0
for t in "${toks[@]}"; do
  case "$t" in
    cat|head|tail|less|more) cur=$t; n=""; expect_n=0; continue;;
    ';'|'&&'|'||') cur=""; continue;;
  esac
  [ -n "$cur" ] || continue
  if [ "$expect_n" = 1 ]; then n=$t; expect_n=0; continue; fi
  case "$t" in
    -n) expect_n=1; continue;;
    -n[0-9]*) n=${t#-n}; continue;;
    -[0-9]*) n=${t#-}; continue;;
    -*) continue;;
  esac
  f=$(shunt_unix_path "$t")
  [ -f "$f" ] || continue
  if [[ "$cur" =~ ^(head|tail)$ && "$n" =~ ^[0-9]+$ && "$n" -le "$SHUNT_MIN_LINES" ]]; then continue; fi
  shunt_allowed "$f" && continue
  shunt_denied "$f" && continue
  lines=$(wc -l < "$f")
  [ "$lines" -gt "$SHUNT_MIN_LINES" ] || continue
  shunt_log block "$t" "$(wc -c < "$f")" 0
  cat >&2 <<MSG
BLOCKED by token-shunt: '$cur $t' would dump $lines lines (limit $SHUNT_MIN_LINES).
Delegate: bash "\$CLAUDE_PROJECT_DIR/.claude/shunt/bulk-read.sh" "<specific question>" $t
Or bound the output: head -n $SHUNT_MIN_LINES / tail -n $SHUNT_MIN_LINES, or use Grep.
MSG
  exit 2
done
exit 0
