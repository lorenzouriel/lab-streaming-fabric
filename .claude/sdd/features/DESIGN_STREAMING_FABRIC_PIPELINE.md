# DESIGN: Streaming Fabric Pipeline (Eventstream → Eventhouse KQL → Activator)

> Technical design for implementing STREAMING_FABRIC_PIPELINE

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STREAMING_FABRIC_PIPELINE |
| **Date** | 2026-10-02 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_STREAMING_FABRIC_PIPELINE.md](./DEFINE_STREAMING_FABRIC_PIPELINE.md) |
| **Status** | Ready for Build |
| **Confidence** | 0.85: KB patterns for Eventhouse, KQL, dashboards and Git; Microsoft Learn for the custom endpoint, materialized views and DatabaseSchema.kql; Activator Git support is preview |

### Assumption verification (done in this phase)

| ID | Result | Source | Design consequence |
|----|--------|--------|--------------------|
| A-001 | ✅ Confirmed by docs: the Kafka endpoint uses `SASL_SSL` + `PLAIN`, username `$ConnectionString`, password = connection string; topic name shown on the Kafka tab | MS Learn *Stream and consume events … Kafka endpoint* | KafkaSink reads security settings from `.env`. Live check in AT-001 |
| A-002 | ✅ Confirmed: a materialized view can be built on another view **only** if the source is `take_any(*)` dedup; composite aggregations (e.g. margin = a − b − c) aren't allowed in the view | MS Learn *Create materialized view* | `sales_dedup` = `take_any(*) by event_id`; KPI views built on it; margin computed in stored functions |
| A-003 | ✅ Mostly: `fabric-cicd` supports Eventstream, Eventhouse, KQLDatabase, KQLDashboard, Reflex, Lakehouse. Activator Git integration is **preview**. Eventstream → Eventhouse **Direct Ingestion** must be reconnected manually after deploy | fabric-cicd docs; MS Learn *RTI Git integration* | Use the Eventhouse destination in **"event processing before ingestion"** mode, rebound with `parameter.yml`. Activator gets a documented manual fallback |
| A-003b | ✅ `DatabaseSchema.kql` (inside the KQLDatabase item) deploys tables, functions, update policies, materialized views and ingestion mappings from Git. It does **not** handle the OneLake availability policy or data loads | MS Learn *Eventhouse and KQL database – Git integration* | All KQL schema lives in `DatabaseSchema.kql`, so `apply_kql.py` is dropped. `post_deploy.py` handles the OneLake policy, dimension and target data, and the target scale |
| A-004 | ⚠️ Not confirmed for trial capacity | Web search inconclusive | All Fabric/Kusto scripts take `FABRIC_AUTH=sp\|cli`; if service principals fail on the trial, `deploy.yml` falls back to a documented local run with `az login` (recorded as an exception to SC8) |
| A-006 | Resolved by design | n/a | `post_deploy.py` computes a `target_scale()` KQL function so that running the producer at `demo.nominal_rate` ≈ 100% of the daily target |
| A-007 | Resolved by design | n/a | Lateness = `emitted_at − event_time > late_threshold`. Both are producer fields, so lateness is deterministic and still works with `--speed`; ingestion time is shown only as an operational metric |
| A-008 | Adjusted | n/a | OneLake availability is enabled on **tables** (`sales_enriched`, dimensions), not on materialized views. SC9 is checked on `sales_enriched` row counts |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ LOCAL / CI                                                                                    │
│  sources/ generator stream --sink kafka --fixed-clock --dup-ratio p --late-ratio q            │
│     │  JSON {event_id, seq, event_time, emitted_at, cod_*, measures}  (SASL_SSL, .env)         │
│  sources/ generator generate ──Parquet──► scripts/post_deploy.py ─┐                            │
└─────┼────────────────────────────────────────────────────────────┼────────────────────────────┘
      ▼                                                             │ azure-kusto-data (.set-or-replace,
┌──────────────────── Fabric workspace (dev | prod, trial capacity) ┼──────── .alter policy) ───┐
│  sales_stream.Eventstream                                         │                            │
│   [custom endpoint (Kafka)] ──► [Eventhouse destination: processed ingestion, JSON mapping]   │
│                                       │                           ▼                            │
│  fruit_juice_eh.Eventhouse / fruit_juice_db.KQLDatabase (schema = DatabaseSchema.kql in Git)  │
│     sales_raw ──update policy: enrich_sales()──► sales_enriched ◄─ dim_* , revenue_target_daily│
│                    (lookup dims, is_late)          │  (OneLake availability → Delta)            │
│                                                    ▼                                           │
│                              MV sales_dedup = take_any(*) by event_id                         │
│                                   │                                                            │
│              MV kpi_product_1m / kpi_client_1m / kpi_factory_1m  (on materialized-view)        │
│                                   │                                                            │
│   fn kpi_*() (+margin) · fn late_events() · fn unmatched_dims() · fn revenue_vs_target()      │
│        │                                  │                                                    │
│        ▼                                  ▼                                                    │
│  sales_dashboard.KQLDashboard ──tile "revenue vs target"──► revenue_alerts.Reflex ──► email   │
│  fruit_juice_lh.Lakehouse ── OneLake shortcut ──► sales_enriched, dim_* (Delta history)        │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
      ▲ fabric-cicd publish (GitHub Actions, parameter.yml per environment) from workspace/
      ▲ tests/e2e: oracle (pandas over regenerated events) == KQL query (azure-kusto-data)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Producer (`sources/`) | Seeded events; SASL Kafka sink; fixed simulated clock; deterministic dup/late injection | Python 3.11, numpy, kafka-python-ng |
