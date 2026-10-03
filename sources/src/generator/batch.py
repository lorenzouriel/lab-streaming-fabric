"""``generator generate``: the reference tables the Eventhouse needs, as Parquet.

    data/parquet/<dataset>/<dim_*>/part-0.parquet                   the six dimensions
    data/parquet/<dataset>/tab_fato004/year=YYYY/part-0.parquet     daily revenue target (Activator)
"""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pyarrow.parquet as pq

from .config import DATA_DIR, calibration_path
from .dims import load_static_dimensions
from .facts import generate_year
from .model import Model, load_calibration

TARGET_TABLE = "tab_fato004"


def generate(cfg: dict[str, Any], data_dir: Path = DATA_DIR, log: Callable[[str], None] = print) -> dict[str, int]:
    start = date.fromisoformat(cfg["period"]["start"])
    end = date.fromisoformat(cfg["period"]["end"])
    calibration = load_calibration(calibration_path(cfg))
    if start < date(calibration["anchor_years"][0], 1, 1):
        raise ValueError(f"period.start must be on or after {calibration['anchor_years'][0]}-01-01")
    if end < start:
        raise ValueError("period.end is before period.start")

    root = data_dir / "parquet" / cfg["dataset"]
    if root.exists():
        shutil.rmtree(root)
    counts: dict[str, int] = {}
    for name, table in load_static_dimensions().items():
        (root / name).mkdir(parents=True)
        pq.write_table(table, root / name / "part-0.parquet", compression="zstd")
        counts[name] = table.num_rows

    model = Model(calibration, cfg, end.year)
    for year in range(start.year, end.year + 1):
        # All five facts are generated (they share one random stream), only the target is kept.
        table = generate_year(model, year, start, end)[TARGET_TABLE]
        target = root / TARGET_TABLE / f"year={year}"
        target.mkdir(parents=True)
        pq.write_table(table, target / "part-0.parquet", compression="zstd")
        counts[TARGET_TABLE] = counts.get(TARGET_TABLE, 0) + table.num_rows
        log(f"  {year}: {TARGET_TABLE}={table.num_rows:,}")
    return counts
