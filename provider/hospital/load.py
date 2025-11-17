from __future__ import annotations
import os
from typing import Optional

import duckdb
import pandas as pd

from .constants import DEFAULT_WAREHOUSE_DIR


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_parquet(metrics: pd.DataFrame, star: pd.DataFrame, catalog: pd.DataFrame, warehouse_dir: Optional[str] = None) -> dict:
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    _ensure_dir(wd)

    paths = {}
    if metrics is not None and not metrics.empty:
        p = os.path.join(wd, "hospital_metrics.parquet")
        metrics.to_parquet(p, index=False)
        paths["metrics"] = p
    if star is not None and not star.empty:
        p = os.path.join(wd, "hospital_star.parquet")
        star.to_parquet(p, index=False)
        paths["star"] = p
    if catalog is not None and not catalog.empty:
        p = os.path.join(wd, "metrics_catalog.parquet")
        catalog.to_parquet(p, index=False)
        paths["catalog"] = p
    return paths


def load_duckdb(metrics: pd.DataFrame, star: pd.DataFrame, catalog: pd.DataFrame, warehouse_dir: Optional[str] = None) -> str:
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    _ensure_dir(wd)
    db_path = os.path.join(wd, "hospital.duckdb")

    con = duckdb.connect(db_path)
    try:
        if metrics is not None and not metrics.empty:
            con.register("df_metrics", metrics)
            con.execute("DROP TABLE IF EXISTS hospital_metrics;")
            con.execute("CREATE TABLE hospital_metrics AS SELECT * FROM df_metrics;")
        if star is not None and not star.empty:
            con.register("df_star", star)
            con.execute("DROP TABLE IF EXISTS hospital_star;")
            con.execute("CREATE TABLE hospital_star AS SELECT * FROM df_star;")
        if catalog is not None and not catalog.empty:
            con.register("df_catalog", catalog)
            con.execute("DROP TABLE IF EXISTS metrics_catalog;")
            con.execute("CREATE TABLE metrics_catalog AS SELECT * FROM df_catalog;")
    finally:
        con.close()
    return db_path
