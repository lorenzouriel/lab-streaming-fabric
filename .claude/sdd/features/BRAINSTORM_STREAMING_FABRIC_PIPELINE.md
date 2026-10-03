# BRAINSTORM: Streaming Fabric Pipeline (Eventstream → Eventhouse KQL → Activator)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STREAMING_FABRIC_PIPELINE |
| **Date** | 2026-10-02 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** `lab-streaming-fabric/README.md` describes a streaming and event-driven pipeline on Microsoft Fabric Real-Time Intelligence that replays the Fruit Juice sales data as an event stream. The README's stack:

- Event Hubs as the source.
- Eventstreams with in-flight transformations.
- Eventhouse/KQL for storage and querying.
- Real-time dashboards.
- Activator alerts, for example "revenue drops below target".
- A Spark Structured Streaming bridge into the Lakehouse.
- CI/CD through Fabric Git integration, `fabric-cicd` and deployment pipelines.

**Context Gathered:**
- The repo was scaffold-only: `README.md` and `.claude/`, no code and no git history.
- The README says the lab depends on a *planned* `generator replay` in `lab-sources`. That dependency is **already met** by `generator stream`, which is deterministic per seed (`event_id = uuid5(seed:seq)`) and supports `--as-of`, `--speed`, `--start-seq` and a `kafka` sink.
- **Done during this session (user request):** `lab-sources` was copied into **`sources/`** in this repo and trimmed to what the lab needs:
  - **Kept:** the seeded model, the `stream` command (stdout, file and kafka sinks), and `generate`, which now writes only Parquet for `dim_*` and `tab_fato004`.
  - **Removed:** fit, export, load, validate, the DB sinks and writers, docker compose, and the foundation fact CSVs. Python went from about 2,900 lines to 836.
  - **Bug fixed:** stream seasonality used the real current month instead of `--as-of`, so a seeded replay in another month produced different events, which would have broken the oracle.
  - **Status:** 13 tests pass, and both commands were smoke-tested.
