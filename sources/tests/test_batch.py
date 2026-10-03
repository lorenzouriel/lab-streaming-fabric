"""generate: dimensions + revenue target as Parquet, deterministic per seed."""
import hashlib

import pyarrow.parquet as pq

from generator.batch import TARGET_TABLE, generate
from generator.config import load_config

DIM_ROWS = {"dim_categoria": 3, "dim_marca": 9, "dim_produto": 35, "dim_cliente": 57,
            "dim_fabrica": 3, "dim_organizacional": 19}


def _run(tmp_path, seed=42):
    cfg = load_config(**{"period.start": "2026-01-01", "period.end": "2026-02-28", "seed": seed})
    return generate(cfg, data_dir=tmp_path, log=lambda _: None), tmp_path / "parquet" / cfg["dataset"]


def _digest(root):
    h = hashlib.sha256()
    for f in sorted(root.rglob("*.parquet")):
        h.update(f.relative_to(root).as_posix().encode() + f.read_bytes())
    return h.hexdigest()


def test_writes_dimensions_and_target(tmp_path):
    counts, root = _run(tmp_path)
    assert {k: counts[k] for k in DIM_ROWS} == DIM_ROWS
    target = pq.read_table(root / TARGET_TABLE)
    assert target.num_rows == counts[TARGET_TABLE] > 0
    days = target.column("COD_DIA").to_pylist()
    assert min(days) >= "20260101" and max(days) <= "20260228"
    assert min(target.column("META_FATURAMENTO").to_pylist()) > 0


def test_same_seed_is_byte_identical(tmp_path):
    _, a = _run(tmp_path / "a")
    _, b = _run(tmp_path / "b")
    _, c = _run(tmp_path / "c", seed=7)
    assert _digest(a) == _digest(b) != _digest(c)
