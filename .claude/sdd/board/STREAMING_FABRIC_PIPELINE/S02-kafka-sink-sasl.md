---
id: S02
feature: STREAMING_FABRIC_PIPELINE
title: "Make the Kafka sink authenticate to the Eventstream endpoint (SASL_SSL) and fail loud"
status: backlog
depends_on: [S01]
agent: python-developer
files: [sources/src/generator/sinks.py, sources/src/generator/cli.py, sources/.env.example, sources/tests/test_sinks.py]
updated: 2026-10-02
---

## Story 2: Make the Kafka sink authenticate to the Eventstream endpoint (SASL_SSL) and fail loud (`sources/src/generator/sinks.py`)

**Description:** Today `KafkaSink` only sets `bootstrap_servers`, so it can't reach the Eventstream custom endpoint, which requires SASL_SSL / PLAIN with `$ConnectionString` (DESIGN A-001). This story reads the security settings from `.env`, fails at startup on auth or topic errors (AT-007), and turns undelivered events into a non-zero exit. It depends on S01 only because both edit `cli.stream()`. It's a prerequisite for S06 (live ingestion) and S07 (e2e).

**Actual Plan**

- `sources/src/generator/sinks.py:42-55` (`KafkaSink.__init__`): build a `security` dict from `.env` keys `KAFKA_SECURITY_PROTOCOL` (default `PLAINTEXT`), `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD`. Map them to `security_protocol`, `sasl_mechanism`, `sasl_plain_username` and `sasl_plain_password`, dropping empty values. Pass `acks="all", retries=5, request_timeout_ms=30_000, **security` to `KafkaProducer` (lines 51-55).
- After construction, call `self._producer.partitions_for(self._topic)`. On an exception or empty result, raise `RuntimeError(f"cannot reach topic {topic!r} on {bootstrap}")`. **Never include the password in the message.**
- `sinks.py:57-60` (`write`): attach `.add_errback(self._on_error)` to the `send` future. `_on_error` increments `self.failures` (initialised to 0 in `__init__`).
- `sinks.py:62-64` (`close`): `flush(timeout=30)` (was 10).
- Give `StdoutSink` and `FileSink` (lines 18-39) a class attribute `failures = 0` so the CLI can read it uniformly.
- `sources/src/generator/cli.py:65-69` already maps `RuntimeError` → exit 2. Keep it, and also catch `kafka.errors.KafkaError` subclasses raised at construction by mapping them to `RuntimeError` inside `KafkaSink`.
- `cli.py:86-88`: after `sink.close()`, if `sink.failures > 0` print `error: N event(s) not delivered` to stderr and return **3**.
- `sources/.env.example`: add a commented Eventstream block with `KAFKA_SECURITY_PROTOCOL=SASL_SSL`, `KAFKA_SASL_MECHANISM=PLAIN`, `KAFKA_SASL_USERNAME=$ConnectionString`, and `KAFKA_SASL_PASSWORD=<Connection string-primary key from the Eventstream Kafka tab>`. Note that `KAFKA_BOOTSTRAP` and `KAFKA_TOPIC` come from the same tab. The existing local lines 3-4 stay as defaults.
- New `sources/tests/test_sinks.py` (pytest, same style as `test_stream.py`). Monkeypatch `kafka.KafkaProducer` with a fake that records kwargs, and monkeypatch `generator.sinks.parse_env`. Cases:
  - `test_plaintext_default_has_no_sasl_kwargs`
  - `test_sasl_settings_from_env` (asserts the four kwargs and that `$ConnectionString` is passed literally)
  - `test_unreachable_topic_raises_runtime_error_without_secret`
  - `test_delivery_errors_are_counted`
  - `test_cli_returns_3_on_delivery_failure` (`cli.main([...,'--sink','kafka','--count','2'])` with the fake)
  - Skip the module if `kafka` isn't importable (`pytest.importorskip`).

**Architecture**

```text
.env (KAFKA_BOOTSTRAP, KAFKA_TOPIC, KAFKA_SECURITY_PROTOCOL, KAFKA_SASL_*)
  └─ KafkaSink.__init__ → KafkaProducer(**security, acks=all)
       └─ partitions_for(topic)  ── fail → RuntimeError → cli exit 2   [AT-007]
  └─ write → send().add_errback → failures++
  └─ close → flush(30s) → cli: failures>0 → exit 3
```

**Acceptance Criteria**

- [ ] With no `KAFKA_SECURITY_PROTOCOL` in `.env`, `KafkaProducer` receives `security_protocol="PLAINTEXT"` and no `sasl_*` kwargs (local Kafka keeps working)
- [ ] With the Eventstream settings, `KafkaProducer` receives `security_protocol="SASL_SSL"`, `sasl_mechanism="PLAIN"`, `sasl_plain_username="$ConnectionString"`, and the password unchanged
- [ ] A bad connection string makes `generator stream --sink kafka` exit **2** before sending any event, and the message doesn't contain the password value
- [ ] Undelivered events make the command exit **3**; a clean run still exits 0
- [ ] stdout and file sinks behave exactly as before (existing tests green, `failures == 0`)
- [ ] No new dependencies beyond the existing `stream` extra (`kafka-python-ng`)
- [ ] `sources/tests/test_sinks.py` exists with the five cases above and runs without a broker
