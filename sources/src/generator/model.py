"""Yearly state of the generative model: the calibration plus the dynamics that extend it.

For the fitted years (2013-2015) the yearly tables (list prices, unit costs, tax rates, fixed-cost
rates, volume level) are read straight from the calibration. For later years they evolve from
the previous year with a per-year seeded random step, so the state of year Y never depends on
how far the run extends past Y.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

# spawn_key tags, so streams for different purposes never collide
_TAG_YEAR = 1
_TAG_MONTH = 2


def rng_for(seed: int, *spawn_key: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy=seed, spawn_key=spawn_key)))


class Model:
    def __init__(self, calibration: dict[str, Any], cfg: dict[str, Any], last_year: int):
        self.cfg = cfg
        self.seed = int(cfg["seed"])
        cal = calibration
        self.clients: list[str] = cal["clients"]
        self.products: list[str] = cal["products"]
        self.factories: list[str] = cal["factories"]
        self.client_org: list[str] = cal["client_org"]
        self.product_litres = np.array(cal["product_litres"])
        keys = cal["keys"]
        self.key_client = np.array(keys["client"])
        self.key_product = np.array(keys["product"])
        self.key_factory = np.array(keys["factory"])
        self.key_logq = np.array(keys["log_qty"])
        self.n_keys = len(self.key_client)
        self.season = np.array(cal["season"])
        self.presence = np.array(cal["presence_by_month"])
        self.qty_sigma = float(cal["qty_sigma"])
        self.price_sigma = float(cal["price_sigma"])
        self.client_price_effect = np.array(cal["client_price_effect"])
        self.freight_per_litre = np.array(cal["freight_per_litre"])          # [client, factory]
        self.target_quantiles = {k: np.array(v) for k, v in cal["target_ratio_quantiles"].items()}

        self.anchor_years: list[int] = cal["anchor_years"]
        first, last_anchor = self.anchor_years[0], self.anchor_years[-1]
        self.first_year = first

        # yearly tables, indexed by calendar year
        self.year_level: dict[int, float] = {}
        self.base_price: dict[int, np.ndarray] = {}     # [product]
        self.unit_cost: dict[int, np.ndarray] = {}      # [factory, product]  (integer valued)
        self.tax_rate: dict[int, np.ndarray] = {}       # [client, product]
        self.fixed_rate: dict[int, np.ndarray] = {}     # [factory]
        for y in self.anchor_years:
            self.year_level[y] = float(cal["year_level"][str(y)])
            self.base_price[y] = np.array(cal["base_price"][str(y)])
            self.unit_cost[y] = np.array(cal["unit_cost"][str(y)])
            self.tax_rate[y] = np.array(cal["tax_rate"][str(y)])
            self.fixed_rate[y] = np.array(cal["fixed_cost_rate"][str(y)])

        # Fitted volume growth of the last anchor year seeds the decay after the fitted period.
        growth = float(np.exp(self.year_level[last_anchor] - self.year_level[last_anchor - 1]) - 1)
        latent_cost = self.unit_cost[last_anchor].copy()
        for y in range(last_anchor + 1, last_year + 1):
            growth, latent_cost = self._extend(y, growth, latent_cost)

    def _extend(self, y: int, prev_growth: float, latent_cost: np.ndarray) -> tuple[float, np.ndarray]:
        vol, prc, fix = self.cfg["volume"], self.cfg["prices"], self.cfg["fixed_cost"]
        rng = rng_for(self.seed, _TAG_YEAR, y)

        growth = vol["terminal_growth"] + (prev_growth - vol["terminal_growth"]) * vol["growth_decay"]
        shock = rng.normal(0.0, vol["shock_sigma"])
        self.year_level[y] = self.year_level[y - 1] + np.log1p(growth) + shock

        price = self.base_price[y - 1] * np.exp(rng.normal(np.log1p(prc["inflation"]), prc["price_sigma"],
                                                           self.base_price[y - 1].shape))
        self.base_price[y] = price

        latent_cost = latent_cost * np.exp(rng.normal(np.log1p(prc["cost_inflation"]), prc["cost_sigma"],
                                                      latent_cost.shape))
        cap = np.maximum(1.0, np.floor(prc["cost_cap_ratio"] * price))[None, :]
        self.unit_cost[y] = np.minimum(np.maximum(1.0, np.rint(latent_cost)), cap)

        tax_step = 1.0 + prc["tax_drift"] + rng.normal(0.0, prc["tax_sigma"])
        self.tax_rate[y] = np.minimum(self.tax_rate[y - 1] * tax_step, prc["tax_cap"])

        self.fixed_rate[y] = rng.choice(np.array(fix["rate_choices"]), size=self.fixed_rate[y - 1].shape)
        return growth, latent_cost

    def freight_rate(self, year: int) -> np.ndarray:
        last = self.anchor_years[-1]
        drift = (1.0 + self.cfg["prices"]["freight_inflation"]) ** max(0, year - last)
        return self.freight_per_litre * drift


def load_calibration(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
