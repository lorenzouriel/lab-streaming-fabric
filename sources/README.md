# sources

The Fruit Juice event producer for this lab, trimmed from [`lab-sources`](../../lab-sources): the same
seeded model (calibration committed), reduced to what the Fabric pipeline needs.

```bash
uv sync                      # add --extra stream for the Kafka sink
uv run generator generate    # dim_* + tab_fato004 (revenue target) -> data/parquet/fruit_juice/
uv run generator stream --sink stdout --rate 5 --as-of 2026-10-02
uv run generator stream --sink kafka --rate 10 --count 1000   # KAFKA_BOOTSTRAP / KAFKA_TOPIC from .env
uv run pytest
```

## Commands

| Command | Output |
|---|---|
| `generate [--start] [--end] [--seed]` | Parquet: the six dimensions (`src/dimensions/*.csv`, fixed universe) and `tab_fato004` hive-partitioned by year |
| `stream [--sink stdout\|file\|kafka] [--rate] [--count] [--duration] [--as-of] [--speed] [--start-seq] [--seed]` | One JSON event per order |

Event fields: `event_id, seq, event_time, cod_dia, cod_cliente, cod_produto, cod_fabrica, cod_organizacional,
faturamento, imposto, custo_variavel, unidades, quantidade_vendida`. Codes are strings (keep leading zeros).

## Determinism

Event *N* depends only on (seed, `--as-of` date, N): not on rate, wall clock or where a run stopped, so
`--start-seq` resumes exactly and a test can regenerate the same events locally as an oracle. Only
`event_time` reflects when the event was produced. `generate` is byte-identical per seed.

## Changes from lab-sources

- Removed: `fit`, `export-original`, `load`, `validate`; CSV/JSON/MongoDB/SQL writers; PostgreSQL, SQL Server
  and MongoDB sinks; docker compose; the foundation fact tables (only the dimension CSVs are kept).
- `generate` writes only what the Eventhouse needs (dimensions + revenue target).
- Fixed: stream seasonality used the real current month instead of `--as-of`, so the same seed gave
  different events in different months.