| Reference data (`sources` `generate`) | `dim_*` + `tab_fato004` Parquet | pyarrow (existing) |
| Eventstream | Kafka-protocol ingress → Eventhouse table (no transforms) | Fabric Eventstream (custom endpoint source) |
| KQL database schema | Tables, JSON mapping, update policy, MVs, functions | `DatabaseSchema.kql` in the Git-synced KQLDatabase item |
| Post-deploy script | Loads dimensions and the daily target, sets `target_scale()`, enables OneLake availability | Python, azure-kusto-data, azure-identity |
| Real-time dashboard | KPIs, lag, late/dup/unmatched counters, revenue vs target | Fabric KQLDashboard |
| Activator | Alert when revenue-to-date < 90% of the prorated target → email | Fabric Reflex (alert on a dashboard tile) |
| Lakehouse | Delta history through a OneLake shortcut to Eventhouse tables | Fabric Lakehouse |
| Oracle + tests | Regenerate the exact emitted events, aggregate, compare with KQL | pytest, pandas, azure-kusto-data |
| CI/CD | PR: lint + unit; main: `fabric-cicd` publish + post-deploy; manual end-to-end | GitHub Actions, fabric-cicd |

---

## Key Decisions

### Decision 1: KQL schema lives in `DatabaseSchema.kql`, not in a separate apply script

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-10-02 |

**Context:** The DEFINE planned `kql/*.kql` and an `apply_kql.py`. The KQLDatabase Git item already carries a `DatabaseSchema.kql` that Fabric runs on sync and deploy. It supports create-merge tables, create-or-alter functions and materialized views, alter update policies, and ingestion mappings.

**Choice:** Write all schema objects in `workspace/fruit_juice_db.KQLDatabase/DatabaseSchema.kql`. Only operations it can't do (the OneLake availability policy and data) go to `scripts/post_deploy.py`.

**Rationale:** One deployment path (Git sync for dev, `fabric-cicd` for prod), so there's no drift between two mechanisms. Every supported command is idempotent (`create-merge`, `create-or-alter`).

**Alternatives Rejected:**
1. `kql/` scripts plus `apply_kql.py`: rejected because it duplicates what Fabric already executes, and the two could diverge.
2. Portal click-ops: rejected because the trial expires and SC6 requires a rebuild from Git.

**Consequences:**
- Schema changes are limited to the supported command set. Dropping or renaming objects needs a manual `.drop`, which is documented.
- Dev reflects `DatabaseSchema.kql` on **Update from Git**; prod on `fabric-cicd` publish.

---

### Decision 2: Dedup with a `take_any` materialized view, KPIs as views on top of it, margin in functions

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-10-02 |

**Context:** The KPIs must equal a deduplicated recompute. KQL allows a view on top of another view only when the source is `take_any(*)` dedup, and doesn't allow composite aggregations inside a view.

**Choice:** `sales_dedup` = `sales_enriched | summarize take_any(*) by event_id` (no lookback, since data is lab-sized). `kpi_{product,client,factory}_1m` are views on `sales_dedup` holding only additive sums plus count. The stored functions `kpi_product()` etc. add `margin = revenue − tax − var_cost`. Readers (tests, dashboard) always go through the functions.

**Rationale:** This is exactly the documented pattern. Queries return the materialized part plus the delta, so results are fresh at query time, which makes the oracle comparison exact.

**Alternatives Rejected:**
1. Dedup inside each KPI view: rejected because `take_any` and `sum` can't be nested in one view `summarize`.
2. Dedup in the update policy with a lookup against existing rows: rejected because it races under concurrent ingestion batches.

**Consequences:**
- Three KPI views to maintain; consistent naming keeps that cheap.
- `take_any` makes duplicate payloads collapse even if they differ in `ingested_at`, which is acceptable.

---

### Decision 3: Lateness is defined by producer fields (`emitted_at` vs `event_time`), with a deterministic simulated clock

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-10-02 |

**Context:** With `--speed` > 1 or `--as-of` in the past, `event_time` is simulated and `ingestion_time()` is wall time, so comparing them is meaningless. Exact parity also needs `event_time` to be reproducible.

