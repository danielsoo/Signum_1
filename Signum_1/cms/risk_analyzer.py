"""
Risk Analyzer - 의료 위험 지표 분석 및 경고 생성
"""
from __future__ import annotations
from typing import List, Dict, Optional
import duckdb
import os
from .constants import DEFAULT_WAREHOUSE_DIR
from .query_tool import query_metrics


class RiskAnalyzer:
    """병원의 위험 지표 분석 및 경고 생성"""
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
    
    def analyze_all_risks(self, ccn: str) -> List[Dict[str, Any]]:
        """
        모든 위험 지표 분석
        
        Returns:
            [
                {
                    "severity": "high|medium|low",
                    "domain": "Mortality|Readmission|Safety",
                    "message": "위험 메시지",
                    "value": 4.2,
                    "national_avg": 3.0
                },
                ...
            ]
        """
        alerts = []
        
        # 1. 사망률 위험 체크 (여러 지표 가능)
        mortality_risks = self._check_mortality_risk(ccn)
        alerts.extend(mortality_risks)
        
        # 2. 재입원율 위험 체크 (여러 지표 가능)
        readmission_risks = self._check_readmission_risk(ccn)
        alerts.extend(readmission_risks)
        
        # 3. 안전 지표 체크 (여러 지표 가능)
        safety_risks = self._check_safety_risk(ccn)
        alerts.extend(safety_risks)
        
        return alerts
    
    def _check_mortality_risk(self, ccn: str) -> List[Dict[str, Any]]:
        """사망률 위험 체크 - 여러 지표 반환 가능"""
        metrics = query_metrics(ccn, domain="Mortality", limit=50)
        
        if metrics.empty:
            return []
        
        alerts = []
        for _, row in metrics.iterrows():
            value = row.get('value')
            compare = row.get('compare_to_national')
            measure_name = row.get('measure_name', '')
            
            if value is None or compare is None or not isinstance(compare, str):
                continue
            
            # 국가 평균보다 나쁘면 경고
            if "Worse" in compare:
                # 단위 추정
                if 'percent' in measure_name.lower() or '%' in measure_name:
                    unit = '%'
                elif 'per 100' in measure_name.lower():
                    unit = ' per 100 patients'
                elif 'per 1000' in measure_name.lower():
                    unit = ' per 1,000 patients'
                else:
                    unit = ' per 100 patients'
                
                # 지표 이름 간단화 (선택적)
                simple_name = measure_name.replace('Death rate for ', '').replace(' patients', '')
                
                alerts.append({
                    "severity": "warning",
                    "domain": "Mortality",
                    "message": f"사망률이 국가 평균보다 높습니다 ({simple_name}: {value:.1f}{unit})",
                    "value": value,
                    "unit": unit,
                    "national_comparison": compare,
                    "measure_name": measure_name
                })
        
        return alerts
    
    def _check_readmission_risk(self, ccn: str) -> List[Dict[str, Any]]:
        """재입원율 위험 체크 - 여러 지표 반환 가능"""
        metrics = query_metrics(ccn, domain="Readmission", limit=50)
        
        if metrics.empty:
            return []
        
        alerts = []
        for _, row in metrics.iterrows():
            value = row.get('value')
            compare = row.get('compare_to_national')
            measure_name = row.get('measure_name', '')
            
            if value is None or compare is None or not isinstance(compare, str):
                continue
            
            # 국가 평균보다 나쁘면 경고
            if "Worse" in compare:
                # Readmission은 보통 퍼센트
                unit = '%'
                
                # 지표 이름 간단화
                simple_name = measure_name.replace('READM-30-', '').replace('-HRRP', '')
                
                alerts.append({
                    "severity": "warning",
                    "domain": "Readmission",
                    "message": f"재입원율이 국가 평균보다 높습니다 ({simple_name}: {value:.1f}{unit})",
                    "value": value,
                    "unit": unit,
                    "national_comparison": compare,
                    "measure_name": measure_name
                })
        
        return alerts
    
    def _check_safety_risk(self, ccn: str) -> List[Dict[str, Any]]:
        """안전 지표 체크 - 여러 지표 반환 가능"""
        metrics = query_metrics(ccn, domain="Safety", limit=50)
        
        if metrics.empty:
            return []
        
        alerts = []
        for _, row in metrics.iterrows():
            value = row.get('value')
            compare = row.get('compare_to_national')
            measure_name = row.get('measure_name', '')
            
            if value is None or compare is None or not isinstance(compare, str):
                continue
            
            # 국가 평균보다 나쁘면 경고
            if "Worse" in compare:
                # 단위 추정
                if 'percent' in measure_name.lower() or '%' in measure_name:
                    unit = '%'
                elif 'per 100' in measure_name.lower():
                    unit = ' per 100 patients'
                elif 'per 1000' in measure_name.lower():
                    unit = ' per 1,000 patients'
                else:
                    unit = ''
                
                # 지표 이름 간단화
                simple_name = measure_name
                
                alerts.append({
                    "severity": "warning",
                    "domain": "Safety",
                    "message": f"안전 지표가 국가 평균보다 높습니다 ({simple_name}: {value:.1f}{unit})",
                    "value": value,
                    "unit": unit,
                    "national_comparison": compare,
                    "measure_name": measure_name
                })
        
        return alerts
    
    def get_domain_metrics(self, ccn: str) -> Dict[str, Dict[str, Any]]:
        """
        도메인별 메트릭 반환
        
        Returns:
            {
                "Mortality": {"latest_value": 2.5, "trend": "...", ...},
                "Readmission": {...},
                ...
            }
        """
        domain_metrics = {}
        
        domains = ["Mortality", "Readmission", "Safety", "PatientExperience", "Timely"]
        
        for domain in domains:
            metrics = query_metrics(ccn, domain=domain, limit=5)
            
            if not metrics.empty:
                latest = metrics.iloc[0]
                domain_metrics[domain] = {
                    "latest_value": latest.get('value'),
                    "national_comparison": latest.get('compare_to_national'),
                    "measure_name": latest.get('measure_name'),
                }
            else:
                domain_metrics[domain] = None
        
        return domain_metrics
