---
id: S09
feature: STREAMING_FABRIC_PIPELINE
title: "Promote to prod with fabric-cicd and document the rebuild from zero"
status: backlog
depends_on: [S03, S06, S08]
agent: fabric-cicd-specialist
files: [parameter.yml, scripts/deploy.py, tests/unit/test_deploy.py, .github/workflows/deploy.yml, docs/runbook.md, README.md]
updated: 2026-10-02
---

## Story 9: Promote to prod with fabric-cicd and document the rebuild from zero (`parameter.yml`, `scripts/deploy.py`, `.github/workflows/deploy.yml`)

**Description:** This closes the loop: a merge to `main` publishes the Git-defined items to the prod workspace with `fabric-cicd` and re-applies the reference data, so the whole pipeline can be rebuilt from Git (G7, G10, SC6, SC8, AT-009). It also updates the root README, which still says "Scaffold only" and refers to a planned `generator replay`. It comes last because it needs every item folder from S06 and S08.

**Actual Plan**

- `parameter.yml` (DESIGN Pattern 6): one `find_replace` entry per environment-specific value recorded in `docs/runbook.md` §1 by S06. Those are the dev workspace GUID → `$workspace.id`, the KQL DB GUID → `$items.KQLDatabase.fruit_juice_db.$id`, the Eventhouse GUID → `$items.Eventhouse.fruit_juice_eh.$id`, and the dev query URI → `$items.Eventhouse.fruit_juice_eh.$queryserviceuri`. Each entry is scoped with `item_type` where the value only appears in one item type. Environment keys: `prod` only (dev is Git-synced, never published).
- `scripts/deploy.py`, CLI `python -m scripts.deploy --env prod [--dry-run]`:
  - Builds `FabricWorkspace(workspace_id=$FABRIC_WORKSPACE_ID, environment=args.env, repository_directory="workspace", item_type_in_scope=["Eventhouse","KQLDatabase","Eventstream","KQLDashboard","Reflex","Lakehouse"], token_credential=<cred>)`, with the credential from `scripts.kusto` (`FABRIC_AUTH`; refactor the credential factory into `scripts.kusto.credential()` and reuse it in `client()`).
  - Then calls `publish_all_items(ws)`.
  - `--dry-run` prints the scope and the resolved parameter replacements without calling the API.
  - **Flag (DESIGN A-004, service principal on trial unverified):** the default in CI is `FABRIC_AUTH=sp`. If the publish returns 401/403 on the trial capacity, the runbook §4 documents running `FABRIC_AUTH=cli uv run python -m scripts.deploy --env prod` locally after `az login`, and SC8 is recorded as partially met. Fail loud with that hint in the error message; don't silently skip.
- `tests/unit/test_deploy.py`. Cases:
  - `test_scope_contains_all_six_item_types`
  - `test_parameter_yml_parses_and_targets_prod` (each entry has `replace_value.prod`, and every `find_value` occurs somewhere under `workspace/`)
  - `test_dry_run_makes_no_api_calls` (monkeypatched `publish_all_items`)
  - `test_unknown_env_rejected`
- `.github/workflows/deploy.yml`: on `push` to `main` with paths `workspace/**`, `parameter.yml`, `scripts/**`, `config/**`.
  - Job steps: `astral-sh/setup-uv` → `uv sync` → `uv run python -m scripts.deploy --env prod` → write `.env` from the secrets (`KUSTO_QUERY_URI_PROD`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `FABRIC_WORKSPACE_ID_PROD`) → `uv run python -m scripts.post_deploy`.
  - `FABRIC_AUTH=sp`; `concurrency: deploy-prod`.
- `docs/runbook.md`:
  - §4 "Prod and CI": create `lab-streaming-fabric-prod`; service principal and tenant setting "Service principals can use Fabric APIs"; workspace Contributor grant; GitHub secrets list; first deploy.
  - §5 "Rebuild from zero" (AT-009): a checklist that recreates both workspaces on a fresh trial from Git only, ending with S07's `pytest -m e2e` against prod. Time it and record the result against SC6's ≤ 30 min.
  - Note that the prod Eventstream gets its **own** connection string (DESIGN Decision 4).
- Root `README.md` (currently 28 lines):
  - Replace "Status: Scaffold only. Depends on the replay producer…" with the current status.
  - Update the Stack table: drop Event Hubs and the Spark bridge (YAGNI in BRAINSTORM).
  - Architecture as in the DESIGN DAG diagram; a quick start linking `docs/runbook.md`.
  - G12: a "Late data: KQL vs Flink" section (late events land in their own window and are flagged and counted, vs Flink dropping them after the watermark).

**Architecture**

```text
push main (workspace/**, parameter.yml, scripts/**, config/**)
  └─ deploy.yml ─► scripts.deploy --env prod ─► fabric-cicd publish_all_items(scope 6 types, parameter.yml prod)
                                                     └─ prod: Eventhouse, KQL DB (DatabaseSchema.kql), Eventstream,
                                                        dashboard, Reflex, Lakehouse
               └─► scripts.post_deploy (prod .env) ─► dims, target, target_scale(), late_threshold(), OneLake
               [401/403 on trial ─► fail with hint → runbook §4 local FABRIC_AUTH=cli]
```

**Acceptance Criteria**

- [ ] `uv run python -m scripts.deploy --env prod --dry-run` lists the six item types and the four replacements, with no API calls (unit-tested)
- [ ] Every `find_value` in `parameter.yml` exists under `workspace/`, and no GUID from the dev workspace remains in the prod items after a publish (check with `git grep` on the replaced values in a dry-run render)
- [ ] A merge to `main` touching `workspace/**` runs `deploy.yml`: publish, then `post_deploy`, both green. Or, if the service principal is rejected on trial, the job fails with the runbook §4 hint and the local `cli` path succeeds (recorded as the SC8 exception).
- [ ] After the prod deploy, `pytest -m e2e` against prod passes AT-001 (AT-009)
- [ ] `docs/runbook.md` §5 rebuild checklist is executed once, with its measured duration recorded
- [ ] Root `README.md` no longer mentions Event Hubs, the Spark bridge or `generator replay`, and includes the KQL vs Flink late-data section
- [ ] `tests/unit/test_deploy.py` has the four cases and passes in PR CI
- [ ] No secrets in `parameter.yml`, workflows (only `${{ secrets.* }}` references) or committed files