**Choice:**
- Add `emitted_at` (the producer's clock when the record is actually sent) to the event.
- Add `--fixed-clock`: `event_time(seq) = as_of 00:00 UTC + seq / rate` seconds, where `rate` is events per simulated second, matching the existing `iter_events` semantics.
- Late events are held and sent after `--late-delay` simulated seconds, keeping their original `event_time`.
- In KQL, `is_late = emitted_at − event_time > late_threshold()` (2 min; the default delay is 5 min).

**Rationale:** The data is fully deterministic, so the oracle needs no read-back. It mirrors Kafka's record timestamp vs event time and works at any speed.

**Alternatives Rejected:**
1. `ingestion_time() − event_time`: rejected because it breaks with simulated time and is flaky near the threshold.
2. Reading `event_time` back from KQL in the oracle: rejected because it weakens the test (the oracle would trust pipeline output).

**Consequences:**
- The event schema gains one additive column, `emitted_at`.
- The dashboard still shows real ingestion lag (`ingested_at − emitted_at`), which is meaningful only for runs at `--speed 1` without `--as-of`.

---

### Decision 4: The Eventstream destination uses processed ingestion, not Direct Ingestion

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-10-02 |

**Context:** Microsoft Learn says Eventhouse destinations in Direct Ingestion mode must be reconnected manually after import or deploy.

**Choice:** Configure the Eventhouse destination with "event processing before ingestion" (no operators), JSON input, into the existing `sales_raw` table using mapping `sales_raw_json`. `parameter.yml` rewrites workspace, Eventhouse and KQL DB IDs per environment with `$items.*.$id` / `$workspace.id`.

**Rationale:** Keeps deploys hands-off. The mapping is owned by `DatabaseSchema.kql`.

**Alternatives Rejected:**
1. Direct Ingestion: rejected because of manual rebinding after every deploy.

**Consequences:**
- Slightly higher latency than direct ingestion; well within the 120 s SLA.
- The custom endpoint key differs per environment, so `.env` holds the connection string of whichever environment you stream to.

---

### Decision 5: The Activator rule runs on a dashboard tile backed by `revenue_vs_target()`, with a computed `target_scale()`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-10-02 |

**Context:** `tab_fato004` daily targets (≈ R$ millions per day, all clients) and stream revenue (rate × 86,400 × ~R$400 per event) are on unrelated scales (A-006). The rule must also follow simulated time.

**Choice:**
- `post_deploy.py` loads `revenue_target_daily` (`tab_fato004` summed per day: 365 rows per year, not 5.7k per month).
- It writes `target_scale()` = `nominal_rate × 86,400 × mean_event_revenue / mean_daily_target`, with `mean_event_revenue` from 10,000 locally generated events.
- `revenue_vs_target()` uses `now_sim = max(event_time)` for the current day, `target_to_date = target × scale × elapsed_fraction`, and returns `pct_of_target`.
- A dashboard tile shows it, and the Activator alert on that tile fires when `pct_of_target < 90`, with a 15 min snooze (KB alerting-rules).

**Rationale:** Running the producer at the nominal rate gives about 100%, and half the rate gives about 50%, so the alert fires. That's demoable in minutes with `--speed`.

**Alternatives Rejected:**
1. Raw target without scaling: rejected because it always fires or never fires.
2. Per client × product targets: rejected under YAGNI; the daily total demonstrates the pattern.
3. Activator directly on the Eventstream: rejected because it can't join the target or compute cumulative-to-date.

**Consequences:**
- Activator Git support is preview. If the Reflex can't round-trip through `fabric-cicd`, `docs/runbook.md` gives the 5-step manual setup, and SC6 notes this exception.

---

### Decision 6: Small reference loads through inline `.set-or-replace … <| datatable(...)`, not queued ingestion

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-10-02 |

**Context:** The data is 126 dimension rows plus ≤ 366 target rows. Queued ingestion takes 3–5 min and needs the ingest SDK and a staging step.

**Choice:** `post_deploy.py` renders each table as a KQL `datatable` literal and runs `.set-or-replace <table> <| datatable(...)[...]` through `azure-kusto-data`, in batches of 500 rows (first batch `.set-or-replace`, the rest `.set-or-append`).

**Rationale:** Idempotent, synchronous, one dependency, instant.

**Alternatives Rejected:**
1. `azure-kusto-ingest` queued ingestion: rejected because of its latency and extra dependency for a tiny load.

**Consequences:**
- Not suitable for large tables, which is fine at this scale.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sources/src/generator/stream.py` | Modify | `emitted_at` field; `fixed_clock`; `inject_faults()` (deterministic dup/late per seq, TAG 4); start at `now()` when no `--as-of` | @python-developer | None |
| 2 | `sources/src/generator/sinks.py` | Modify | KafkaSink: SASL_SSL settings from `.env`; fail-fast metadata check; delivery-error tracking → non-zero exit | @python-developer | None |
| 3 | `sources/src/generator/cli.py` | Modify | Flags `--fixed-clock`, `--dup-ratio`, `--late-ratio`, `--late-delay`; exit codes (2 config, 3 delivery) | @python-developer | 1, 2 |
| 4 | `sources/.env.example` | Modify | `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD` | (general) | 2 |
| 5 | `sources/tests/test_stream.py` | Modify | Fixed clock, `emitted_at`, fault-injection determinism (AT-011), count semantics | @test-generator | 1, 3 |
| 6 | `sources/tests/test_sinks.py` | Create | KafkaSink config from env (mocked `KafkaProducer`), delivery-failure exit path (AT-007 unit) | @test-generator | 2 |
| 7 | `sources/README.md` | Modify | Document the new flags and fields | @code-documenter | 1–3 |
| 8 | `workspace/fruit_juice_eh.Eventhouse/` (`.platform`, `EventhouseProperties.json`) | Create (Git sync) | Eventhouse item | @fabric-architect | None |
| 9 | `workspace/fruit_juice_db.KQLDatabase/DatabaseSchema.kql` | Create | Tables, JSON mapping, `enrich_sales()` + update policy, `sales_dedup`, KPI views, functions | @fabric-logging-specialist | 8 |
| 10 | `workspace/fruit_juice_db.KQLDatabase/{.platform, DatabaseProperties.json}` | Create (Git sync) | KQL DB item metadata | @fabric-architect | 8 |
| 11 | `workspace/sales_stream.Eventstream/` | Create (portal → Git sync) | Custom endpoint source → Eventhouse destination (processed ingestion, `sales_raw_json`) | @fabric-pipeline-developer | 9 |
| 12 | `workspace/sales_dashboard.KQLDashboard/` | Create (portal → Git sync) | Tiles over `kpi_*()`, `late_events()`, `unmatched_dims()`, `revenue_vs_target()`, lag | @fabric-logging-specialist | 9 |
| 13 | `workspace/revenue_alerts.Reflex/` | Create (portal → Git sync) | Alert on the revenue-vs-target tile: `pct_of_target < 90` → email, 15 min snooze | @fabric-logging-specialist | 12 |
| 14 | `workspace/fruit_juice_lh.Lakehouse/` (+ `shortcuts.metadata.json`) | Create (portal → Git sync) | OneLake shortcuts to `sales_enriched`, `dim_*` | @fabric-architect | 9, 17 |
| 15 | `parameter.yml` | Create | `fabric-cicd` replacements per environment (dev/prod): workspace, Eventhouse and KQL DB IDs, query URI | @fabric-cicd-specialist | 8–14 |
| 16 | `config/pipeline.toml` | Create | Tunables: `late_threshold`, `demo.nominal_rate`, `target.years`, `target.mean_sample` | (general) | None |
| 17 | `scripts/post_deploy.py` | Create | Load `dim_*` + `revenue_target_daily`; write `target_scale()` and `late_threshold()`; enable OneLake availability on tables | @python-developer | 9, 16 |
| 18 | `scripts/kusto.py` | Create | Shared Kusto client (`FABRIC_AUTH=sp\|cli`), `datatable` rendering, query helpers (used by 17 and tests) | @python-developer | None |
| 19 | `scripts/deploy.py` | Create | `fabric-cicd` publish for an environment (`--env dev\|prod`) with a selectable credential | @fabric-cicd-specialist | 15 |
| 20 | `pyproject.toml` (repo root) | Create | Root project: azure-kusto-data, azure-identity, fabric-cicd, pandas, pytest, ruff; `sources` as a path dependency | (general) | None |
| 21 | `.env.example` (repo root) | Create | `KUSTO_QUERY_URI`, `KUSTO_DATABASE`, `FABRIC_AUTH`, `AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET`, `FABRIC_WORKSPACE_ID` | (general) | None |
| 22 | `tests/oracle.py` | Create | Regenerate emitted events (no sleep), dedup, 1-minute KPIs, late/dup counts with pandas | @test-generator | 1, 3 |
| 23 | `tests/unit/test_oracle.py` | Create | Oracle on fixed seeds; dup/late accounting; `target_scale` math | @test-generator | 22, 17 |
| 24 | `tests/unit/test_schema.py` | Create | Static checks of `DatabaseSchema.kql`: every referenced table, view and function is defined; mapping columns = event fields | @test-generator | 9 |
| 25 | `tests/e2e/conftest.py` | Create | `e2e` marker; skips without env; clears tables; runs producer subprocess; waits for counts | @test-generator | 18 |
| 26 | `tests/e2e/test_pipeline.py` | Create | AT-001–AT-007, AT-010 against a live database | @test-generator | 22, 25 |
| 27 | `.github/workflows/ci.yml` | Create | PR: ruff + `pytest -m "not e2e"` (root + `sources/`) | @ci-cd-specialist | 20 |
| 28 | `.github/workflows/deploy.yml` | Create | Push to main: `deploy.py --env prod` + `post_deploy.py --env prod` (service principal secrets) | @fabric-cicd-specialist | 17, 19 |
| 29 | `.github/workflows/e2e.yml` | Create | `workflow_dispatch`: e2e suite against dev (needs Eventstream connection string secret) | @ci-cd-specialist | 26 |
| 30 | `.gitignore` (repo root) | Create | `.env`, `.venv`, `data/`, caches | (general) | None |
| 31 | `docs/runbook.md` | Create | Bootstrap from zero (AT-009): capacity/workspaces, SP grant, Git connect, portal steps for items 11–14, connection string, demo + alert (AT-008), Activator fallback | @code-documenter | all |
| 32 | `README.md` (repo root) | Modify | Status, architecture, late-data semantics vs Flink (G12), quick start | @code-documenter | 31 |

**Total Files:** 32 entries (several are item folders)

> Items 8, 10, 11–14 are **created in the dev portal once and committed by Fabric Git integration**, not hand-written. Their JSON formats are generated by Fabric and not reliably hand-authorable. Build creates `DatabaseSchema.kql` (9) by hand and writes the portal steps for the rest in `docs/runbook.md`. **Prerequisite:** this folder must become a Git repo with a GitHub remote before Git sync. It isn't one today.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1, 2, 3, 17, 18 | Producer and scripts: dataclasses, typed Python, the existing `sources/` idioms |
| @test-generator | 5, 6, 22–26 | pytest fixtures, mocks for `KafkaProducer`, e2e markers |
| @fabric-logging-specialist | 9, 12, 13 | KQL tables, MVs, functions, real-time dashboards, Activator (its KB: eventhouse-basics, kql-queries, alerting-rules) |
| @fabric-architect | 8, 10, 14 | Eventhouse/Lakehouse item layout, OneLake availability and shortcuts |
| @fabric-pipeline-developer | 11 | Eventstream source/destination configuration |
| @fabric-cicd-specialist | 15, 19, 28 | `fabric-cicd`, `parameter.yml`, Fabric deployment |
| @ci-cd-specialist | 27, 29 | GitHub Actions workflows |
| @code-documenter | 7, 31, 32 | Runbook and READMEs |
| (general) | 4, 16, 20, 21, 30 | Small config files; no specialist needed |

**Agent Discovery:**
- Scanned: `.claude/agents/**/*.md` (68 agents)
- Matched by: file type (`.kql`, `.yml`, `.py`), purpose keywords (KQL, Eventstream, fabric-cicd), path patterns (`workspace/`, `sources/`), KB domains (`microsoft-fabric`, `testing`)

---

## Code Patterns

### Pattern 1: `DatabaseSchema.kql` (tables, mapping, update policy, dedup and KPI views, functions)

```kusto
// KQL script - executed by Fabric on Git sync / fabric-cicd deploy. Supported commands only:
// .create-merge table, .create-or-alter function|materialized-view|ingestion mapping, .alter table policy update

.create-merge table sales_raw (event_id:string, seq:long, event_time:datetime, emitted_at:datetime, cod_dia:string, cod_cliente:string, cod_produto:string, cod_fabrica:string, cod_organizacional:string, faturamento:real, imposto:real, custo_variavel:real, unidades:real, quantidade_vendida:real)

.create-or-alter table sales_raw ingestion json mapping 'sales_raw_json' '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"seq","path":"$.seq","datatype":"long"},{"column":"event_time","path":"$.event_time","datatype":"datetime"},{"column":"emitted_at","path":"$.emitted_at","datatype":"datetime"},{"column":"cod_dia","path":"$.cod_dia","datatype":"string"},{"column":"cod_cliente","path":"$.cod_cliente","datatype":"string"},{"column":"cod_produto","path":"$.cod_produto","datatype":"string"},{"column":"cod_fabrica","path":"$.cod_fabrica","datatype":"string"},{"column":"cod_organizacional","path":"$.cod_organizacional","datatype":"string"},{"column":"faturamento","path":"$.faturamento","datatype":"real"},{"column":"imposto","path":"$.imposto","datatype":"real"},{"column":"custo_variavel","path":"$.custo_variavel","datatype":"real"},{"column":"unidades","path":"$.unidades","datatype":"real"},{"column":"quantidade_vendida","path":"$.quantidade_vendida","datatype":"real"}]'

.create-merge table dim_cliente (Cod_Cliente:string, Desc_Cliente:string, Cod_Cidade:string, Desc_Cidade:string, Cod_Estado:string, Desc_Estado:string, Cod_Regiao:string, Desc_Regiao:string, Cod_Segmento:string, Desc_Segmento:string)
.create-merge table dim_produto (Cod_Produto:string, Desc_Produto:string, Atr_Tamanho:string, Atr_Sabor:string, Cod_Marca:string)
.create-merge table dim_marca (Cod_Marca:string, Desc_Marca:string, Cod_Categoria:string)
.create-merge table dim_categoria (Cod_Categoria:string, Desc_Categoria:string)
.create-merge table dim_fabrica (Cod_Fabrica:string, Desc_Fabrica:string)
.create-merge table dim_organizacional (Cod_Filho:string, Desc_Filho:string, Cod_Pai:string, Esquerda:int, Direita:int, Nivel:int)
.create-merge table revenue_target_daily (cod_dia:string, day:datetime, meta_faturamento:real)

.create-merge table sales_enriched (event_id:string, seq:long, event_time:datetime, emitted_at:datetime, ingested_at:datetime, is_late:bool, cod_dia:string, cod_cliente:string, cod_produto:string, cod_fabrica:string, cod_organizacional:string, faturamento:real, imposto:real, custo_variavel:real, unidades:real, quantidade_vendida:real, desc_cliente:string, desc_regiao:string, desc_produto:string, desc_marca:string, desc_categoria:string, desc_fabrica:string)

// Overwritten by post_deploy.py from config/pipeline.toml; defaults keep the schema valid on first sync.
.create-or-alter function with (folder='config') late_threshold() { 2m }
.create-or-alter function with (folder='config') target_scale() { 1.0 }

.create-or-alter function with (folder='etl') enrich_sales() {
    sales_raw
    | extend ingested_at = ingestion_time(), is_late = emitted_at - event_time > late_threshold()
    | lookup kind=leftouter (dim_cliente | project cod_cliente = Cod_Cliente, desc_cliente = Desc_Cliente, desc_regiao = Desc_Regiao) on cod_cliente
    | lookup kind=leftouter (dim_produto
        | lookup kind=leftouter dim_marca on Cod_Marca
        | lookup kind=leftouter dim_categoria on Cod_Categoria
        | project cod_produto = Cod_Produto, desc_produto = Desc_Produto, desc_marca = Desc_Marca, desc_categoria = Desc_Categoria) on cod_produto
    | lookup kind=leftouter (dim_fabrica | project cod_fabrica = Cod_Fabrica, desc_fabrica = Desc_Fabrica) on cod_fabrica
    | project event_id, seq, event_time, emitted_at, ingested_at, is_late, cod_dia, cod_cliente, cod_produto, cod_fabrica,
              cod_organizacional, faturamento, imposto, custo_variavel, unidades, quantidade_vendida,
              desc_cliente, desc_regiao, desc_produto, desc_marca, desc_categoria, desc_fabrica
}

.alter table sales_enriched policy update @'[{"IsEnabled": true, "Source": "sales_raw", "Query": "enrich_sales()", "IsTransactional": true, "PropagateIngestionProperties": false}]'

.create-or-alter materialized-view with (folder='kpi') sales_dedup on table sales_enriched {
    sales_enriched | summarize take_any(*) by event_id
}

.create-or-alter materialized-view with (folder='kpi') kpi_product_1m on materialized-view sales_dedup {
    sales_dedup
    | summarize revenue = sum(faturamento), tax = sum(imposto), var_cost = sum(custo_variavel),
                litres = sum(quantidade_vendida), units = sum(unidades), events = count()
      by window_start = bin(event_time, 1m), cod_produto
}
// kpi_client_1m (by cod_cliente) and kpi_factory_1m (by cod_fabrica): identical body, different key.

.create-or-alter function with (folder='kpi') kpi_product() {
    materialized_view('kpi_product_1m') | extend margin = revenue - tax - var_cost
}
.create-or-alter function with (folder='quality') late_events() { materialized_view('sales_dedup') | where is_late }
.create-or-alter function with (folder='quality') unmatched_dims() {
    materialized_view('sales_dedup') | where isempty(desc_cliente) or isempty(desc_produto) or isempty(desc_fabrica)
}
.create-or-alter function with (folder='quality') duplicate_count() {
    toscalar(sales_raw | count) - toscalar(materialized_view('sales_dedup') | count)
}

.create-or-alter function with (folder='alerting') revenue_vs_target() {
    let now_sim = toscalar(materialized_view('sales_dedup') | summarize max(event_time));
    let today = startofday(now_sim);
    let elapsed = todouble(now_sim - today) / todouble(1d);
    let target = toscalar(revenue_target_daily | where day == today | summarize sum(meta_faturamento)) * target_scale();
    materialized_view('sales_dedup')
    | where event_time between (today .. now_sim)
    | summarize revenue_to_date = sum(faturamento)
    | extend day = today, target_to_date = target * elapsed
    | extend pct_of_target = iff(target_to_date > 0, round(100.0 * revenue_to_date / target_to_date, 1), real(null))
}
```

### Pattern 2: Deterministic clock and fault injection (`sources/src/generator/stream.py`)

```python
_TAG_FAULT = 4


def fixed_clock(start: datetime, rate: float) -> Callable[[int], datetime]:
    """Simulated time as a pure function of seq: event N happens N/rate simulated seconds after start."""
    return lambda seq: start + timedelta(seconds=seq / rate)


def inject_faults(events: Iterable[StreamEvent], seed: int, *, dup_ratio: float = 0.0, late_ratio: float = 0.0,
                  late_delay: timedelta = timedelta(minutes=5)) -> Iterator[StreamEvent]:
    """Deterministic per (seed, seq): a late event is held and emitted once the clock passes event_time + delay
    (keeping its original event_time); a duplicate is re-sent, identical, right after the original."""
    held: list[StreamEvent] = []          # ordered by release time, since event_time is monotonic
    for event in events:
        while held and held[0].event_time + late_delay <= event.event_time:
            late = held.pop(0)
            yield replace(late, emitted_at=event.event_time)
        rng = rng_for(seed, _TAG_FAULT, event.seq)
        is_dup, is_late = rng.random() < dup_ratio, rng.random() < late_ratio
        if is_late:
            held.append(event)
            continue
        yield event
        if is_dup:
            yield event
    for late in held:                     # end of stream: release with the delay applied
        yield replace(late, emitted_at=late.event_time + late_delay)
```

`StreamEvent` gains `emitted_at: datetime` (equal to `event_time` unless the event is late) and `to_dict()` serialises it like `event_time`. Both `rng.random()` draws always happen, so the dup decision never depends on the late ratio. A late event is never duplicated, which keeps the accounting simple.

### Pattern 3: KafkaSink security from `.env`, fail fast

```python
class KafkaSink:
    def __init__(self, dataset: str):
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise RuntimeError("the kafka sink needs: uv sync --extra stream") from e
        env = parse_env()
        self._topic = env.get("KAFKA_TOPIC", f"{dataset}.sales")
        security = {k: v for k, v in {
            "security_protocol": env.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            "sasl_mechanism": env.get("KAFKA_SASL_MECHANISM"),
            "sasl_plain_username": env.get("KAFKA_SASL_USERNAME"),
            "sasl_plain_password": env.get("KAFKA_SASL_PASSWORD"),
        }.items() if v}
        self._producer = KafkaProducer(
            bootstrap_servers=env.get("KAFKA_BOOTSTRAP", "127.0.0.1:9094").split(","),
            acks="all", retries=5, request_timeout_ms=30_000, **security,
            key_serializer=lambda k: k.encode("utf-8"),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )
        if not self._producer.partitions_for(self._topic):   # auth/topic errors surface here, not at close
            raise RuntimeError(f"cannot reach topic {self._topic!r} on {env.get('KAFKA_BOOTSTRAP')}")
        self.failures = 0

    def write(self, event: StreamEvent) -> None:
        d = event.to_dict()
        key = f"{d['cod_cliente']}|{d['cod_produto']}|{d['cod_fabrica']}"
        self._producer.send(self._topic, key=key, value=d).add_errback(self._on_error)

    def _on_error(self, exc: Exception) -> None:
        self.failures += 1

    def close(self) -> None:
        self._producer.flush(timeout=30)
        self._producer.close()
```

The CLI returns exit code 3 when `sink.failures > 0` and 2 on `RuntimeError` at construction (AT-007). In `.env` for the Eventstream: `KAFKA_SECURITY_PROTOCOL=SASL_SSL`, `KAFKA_SASL_MECHANISM=PLAIN`, `KAFKA_SASL_USERNAME=$ConnectionString`, and `KAFKA_SASL_PASSWORD=<connection string-primary key>`. Because `parse_env` doesn't expand `$`, the literal `$ConnectionString` survives.

### Pattern 4: Shared Kusto client and inline reference loads (`scripts/kusto.py`)

```python
import os

from azure.identity import AzureCliCredential, ClientSecretCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder

BATCH = 500


def client() -> KustoClient:
    uri = os.environ["KUSTO_QUERY_URI"]
    if os.environ.get("FABRIC_AUTH", "cli") == "sp":
        cred = ClientSecretCredential(os.environ["AZURE_TENANT_ID"], os.environ["AZURE_CLIENT_ID"],
                                      os.environ["AZURE_CLIENT_SECRET"])
    else:
        cred = AzureCliCredential()
    return KustoClient(KustoConnectionStringBuilder.with_azure_token_credential(uri, cred))


def _literal(value) -> str:
    if value is None:
        return "dynamic(null)"
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return repr(value)


def replace_table(kc: KustoClient, db: str, table: str, schema: str, rows: list[tuple]) -> None:
    """Idempotent: first batch .set-or-replace, rest .set-or-append (all inline datatable literals)."""
    for i in range(0, max(len(rows), 1), BATCH):
        verb = ".set-or-replace" if i == 0 else ".set-or-append"
        body = ",".join(",".join(_literal(v) for v in row) for row in rows[i:i + BATCH])
        kc.execute_mgmt(db, f"{verb} {table} <| datatable({schema})[{body}]")
```

`post_deploy.py` also runs:
- `.create-or-alter function with (folder='config') target_scale() { <value> }` and `late_threshold()`.
- `.alter-merge table <t> policy mirroring dataformat=parquet with (IsEnabled=true)` for `sales_enriched` and `dim_*` (OneLake availability). The exact command is to be confirmed against Learn during build; fallback is the KQL DB UI toggle, documented in the runbook.

### Pattern 5: Oracle (`tests/oracle.py`)

```python
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from generator.config import calibration_path, load_config
from generator.model import Model, load_calibration
from generator.stream import EventGenerator, fixed_clock, inject_faults

MEASURES = {"revenue": "faturamento", "tax": "imposto", "var_cost": "custo_variavel",
            "litres": "quantidade_vendida", "units": "unidades"}


def emitted_events(seed: int, as_of: date, count: int, rate: float, dup: float, late: float,
                   late_delay_s: float) -> pd.DataFrame:
    cfg = load_config(seed=seed)
    gen = EventGenerator(Model(load_calibration(calibration_path(cfg)), cfg, last_year=as_of.year), as_of)
    clock = fixed_clock(datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc), rate)
    events = (gen.event(seq, clock(seq)) for seq in range(count))
    out = inject_faults(events, seed, dup_ratio=dup, late_ratio=late, late_delay=timedelta(seconds=late_delay_s))
    return pd.DataFrame([e.to_dict() for e in out]).assign(
        event_time=lambda d: pd.to_datetime(d.event_time), emitted_at=lambda d: pd.to_datetime(d.emitted_at))


