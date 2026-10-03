# Ch.5 — Data Value patterns

Reliable data isn't useful data. Two ways to add value: **add** information (enrich, decorate) or **reduce** it (aggregate, sessionize). Plus ordered delivery.

## Static Joiner
Enrich events with a slowly changing dimension. Model as SCD Type 2 (`start_date`, `end_date`, current row `end_date = '9999-12-31'`) and join `event_time BETWEEN start_date AND end_date`. For idempotent backfills join at the **execution date**, not `NOW()`. SCD4 = same idea, current and history in separate tables.

## Dynamic Joiner
Both sides streaming → time-bounded buffers. Watermark on each stream plus a range condition (`display_time BETWEEN event_time AND event_time + 2 min`); the GC watermark evicts rows too old to ever match. Tighter buffer = less memory, more missed joins. Flink temporal table joins are a cleaner API than Spark stream-stream joins.

## Wrapper
Separate raw from computed attributes inside the record: `{raw: {...}, computed: {...}}` (Spark `F.struct`, SQL `NAMED_STRUCT`, T-SQL: two JSON columns or a separate `_computed` column group). Users read computed; raw stays for debugging.

## Metadata Decorator
Technical context (job version, batch id, processing time) users shouldn't see → Kafka headers, or a separate technical table. Not the Wrapper: metadata is *about* the data, not part of it.

## Distributed Aggregator
Group-and-reduce across a cluster requires a shuffle (same key → same executor); the shuffle is usually the bottleneck. Skewed keys → salt: append random suffix, aggregate, re-aggregate on the original key. Verify with `explain()` — look for `Exchange hashpartitioning`.

## Local Aggregator
If rows sharing a key are already co-located (Kafka partitioned by user id, table bucketed on the key, Redshift `DISTKEY`), skip the shuffle: Kafka Streams `groupByKey`, Spark `sortWithinPartitions` + `foreachPartition`. Requires a static partition count and consistent key — rescaling partitions breaks the guarantee.

## Incremental Sessionizer (batch)
Three stores: input partition, completed sessions, pending sessions. Each run: current partition + previous pending → start/accumulate/finalize → write completed and new pending. Key by `{{ ds }}`. Forward dependency: backfilling 09:00 cascades to every later hour. Flag pending sessions as incomplete so consumers know.

## Stateful Sessionizer (streaming)
State store replaces the pending table: Spark `applyInPandasWithState`, Flink `EventTimeSessionWindows.withGap(10 min)`. State survives via checkpoints, but rebalancing state on scale-out is expensive. **Expire on event time (watermark), never processing time** — processing time is nondeterministic across restarts.

## Bin Pack Orderer
Sinks with partial-commit semantics (Kinesis `PutRecords`, DynamoDB `BatchWriteItem`, Elasticsearch bulk) break ordering on partial failure. Sort by entity key + event time, pack into bins where each entity appears at most once per bin, deliver bins sequentially. A retry stays inside its bin.

## FIFO Orderer
Simpler, slower: one record at a time with ack. Or rely on the sink: Kafka idempotent producer (`max.in.flight.requests.per.connection<=5`), Kinesis `SequenceNumberForOrdering`, Pub/Sub `ordering_key`.

## Rules
- SCD2 joins at execution time for idempotency.
- Wrapper = visible business attributes; Decorator = hidden technical context.
- Shuffle is the aggregation bottleneck; salt skew, pre-aggregate counts.
- Sessionization is forward-dependent — backfills cascade.

## Stack mapping
- **T-SQL SCD2 join**: `JOIN dim_user u ON e.user_id = u.user_id AND @run_ts >= u.valid_from AND @run_ts < u.valid_to`; use half-open intervals to avoid overlap. Sessionization in batch: `LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time)` → gap flag → running `SUM` as session id; persist pending sessions in a state table keyed by run date.
- **Fabric semantic models**: keep SCD2 dims with surrogate keys; Direct Lake wants the join key materialized, not a range join — resolve the point-in-time key in Silver.
- **Databricks**: `MERGE` for SCD2 maintenance; salting via `F.rand()` bucket column; `applyInPandasWithState` for streaming sessions; check `explain()` for `Exchange`.
- **Local Aggregator on SQL Server**: partition-aligned indexes let the optimizer aggregate per partition without a global sort — the same colocation idea.
