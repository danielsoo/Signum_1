from __future__ import annotations
import os
from typing import List, Optional

import pandas as pd
import typer
from rich import print

from .extract import extract_from_zips
from .transform import transform_all
from .load import save_parquet, load_duckdb
from .validate import write_report
from .constants import DEFAULT_WAREHOUSE_DIR, DEFAULT_REPORTS_DIR

app = typer.Typer(help="CMS Hospital ETL runner")


@app.command()
def run(
    zip_list: List[str] = typer.Argument(..., help="Paths to ZIP files"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse output dir"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports output dir"),
):
    """Run full ETL: extract -> transform -> load -> validate."""
    print("[bold]Extracting[/bold] from ZIPs...")
    extracted = extract_from_zips(zip_list)
    if not extracted:
        print("[red]No target CSVs found in provided ZIPs[/red]")
        raise typer.Exit(code=1)

    # Prepare for transform
    tuples = [(e.dataset_key, e.release, e.frame) for e in extracted]
    releases = [e.release for e in extracted]

    print("[bold]Transforming[/bold] to standard schema...")
    tr = transform_all(tuples)

    print("[bold]Loading[/bold] to Parquet and DuckDB...")
    save_paths = save_parquet(tr.metrics, tr.star, tr.metrics_catalog, warehouse_dir)
    db_path = load_duckdb(tr.metrics, tr.star, tr.metrics_catalog, warehouse_dir)

    print("[bold]Validating[/bold] and generating report...")
    report_path = write_report(tr.metrics, tr.star, releases, reports_dir)

    print("[green]Done.[/green]")
    print({"parquet": save_paths, "duckdb": db_path, "report": report_path})


@app.command()
def query(
    ccn: str = typer.Argument(..., help="Hospital CCN (6 digits)"),
    start: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)"),
    domain: Optional[str] = typer.Option(None, help="Domain filter"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
):
    import duckdb
    db_path = os.path.join(warehouse_dir, "hospital.duckdb")
    if not os.path.exists(db_path):
        print(f"[red]DuckDB not found at {db_path}. Run etl first.[/red]")
        raise typer.Exit(code=1)

    con = duckdb.connect(db_path, read_only=True)
    try:
        sql = "SELECT * FROM hospital_metrics WHERE ccn = ?"
        params = [ccn]
        if start:
            sql += " AND period_end >= ?"; params.append(start)
        if end:
            sql += " AND period_end <= ?"; params.append(end)
        if domain:
            sql += " AND domain = ?"; params.append(domain)
        sql += " ORDER BY period_end DESC LIMIT 100"
        df = con.execute(sql, params).df()
        print(df.head(20))
    finally:
        con.close()


@app.command()
def sample(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR),
    out: Optional[str] = typer.Option(None, help="Output parquet path"),
):
    from .sample_extractor import build_star_training_sample
    path = build_star_training_sample(warehouse_dir, out)
    print({"sample": path})


if __name__ == "__main__":
    app()