def expected_kpis(emitted: pd.DataFrame, key: str) -> pd.DataFrame:
    dedup = emitted.drop_duplicates("event_id")
    agg = (dedup.assign(window_start=dedup.event_time.dt.floor("1min"))
           .groupby(["window_start", key])
           .agg(**{k: (v, "sum") for k, v in MEASURES.items()}, events=("event_id", "count"))
           .reset_index())
    return agg.assign(margin=agg.revenue - agg.tax - agg.var_cost)
```

The e2e test runs the producer with the same arguments (`--fixed-clock --seed --as-of --count --rate --dup-ratio --late-ratio --late-delay --no-jitter`). It waits until `sales_raw | count` equals `len(emitted)`, then compares `kpi_product()`, `kpi_client()` and `kpi_factory()` with `expected_kpis`. Rows are joined on the keys: no missing or extra rows, and |diff| ≤ 0.005 on every measure.

### Pattern 6: Configuration structure

```toml
# config/pipeline.toml
[kql]
late_threshold = "2m"        # written into late_threshold() by post_deploy.py

[demo]
nominal_rate = 5.0            # events per simulated second that should hit ~100% of the daily target
target_mean_sample = 10000    # events generated locally to estimate mean revenue per event

[target]
years = [2026]                # revenue_target_daily is loaded for these years (365 rows each)

