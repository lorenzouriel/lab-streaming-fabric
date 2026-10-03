---
id: S08
feature: STREAMING_FABRIC_PIPELINE
title: "Build the real-time dashboard and the revenue-below-target Activator alert"
status: backlog
depends_on: [S05, S06]
agent: fabric-logging-specialist
files: [workspace/sales_dashboard.KQLDashboard/, workspace/revenue_alerts.Reflex/, docs/runbook.md]
updated: 2026-10-02
---

## Story 8: Build the real-time dashboard and the revenue-below-target Activator alert (`workspace/sales_dashboard.KQLDashboard/`, `workspace/revenue_alerts.Reflex/`)

**Description:** Delivers the visible half of the lab: a real-time dashboard over the KQL reader functions (G9) and an Activator rule that emails when revenue to date falls below 90% of the prorated daily target (G8, DESIGN Decision 5). Both are built in the dev portal and committed through Git sync, like S06. It depends on S06 (live database) and S05 (`target_scale()` and the targets loaded). It's a prerequisite for S09 (prod promotion of these items).

**Actual Plan**

- In dev, create the real-time dashboard `sales_dashboard` with data source `fruit_juice_db` and auto refresh 30 s (KB `real-time-dashboard`). Tiles, using **only** the functions from S04 (no ad-hoc table queries):
  1. Revenue per minute, as a time chart: `kpi_product() | summarize revenue=sum(revenue) by window_start`.
  2. Revenue by product, top 10: `kpi_product() | summarize revenue=sum(revenue), margin=sum(margin) by cod_produto | top 10 by revenue`. Join `dim_produto` in the tile for labels.
  3. Revenue by factory: `kpi_factory()`.
  4. Events per minute: `kpi_product() | summarize events=sum(events) by window_start`.
  5. Ingestion lag p95: `materialized_view('sales_dedup') | summarize p95=percentile(ingested_at - emitted_at, 95)`, with the subtitle "meaningful only for --speed 1 without --as-of" (DESIGN Decision 3).
  6. Duplicates: `print duplicate_count()`.
  7. Late events: `late_events() | count`.
  8. Unmatched codes: `unmatched_dims() | count`.
  9. Revenue vs target: `revenue_vs_target()`, a stat tile on `pct_of_target`.
- Activator: on tile 9, **Set alert** → new Reflex item `revenue_alerts`, condition `pct_of_target < 90`, check every 5 min, action **email** to the workspace owner, snooze 15 min (KB `alerting-rules`: snooze ≥ evaluation interval).
- Commit to Git from the workspace → `workspace/sales_dashboard.KQLDashboard/` and `workspace/revenue_alerts.Reflex/`. `git pull`.
- **Flag (DESIGN A-003, Activator Git is preview):** if the Reflex folder isn't produced or doesn't reload with **Update from Git**, keep the dashboard in Git and write `docs/runbook.md` §3 "Activator manual setup" (the 5 steps above). Record the deviation in the runbook's Known issues. This is the documented SC6 exception; it doesn't block this story.
- `docs/runbook.md` §2 "Demo: revenue alert" (AT-008):
  1. `uv run python -m scripts.post_deploy` (ensures `target_scale()`).
  2. Clear the tables (the same commands as S07's `clean_db`).
  3. **Below-target run:** `generator stream --sink kafka --fixed-clock --as-of 2026-10-02 --rate <nominal_rate/2> --speed 120 --duration 600`. Expect an email within 5 min of `pct_of_target` < 90.
  4. Clear, then a **control run** at `--rate <nominal_rate>`: no email over 10 min.
  - The default `demo.nominal_rate = 5.0` comes from DESIGN Pattern 6. If the control run doesn't land in the 95–105% range, the runbook says to raise `demo.target_mean_sample` and re-run `post_deploy`, not to edit the rule.
- No new code files; the KQL lives in S04's functions.

**Architecture**

```text
fruit_juice_db functions ─► sales_dashboard (9 tiles, 30 s refresh)
                                   └─ tile 9: revenue_vs_target().pct_of_target
                                          └─► revenue_alerts.Reflex: pct < 90, every 5 min, snooze 15 min ─► email
demo: stream at nominal_rate/2 (--speed 120) ─► pct ≈ 50 ─► alert   |   nominal_rate ─► pct ≈ 100 ─► none
```

**Acceptance Criteria**

- [ ] `workspace/sales_dashboard.KQLDashboard/` is committed by Git sync, and every tile query references only S04 functions, `materialized_view('sales_dedup')` or dimension tables
- [ ] With a live run, the tiles show non-zero revenue, events and lag; duplicates and late counts match the producer summary line of the same run
- [ ] The below-target demo produces exactly one email within 5 min (snooze prevents repeats for 15 min) (AT-008)
- [ ] The control run at `nominal_rate` produces no email over 10 min, and `pct_of_target` shows 90–110
- [ ] Either `workspace/revenue_alerts.Reflex/` round-trips through **Update from Git**, or the runbook §3 manual fallback plus a Known issues entry exists. One of the two is in place.
- [ ] `docs/runbook.md` §2 contains the exact demo commands with `--rate` values derived from `demo.nominal_rate`
