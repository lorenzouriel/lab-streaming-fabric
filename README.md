# lab-streaming-fabric
Streaming and event-driven pipeline on **Microsoft Fabric Real-Time Intelligence**, replaying the Fruit Juice sales data from [`lab-sources`](../lab-sources) as an event stream.

## Stack
| Layer | Tooling |
|---|---|
| Event source | Azure Event Hubs |
| Ingestion / routing | Eventstreams (with in-flight transformations) |
| Storage and analytics | Eventhouse (KQL database) |
| Querying | KQL, real-time dashboards |
| Alerting | Activator (rules and actions on streaming conditions) |
| Batch bridge | Spark Structured Streaming notebooks into the Lakehouse |
| CI/CD | Fabric Git integration, `fabric-cicd`, deployment pipelines |

## Architecture
Replay producer → Eventstream → Eventhouse (hot, KQL) and Lakehouse (Delta, history) → real-time dashboard and Activator alerts (for example, revenue drops below target).

## CI/CD plan
- Eventstream, Eventhouse, KQL queryset and dashboard items versioned in Git.
- `fabric-cicd` publishes to test and prod with parameterised connections.

## Status
Scaffold only. Depends on the replay producer planned for `lab-sources` (`generator replay`). Planned contents: `workspace/`, `kql/`, `notebooks/`, `tests/`, `.github/workflows/`.

## Prerequisites
Fabric capacity (trial or F-SKU), Event Hubs namespace or equivalent, service principal for CI/CD.
