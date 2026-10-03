# Database CI/CD

> **Purpose**: Treating the database as code with SQL database projects, dacpac/SqlPackage, schema-drift detection, and a gated CI/CD pipeline
> **MCP Validated**: 2026-09-16

## When to Use

- Replacing manual/ad-hoc schema deployments with a declarative, versioned, diffable process
- Detecting and reconciling schema drift (a hotfix applied via SSMS that the project doesn't know about)
- Wiring database deployment into GitHub Actions / Azure DevOps with review gates

## Implementation

```bash
dotnet new sqlproj -n SalesDbProject     # SDK-style: cross-platform, .NET 8+, default globbing
dotnet build SalesDbProject.sqlproj      # validates every object reference -> bin/Debug/SalesDbProject.dacpac
dotnet tool install --global microsoft.sqlpackage

# ALWAYS preview before deploying to production — SqlPackage diffs and drops what it doesn't know about
sqlpackage /Action:Script       /SourceFile:...dacpac /TargetConnectionString:"..." /OutputPath:deploy-script.sql
sqlpackage /Action:DeployReport /SourceFile:...dacpac /TargetConnectionString:"..." /OutputPath:report.xml
sqlpackage /Action:Publish      /SourceFile:...dacpac /TargetConnectionString:"..."
```

```sql
-- Post-deployment seed data MUST be idempotent (it reruns on every deploy)
MERGE INTO [dbo].[OrderStatuses] AS target
USING (VALUES (1, N'Pending'), (2, N'Processing')) AS source ([StatusID], [StatusName])
ON target.[StatusID] = source.[StatusID]
WHEN MATCHED THEN UPDATE SET [StatusName] = source.[StatusName]
WHEN NOT MATCHED THEN INSERT ([StatusID], [StatusName]) VALUES (source.[StatusID], source.[StatusName]);
```

```bash
# Detect schema drift: extract live schema, let Git report the delta
sqlpackage /Action:Extract /SourceConnectionString:"..." /TargetFile:SalesDbProject /p:ExtractTarget=SchemaObjectType
git status --porcelain | wc -l   # automated drift count
```

## Configuration

| Layer | GitHub Actions | Azure DevOps |
|---|---|---|
| Build | `dotnet build *.sqlproj` -> upload `.dacpac` artifact | `DotNetCoreCLI@2` -> `PublishBuildArtifacts@1` |
| Deploy | `azure/sql-action@v2.3` (supports SQL auth, Entra, service principal) | `SqlAzureDacpacDeployment@1` |
| Secrets | Repo/environment secrets, or OIDC via `azure/login` (no stored credential) | Service connection + branch control checks |
| Gates | Environment protection rules, `CODEOWNERS`, required reviewers | Branch policies, build validation |

## Example Usage

```yaml
# Two-stage pipeline: build once into a .dacpac, deploy that SAME artifact through every environment
jobs:
  build:
    steps:
      - run: dotnet build ./SalesDbProject.sqlproj -o ./output
      - uses: actions/upload-artifact@v4
        with: { name: dacpac, path: ./output/SalesDbProject.dacpac }
  deploy:
    needs: build
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dacpac }
      - uses: azure/login@v2
        with: { client-id: "${{ secrets.AZURE_CLIENT_ID }}", tenant-id: "${{ secrets.AZURE_TENANT_ID }}", subscription-id: "${{ secrets.AZURE_SUBSCRIPTION_ID }}" }
      - uses: azure/sql-action@v2.3
        with: { connection-string: "${{ secrets.AZURE_SQL_CONNECTION_STRING }}", path: './SalesDbProject.dacpac', action: 'publish' }
```

Three testing layers, each catching what the previous can't: **build validation** (structure), **unit tests** (pre-test/test/post-test with Row Count / Scalar Value / Expected Schema conditions, plus negative tests via `ExpectedSqlException`), **integration tests** (a dedicated, auto-deployed, reset-to-known-state database — never production).

## See Also

- [azure-sql-tuning](azure-sql-tuning.md)
- [error-handling](error-handling.md)
