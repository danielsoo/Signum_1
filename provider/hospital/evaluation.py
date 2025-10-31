"""
Model Evaluation - 방향성 기반 평가 메트릭

CMS 별점은 상대적 순위이므로 절대 정확도보다는:
- 방향 정확도 (개선/하락 예측)
- 순위 상관관계
- 분포 유사도
를 측정합니다.
"""
from __future__ import annotations
import os
from typing import Dict, Optional
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
from scipy.stats import wasserstein_distance

from .constants import DEFAULT_WAREHOUSE_DIR


class StarEvaluator:
    """
    별점 예측 모델 평가기
    
    방향성 기반 평가 메트릭을 사용하여 모델 성능을 평가합니다.
    """
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        """
        Args:
            warehouse_dir: 웨어하우스 디렉토리 경로
        """
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
    
    def evaluate_predictions(self, release: str) -> Optional[Dict]:
        """
        특정 릴리스에 대한 예측 평가
        
        Args:
            release: 평가할 릴리스 (예: "2024_01")
        
        Returns:
            {
                "n_hospitals": int,
                "direction_accuracy": float,
                "rank_correlation": float,
                "wasserstein_distance": float,
                "smoothness": float,
                "domain_rmse": float,
                ...
            }
        """
        if not os.path.exists(self.db_path):
            return None
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            # 예측과 실제 별점 가져오기
            query = """
                SELECT 
                    p.ccn,
                    p.predicted_star,
                    s.star_rating as actual_star
                FROM star_predictions p
                INNER JOIN hospital_star s 
                    ON p.ccn = s.ccn AND p.release = s.release
                WHERE p.release = ? 
                    AND p.predicted_star IS NOT NULL 
                    AND s.star_rating IS NOT NULL
            """
            df = con.execute(query, [release]).df()
            
            if df.empty:
                return None
            
            n_hospitals = len(df)
            if n_hospitals == 0:
                return None
            
            predicted = df['predicted_star'].values
            actual = df['actual_star'].values
            
            # 1. Direction Accuracy (방향 정확도)
            # 이전 별점과 비교하여 개선/하락 방향이 맞는지
            direction_acc = self._calculate_direction_accuracy(df, con, release)
            
            # 2. Rank Correlation (순위 상관관계)
            rank_corr = self._calculate_rank_correlation(predicted, actual)
            
            # 3. Wasserstein Distance (분포 유사도)
            wd = wasserstein_distance(predicted, actual)
            
            # 4. Smoothness (시계열 일관성)
            smoothness = self._calculate_smoothness(df, con, release)
            
            # 5. RMSE (절대 정확도 - 참고용)
            rmse = np.sqrt(np.mean((predicted - actual) ** 2))
            
            return {
                "release": release,
                "n_hospitals": n_hospitals,
                "direction_accuracy": float(direction_acc),
                "rank_correlation": float(rank_corr),
                "wasserstein_distance": float(wd),
                "smoothness": float(smoothness),
                "rmse": float(rmse),
                "mae": float(np.mean(np.abs(predicted - actual))),
            }
            
        finally:
            con.close()
    
    def _calculate_direction_accuracy(self, df: pd.DataFrame, con: duckdb.DuckDBPyConnection, release: str) -> float:
        """
        방향 정확도 계산
        
        이전 별점 대비 개선/하락/유지 방향이 맞는지 측정
        """
        correct = 0
        total = 0
        
        for _, row in df.iterrows():
            ccn = row['ccn']
            predicted = row['predicted_star']
            actual = row['actual_star']
            
            # 이전 별점 조회
            prev_query = """
                SELECT star_rating 
                FROM hospital_star 
                WHERE ccn = ? AND release < ? AND star_rating IS NOT NULL
                ORDER BY release DESC 
                LIMIT 1
            """
            prev_result = con.execute(prev_query, [ccn, release]).df()
            
            if prev_result.empty:
                continue
            
            prev_star = prev_result.iloc[0]['star_rating']
            
            # 방향 계산
            predicted_direction = self._get_direction(prev_star, predicted)
            actual_direction = self._get_direction(prev_star, actual)
            
            if predicted_direction == actual_direction:
                correct += 1
            total += 1
        
        return correct / total if total > 0 else 0.0
    
    def _get_direction(self, prev: float, current: float) -> str:
        """방향 계산: 'up', 'down', 'same'"""
        diff = current - prev
        if diff > 0.3:
            return 'up'
        elif diff < -0.3:
            return 'down'
        else:
            return 'same'
    
    def _calculate_rank_correlation(self, predicted: np.ndarray, actual: np.ndarray) -> float:
        """
        순위 상관관계 (Spearman)
        
        절대 값이 아니라 순위가 얼마나 맞는지 측정
        """
        if len(predicted) < 2:
            return 0.0
        
        correlation, p_value = stats.spearmanr(predicted, actual)
        return correlation if not np.isnan(correlation) else 0.0
    
    def _calculate_smoothness(self, df: pd.DataFrame, con: duckdb.DuckDBPyConnection, release: str) -> float:
        """
        시계열 일관성 점수
        
        예측이 시간에 따라 부드럽게 변하는지 측정
        """
        smoothness_scores = []
        
        for _, row in df.iterrows():
            ccn = row['ccn']
            predicted = row['predicted_star']
            
            # 이전 3개 릴리스 별점 가져오기
            history_query = """
                SELECT star_rating 
                FROM hospital_star 
                WHERE ccn = ? AND release <= ? AND star_rating IS NOT NULL
                ORDER BY release DESC 
                LIMIT 4
            """
            history = con.execute(history_query, [ccn, release]).df()['star_rating'].values
            
            if len(history) < 2:
                continue
            
            # 변화량 계산 (작을수록 부드러움)
            changes = np.abs(np.diff(history))
            
            # 예측값이 마지막 별점과의 차이
            if len(history) > 0:
                last_star = history[0]
                pred_change = abs(predicted - last_star)
                
                # 평균 변화량과 비교
                avg_change = np.mean(changes) if len(changes) > 0 else 0
                
                # 평균 변화량과 비슷하면 부드러움 (1.0에 가까울수록 좋음)
                if avg_change > 0:
                    smoothness = 1.0 / (1.0 + abs(pred_change - avg_change))
                else:
                    smoothness = 1.0 if pred_change < 0.5 else 0.5
                
                smoothness_scores.append(smoothness)
        
        return np.mean(smoothness_scores) if smoothness_scores else 0.0
    
    def save_evaluation(self, metrics: Dict):
        """
        평가 결과 저장
        
        Args:
            metrics: evaluate_predictions()의 반환값
        """
        if not metrics:
            return
        
        con = duckdb.connect(self.db_path)
        try:
            # star_evaluations 테이블 생성
            con.execute("""
                CREATE TABLE IF NOT EXISTS star_evaluations (
                    release VARCHAR PRIMARY KEY,
                    n_hospitals INTEGER,
                    direction_accuracy FLOAT,
                    rank_correlation FLOAT,
                    wasserstein_distance FLOAT,
                    smoothness FLOAT,
                    rmse FLOAT,
                    mae FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 평가 결과 삽입
            con.execute("""
                INSERT OR REPLACE INTO star_evaluations 
                (release, n_hospitals, direction_accuracy, rank_correlation, 
                 wasserstein_distance, smoothness, rmse, mae)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics['release'],
                metrics['n_hospitals'],
                metrics['direction_accuracy'],
                metrics['rank_correlation'],
                metrics['wasserstein_distance'],
                metrics['smoothness'],
                metrics['rmse'],
                metrics['mae']
            ))
            
            con.commit()
            
        finally:
            con.close()

