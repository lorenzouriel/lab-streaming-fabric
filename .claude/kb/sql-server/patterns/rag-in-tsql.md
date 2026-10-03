# RAG in T-SQL

> **Purpose**: Building a Retrieval-Augmented Generation loop entirely inside T-SQL — vector retrieval, JSON-based prompt augmentation, and calling an LLM endpoint from a stored procedure
> **Confidence**: 0.85 — depends on preview vector-index features; verify current preview/GA status before production use
> **MCP Validated**: 2026-09-16

## When to Use

- Grounding an LLM answer in current row data without standing up a separate middleware service
- Data changes often (RAG beats fine-tuning — it reads current rows every call) or traceability/privacy rules out fine-tuning
- Adding a "chat with your data" endpoint that a client application calls like any other stored procedure

## Implementation

```sql
CREATE PROCEDURE dbo.AskProductQuestion @Question NVARCHAR(1000), @Answer NVARCHAR(MAX) OUTPUT AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @questionVector VECTOR(1536), @context NVARCHAR(MAX), @payload NVARCHAR(MAX),
            @response NVARCHAR(MAX), @returnValue INT;

    -- 1. RETRIEVE: embed the question, find nearest rows (VECTOR_SEARCH at scale, VECTOR_DISTANCE for small tables)
    SELECT @questionVector = AI_GENERATE_EMBEDDINGS(@Question USE MODEL my_embedding_model);
    SET @context = (
        SELECT TOP 3 p.Name AS ProductName, p.Color, pm.Name AS Model
        FROM Production.Product AS p JOIN Production.ProductModel AS pm ON p.ProductModelID = pm.ProductModelID
        ORDER BY VECTOR_DISTANCE('cosine', p.DescriptionVector, @questionVector)
        FOR JSON PATH
    );

    -- 2. AUGMENT: system message is the contract, user message is evidence + question. Keep temperature low.
    SET @payload = JSON_OBJECT(
        'messages': JSON_ARRAY(
            JSON_OBJECT('role': 'system', 'content': 'Answer using only the provided product data. Be concise.'),
            JSON_OBJECT('role': 'user', 'content': 'Products: ' + ISNULL(@context, '[]') + ' Question: ' + @Question)
        ), 'max_tokens': 500, 'temperature': 0.5
    );

    -- 3. GENERATE: call the model — enable sp_invoke_external_rest_endpoint via sp_configure on box SQL Server 2025
    EXEC @returnValue = sp_invoke_external_rest_endpoint
        @url = N'https://<endpoint>.openai.azure.com/openai/deployments/<model>/chat/completions?api-version=2024-10-21',
        @method = 'POST', @payload = @payload, @credential = [https://<endpoint>.openai.azure.com],
        @retry_count = 3, @response = @response OUTPUT;

    IF @returnValue = 0
        SET @Answer = JSON_VALUE(@response, '$.result.choices[0].message.content');
    ELSE IF @returnValue = 429
        SET @Answer = 'Service is busy. Try again later.';
    ELSE
        SET @Answer = 'Unable to process your question. Please try again.';
END;
```

## Configuration

| Aspect | Guidance |
|---|---|
| Prompt shaping | `FOR JSON AUTO` for quick/inferred shape; `FOR JSON PATH` for explicit nesting; `WITHOUT_ARRAY_WRAPPER` for single-row context |
| Context hygiene | Include only columns that answer the question — every extra column is tokens and noise |
| Temperature | 0.3–0.5 for RAG (consistency, not creativity); pair with `max_tokens` |
| Authentication | Database-scoped credential with managed identity — never a stored API key |
| HTTP failure codes | `0` = success; `429` = throttled (retry); `401`/`403` = credential problem |
| Embedding storage at scale | `VECTOR(1536)` column + DiskANN index; `ALLOW_STALE_VECTOR_INDEX = ON` (Azure SQL/Fabric) keeps the table writable |

## Example Usage

```sql
-- Populate embeddings in throttled batches — an unthrottled UPDATE across a real table hits 429 fast
UPDATE TOP (30) r SET r.ReviewVector = AI_GENERATE_EMBEDDINGS(
    p.Name + ' - ' + r.ReviewTitle + ': ' + r.ReviewText USE MODEL my_embedding_model)
FROM dbo.ProductReview AS r JOIN SalesLT.Product AS p ON r.ProductID = p.ProductID
WHERE r.ReviewVector IS NULL;
-- WAITFOR DELAY between batches + a retry loop on rate-limit errors
```

RAG vs. fine-tuning decision rule: data changes often → RAG; need traceability (know which rows produced an answer) → RAG; privacy-sensitive (corpus never leaves the database, only a per-request slice) → RAG.

## See Also

- [native-search-and-ai-features](../concepts/native-search-and-ai-features.md)
- [advanced-tsql-querying](advanced-tsql-querying.md)
- Generic RAG pipeline architecture (non-T-SQL-native) lives in `../ai-data-engineering/`
