# Ch.6 — Data Flow patterns

Tasks must be coordinated within a pipeline and across teams without creating a fragile point-to-point dependency web.

## Local Sequencer
Split a monolith into sequential tasks. Boundary criteria: (1) separation of concerns — if naming the task is hard, it does too much; (2) retry cost — split expensive steps so a downstream failure doesn't rerun them; (3) use native operators where the orchestrator already does the thing (SQL, HTTP). Each task is a restart boundary: `sensor >> load >> expose`.

## Isolated Sequencer (cross-team)
Two coupling styles:
- **Data-based (loose)**: producer writes a readiness marker; consumer polls it. Teams evolve independently.
- **Task-based (tight)**: producer triggers consumer's DAG (`ExternalTaskMarker` / `ExternalTaskSensor`). Producer backfills cascade automatically.
Prefer data-based across team boundaries. Task-based only when the consumer just needs a signal and the producer owns the dataset outright.

## Aligned Fan-In
All parents succeed before the child runs — e.g. 24 hourly loads → 1 daily aggregate. Generate hourly tasks in a loop, all wired to the aggregate.
- Pros: parallelism, fast failure signal (hour 3 fails in minutes, not at hour 24), granular backfill.
- Cons: infrastructure spikes (24 concurrent jobs), scheduling skew (child waits for the slowest parent), scheduler overhead at fine granularity.

## Unaligned Fan-In
Relax the all-success rule via `trigger_rule` (`one_success`, `all_done`) to release partial datasets instead of blocking on one bad hour. Consumers may get incomplete data — flag partial partitions explicitly and document it.

## Exclusive Choice (Fan-Out)
Conditional routing: `BranchPythonOperator` decides "create new weekly partition" vs "append". Downstream join task needs `trigger_rule='none_failed_min_one_success'` so skipped branches don't block it. Don't over-branch.

## Concurrency Control
`max_active_runs` caps simultaneous DAG runs (backfills otherwise flood the cluster). `depends_on_past=True` forces sequential execution at task level even when DAG-level concurrency allows more — required for stateful/forward-dependent tasks.

## Decision guide
- Your Silver dataset feeds the BI team → Isolated Sequencer, data-based: you write `_SUCCESS`/control row; they `FileSensor`. Same Airflow and cascading backfills matter → `ExternalTaskMarker`.
- Hourly → daily aggregate → Aligned Fan-In; if partial days are acceptable → Unaligned with `all_done` + partial flag.
- Backfill-prone pipeline → always set `max_active_runs`.

## Stack mapping
- **Airflow**: `ExternalTaskSensor(mode='reschedule')`, `ExternalTaskMarker`, `trigger_rule`, `max_active_runs`, `depends_on_past`, TaskGroups for the hourly loop, Datasets (data-aware scheduling) as a native data-based coupling primitive.
- **Azure DevOps / ADF / Fabric Pipelines**: Execute Pipeline activity = task-based coupling; storage event trigger or control-table lookup = data-based. Fabric pipeline concurrency setting = Concurrency Control.
- **SQL Server Agent**: job steps are a Local Sequencer with `On failure: quit` as restart boundary; cross-job dependencies via a control table polled by a sensor step (data-based), or `sp_start_job` (task-based — avoid across teams).
- **dbt**: DAG is implicit from `ref()`; cross-project = data-based via sources with freshness checks; `--select state:modified+` for granular backfill.
