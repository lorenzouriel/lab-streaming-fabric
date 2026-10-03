# SQL Server Knowledge Base

> **Purpose**: SQL Server / T-SQL engine internals and DBA operations — architecture, indexing, query internals, HA/DR, security, maintenance
> **MCP Validated**: 2026-09-16
>
> Cross-dialect SQL (window functions, CTEs, dedup, pivot/unpivot, gap-and-island) lives in [../sql-patterns/](../sql-patterns/index.md), not here — this domain owns what's genuinely SQL-Server-specific.

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/engine-architecture.md](concepts/engine-architecture.md) | Protocol/Relational/Storage Engine layers, query flow, system databases |
| [concepts/query-processing.md](concepts/query-processing.md) | Parsing, optimization, plan caching, parameterization, parameter sniffing, MAXDOP |
| [concepts/indexing-internals.md](concepts/indexing-internals.md) | Clustered/nonclustered/columnstore B-tree and rowgroup internals, fragmentation |
| [concepts/transactions-and-isolation.md](concepts/transactions-and-isolation.md) | COMMIT/ROLLBACK, write-ahead logging, isolation levels vs. blocking |
| [concepts/query-store.md](concepts/query-store.md) | What Query Store captures and why it anchors regression hunting |
| [concepts/specialized-table-types.md](concepts/specialized-table-types.md) | Temporal, ledger, in-memory OLTP, external, graph tables — when each is worth it |
| [concepts/security-model.md](concepts/security-model.md) | Logins vs. users, roles, schemas as a permission boundary, contained databases |
| [concepts/recovery-and-ha-dr.md](concepts/recovery-and-ha-dr.md) | Recovery models, backup types, HA vs. DR technology landscape, RTO/RPO |
| [concepts/external-data-access.md](concepts/external-data-access.md) | OPENJSON/OPENROWSET/OPENQUERY/OPENDATASOURCE/OPENXML, Data API Builder |
| [concepts/native-search-and-ai-features.md](concepts/native-search-and-ai-features.md) | Full-text/vector/hybrid search, AI-assisted dev tooling (Copilot, MCP) |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/query-optimization-techniques.md](patterns/query-optimization-techniques.md) | Sargability, existence checks, predicate ordering, NOLOCK/RCSI tradeoffs |
| [patterns/join-algorithms.md](patterns/join-algorithms.md) | Recognizing and influencing Nested Loops / Merge / Hash join choice |
| [patterns/error-handling.md](patterns/error-handling.md) | TRY/CATCH + THROW as standard, RAISERROR's remaining fit, trigger semantics |
| [patterns/routine-selection.md](patterns/routine-selection.md) | Views vs. procedures vs. functions vs. triggers decision framework |
| [patterns/advanced-tsql-querying.md](patterns/advanced-tsql-querying.md) | JSON, regex, fuzzy matching, graph MATCH traversal |
| [patterns/index-maintenance-playbook.md](patterns/index-maintenance-playbook.md) | Rebuild vs. reorganize thresholds, statistics, DBCC toolkit, Ola Hallengren |
| [patterns/backup-restore-strategy.md](patterns/backup-restore-strategy.md) | Backup policy by RPO/RTO tier, restore sequence, dbatools automation |
| [patterns/always-on-setup.md](patterns/always-on-setup.md) | Availability Group replicas, listener, quorum/witness, log shipping |
| [patterns/monitoring-and-alerting.md](patterns/monitoring-and-alerting.md) | Extended Events slow-query capture, Database Mail job alerts, wait-based triage |
| [patterns/capacity-and-storage-design.md](patterns/capacity-and-storage-design.md) | Scale-up vs. scale-out, capacity planning cycle, data compression / sparse columns |
| [patterns/database-ci-cd.md](patterns/database-ci-cd.md) | Database-as-code, dacpac/SqlPackage, schema-drift detection, gated pipelines |
| [patterns/azure-sql-tuning.md](patterns/azure-sql-tuning.md) | The Azure-SQL-specific diagnostic funnel — provisioning, database-scoped defaults |
| [patterns/rag-in-tsql.md](patterns/rag-in-tsql.md) | Retrieval-Augmented Generation loop entirely inside T-SQL |

### Reference (no line limit)

| File | Purpose |
|------|---------|
| [reference/dba-field-guide.md](reference/dba-field-guide.md) | Monitoring, performance troubleshooting, logs/events, full DMV reference |
| [reference/troubleshooting-cheat-sheet.md](reference/troubleshooting-cheat-sheet.md) | Terse incident-response card — identify, measure, resolve |
| [reference/ha-dr-field-guide.md](reference/ha-dr-field-guide.md) | HA/DR decision framework, HADR DMVs, failover/quorum troubleshooting, runbooks |
| [reference/security-compliance-layers.md](reference/security-compliance-layers.md) | Encryption (TDE/Always Encrypted/cell), masking, RLS, auditing, AI/API endpoint security |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) — Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Wait-based troubleshooting** | Don't guess the bottleneck — read `sys.dm_os_wait_stats` / `dm_os_waiting_tasks`; the engine records why every thread suspended |
| **Query Store** | Per-database flight recorder for plans/runtime stats — the backbone of regression detection and parameter-sniffing diagnosis |
| **Sargability** | Keep indexed columns bare in predicates — a function/expression on the column disables seek and forces a scan |
| **RTO vs. RPO** | RTO drives HA technology choice (AG/FCI); RPO drives backup/log-shipping frequency. HA is not a backup |
| **Deployment target matters** | On-prem, Azure SQL Database, Managed Instance, and SQL Server on Azure VM have different HA/DR mechanisms and tuning levers — always state which one applies |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| sql-server-specialist | concepts/query-processing.md, concepts/indexing-internals.md, concepts/query-store.md, patterns/query-optimization-techniques.md, patterns/join-algorithms.md, patterns/routine-selection.md | Query tuning, execution plan analysis, index design, T-SQL routine selection |
| sql-server-dba | concepts/recovery-and-ha-dr.md, concepts/security-model.md, patterns/backup-restore-strategy.md, patterns/always-on-setup.md, reference/*.md | Backup/HA-DR design, security/compliance, maintenance, incident troubleshooting |
| sql-optimizer | (escalates in from here for cross-dialect translation; escalates out here for SQL-Server-specific internals) | Boundary cases between cross-dialect and engine-specific tuning |
