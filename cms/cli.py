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


@app.command()
def search(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
):
    """
    Interactive hospital search with Google + NPPES + CMS integration
    
    Supports:
    - Hospital search by name, location, specialty
    - Doctor search with hospital affiliations
    - Regional/specialty filtered search
    
    Example:
        python -m cms.cli search
    """
    import sys
    import os
    from pathlib import Path
    
    # Try to import from Signum_1/cms
    project_root = Path(__file__).resolve().parents[1]
    signum1_path = project_root / "Signum_1"
    signum1_cms = signum1_path / "cms"
    
    if not signum1_cms.exists():
        print("[red]Error: Signum_1/cms directory not found.[/red]")
        print(f"[yellow]Expected: {signum1_cms}[/yellow]")
        raise typer.Exit(code=1)
    
    # Add Signum_1 to Python path so we can import cms.interactive_search
    signum1_str = str(signum1_path)
    if signum1_str not in sys.path:
        sys.path.insert(0, signum1_str)
    
    # Change to Signum_1 directory to ensure relative imports work
    original_cwd = os.getcwd()
    try:
        os.chdir(str(signum1_path))
        from cms import interactive_search
    except ImportError as e:
        print(f"[red]Error importing interactive_search: {e}[/red]")
        print(f"[yellow]Make sure Signum_1/cms/interactive_search.py exists[/yellow]")
        raise typer.Exit(code=1)
    finally:
        os.chdir(original_cwd)
    
    # Use the warehouse_dir from Signum_1 if it exists and no explicit path given
    signum1_warehouse = signum1_path / "warehouse"
    if signum1_warehouse.exists() and warehouse_dir == DEFAULT_WAREHOUSE_DIR:
        warehouse_dir = str(signum1_warehouse)
    elif not Path(warehouse_dir).exists():
        # If default doesn't exist, try Signum_1/warehouse
        if signum1_warehouse.exists():
            warehouse_dir = str(signum1_warehouse)
            print(f"[yellow]Using warehouse: {warehouse_dir}[/yellow]")
    
    interactive_search.search_interactive(warehouse_dir)


if __name__ == "__main__":
    app()
