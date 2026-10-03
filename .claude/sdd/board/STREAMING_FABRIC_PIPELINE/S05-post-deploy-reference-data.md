---
id: S05
feature: STREAMING_FABRIC_PIPELINE
title: "Load reference data and runtime config with post_deploy.py"
status: backlog
depends_on: [S03, S04]
agent: python-developer
files: [scripts/post_deploy.py, tests/unit/test_post_deploy.py]
updated: 2026-10-02
---

## Story 5: Load reference data and runtime config with post_deploy.py (`scripts/post_deploy.py`)

**Description:** `DatabaseSchema.kql` can't load data or set the OneLake availability policy (DESIGN A-003b). This idempotent script fills that gap per environment:
- loads the six `dim_*` tables and `revenue_target_daily`
- writes `target_scale()` (DESIGN Decision 5, which resolves A-006) and `late_threshold()`
- enables OneLake availability on `sales_enriched` and `dim_*`

It's a prerequisite for S06 (dims must exist before enrichment), S07 (e2e) and S08 (the alert).

**Actual Plan**

- `scripts/post_deploy.py`, CLI `python -m scripts.post_deploy [--config config/pipeline.toml] [--skip-onelake]`. It reads the connection from the repo-root `.env` through `scripts.kusto.load_env()` / `client()` / `database()` (S03).
- Steps, each printing one line:
  1. **Dimensions:** `generator.dims.load_static_dimensions()` (`sources/src/generator/dims.py:33`) → `kusto.replace_table(kc, db, name, schema, rows)` for each of the 6 tables. The schema string is built from `SCHEMAS` (`dims.py:18-30`): `pa.string()` → `string`, `pa.int32()` → `int`.
  2. **Target:** for each year in `target.years`, build a `Model` and call `generator.facts.generate_year(model, year, date(year,1,1), date(year,12,31))["tab_fato004"]` (`sources/src/generator/facts.py:147`). Group by `COD_DIA`, summing `META_FATURAMENTO` → rows `(cod_dia, day=datetime, meta_faturamento)` → `replace_table(..., "revenue_target_daily", "cod_dia:string, day:datetime, meta_faturamento:real", rows)`. No Parquet round-trip and no `generator generate` call: calling the library directly gives the same seeded data.
  3. **Target scale:** `mean_event_revenue` = mean `faturamento` of `demo.target_mean_sample` events from `EventGenerator(model, as_of)` (`sources/src/generator/stream.py:56`) with `as_of = e2e.as_of`. `mean_daily_target` = mean of the loaded daily targets. `scale = demo.nominal_rate * 86400 * mean_event_revenue / mean_daily_target`. Then `.create-or-alter function with (folder='config') target_scale() { <scale:.10g> }`. Expose this as the pure function `compute_target_scale(nominal_rate, mean_event_revenue, mean_daily_target) -> float` for tests.
  4. **Late threshold:** `.create-or-alter function with (folder='config') late_threshold() { <kql.late_threshold> }`, after validating the value against `^\d+(ms|s|m|h|d)$`.
  5. **OneLake availability** (unless `--skip-onelake`): for `sales_enriched` and each `dim_*`, run `.alter-merge table <t> policy mirroring dataformat=parquet with (IsEnabled=true)`. **Flag:** the command syntax is DESIGN Pattern 4's proposal, to confirm against Microsoft Learn before merging. If it's rejected, print a warning pointing to the runbook UI toggle and continue (exit 0) rather than failing the deploy, because history is a SHOULD (G11).
- `scripts/post_deploy.py` must be safe to re-run (AT-005): only `.set-or-replace`/`.set-or-append` and `.create-or-alter`, never `.append` alone.
- New `tests/unit/test_post_deploy.py` (pytest, fake Kusto client recording commands, as in S03's `test_kusto.py`). Cases:
  - `test_compute_target_scale` (hand-computed numbers)
  - `test_dimension_schema_strings` (6 tables, types mapped)
  - `test_daily_target_rows_one_per_day` (2026 → 365 rows, all > 0)
  - `test_commands_are_idempotent_verbs` (no bare `.append`/`.ingest`)
  - `test_rejects_bad_late_threshold`
  - `test_onelake_failure_is_warning_not_error`

**Architecture**

```text
config/pipeline.toml ─┐
generator.dims / facts.generate_year / EventGenerator ─┐
                      ▼                                 ▼
          post_deploy.main ──► kusto.replace_table: dim_* (126 rows), revenue_target_daily (365/yr)
                           ──► .create-or-alter target_scale() { nominal_rate·86400·mean_rev / mean_target }
                           ──► .create-or-alter late_threshold() { 2m }
                           ──► .alter-merge table … policy mirroring (IsEnabled=true)  [warn on failure]
```

**Acceptance Criteria**

- [ ] Running the script twice against the same database leaves row counts at 3 / 9 / 35 / 57 / 3 / 19 for `dim_categoria / dim_marca / dim_produto / dim_cliente / dim_fabrica / dim_organizacional` and 365 for `revenue_target_daily` (2026) (AT-005)
- [ ] `target_scale()` returns the value from `compute_target_scale` for the configured inputs; changing `demo.nominal_rate` and re-running changes it proportionally
- [ ] `late_threshold()` returns the configured timespan, and an invalid value aborts with exit 2 before any command runs
- [ ] A rejected OneLake command produces a warning and exit 0; a dimension load failure produces exit 1
- [ ] No Parquet files are written or read (the generator library is called directly)
- [ ] No secrets are printed (connection settings come only from `.env` / environment)
- [ ] `tests/unit/test_post_deploy.py` has the six cases and passes without network access
