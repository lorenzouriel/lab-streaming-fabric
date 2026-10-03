# Ch.8 — Data Storage patterns

Physical layout is one of the highest-leverage optimizations. A bad layout makes a simple aggregation 100x slower. Choose layout for the *query pattern* before writing.

## Partitioner
Physically isolate directories by a low-to-medium cardinality column (date, hour, country). Filters on the partition column skip everything else (partition pruning). High-cardinality partitioning (user id) recreates the small-files problem — that's what Compactor (ch.2) and Z-order are for.

## Bucket
Within a partition, hash a high-cardinality key (user id) into N fixed buckets. Same key → same file. If both join sides are bucketed on the same key with the same N, Spark skips the shuffle; also enables Local Aggregator (ch.5). Spark: `bucketBy(32,'user_id').sortBy('user_id').saveAsTable(...)` — needs a metastore table, not a bare path.

## Sorter
Sort within files/partitions: enables data skipping (row-group min/max statistics) and better compression. Delta: `OPTIMIZE t ZORDER BY (user_id, event_date)` = compaction + multi-dimensional sort in one command. Use Z-order for columns you filter on often but that are too high-cardinality to partition.

## Table File Format Selector
- **Delta Lake**: ACID, time travel, schema enforcement, CDF, Z-order, VACUUM. Native for Databricks and Fabric OneLake (Direct Lake reads Delta directly).
- **Iceberg**: same ACID, hidden partitioning + partition evolution without rewrites, strongest multi-engine story (Spark, Flink, Trino, Snowflake).
- **Hudi**: merge-on-read for write-heavy streaming ingestion.
- Raw formats (CSV/JSON/Avro) only at the ingestion boundary.

## Columnar Format
Parquet reads only the columns touched — 3 of 50 columns = 3 columns of I/O. With Snappy/ZSTD it's 5–10x smaller than JSON/CSV. Analytical workloads: Parquet always. Avro/JSON only where row-level streaming writes and schema evolution matter at ingestion.

## Rules
- Partition by low-cardinality; bucket by high-cardinality join keys; Z-order the filter columns in between.
- `OPTIMIZE` without `VACUUM` reclaims nothing.
- Delta for Databricks/Fabric; Iceberg for multi-engine; Hudi for write throughput.

## Decision guide
- Visits queried by date → partition by `event_date`.
- visits ⋈ users on `user_id` → bucket both on `user_id`, same bucket count.
- Filters on `user_id` and `page` → Z-order `(user_id, page)`.
- Fabric Lakehouse → Delta, V-Order enabled for Direct Lake.

## Stack mapping
- **SQL Server**: table partitioning on a date column with aligned indexes = Partitioner (pruning via partition elimination; also enables `SWITCH` for idempotent loads, ch.4). Clustered columnstore index = the columnar format; rowgroup elimination works on the *load order*, so sort on the filter column before bulk insert = Sorter. Hash-distributed tables in Synapse/Fabric Warehouse = Bucket (co-locate join keys). `DATA_COMPRESSION = COLUMNSTORE_ARCHIVE` for cold partitions.
- **Fabric**: Delta + V-Order (`spark.sql.parquet.vorder.enabled`) for Direct Lake read performance; `OPTIMIZE`/`VACUUM` via Lakehouse maintenance; Warehouse uses hash/round-robin distribution.
- **Databricks**: Liquid Clustering (`CLUSTER BY`) is the successor to Z-order/bucketing for evolving layouts — prefer it on new tables; keep the pattern names but map to it.
- **PostgreSQL**: declarative partitioning; BRIN index on sorted append-only tables ≈ min/max data skipping.
