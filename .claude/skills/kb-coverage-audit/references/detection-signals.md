# Stack detection signals

Non-exhaustive starting points for step 1 of the audit. Read whichever of these exist
in the project being scanned; skip categories with no matching files. If the project
uses a format not listed here, still read and normalize it — this list is a starting
point, not a whitelist.

## Containers / infra

- `docker-compose.yml`, `docker-compose.*.yml` — read every `image:` line (the part
  before `:` or `@sha256:` is the tool; a registry prefix like `quay.io/`,
  `mcr.microsoft.com/`, `ghcr.io/` still names a real product) and every
  `container_name:` for a human label.
- `Dockerfile`, `*.Dockerfile` — `FROM` lines.
- Kubernetes manifests (`*.yaml`/`*.yml` under `k8s/`, `manifests/`, or containing
  `apiVersion:`/`kind: Deployment`) — `image:` fields, plus `kind:` for the platform
  primitives in use (Ingress controller, CRDs naming an operator, etc.).
- Helm — `Chart.yaml` `dependencies:`, `values.yaml` image repositories.

## Language / package manifests

- Node/JS/TS: `package.json` (`dependencies`, `devDependencies`), lockfiles only to
  confirm a package manager choice (npm/pnpm/yarn/bun), not for exhaustive deps.
- Python: `requirements*.txt`, `pyproject.toml` (`[project.dependencies]` or
  `[tool.poetry.dependencies]`), `Pipfile`.
- Go: `go.mod`.
- Rust: `Cargo.toml`.
- Ruby: `Gemfile`.
- PHP: `composer.json`.
- Java/Kotlin: `pom.xml`, `build.gradle`/`build.gradle.kts`.
- .NET: `*.csproj`, `*.sln`/`*.slnx`, `packages.config`, `Directory.Packages.props`.

## Infrastructure as code

- Terraform: `*.tf` — `provider "..."` blocks and `resource "<type>.."` prefixes name
  the cloud/service directly (e.g. `resource "aws_glue_job"` implies AWS Glue).
- CloudFormation / SAM: `template.yaml`/`template.json` — `Resources.*.Type`.
- Pulumi: language-native files under `infra/`/`pulumi/` — imported provider packages.
- CDK: `cdk.json` plus the stack source files' imports.

## CI/CD

- `.github/workflows/*.yml` — `uses:` actions and any service containers defined
  under `services:`.
- `azure-pipelines.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`.

## Naming and docs signals

- Top-level directory names are often the tool's category, not its identity (a folder
  called `lakehouse` or `monitor` tells you the *purpose*, not the *product*) — open
  that folder's `README.md` and its compose/config files to get the actual product
  names.
- Config file names inside a folder are frequently a direct giveaway
  (`otel-config.yaml`, `prometheus.yml`, `loki-config.yaml`, `tempo-config.yaml` each
  name their tool outright).
- `.env.example` variable prefixes sometimes name a product (`RUSTFS_VERSION`,
  `ICEBERG_REST_VERSION`) even when no compose file is present.

## Normalizing what you find

Collapse variants to one canonical name before matching against the KB registry —
e.g. `mcr.microsoft.com/mssql/server` → "SQL Server", `grafana/loki` → "Loki",
`trinodb/trino` → "Trino". Keep the category alongside the name (database, query
engine, observability, object storage, orchestration, ...); the KB registry match in
SKILL.md step 4 is done per-category first, per-name second.
