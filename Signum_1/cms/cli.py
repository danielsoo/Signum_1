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
# Lazy imports for optional modules - only import when specific commands are used
# from .model import StarPredictor
# from .evaluation import StarEvaluator
# from .insights import InsightsAnalyzer
# from .reports import ReportGenerator
# from .sequential_trainer import SequentialTrainer
# from .training_tracker import TrainingTracker, DataFileManager
from .constants import DEFAULT_WAREHOUSE_DIR, DEFAULT_REPORTS_DIR

app = typer.Typer(help="CMS Hospital ETL runner")


# Import interactive search
def get_interactive_search():
    """Import interactive search module"""
    from . import interactive_search
    return interactive_search


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

    print("[bold]Generating[/bold] ETL HTML report...")
    try:
        from .reports import ReportGenerator
        report_generator = ReportGenerator(warehouse_dir, reports_dir)
        html_report_path = report_generator.generate_etl_report(tr.metrics, tr.star, releases)
    except ImportError:
        print("[yellow]⚠️  Reports module not available, skipping HTML report generation[/yellow]")
        html_report_path = None

    print("[green]Done.[/green]")
    print({"parquet": save_paths, "duckdb": db_path, "report": report_path, "html_report": html_report_path})


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
def predict(
    for_release: Optional[str] = typer.Option(None, help="Release to predict for (YYYY_MM)"),
    generate_report: bool = typer.Option(False, help="Generate HTML report"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports dir"),
):
    """Generate star rating predictions for hospitals without official ratings."""
    try:
        from .model import StarPredictor
    except ImportError:
        print("[red]❌ Model module not available. Please install required dependencies.[/red]")
        raise typer.Exit(code=1)
    
    predictor = StarPredictor(warehouse_dir)
    
    if for_release is None:
        # Auto-detect latest release
        import duckdb
        db_path = os.path.join(warehouse_dir, "hospital.duckdb")
        con = duckdb.connect(db_path, read_only=True)
        try:
            result = con.execute("SELECT MAX(release) AS latest_release FROM hospital_star").df()
            latest = None if result.empty else result.iloc[0]["latest_release"]
            if latest is None or pd.isna(latest):
                print("[red]No releases found in database. Run ETL first.[/red]")
                raise typer.Exit(code=1)
            for_release = str(latest)
        finally:
            con.close()

    if for_release is None:
        print("[red]Internal error: release not resolved[/red]")
        raise typer.Exit(code=1)
    
    print(f"[bold]Generating predictions for release {for_release}[/bold]")
    
    # Generate predictions
    predictions = predictor.predict_for_release(for_release)
    
    if predictions.empty:
        print("[yellow]No hospitals need predictions (all have official ratings)[/yellow]")
    else:
        print(f"[green]Generated {len(predictions)} predictions[/green]")
        
        # Save predictions
        predictor.save_predictions(predictions)
        
        # Generate report if requested
        if generate_report:
            try:
                from .reports import ReportGenerator
                print("[bold]Generating prediction report...[/bold]")
                report_generator = ReportGenerator(warehouse_dir, reports_dir)
                report_path = report_generator.generate_prediction_report(for_release)
                print(f"[green]Report saved: {report_path}[/green]")
            except ImportError:
                print("[yellow]⚠️  Reports module not available, skipping report generation[/yellow]")


@app.command()
def evaluate(
    release: str = typer.Argument(..., help="Release to evaluate (YYYY_MM)"),
    generate_report: bool = typer.Option(False, help="Generate HTML report"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports dir"),
):
    """Evaluate model predictions using direction-based metrics."""
    try:
        from .evaluation import StarEvaluator
    except ImportError:
        print("[red]❌ Evaluation module not available. Please install required dependencies.[/red]")
        raise typer.Exit(code=1)
    
    evaluator = StarEvaluator(warehouse_dir)
    
    print(f"[bold]Evaluating predictions for release {release}[/bold]")
    
    # Run evaluation
    metrics = evaluator.evaluate_predictions(release)
    
    if not metrics:
        print("[red]No evaluation data found. Run predictions first.[/red]")
        raise typer.Exit(code=1)
    
    print(f"[green]Evaluation completed for {metrics['n_hospitals']} hospitals[/green]")
    print(f"Direction accuracy: {metrics['direction_accuracy']:.3f}")
    print(f"Rank correlation: {metrics['rank_correlation']:.3f}")
    print(f"Wasserstein distance: {metrics['wasserstein_distance']:.3f}")
    
    # Save evaluation
    evaluator.save_evaluation(metrics)
    
    # Generate report if requested
    if generate_report:
        try:
            from .reports import ReportGenerator
            print("[bold]Generating evaluation report...[/bold]")
            report_generator = ReportGenerator(warehouse_dir, reports_dir)
            report_path = report_generator.generate_evaluation_report(release)
            print(f"[green]Report saved: {report_path}[/green]")
        except ImportError:
            print("[yellow]⚠️  Reports module not available, skipping report generation[/yellow]")


@app.command()
def insights(
    release: Optional[str] = typer.Option(None, help="Release to analyze (YYYY_MM)"),
    generate_report: bool = typer.Option(False, help="Generate HTML report"),
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports dir"),
):
    """Generate hospital insights including growth trends and narratives."""
    # insights.py exists but might need other dependencies
    analyzer = InsightsAnalyzer(warehouse_dir)
    
    if release is None:
        # Auto-detect latest release
        import duckdb
        db_path = os.path.join(warehouse_dir, "hospital.duckdb")
        con = duckdb.connect(db_path, read_only=True)
        try:
            result = con.execute("SELECT MAX(release) AS latest_release FROM hospital_star").df()
            latest = None if result.empty else result.iloc[0]["latest_release"]
            if latest is None or pd.isna(latest):
                print("[red]No releases found in database. Run ETL first.[/red]")
                raise typer.Exit(code=1)
            release = str(latest)
        finally:
            con.close()
    
    if release is None:
        print("[red]Internal error: release not resolved[/red]")
        raise typer.Exit(code=1)
    target_release: str = release
    print(f"[bold]Analyzing insights for release {target_release}[/bold]")
    
    # Analyze insights
    insights_df = analyzer.analyze_all_hospitals(target_release)
    
    if insights_df.empty:
        print("[red]No insights data found for this release.[/red]")
        raise typer.Exit(code=1)
    
    print(f"[green]Analyzed {len(insights_df)} hospitals[/green]")
    
    # Count trends
    improving = len(insights_df[insights_df['trend_direction'] == 'Improving'])
    stable = len(insights_df[insights_df['trend_direction'] == 'Stable'])
    declining = len(insights_df[insights_df['trend_direction'] == 'Declining'])
    
    print(f"Trends: {improving} improving, {stable} stable, {declining} declining")
    
    # Save insights
    analyzer.save_insights(insights_df)
    
    # Generate report if requested
    if generate_report:
        try:
            from .reports import ReportGenerator
            print("[bold]Generating insights report...[/bold]")
            report_generator = ReportGenerator(warehouse_dir, reports_dir)
            report_path = report_generator.generate_insights_report(target_release)
            print(f"[green]Report saved: {report_path}[/green]")
        except ImportError:
            print("[yellow]⚠️  Reports module not available, skipping report generation[/yellow]")


@app.command()
def dashboard(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse dir"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports dir"),
):
    """Generate index dashboard with links to all reports."""
    try:
        from .reports import ReportGenerator
        print("[bold]Generating dashboard...[/bold]")
        report_generator = ReportGenerator(warehouse_dir, reports_dir)
        dashboard_path = report_generator.generate_index_dashboard()
        print(f"[green]Dashboard saved: {dashboard_path}[/green]")
    except ImportError:
        print("[red]❌ Reports module not available. Please install required dependencies.[/red]")
        raise typer.Exit(code=1)


@app.command()
def learn(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse directory"),
    reports_dir: str = typer.Option(DEFAULT_REPORTS_DIR, help="Reports directory"),
    force: bool = typer.Option(False, help="Force retrain all data (ignore previous training)"),
):
    """
    🚀 COMPLETE AUTOMATION: Learn from cms/data folder automatically
    
    This command does EVERYTHING:
    1. Finds ZIP files in cms/data folder
    2. Skips already processed files
    3. Processes new files in chronological order
    4. Trains AI models sequentially
    5. Generates predictions and evaluations
    6. Creates insights and narratives
    7. Generates all HTML reports
    8. Packages everything for delivery
    
    Just put ZIP files in cms/data/ and run this command!
    """
    print("🚀 CMS Hospital Analytics - COMPLETE AUTOMATION")
    print("=" * 60)
    
    try:
        from .sequential_trainer import SequentialTrainer
        from .training_tracker import TrainingTracker
    except ImportError:
        print("[red]❌ Training modules not available. Please install required dependencies.[/red]")
        raise typer.Exit(code=1)
    
    # 학습 상태 초기화 (강제 재학습)
    if force:
        print("⚠️ Force mode: Resetting all training status")
        tracker = TrainingTracker(warehouse_dir)
        tracker.reset_training_status()
    
    # 순차 학습기 초기화
    trainer = SequentialTrainer(warehouse_dir, reports_dir)
    
    # 현재 상태 확인
    status = trainer.get_status()
    print(f"📁 Data folder: cms/data")
    print(f"📊 Warehouse: {warehouse_dir}")
    print(f"📄 Reports: {reports_dir}")
    print()
    
    data_summary = status["data_summary"]
    training_summary = status["training_summary"]
    
    print(f"📦 Found {data_summary['total_files']} ZIP files")
    print(f"✅ Already processed: {training_summary['total_processed_files']} files")
    print(f"📅 Processed releases: {len(training_summary['processed_releases'])}")
    
    if data_summary["date_range"]["earliest"] and data_summary["date_range"]["latest"]:
        print(f"📅 Date range: {data_summary['date_range']['earliest']} to {data_summary['date_range']['latest']}")
    print()
    
    # 학습 실행
    try:
        print("🎯 Starting sequential training...")
        results = trainer.train_sequential()
        
        if results["status"] == "no_data":
            print("❌ No ZIP files found in cms/data folder")
            print("📋 Please add ZIP files to cms/data/ and try again")
            raise typer.Exit(code=1)
        
        elif results["status"] == "already_processed":
            print("✅ All files already processed!")
            print("💡 Use --force to retrain all data")
            
            # 기존 결과 리포트 생성
            print("📊 Generating reports from existing data...")
            _generate_final_reports(trainer, warehouse_dir, reports_dir)
            
        elif results["status"] == "success":
            print("🎉 Training completed successfully!")
            print()
            
            # 결과 요약
            print("📊 Training Results:")
            print(f"  ✅ Processed: {len(results['processed_files'])} files")
            print(f"  ❌ Errors: {len(results['errors'])} files")
            print(f"  📄 Reports: {len(results['reports_generated'])} generated")
            
            if results["processed_files"]:
                print()
                print("📋 Processed Files:")
                for file_info in results["processed_files"]:
                    # filename 우선순위: file -> file_path -> filename 키
                    file_field = file_info.get("file") or file_info.get("file_path") or file_info.get("filename") or "unknown"
                    filename = os.path.basename(file_field) if isinstance(file_field, str) else str(file_field)
                    # 레코드 안전 접근
                    recs = file_info.get("records", {}) or {}
                    records_total = recs.get("total") if isinstance(recs, dict) else None
                    records_text = f"{records_total} records" if records_total is not None else "records processed"
                    print(f"  ✅ {filename} ({records_text})")
            
            if results["errors"]:
                print()
                print("❌ Errors:")
                for error_info in results["errors"]:
                    filename = os.path.basename(error_info["file"])
                    print(f"  ❌ {filename}: {error_info['error']}")
            
            # 최종 리포트 생성
            try:
                from .reports import ReportGenerator
                print()
                print("📊 Generating final reports...")
                _generate_final_reports(trainer, warehouse_dir, reports_dir)
            except ImportError:
                print("[yellow]⚠️  Reports module not available, skipping report generation[/yellow]")
        
        # 최종 패키징
        print()
        print("📦 Packaging results...")
        package_path = _package_all_results(warehouse_dir, reports_dir)
        
        print()
        print("🎉 COMPLETE AUTOMATION FINISHED!")
        print("=" * 60)
        print(f"📦 Results package: {package_path}")
        print(f"📊 Dashboard: {reports_dir}/index.html")
        print()
        print("🚀 Ready for delivery!")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command()
def status(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR, help="Warehouse directory"),
):
    """Check current training status and data summary."""
    try:
        from .sequential_trainer import SequentialTrainer
    except ImportError:
        print("[red]❌ SequentialTrainer module not available. Please install required dependencies.[/red]")
        raise typer.Exit(code=1)
    
    trainer = SequentialTrainer(warehouse_dir)
    status = trainer.get_status()
    
    print("📊 CMS Hospital Analytics Status")
    print("=" * 40)
    
    data_summary = status["data_summary"]
    training_summary = status["training_summary"]
    
    print(f"📁 Data folder: cms/data")
    print(f"📦 Total ZIP files: {data_summary['total_files']}")
    print(f"📅 Files with dates: {data_summary['files_with_dates']}")
    
    if data_summary["date_range"]["earliest"]:
        print(f"📅 Date range: {data_summary['date_range']['earliest']} to {data_summary['date_range']['latest']}")
    
    print()
    print(f"✅ Processed files: {training_summary['total_processed_files']}")
    print(f"📅 Processed releases: {len(training_summary['processed_releases'])}")
    
    if training_summary["processed_releases"]:
        print(f"📅 Releases: {', '.join(training_summary['processed_releases'])}")
    
    if training_summary["last_training_date"]:
        print(f"🕒 Last training: {training_summary['last_training_date']}")
    
    print()
    print("📋 Recent training history:")
    for entry in training_summary["recent_training"]:
        filename = os.path.basename(entry["file_path"])
        print(f"  ✅ {filename} ({entry['release']}) - {entry['processed_at']}")


