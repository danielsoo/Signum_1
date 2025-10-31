"""
Sequential Trainer - 순차 학습 모듈

cms/data 폴더의 ZIP 파일을 자동으로 찾아서 순차적으로 ETL → 학습 → 평가 → 리포트 생성까지
모든 과정을 자동화합니다.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

from .training_tracker import TrainingTracker, DataFileManager
from .constants import DEFAULT_WAREHOUSE_DIR, DEFAULT_REPORTS_DIR
from .extract import extract_from_zips
from .transform import transform_all
from .load import save_parquet, load_duckdb


class SequentialTrainer:
    """
    순차 학습기를 구현한 클래스.
    
    기능:
    - 자동 ZIP 파일 검색 및 정렬
    - 이미 처리된 파일 건너뛰기
    - ETL → 학습 → 평가 → 리포트 자동 실행
    """
    
    def __init__(self, warehouse_dir: str, reports_dir: Optional[str] = None):
        """
        Args:
            warehouse_dir: 웨어하우스 디렉토리 경로
            reports_dir: 리포트 디렉토리 경로
        """
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.reports_dir = reports_dir or DEFAULT_REPORTS_DIR
        
        # 프로젝트 루트 찾기 (cms/data 폴더 위치)
        project_root = Path(__file__).resolve().parents[1]
        self.data_dir = project_root / "cms" / "data"
        
        # 학습 상태 추적기
        self.tracker = TrainingTracker(self.warehouse_dir)
        
        # 디렉토리 생성
        os.makedirs(self.warehouse_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def get_status(self) -> Dict:
        """
        현재 학습 상태 및 데이터 요약 반환
        
        Returns:
            {
                "data_summary": {
                    "total_files": int,
                    "files_with_dates": int,
                    "date_range": {"earliest": str, "latest": str}
                },
                "training_summary": {
                    "total_processed_files": int,
                    "processed_releases": List[str],
                    "last_training_date": str,
                    "recent_training": List[Dict]
                }
            }
        """
        # ZIP 파일 검색
        zip_files = DataFileManager.find_zip_files(str(self.data_dir))
        processed_files = self.tracker.get_processed_files()
        
        # 데이터 요약
        releases_with_dates = [
            f["release"] for f in zip_files 
            if f["release"] != "unknown"
        ]
        date_range = DataFileManager.get_date_range(zip_files)
        
        data_summary = {
            "total_files": len(zip_files),
            "files_with_dates": len(releases_with_dates),
            "date_range": date_range
        }
        
        # 학습 요약
        processed_releases = self.tracker.get_processed_releases()
        status = self.tracker._load_status()
        
        training_summary = {
            "total_processed_files": len(processed_files),
            "processed_releases": processed_releases,
            "last_training_date": status.get("last_training_date"),
            "recent_training": self.tracker.get_recent_training(limit=10)
        }
        
        return {
            "data_summary": data_summary,
            "training_summary": training_summary
        }
    
    def train_sequential(self) -> Dict:
        """
        순차 학습 실행
        
        Returns:
            {
                "status": "success" | "no_data" | "already_processed",
                "processed_files": List[Dict],
                "errors": List[Dict],
                "reports_generated": List[str]
            }
        """
        # 입력 항목(최상위 ZIP 또는 디렉터리) 찾기
        zip_files = DataFileManager.find_input_items(str(self.data_dir))
        
        if not zip_files:
            return {
                "status": "no_data",
                "processed_files": [],
                "errors": [],
                "reports_generated": []
            }
        
        # 처리되지 않은 파일/폴더 필터링
        unprocessed_files = [
            f for f in zip_files 
            if not self.tracker.is_file_processed(f["path"])
        ]
        
        # 처리된 파일들도 가져오기 (AI 학습 확인용)
        processed_files_info = {
            f["release"]: f for f in zip_files
            if self.tracker.is_file_processed(f["path"])
        }
        
        # 모든 릴리스 수집
        all_releases = {f["release"]: f for f in zip_files}
        
        # ETL이 완료되었지만 AI 학습이 필요한 릴리스 확인
        if not unprocessed_files and all_releases:
            releases_needing_ai = self.tracker.get_incomplete_ai_trainings(list(all_releases.keys()))
            if not releases_needing_ai:
                # 모든 것이 완료됨
                return {
                    "status": "already_processed",
                    "processed_files": [],
                    "errors": [],
                    "reports_generated": []
                }
        
        # 단계별 처리: ETL → AI 학습 → 평가
        processed = []
        errors = []
        reports_generated = []
        
        # 진행 상황 표시 시작
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            transient=False
        ) as progress:
            total_files = len(unprocessed_files)
            
            # ========== PHASE 1: 모든 파일의 ETL 먼저 완료 ==========
            if unprocessed_files:
                rprint("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
                rprint("[bold cyan]📦 PHASE 1: EXTRACT, TRANSFORM & LOAD (ETL) - ZIPs & Folders[/bold cyan]")
                rprint("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
                
                phase1_task = progress.add_task(
                    f"[bold cyan]ETL: Processing {total_files} files...[/bold cyan]",
                    total=total_files
                )
                
                etl_results = {}
                for idx, file_info in enumerate(unprocessed_files):
                    file_path = file_info["path"]
                    release = file_info["release"]
                    filename = file_info["filename"]
                    
                    file_task = progress.add_task(
                        f"[yellow]  └─ {filename}[/yellow]",
                        total=100
                    )
                    
                    try:
                        # ETL 실행
                        progress.update(
                            file_task,
                            description=f"[cyan]  └─ Extracting & Loading {filename}...[/cyan]",
                            advance=10
                        )
                        
                        result = self._process_single_file(file_path, release)
                        
                        if result["success"]:
                            progress.update(
                                file_task,
                                advance=90,
                                description=f"[green]  └─ ✅ {filename} - {result['records']['total']:,} records loaded[/green]"
                            )
                            
                            # ETL 결과 저장
                            etl_results[release] = {
                                "file_path": file_path,
                                "release": release,
                                "filename": filename,
                                "records": result["records"]
                            }
                            
                            # ETL 완료만 표시 (아직 AI 학습 안 함)
                            self.tracker.mark_file_processed(file_path, release, result["records"])
                        else:
                            errors.append({
                                "file": file_path,
                                "error": result["error"]
                            })
                            progress.update(
                                file_task,
                                description=f"[red]  └─ ❌ {filename} - {result['error']}[/red]"
                            )
                        
                        progress.remove_task(file_task)
                        progress.update(phase1_task, advance=1)
                        
                    except Exception as e:
                        error_msg = str(e)
                        errors.append({
                            "file": file_path,
                            "error": error_msg
                        })
                        progress.update(
                            file_task,
                            description=f"[red]  └─ ❌ {filename} - {error_msg}[/red]"
                        )
                        progress.remove_task(file_task)
                        progress.update(phase1_task, advance=1)
                
                # ETL이 완료된 것들 etl_results에 추가
                for release, file_info in processed_files_info.items():
                    if release not in etl_results:
                        etl_results[release] = {
                            "file_path": file_info["path"],
                            "release": release,
                            "filename": file_info["filename"],
                            "records": {}  # ETL은 이미 완료됨
                        }
            else:
                # ETL이 모두 완료된 경우 - 이미 처리된 파일 정보 사용
                rprint("\n[green]✅ All ETL files already processed![/green]")
                rprint("[cyan]Proceeding to AI training phase...[/cyan]\n")
                
                etl_results = {}
                for release, file_info in processed_files_info.items():
                    etl_results[release] = {
                        "file_path": file_info["path"],
                        "release": release,
                        "filename": file_info["filename"],
                        "records": {}  # ETL은 이미 완료됨
                    }
            
            if not etl_results:
                rprint("\n[red]❌ No files available for processing.[/red]")
                return {
                    "status": "success",
                    "processed_files": [],
                    "errors": errors,
                    "reports_generated": []
                }
            
            # AI 비활성화 플래그 (환경변수): DISABLE_AI=1 이면 AI 단계 스킵
            ai_disabled = os.environ.get("DISABLE_AI", "") in ("1", "true", "True")

            # ========== PHASE 2: 모든 파일의 AI 학습 ==========
            if ai_disabled:
                rprint("\n[yellow]⚠️ AI is disabled by environment (DISABLE_AI=1). Skipping AI training & prediction.[/yellow]")
                releases = sorted(etl_results.keys())
                # PHASE 3도 함께 스킵하도록 플래그 유지
            else:
                rprint("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
                rprint("[bold cyan]🧠 PHASE 2: AI MODEL TRAINING & PREDICTION[/bold cyan]")
                rprint("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
                
                releases = sorted(etl_results.keys())
            
            if not ai_disabled:
                # 이미 완료된 학습 확인
                incomplete_releases = self.tracker.get_incomplete_ai_trainings(releases)
                completed_count = len(releases) - len(incomplete_releases)
                
                if incomplete_releases:
                    rprint(f"[yellow]📋 {completed_count}/{len(releases)} releases already completed, continuing from where we left off...[/yellow]")
                    rprint(f"[cyan]🔄 Processing {len(incomplete_releases)} remaining releases...[/cyan]\n")
                else:
                    rprint(f"[green]✅ All {len(releases)} releases already completed! Skipping AI training.[/green]\n")
                
                phase2_task = progress.add_task(
                    f"[bold cyan]AI Training: {len(releases)} releases ({len(incomplete_releases)} remaining)...[/bold cyan]",
                    total=len(releases)
                )
                
                # 이미 완료된 것들 먼저 표시
                for release in releases:
                    if release not in incomplete_releases:
                        file_info = etl_results[release]
                        # 이전 결과 불러오기
                        if self.tracker.is_ai_training_complete(release):
                            status = self.tracker._load_status()
                            ai_info = status.get("ai_training_complete", {}).get(release, {})
                            file_info["ai_predictions"] = ai_info.get("predictions", 0)
                            file_info["ai_success"] = True
                            file_info["evaluation"] = ai_info.get("metrics", {})
                        progress.update(phase2_task, advance=1)
                
                # 완료되지 않은 것들 처리
                for idx, release in enumerate(incomplete_releases):
                    file_info = etl_results[release]
                    filename = file_info["filename"]
                    
                    release_task = progress.add_task(
                        f"[yellow]  └─ {release} ({filename})[/yellow]",
                        total=100
                    )
                    
                    try:
                        # AI 학습 진행
                        progress.update(
                            release_task,
                            description=f"[cyan]  └─ 🧠 Training models for {release}...[/cyan]",
                            advance=10
                        )
                        
                        ai_result = self._train_and_predict_for_release(release, progress, release_task)
                        
                        if ai_result.get("success"):
                            predictions = ai_result.get("predictions", 0)
                            
                            # 완료 표시 (아직 평가는 안 함)
                            self.tracker.mark_ai_training_complete(release, predictions)
                            
                            progress.update(
                                release_task,
                                advance=85,
                                description=f"[green]  └─ ✅ {release} - {predictions:,} predictions generated[/green]"
                            )
                            
                            file_info["ai_predictions"] = predictions
                            file_info["ai_success"] = True
                        else:
                            error_msg = ai_result.get("error", "Unknown error")
                            progress.update(
                                release_task,
                                advance=85,
                                description=f"[yellow]  └─ ⚠️ {release} - Skipped ({error_msg})[/yellow]"
                            )
                            
                            file_info["ai_predictions"] = 0
                            file_info["ai_success"] = False
                        
                        progress.remove_task(release_task)
                        progress.update(phase2_task, advance=1)
                        
                    except Exception as e:
                        error_msg = str(e)
                        progress.update(
                            release_task,
                            description=f"[red]  └─ ❌ {release} - Error: {error_msg}[/red]"
                        )
                        progress.remove_task(release_task)
                        file_info["ai_predictions"] = 0
                        file_info["ai_success"] = False
                        progress.update(phase2_task, advance=1)
            
            # ========== PHASE 3: 모든 파일의 평가 ==========
            if ai_disabled:
                rprint("[yellow]⚠️ AI is disabled. Skipping evaluation phase.[/yellow]")
            else:
                rprint("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
                rprint("[bold cyan]📊 PHASE 3: MODEL EVALUATION[/bold cyan]")
                rprint("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
            
            # 평가가 필요한 릴리스 확인 (예측이 완료된 것만)
            if ai_disabled:
                releases_to_evaluate = []
            else:
                releases_to_evaluate = [r for r in releases if etl_results[r].get("ai_success", False)]
            
            if not releases_to_evaluate:
                rprint("[yellow]⚠️ No releases with successful predictions to evaluate[/yellow]\n")
            else:
                phase3_task = progress.add_task(
                    f"[bold cyan]Evaluation: {len(releases_to_evaluate)} releases...[/bold cyan]",
                    total=len(releases_to_evaluate)
                )
                
                for idx, release in enumerate(releases_to_evaluate):
                    file_info = etl_results[release]
                    filename = file_info["filename"]
                    
                    # 이미 평가가 완료되었는지 확인
                    if self.tracker.is_ai_training_complete(release):
                        status = self.tracker._load_status()
                        ai_info = status.get("ai_training_complete", {}).get(release, {})
                        if ai_info.get("metrics"):
                            # 이미 평가 완료
                            file_info["evaluation"] = ai_info.get("metrics", {})
                            progress.update(phase3_task, advance=1)
                            continue
                    
                    eval_task = progress.add_task(
                        f"[yellow]  └─ {release}[/yellow]",
                        total=100
                    )
                    
                    try:
                        progress.update(
                            eval_task,
                            description=f"[cyan]  └─ 📊 Evaluating predictions for {release}...[/cyan]",
                            advance=20
                        )
                        
                        eval_result = self._evaluate_for_release(release, progress, eval_task)
                        
                        if eval_result.get("success"):
                            metrics = eval_result.get("metrics", {})
                            accuracy = metrics.get('direction_accuracy', 0)
                            
                            # 평가 결과 저장
                            self.tracker.mark_ai_training_complete(
                                release,
                                file_info.get("ai_predictions", 0),
                                metrics
                            )
                            
                            progress.update(
                                eval_task,
                                advance=75,
                                description=f"[green]  └─ ✅ {release} - Accuracy: {accuracy:.1%}[/green]"
                            )
                            
                            file_info["evaluation"] = metrics
                        else:
                            error_msg = eval_result.get("error", "No evaluation data")
                            progress.update(
                                eval_task,
                                advance=75,
                                description=f"[yellow]  └─ ⚠️ {release} - {error_msg}[/yellow]"
                            )
                        
                        progress.remove_task(eval_task)
                        progress.update(phase3_task, advance=1)
                        
                    except Exception as e:
                        error_msg = str(e)
                        progress.update(
                            eval_task,
                            description=f"[red]  └─ ❌ {release} - Error: {error_msg}[/red]"
                        )
                        progress.remove_task(eval_task)
                        progress.update(phase3_task, advance=1)
            
            # 최종 결과 정리
            processed = list(etl_results.values())
        
        return {
            "status": "success",
            "processed_files": processed,
            "errors": errors,
            "reports_generated": reports_generated
        }
    
    def _process_single_file(self, zip_path: str, release: str) -> Dict:
        """
        단일 ZIP 파일 처리 (ETL만 실행)
        
        Args:
            zip_path: ZIP 파일 경로
            release: 릴리스 문자열
            
        Returns:
            {
                "success": bool,
                "records": {"total": int, "metrics": int, "star": int},
                "error": Optional[str]
            }
        """
        try:
            # 1. Extract
            extracted = extract_from_zips([zip_path])
            if not extracted:
                return {
                    "success": False,
                    "records": {},
                    "error": "No target CSVs found in ZIP"
                }
            
            # 2. Transform
            tuples = [(e.dataset_key, e.release, e.frame) for e in extracted]
            tr = transform_all(tuples)
            
            # 레코드 수 집계
            metrics_count = len(tr.metrics) if not tr.metrics.empty else 0
            star_count = len(tr.star) if not tr.star.empty else 0
            
            records = {
                "total": metrics_count + star_count,
                "metrics": metrics_count,
                "star": star_count
            }
            
            # 3. Load
            save_parquet(tr.metrics, tr.star, tr.metrics_catalog, self.warehouse_dir)
            load_duckdb(tr.metrics, tr.star, tr.metrics_catalog, self.warehouse_dir)
            
            return {
                "success": True,
                "records": records,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "records": {},
                "error": str(e)
            }
    
    def _train_and_predict_for_release(self, release: str, progress: Optional[Progress] = None, task_id: Optional[int] = None) -> Dict:
        """
        특정 릴리스에 대해 AI 모델 학습 및 예측
        
        Args:
            release: 릴리스 문자열
            progress: Rich Progress 객체 (진행 상황 표시용)
            task_id: 진행 상황 업데이트할 task ID
        
        Returns:
            {
                "success": bool,
                "predictions": int,
                "error": Optional[str]
            }
        """
        try:
            # 모델 임포트 시도
            try:
                from .model import StarPredictor
            except ImportError:
                return {
                    "success": False,
                    "predictions": 0,
                    "error": "Model module not available"
                }
            
            predictor = StarPredictor(self.warehouse_dir)
            
            # 학습할 수 있는 릴리스 확인 (최소 2개 필요)
            import duckdb
            db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
            if not os.path.exists(db_path):
                return {"success": False, "predictions": 0, "error": "Database not found"}
            
            con = duckdb.connect(db_path, read_only=True)
            try:
                # 사용 가능한 릴리스 확인
                releases_query = "SELECT DISTINCT release FROM hospital_star WHERE star_rating IS NOT NULL ORDER BY release"
                available_releases = con.execute(releases_query).df()['release'].tolist()
                
                if len(available_releases) < 2:
                    return {"success": False, "predictions": 0, "error": "Insufficient data (need at least 2 releases)"}
                
                # 현재 릴리스 이전 데이터로 학습
                train_releases = [r for r in available_releases if r < release]
                # 슬라이딩 윈도우: 최근 N개 릴리스만 사용하여 안정화
                MAX_TRAIN_RELEASES = 10
                if len(train_releases) > MAX_TRAIN_RELEASES:
                    train_releases = train_releases[-MAX_TRAIN_RELEASES:]
                
                if len(train_releases) == 0:
                    # 현재 릴리스가 첫 번째면, 모든 이전 릴리스 사용
                    train_releases = available_releases[:-1] if len(available_releases) > 1 else []
                
                if len(train_releases) == 0:
                    return {"success": False, "predictions": 0, "error": "No training data available"}
                
                if progress and task_id is not None:
                    progress.update(
                        task_id,
                        advance=5,
                        description=f"[cyan]  └─ 🧠 Training on {len(train_releases)} releases: {', '.join(train_releases[:3])}...[/cyan]"
                    )
                
                # 모델 학습 (진행 상황 출력 포함)
                predictor.train(train_releases, progress_callback=progress, task_id=task_id if progress else None)
                
                if progress and task_id is not None:
                    progress.update(
                        task_id,
                        advance=10,
                        description="[cyan]  └─ 🔮 Generating predictions...[/cyan]"
                    )
                
                # 예측 생성
                predictions = predictor.predict_for_release(release)
                
                if not predictions.empty:
                    predictor.save_predictions(predictions)
                    num_predictions = len(predictions)
                else:
                    num_predictions = 0
                
                return {
                    "success": True,
                    "predictions": num_predictions,
                    "error": None
                }
                
            finally:
                con.close()
                
        except Exception as e:
            return {
                "success": False,
                "predictions": 0,
                "error": str(e)
            }
    
    def _evaluate_for_release(self, release: str, progress: Optional[Progress] = None, task_id: Optional[int] = None) -> Dict:
        """
        특정 릴리스에 대한 모델 평가
        
        Args:
            release: 릴리스 문자열
            progress: Rich Progress 객체
            task_id: 진행 상황 업데이트할 task ID
        
        Returns:
            {
                "success": bool,
                "metrics": Dict,
                "error": Optional[str]
            }
        """
        try:
            try:
                from .evaluation import StarEvaluator
            except ImportError:
                return {
                    "success": False,
                    "metrics": {},
                    "error": "Evaluation module not available"
                }
            
            evaluator = StarEvaluator(self.warehouse_dir)
            
            # 예측이 있는지 확인
            import duckdb
            db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
            if not os.path.exists(db_path):
                return {"success": False, "metrics": {}, "error": "Database not found"}
            
            con = duckdb.connect(db_path, read_only=True)
            try:
                # 예측 존재 확인
                pred_check = con.execute(
                    "SELECT COUNT(*) as cnt FROM star_predictions WHERE release = ?",
                    [release]
                ).df()
                
                if pred_check.empty or pred_check.iloc[0]['cnt'] == 0:
                    return {"success": False, "metrics": {}, "error": "No predictions found"}
                
                # 평가 실행
                metrics = evaluator.evaluate_predictions(release)
                
                if metrics:
                    evaluator.save_evaluation(metrics)
                    return {
                        "success": True,
                        "metrics": metrics,
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "metrics": {},
                        "error": "No evaluation data generated"
                    }
                    
            finally:
                con.close()
                
        except Exception as e:
            return {
                "success": False,
                "metrics": {},
                "error": str(e)
            }

