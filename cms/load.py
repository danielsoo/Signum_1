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
            con.execute("CREATE TABLE IF NOT EXISTS hospital_metrics AS SELECT * FROM df_metrics WHERE 1=0;")
            con.execute("INSERT INTO hospital_metrics SELECT * FROM df_metrics;")
        if star is not None and not star.empty:
            con.register("df_star", star)
            con.execute("CREATE TABLE IF NOT EXISTS hospital_star AS SELECT * FROM df_star WHERE 1=0;")
            con.execute("INSERT INTO hospital_star SELECT * FROM df_star;")
        if catalog is not None and not catalog.empty:
            con.register("df_catalog", catalog)
            con.execute("CREATE TABLE IF NOT EXISTS metrics_catalog AS SELECT * FROM df_catalog WHERE 1=0;")
            con.execute("INSERT INTO metrics_catalog SELECT * FROM df_catalog;")

        # Ensure prediction/evaluation tables exist (empty schema init)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS star_predictions (
                ccn VARCHAR,
                period_end DATE,
                target_release VARCHAR,
                model_name VARCHAR,
                prediction_type VARCHAR,
                pred_star DOUBLE,
                conf_lo DOUBLE,
                conf_hi DOUBLE,
                prob_star_1 DOUBLE,
                prob_star_2 DOUBLE,
                prob_star_3 DOUBLE,
                prob_star_4 DOUBLE,
                prob_star_5 DOUBLE,
                generated_at TIMESTAMP
            );
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS star_evaluations (
                ccn VARCHAR,
                period_end DATE,
                target_release VARCHAR,
                model_name VARCHAR,
                prediction_type VARCHAR,
                pred_star DOUBLE,
                actual_star DOUBLE,
                abs_error DOUBLE,
                within_band INTEGER,
                evaluated_at TIMESTAMP
            );
            """
        )
    finally:
        con.close()
    return db_path
