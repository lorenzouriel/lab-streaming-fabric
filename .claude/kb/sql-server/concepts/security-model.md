# Security Model

> **Purpose**: Logins vs. users, database/server roles, schemas as a permission boundary, and contained databases
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

A **login** authenticates to the SQL Server *instance*; a **user** grants access inside a specific *database*. They are separate objects — a login with no matching user has no database access, and a user with no matching login is **orphaned** (common after a cross-server restore). Roles group permissions at the database or server level; schemas group objects and double as a permission boundary; contained databases remove the server-login dependency entirely.

## The Concept

```sql
-- Login (server) then user (database) — the two-step pattern, both auth modes
CREATE LOGIN [YourDomain\User] FROM WINDOWS;             -- or: WITH PASSWORD = '...'
CREATE USER [YourDomain\User] FOR LOGIN [YourDomain\User];

-- Fix an orphaned user after a cross-server restore
ALTER USER YourSQLLogin WITH LOGIN = YourSQLLogin;

-- Database roles: group by function, not by individual
CREATE ROLE AppAdmins;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.Customers TO AppAdmins;
ALTER ROLE AppAdmins ADD MEMBER AppServiceAccount;

-- Schema as a permission boundary: covers objects added later, automatically
CREATE SCHEMA Sales;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::Sales TO SalesTeam;

-- Passwordless identity (Entra / managed identity) — the modern default
CREATE USER [app-service-identity] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [app-service-identity];

-- Contained database: authentication lives inside the database, not the server
ALTER DATABASE YourDB SET CONTAINMENT = PARTIAL;
CREATE USER ContainedUser WITH PASSWORD = 'YourPassword';
```

## Quick Reference

| Built-in database role | Grants |
|---|---|
| `db_owner` | Full control incl. config — common over-grant, avoid for real users |
| `db_datareader` / `db_datawriter` | Read all tables / write all tables |
| `db_ddladmin` | Run any DDL |
| `db_securityadmin` / `db_accessadmin` | Manage role membership / add-remove users |

| Built-in server role | Grants |
|---|---|
| `sysadmin` | Full instance control — treat like domain admin, short reviewed list |
| `dbcreator` | Create/alter/drop databases |
| `securityadmin` | Manage logins |

| Verify | Query |
|--------|-------|
| What can this principal actually do | `SELECT * FROM sys.fn_my_permissions('Sales.Orders', 'OBJECT')` |
| Everything granted to a principal | `sys.database_permissions` joined to `sys.database_principals` |

## Common Mistakes

### Wrong

Defaulting a real application or human user into `db_owner` because it's convenient, or granting permissions per-table one at a time across a dozen individuals.

### Correct

Grant at the schema level (`GRANT SELECT ON SCHEMA::Sales TO SalesTeam`) and build custom roles scoped to job function; review role membership periodically — an unreviewed role is where over-privileged access quietly accumulates. Prefer `FROM EXTERNAL PROVIDER` (managed identity / Entra) over SQL-authenticated passwords wherever the platform supports it.

## Related

- [recovery-and-ha-dr](recovery-and-ha-dr.md)
- [reference/security-compliance-layers](../reference/security-compliance-layers.md) — encryption, masking, RLS, auditing