[e2e]
seed = 42
as_of = "2026-10-02"
count = 2000
rate = 20.0
dup_ratio = 0.05
late_ratio = 0.05
late_delay_s = 300
timeout_s = 300
```

```yaml
# parameter.yml (fabric-cicd); "dev"/"prod" are the environment keys passed by scripts/deploy.py
find_replace:
  - find_value: "<dev-workspace-guid>"
    replace_value:
      prod: "$workspace.id"
  - find_value: "<dev-kqldb-guid>"
    replace_value:
      prod: "$items.KQLDatabase.fruit_juice_db.$id"
  - find_value: "<dev-eventhouse-guid>"
    replace_value:
      prod: "$items.Eventhouse.fruit_juice_eh.$id"
  - find_value: "<dev-query-uri>"
    replace_value:
      prod: "$items.Eventhouse.fruit_juice_eh.$queryserviceuri"
```

---

## Data Flow

```text
1. post_deploy.py (once per environment, re-runnable)
   → dim_* (126 rows), revenue_target_daily (365/year), target_scale(), late_threshold(), OneLake policies
   │
2. generator stream --sink kafka [--fixed-clock] [--dup-ratio p --late-ratio q --late-delay s]
   → JSON events (event_time, emitted_at) over SASL_SSL to the Eventstream custom endpoint
   │
