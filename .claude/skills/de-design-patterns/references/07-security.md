# Ch.7 — Data Security patterns

Security is architecture, not a final step. Transform sensitive data before it moves, control who sees which rows/columns, manage secrets outside code.

## Anonymizer
Replace PII before crossing a boundary.
- **Pseudonymization** (reversible with a key): `HMAC/SHA2(user_id || salt)`. Salt is a secret; rotate it. Allows re-linking downstream.
- **Anonymization** (irreversible): truncate, generalize, drop. `SUBSTRING(email,1,3) + '***'`, `SELECT * EXCEPT (ip, lat, lon)`.
Choose by whether downstream needs re-linkability.

## Tokenizer
Replace values with opaque tokens; the real value lives only in a token vault. Lake compromise leaks nothing without vault access. Stronger than hashing (no offline dictionary attack on low-entropy values like emails).

## Vault (Secret Manager)
No credentials in code, config, or plain Airflow Variables. Retrieve at runtime from AWS Secrets Manager / Azure Key Vault / HashiCorp Vault; rotation shouldn't require a code change.

## Coarse-Grained Accessor
`GRANT SELECT ON SCHEMA/TABLE TO role` when everything in the table has one sensitivity level.

## Fine-Grained Accessor
- Column-level: `GRANT SELECT (visit_id, event_time) ON visits TO analyst` — PII columns invisible even if the name is known.
- Row-level: policy filtering by session user (Delta/Unity `ROW FILTER`, SQL Server `SECURITY POLICY`).
Views can emulate both, but native enforcement is harder to bypass. Start deny-all, grant additively.

## Encryption
- At rest: storage-native (S3 SSE, Azure Storage encryption, TDE) is table stakes; column-level (AES / envelope encryption with a data key wrapped by a vault master key) for the most sensitive attributes.
- In transit: TLS everywhere — Kafka `security.protocol=SSL`, JDBC `encrypt=true`. Non-negotiable.

## Decision guide
- Prod → staging replication → Anonymizer inside a Transformation Replicator (ch.2).
- User ids for analytics → Tokenizer with vault lookup.
- Multi-team lakehouse → Fine-Grained Accessor: column grants + row filters.
- API keys in Airflow connections → Vault via `SecretsBackend`.

## Stack mapping
- **SQL Server**: Row-Level Security = `CREATE FUNCTION dbo.fn_rls(@tenant) RETURNS TABLE WITH SCHEMABINDING` + `CREATE SECURITY POLICY ... ADD FILTER PREDICATE` (and `BLOCK PREDICATE` for writes). Column-level `GRANT SELECT (col1, col2)`. Dynamic Data Masking (`ADD MASKED WITH (FUNCTION = 'email()')`) is presentation-layer only — not a substitute for anonymization before replication. Always Encrypted for column-level encryption with client-side keys in Key Vault; TDE for at rest. `HASHBYTES('SHA2_256', CONCAT(user_id, @salt))` for pseudonymization.
- **Fabric / Databricks**: Unity Catalog row filters and column masks; OneLake security roles; Purview sensitivity labels as the catalog tags for the PII exclusion list.
- **Airflow**: `AIRFLOW__SECRETS__BACKEND` = Azure Key Vault / AWS Secrets Manager backend; never Variables for secrets.
- **Power BI**: RLS roles on the semantic model + `USERPRINCIPALNAME()`; for Direct Lake, the underlying OneLake security applies.
