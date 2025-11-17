"""
AI Prediction Models - Hybrid Ensemble

Markov Transition Model + Domain Regression Model을 결합한 Hybrid Ensemble 방식으로
병원 별점을 예측합니다.
"""
from __future__ import annotations
import os
import pickle
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np
import pandas as pd
import duckdb
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from .constants import DEFAULT_WAREHOUSE_DIR
from .query_tool import query_metrics


class MarkovTransitionModel:
    """
    Markov Transition Model - 별점 변화 패턴 학습
    
    과거 별점 변화 패턴을 학습하여 다음 별점을 예측합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.transition_matrix = None  # [from_star][to_star] = count
        self.star_history = {}  # {ccn: [star_ratings]}
        
    def train(self, star_data: pd.DataFrame):
        """
        별점 데이터로 전환 행렬 학습
        
        Args:
            star_data: ccn, star_rating, release 컬럼을 가진 DataFrame
        """
        # 별점 범위: 1~5
        self.transition_matrix = defaultdict(lambda: defaultdict(int))
        self.star_history = {}
        
        # CCN별 별점 히스토리 구성
        for ccn in star_data['ccn'].unique():
            ccn_data = star_data[star_data['ccn'] == ccn].sort_values('release')
            stars = ccn_data['star_rating'].dropna().tolist()
            if len(stars) >= 2:
                self.star_history[ccn] = stars
                
                # 전환 패턴 학습
                for i in range(len(stars) - 1):
                    from_star = int(stars[i])
                    to_star = int(stars[i + 1])
                    if 1 <= from_star <= 5 and 1 <= to_star <= 5:
                        self.transition_matrix[from_star][to_star] += 1
    
    def predict_next(self, current_star: Optional[float], ccn: Optional[str] = None) -> Tuple[float, float]:
        """
        다음 별점 예측
        
        Args:
            current_star: 현재 별점 (없으면 None)
            ccn: CCN (히스토리 기반 예측용)
        
        Returns:
            (predicted_star, confidence) - 예측 별점과 신뢰도 (0-1)
        """
        if self.transition_matrix is None or len(self.transition_matrix) == 0:
            return 3.0, 0.0  # 기본값, 신뢰도 없음
        
        # 현재 별점이 없으면 CCN 히스토리에서 최신 값 사용
        if current_star is None and ccn and ccn in self.star_history:
            history = self.star_history[ccn]
            if history:
                current_star = history[-1]
        
        if current_star is None:
            return 3.0, 0.0
        
        from_star = int(round(current_star))
        if from_star < 1 or from_star > 5:
            return 3.0, 0.0
        
        # 전환 확률 계산
        transitions = self.transition_matrix[from_star]
        total = sum(transitions.values())
        
        if total == 0:
            return float(from_star), 0.0  # 변화 없음으로 예측
        
        # 가중 평균으로 예측 (가장 빈번한 전환을 예측)
        weighted_sum = sum(star * count for star, count in transitions.items())
        predicted = weighted_sum / total
        
        # 신뢰도: 데이터가 많을수록 높음 (최대 1.0)
        confidence = min(1.0, total / 100.0)  # 100개 이상이면 최대 신뢰도
        
        return predicted, confidence
    
    def get_probability_distribution(self, current_star: Optional[float], ccn: Optional[str] = None) -> Dict[int, float]:
        """
        각 별점(1-5)에 대한 확률 분포 반환
        
        Returns:
            {1: 0.1, 2: 0.2, 3: 0.4, 4: 0.2, 5: 0.1} 형태
        """
        if current_star is None and ccn and ccn in self.star_history:
            history = self.star_history[ccn]
            if history:
                current_star = history[-1]
        
        if current_star is None or self.transition_matrix is None:
            return {i: 0.2 for i in range(1, 6)}  # 균등 분포
        
        from_star = int(round(current_star))
        if from_star < 1 or from_star > 5:
            return {i: 0.2 for i in range(1, 6)}
        
        transitions = self.transition_matrix[from_star]
        total = sum(transitions.values())
        
        if total == 0:
            # 변화 없음 - 현재 별점에 높은 확률 부여
            dist = {i: 0.05 for i in range(1, 6)}
            dist[from_star] = 0.8
            return dist
        
        # 확률 분포 계산
        dist = {}
        for star in range(1, 6):
            count = transitions.get(star, 0)
            dist[star] = count / total
        
        return dist


class DomainRegressionModel:
    """
    Domain Regression Model - 도메인 메트릭에서 별점 직접 예측
    
    Mortality, Readmission, Safety 등 도메인 성과 데이터로부터 별점을 예측합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.model = RandomForestRegressor(
            n_estimators=10,   # 점진 학습: 처음은 작게 시작
            max_depth=8,       # 메모리 절약
            random_state=42,
            n_jobs=1,          # CPU 부하 감소
            warm_start=True    # 점진적으로 트리를 추가
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        
    def prepare_features(self, metrics_data: pd.DataFrame) -> pd.DataFrame:
        """
        도메인 메트릭을 특징 벡터로 변환
        
        Args:
            metrics_data: hospital_metrics 테이블 데이터
        
        Returns:
            특징 벡터 DataFrame (ccn별로 집계)
        """
        # 도메인별 평균 점수 계산
        domain_features = {}
        
        domains = ['Mortality', 'Readmission', 'Safety', 'PatientExperience', 'Timely']
        
        for ccn in metrics_data['ccn'].unique():
            ccn_metrics = metrics_data[metrics_data['ccn'] == ccn]
            features = []
            
            for domain in domains:
                domain_data = ccn_metrics[ccn_metrics['domain'] == domain]
                if not domain_data.empty:
                    # 도메인별 평균 점수 (값이 있으면 사용)
                    values = domain_data['value'].dropna()
                    if len(values) > 0:
                        features.append(values.mean())
                    else:
                        features.append(0.0)
                else:
                    features.append(0.0)
            
            domain_features[ccn] = features
        
        feature_df = pd.DataFrame.from_dict(domain_features, orient='index', columns=domains)
        return feature_df
    
    def train(self, metrics_data: pd.DataFrame, star_data: pd.DataFrame, progress_callback=None, task_id: Optional[int] = None, max_estimators: int = 80, step: int = 10, time_budget_sec: int = 180):
        """
        도메인 메트릭과 별점 데이터로 모델 학습
        
        Args:
            metrics_data: 도메인 메트릭 데이터
            star_data: 별점 데이터 (ccn, star_rating 컬럼 필요)
            progress_callback: 진행 상황 업데이트용 Rich Progress (선택)
            task_id: 업데이트할 Task ID (선택)
            max_estimators: 최대로 구성할 트리 개수
            step: 한 번에 추가할 트리 개수
            time_budget_sec: 학습 시간 예산(초)
        """
        import time
        # 특징 준비
        feature_df = self.prepare_features(metrics_data)
        
        # 별점과 매칭
        # star_data에서 최신 별점만 사용
        latest_stars = star_data.groupby('ccn').first()['star_rating']
        
        # 공통 CCN만 사용
        common_ccns = set(feature_df.index) & set(latest_stars.index)
        
        if len(common_ccns) == 0:
            self.is_trained = False
            return
        
        X = feature_df.loc[list(common_ccns)].values
        y = latest_stars.loc[list(common_ccns)].values
        
        # 결측치 제거
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[mask]
        y = y[mask]
        
        if len(X) == 0:
            self.is_trained = False
            return
        
        # 정규화
        X_scaled = self.scaler.fit_transform(X)
        
        # 점진 학습: 트리를 step씩 늘려가며 시간 예산과 함께 학습
        built = 0
        start_ts = time.time()
        # warm_start=True 이므로 n_estimators를 증가시키며 동일 모델에 적층
        while built < max_estimators:
            # 시간 예산 초과 시 중단 (부분 모델 사용)
            if time.time() - start_ts > time_budget_sec:
                if progress_callback and task_id is not None:
                    progress_callback.update(task_id, description="[yellow]  └─ ⏱️ Time budget reached. Using partial model[/yellow]", advance=1)
                break
            # 트리 개수 증가
            self.model.n_estimators += step
            # 학습
            self.model.fit(X_scaled, y)
            built += step
            # 진행 표시
            if progress_callback and task_id is not None:
                pct = min(100, int(100 * built / max_estimators))
                progress_callback.update(task_id, description=f"[cyan]  └─ 🌲 Building trees... ({min(built, max_estimators)}/{max_estimators})[/cyan]", advance=1)
        self.feature_names = feature_df.columns.tolist()
        self.is_trained = True
    
    def predict(self, ccn: str, metrics_data: pd.DataFrame) -> Tuple[float, float]:
        """
        특정 병원의 별점 예측
        
        Args:
            ccn: 병원 CCN
            metrics_data: 해당 병원의 메트릭 데이터
        
        Returns:
            (predicted_star, confidence) - 예측 별점과 신뢰도
        """
        if not self.is_trained:
            return 3.0, 0.0
        
        # 특징 준비
        features = self.prepare_features(metrics_data)
        
        if ccn not in features.index:
            return 3.0, 0.0
        
        X = features.loc[[ccn]].values
        X_scaled = self.scaler.transform(X)
        
        # 예측
        predicted = self.model.predict(X_scaled)[0]
        
        # 신뢰도: 특징 데이터의 완성도에 비례
        feature_completeness = np.sum(X[0] > 0) / len(X[0])  # 0이 아닌 도메인 비율
        confidence = min(1.0, feature_completeness * 1.2)  # 최대 1.0
        
        return float(predicted), float(confidence)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """도메인별 중요도 반환"""
        if not self.is_trained:
            return {}
        
        importances = self.model.feature_importances_
        return dict(zip(self.feature_names, importances.tolist()))


class StarPredictor:
    """
    Hybrid Ensemble Star Rating Predictor
    
    Markov Transition Model과 Domain Regression Model을 결합하여
    별점을 예측합니다.
    """
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        """
        Args:
            warehouse_dir: 웨어하우스 디렉토리 경로
        """
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
        self.model_dir = os.path.join(self.warehouse_dir, "models")
        os.makedirs(self.model_dir, exist_ok=True)
        
        self.markov_model = MarkovTransitionModel()
        self.regression_model = DomainRegressionModel()
        
        self.markov_weight = 0.5  # 기본 가중치 (학습 후 조정 가능)
        self.regression_weight = 0.5
    
    def train(self, train_releases: Optional[List[str]] = None, progress_callback=None, task_id: Optional[int] = None):
        """
        모델 학습
        
        Args:
            train_releases: 학습할 릴리스 목록 (None이면 모든 데이터 사용)
            progress_callback: Rich Progress 객체 (선택적)
            task_id: 진행 상황 업데이트할 task ID (선택적)
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            if progress_callback and task_id is not None:
                progress_callback.update(task_id, description="[cyan]  └─ 📥 Loading training data...[/cyan]", advance=2)
            
            # 별점 데이터 로드
            query = "SELECT ccn, star_rating, release FROM hospital_star WHERE star_rating IS NOT NULL"
            if train_releases:
                placeholders = ','.join('?' * len(train_releases))
                query += f" AND release IN ({placeholders})"
            query += " ORDER BY ccn, release"
            
            params = list(train_releases) if train_releases else []
            star_df = con.execute(query, params).df()
            
            # 메트릭 데이터 로드
            query = "SELECT ccn, domain, value, release FROM hospital_metrics WHERE value IS NOT NULL"
            if train_releases:
                placeholders = ','.join('?' * len(train_releases))
                query += f" AND release IN ({placeholders})"
            
            metrics_df = con.execute(query, params).df()
            
            if star_df.empty or metrics_df.empty:
                if progress_callback and task_id is not None:
                    progress_callback.update(task_id, description="[yellow]  └─ ⚠️ Insufficient training data[/yellow]", advance=5)
                return
            
            if progress_callback and task_id is not None:
                progress_callback.update(task_id, description="[cyan]  └─ 📊 Training Markov Transition Model...[/cyan]", advance=2)
            
            # Markov 모델 학습
            self.markov_model.train(star_df)
            
            if progress_callback and task_id is not None:
                progress_callback.update(task_id, description="[cyan]  └─ 📊 Training Domain Regression Model (this may take a while)...[/cyan]", advance=2)
            
            # Regression 모델 학습 (시간이 오래 걸림)
            self.regression_model.train(metrics_df, star_df, progress_callback=progress_callback, task_id=task_id)
            
            if progress_callback and task_id is not None:
                progress_callback.update(task_id, description="[cyan]  └─ 💾 Saving models...[/cyan]", advance=1)
            
            # 모델 저장
            self._save_models()
            
            if progress_callback and task_id is not None:
                progress_callback.update(task_id, description="[green]  └─ ✅ Model training completed[/green]", advance=3)
            
        finally:
            con.close()
    
    def predict_for_release(self, release: str) -> pd.DataFrame:
        """
        특정 릴리스에 대해 공식 별점이 없는 병원들의 별점 예측
        
        Args:
            release: 릴리스 문자열 (예: "2024_01")
        
        Returns:
            DataFrame with columns: ccn, predicted_star, confidence, method, probabilities
        """
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            # 해당 릴리스에서 공식 별점이 있는 병원 찾기
            official_stars_query = """
                SELECT DISTINCT ccn 
                FROM hospital_star 
                WHERE release = ? AND star_rating IS NOT NULL
            """
            official_ccns = set(con.execute(official_stars_query, [release]).df()['ccn'].tolist())
            
            # 해당 릴리스에 데이터는 있지만 공식 별점이 없는 병원 찾기
            all_ccns_query = """
                SELECT DISTINCT ccn 
                FROM hospital_metrics 
                WHERE release = ?
            """
            all_ccns = set(con.execute(all_ccns_query, [release]).df()['ccn'].tolist())
            
            # 예측 대상: 공식 별점이 없는 병원
            predict_ccns = all_ccns - official_ccns
            
            if len(predict_ccns) == 0:
                return pd.DataFrame()
            
            # 각 병원에 대해 예측
            predictions = []
            
            for ccn in predict_ccns:
                # 이전 별점 조회
                prev_star_query = """
                    SELECT star_rating 
                    FROM hospital_star 
                    WHERE ccn = ? AND star_rating IS NOT NULL AND release < ?
                    ORDER BY release DESC 
                    LIMIT 1
                """
                prev_star_result = con.execute(prev_star_query, [ccn, release]).df()
                prev_star = prev_star_result.iloc[0]['star_rating'] if not prev_star_result.empty else None
                
                # 현재 릴리스 메트릭 조회
                metrics_query = """
                    SELECT domain, value 
                    FROM hospital_metrics 
                    WHERE ccn = ? AND release = ? AND value IS NOT NULL
                """
                metrics_data = con.execute(metrics_query, [ccn, release]).df()
                
                # Markov 예측
                markov_pred, markov_conf = self.markov_model.predict_next(prev_star, ccn)
                markov_probs = self.markov_model.get_probability_distribution(prev_star, ccn)
                
                # Regression 예측
                regress_pred, regress_conf = self.regression_model.predict(ccn, metrics_data)
                
                # Ensemble (신뢰도 기반 가중 평균)
                total_conf = markov_conf + regress_conf
                if total_conf > 0:
                    w_markov = markov_conf / total_conf
                    w_regress = regress_conf / total_conf
                else:
                    w_markov = 0.5
                    w_regress = 0.5
                
                ensemble_pred = w_markov * markov_pred + w_regress * regress_pred
                ensemble_conf = (markov_conf + regress_conf) / 2
                
                predictions.append({
                    'ccn': ccn,
                    'predicted_star': round(ensemble_pred, 2),
                    'confidence': round(ensemble_conf, 3),
                    'markov_prediction': round(markov_pred, 2),
                    'regression_prediction': round(regress_pred, 2),
                    'markov_weight': round(w_markov, 3),
                    'regression_weight': round(w_regress, 3),
                    'prob_1': markov_probs.get(1, 0.0),
                    'prob_2': markov_probs.get(2, 0.0),
                    'prob_3': markov_probs.get(3, 0.0),
                    'prob_4': markov_probs.get(4, 0.0),
                    'prob_5': markov_probs.get(5, 0.0),
                    'release': release
                })
            
            return pd.DataFrame(predictions)
            
        finally:
            con.close()
    
    def save_predictions(self, predictions: pd.DataFrame):
        """
        예측 결과를 데이터베이스에 저장
        
        Args:
            predictions: predict_for_release()의 반환값
        """
        if predictions.empty:
            return
        
        con = duckdb.connect(self.db_path)
        try:
            # star_predictions 테이블 생성 (없으면)
            con.execute("""
                CREATE TABLE IF NOT EXISTS star_predictions (
                    ccn VARCHAR,
                    predicted_star FLOAT,
                    confidence FLOAT,
                    markov_prediction FLOAT,
                    regression_prediction FLOAT,
                    markov_weight FLOAT,
                    regression_weight FLOAT,
                    prob_1 FLOAT,
                    prob_2 FLOAT,
                    prob_3 FLOAT,
                    prob_4 FLOAT,
                    prob_5 FLOAT,
                    release VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ccn, release)
                )
            """)
            
            # 기존 예측 삭제 (같은 릴리스)
            if 'release' in predictions.columns:
                releases = predictions['release'].unique()
                for release in releases:
                    con.execute("DELETE FROM star_predictions WHERE release = ?", [release])
            
            # 새 예측 삽입 (DuckDB는 INSERT OR REPLACE를 지원하지 않으므로 DELETE 후 INSERT)
            for _, row in predictions.iterrows():
                # 기존 예측 삭제
                con.execute(
                    "DELETE FROM star_predictions WHERE ccn = ? AND release = ?",
                    [row['ccn'], row.get('release', 'unknown')]
                )
                
                # 새 예측 삽입
                con.execute("""
                    INSERT INTO star_predictions 
                    (ccn, predicted_star, confidence, markov_prediction, regression_prediction,
                     markov_weight, regression_weight, prob_1, prob_2, prob_3, prob_4, prob_5, release)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['ccn'], row['predicted_star'], row['confidence'],
                    row.get('markov_prediction', 0), row.get('regression_prediction', 0),
                    row.get('markov_weight', 0.5), row.get('regression_weight', 0.5),
                    row.get('prob_1', 0), row.get('prob_2', 0), row.get('prob_3', 0),
                    row.get('prob_4', 0), row.get('prob_5', 0), row.get('release', 'unknown')
                ))
            
            con.commit()
            
        finally:
            con.close()
    
    def _save_models(self):
        """모델 저장 (pickle)"""
        model_path = os.path.join(self.model_dir, "star_predictor.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump({
                'markov': self.markov_model,
                'regression': self.regression_model,
                'weights': {
                    'markov': self.markov_weight,
                    'regression': self.regression_weight
                }
            }, f)
    
    def _load_models(self):
        """저장된 모델 로드"""
        model_path = os.path.join(self.model_dir, "star_predictor.pkl")
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self.markov_model = data['markov']
                self.regression_model = data['regression']
                if 'weights' in data:
                    self.markov_weight = data['weights']['markov']
                    self.regression_weight = data['weights']['regression']