- Because of this, everything previously treated as an "upstream `lab-sources` change" is now an **in-repo change to `sources/`**: SASL_SSL support in the Kafka sink, and `--dup-ratio`/`--late-ratio` injection.
- The `sources/` Kafka sink only sets `bootstrap_servers`. Neither SASL_SSL nor the Eventstream connection-string auth is wired yet.
- Event fields: `event_id, seq, event_time, cod_dia, cod_cliente, cod_produto, cod_fabrica, cod_organizacional, faturamento, imposto, custo_variavel, unidades, quantidade_vendida`. Codes are strings with leading zeros.
- The sibling `lab-streaming-oss` brainstorm sets conventions for the series that this lab mirrors: the KPI set (revenue, tax, variable cost, margin, litres and units per window by product, client and factory), a recompute oracle that must match exactly, and dup/late injection.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sources/` (producer, already vendored), `workspace/` (Git-synced Fabric items), `kql/` (numbered idempotent scripts), `scripts/` (`load_dims.py`, `apply_kql.py`), `parameter.yml`, `tests/`, `.github/workflows/` | Mostly KQL plus Fabric item definitions; Python for the producer, dimension loading and tests |
| Relevant KB Domains | `microsoft-fabric` (eventhouse-basics, kql-queries, real-time-dashboard, alerting-rules, git-integration, deployment-rules, environment-promotion), `streaming`, `testing`, `python`, `data-quality` | No KB coverage for Eventstream custom endpoints, Activator, or materialized-view-over-materialized-view limits; validate those with MCP or docs in /design |
| IaC Patterns | Fabric Git integration and `fabric-cicd` with `parameter.yml`; no Terraform | The workspace has to be fully rebuildable from Git because the trial capacity expires |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | What's the goal relative to the OSS reference lab? | **Mirror the OSS KPIs and oracle, implemented Fabric-natively** | The same KPI definitions and an exact-match oracle, built with Eventstream, KQL update policies and views, and Activator rather than a Flink port |
| 2 | How do events enter Fabric? | **Eventstream custom endpoint** (Kafka protocol) | No Azure subscription or Event Hubs. The producer's Kafka sink needs SASL_SSL with the connection string |
| 3 | Which capacity? | **Fabric free trial** | It expires after 60 days, so everything must be rebuildable from Git and scripts. Keep CU use low: no always-on Spark |
| 4 | Which patterns must the MVP demonstrate? | **All four:** enrichment + windowed KPIs; dedup + late data; Activator alerting; replay + Lakehouse history | Dedup and late data need `--dup-ratio`/`--late-ratio` added to `sources/` |
| 5 | How does data reach the Lakehouse? | **OneLake availability** on the Eventhouse tables | History needs no code. The Spark Structured Streaming bridge is dropped |
| 6 | How do dimensions and the revenue target reach the Eventhouse? | **Script-ingested KQL tables** (`azure-kusto-ingest`, `.set-or-replace`) | Fast lookups inside update policies; idempotent per environment; fed by `sources` `generate` Parquet |
| 7 | What are the KPIs verified against? | **A local Python recompute** | Regenerate the same seeded events (with the same `--as-of`), dedup and aggregate them in pandas, then assert equality with KQL |
| 8 | What CI/CD scope? | **dev + prod via `fabric-cicd`** | Two workspaces on the trial. A PR runs lint and unit tests; a merge publishes to prod; the live parity test runs manually |

---

## Sample Data Inventory

> Samples improve LLM accuracy through in-context learning and few-shot prompting.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `sources/` → `generator stream` (events), `generator generate` (`dim_*` + `tab_fato004` Parquet) | Unbounded stream; dimensions 57 / 35 / 9 / 3 / 3 / 19 rows; target about 5.7k rows per month | Deterministic per (seed, as-of, seq); `--count N` for bounded runs |
| Output examples | None yet | 0 | Defined in /design: `kpi_*_1m` views, `late_events`, dashboard tiles |
| Ground truth | A pandas recompute over the regenerated seeded events (dedup on `event_id`) | Computed per test run | Same seed, count and as-of give the same expected KPIs; no golden files |
| Related code | `sources/src/generator/stream.py`, `sinks.py`, `batch.py`; the OSS brainstorm's KPI definitions | 3 files + 1 doc | The event schema is the KQL `sales_raw` contract |

**How samples will be used:**

- `StreamEvent.to_dict` defines the `sales_raw` table schema and the Eventstream JSON mapping.
- Seeded bounded runs serve as end-to-end fixtures, with the pandas recompute as the oracle.
- The `generate` Parquet output is what `load_dims.py` ingests for enrichment and the Activator target.

---

## Approaches Explored

### Approach A: Thin Eventstream + KQL-native processing ⭐ Recommended

**Description:** The Eventstream custom endpoint passes events through with no transformations into `sales_raw`.
- An update policy enriches each row with the `dim_*` tables and adds `ingest_lag` and `is_late`, writing to `sales_enriched`.
- A materialized view deduplicates on `event_id` (`take_any`).
- Materialized views compute windowed KPIs (`bin(event_time, 1m)` by product, client and factory).

The real-time dashboard and Activator read the KPIs, and OneLake availability exposes the tables as Delta.

**Pros:**
- KQL covers every chosen pattern (dedup, joins, late data, windows) as versioned `.kql` scripts.
- The oracle stays exact, because `materialized_view()` returns the materialized part plus the delta.
- Late events land in their correct window and are also flagged and counted. This contrasts well with Flink's watermark drop.

**Cons:**
- Eventstream's "in-flight transformations" from the README shrink to a footnote.
- Materialized views over a dedup materialized view have restrictions that /design must verify.

**Why Recommended:** It's the best Fabric-native fit for the parity goal. Confidence is **0.85**: KB patterns (`eventhouse-basics`, `kql-queries`, `real-time-dashboard`, `alerting-rules`) but no codebase precedent.

---

### Approach B: Eventstream in-flight processing

**Description:** Eventstream's no-code operators (Manage fields, Filter, Group by with tumbling windows) compute the KPIs before landing. Eventhouse stores only the results.

**Pros:**
- Uses Eventstream as the README describes.

**Cons:**
- No dedup operator, and joins only work stream to stream, not against reference dimensions. That fails two of the four chosen patterns.
- Limited late-data control, and the windowing semantics make an exact oracle hard.

---

### Approach C: Hybrid

**Description:** Eventstream does light in-flight work (typing, a derived margin column, routing malformed events to a side table). KQL does dedup, enrichment and windows as in A.

**Pros:**
- Shows Eventstream transformations and gives a cheap dead-letter-style route.

**Cons:**
- Logic is split across two places, and the Eventstream topology JSON is harder to review and test than `.kql`.
- The DLQ wasn't one of the chosen patterns.

---

## Data Engineering Context (if applicable)

### Source Systems
| Source | Type | Volume Estimate | Current Freshness |
|--------|------|-----------------|-------------------|
| `generator stream --sink kafka` | Kafka-protocol producer → Eventstream custom endpoint | Lab scale: 1–20 events/s for demos; about 2k bounded events per parity test | Real-time |
| `generator generate` | Parquet (`dim_*`, `tab_fato004`) → KQL tables via script | 126 dimension rows; target about 5.7k rows per month | Loaded once per environment |

### Data Flow Sketch
```text
sources/ generator stream --sink kafka (SASL_SSL, Eventstream connection string in .env)
   │   --dup-ratio / --late-ratio (deterministic per seed)
   ▼
