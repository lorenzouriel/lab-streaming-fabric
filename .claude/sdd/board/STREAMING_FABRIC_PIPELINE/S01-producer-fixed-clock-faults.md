---
id: S01
feature: STREAMING_FABRIC_PIPELINE
title: "Add fixed clock, emitted_at and deterministic dup/late injection to the producer"
status: ready
depends_on: []
agent: python-developer
files: [sources/src/generator/stream.py, sources/src/generator/cli.py, sources/tests/test_stream.py, sources/README.md]
updated: 2026-10-02
---

## Story 1: Add fixed clock, emitted_at and deterministic dup/late injection to the producer (`sources/src/generator/stream.py`, `cli.py`)

**Description:** This makes every emitted event, including injected duplicates and late events, a pure function of (seed, as-of, rate, seq, fault flags), so the oracle can regenerate the exact stream offline. It adds the `emitted_at` field that the KQL lateness rule relies on. This is the foundation: the KQL mapping (S04), `target_scale` (S05) and the oracle (S07) all build on the event shape defined here.

**Actual Plan**

- `sources/src/generator/stream.py:22-46` (`StreamEvent`): add the field `emitted_at: datetime` directly after `event_time` (line 26). In `to_dict()` (lines 38-46), serialise it with the same format as `event_time` (line 41) under the key `"emitted_at"`, placed right after `"event_time"`. Extract the formatter into `_iso_ms(dt: datetime) -> str` so both fields share it.
- `stream.py:72-93` (`EventGenerator.event`): pass `emitted_at=event_time` in the `StreamEvent(...)` call (line 87). Content must stay unchanged, because the rng draws on lines 73-84 are untouched.
- `stream.py:102-119` (`iter_events`): add the keyword `fixed_clock: bool = False`. When it's true, the timestamp is `start_time + timedelta(seconds=seq / rate)` instead of `now()` (line 115); wall pacing (lines 118-119) is unchanged. Docstring: `rate` = events per simulated second (as today: wall interval = `1/(rate*speed)`).
- `stream.py`: add the module constant `_TAG_FAULT = 4` next to `_TAG_STREAM` (line 19), and add the new function `inject_faults(events, seed, *, dup_ratio=0.0, late_ratio=0.0, late_delay=timedelta(minutes=5)) -> Iterator[StreamEvent]`, exactly as DESIGN Pattern 2:
  - Per seq: `rng = rng_for(seed, _TAG_FAULT, seq)`. **Always** draw `u_dup = rng.random()` then `u_late = rng.random()`. Late takes precedence (a late event is never duplicated).
  - Held late events are released, with `dataclasses.replace(e, emitted_at=<current event_time>)`, before the first event whose `event_time >= held.event_time + late_delay`. At end of stream they're released with `emitted_at = event_time + late_delay`.
- `sources/src/generator/cli.py:22-34` (stream parser): add `--fixed-clock` (store_true), `--dup-ratio` (float, default 0.0), `--late-ratio` (float, default 0.0), `--late-delay` (float simulated seconds, default 300). Validate ratios in `[0, 1)` and fail via `parser.error`.
- `cli.py:54-88` (`stream()`):
  - Line 62: start at `datetime.now(timezone.utc)` when `--as-of` is not given and `--fixed-clock` is off; otherwise use midnight of `as_of`. This fixes the 00:00 start that skews the lag tile.
  - Lines 75-77: pass `fixed_clock=args.fixed_clock`, then wrap the iterator with `inject_faults(..., seed=cfg["seed"], ...)` when either ratio is > 0.
  - Count `duplicates` (same `event_id` seen twice in the loop) and `late` (`emitted_at > event_time`) next to `emitted`.
  - Summary (line 87): `stopped after N event(s) (D duplicate(s), L late); resume with --start-seq X`, where X = max seq written + 1.
- `--count` keeps meaning **unique** events (iter_events count). Duplicates and late releases don't consume it.
- `sources/tests/test_stream.py` (pytest, matching the existing function-per-case style and the `generator` fixture at lines 14-18). Add:
  - `test_emitted_at_equals_event_time_by_default`
  - `test_fixed_clock_is_pure_function_of_seq` (two runs with different `speed` give identical `event_time`s)
  - `test_inject_faults_deterministic` (AT-011: two runs give identical lists)
  - `test_inject_faults_counts` (seed 42, 2000 events, 0.05/0.05: unique ids = 2000; the late count equals the number of seqs with `u_late < 0.05`; every late event has `emitted_at - event_time >= late_delay`; no late event is duplicated)
  - `test_dup_decision_independent_of_late_ratio`
  - Update the import on line 10.
- `sources/README.md:21` (Event fields): add `emitted_at`. In "Determinism" (line 24), document `--fixed-clock`, the fault flags, and that held late events are **not** sent when stopped with Ctrl+C.
- Defaults `--late-delay 300` and the KQL `late_threshold` 2 min come from DESIGN Decision 3. They aren't open questions.

**Architecture**

```text
cli.stream()
  └─ iter_events(gen, rate, fixed_clock)      [event_time = as_of + seq/rate]
       └─ EventGenerator.event(seq, t)        [emitted_at = event_time]
  └─ inject_faults(seed, dup, late, delay)    [rng_for(seed, 4, seq): u_dup, u_late]
       ├─ late → hold → release(emitted_at = later event_time)
       └─ dup  → yield event twice (identical)
  └─ sink.write(event)                        [summary: emitted, duplicates, late]
```

**Acceptance Criteria**

- [ ] `StreamEvent.to_dict()` contains `emitted_at`, ISO-8601 with ms and `Z`, equal to `event_time` for non-late events
- [ ] With the same seed and as-of, `EventGenerator.event(n)` content (every field except the timestamps) is unchanged from before this story, and the existing 11 tests in `test_stream.py` pass unmodified apart from the import line
- [ ] With `--fixed-clock`, `event_time(seq) = as_of 00:00Z + seq/rate` regardless of `--speed` and `--no-jitter`
- [ ] `inject_faults` output is identical across runs for the same inputs (AT-011)
- [ ] For seed 42, count 2000, dup 0.05, late 0.05: unique `event_id`s = 2000 exactly, and no event is both late and duplicated
- [ ] Every late event has `emitted_at - event_time >= late_delay` and keeps its original `event_time` and `cod_dia`
- [ ] Ratios of 0 produce output identical to running without `inject_faults`
- [ ] `--dup-ratio 1.5` exits with an argparse error (code 2)
- [ ] No new third-party dependencies in `sources/pyproject.toml`
- [ ] New cases are in `sources/tests/test_stream.py` and `uv run pytest` in `sources/` is green
