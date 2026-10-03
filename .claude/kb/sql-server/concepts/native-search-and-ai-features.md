# Native Search and AI Features

> **Purpose**: What SQL Server natively offers for full-text, vector, and hybrid search, plus AI-assisted development tooling (Copilot, MCP, instruction files) — the "what it is" companion to the RAG implementation pattern
> **Confidence**: 0.85 — vector features are recent/preview-adjacent; verify current status before relying on specifics
> **MCP Validated**: 2026-09-16 (VECTOR data type GA and DiskANN preview status confirmed against current Microsoft Learn / Azure SQL blog sources, superseding the source notes' "in preview" framing for the base type)

## Overview

SQL Server 2025 and Azure SQL Database offer three complementary, natively-queryable search tools: **full-text search** (linguistic keyword matching), **vector search** (semantic similarity over embeddings), and **hybrid search** (both, merged with Reciprocal Rank Fusion). Do not duplicate cross-dialect window-function/CTE material here — see `../sql-patterns/`. This file covers what's SQL-Server-specific: the native `VECTOR` type, `CONTAINS`/`FREETEXT`, and RRF fusion. Separately, AI-assisted development (GitHub Copilot, MCP servers, instruction files) is how developers write T-SQL against a real schema instead of a generic guess.

## The Concept

```sql
-- Full-text: understands word forms, not just character sequences
SELECT ProductID, Name FROM Production.Product WHERE CONTAINS(Name, 'mountain');
SELECT ProductID, Name FROM Production.Product WHERE FREETEXT(Name, 'riding bikes');  -- auto-expands inflections

-- Native VECTOR type (GA with SQL Server 2025 / Azure SQL, Nov 2025)
CREATE TABLE dbo.Products (
    ProductID INT PRIMARY KEY, DescriptionVector VECTOR(1536) NOT NULL  -- max 1998 dims
);
SELECT TOP 10 ProductID, VECTOR_DISTANCE('cosine', @query, DescriptionVector) AS Distance
FROM dbo.Products ORDER BY Distance;   -- exact (ENN) — fine under ~50K rows

-- DiskANN approximate index (still PREVIEW as of 2026 — verify current status before depending on it)
CREATE VECTOR INDEX idx_Products_Vec ON dbo.Products(DescriptionVector)
    WITH (METRIC = 'cosine', TYPE = 'DiskANN');
```

Vector index limitations to design around: table needs a single-column integer clustered PK; the table goes read-only while the index exists unless `ALLOW_STALE_VECTOR_INDEX = ON` (Azure SQL/Fabric; not available on box SQL Server 2025); indexes can't be partitioned. For churny tables, run exact search until data stabilizes, then index.

**Hybrid search** fuses full-text (BM25 rank) and vector (cosine distance) result lists — scores are on incomparable scales, so fuse by **rank position** with Reciprocal Rank Fusion: `RRF_score = 1/(k + rank_fulltext) + 1/(k + rank_vector)`, `k = 60` by convention. See [rag-in-tsql](../patterns/rag-in-tsql.md) for the full query.

**AI-assisted development**: GitHub Copilot (SSMS 22+, VS Code, Visual Studio) does completion, NL-to-SQL, and optimization suggestions against a *connected* database — without an MCP server it only sees your editor buffer, not your real schema. The **SQL MCP Server** (Microsoft OSS, built on Data API Builder), **Azure MCP Server**, and **Microsoft Fabric MCP Server** are the three named context providers. Least-privilege the MCP service account, never commit a live secret in `mcp.json`, and treat every AI-generated statement as a first draft needing a security read (unparameterized dynamic SQL, over-broad `GRANT`s). `copilot-instructions.md` (repo-wide) and `.prompt.md` templates encode T-SQL house style once instead of re-explaining it per prompt.

## Quick Reference

| Query shape | Best fit |
|---|---|
| Exact token (part number, error string) | Full-text (`CONTAINS`) |
| Described need, no obvious keyword | Vector (`VECTOR_DISTANCE` / `VECTOR_SEARCH`) |
| Mixed / can't predict | Hybrid (RRF) |

| Distance metric | Use when |
|---|---|
| Cosine | Default for most modern embedding models |
| Euclidean | Magnitude matters |
| Dot product | Model trained on it (SQL Server returns it negated for consistent ordering) |

## Common Mistakes

### Wrong

`VECTOR_SEARCH(...) WHERE CategoryID = 5` — the `WHERE` filter applies *after* finding the top-N nearest neighbors, so if none of the top 10 match the filter you get zero rows, not a smaller-but-correct result.

### Correct

Over-fetch before filtering: `TOP_N = 50` inside `VECTOR_SEARCH`, then apply the `WHERE` clause outside it and take the final `TOP 10`.

## Related

- [rag-in-tsql](../patterns/rag-in-tsql.md)
- [advanced-tsql-querying](../patterns/advanced-tsql-querying.md)
- Cross-dialect vector DB / RAG pipeline patterns (non-SQL-Server-native) live in `../ai-data-engineering/`