3. Eventstream (no operators) → Eventhouse destination (processed ingestion, mapping sales_raw_json) → sales_raw
   │
4. Update policy enrich_sales(): lookup dims, is_late, ingested_at → sales_enriched (transactional)
   │
5. MV sales_dedup (take_any by event_id) → MVs kpi_{product,client,factory}_1m (1-minute sums)
   │
6. Functions kpi_*(), late_events(), unmatched_dims(), duplicate_count(), revenue_vs_target()
   │        ├─► real-time dashboard tiles (auto refresh 30 s)
   │        ├─► Activator alert on the revenue_vs_target tile (pct_of_target < 90 → email)
   │        └─► e2e tests (compare with oracle)
   │
7. OneLake availability: sales_enriched, dim_* → Delta → Lakehouse shortcuts (history; ≤ 15 min)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Eventstream custom endpoint | Kafka protocol (kafka-python-ng) | SASL_SSL PLAIN, `$ConnectionString` + per-environment connection string (`.env` / GitHub secret) |
| Eventhouse KQL DB | azure-kusto-data (query + mgmt) | `AzureCliCredential` (local) or `ClientSecretCredential` (service principal, CI) via `FABRIC_AUTH` |
| Fabric REST (deploy) | fabric-cicd | Same credential choice; SP requires the tenant setting "Service principals can use Fabric APIs" plus workspace Contributor/Admin |
| Fabric Git integration | GitHub repo ↔ dev workspace (`workspace/` folder) | GitHub account connection (portal) |
| Activator | Email action | Fabric user mailbox |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit (producer) | Fixed clock, `emitted_at`, fault-injection determinism and counts, KafkaSink config and failure path | `sources/tests/test_stream.py`, `test_sinks.py` | pytest, `unittest.mock` | All new branches |
| Unit (pipeline) | Oracle aggregation, `target_scale`, `datatable` literal escaping, `DatabaseSchema.kql` references and mapping | `tests/unit/*` | pytest, pandas | All pure functions |
| E2E (live, manual dispatch) | Producer → Eventstream → KQL → views vs oracle | `tests/e2e/test_pipeline.py` | pytest `-m e2e`, azure-kusto-data, subprocess | AT-001–007, AT-010 |
| Manual (runbook) | Alert email; rebuild from zero | `docs/runbook.md` checklist | Portal + scripts | AT-008, AT-009 |

