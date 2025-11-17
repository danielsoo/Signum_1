from __future__ import annotations
import os
from typing import Optional

import duckdb

from .constants import DEFAULT_WAREHOUSE_DIR


def query_metrics(ccn: str, start: Optional[str] = None, end: Optional[str] = None, domain: Optional[str] = None, warehouse_dir: Optional[str] = None, limit: int = 100):
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        sql = "SELECT * FROM hospital_metrics WHERE ccn = ?"
        params = [ccn]
        if start:
            sql += " AND period_end >= ?"
            params.append(start)
        if end:
            sql += " AND period_end <= ?"
            params.append(end)
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY period_end DESC LIMIT ?"
        params.append(limit)
        return con.execute(sql, params).df()
    finally:
        con.close()


def query_star(ccn: str, start: Optional[str] = None, end: Optional[str] = None, warehouse_dir: Optional[str] = None, limit: int = 100):
    wd = warehouse_dir or DEFAULT_WAREHOUSE_DIR
    db_path = os.path.join(wd, "hospital.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        sql = "SELECT * FROM hospital_star WHERE ccn = ?"
        params = [ccn]
        if start:
            sql += " AND period_end >= ?"
            params.append(start)
        if end:
            sql += " AND period_end <= ?"
            params.append(end)
        sql += " ORDER BY period_end DESC LIMIT ?"
        params.append(limit)
        return con.execute(sql, params).df()
    finally:
        con.close()
