"""EventGenerator / pacing / stdout+file sinks (no broker needed)."""
import json
import time
from datetime import date, datetime, timezone

import pytest

from generator.config import calibration_path, load_config
from generator.model import Model, load_calibration
from generator.stream import EventGenerator, iter_events
from generator.sinks import FileSink, StdoutSink


@pytest.fixture(scope="session")
def generator():
    cfg = load_config()
    model = Model(load_calibration(calibration_path(cfg)), cfg, last_year=2026)
    return EventGenerator(model, date(2026, 5, 1))


def test_event_is_pure_function_of_seq(generator):
    t = datetime(2026, 5, 1, tzinfo=timezone.utc)
    a, b = generator.event(123, t), generator.event(123, t)
    assert a == b
    assert generator.event(123, t) != generator.event(124, t)


def test_event_content_ignores_the_timestamp_argument(generator):
    e1 = generator.event(5, datetime(2026, 1, 1, tzinfo=timezone.utc))
    e2 = generator.event(5, datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc))
    assert e1.cod_cliente == e2.cod_cliente and e1.faturamento == e2.faturamento
    assert e1.event_time != e2.event_time


def test_values_are_sane(generator):
    for seq in range(200):
        e = generator.event(seq)
        assert e.faturamento > 0 and e.imposto >= 0 and e.custo_variavel >= 0
        assert e.quantidade_vendida > 0 and e.unidades >= 1
        assert e.cod_cliente and e.cod_produto and e.cod_fabrica and e.cod_organizacional
        assert e.cod_dia == e.event_time.strftime("%Y%m%d")


def test_covers_the_key_universe_given_enough_events(generator):
    seen = {(generator.event(seq).cod_cliente, generator.event(seq).cod_produto, generator.event(seq).cod_fabrica)
            for seq in range(3000)}
    assert len(seen) > 500   # not collapsed onto a handful of keys


def test_iter_events_respects_count_and_is_deterministic(generator):
    fast = list(iter_events(generator, rate=500, count=10, start_time=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    slow = list(iter_events(generator, rate=500, count=10, start_time=datetime(2026, 1, 1, tzinfo=timezone.utc), jitter=False))
    assert len(fast) == len(slow) == 10
    assert [e.seq for e in fast] == list(range(10))
    for a, b in zip(fast, slow):
        assert a.cod_cliente == b.cod_cliente and a.faturamento == b.faturamento   # rate/jitter never change content


def test_iter_events_start_seq_resumes_exactly(generator):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    whole = list(iter_events(generator, rate=1000, count=6, start_time=start))
    resumed = list(iter_events(generator, rate=1000, count=3, start_seq=3, start_time=start))
    assert [(e.cod_cliente, e.faturamento) for e in resumed] == [(e.cod_cliente, e.faturamento) for e in whole[3:]]


def test_iter_events_duration_stops_on_time(generator):
    t0 = time.monotonic()
    events = list(iter_events(generator, rate=20, duration=0.3))
    assert time.monotonic() - t0 < 1.0
    assert len(events) >= 1


def test_file_sink_appends_valid_ndjson(tmp_path, generator):
    path = tmp_path / "events.jsonl"
    sink = FileSink(path)
    for seq in range(3):
        sink.write(generator.event(seq))
    sink.close()
    FileSink(path).close()   # reopening in append mode must not truncate
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    rows = [json.loads(line) for line in lines]
    assert [r["seq"] for r in rows] == [0, 1, 2]
    assert all(r["event_time"].endswith("Z") for r in rows)


def test_stdout_sink_writes_one_json_line(generator, capsys):
    StdoutSink().write(generator.event(0))
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    json.loads(out)   # must parse


def test_event_content_depends_on_as_of_not_wall_clock():
    cfg = load_config()
    model = Model(load_calibration(calibration_path(cfg)), cfg, last_year=2026)
    may, may_again = EventGenerator(model, date(2026, 5, 1)), EventGenerator(model, date(2026, 5, 20))
    assert may.event(3).to_dict() == may_again.event(3, may.event(3).event_time).to_dict()
    assert EventGenerator(model, date(2026, 12, 1)).event(3).quantidade_vendida != may.event(3).quantidade_vendida


def test_unknown_sink_raises():
    from generator.sinks import make_sink
    with pytest.raises(ValueError):
        make_sink("carrier-pigeon", "fruit_juice")
