# Document Lifecycle

> **Purpose**: When to create vs. update each document, and how to notice one has gone stale
> **MCP Validated**: not applicable — house convention, not MCP-fed

## When to Use

- Deciding which document a request actually belongs to (a status question is not automatically a new file).
- Running a periodic project check and deciding what's due for an update.
- Onboarding someone new to a project and needing to know what's authoritative.

## Implementation

| Document | Created when | Updated when | Staleness signal |
|----------|---------------|----------------|-------------------|
| understanding-context | First conversation about the project, before the charter | Rarely — it's a point-in-time brainstorm | N/A — historical by design, never "fixed" |
| project-charter | Once initiating is underway and scope is roughly known | Only on a real scope/objective change, never for status | Referenced scope no longer matches what's being built |
| matrix | Once stakeholders are identifiable | Whenever influence/interest shifts — new budget holder, reorg, escalation | No update in 60+ days on an active project |
| kickoff-minutes | Immediately after the kickoff meeting | Never — it's a historical record | N/A |
| project-plan | Once scope, schedule, and resources are set | On major scope/timeline/resourcing change | Milestones in the plan don't match the tracker anymore |
| communication-plan | Once the plan exists | When cadence, channel, or audience changes | Reports are going out on a different cadence than documented |
| meeting-minutes | After every substantive meeting | Never — append a new dated file instead | A meeting happened with no corresponding file |
| progress-reports | On the cadence set in communication-plan | N/A — always a new dated file | Latest file is older than the stated cadence |
| risk-reports | When a new risk is identified, and on the reporting cadence | Existing risk entries updated as status/owner changes | A known blocker isn't reflected in the latest risk report |
| closure-document | Once the project (or phase, or contract) actually ends | N/A — written once | N/A |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Progress report cadence | Weekly | Overridden by whatever `communication-plan.md` states |
| Stakeholder matrix review | Every Monitoring & Controlling checkpoint | Minimum: once per month on active projects |
| Staleness check trigger | On request, or when scaffolding a status document | Not a background poller — checked when the user asks or a new report is due |

## Example Usage

```text
User: "Write this week's status update."

1. Check communication-plan.md for the agreed cadence/audience — don't guess.
2. Check whether last week's progress-reports/ file exists; if not, ask
   whether to backfill or start fresh.
3. Pull real state: tracker (04-execution/ pointer), recent meeting-minutes,
   open risk-reports items.
4. Write progress-reports/<YYYY-MM-DD>.md — never edit a prior week's file.
5. If a new risk surfaced while assembling this, also update risk-reports/,
   don't bury it inside the progress report prose.
```

## See Also

- [scaffold-structure](scaffold-structure.md)
- [document-purposes](../concepts/document-purposes.md)
- [stakeholder-mapping](../concepts/stakeholder-mapping.md)
