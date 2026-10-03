# External Data Access

> **Purpose**: The OPEN* function family (OPENJSON, OPENROWSET, OPENQUERY, OPENDATASOURCE, OPENXML) and Data API Builder — how SQL Server reaches outside itself
> **Confidence**: 0.90
> **MCP Validated**: 2026-09-16

## Overview

SQL Server integrates with the outside world through a family of `OPEN*` table functions, each solving a different integration problem — remote servers, JSON payloads, bulk file loads, XML. Choosing the right one depends on where the data lives and whether it's a one-off query or a production pipeline. Data API Builder (DAB) goes the other direction: it turns your schema into a REST/GraphQL API without hand-written backend code.

## The Concept

```sql
-- OPENJSON: the modern standard for JSON integration
SELECT order_id, customer_id, status
FROM OPENJSON(@order_json)
WITH (order_id INT '$.order_id', customer_id INT '$.customer_id', status VARCHAR(50) '$.status');

-- OPENQUERY: pushdown to a linked server — filters/joins run remotely
SELECT * FROM OPENQUERY(LinkedServerName,
    'SELECT customer_id, email FROM SalesDB.dbo.Customers WHERE email LIKE ''%@gmail.com''');

-- OPENROWSET BULK: fast file import, bypasses row-by-row insert overhead
SELECT * FROM OPENROWSET(BULK 'C:\Data\products_import.csv',
    FORMATFILE = 'C:\Data\products_import.fmt') AS DataFile;

-- OPENDATASOURCE: ad-hoc, no pushdown — pulls everything then filters locally
SELECT * FROM OPENDATASOURCE('SQLNCLI', 'Server=RemoteServer;Trusted_Connection=yes;')
    .SalesDB.dbo.Orders;
```

`OPENXML` is legacy — prefer native XML methods (`nodes()`, `value()`, `query()`) for new code; always call `sp_xml_removedocument` if you do use it, or you leak the in-memory DOM handle.

**Data API Builder**: point a JSON config at your database (`data-source`, `runtime`, `entities`) and DAB generates REST + GraphQL endpoints — tables get full CRUD, views/procedures get read/execute. Field mappings decouple API names from column names; `set-session-context: true` flows caller identity into `SESSION_CONTEXT()` for RLS; `allow-introspection: false` and a `depth-limit` are the GraphQL exposure controls in production.

## Quick Reference

| Function | Data lives in | Production-safe? | Notes |
|----------|---------------|-------------------|-------|
| `OPENJSON` | JSON string/column | Yes | Best for API ingestion |
| `OPENQUERY` | Linked server | Yes | Pushdown — filter runs remotely |
| `OPENROWSET BULK` | Files (CSV/JSON) | For ETL | Fastest bulk file load |
| `OPENDATASOURCE` / bare `OPENROWSET` | Remote server (ad-hoc) | Rarely | No pushdown — pulls all data first |
| `OPENXML` | XML string | Legacy only | Use native XML methods instead |

## Common Mistakes

### Wrong

Using `OPENDATASOURCE` or bare `OPENROWSET` for a frequent production query against a large remote table — the `WHERE` clause runs locally on everything fetched, not on the remote server.

### Correct

Configure a linked server and use `OPENQUERY` with the filter *inside* the quoted remote query string, so filtering happens on the remote side. `Ad Hoc Distributed Queries` must be deliberately enabled (and audited) for `OPENDATASOURCE`/`OPENROWSET` to work at all.

## Related

- [native-search-and-ai-features](native-search-and-ai-features.md) — `OPENJSON`/JSON functions for AI/RAG payloads
- [advanced-tsql-querying](../patterns/advanced-tsql-querying.md)
