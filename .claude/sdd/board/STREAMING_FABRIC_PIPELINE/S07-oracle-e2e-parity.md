---
id: S07
feature: STREAMING_FABRIC_PIPELINE
title: "Add the oracle and the live end-to-end parity suite"
status: backlog
depends_on: [S01, S05, S06]
agent: test-generator
files: [tests/oracle.py, tests/unit/test_oracle.py, tests/e2e/conftest.py, tests/e2e/test_pipeline.py, .github/workflows/e2e.yml]
updated: 2026-10-02
---

## Story 7: Add the oracle and the live end-to-end parity suite (`tests/oracle.py`, `tests/e2e/test_pipeline.py`)

**Description:** This is the proof of the lab's core claim. It regenerates the exact emitted stream offline (S01 makes this possible), computes the expected KPIs, duplicate counts and late counts with pandas, and compares them with the live KQL views after a seeded producer run. It covers AT-001 to AT-007 and AT-010. It runs locally with a marker and through a manual GitHub workflow. It depends on S06 for a live dev database. The oracle unit tests only need S01.

**Actual Plan**

- `tests/oracle.py`: DESIGN Pattern 5, `emitted_events(...)` and `expected_kpis(emitted, key)`, plus:
  - `expected_counts(emitted) -> dict(raw=len, unique=nunique(event_id), late=(emitted_at>event_time) on unique rows)`
  - `compare(expected, actual, keys, tol=0.005) -> list[str]` (human-readable mismatches: missing or extra keys and per-measure deltas)
  - It reuses `generator.stream.EventGenerator`, `iter_events(..., fixed_clock=True, sleep=lambda _: None)` and `inject_faults`, rather than re-implementing the clock, so the oracle and the producer share one code path. Use `iter_events` (`sources/src/generator/stream.py:102`) with `sleep` injected, not the loop shown in Pattern 5.
- `tests/unit/test_oracle.py`. Cases:
  - `test_expected_kpis_hand_example` (3 events, 2 windows)
  - `test_dedup_before_aggregation`
  - `test_late_events_counted_in_their_event_time_window`
  - `test_compare_reports_missing_extra_and_delta`
  - `test_oracle_matches_cli_file_sink` (run `generator.cli.main([... '--sink','file','--fixed-clock', ...])` into `tmp_path` and compare with `emitted_events` for the same args; ignore `--speed`)
- `tests/e2e/conftest.py`:
  - Mark everything `e2e`; skip when `KUSTO_QUERY_URI` or `sources/.env` `KAFKA_SASL_PASSWORD` is missing.
  - Fixture `kql` (client + db from `scripts.kusto`).
  - Fixture `clean_db`: `.clear table sales_raw data`, `.clear table sales_enriched data`, `.clear materialized-view <mv> data` for the four views. **Flag:** the `.clear materialized-view … data` syntax is the DESIGN proposal (Testing Strategy), to confirm against Microsoft Learn. The fallback is to use a fresh seed per test and filter queries by `seq` range plus a per-run `event_id` set. Pick the fallback if the command is rejected; don't drop views.
  - Helper `run_producer(**e2e_args)` → `subprocess.run(["uv","run","generator","stream","--sink","kafka","--fixed-clock",...], cwd="sources")` returning the exit code and stderr.
  - Helper `wait_for(kql_count_query, expected, timeout_s)`.
- `tests/e2e/test_pipeline.py`, parameters from `config/pipeline.toml [e2e]`:
  - `test_parity` (AT-001, no faults)
  - `test_duplicates` (AT-002: raw count > unique; `materialized_view('sales_dedup') | count` = 2000; `duplicate_count()` = oracle `raw - unique`)
  - `test_late` (AT-003: `late_events() | count` = oracle late; KPIs equal)
  - `test_replay` (AT-004: snapshot KPIs, clean, rerun, identical)
  - `test_post_deploy_idempotent` (AT-005: run `scripts.post_deploy` twice; `.show database schema as csl script` hash unchanged; counts unchanged)
  - `test_unmatched` (AT-006: `.set-or-append sales_raw <| datatable(...)` one row with `cod_cliente='999999'` → `unmatched_dims() | count` = 1)
  - `test_bad_credentials` (AT-007: run the producer with `KAFKA_SASL_PASSWORD=invalid` via env override → exit code 2, no rows)
  - `test_onelake` (AT-010, additionally marked `slow`, skipped unless `RUN_SLOW=1`; polls ≤ 15 min)
  - Each parity test compares `kpi_product()`, `kpi_client()` and `kpi_factory()` with `expected_kpis` using `compare` and asserts `== []`.
- `.github/workflows/e2e.yml`: `workflow_dispatch` only. Secrets `KUSTO_QUERY_URI`, `AZURE_*`, `KAFKA_BOOTSTRAP`, `KAFKA_TOPIC`, `KAFKA_SASL_PASSWORD`. It writes `.env` and `sources/.env` from the secrets at runtime, sets `FABRIC_AUTH=sp`, then runs `uv run pytest -m e2e -o addopts=""`.

**Architecture**

```text
config [e2e] ─┬─► run_producer (CLI, Kafka) ─► Eventstream ─► sales_raw … kpi_*_1m ─► kpi_*() ─┐
              └─► oracle.emitted_events (same iter_events + inject_faults, no sleep)            │
                       └─ expected_kpis / expected_counts ──────────── compare(tol 0.005) ◄─────┘
                                                                         └─ assert [] (AT-001..006)
```

**Acceptance Criteria**

- [ ] The oracle produces events through `generator.stream.iter_events` + `inject_faults`; there's no second implementation of the clock or the fault logic
- [ ] `test_oracle_matches_cli_file_sink` proves the oracle equals the CLI output for the same arguments (unit, no network)
- [ ] Against dev, `uv run pytest -m e2e -o addopts=""` passes AT-001 to AT-007, with 0 mismatched KPI rows and |Δ| ≤ 0.005
- [ ] `test_late` asserts the late count equals the oracle's exactly (not "≥")
- [ ] `test_bad_credentials` asserts exit code 2 and zero new rows in `sales_raw`
- [ ] e2e tests are excluded from the default `uv run pytest` and from `ci.yml`
- [ ] `e2e.yml` only runs on `workflow_dispatch`, and secrets are only written to files that `.gitignore` excludes
- [ ] `tests/unit/test_oracle.py` has the five cases and passes in PR CI