@app.command()
def sample(
    warehouse_dir: str = typer.Option(DEFAULT_WAREHOUSE_DIR),
    out: Optional[str] = typer.Option(None, help="Output parquet path"),
):
    from .sample_extractor import build_star_training_sample
    path = build_star_training_sample(warehouse_dir, out)
    print({"sample": path})


def _generate_final_reports(trainer: SequentialTrainer, warehouse_dir: str, reports_dir: str):
    """최종 리포트 생성"""
    try:
        from .reports import ReportGenerator
    except ImportError:
        print("⚠️ Reports module not available, skipping report generation")
        return
    
    try:
        # 최신 릴리스 찾기
        processed_releases = trainer.tracker.get_processed_releases()
        if not processed_releases:
            print("⚠️ No processed releases found")
            return
        
        latest_release = processed_releases[-1]
        earliest_release = processed_releases[0]
        
        # 리포트 생성기 초기화
        report_generator = ReportGenerator(warehouse_dir, reports_dir)
        
        # 모든 리포트 생성
        print("  📄 Generating ETL report...")
        # DuckDB에서 최소 프레임 로드 (샘플 500행 정도면 충분)
        import duckdb
        db_path = os.path.join(warehouse_dir, "hospital.duckdb")
        if not os.path.exists(db_path):
            print("⚠️ DuckDB not found; skipping ETL report")
        else:
            con = duckdb.connect(db_path, read_only=True)
            try:
                metrics = con.execute(
                    """
                    SELECT *
                    FROM hospital_metrics
                    WHERE release IN (?, ?)
                    LIMIT 500
                    """,
                    [earliest_release, latest_release],
                ).df()
                star = con.execute(
                    """
                    SELECT *
                    FROM hospital_star
                    WHERE release IN (?, ?)
                    """,
                    [earliest_release, latest_release],
                ).df()
            finally:
                con.close()
            etl_report = report_generator.generate_etl_report(metrics, star, processed_releases)
        
        print("  📄 Generating prediction report...")
        # Use the latest release for predictions instead of next release
        pred_report = report_generator.generate_prediction_report(latest_release)
        
        print("  📄 Generating evaluation report...")
        eval_report = report_generator.generate_evaluation_report(latest_release)
        
        print("  📄 Generating insights report...")
        insights_report = report_generator.generate_insights_report(latest_release)
        
        print("  📄 Generating dashboard...")
        dashboard = report_generator.generate_index_dashboard()
        
        print(f"✅ Generated 5 reports")
        
    except Exception as e:
        print(f"⚠️ Report generation failed: {e}")


def _package_all_results(warehouse_dir: str, reports_dir: str) -> str:
    """모든 결과를 패키지로 압축"""
    import zipfile
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"cms_analysis_{timestamp}.zip"
    package_path = os.path.join(os.path.dirname(warehouse_dir), package_name)
    
    try:
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 웨어하우스 파일들 추가
            if os.path.exists(warehouse_dir):
                for root, dirs, files in os.walk(warehouse_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(warehouse_dir))
                        zipf.write(file_path, arcname)
            
            # 리포트 파일들 추가
            if os.path.exists(reports_dir):
                for root, dirs, files in os.walk(reports_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(reports_dir))
                        zipf.write(file_path, arcname)
        
        return package_path
        
    except Exception as e:
        print(f"⚠️ Packaging failed: {e}")
        return ""


def _get_next_release(current_release: str) -> str:
    """다음 릴리스 계산"""
    year, month = current_release.split('_')
    year = int(year)
    month = int(month)
    
    month += 1
    if month > 12:
        month = 1
        year += 1
    
    return f"{year:04d}_{month:02d}"


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
    from .interactive_search import search_interactive
    search_interactive(warehouse_dir)


if __name__ == "__main__":
    app()
