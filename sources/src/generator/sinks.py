"""Where `generator stream` events go: stdout, a JSON Lines file, or Kafka (the Eventstream endpoint)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Protocol

from .config import parse_env
from .stream import StreamEvent


class Sink(Protocol):
    def write(self, event: StreamEvent) -> None: ...
    def close(self) -> None: ...


class StdoutSink:
    """One JSON object per line, flushed immediately so a consumer piping this sees it right away."""

    def write(self, event: StreamEvent) -> None:
        sys.stdout.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def close(self) -> None:
        pass


class FileSink:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8", newline="\n")

    def write(self, event: StreamEvent) -> None:
        self._fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class KafkaSink:
    def __init__(self, dataset: str):
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise RuntimeError("the kafka sink needs: uv sync --extra stream") from e
        env = parse_env()
        bootstrap = env.get("KAFKA_BOOTSTRAP", "127.0.0.1:9094")
        self._topic = env.get("KAFKA_TOPIC", f"{dataset}.sales")
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap.split(","),
            key_serializer=lambda k: k.encode("utf-8"),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )

    def write(self, event: StreamEvent) -> None:
        d = event.to_dict()
        key = f"{d['cod_cliente']}|{d['cod_produto']}|{d['cod_fabrica']}"   # same key -> same partition -> in order
        self._producer.send(self._topic, key=key, value=d)

    def close(self) -> None:
        self._producer.flush(timeout=10)
        self._producer.close()


SINKS = ("stdout", "file", "kafka")


def make_sink(name: str, dataset: str, file_path: Path | None = None) -> Sink:
    if name == "stdout":
        return StdoutSink()
    if name == "file":
        return FileSink(file_path)
    if name == "kafka":
        return KafkaSink(dataset)
    raise ValueError(f"unknown sink {name!r}; choices: {', '.join(SINKS)}")
