#!/usr/bin/env bash
# Usage: status.sh — summarize .claude/shunt/shunt.log (blocks, delegations, estimated tokens saved)
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

[ -f "$SHUNT_LOG" ] || { echo "no shunt activity logged yet ($SHUNT_LOG)"; exit 0; }
awk -F'\t' '
  $2=="block"      { blocks++ }
  $2=="fail"       { fails++ }
  $2=="bulk-read"  { reads++;  in_b += $4; out_b += $5 }
  $2=="code-write" { writes++; wr_in += $4; wr_out += $5 }
  END {
    printf "blocked reads      : %d\n", blocks
    printf "bulk-read calls    : %d\n", reads
    printf "code-write calls   : %d\n", writes
    printf "worker failures    : %d\n", fails
    printf "bulk-read in/out   : %d -> %d bytes\n", in_b, out_b
    if (in_b > 0) printf "est. tokens saved  : ~%d (%.0f%% of raw file bytes / 4)\n", (in_b - out_b) / 4, 100 * (in_b - out_b) / in_b
    printf "code kept out of context: ~%d tokens (bytes / 4)\n", wr_out / 4
  }' "$SHUNT_LOG"
