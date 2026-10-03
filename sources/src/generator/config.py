"""Configuration loading, project paths and the .env reader."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parent.parent
ROOT = SRC_DIR.parent
DATA_DIR = ROOT / "data"
ENV_FILE = ROOT / ".env"
DEFAULT_CONFIG = SRC_DIR / "config" / "fruit_juice.toml"
CALIBRATION_DIR = SRC_DIR / "calibration"
DIMENSIONS_DIR = SRC_DIR / "dimensions"


def load_config(path: Path | str | None = None, **overrides: Any) -> dict[str, Any]:
    """Load the TOML config; overrides use dotted keys, e.g. ``**{"period.end": "2015-12-31"}``."""
    with open(path or DEFAULT_CONFIG, "rb") as fh:
        cfg = tomllib.load(fh)
    for dotted, value in overrides.items():
        node = cfg
        *parents, leaf = dotted.split(".")
        for part in parents:
            node = node[part]
        node[leaf] = value
    return cfg


def calibration_path(cfg: dict[str, Any]) -> Path:
    return CALIBRATION_DIR / f"{cfg['dataset']}.json"


def parse_env(path: Path = ENV_FILE) -> dict[str, str]:
    """Plain KEY=value lines; comments on their own line, optional quotes."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values
