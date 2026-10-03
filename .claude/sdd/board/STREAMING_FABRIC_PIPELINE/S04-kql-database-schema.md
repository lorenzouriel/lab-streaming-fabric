---
id: S04
feature: STREAMING_FABRIC_PIPELINE
title: "Write the KQL database schema (DatabaseSchema.kql) with static checks"
status: backlog
depends_on: [S01, S03]
agent: fabric-logging-specialist
files: [workspace/fruit_juice_db.KQLDatabase/DatabaseSchema.kql, tests/unit/test_schema.py]
updated: 2026-10-02
---

## Story 4: Write the KQL database schema (DatabaseSchema.kql) with static checks (`workspace/fruit_juice_db.KQLDatabase/DatabaseSchema.kql`)

**Description:** Defines every KQL object as code, in the file Fabric runs on Git sync and on `fabric-cicd` publish (DESIGN Decision 1). The objects are `sales_raw` and its JSON mapping, the dimension and target tables, `sales_enriched` with the `enrich_sales()` update policy, the `sales_dedup` view, three KPI views on top of it, and the reader functions. The JSON mapping must match the S01 event shape (including `emitted_at`). It's a prerequisite for S05 (loads), S06 (Eventstream destination), S07 (oracle comparison) and S08 (dashboard and alert).

**Actual Plan**

- Create `workspace/fruit_juice_db.KQLDatabase/DatabaseSchema.kql` with exactly the content of DESIGN Pattern 1, expanded:
  - `kpi_client_1m` (`by window_start = bin(event_time, 1m), cod_cliente`) and `kpi_factory_1m` (`... cod_fabrica`), with bodies identical to `kpi_product_1m` apart from the key.
  - Functions `kpi_client()` and `kpi_factory()` mirror `kpi_product()` (adding `margin`).
  - Use only the commands supported by DatabaseSchema.kql (DESIGN A-003b): `.create-merge table`, `.create-or-alter function|materialized-view|... ingestion json mapping`, `.alter table ... policy update`. **No** `.drop`, `.set-or-replace` or `.alter ... policy mirroring` here (those are S05).
- Order inside the file: tables → mapping → config functions (`late_threshold()` = `2m`, `target_scale()` = `1.0` placeholders) → `enrich_sales()` → update policy → `sales_dedup` → KPI views → reader functions (`kpi_*()`, `late_events()`, `unmatched_dims()`, `duplicate_count()`, `revenue_vs_target()`).
- Column names and types of `sales_raw` = the keys of `StreamEvent.to_dict()` after S01 (`sources/src/generator/stream.py:38-46`), in the same order. `cod_*` are `string`; measures are `real`; `seq` is `long`.
- Dimension table columns mirror `sources/src/generator/dims.py:18-30` (`SCHEMAS`) exactly, including case (`Cod_Cliente`, …). `Esquerda`, `Direita` and `Nivel` are `int`.
- The file **won't be loadable by Fabric on its own**. It sits beside the `.platform` and `DatabaseProperties.json` that Git sync generates in S06. S06 replaces Fabric's generated `DatabaseSchema.kql` with this one.
- `ingestion_time()` inside the update-policy query is the DESIGN default for `ingested_at`. If it comes back empty in S06, `ingested_at` is only used by the lag tile, so parity is unaffected. Flag it in S06 instead of changing the schema. (DESIGN assumption, not an open question.)
- New `tests/unit/test_schema.py` (pytest, regex-based; no Kusto parser available in Python). Cases:
  - `test_only_supported_commands` (every line starting with `.` matches the allow-list)
  - `test_mapping_matches_event_fields` (the JSON in `sales_raw_json` parses; its `column` list == `list(StreamEvent.to_dict())` for a generated event)
  - `test_sales_raw_columns_match_event_fields`
  - `test_dim_tables_match_generator_schemas` (vs `generator.dims.SCHEMAS`)
  - `test_every_referenced_object_is_defined` (identifiers used after `on table`/`on materialized-view`, in `materialized_view('…')` and in function calls `name()` resolve to objects defined in the file)
  - `test_kpi_views_have_identical_measures`

**Architecture**

```text
sales_raw ──(mapping sales_raw_json)
   └─ update policy: enrich_sales()  [lookup dim_cliente/produto+marca+categoria/fabrica; is_late = emitted_at-event_time > late_threshold()]
        └─► sales_enriched
              └─ MV sales_dedup = take_any(*) by event_id
                    ├─ MV kpi_product_1m | kpi_client_1m | kpi_factory_1m  (sum ×5, count by bin(event_time,1m), key)
                    │     └─ fn kpi_*()  [+ margin]
                    └─ fn late_events() · unmatched_dims() · duplicate_count() · revenue_vs_target()
```

**Acceptance Criteria**

- [ ] `DatabaseSchema.kql` contains only `.create-merge table`, `.create-or-alter …` and `.alter table … policy update` commands
- [ ] `sales_raw` columns and the `sales_raw_json` mapping list exactly the 14 event fields in `to_dict()` order, including `emitted_at`
- [ ] The six `dim_*` tables match `generator.dims.SCHEMAS` column for column
- [ ] `sales_dedup` is `take_any(*) by event_id`, and the three KPI views are defined `on materialized-view sales_dedup` with no composite aggregation (margin only in `kpi_*()`)
- [ ] No view or function uses `now()` or `ago()`
- [ ] `revenue_vs_target()` returns columns `revenue_to_date, day, target_to_date, pct_of_target`
- [ ] `tests/unit/test_schema.py` has the six cases and passes under `uv run pytest`
- [ ] No `.platform`, `DatabaseProperties.json` or other Fabric-generated files are hand-written in this story
