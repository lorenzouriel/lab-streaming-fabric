#!/usr/bin/env bash
# Usage: code-write.sh --spec "<what to write>" --out <path> [--ref <file>]... [--force]
# Worker generates the code; it is written straight to disk and never enters Claude's context.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
shunt_need

spec=""; out=""; force=0; refs=()
while [ $# -gt 0 ]; do
  case "$1" in
    --spec)  spec="${2:-}"; shift 2;;
    --out)   out="${2:-}"; shift 2;;
    --ref)   refs+=("${2:-}"); shift 2;;
    --force) force=1; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$spec" ] && [ -n "$out" ] || { echo 'usage: code-write.sh --spec "<spec>" --out <path> [--ref <file>]... [--force]' >&2; exit 2; }
dest=$(shunt_unix_path "$out")
[ ! -e "$dest" ] || [ "$force" = 1 ] || { echo "shunt: $out exists; pass --force to overwrite" >&2; exit 1; }

sys=$(mktemp); usr=$(mktemp); trap 'rm -f "$sys" "$usr"' EXIT
cat > "$sys" <<'PROMPT'
You are a boilerplate code generator. Output only the code for the requested file: no explanations,
no markdown fences, no commentary. Match the naming, style, imports and structure of the reference files exactly.
Do not invent APIs that the references do not show. If the spec is ambiguous, choose the most conventional option.
PROMPT

printf 'Target file: %s\n\nSpec:\n%s\n\n' "$(shunt_norm_path "$out")" "$spec" > "$usr"
bytes_in=${#spec}
for f in ${refs[@]+"${refs[@]}"}; do
  [ -n "$f" ] || continue
  p=$(shunt_unix_path "$f")
  [ -f "$p" ] || { echo "shunt: missing reference $f" >&2; exit 1; }
  if shunt_denied "$p" && [ "${SHUNT_ALLOW_SECRETS:-0}" != 1 ]; then echo "shunt: reference $f matches a sensitive pattern" >&2; exit 1; fi
  bytes_in=$((bytes_in + $(wc -c < "$p")))
  printf '<reference path="%s">\n' "$(shunt_norm_path "$f")" >> "$usr"; cat "$p" >> "$usr"; printf '\n</reference>\n\n' >> "$usr"
done

code=$(shunt_chat "$sys" "$usr" writer) || exit $?
# strip a single wrapping markdown fence if the worker added one
code=$(printf '%s\n' "$code" | sed -e '1{/^```/d}' -e '${/^```[[:space:]]*$/d}')
mkdir -p "$(dirname "$dest")"
printf '%s\n' "$code" > "$dest"
lines=$(wc -l < "$dest")
echo "wrote $lines lines to $out (unreviewed: run tests/linters, read only failures)"
shunt_log code-write "$out" "$bytes_in" "$(wc -c < "$dest")"
