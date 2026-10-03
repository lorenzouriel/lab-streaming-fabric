# DEFINE: Streaming Fabric Pipeline (Eventstream → Eventhouse KQL → Activator)

> A Fabric Real-Time Intelligence pipeline that ingests the seeded Fruit Juice sales stream, deduplicates it, enriches it and computes windowed KPIs in KQL, alerts on revenue falling below target, and exposes history as Delta. The KPIs are checked for exact parity against a local recompute, and the workspace can be rebuilt from Git.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STREAMING_FABRIC_PIPELINE |
| **Date** | 2026-10-02 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

The streaming lab series has no Microsoft Fabric implementation of its reference patterns: enrichment, windowed KPIs, dedup, late data, alerting, and replay with history. Without one, the author can't practise Fabric Real-Time Intelligence end to end, and portfolio readers can't compare Fabric with the OSS reference on the same KPIs and the same exact-match oracle.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Lab author | Data engineer learning Fabric RTI | Needs hands-on, inspectable practice with Eventstream, KQL update policies, materialized views and Activator, rebuildable after the 60-day trial expires |
| Portfolio reader / reviewer | Hiring manager or peer engineer | Needs proof that each pattern works on Fabric, meaning passing parity tests and a live dashboard, not a diagram |
| Streaming lab series | Sibling labs (`lab-streaming-oss`, `-databricks`, `-snowflake`) | Needs a Fabric counterpart with the same KPI definitions and oracle so the platforms can be compared |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: `sources/` producer streams events into an Eventstream custom endpoint over the Kafka protocol with SASL_SSL auth from `.env` |
| **MUST** | G2: `sources/` producer can inject duplicates and late events deterministically per seed (`--dup-ratio`, `--late-ratio`) |
| **MUST** | G3: Eventhouse KQL objects (raw table, enrichment update policy, dedup view, 1-minute KPI views, late-event function) created by idempotent, versioned `.kql` scripts |
| **MUST** | G4: Dimensions (`dim_*`) and revenue target (`tab_fato004`) loaded into KQL tables by an idempotent script from `generator generate` Parquet |
| **MUST** | G5: An automated end-to-end parity test: KQL KPIs exactly equal a local pandas recompute of the same seeded events, including the dedup and late-count checks |
| **MUST** | G6: Replay (clear the tables, same seed, `--start-seq 0`) reproduces identical KPIs |
| **MUST** | G7: The workspace (Eventhouse, KQL DB, Eventstream, dashboard, Activator, Lakehouse) is defined in Git and can be recreated on a fresh trial capacity by scripts alone |
| **SHOULD** | G8: An Activator rule emails when simulated daily cumulative revenue falls below the prorated `tab_fato004` daily target |
| **SHOULD** | G9: A real-time dashboard shows the KPIs, ingestion lag, and late and duplicate counters |
| **SHOULD** | G10: CI: a PR runs ruff and the unit tests; a merge to `main` publishes dev → prod with `fabric-cicd` and applies the KQL scripts and dimensions to prod |
| **SHOULD** | G11: OneLake availability exposes the dedup and KPI tables as Delta through a Lakehouse shortcut |
| **COULD** | G12: README section comparing late-data semantics: KQL (late events aggregated into their window and flagged) vs Flink (dropped after the watermark) |

---

## Success Criteria

