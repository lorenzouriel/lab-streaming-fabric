# SQL Server Data Security and Compliance, Layer by Layer

> Defense in depth is only useful if you can say, per layer, exactly which adversary it stops and which one it lets straight through. TDE stops the person who steals a backup file; it does nothing against a valid login. Masking hides values on a screen and folds instantly to anyone who can write a `WHERE` clause. Treating either as "the security layer" is how systems end up compliant on paper and exposed in practice. See [../concepts/security-model](../concepts/security-model.md) for logins/users/roles/schemas basics this reference builds on.

## Layer 1: Encryption — Three Flavors, Three Adversaries

**Transparent Data Encryption (TDE)** — the stolen-backup/media attacker. Encrypts data files, log, and backups at rest; transparent to applications. Does nothing against someone with a valid login.

```sql
CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'S0me-Strong-DMK-P@ss!';
CREATE CERTIFICATE TDE_Cert WITH SUBJECT = 'TDE Certificate for production';
-- BACK UP THE CERTIFICATE IMMEDIATELY -- without it, a TDE backup cannot be restored elsewhere.
-- Losing this cert is the #1 TDE disaster.
BACKUP CERTIFICATE TDE_Cert TO FILE = 'C:\Secure\TDE_Cert.cer'
    WITH PRIVATE KEY (FILE = 'C:\Secure\TDE_Cert.pvk', ENCRYPTION BY PASSWORD = 'Cert-Backup-P@ss!');

CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256 ENCRYPTION BY SERVER CERTIFICATE TDE_Cert;
ALTER DATABASE SalesDB SET ENCRYPTION ON;

-- Confirm state (3 = fully encrypted)
SELECT DB_NAME(database_id), encryption_state_desc, percent_complete FROM sys.dm_database_encryption_keys;
```

On Azure SQL/Managed Instance, TDE is on by default with a service-managed key (switch to BYOK via Key Vault if needed); on Fabric it's on and fully managed.

**Always Encrypted** — the only control here that defends against a privileged DBA; the engine only ever handles ciphertext, keys live in Key Vault / a driver-managed store.

```sql
CREATE COLUMN MASTER KEY CMK_Prod WITH (KEY_STORE_PROVIDER_NAME = 'AZURE_KEY_VAULT', KEY_PATH = 'https://kv-prod.vault.azure.net/keys/CMK_Prod/0123abcd');
CREATE COLUMN ENCRYPTION KEY CEK_Prod WITH VALUES (COLUMN_MASTER_KEY = CMK_Prod, ALGORITHM = 'RSA_OAEP', ENCRYPTED_VALUE = 0x...);

CREATE TABLE dbo.Customers (
    CustomerID int PRIMARY KEY,
    -- DETERMINISTIC: same plaintext -> same ciphertext; enables =/JOIN/GROUP BY, requires BIN2 collation.
    -- Cost: equal values are visibly equal (frequency analysis possible).
    NationalID char(11) COLLATE Latin1_General_BIN2
        ENCRYPTED WITH (ENCRYPTION_TYPE = DETERMINISTIC, ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256', COLUMN_ENCRYPTION_KEY = CEK_Prod),
    -- RANDOMIZED: strongest, leaks nothing, supports NO query operations
    CreditLimit money
        ENCRYPTED WITH (ENCRYPTION_TYPE = RANDOMIZED, ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256', COLUMN_ENCRYPTION_KEY = CEK_Prod)
);
```

Inserts/equality filters against encrypted columns must go through parameterized commands with `Column Encryption Setting=Enabled` — literals from plain T-SQL don't work. When the permitted operation list is too short (no ranges, no `LIKE`), **secure enclaves** (`ENCLAVE_COMPUTATIONS` on the CMK) unlock range comparisons and in-place re-encryption.

**Column-level (cell) encryption** — when you want to `GRANT`/`DENY` decryption rights yourself rather than use Always Encrypted:

```sql
CREATE SYMMETRIC KEY SymKey_PII WITH ALGORITHM = AES_256 ENCRYPTION BY CERTIFICATE Cert_PII;
-- ENCRYPTBYKEY's 3rd arg is an authenticator binding ciphertext to a row (prevents copy/paste across rows)
INSERT INTO dbo.Customers (CustomerID, CardNumber_enc)
VALUES (1, ENCRYPTBYKEY(KEY_GUID('SymKey_PII'), CONVERT(varbinary, '4111-1111-1111-1111'), 1, CONVERT(varbinary, 1)));

GRANT VIEW DEFINITION ON SYMMETRIC KEY::SymKey_PII TO PaymentsRole;
```

Cost: application changes everywhere, and `ENCRYPTBYKEY` output is non-deterministic (random IV) so you can't seek on it — store a keyed hash alongside for equality search if you need to look values up. Compose the layers: TDE as the baseline for everything at rest, Always Encrypted/cell encryption reserved for the few columns that must stay opaque even to the engine.

## Layer 2: Dynamic Data Masking — Not a Security Boundary

```sql
CREATE TABLE dbo.Customers (
    Email  varchar(100)  MASKED WITH (FUNCTION = 'email()'),                         -- jXXX@XXXX.com
    Phone  varchar(20)   MASKED WITH (FUNCTION = 'partial(3, "-XXX-XX", 2)'),         -- 206-XXX-XX89
    Income decimal(18,2) MASKED WITH (FUNCTION = 'random(10000, 100000)'),
    SSN    char(11)      MASKED WITH (FUNCTION = 'default()')                         -- XXXX
);

GRANT UNMASK ON dbo.Customers(Phone) TO TelemarketingTeam;   -- column-scoped since 2022
```

