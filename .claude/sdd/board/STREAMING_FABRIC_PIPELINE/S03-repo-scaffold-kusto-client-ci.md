---
id: S03
feature: STREAMING_FABRIC_PIPELINE
title: "Scaffold the repo: git, root Python project, config, Kusto client and PR CI"
status: ready
depends_on: []
agent: python-developer
files: [pyproject.toml, .gitignore, .env.example, config/pipeline.toml, scripts/kusto.py, tests/unit/test_kusto.py, .github/workflows/ci.yml]
updated: 2026-10-02
---

## Story 3: Scaffold the repo: git, root Python project, config, Kusto client and PR CI (`pyproject.toml`, `scripts/kusto.py`, `.github/workflows/ci.yml`)

**Description:** Today the repo root holds only `README.md` and `sources/`. It isn't a git repository, and it has no root Python project or CI. Fabric Git integration needs a GitHub repo, so this story creates the skeleton every later root-level story builds on. That includes the shared Kusto client (`FABRIC_AUTH=sp|cli`, DESIGN Pattern 4) used by S05 and S07, and the PR workflow (DESIGN file 27). It's the foundation for S04, S05, S07 and S09.

**Actual Plan**

- `git init` with `main` as the default branch. Initial commit of the existing tree (`README.md`, `sources/`, `.claude/`). **Don't create or push a GitHub remote.** The user creates `uriel-labs/lab-streaming-fabric` (name to confirm) and pushes; the runbook (S06) records the URL.
- Root `.gitignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `.env`, `/data/`, `sources/data/`, `.claude/sdd/board/*/BOARD.html`.
- Root `pyproject.toml`:
  - Project `lab-streaming-fabric`, Python ≥ 3.11, dependencies `azure-kusto-data>=4`, `azure-identity>=1.15`, `pandas>=2.2`, `fabric-cicd>=0.1`, plus `fabric-sources` from path `sources` (`[tool.uv.sources] fabric-sources = { path = "sources", editable = true }`).
  - Dev group: `pytest>=8`, `ruff>=0.6`.
  - `[tool.pytest.ini_options] testpaths = ["tests"]`, `markers = ["e2e: needs a live Fabric KQL database and Eventstream"]`, `addopts = "-m 'not e2e'"`.
  - `[tool.ruff] line-length = 120`, matching the ~120-column style in `sources/src/generator/cli.py`.
- Root `.env.example`: `KUSTO_QUERY_URI=`, `KUSTO_DATABASE=fruit_juice_db`, `FABRIC_AUTH=cli`, `AZURE_TENANT_ID=`, `AZURE_CLIENT_ID=`, `AZURE_CLIENT_SECRET=`, `FABRIC_WORKSPACE_ID=`, each with a one-line comment. Same plain `KEY=value` rules as `sources/.env.example:1`.
- `config/pipeline.toml`: exactly the `[kql]`, `[demo]`, `[target]` and `[e2e]` tables from DESIGN Pattern 6.
- `scripts/__init__.py` (empty) and `scripts/kusto.py`, per DESIGN Pattern 4:
  - `load_env()` reads the repo-root `.env` with the same rules as `sources/src/generator/config.py:parse_env`. Import and reuse `generator.config.parse_env(path)` rather than duplicating it; shell variables win.
  - `client() -> KustoClient` (`FABRIC_AUTH`: `cli` → `AzureCliCredential`, `sp` → `ClientSecretCredential`; anything else → `ValueError`).
  - `database() -> str`, `literal(value) -> str` (strings escape `\` and `'`; `None` → `dynamic(null)`; bool → `true`/`false`; datetime → `datetime(<iso>)`; numbers via `repr`).
  - `replace_table(kc, db, table, schema, rows, batch=500)`.
  - `query_df(kc, db, kql) -> pandas.DataFrame`.
  - `mgmt(kc, db, command)`.
- `tests/unit/test_kusto.py` (pytest, function-per-case like `sources/tests`). Cases:
  - `test_literal_escapes_quotes_and_backslashes`
  - `test_literal_types` (None, bool, int, float, datetime, str)
  - `test_replace_table_batches_and_verbs` (fake client records commands: first `.set-or-replace`, then `.set-or-append`; 1,001 rows → 3 commands)
  - `test_replace_table_empty_rows_still_replaces`
  - `test_client_rejects_unknown_auth`
- `.github/workflows/ci.yml`: on `pull_request` and `push` to `main`. Job on `ubuntu-latest`: `astral-sh/setup-uv`, then `uv sync` → `uv run ruff check .` → `uv run pytest` (root, e2e excluded by addopts) → `cd sources && uv sync && uv run pytest`. No secrets used.

**Architecture**

```text
repo/
  pyproject.toml ──path dep──► sources/ (generator)
  scripts/kusto.py: load_env → client(FABRIC_AUTH) → mgmt / query_df / replace_table(literal)
  config/pipeline.toml  (read by S05 post_deploy, S07 e2e)
  .github/workflows/ci.yml: ruff → pytest (root, not e2e) → pytest (sources)
```

**Acceptance Criteria**

- [ ] `git status` works at the repo root and `.env` / `.venv` / `data/` are ignored (`git check-ignore .env` succeeds)
- [ ] `uv sync` at the root installs and `uv run python -c "import generator, scripts.kusto"` succeeds
- [ ] `uv run ruff check .` passes on the whole repo, including `sources/`
- [ ] `uv run pytest` at the root runs `tests/unit/test_kusto.py` (5 cases green) and doesn't collect e2e tests
- [ ] `literal("O'Brien\\x")` returns `'O\'Brien\\\\x'` (quote and backslash escaped)
- [ ] `scripts/kusto.py` reuses `generator.config.parse_env`; there's no second `.env` parser in the repo
- [ ] `ci.yml` uses no secrets and runs both test suites
- [ ] No GitHub remote is created and nothing is pushed by this story