| Acceptance test | Covered by |
|-----------------|-----------|
| AT-001 Happy path parity | e2e `test_parity` (count 2000, no faults) |
| AT-002 Duplicates | e2e `test_duplicates` (dup 0.05): raw > unique; dedup = unique; KPIs equal |
| AT-003 Late events | e2e `test_late` (late 0.05): `late_events()` count = oracle late count; KPIs equal |
| AT-004 Replay | e2e `test_replay`: clear, rerun, compare to the first snapshot |
| AT-005 Idempotent setup | e2e `test_post_deploy_idempotent`: run twice, compare `.show database schema` hash + counts |
| AT-006 Unknown code | e2e `test_unmatched`: inline ingest one crafted row into `sales_raw` → `unmatched_dims()` = 1 |
| AT-007 Auth failure | unit (mocked) + e2e `test_bad_credentials` (exit code 2) |
| AT-008 Alert | Runbook: run at `nominal_rate/2` with `--speed 120` → email; at `nominal_rate` → none |
| AT-009 Rebuild | Runbook checklist on fresh workspaces, then AT-001 against prod |
| AT-010 History | e2e `test_onelake` (opt-in, slow): Lakehouse SQL endpoint count = KQL count after polling ≤ 15 min |
| AT-011 Determinism | unit `test_inject_faults_deterministic` |

