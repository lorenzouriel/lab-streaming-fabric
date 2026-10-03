---
id: S06
feature: STREAMING_FABRIC_PIPELINE
title: "Bootstrap the dev workspace: Eventhouse, KQL DB, Eventstream and Lakehouse synced to Git"
status: backlog
depends_on: [S02, S04, S05]
agent: fabric-architect
files: [workspace/fruit_juice_eh.Eventhouse/, workspace/fruit_juice_db.KQLDatabase/, workspace/sales_stream.Eventstream/, workspace/fruit_juice_lh.Lakehouse/, docs/runbook.md]
updated: 2026-10-02
---

## Story 6: Bootstrap the dev workspace: Eventhouse, KQL DB, Eventstream and Lakehouse synced to Git (`workspace/`, `docs/runbook.md`)

**Description:** Creates the dev Fabric items once in the portal and commits their Fabric-generated definitions through Git integration. Those JSON formats can't reliably be hand-authored (DESIGN file manifest note). After that, Git is the source of truth. This story is mostly operator steps plus the runbook that makes them repeatable, and it's where the first live event lands in `sales_raw`. It's a prerequisite for S07 (e2e), S08 (dashboard and Activator) and S09 (prod promotion).

**Actual Plan**

- **Prerequisite:** the GitHub remote exists and `main` is pushed (S03 leaves this to the user).
- Write `docs/runbook.md` §1 "Bootstrap dev" as a numbered checklist, then follow it once:
  1. Start the Fabric trial; create workspace `lab-streaming-fabric-dev` on it.
  2. Workspace settings → Git integration → connect to the GitHub repo, branch `main`, **Git folder `workspace`**.
  3. Create Eventhouse `fruit_juice_eh`. Its default KQL database is renamed or created as `fruit_juice_db`.
  4. Commit to Git from the workspace. This generates `workspace/fruit_juice_eh.Eventhouse/{.platform,EventhouseProperties.json}` and `workspace/fruit_juice_db.KQLDatabase/{.platform,DatabaseProperties.json,DatabaseSchema.kql}`.
  5. Locally, `git pull`, then restore S04's `DatabaseSchema.kql` over the generated one (`git checkout <S04 commit> -- workspace/fruit_juice_db.KQLDatabase/DatabaseSchema.kql`). Commit, push, then **Update from Git** in the workspace. Verify with `.show tables`, `.show materialized-views` and `.show functions`.
  6. Fill the root `.env` (`KUSTO_QUERY_URI` from Eventhouse → Query URI, `KUSTO_DATABASE=fruit_juice_db`), then `az login` and `uv run python -m scripts.post_deploy` (S05).
  7. Create Eventstream `sales_stream`:
     - Source: custom endpoint `producer`.
     - Destination: Eventhouse with **"Event processing before ingestion"** (not Direct Ingestion, per DESIGN Decision 4), KQL DB `fruit_juice_db`, existing table `sales_raw`, input format JSON, mapping `sales_raw_json`. Publish.
  8. Copy the Kafka tab values into `sources/.env`: `KAFKA_BOOTSTRAP`, `KAFKA_TOPIC`, `KAFKA_SASL_PASSWORD`, plus the fixed SASL lines from S02.
  9. Smoke test: `cd sources && uv sync --extra stream && uv run generator stream --sink kafka --fixed-clock --as-of 2026-10-02 --rate 20 --count 100 --seed 42`. Expect `sales_raw | count` = 100 and `materialized_view('sales_dedup') | count` = 100 within 120 s, and `unmatched_dims() | count` = 0.
  10. Create Lakehouse `fruit_juice_lh` with OneLake shortcuts (Eventhouse source) to `sales_enriched` and the six `dim_*` tables. If S05's mirroring command was rejected, first turn on OneLake availability for those tables in the KQL DB UI.
  11. Commit to Git from the workspace, then `git pull`. The new folders are `sales_stream.Eventstream/` and `fruit_juice_lh.Lakehouse/`.
- Record in the runbook which IDs appear in the committed JSON (workspace, Eventhouse, KQL DB GUIDs, query URI). S09's `parameter.yml` replaces exactly these. Capture them with `git grep -n -E '[0-9a-f]{8}-[0-9a-f]{4}'` over `workspace/`.
- **Flags to record in `docs/runbook.md` §Known issues if observed** (DESIGN assumptions, not DEFINE open questions):
  - whether `ingested_at` is populated by `ingestion_time()` in the update policy
  - whether the Eventstream destination kept "processed ingestion" after commit
- No secrets are committed: `.env` files stay ignored. Verify with `git grep -n "SharedAccessKey"` = empty.

**Architecture**

```text
portal (once) ──► Fabric dev workspace ──Git sync (folder workspace/)──► GitHub main
                     fruit_juice_eh / fruit_juice_db  ◄── DatabaseSchema.kql (S04) via Update from Git
                     sales_stream: custom endpoint ─► Eventhouse dest (processed, sales_raw_json)
                     fruit_juice_lh: shortcuts ─► sales_enriched, dim_*
generator stream --sink kafka (S02) ─► sales_stream ─► sales_raw ─► … sales_dedup   [smoke: 100 = 100]
post_deploy.py (S05) ─► dim_*, revenue_target_daily, target_scale(), late_threshold()
```

**Acceptance Criteria**

- [ ] `workspace/` contains `fruit_juice_eh.Eventhouse/`, `fruit_juice_db.KQLDatabase/` (with S04's `DatabaseSchema.kql`, not the generated one), `sales_stream.Eventstream/` and `fruit_juice_lh.Lakehouse/`, all committed by Fabric Git sync
- [ ] After **Update from Git**, `.show materialized-views` lists `sales_dedup`, `kpi_product_1m`, `kpi_client_1m`, `kpi_factory_1m`, all enabled
- [ ] The smoke run delivers 100/100 events to `sales_raw` within 120 s, with `unmatched_dims()` = 0
- [ ] The Eventstream destination uses processed ingestion with mapping `sales_raw_json` (visible in the committed Eventstream definition)
- [ ] The Lakehouse shortcut to `sales_enriched` returns the same row count as KQL (SC9, after the OneLake sync)
- [ ] `git grep -n "SharedAccessKey\|AZURE_CLIENT_SECRET="` over the repo finds no secret values
- [ ] `docs/runbook.md` §1 lists every step above, plus the list of environment-specific IDs found in `workspace/`