Eventstream (custom endpoint, no transforms)
   ▼
Eventhouse / KQL DB
   sales_raw ──update policy──► sales_enriched (join dim_*; ingest_lag, is_late)
                                   ├─ MV sales_dedup      take_any by event_id
                                   ├─ MV kpi_*_1m         bin(event_time,1m) × product|client|factory
                                   └─ fn late_events      where is_late
   dim_* , tab_fato004  ◄── scripts/load_dims.py (.set-or-replace from generate Parquet)
   ▼
Real-time dashboard (KPIs, lag, late and dup counters)
Activator: daily cumulative revenue < prorated tab_fato004 target → email
OneLake availability → Lakehouse shortcut (Delta history)
```

### Key Data Questions Explored
| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | What's the expected data volume? | Tens of events per second at most; about 2k per test run | Trial capacity is plenty; the concern is idle CU burn, not throughput |
| 2 | What freshness SLA is needed? | Seconds to a minute (demo); no formal SLA | Eventstream → Eventhouse streaming ingestion; 1-minute windows |
| 3 | Who consumes the output? | The author (learning), portfolio readers, and Activator | One dashboard plus one Activator rule; tests prove parity |

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A: Thin Eventstream + KQL-native processing |
| **User Confirmation** | 2026-10-02 (this session) |
| **Reasoning** | It covers all four chosen patterns, keeps logic in versionable and testable `.kql`, and keeps the oracle exact |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Eventstream custom endpoint as the entry point | No Azure subscription; stays on Fabric capacity | Azure Event Hubs; both switchable |
| 2 | Producer vendored into `sources/` and trimmed | Self-contained lab; producer changes (SASL, dup/late) land in-repo | Depending on the sibling `lab-sources` repo |
| 3 | All processing in KQL (update policy + materialized views) | Dedup, joins, late data and windows in one place, as scripts | Eventstream operators; a hybrid split |
| 4 | Late events are aggregated into their correct window, flagged and counted | This is how KQL views behave; a documented contrast with Flink's watermark drop | Dropping late events |
| 5 | History via OneLake availability | No code; low CU on the trial | Spark Structured Streaming notebook; an Eventstream → Lakehouse destination |
| 6 | Dimensions and target loaded by a script into KQL tables | Fast update-policy joins; idempotent | A KQL shortcut to the Lakehouse; streaming the dimensions |
| 7 | Oracle = local pandas recompute of the same seeded events | Exact, no extra infrastructure; mirrors the OSS oracle | A file-sink tee; visual checks only |
| 8 | dev + prod workspaces, `fabric-cicd` on merge, manual live E2E test | Fits the trial; one promotion mechanism | dev/test/prod + deployment pipelines; Git sync only |
| 9 | Stream seasonality tied to `--as-of` (bug fix, already applied) | A replay in a different month must give identical events | Keeping the wall-clock month |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Azure Event Hubs | The Eventstream custom endpoint covers ingestion without an Azure subscription | Yes |
| Spark Structured Streaming bridge into the Lakehouse | OneLake availability provides Delta history with no code; Spark is covered by `lab-streaming-databricks` | Yes |
| Eventstream in-flight transformations | Approach A keeps all logic in KQL | Yes |
| test workspace + Fabric deployment pipelines | dev + prod with `fabric-cicd` is enough on a trial | Yes |
| DLQ and schema evolution | Not selected for the MVP; unknown codes are counted through null dimension joins instead | Yes |
| Teams and Power Automate Activator actions | Email proves the rule fires | Yes |
| Extra KQL querysets and Copilot | Not needed for the MVP or the tests | Yes |
| `lab-sources` features in `sources/` (fit, export, load, validate, CSV/JSON/Mongo/SQL writers, DB sinks, docker compose) | Not used by this lab; already removed | Yes (from `lab-sources`) |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Architecture concept (flow, update policy and views, dimension loading, replay, late-data semantics) | ✅ | "Looks right" | No |
| Components, tests, CI/CD, error handling, YAGNI cuts | ✅ | "Looks right" | No. Afterwards the user asked to vendor and trim `lab-sources` into `sources/`, which was done and is reflected here |

**Minimum Validations:** 2 (to ensure alignment)

---

## Suggested Requirements for /define

Based on this brainstorm session, the following should be captured in the DEFINE phase:

### Problem Statement (Draft)
There is no Fabric Real-Time Intelligence implementation of the streaming reference patterns (enrichment, windowed KPIs, dedup, late data, alerting, replay and history) over the Fruit Juice stream that can be rebuilt from Git and is checked for exact parity against a seeded oracle.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| The author (learning) | Needs hands-on practice with Eventstream, KQL update policies, materialized views and Activator |
| Portfolio readers / reviewers | Need proof that the patterns work on Fabric: tests and a live dashboard, not a diagram |
| The streaming lab series | Needs a Fabric counterpart with the same KPIs and oracle as `lab-streaming-oss` |

### Success Criteria (Draft)
- [ ] `generator stream --sink kafka` authenticates to the Eventstream custom endpoint with SASL_SSL using `.env` settings
- [ ] A seeded bounded run (`--count 2000`, fixed `--as-of`) gives `kpi_*` views **exactly equal** to the pandas recompute
- [ ] With `--dup-ratio`/`--late-ratio`, the KPIs still match the deduplicated recompute, and the late and duplicate counts match what was injected
- [ ] Replay (clear the tables, same seed, `--start-seq 0`) reproduces identical KPIs
- [ ] An Activator rule fires an email when simulated daily revenue falls below the prorated `tab_fato004` target (driven with `--speed`)
- [ ] The KPI tables are queryable as Delta from a Lakehouse shortcut through OneLake availability
- [ ] The real-time dashboard shows the KPIs, ingestion lag, and late and duplicate counters
- [ ] A PR runs ruff and the unit tests; a merge to `main` publishes dev → prod with `fabric-cicd` (service principal) and applies the KQL scripts and dimensions to prod
- [ ] The whole workspace can be recreated from Git and scripts on a new trial capacity

### Constraints Identified
- Fabric free trial: 60-day expiry, so no click-ops state can exist outside Git and scripts. Avoid always-on compute beyond the Eventhouse
- `sources/` changes are needed: SASL_SSL in `KafkaSink`, and deterministic `--dup-ratio`/`--late-ratio`
- Codes (`cod_*`) stay strings end to end
- To be verified in /design (low KB coverage): Eventstream custom endpoint auth and item definitions in Git; Activator item support in Git and `fabric-cicd`; restrictions on materialized views over a dedup view; whether the service principal can call the Fabric APIs against a trial-capacity workspace
- Python 3.11+ and `uv`; Windows development machine

### Out of Scope (Confirmed)
- Event Hubs, Spark Structured Streaming, Eventstream in-flight transformations
- A test workspace and deployment pipelines
- DLQ and schema evolution
- Activator actions other than email

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 8 discovery + 1 samples + 1 approach selection |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Validations Completed | 2 |
| Duration | ~1 session (includes vendoring and trimming `sources/`) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_STREAMING_FABRIC_PIPELINE.md`
