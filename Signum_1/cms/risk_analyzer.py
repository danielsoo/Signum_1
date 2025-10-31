"""
Risk Analyzer - Medical risk indicator analysis and warning generation
"""
from __future__ import annotations
from typing import List, Dict, Optional
import duckdb
import os
from .constants import DEFAULT_WAREHOUSE_DIR
from .query_tool import query_metrics


class RiskAnalyzer:
    """Hospital risk indicator analysis and warning generation"""
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
    
    def analyze_all_risks(self, ccn: str) -> List[Dict[str, Any]]:
        """
        Analyze all risk indicators
        
        Returns:
            [
                {
                    "severity": "high|medium|low",
                    "domain": "Mortality|Readmission|Safety",
                    "message": "Risk message",
                    "value": 4.2,
                    "national_avg": 3.0
                },
                ...
            ]
        """
        alerts = []
        
        # 1. Check mortality risks (multiple indicators possible)
        mortality_risks = self._check_mortality_risk(ccn)
        alerts.extend(mortality_risks)
        
        # 2. Check readmission risks (multiple indicators possible)
        readmission_risks = self._check_readmission_risk(ccn)
        alerts.extend(readmission_risks)
        
        # 3. Check safety indicators (multiple indicators possible)
        safety_risks = self._check_safety_risk(ccn)
        alerts.extend(safety_risks)
        
        return alerts
    
    def _check_mortality_risk(self, ccn: str) -> List[Dict[str, Any]]:
        """Check mortality risks - can return multiple indicators"""
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
            
            # Warn if worse than national average
            if "Worse" in compare:
                # Estimate unit
                if 'percent' in measure_name.lower() or '%' in measure_name:
                    unit = '%'
                elif 'per 100' in measure_name.lower():
                    unit = ' per 100 patients'
                elif 'per 1000' in measure_name.lower():
                    unit = ' per 1,000 patients'
                else:
                    unit = ' per 100 patients'
                
                # Simplify indicator name (optional)
                simple_name = measure_name.replace('Death rate for ', '').replace(' patients', '')
                
                alerts.append({
                    "severity": "warning",
                    "domain": "Mortality",
                    "message": f"Mortality rate is higher than national average ({simple_name}: {value:.1f}{unit})",
                    "value": value,
                    "unit": unit,
                    "national_comparison": compare,
                    "measure_name": measure_name
                })
        
        return alerts
    
    def _check_readmission_risk(self, ccn: str) -> List[Dict[str, Any]]:
        """Check readmission risks - can return multiple indicators"""
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
                # Readmission is usually in percentage
                unit = '%'
                
                # Simplify indicator name
                simple_name = measure_name.replace('READM-30-', '').replace('-HRRP', '')
                
                alerts.append({
                    "severity": "warning",
                    "domain": "Readmission",
                    "message": f"Readmission rate is higher than national average ({simple_name}: {value:.1f}{unit})",
                    "value": value,
                    "unit": unit,
                    "national_comparison": compare,
                    "measure_name": measure_name
                })
        
        return alerts
    
    def _check_safety_risk(self, ccn: str) -> List[Dict[str, Any]]:
        """Check safety indicators - can return multiple indicators"""
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
            
            # Warn if worse than national average
            if "Worse" in compare:
                # Estimate unit
                if 'percent' in measure_name.lower() or '%' in measure_name:
                    unit = '%'
                elif 'per 100' in measure_name.lower():
                    unit = ' per 100 patients'
                elif 'per 1000' in measure_name.lower():
                    unit = ' per 1,000 patients'
                else:
                    unit = ''
                
                # Simplify indicator name
                simple_name = measure_name
                
                alerts.append({
                    "severity": "warning",
                    "domain": "Safety",
                    "message": f"Safety indicator is higher than national average ({simple_name}: {value:.1f}{unit})",
                    "value": value,
                    "unit": unit,
                    "national_comparison": compare,
                    "measure_name": measure_name
                })
        
        return alerts
    
    def get_domain_metrics(self, ccn: str) -> Dict[str, Dict[str, Any]]:
        """
        Return metrics by domain
        
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
