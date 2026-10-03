"""Dimension tables: the fixed universe of the original dataset, read from ``src/dimensions/``."""
from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv

from .config import DIMENSIONS_DIR

_S, _I = pa.string(), pa.int32()

SCHEMAS: dict[str, pa.Schema] = {
    "dim_categoria": pa.schema([("Cod_Categoria", _S), ("Desc_Categoria", _S)]),
    "dim_marca": pa.schema([("Cod_Marca", _S), ("Desc_Marca", _S), ("Cod_Categoria", _S)]),
    "dim_produto": pa.schema([("Cod_Produto", _S), ("Desc_Produto", _S), ("Atr_Tamanho", _S),
                              ("Atr_Sabor", _S), ("Cod_Marca", _S)]),
    "dim_cliente": pa.schema([("Cod_Cliente", _S), ("Desc_Cliente", _S), ("Cod_Cidade", _S),
                              ("Desc_Cidade", _S), ("Cod_Estado", _S), ("Desc_Estado", _S),
                              ("Cod_Regiao", _S), ("Desc_Regiao", _S), ("Cod_Segmento", _S),
                              ("Desc_Segmento", _S)]),
    "dim_fabrica": pa.schema([("Cod_Fabrica", _S), ("Desc_Fabrica", _S)]),
    "dim_organizacional": pa.schema([("Cod_Filho", _S), ("Desc_Filho", _S), ("Cod_Pai", _S),
                                     ("Esquerda", _I), ("Direita", _I), ("Nivel", _I)]),
}


def load_static_dimensions(tables_dir: Path = DIMENSIONS_DIR) -> dict[str, pa.Table]:
    tables = {}
    for name, schema in SCHEMAS.items():
        tables[name] = pacsv.read_csv(
            tables_dir / f"{name}.csv",
            convert_options=pacsv.ConvertOptions(column_types=schema, strings_can_be_null=True, null_values=[""]),
        )
    return tables