Isolation between e2e tests: each test does `.clear table sales_raw data` and `.clear table sales_enriched data`. Materialized views are cleared with `.clear materialized-view <name> data` (confirm the command in build; fallback is `.drop` + re-sync). Then the producer runs with a test-specific seed.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Kafka auth/topic error at startup | `RuntimeError` → CLI exit 2 with a clear message (AT-007) | No |
| Kafka delivery failure | Producer `retries=5`; remaining failures counted → exit 3 after flush | Yes (client) |
| At-least-once redelivery / injected dups | Absorbed by `sales_dedup` | n/a |
| Unknown dimension code | Left lookup keeps the row with null descriptions; `unmatched_dims()` + dashboard tile | No |
| Update policy failure | Transactional: the ingestion into `sales_raw` fails too and Eventstream retries; visible in `.show ingestion failures` (runbook) | Yes (Eventstream) |
| Materialized view disabled by schema mismatch | Only additive schema changes; runbook `.enable materialized-view` | No |
| e2e timeout waiting for counts | Fail with the observed vs expected counts and the last ingestion failures | No |
| Service principal rejected on trial (A-004) | `FABRIC_AUTH=cli` local fallback; documented | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `kql.late_threshold` | timespan string | `2m` | Lateness cut-off written into `late_threshold()` |
| `demo.nominal_rate` | float | `5.0` | Rate (events per simulated second) that should equal 100% of the daily target |
| `target.years` | list[int] | `[2026]` | Years of `revenue_target_daily` to load |
| `e2e.*` | mixed | see Pattern 6 | Seeded parity run parameters |
| `KAFKA_*` (`sources/.env`) | string | PLAINTEXT, local | Eventstream bootstrap, topic, SASL settings |
| `KUSTO_QUERY_URI`, `KUSTO_DATABASE` (`.env`) | string | none | Target KQL database for scripts and tests |
| `FABRIC_AUTH` | `sp` \| `cli` | `cli` | Credential type for Kusto + fabric-cicd |

---

## Security Considerations

- Eventstream connection strings and SP secrets live only in git-ignored `.env` files and GitHub Actions secrets. They're never in `parameter.yml`, the workspace items or logs (the CLI never prints `KAFKA_SASL_PASSWORD`).
- The service principal is scoped to the two lab workspaces (Contributor); no tenant admin APIs.
- `datatable` literals escape quotes and backslashes; the input is generator output, not user input.
- The data is synthetic with no PII (business codes only).

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Producer: per-event line to stderr (existing) plus a summary with `emitted`, `duplicates`, `late`, `failures`; scripts: plain stdout steps |
| Metrics | Dashboard tiles: events/min, ingestion lag p95 (`ingested_at − emitted_at`), `duplicate_count()`, `late_events()` count, `unmatched_dims()` count, `revenue_vs_target()` |
| Tracing | `event_id` / `seq` carried end to end; `.show ingestion failures` and `.show materialized-view <name>` (health) in the runbook |

---

## Pipeline Architecture

### DAG Diagram

```text
[generator stream] ──Kafka──→ [Eventstream] ──→ [sales_raw] ──update policy──→ [sales_enriched] ──OneLake──→ [Lakehouse Delta]
[post_deploy.py] ──→ [dim_*, revenue_target_daily] ──lookup──↗        ↓
                                                              [MV sales_dedup] ──→ [MV kpi_*_1m] ──→ [fn kpi_*()]
                                                                     ↓                                   ↓
                                                     [late_events / unmatched_dims]          [Dashboard] → [Activator]
```

### Partition Strategy

| Table | Partition Key | Granularity | Rationale |
|-------|-------------|-------------|-----------|
| `sales_raw`, `sales_enriched` | none (default extent time) | n/a | Lab volumes (≤ 1M rows); KQL default extents are enough |
| `kpi_*_1m` | `window_start` (group key) | 1 minute | Matches dashboard and oracle grain |

### Incremental Strategy

| Model | Strategy | Key Column | Lookback |
|-------|----------|------------|----------|
| `sales_enriched` | Update policy per ingestion batch | n/a | n/a |
| `sales_dedup` | Materialized view, `take_any` by key | `event_id` | None (whole history; lab scale) |
| `kpi_*_1m` | Materialized view over the dedup view | `window_start` + dimension key | n/a |

### Schema Evolution Plan

| Change Type | Handling | Rollback |
|-------------|----------|----------|
| New event field | Add to `sales_raw` (`.create-merge`), mapping, `enrich_sales()` project, `sales_enriched`; MVs unaffected unless used | Remove from mapping; the column stays (unused) |
| Type change | Not supported in place: new column plus migration (out of scope) | n/a |
| Column removal | Out of scope (DEFINE: schema evolution excluded) | n/a |

### Data Quality Gates

| Gate | Tool | Threshold | Action on Failure |
|------|------|-----------|-------------------|
| KPI parity vs oracle | e2e pytest | 0 mismatched rows, \|Δ\| ≤ 0.005 | Test fails |
| Unique events = produced | e2e pytest (`sales_dedup` count) | = `count` | Test fails |
| Unmatched dimension codes | `unmatched_dims()` dashboard tile | 0 for generated data | Visible on dashboard |
| Freshness | Dashboard lag tile | p95 ≤ 120 s | Visible; e2e timeout |
| Schema references | `tests/unit/test_schema.py` | all referenced objects defined | PR fails |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-02 | design-agent | Initial version. Verified A-001–A-003 against Microsoft Learn and fabric-cicd docs; replaced `kql/` + `apply_kql.py` with `DatabaseSchema.kql`; added `emitted_at`/fixed clock; target as a daily aggregate with `target_scale()`; OneLake availability on tables only |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_STREAMING_FABRIC_PIPELINE.md`
