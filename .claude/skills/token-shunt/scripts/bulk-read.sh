#!/usr/bin/env bash
# Usage: bulk-read.sh "<question>" <file> [file ...]
# Sends files to the cheap worker model, prints a bullets-only answer with line numbers.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
shunt_need

[ $# -ge 2 ] || { echo 'usage: bulk-read.sh "<question>" <file> [file ...]' >&2; exit 2; }
question="$1"; shift

sys=$(mktemp); usr=$(mktemp); trap 'rm -f "$sys" "$usr"' EXIT
cat > "$sys" <<'PROMPT'
You are a bulk file reader for code analysis. Answer the question using only the provided files.
Output structured bullets only. No greetings, no prose, no closing remarks.
Every bullet must cite file:line (lines are prefixed in the input as "N: "). Quote identifiers exactly.
If the files do not contain the answer, say "not found" for that point. Never invent code.
PROMPT
if [ -n "${SHUNT_BULK_PROMPT_FILE:-}" ] && [ -f "$SHUNT_BULK_PROMPT_FILE" ]; then cp "$SHUNT_BULK_PROMPT_FILE" "$sys"; fi

printf 'Question: %s\n\n' "$question" > "$usr"
bytes_in=0; skipped=()
for f in "$@"; do
  p=$(shunt_unix_path "$f")
  [ -f "$p" ] || { skipped+=("$f (missing)"); continue; }
  if shunt_denied "$p" && [ "${SHUNT_ALLOW_SECRETS:-0}" != 1 ]; then skipped+=("$f (sensitive pattern)"); continue; fi
  sz=$(wc -c < "$p"); bytes_in=$((bytes_in + sz))
  [ "$bytes_in" -le "$SHUNT_MAX_BYTES" ] || { echo "shunt: input exceeds SHUNT_MAX_BYTES=$SHUNT_MAX_BYTES; split the request" >&2; exit 1; }
  printf '<file path="%s">\n' "$(shunt_norm_path "$f")" >> "$usr"
  awk '{printf "%d: %s\n", NR, $0}' "$p" >> "$usr"
  printf '</file>\n\n' >> "$usr"
done
[ "$bytes_in" -gt 0 ] || { echo "shunt: no readable files${skipped[*]:+ (skipped: ${skipped[*]})}" >&2; exit 1; }

out=$(shunt_chat "$sys" "$usr" reader) || exit $?
[ ${#skipped[@]} -eq 0 ] || printf 'SKIPPED (not sent to worker; read directly if needed): %s\n' "${skipped[*]}"
printf '%s\n' "$out"
shunt_log bulk-read "$*" "$bytes_in" "${#out}"
