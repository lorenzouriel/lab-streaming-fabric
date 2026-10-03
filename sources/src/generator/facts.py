"""Daily fact construction (TAB_FATO001-005).

One month at a time, vectorised with numpy. Key invariants of the original dataset hold by
construction (they are what Rateio.sql relies on):

* Fato_002 has exactly one row per Fato_001 row, on (day, client, product, factory)
* Fato_003 has one row per (factory, day) with sales
* Fato_004 has one row per distinct (day, client, product, organisation) of Fato_001
* Fato_005 has one row per distinct (day, product, factory) of Fato_001
"""
from __future__ import annotations

import calendar
from datetime import date

import numpy as np
import pyarrow as pa

from .model import _TAG_MONTH, Model, rng_for

FACT_SCHEMAS: dict[str, pa.Schema] = {
    "tab_fato001": pa.schema([
        ("DATA_FATO", pa.timestamp("ms")), ("COD_DIA", pa.string()), ("COD_CLIENTE", pa.string()),
        ("COD_FABRICA", pa.string()), ("COD_PRODUTO", pa.string()), ("COD_ORGANIZACIONAL", pa.string()),
        ("FATURAMENTO", pa.float64()), ("IMPOSTO", pa.float64()), ("CUSTO_VARIAVEL", pa.float64()),
        ("UNIDADE_VENDIDA", pa.float64()), ("QUANTIDADE_VENDIDA", pa.float64())]),
    "tab_fato002": pa.schema([
        ("DATA_FATO", pa.timestamp("ms")), ("COD_DIA", pa.string()), ("COD_CLIENTE", pa.string()),
        ("COD_FABRICA", pa.string()), ("COD_PRODUTO", pa.string()), ("FRETE", pa.float64())]),
    "tab_fato003": pa.schema([
        ("DATA_FATO", pa.timestamp("ms")), ("COD_DIA", pa.string()), ("COD_FABRICA", pa.string()),
        ("CUSTO_FIXO", pa.float64())]),
    "tab_fato004": pa.schema([
        ("DATA_FATO", pa.timestamp("ms")), ("COD_DIA", pa.string()), ("COD_CLIENTE", pa.string()),
        ("COD_PRODUTO", pa.string()), ("COD_ORGANIZACIONAL", pa.string()),
        ("META_FATURAMENTO", pa.float64())]),
    "tab_fato005": pa.schema([
        ("DATA_FATO", pa.timestamp("ms")), ("COD_DIA", pa.string()), ("COD_FABRICA", pa.string()),
        ("COD_PRODUTO", pa.string()), ("META_CUSTO", pa.float64())]),
}

_MIN_QTY = 1.0  # litres; keeps rows from degenerating when a month is split over many days


def _sample_ratio(rng: np.random.Generator, quantiles: np.ndarray, size: int) -> np.ndarray:
    return np.interp(rng.random(size), np.linspace(0.0, 1.0, len(quantiles)), quantiles)


