# Ch.11 — Streaming patterns

Streaming is not fast batch. Data is unbounded and out of order; you can't wait for "all of it". Windows impose boundaries, watermarks are the clock, state is the price of remembering the past.

## Tumbling Window
Fixed, non-overlapping buckets (10:00–10:09:59, then 10:10–…). Per-minute/hour metrics, event counts. Deterministic, no state carry-over. Spark `groupBy(window('event_time','10 minutes'))`; Flink `TumblingEventTimeWindows.of(10 min)`.

## Sliding Window
Overlapping: 10-min window every 5 min → each event lands in `size/slide` windows. Moving averages, rolling counts, trend detection. Cost scales with that ratio.

## Session Window
Closes after a gap of inactivity (e.g. 20 min); length is data-driven. Streaming form of the Stateful Sessionizer (ch.5). Needs state management.

## Late data in windows
Every window must decide: (1) ignore — simple, lossy; (2) `allowedLateness` — keep the window open past the watermark and emit updates; (3) side output — route late events to dead-letter / integration queue (ch.3 integrators). Spark: `withWatermark` + output mode; Flink: `.allowedLateness(15 min).sideOutputLateData(tag)`.

## Stateful Stream Processing
Per-key state that lives for the stream's lifetime: fraud (per-user history), anomaly (per-sensor baseline), CEP (sequence patterns). Flink `ValueState/ListState/MapState`, Spark `applyInPandasWithState` / `transformWithState`. **Set TTL/eviction** or state grows until OOM; persist via checkpoints with a retention policy.

## Rules
- Always configure watermarks — without them the job either buffers forever or drops arbitrarily.
- Late data needs an explicit choice: ignore, allow, or capture.
- Event-time expiration only; processing-time is nondeterministic on restart.
- Every stateful job: checkpoint location + retention configured.

## Decision guide
- Visits per 10 min → Tumbling on `event_time`.
- Rolling 1h avg session duration → Sliding (1h, 5m slide).
- User sessions with 20-min timeout → Session Window + Stateful Sessionizer.
- Mobile events 30 min late → `withWatermark('event_time','30 minutes')` + allowed lateness, update mode.

## Stack mapping
- **Databricks / Fabric Spark Structured Streaming**: `withWatermark` before `groupBy(window(...))`; `outputMode('update')` for late-data corrections into Delta (sink must be idempotent — `MERGE` in `foreachBatch`, ch.4); `transformWithState` (Spark 4 / DBR 16+) for TTL-aware arbitrary state; checkpoint on ADLS/OneLake, never local.
- **Fabric Eventstream / Real-Time Intelligence + KQL**: tumbling = `summarize ... by bin(event_time, 10m)`; sliding = `series_*` / `make-series` with `range` step; session-like = `summarize ... by user, session_id` after `row_window_session()`; late data handled by the eventhouse ingestion batching policy — set `IngestionBatching` and query with `ingestion_time()` vs event time to detect it.
- **Kafka Streams / Flink**: Flink preferred for session windows and temporal joins; Kafka Streams `groupByKey` for local aggregation when the topic is keyed correctly (ch.5).
- **SQL Server**: not a stream processor; micro-batch via CDC polling + `MERGE` every N seconds is the honest equivalent, with `rowversion`/LSN as the watermark.
