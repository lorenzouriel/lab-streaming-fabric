# High Availability & High Throughput for Real-Time Pipelines

> **Purpose**: Configure Kafka and Flink for zero-downtime failover and sustained high-volume event processing
> **Researched**: 2026-09-16 (web-verified, see Sources)

## When to Use

- Designing a production streaming pipeline that must survive broker/node/AZ failure without data loss
- Sizing partitions, replication, and parallelism for a target events/sec throughput
- Choosing between availability guarantees (durability) and raw throughput when they trade off against each other

## The HA/Throughput Tension

Every durability knob (more replicas, `acks=all`, sync flushes) costs latency and throughput; every throughput knob (larger batches, fewer replicas, async acks) costs durability or failover speed. Size deliberately per data class rather than applying one config cluster-wide — payment events and clickstream events do not need the same guarantees.

## Kafka: High Availability

```text
Production baseline (per Confluent, AutoMQ, and AWS MSK guidance):
- Replication factor: 3, spread across 3 AZs (one replica per AZ)
- min.insync.replicas: 2  -- tolerates 1 replica loss while keeping strong durability
- Producer acks: all       -- leader waits for all in-sync replicas before ack
- Broker count: >= 3 (KRaft controller quorum: 3 or 5 controllers, odd number)
- Rack awareness (broker.rack) set per AZ so replica placement spans failure domains
```

| Setting | Production Value | Effect |
|---------|-------------------|--------|
| `replication.factor` | `3` | Survives loss of 1-2 brokers/AZs depending on placement |
| `min.insync.replicas` | `2` | Writes fail fast rather than silently under-replicating when ISR shrinks below 2 |
| `acks` (producer) | `all` | Strongest durability; leader confirms only after ISR replicas ack |
| `unclean.leader.election.enable` | `false` | Never elects an out-of-sync replica as leader (prevents silent data loss) |
| Controller quorum (KRaft) | `3` or `5` | Odd count avoids split-brain in controller election |

**Multi-AZ vs. multi-region:** multi-AZ replication handles broker and single-AZ failure inside one region. It is not disaster recovery — a full regional outage needs cross-region replication (MirrorMaker2 or a managed replicator) with an explicit RPO/RTO target, since cross-region replication is inherently asynchronous.

## Kafka: High Throughput

```text
partitions_needed ≈ target_throughput_MBps / per_partition_throughput_MBps
# per-partition throughput is typically 5-15 MB/s depending on message size and compression
```

| Setting | Value | Effect |
|---------|-------|--------|
| Partition count | Sized to target parallelism | Partitions are Kafka's unit of parallelism -- more partitions, more concurrent consumers, but slower rebalances and leader failover |
| `linger.ms` | `10-50` | Batches messages before sending -- trades a few ms latency for much higher throughput |
| `batch.size` | `64KB-256KB` | Larger batches amortize network overhead |
| `compression.type` | `zstd` or `lz4` | Reduces network/disk I/O; zstd gives the best ratio, lz4 the lowest CPU cost |
| `fetch.min.bytes` (consumer) | `>1` | Consumer waits to accumulate data before fetching, reducing request overhead |

**Partition count is a durability/ops trade-off too:** very high partition counts increase metadata overhead and slow down leader election during failover, working against the HA goals above. Pick partition count from target throughput, not "as many as possible."

## Flink: High Availability

```text
JobManager HA (Kubernetes HA services or ZooKeeper quorum):
- Run >= 2 JobManager replicas (1 leader, N standby)
- On leader failure, a standby is elected and resumes from the last completed checkpoint
- Checkpoint metadata + job graph stored in a shared, durable store (S3/HDFS/GCS), not local disk
```

| Setting | Production Value | Effect |
|---------|-------------------|--------|
| Checkpoint interval | `1-5 min` | Lower = faster recovery, higher = less runtime overhead |
| Checkpoint storage | S3 / HDFS / GCS | Durable, shared across JobManager replicas -- required for HA |
| State backend | RocksDB (incremental) | Handles state larger than memory; incremental checkpoints avoid re-uploading unchanged state |
| Restart strategy | `exponential-delay` | Avoids restart storms hammering a degraded downstream system |
| Savepoints | Manual, before upgrades/rescaling | Never rely on checkpoints for planned migrations -- use savepoints |

## Flink: High Throughput

| Technique | Effect |
|-----------|--------|
| Parallelism = Kafka partition count | Avoids idle subtasks; one Flink subtask per partition is the natural ceiling |
| Incremental RocksDB checkpoints | Dramatically cuts checkpoint duration/storage on large state, which reduces backpressure caused by checkpoint stalls |
| Async state API (Flink 2.0+, State V2) | Overlaps state access with I/O instead of blocking the operator thread |
| Operator chaining | Reduces serialization/network overhead between chained operators on the same subtask |
| Watch backpressure metrics | Sustained backpressure on a subtask means it (or a downstream sink) is the bottleneck -- scale that operator, don't just add parallelism everywhere |

## Configuration Summary

| Goal | Kafka | Flink |
|------|-------|-------|
| Survive broker/node failure | RF=3, min.insync.replicas=2, acks=all | JobManager HA (2+ replicas), checkpoint storage on durable FS |
| Survive AZ failure | Rack-aware replica placement across 3 AZs | Multi-AZ TaskManager deployment |
| Survive region failure | Cross-region replication (MirrorMaker2/MSK Replicator), explicit RPO/RTO | Cross-region savepoint restore runbook |
| Maximize throughput | Partition count sized to target MB/s, batching + compression | Parallelism = partitions, incremental checkpoints, async state |

## See Also

- [kafka-fundamentals concept](../concepts/kafka-fundamentals.md)
- [flink-architecture concept](../concepts/flink-architecture.md)
- [production-best-practices](production-best-practices.md)

## Sources

- [Kafka Multi-AZ Architecture: High Availability Without Letting Replication Cost Explode — AutoMQ](https://www.automq.com/blog/kafka-multi-az-architecture-high-availability-without-letting-replication-cost-explode)
- [Kafka Disaster Recovery: RPO, RTO, Multi-AZ, Multi-Region, and Failover Choices — AutoMQ](https://www.automq.com/blog/kafka-disaster-recovery-rpo-rto-multi-az-multi-region-and-failover-choices)
- [Guide to Apache Kafka Disaster Recovery and Multi-Region Architectures — SoftwareMill](https://softwaremill.com/guide-to-apache-kafka-disaster-recovery-and-multi-region-architectures/)
- [Amazon MSK Replicator and MirrorMaker2 — AWS Big Data Blog](https://aws.amazon.com/blogs/big-data/amazon-msk-replicator-and-mirrormaker2-choosing-the-right-replication-strategy-for-apache-kafka-disaster-recovery-and-migrations/)
- [Tuning Checkpoints and Large State — Apache Flink docs](https://nightlies.apache.org/flink/flink-docs-master/docs/ops/state/large_state_tuning/)
- [Using RocksDB State Backend in Apache Flink: When and How — Apache Flink blog](https://flink.apache.org/2021/01/18/using-rocksdb-state-backend-in-apache-flink-when-and-how/)
- [Running Flink in Production: The Operations Guide — Streamkap](https://streamkap.com/resources-and-guides/flink-production-guide)
- [Top Trends for Data Streaming with Apache Kafka and Flink in 2026 — Kai Waehner](https://www.kai-waehner.de/blog/2025/12/10/top-trends-for-data-streaming-with-apache-kafka-and-flink-in-2026/)