def _month_tables(model: Model, year: int, month: int, start: date, end: date) -> dict[str, dict[str, np.ndarray]]:
    cfg_v, cfg_p = model.cfg["volume"], model.cfg["prices"]
    rng = rng_for(model.seed, _TAG_MONTH, year, month)
    n_days = calendar.monthrange(year, month)[1]
    dates = [date(year, month, d) for d in range(1, n_days + 1)]

    weekday = np.array([d.weekday() for d in dates])
    weight = np.where(weekday < 5, 1.0, np.where(weekday == 5, cfg_v["saturday_weight"], cfg_v["sunday_weight"]))
    in_range = np.array([start <= d <= end for d in dates])
    weight = np.where(in_range, weight, 0.0)
    if not in_range.any():
        return {}

    # --- which keys trade this month, and how much ---------------------------------------
    present = np.flatnonzero(rng.random(model.n_keys) < model.presence[month - 1])
    n_present = len(present)
    monthly_qty = np.exp(model.key_logq[present] + model.season[month - 1] + model.year_level[year]
                         + rng.normal(0.0, model.qty_sigma, n_present))
    month_price_noise = np.exp(rng.normal(0.0, model.price_sigma, n_present))

    # --- purchase days (weighted sampling without replacement, Gumbel-top-k style) ---------
    n_orders = 1 + rng.poisson(max(cfg_v["orders_per_month"] - 1.0, 0.0), n_present)
    n_orders = np.minimum(n_orders, int(in_range.sum()))
    u = rng.random((n_present, n_days))
    with np.errstate(divide="ignore"):
        score = np.where(weight > 0, np.log(u) / np.where(weight > 0, weight, 1.0), -np.inf)
    order = np.argsort(-score, axis=1, kind="stable")
    rank = np.empty_like(order)
    np.put_along_axis(rank, order, np.broadcast_to(np.arange(n_days), order.shape), axis=1)
    row_key, row_day = np.nonzero(rank < n_orders[:, None])       # row-major: grouped by key

    # --- split the month's litres over its purchase days -----------------------------------
    gamma = rng.gamma(cfg_v["share_concentration"], size=len(row_key))
    share = gamma / np.bincount(row_key, weights=gamma, minlength=n_present)[row_key]
    qty = np.maximum(np.round(monthly_qty[row_key] * share, 2), _MIN_QTY)

    key = present[row_key]                                          # global key index per row
    client, product, factory = model.key_client[key], model.key_product[key], model.key_factory[key]

    price = (model.base_price[year][product] * np.exp(model.client_price_effect[client])
             * month_price_noise[row_key] * np.exp(rng.normal(0.0, cfg_p["daily_price_noise"], len(key))))
    revenue = np.round(qty * price, 2)
    tax = np.round(revenue * model.tax_rate[year][client, product], 2)
    var_cost = np.round(qty * model.unit_cost[year][factory, product], 2)
    units = np.maximum(1.0, np.rint(qty / model.product_litres[product]))

    # order rows by (day, client, product, factory) like a table extract
    o = np.lexsort((factory, product, client, row_day))
    row_day, key, client, product, factory = row_day[o], key[o], client[o], product[o], factory[o]
    qty, revenue, tax, var_cost, units = qty[o], revenue[o], tax[o], var_cost[o], units[o]

    freight = np.round(qty * model.freight_rate(year)[client, factory], 2)

    n_c, n_p, n_f = len(model.clients), len(model.products), len(model.factories)
    day_str = np.array([d.strftime("%Y%m%d") for d in dates])
    day_ts = np.array([np.datetime64(d.isoformat(), "ms") for d in dates])
    clients_arr, products_arr = np.array(model.clients), np.array(model.products)
    factories_arr, orgs_arr = np.array(model.factories), np.array(model.client_org)

    def head(idx_day: np.ndarray) -> dict[str, np.ndarray]:
        return {"DATA_FATO": day_ts[idx_day], "COD_DIA": day_str[idx_day]}

    f1 = {**head(row_day), "COD_CLIENTE": clients_arr[client], "COD_FABRICA": factories_arr[factory],
          "COD_PRODUTO": products_arr[product], "COD_ORGANIZACIONAL": orgs_arr[client],
          "FATURAMENTO": revenue, "IMPOSTO": tax, "CUSTO_VARIAVEL": var_cost,
          "UNIDADE_VENDIDA": units, "QUANTIDADE_VENDIDA": qty}
    f2 = {**head(row_day), "COD_CLIENTE": clients_arr[client], "COD_FABRICA": factories_arr[factory],
          "COD_PRODUTO": products_arr[product], "FRETE": freight}

    # Fato_003: fixed cost = yearly rate per litre x litres shipped by the factory that day
    code3 = row_day * n_f + factory
    u3, inv3 = np.unique(code3, return_inverse=True)
    litres3 = np.bincount(inv3, weights=qty)
    d3, f3_fac = u3 // n_f, u3 % n_f
    f3 = {**head(d3), "COD_FABRICA": factories_arr[f3_fac],
          "CUSTO_FIXO": np.round(litres3 * model.fixed_rate[year][f3_fac], 2)}

    # Fato_004: revenue target per (day, client, product); the organisation follows the client
    code4 = (row_day * n_c + client) * n_p + product
    u4, inv4 = np.unique(code4, return_inverse=True)
    revenue4 = np.bincount(inv4, weights=revenue)
    d4, c4, p4 = u4 // (n_c * n_p), (u4 // n_p) % n_c, u4 % n_p
    ratio4 = _sample_ratio(rng, model.target_quantiles["tab_fato004"], len(u4))
    f4 = {**head(d4), "COD_CLIENTE": clients_arr[c4], "COD_PRODUTO": products_arr[p4],
          "COD_ORGANIZACIONAL": orgs_arr[c4], "META_FATURAMENTO": np.maximum(1.0, np.rint(revenue4 * ratio4))}

    # Fato_005: cost target per (day, product, factory)
    code5 = (row_day * n_p + product) * n_f + factory
    u5, inv5 = np.unique(code5, return_inverse=True)
    cost5 = np.bincount(inv5, weights=var_cost)
    d5, p5, f5_fac = u5 // (n_p * n_f), (u5 // n_f) % n_p, u5 % n_f
    ratio5 = _sample_ratio(rng, model.target_quantiles["tab_fato005"], len(u5))
    f5 = {**head(d5), "COD_FABRICA": factories_arr[f5_fac], "COD_PRODUTO": products_arr[p5],
          "META_CUSTO": np.maximum(1.0, np.rint(cost5 * ratio5))}

    return {"tab_fato001": f1, "tab_fato002": f2, "tab_fato003": f3, "tab_fato004": f4, "tab_fato005": f5}


def generate_year(model: Model, year: int, start: date, end: date) -> dict[str, pa.Table]:
    """All five fact tables for one calendar year, clipped to [start, end]."""
    parts: dict[str, list[dict[str, np.ndarray]]] = {name: [] for name in FACT_SCHEMAS}
    for month in range(1, 13):
        if date(year, month, calendar.monthrange(year, month)[1]) < start or date(year, month, 1) > end:
            continue
        for name, cols in _month_tables(model, year, month, start, end).items():
            parts[name].append(cols)
    tables = {}
    for name, schema in FACT_SCHEMAS.items():
        if not parts[name]:
            continue
        merged = {f.name: np.concatenate([p[f.name] for p in parts[name]]) for f in schema}
        tables[name] = pa.table({k: pa.array(v, type=schema.field(k).type) for k, v in merged.items()},
                                schema=schema)
    return tables
