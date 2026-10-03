"""``generator stream``: individual synthetic sales events (one order each) in (near) real time.

Drawn from the same fitted model as the batch tables, so events joined to the dimensions see
consistent clients, products, prices and tax rates. Reproducible: for a given seed and as-of date,
event N always has the same content, whatever the rate or where a previous run stopped.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Iterator

import numpy as np

from .model import Model, rng_for

_TAG_STREAM = 3


@dataclass(frozen=True)
class StreamEvent:
    seq: int
    event_id: str
    event_time: datetime          # UTC
    cod_dia: str
    cod_cliente: str
    cod_produto: str
    cod_fabrica: str
    cod_organizacional: str
    faturamento: float
    imposto: float
    custo_variavel: float
    unidades: float
    quantidade_vendida: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "seq": self.seq,
            "event_time": self.event_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "cod_dia": self.cod_dia, "cod_cliente": self.cod_cliente, "cod_produto": self.cod_produto,
            "cod_fabrica": self.cod_fabrica, "cod_organizacional": self.cod_organizacional,
            "faturamento": self.faturamento, "imposto": self.imposto, "custo_variavel": self.custo_variavel,
            "unidades": self.unidades, "quantidade_vendida": self.quantidade_vendida,
        }


# A day's modelled volume for a key is split into roughly this many individual orders; a single
# event's quantity is sampled as one Dirichlet-ish share of that day's total (see `share_concentration`
# in facts.py for the same idea applied to a month). Keeps order sizes realistic instead of handing out
# a whole day's quantity in one event.
_ASSUMED_ORDERS_PER_DAY = 6.0


class EventGenerator:
    """Deterministic: `event(n)` depends only on the seed and `n`, never on call order or timing."""

    def __init__(self, model: Model, as_of: date):
        self.model = model
        as_of_year = as_of.year
        if as_of_year not in model.year_level:
            raise ValueError(f"model was not extended to {as_of_year}; pass last_year={as_of_year} when building it")
        weight = np.exp(model.key_logq)
        self._key_p = weight / weight.sum()
        price = model.base_price[as_of_year][model.key_product] * np.exp(model.client_price_effect[model.key_client])
        self._price = price
        self._tax_rate = model.tax_rate[as_of_year][model.key_client, model.key_product]
        self._unit_cost = model.unit_cost[as_of_year][model.key_factory, model.key_product]
        self._daily_qty_mean = np.exp(model.key_logq + model.season[as_of.month - 1])

    def event(self, seq: int, event_time: datetime | None = None) -> StreamEvent:
        rng = rng_for(self.model.seed, _TAG_STREAM, seq)
        key = rng.choice(self.model.n_keys, p=self._key_p)
        client, product, factory = (int(self.model.key_client[key]), int(self.model.key_product[key]),
                                    int(self.model.key_factory[key]))

        order_share = rng.gamma(1.0 / _ASSUMED_ORDERS_PER_DAY) if _ASSUMED_ORDERS_PER_DAY > 1 else 1.0
        qty = max(0.5, round(float(self._daily_qty_mean[key] / _ASSUMED_ORDERS_PER_DAY * (0.4 + order_share)), 2))
        price = float(self._price[key]) * float(np.exp(rng.normal(0.0, self.model.price_sigma)))
        revenue = round(qty * price, 2)
        tax = round(revenue * float(self._tax_rate[key]), 2)
        cost = round(qty * float(self._unit_cost[key]), 2)
        units = max(1.0, round(qty / float(self.model.product_litres[product])))

        event_time = event_time or datetime.now(timezone.utc)
        return StreamEvent(
            seq=seq, event_id=str(uuid.uuid5(uuid.NAMESPACE_OID, f"{self.model.seed}:{seq}")),
            event_time=event_time, cod_dia=event_time.strftime("%Y%m%d"),
            cod_cliente=self.model.clients[client], cod_produto=self.model.products[product],
            cod_fabrica=self.model.factories[factory], cod_organizacional=self.model.client_org[client],
            faturamento=revenue, imposto=tax, custo_variavel=cost, unidades=units, quantidade_vendida=qty,
        )


def clock(start: datetime, speed: float) -> Callable[[], datetime]:
    """Real time at `start` if speed == 1.0; otherwise simulated time advancing `speed`x faster than the wall clock."""
    origin_wall = time.monotonic()
    return lambda: start + timedelta(seconds=(time.monotonic() - origin_wall) * speed)


def iter_events(generator: EventGenerator, rate: float, *, start_seq: int = 0, count: int | None = None,
                duration: float | None = None, start_time: datetime | None = None, speed: float = 1.0,
                jitter: bool = True, rng_seed: int | None = None,
                sleep: Callable[[float], None] = time.sleep) -> Iterator[StreamEvent]:
    """Yields events at `rate` events/second (a Poisson process by default; `jitter=False` for a fixed interval)."""
    now = clock(start_time or datetime.now(timezone.utc), speed)
    pace_rng = np.random.default_rng(rng_seed)   # pacing only: does not affect event content, so it need not be seeded
    t0 = time.monotonic()
    seq = start_seq
    emitted = 0
    while count is None or emitted < count:
        if duration is not None and time.monotonic() - t0 >= duration:
            return
        yield generator.event(seq, now())
        seq += 1
        emitted += 1
        mean_interval = 1.0 / (rate * speed)
        sleep(pace_rng.exponential(mean_interval) if jitter else mean_interval)
