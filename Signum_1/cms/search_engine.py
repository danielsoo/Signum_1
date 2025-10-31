"""
Hospital Search Engine - 병원명/주소로 CCN 검색
"""
from __future__ import annotations
import os
from typing import List, Optional, Dict, Any
import duckdb
from .constants import DEFAULT_WAREHOUSE_DIR


class HospitalSearchEngine:
    """병원명/주소로 CCN 검색 엔진"""
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
    
    def search_by_name(self, name: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        병원명으로 검색
        
        Args:
            name: 병원명 (예: "Mayo Clinic")
            state: 주 코드 (예: "MN") - 선택사항
        
        Returns:
            [{"ccn": "...", "facility_name": "...", "state": "...", "city": "...", ...}]
        """
        if not os.path.exists(self.db_path):
            return []
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            # 병원명으로 유사 검색
            params = [f"%{name}%"]
            query = """
                SELECT DISTINCT ccn, facility_name, state, city, zip
                FROM hospital_star 
                WHERE facility_name LIKE ?
            """
            
            if state:
                query += " AND state = ?"
                params.append(state)
            
            query += " LIMIT 20"
            
            df = con.execute(query, params).df()

            # 폴백: hospital_star에서 결과가 없으면 hospital_metrics에서 후보 추출
            if df.empty:
                params_fb = [f"%{name}%"]
                query_fb = """
                    SELECT DISTINCT ccn, facility_name, state, city, zip
                    FROM hospital_metrics
                    WHERE facility_name LIKE ?
                """
                if state:
                    query_fb += " AND state = ?"
                    params_fb.append(state)
                query_fb += " LIMIT 20"
                df = con.execute(query_fb, params_fb).df()
            
            results = []
            for _, row in df.iterrows():
                results.append({
                    "ccn": row['ccn'],
                    "facility_name": row['facility_name'],
                    "state": row.get('state'),
                    "city": row.get('city'),
                    "zip": row.get('zip')
                })
            
            return results
            
        finally:
            con.close()
    
    def count_hospitals_by_address(self, city: str, state: Optional[str] = None) -> int:
        """병원 수 카운트 (빠른 조회용)"""
        if not os.path.exists(self.db_path):
            return 0
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            params = [f"%{city}%"]
            query = """
                SELECT COUNT(DISTINCT ccn) as cnt
                FROM hospital_star 
                WHERE city LIKE ?
            """
            
            if state:
                query += " AND state = ?"
                params.append(state)
            
            result = con.execute(query, params).fetchone()
            count = result[0] if result else 0
            
            # 폴백: hospital_star에 결과가 없으면 hospital_metrics 확인
            if count == 0:
                params_fb = [f"%{city}%"]
                query_fb = """
                    SELECT COUNT(DISTINCT ccn) as cnt
                    FROM hospital_metrics 
                    WHERE city LIKE ?
                """
                if state:
                    query_fb += " AND state = ?"
                    params_fb.append(state)
                result = con.execute(query_fb, params_fb).fetchone()
                count = result[0] if result else 0
            
            return count
            
        finally:
            con.close()
    
    def search_by_address(self, city: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """주소로 검색 (전체 결과, 정렬됨)"""
        if not os.path.exists(self.db_path):
            return []
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            params = [f"%{city}%"]
            query = """
                SELECT DISTINCT ccn, facility_name, state, city, zip, star_rating
                FROM hospital_star 
                WHERE city LIKE ?
            """
            
            if state:
                query += " AND state = ?"
                params.append(state)
            
            # 별점으로 정렬: NULL은 맨 아래, 나머지는 5->1 순서
            query += """
                ORDER BY 
                    CASE WHEN star_rating IS NULL THEN 1 ELSE 0 END,
                    star_rating DESC,
                    facility_name ASC
            """
            
            df = con.execute(query, params).df()

            # 폴백: hospital_star에서 결과가 없으면 hospital_metrics에서 후보 추출
            if df.empty:
                params_fb = [f"%{city}%"]
                query_fb = """
                    SELECT DISTINCT ccn, facility_name, state, city, zip
                    FROM hospital_metrics 
                    WHERE city LIKE ?
                """
                if state:
                    query_fb += " AND state = ?"
                    params_fb.append(state)
                query_fb += " ORDER BY facility_name ASC"
                df = con.execute(query_fb, params_fb).df()
            
            results = []
            for _, row in df.iterrows():
                results.append({
                    "ccn": row['ccn'],
                    "facility_name": row['facility_name'],
                    "state": row.get('state'),
                    "city": row.get('city'),
                    "zip": row.get('zip')
                })
            
            return results
            
        finally:
            con.close()
    
    def search_by_address_paginated(self, city: str, state: Optional[str] = None, 
                                     limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """주소로 검색 (페이지별, OFFSET/LIMIT 사용)"""
        if not os.path.exists(self.db_path):
            return []
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            params = [f"%{city}%"]
            query = """
                SELECT DISTINCT ccn, facility_name, state, city, zip, star_rating
                FROM hospital_star 
                WHERE city LIKE ?
            """
            
            if state:
                query += " AND state = ?"
                params.append(state)
            
            # 별점으로 정렬: NULL은 맨 아래, 나머지는 5->1 순서
            query += """
                ORDER BY 
                    CASE WHEN star_rating IS NULL THEN 1 ELSE 0 END,
                    star_rating DESC,
                    facility_name ASC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            df = con.execute(query, params).df()

            # 폴백: hospital_star에서 결과가 없으면 hospital_metrics에서 후보 추출
            if df.empty and offset == 0:
                params_fb = [f"%{city}%"]
                query_fb = """
                    SELECT DISTINCT ccn, facility_name, state, city, zip
                    FROM hospital_metrics 
                    WHERE city LIKE ?
                """
                if state:
                    query_fb += " AND state = ?"
                    params_fb.append(state)
                query_fb += " ORDER BY facility_name ASC LIMIT ? OFFSET ?"
                params_fb.extend([limit, offset])
                df = con.execute(query_fb, params_fb).df()
            
            results = []
            for _, row in df.iterrows():
                results.append({
                    "ccn": row['ccn'],
                    "facility_name": row['facility_name'],
                    "state": row.get('state'),
                    "city": row.get('city'),
                    "zip": row.get('zip')
                })
            
            return results
            
        finally:
            con.close()
    
    def get_by_ccn(self, ccn: str) -> Optional[Dict[str, Any]]:
        """CCN으로 정확히 찾기"""
        if not os.path.exists(self.db_path):
            return None
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
                SELECT ccn, facility_name, state, city, zip
                FROM hospital_star 
                WHERE ccn = ?
                LIMIT 1
            """
            df = con.execute(query, [ccn]).df()
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    "ccn": row['ccn'],
                    "facility_name": row['facility_name'],
                    "state": row.get('state'),
                    "city": row.get('city'),
                    "zip": row.get('zip')
                }

            # 폴백: hospital_metrics에서 조회
            query_fb = """
                SELECT ccn, facility_name, state, city, zip
                FROM hospital_metrics 
                WHERE ccn = ?
                LIMIT 1
            """
            df2 = con.execute(query_fb, [ccn]).df()
            if not df2.empty:
                row = df2.iloc[0]
                return {
                    "ccn": row['ccn'],
                    "facility_name": row['facility_name'],
                    "state": row.get('state'),
                    "city": row.get('city'),
                    "zip": row.get('zip')
                }
            
            return None
            
        finally:
            con.close()
    
    def get_latest_star_rating(self, ccn: str, use_prediction: bool = True, use_estimated: bool = True) -> Optional[float]:
        """
        최신 별점 가져오기
        
        Args:
            ccn: 병원 CCN
            use_prediction: 공식 별점이 없으면 예측 별점 사용 여부
        
        Returns:
            별점 (1.0-5.0) 또는 None
        """
        if not os.path.exists(self.db_path):
            return None
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            # 먼저 테이블 존재 확인
            tables = con.execute("SHOW TABLES").df()['name'].tolist()
            
            # 공식 별점 확인
            if 'hospital_star' in tables:
                query = """
                    SELECT star_rating, release
                    FROM hospital_star 
                    WHERE ccn = ? AND star_rating IS NOT NULL
                    ORDER BY release DESC
                    LIMIT 1
                """
                df = con.execute(query, [ccn]).df()
                
                if not df.empty:
                    rating = float(df.iloc[0]['star_rating'])
                    # 별점은 1-5 사이여야 함 (유효성 검사)
                    if 1.0 <= rating <= 5.0:
                        return rating
            
            # 공식 별점이 없고 예측 별점 사용이 활성화된 경우
            if use_prediction and 'star_predictions' in tables:
                query = """
                    SELECT predicted_star, confidence, release
                    FROM star_predictions 
                    WHERE ccn = ?
                    ORDER BY release DESC
                    LIMIT 1
                """
                df = con.execute(query, [ccn]).df()
                
                if not df.empty:
                    predicted = float(df.iloc[0]['predicted_star'])
                    confidence = float(df.iloc[0]['confidence'])
                    
                    # 신뢰도가 0.3 이상이고 별점 범위 내인 경우만 반환
                    if confidence >= 0.3 and 1.0 <= predicted <= 5.0:
                        return predicted

            # 공식/예측 별점이 없고 추정 사용 시, 추정 별점 계산
            if use_estimated and 'hospital_metrics' in tables:
                est = self.get_estimated_star_rating(ccn)
                if est is not None:
                    return est
            
            return None
            
        except Exception:
            return None
        finally:
            con.close()

    def get_cms_rating_with_source(self, ccn: str) -> Dict[str, Any]:
        """
        CMS 별점 + 출처 + 부가정보 반환
        Returns: {
            "rating": float|None,
            "source": "official|predicted|estimated|none",
            "confidence": Optional[float],
            "reason": Optional[str]
        }
        """
        res: Dict[str, Any] = {"rating": None, "source": "none", "confidence": None, "reason": None}
        if not os.path.exists(self.db_path):
            return res
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            tables = con.execute("SHOW TABLES").df()['name'].tolist()
            # 공식
            if 'hospital_star' in tables:
                df = con.execute(
                    """
                    SELECT star_rating, reason FROM hospital_star
                    WHERE ccn = ? AND star_rating IS NOT NULL
                    ORDER BY release DESC LIMIT 1
                    """, [ccn]
                ).df()
                if not df.empty:
                    rating = float(df.iloc[0]['star_rating'])
                    if 1.0 <= rating <= 5.0:
                        res["rating"] = rating
                        res["source"] = "official"
                        res["reason"] = df.iloc[0].get('reason')
                        return res
            # 예측
            if 'star_predictions' in tables:
                df = con.execute(
                    """
                    SELECT predicted_star, confidence FROM star_predictions
                    WHERE ccn = ? ORDER BY release DESC LIMIT 1
                    """, [ccn]
                ).df()
                if not df.empty:
                    pred = float(df.iloc[0]['predicted_star'])
                    conf = float(df.iloc[0]['confidence'])
                    if conf >= 0.3 and 1.0 <= pred <= 5.0:
                        res["rating"] = pred
                        res["source"] = "predicted"
                        res["confidence"] = conf
                        return res
            # 추정
            est = self.get_estimated_star_rating(ccn)
            if est is not None:
                res["rating"] = est
                res["source"] = "estimated"
            return res
        except Exception:
            return res
        finally:
            con.close()

    def get_estimated_star_rating(self, ccn: str) -> Optional[float]:
        """
        공식/예측 별점이 없을 때 도메인 메트릭으로 추정 별점(1~5) 계산.
        방법: 같은 release 내 도메인별 percent_rank → CMS 가중치 합산 → 1~5 매핑.
        """
        if not os.path.exists(self.db_path):
            return None
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            # 해당 CCN의 최신 release 추출
            rel_df = con.execute(
                """
                SELECT release FROM hospital_metrics
                WHERE ccn = ? AND value IS NOT NULL
                ORDER BY release DESC LIMIT 1
                """, [ccn]
            ).df()
            if rel_df.empty:
                return None
            release = rel_df.iloc[0]['release']

            # 도메인별 percent_rank 계산 (direction에 따라 정렬 방향 결정)
            # percent_rank(): 0~1, 높을수록 좋은 성능이 되도록 처리
            sql = f"""
            WITH base AS (
                SELECT ccn, domain, TRY_CAST(value AS DOUBLE) AS val,
                       direction
                FROM hospital_metrics
                WHERE release = '{release}' AND value IS NOT NULL AND domain IS NOT NULL
            ),
            ranked AS (
                SELECT ccn, domain,
                CASE
                  WHEN lower(direction) LIKE '%lower%' THEN
                    percent_rank() OVER (PARTITION BY domain ORDER BY val ASC)
                  ELSE
                    percent_rank() OVER (PARTITION BY domain ORDER BY val DESC)
                END AS pr
                FROM base
            ),
            agg AS (
                SELECT ccn,
                  AVG(CASE WHEN domain='Mortality' THEN pr END) AS mort,
                  AVG(CASE WHEN domain='Readmission' THEN pr END) AS readm,
                  AVG(CASE WHEN domain='Safety' THEN pr END) AS safety,
                  AVG(CASE WHEN domain='PatientExperience' THEN pr END) AS px,
                  AVG(CASE WHEN domain='Timely' THEN pr END) AS timely
                FROM ranked GROUP BY ccn
            )
            SELECT ccn,
              -- 가중치: 0.22,0.22,0.22,0.22,0.12 (결측은 남은 가중치로 재분배)
              (
                COALESCE(mort, 0) * 0.22 +
                COALESCE(readm, 0) * 0.22 +
                COALESCE(safety, 0) * 0.22 +
                COALESCE(px, 0) * 0.22 +
                COALESCE(timely, 0) * 0.12
              ) /
              NULLIF( (CASE WHEN mort IS NOT NULL THEN 0.22 ELSE 0 END) +
                      (CASE WHEN readm IS NOT NULL THEN 0.22 ELSE 0 END) +
                      (CASE WHEN safety IS NOT NULL THEN 0.22 ELSE 0 END) +
                      (CASE WHEN px IS NOT NULL THEN 0.22 ELSE 0 END) +
                      (CASE WHEN timely IS NOT NULL THEN 0.12 ELSE 0 END), 0)
              AS score
            FROM agg
            WHERE ccn = '{ccn}'
            """
            df = con.execute(sql).df()
            if df.empty or df.iloc[0]['score'] is None:
                return None
            score = float(df.iloc[0]['score'])
            score = max(0.0, min(1.0, score))
            # 0~1 → 1~5 매핑 (소수점 한 자리)
            est = round(1.0 + 4.0 * score, 1)
            return est
        except Exception:
            return None
        finally:
            con.close()
    
    def get_predicted_star_rating(self, ccn: str) -> Optional[Dict]:
        """
        예측 별점 상세 정보 가져오기
        
        Returns:
            {
                "predicted_star": float,
                "confidence": float,
                "release": str,
                "markov_prediction": float,
                "regression_prediction": float
            } 또는 None
        """
        if not os.path.exists(self.db_path):
            return None
        
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            tables = con.execute("SHOW TABLES").df()['name'].tolist()
            
            if 'star_predictions' not in tables:
                return None
            
            query = """
                SELECT predicted_star, confidence, release,
                       markov_prediction, regression_prediction,
                       markov_weight, regression_weight
                FROM star_predictions 
                WHERE ccn = ?
                ORDER BY release DESC
                LIMIT 1
            """
            df = con.execute(query, [ccn]).df()
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    "predicted_star": float(row['predicted_star']),
                    "confidence": float(row['confidence']),
                    "release": row['release'],
                    "markov_prediction": float(row.get('markov_prediction', 0)),
                    "regression_prediction": float(row.get('regression_prediction', 0)),
                    "markov_weight": float(row.get('markov_weight', 0.5)),
                    "regression_weight": float(row.get('regression_weight', 0.5))
                }
            
            return None
            
        except Exception:
            return None
        finally:
            con.close()
    
    def get_psychiatric_quality_indicators(self, ccn: str) -> Optional[Dict[str, Any]]:
        """
        정신병원 품질 지표 조회 (IPFQR 데이터)
        
        Returns:
            {
                "facility_type": "psychiatric",
                "has_data": True/False,
                "indicators": [
                    {"name": "...", "value": "...", "description": "...", "good": True/False},
                    ...
                ]
            }
            또는 None (정신병원이 아니거나 데이터 없음)
        """
        # IPFQR CSV 파일 경로 찾기
        data_dir = os.path.join(os.path.dirname(self.warehouse_dir), "cms", "data")
        ipfqr_file = None
        
        # data 폴더 내에서 IPFQR 파일 찾기
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if "IPFQR_QualityMeasures_Facility" in file and file.endswith('.csv'):
                        ipfqr_file = os.path.join(root, file)
                        break
                if ipfqr_file:
                    break
        
        if not ipfqr_file or not os.path.exists(ipfqr_file):
            return None
        
        try:
            import pandas as pd
            df = pd.read_csv(ipfqr_file, dtype=str, low_memory=False)
            
            # CCN으로 검색
            matches = df[df['Facility ID'].astype(str).str.strip() == ccn]
            
            if matches.empty:
                return None
            
            row = matches.iloc[0]
            indicators = []
            
            # 주요 지표 추출 및 해석
            # 1. 물리적 제지 사용 (낮을수록 좋음)
            restraint_rate = row.get('HBIPS-2 Overall Rate Per 1000')
            if pd.notna(restraint_rate) and str(restraint_rate).strip() and str(restraint_rate) not in ['Not Available', 'N/A']:
                try:
                    rate_val = float(restraint_rate)
                    indicators.append({
                        "name": "Physical Restraint Use",
                        "value": f"{rate_val:.2f} per 1,000 patient hours",
                        "description": "Hours of physical restraint use",
                        "good": rate_val < 0.5  # 0.5 미만이면 좋음
                    })
                except:
                    pass
            
            # 2. 격리 사용 (낮을수록 좋음)
            seclusion_rate = row.get('HBIPS-3 Overall Rate Per 1000')
            if pd.notna(seclusion_rate) and str(seclusion_rate).strip() and str(seclusion_rate) not in ['Not Available', 'N/A']:
                try:
                    rate_val = float(seclusion_rate)
                    indicators.append({
                        "name": "Seclusion Use",
                        "value": f"{rate_val:.2f} per 1,000 patient hours",
                        "description": "Hours of seclusion use",
                        "good": rate_val < 0.5  # 0.5 미만이면 좋음
                    })
                except:
                    pass
            
            # 3. 7일 내 후속 진료 (높을수록 좋음)
            fuh7_pct = row.get('FUH-7 %')
            if pd.notna(fuh7_pct) and str(fuh7_pct).strip() and str(fuh7_pct) not in ['Not Available', 'N/A']:
                try:
                    pct_val = float(fuh7_pct)
                    indicators.append({
                        "name": "7-Day Follow-Up After Discharge",
                        "value": f"{pct_val:.1f}%",
                        "description": "Patients receiving follow-up within 7 days",
                        "good": pct_val >= 50.0  # 50% 이상이면 좋음
                    })
                except:
                    pass
            
            # 4. 30일 재입원율 (낮을수록 좋음)
            readm_rate = row.get('READM-30-IPF Rate')
            if pd.notna(readm_rate) and str(readm_rate).strip() and str(readm_rate) not in ['Not Available', 'N/A']:
                try:
                    rate_val = float(readm_rate)
                    indicators.append({
                        "name": "30-Day Readmission Rate",
                        "value": f"{rate_val:.1f}%",
                        "description": "Patients readmitted within 30 days",
                        "good": rate_val < 20.0  # 20% 미만이면 좋음
                    })
                except:
                    pass
            
            # 5. 약물 치료 지속성
            medcopsy_pct = row.get('MedCoPsy %')
            if pd.notna(medcopsy_pct) and str(medcopsy_pct).strip() and str(medcopsy_pct) not in ['Not Available', 'N/A']:
                try:
                    pct_val = float(medcopsy_pct)
                    indicators.append({
                        "name": "Medication Continuation Post-Discharge",
                        "value": f"{pct_val:.1f}%",
                        "description": "Patients continuing medication after discharge",
                        "good": pct_val >= 70.0  # 70% 이상이면 좋음
                    })
                except:
                    pass
            
            # 6. 퇴원 기록 전송 적시성
            tr2_pct = row.get('TR-2 %')
            if pd.notna(tr2_pct) and str(tr2_pct).strip() and str(tr2_pct) not in ['Not Available', 'N/A']:
                try:
                    pct_val = float(tr2_pct)
                    indicators.append({
                        "name": "Timely Transition Record",
                        "value": f"{pct_val:.1f}%",
                        "description": "Discharge records sent on time",
                        "good": pct_val >= 80.0  # 80% 이상이면 좋음
                    })
                except:
                    pass
            
            if not indicators:
                return {
                    "facility_type": "psychiatric",
                    "has_data": False,
                    "indicators": []
                }
            
            return {
                "facility_type": "psychiatric",
                "has_data": True,
                "indicators": indicators
            }
            
        except Exception as e:
            return None
    
    def get_pediatric_quality_indicators(self, ccn: str) -> Optional[Dict[str, Any]]:
        """
        소아병원 품질 지표 조회 (PCH 데이터)
        
        Returns:
            {
                "facility_type": "pediatric",
                "has_data": True/False,
                "indicators": [
                    {"name": "...", "value": "...", "description": "...", "good": True/False},
                    ...
                ]
            }
            또는 None (소아병원이 아니거나 데이터 없음)
        """
        # PCH CSV 파일 경로 찾기
        data_dir = os.path.join(os.path.dirname(self.warehouse_dir), "cms", "data")
        pch_files = {}
        
        # data 폴더 내에서 PCH 파일들 찾기
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.startswith('PCH_') and file.endswith('.csv'):
                        if 'Complications' in file:
                            pch_files['complications'] = os.path.join(root, file)
                        elif 'HCAHPS' in file and 'HOSPITAL' in file:
                            pch_files['hcahps'] = os.path.join(root, file)
                        elif 'INFECTIONS' in file:
                            pch_files['infections'] = os.path.join(root, file)
                
                # 최소 1개 파일이라도 있으면 break
                if pch_files:
                    break
        
        if not pch_files:
            return None
        
        try:
            import pandas as pd
            indicators = []
            found_data = False
            
            # 1. 합병증 및 예기치 않은 병원 방문
            if 'complications' in pch_files:
                try:
                    df = pd.read_csv(pch_files['complications'], dtype=str, low_memory=False)
                    matches = df[df['Facility ID'].astype(str).str.strip() == ccn]
                    
                    if not matches.empty:
                        found_data = True
                        for _, row in matches.iterrows():
                            measure_desc = row.get('Measure Description', '')
                            rate = row.get('Rate')
                            performance = row.get('Performance Category', '')
                            
                            if pd.notna(rate) and str(rate).strip() and rate not in ['Not Available', 'N/A']:
                                try:
                                    rate_val = float(rate)
                                    # 낮은 합병증률이 좋음
                                    is_good = 'Better' in performance or rate_val < 5.0
                                    
                                    indicators.append({
                                        "name": measure_desc[:50],  # 이름 제한
                                        "value": f"{rate_val:.2f}%",
                                        "description": "Complication/unplanned visit rate",
                                        "good": is_good
                                    })
                                except:
                                    pass
                except Exception:
                    pass
            
            # 2. 환자 경험 (HCAHPS)
            if 'hcahps' in pch_files:
                try:
                    df = pd.read_csv(pch_files['hcahps'], dtype=str, low_memory=False)
                    matches = df[df['Facility ID'].astype(str).str.strip() == ccn]
                    
                    if not matches.empty:
                        found_data = True
                        # Star Rating이 있는 행만 선택
                        star_rows = matches[matches['Patient Survey Star Rating'].notna()]
                        
                        for _, row in star_rows.head(3).iterrows():  # 상위 3개만
                            question = row.get('HCAHPS Question', '')
                            star_rating = row.get('Patient Survey Star Rating')
                            
                            if pd.notna(star_rating) and str(star_rating).strip():
                                try:
                                    stars = int(star_rating)
                                    is_good = stars >= 4
                                    
                                    indicators.append({
                                        "name": f"Patient Satisfaction: {question[:30]}",
                                        "value": f"{stars} stars",
                                        "description": "Patient experience rating",
                                        "good": is_good
                                    })
                                except:
                                    pass
                except Exception:
                    pass
            
            # 3. 의료 관련 감염
            if 'infections' in pch_files:
                try:
                    df = pd.read_csv(pch_files['infections'], dtype=str, low_memory=False)
                    matches = df[df['Facility ID'].astype(str).str.strip() == ccn]
                    
                    if not matches.empty:
                        found_data = True
                        for _, row in matches.head(3).iterrows():  # 상위 3개만
                            measure_name = row.get('Measure Name', '')
                            score = row.get('Score')
                            
                            if pd.notna(score) and str(score).strip() and score not in ['Not Available', 'N/A']:
                                try:
                                    score_val = float(score)
                                    # SIR (Standardized Infection Ratio): 1.0 미만이 좋음
                                    is_good = score_val < 1.0
                                    
                                    indicators.append({
                                        "name": measure_name[:50],
                                        "value": f"{score_val:.2f} SIR",
                                        "description": "Infection ratio (lower is better)",
                                        "good": is_good
                                    })
                                except:
                                    pass
                except Exception:
                    pass
            
            if not found_data:
                return None
            
            if not indicators:
                return {
                    "facility_type": "pediatric",
                    "has_data": False,
                    "indicators": []
                }
            
            return {
                "facility_type": "pediatric",
                "has_data": True,
                "indicators": indicators
            }
            
        except Exception as e:
            return None