- [ ] SC1: `generator stream --sink kafka --count 2000` delivers **2,000/2,000** events into `sales_raw`, with no auth errors, within **120 s** of the producer finishing
- [ ] SC2: For a seeded run (`--count 2000`, fixed `--as-of`, fixed seed), every row of every `kpi_*_1m` view equals the pandas recompute: **0 mismatched rows**, with sums compared at a tolerance of **≤ 0.005** (2-decimal currency)
- [ ] SC3: With `--dup-ratio 0.05 --late-ratio 0.05`, the KPIs still match the deduplicated recompute (0 mismatches), the `sales_dedup` count equals the number of unique `event_id`s, and the late count equals the injected late count **exactly**
- [ ] SC4: Replay of the same seeded run after clearing the tables gives KPIs **identical** to the first run (0 differing rows)
- [ ] SC5: Re-running `apply_kql.py` and `load_dims.py` against an existing database makes **0 schema changes** and leaves dimension and target row counts unchanged (57 / 35 / 9 / 3 / 3 / 19 dimension rows)
- [ ] SC6: From an empty trial workspace, scripts and `fabric-cicd` alone (no portal clicks except creating the capacity and workspace, granting the service principal access, and copying the Eventstream connection string) produce a working pipeline that passes SC1 and SC2, in **≤ 30 min**
- [ ] SC7: The Activator rule sends an email within **5 min** of a demo run whose revenue rate is set below the prorated target, and sends **none** in a run at or above it
- [ ] SC8: PR workflow finishes green with ruff plus unit tests in **≤ 5 min**; merge workflow publishes to prod and applies KQL without manual steps
- [ ] SC9: `sales_enriched` and the `dim_*` tables are readable as Delta from the Lakehouse, with row counts equal to the KQL counts, within **15 min** of ingestion (OneLake availability latency; KPIs are views, not tables, see DESIGN A-008)

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Happy path parity | Empty KQL tables, dims loaded, seed 42, as-of 2026-10-02 | Producer streams `--count 2000` to the Eventstream endpoint and the test waits for 2,000 raw rows | Every `kpi_*_1m` view equals the pandas recompute (SC2) |
| AT-002 | Duplicates | Same as AT-001 with `--dup-ratio 0.05` | Stream completes | `sales_raw` > 2,000 rows; `sales_dedup` = 2,000 unique `event_id`s; KPIs equal the deduplicated recompute |
| AT-003 | Late events | Same as AT-001 with `--late-ratio 0.05` | Stream completes | Late events count toward the window their `event_time` belongs to; `late_events` count = injected late count; KPIs still equal the recompute |
| AT-004 | Replay | AT-001 has completed | Clear tables and views, re-run identical producer command | KPIs are identical to AT-001 |
| AT-005 | Idempotent setup | Database already provisioned and dims loaded | Run `apply_kql.py` and `load_dims.py` again | No errors; schema unchanged; dimension and target counts unchanged |
| AT-006 | Unknown code | A crafted event with `cod_cliente` not in `dim_cliente` | Ingested | Row lands in `sales_enriched` with null client attributes and is counted by the unmatched-dimension counter; pipeline keeps ingesting |
| AT-007 | Auth failure | `.env` with a wrong Eventstream connection string | Producer starts | Exits non-zero with a clear auth error; no partial silent success |
| AT-008 | Alert fires | Activator rule active, target loaded for the as-of day | Demo run at a revenue rate below the prorated target (`--speed`) | One email within 5 min; no email in a run at or above target |
| AT-009 | Rebuild from Git | Fresh trial workspace pair (dev, prod) | Follow the README bootstrap: Git sync dev, merge → `fabric-cicd` prod, run `apply_kql.py` and `load_dims.py` | AT-001 passes against prod |
| AT-010 | History | OneLake availability enabled | Wait for the OneLake sync after AT-001 | Lakehouse shortcut tables return the same row counts as KQL |
| AT-011 | Determinism (unit) | No Fabric needed | Generate events for (seed, as-of, count) twice, including dup/late injection | Identical event lists; injected dup/late sets identical |

---

## Out of Scope