Masking operates at the presentation layer — the **true value still drives predicate evaluation**, so a masked user can binary-search a value out of a column one range-query at a time (`WHERE Income > 50000`, `> 75000`, ...). And a user with `SELECT` + `ALTER` can simply drop the mask. Treat DDM as accidental-exposure reduction for dev/test and support staff — never as the actual boundary; put encryption or RLS underneath anything that must truly stay protected.

## Layer 3: Row-Level Security — the Per-Row Boundary

An inline table-valued function (the predicate) bound to a table via a security policy:

```sql
CREATE FUNCTION Security.fn_TenantPredicate(@TenantID int)
RETURNS TABLE WITH SCHEMABINDING AS RETURN
    SELECT 1 AS ok WHERE @TenantID = CAST(SESSION_CONTEXT(N'TenantID') AS int);

CREATE SECURITY POLICY Security.TenantPolicy
ADD FILTER PREDICATE Security.fn_TenantPredicate(TenantID) ON dbo.Orders
WITH (STATE = ON);
```

Use **filter** predicates to silently hide rows and **block** predicates so a user can't insert/update a row they'd then be unable to see. RLS applies transparently through views and stored procedures — there's no path around a bound policy. Watch for row-existence leaking through error-based side channels (a constraint violation on a "hidden" row still reveals it exists). Hierarchical access (managers see reports' data) is a recursive-CTE predicate — same cost warning as any org-chart walk, runs per query.

## Layer 4: Permissions, Roles, Passwordless Identity

Grant at schema level so future objects are automatically covered; build roles around job function:

```sql
GRANT SELECT ON SCHEMA::Sales TO SalesAnalyst;      -- includes tables added later
CREATE ROLE DataReaders;
ALTER ROLE DataReaders ADD MEMBER JohnSmith;
```

Passwordless is the modern default — no secret in a connection string to leak:

```sql
CREATE USER [app-service-identity] FROM EXTERNAL PROVIDER;   -- managed identity
CREATE USER [developer@contoso.com] FROM EXTERNAL PROVIDER;  -- Entra user/group
```

Verify least privilege, don't assume it — `sys.fn_my_permissions('Sales.Orders', 'OBJECT')` answers "what can this principal actually do here" directly, instead of reconstructing it from stacked role memberships.

## Layer 5: Auditing — Accountability That Survives a Compromise

`CREATE SERVER AUDIT` / `CREATE DATABASE AUDIT SPECIFICATION` plus `sys.fn_get_audit_file` cover the mechanics (see [../patterns/monitoring-and-alerting](../patterns/monitoring-and-alerting.md) for the adjacent alerting setup). In Azure SQL, route audit data to Blob storage, Log Analytics (query in KQL), or Event Hubs.

Two rules matter more than the destination: **pick a focused action-group set** — `BATCH_COMPLETED_GROUP` is a firehose that hurts performance and buries the signal; and **store logs separate from the database**, ideally immutable, so a database compromise can't rewrite the record of what happened. Alert on failed logins, off-hours permission changes, and access-volume anomalies — an unreviewed audit log is evidence after the fact, not a control.

## Layer 6: Securing AI Service Endpoints

Calling Azure OpenAI/ML from inside the database introduces exfiltration via crafted prompts, runaway cost, and model probing all at once. Authenticate with managed identity, never a stored key:

```sql
CREATE DATABASE SCOPED CREDENTIAL AzureOpenAICredential
WITH IDENTITY = 'Managed Identity', SECRET = '{"resourceId": "https://cognitiveservices.azure.com/"}';
```

Wrap calls in a procedure, log every invocation (caller, duration, status) for cost/anomaly detection, and gate `EXECUTE` to a dedicated role rather than leaving it open. Catch abuse with a per-caller call-count query over the last hour.

## Layer 7: Securing Data API Endpoints — GraphQL, REST, MCP

For **GraphQL**: disable introspection in production, set field-level include/exclude lists (a column like `CostPrice` should never leave even for authenticated reads), cap query depth/complexity against nested-query DoS. For **REST**: role permissions layered with database policy filters (e.g., anonymous sees only `IsPublic = true` rows).

**MCP deserves the tightest leash** — an AI agent may attempt operations a human never would, and prompt injection is squarely in scope:

```json
{
  "mcpServers": { "sqlDatabase": {
    "authentication": { "type": "azure-identity", "scope": "https://database.windows.net/.default" },
    "security": { "allowedOperations": ["read"], "deniedTables": ["dbo.Passwords"], "maxRowsReturned": 1000 }
  }}
}
```

Validate AI-generated SQL against an **allowlist** of permitted tables/operations, not a blocklist — a `LIKE '%INSERT%'` blocklist is trivially defeated by comments, casing, or encoding. Combine a read-only guard with an explicit table allowlist before `sp_executesql`.

## Key Takeaways

- Match each control to the attacker it stops: TDE → stolen media, Always Encrypted → privileged DBA, masking → accidental on-screen exposure, RLS → wrong-row access, permissions → the front door, auditing → after-the-fact accountability
- Masking is not access control — range queries can extract a masked value one bit at a time, and `ALTER` bypasses it entirely
- RLS applies transparently through views/procedures but watch for row-existence leaks via constraint errors
- Grant at the schema level, build roles by job function, verify with `sys.fn_my_permissions` rather than assuming
- Passwordless identity (managed identity, Entra) removes an entire class of leaked-secret incidents
- AI and API endpoints are new attack surface, not exceptions to old rules: managed identity over stored keys, allowlists over blocklists, log every AI call
- Security is the composition of all seven layers, not any single one — cheapest to design in while deciding which column holds the sensitive data, not after an incident