- Azure Event Hubs (the custom endpoint replaces it)
- Spark Structured Streaming notebooks or any Spark job
- Eventstream in-flight transformations (Eventstream stays pass-through)
- A test workspace stage and Fabric deployment pipelines (dev + prod via `fabric-cicd` only)
- DLQ and schema evolution handling
- Activator actions other than email (Teams, Power Automate)
- Extra KQL querysets and Copilot
- Running the live end-to-end tests on every PR (manual `workflow_dispatch` only)
- Batch facts other than `tab_fato004`, and any changes to the sibling `lab-sources` repo

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Resource | Fabric free trial capacity, which expires after 60 days | Everything must be reproducible from Git and scripts; no persistent click-ops state; avoid idle compute beyond the Eventhouse |
| Technical | Ingestion only via the Eventstream custom endpoint (Kafka protocol, SASL_SSL PLAIN with the connection string) | `sources/` KafkaSink must support SASL_SSL from `.env`; secrets never committed |
| Technical | Processing in KQL only (update policy + materialized views) | Dedup, enrichment, late detection and windows must all be expressible in KQL |
| Technical | `cod_*` codes are strings with leading zeros | String columns end to end (Eventstream mapping, KQL, pandas) |
| Technical | Producer determinism: event N depends only on (seed, as-of, N); `event_time` is wall or simulated time | The oracle must use `event_time` read back from KQL, or a fixed simulated clock, to assign windows |
| Technical | Service principal for `fabric-cicd` and KQL admin | Needs the tenant setting allowing service principals to use the Fabric APIs, plus workspace access |
| Platform | Windows dev machine, Python 3.11+, `uv`; GitHub Actions | Scripts must run on both Windows and Ubuntu runners |
| Timeline | None fixed (lab) | Ordered by MoSCoW; SHOULD items may move to a follow-up |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sources/` (producer changes), `workspace/` (Git-synced Fabric items), `kql/` (numbered idempotent scripts), `scripts/` (`apply_kql.py`, `load_dims.py`), `parameter.yml`, `tests/` (unit + e2e), `.github/workflows/` | `sources/` is already vendored and trimmed (836 lines, 13 tests passing) |
| **KB Domains** | `microsoft-fabric` (eventhouse-basics, kql-queries, real-time-dashboard, alerting-rules, git-integration, deployment-rules, environment-promotion), `streaming`, `testing`, `python`, `data-quality` | KB gaps: Eventstream custom endpoint, Activator item definitions, limits on materialized views over a dedup view. Validate with Context7 or the Microsoft docs in /design |
| **IaC Impact** | New resources | Two workspaces (dev, prod) on the trial capacity; Eventhouse + KQL DB, Eventstream, real-time dashboard, Activator and Lakehouse items; a service principal. No Terraform: Fabric Git integration and `fabric-cicd` |

---

## Data Contract

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| `generator stream --sink kafka` | Kafka-protocol producer → Eventstream custom endpoint (JSON) | 1–20 events/s demo; 2,000 events per parity run | Real-time; in `sales_raw` ≤ 120 s after send | Lab author (`sources/`) |
| `generator generate` → `load_dims.py` | Parquet → KQL tables | 126 dimension rows; `tab_fato004` ~5.7k rows per month | Loaded once per environment, re-runnable | Lab author (`sources/`) |

### Schema Contract (`sales_raw`, from `StreamEvent.to_dict`)
| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| `event_id` | string (UUIDv5) | NOT NULL; unique after dedup | No |
| `seq` | long | NOT NULL, ≥ 0 | No |
| `event_time` | datetime (UTC, ms) | NOT NULL | No |
| `cod_dia` | string `YYYYMMDD` | NOT NULL; equals the date of `event_time` (for late events, the original date) | No |
| `cod_cliente` | string | NOT NULL; FK → `dim_cliente.Cod_Cliente` (unmatched rows counted, not dropped) | No (business codes) |
| `cod_produto` | string | NOT NULL; FK → `dim_produto.Cod_Produto` | No |
| `cod_fabrica` | string (leading zeros) | NOT NULL; FK → `dim_fabrica.Cod_Fabrica` | No |
| `cod_organizacional` | string | NOT NULL; FK → `dim_organizacional.Cod_Filho` | No |
| `faturamento` | real | NOT NULL, > 0 | No |
| `imposto` | real | NOT NULL, ≥ 0 | No |
| `custo_variavel` | real | NOT NULL, ≥ 0 | No |
| `unidades` | real | NOT NULL, ≥ 1 | No |
| `quantidade_vendida` | real | NOT NULL, ≥ 0.5 | No |

KPI measures (mirroring `lab-streaming-oss`): revenue = Σ`faturamento`, tax = Σ`imposto`, variable cost = Σ`custo_variavel`, margin = revenue − tax − variable cost, litres = Σ`quantidade_vendida`, units = Σ`unidades`, event count. Grain: `bin(event_time, 1m)` × {product | client | factory}.

### Freshness SLAs
| Layer | Target | Measurement |
|-------|--------|-------------|
| `sales_raw` | ≤ 120 s from producer send | `ingestion_time() - event_time` (p95, non-late events) |
| `kpi_*_1m` views | Query-time fresh (materialized + delta) | `materialized_view()` reads |
| Lakehouse Delta (OneLake) | ≤ 15 min | Row-count parity check |

### Completeness Metrics
- 100% of produced unique `event_id`s are present in `sales_dedup` after the run (SC1, SC3)
- 0 mismatched KPI rows against the oracle (SC2)
- The unmatched-dimension count is 0 for generated data; it's non-zero only in AT-006

### Lineage Requirements
- Table-level lineage documented in the README: `sales_raw` → `sales_enriched` → `sales_dedup` → `kpi_*_1m` → dashboard, Activator and OneLake
- Not needed: column-level lineage or Purview

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | The Eventstream custom endpoint accepts `kafka-python-ng` producers with SASL_SSL PLAIN (`$ConnectionString` username) | Switch the producer client (e.g. `confluent-kafka`) or use the Event Hubs SDK sink | [ ] |
| A-002 | A materialized view can aggregate over a dedup source: either an MV over a `take_any` MV, or dedup inside each KPI view's source query | Restructure: KPI views as stored functions over `sales_dedup`, or dedup in the update policy with a lookup | [ ] |
| A-003 | Eventstream, KQL database, real-time dashboard and Activator items are all supported by Fabric Git integration and `fabric-cicd` | Unsupported items must be created by a REST script (Fabric items API) and documented as a bootstrap step | [ ] |
| A-004 | A service principal can call the Fabric REST APIs against workspaces on a trial capacity | CI publish runs with a user token (manual) or needs an F-SKU; affects SC6/SC8 | [ ] |
| A-005 | Activator can run a rule over a KQL query or dashboard tile and send email on the trial | Fall back to a dashboard-only alert indicator; G8 becomes COULD | [ ] |
| A-006 | Stream revenue and the `tab_fato004` daily target are on unrelated scales; the demo calibrates `--rate`/`--speed` so the expected simulated-day revenue ≈ target, and a lower rate breaches it | The rule needs a scale factor parameter instead of the raw target | [ ] |
| A-007 | Late injection = the producer emits an event later with its original (earlier) `event_time`; "late" in KQL = `ingestion_time() - event_time` > a fixed threshold | If ingestion lag variance overlaps the threshold, counts are flaky; use an injected-delay margin (e.g. ≥ 5 min of simulated time) well above normal lag | [ ] |
| A-008 | OneLake availability of an Eventhouse table (or a materialized view) is enabled per table and exposed as Delta to a Lakehouse shortcut | Expose `sales_dedup` only, or materialize KPIs into tables via a scheduled `.set-or-append` | [ ] |
| A-009 | Trial capacity CU is enough for always-on Eventhouse + Eventstream at ≤ 20 events/s | Pause between sessions; lower the demo rates | [ ] |

**Note:** A-001 to A-004 are critical and need verification early in /design against current docs (Context7 or Microsoft Learn), since the KB doesn't cover them.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific gap in the lab series, with who is affected and why |
| Users | 3 | Three personas with concrete pain points |
| Goals | 3 | 12 goals with MoSCoW, each traceable to an acceptance test |
| Success | 3 | Numeric criteria (counts, mismatches = 0, latency, time to rebuild) |
| Scope | 2 | Explicit in and out lists; some platform capabilities (A-001 to A-005) are unverified and could force scope changes |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15**

---

## Open Questions

None block Design. The design phase must resolve these as verification tasks:
1. A-002: the exact KQL dedup → KPI materialization shape.
2. A-003/A-004: which items `fabric-cicd` supports, and whether service principals work on the trial.
3. A-006: the Activator rule definition and the demo calibration formula (rate × speed vs daily target).
4. Default injected late delay and the KQL lateness threshold (A-007).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-02 | define-agent | Initial version from BRAINSTORM_STREAMING_FABRIC_PIPELINE.md (`sources/` already vendored and trimmed) |
| 1.1 | 2026-10-02 | design-agent | Status → Designed; SC9 narrowed to tables (OneLake availability does not apply to materialized views); A-001–A-003 verified in DESIGN |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_STREAMING_FABRIC_PIPELINE.md`
