from __future__ import annotations
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import duckdb
from scipy import stats

from .constants import DEFAULT_WAREHOUSE_DIR

logger = logging.getLogger(__name__)


class InsightsAnalyzer:
    """
    Analyzes hospital performance trends and generates insights.
    
    Features:
    - Growth Index calculation (improving/stable/declining)
    - Domain-specific trend analysis
    - Narrative generation for hospital performance
    """
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        self.warehouse_dir = warehouse_dir or DEFAULT_WAREHOUSE_DIR
        self.db_path = os.path.join(self.warehouse_dir, "hospital.duckdb")
        
        # Domain mapping for analysis
        self.domains = ['Mortality', 'Readmission', 'PatientExperience', 'Safety', 'Timely']
    
    def calculate_growth_index(self, ccn: str, current_release: str, lookback_periods: int = 4) -> Dict:
        """
        Calculate growth index for a hospital.
        
        Growth Index = sigmoid(trend_slope + recent_star_change)
        Returns value between 0-1 (0=declining, 0.5=stable, 1=improving)
        """
        # Get historical star ratings
        historical_data = self._get_hospital_star_history(ccn, current_release, lookback_periods)
        
        if len(historical_data) < 2:
            return {
                'growth_index': 0.5,  # Neutral if insufficient data
                'trend_slope': 0.0,
                'recent_change': 0.0,
                'trend_direction': 'Stable',
                'confidence': 'Low'
            }
        
        # Calculate trend slope using linear regression
        periods = np.arange(len(historical_data))
        ratings = historical_data['star_rating'].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(periods, ratings)
        
        # Calculate recent change (last 2 periods)
        recent_change = 0.0
        if len(historical_data) >= 2:
            recent_change = ratings[-1] - ratings[-2]
        
        # Calculate growth index using sigmoid
        growth_input = slope + recent_change
        growth_index = 1 / (1 + np.exp(-growth_input))  # Sigmoid function
        
        # Determine trend direction
        if growth_index > 0.6:
            trend_direction = 'Improving'
        elif growth_index < 0.4:
            trend_direction = 'Declining'
        else:
            trend_direction = 'Stable'
        
        # Determine confidence based on R-squared
        if r_value**2 > 0.7:
            confidence = 'High'
        elif r_value**2 > 0.4:
            confidence = 'Medium'
        else:
            confidence = 'Low'
        
        return {
            'growth_index': float(growth_index),
            'trend_slope': float(slope),
            'recent_change': float(recent_change),
            'trend_direction': trend_direction,
            'confidence': confidence,
            'r_squared': float(r_value**2)
        }
    
    def analyze_domain_trends(self, ccn: str, current_release: str, lookback_periods: int = 4) -> Dict:
        """
        Analyze trends for each domain.
        
        Returns domain-specific trend analysis with change rates and directions.
        """
        domain_trends = {}
        
        for domain in self.domains:
            trend_data = self._get_domain_trend_data(ccn, domain, current_release, lookback_periods)
            
            if len(trend_data) < 2:
                domain_trends[domain] = {
                    'change_rate': 0.0,
                    'direction': '→',
                    'trend': 'No Data',
                    'confidence': 'Low'
                }
                continue
            
            # Calculate change rate (percentage change from first to last)
            first_value = trend_data.iloc[0]['avg_value']
            last_value = trend_data.iloc[-1]['avg_value']
            
            if first_value != 0:
                change_rate = ((last_value - first_value) / abs(first_value)) * 100
            else:
                change_rate = 0.0
            
            # Determine direction
            if change_rate > 5:
                direction = '↑'
                trend = 'Improving'
            elif change_rate < -5:
                direction = '↓'
                trend = 'Declining'
            else:
                direction = '→'
                trend = 'Stable'
            
            # Calculate confidence based on consistency
            if len(trend_data) >= 3:
                values = trend_data['avg_value'].values
                consistency = 1.0 - (np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0.0
                
                if consistency > 0.8:
                    confidence = 'High'
                elif consistency > 0.5:
                    confidence = 'Medium'
                else:
                    confidence = 'Low'
            else:
                confidence = 'Low'
            
            domain_trends[domain] = {
                'change_rate': float(change_rate),
                'direction': direction,
                'trend': trend,
                'confidence': confidence,
                'first_value': float(first_value),
                'last_value': float(last_value)
            }
        
        return domain_trends
    
    def generate_narrative(self, ccn: str, current_release: str) -> str:
        """
        Generate a narrative description of hospital performance.
        
        Combines growth index and domain trends into a readable story.
        """
        # Get hospital name
        hospital_name = self._get_hospital_name(ccn)
        
        # Calculate growth index
        growth_data = self.calculate_growth_index(ccn, current_release)
        
        # Analyze domain trends
        domain_trends = self.analyze_domain_trends(ccn, current_release)
        
        # Get current and previous star ratings
        current_star = self._get_current_star_rating(ccn, current_release)
        previous_star = self._get_previous_star_rating(ccn, current_release)
        
        # Build narrative
        narrative_parts = []
        
        # Overall performance
        if current_star and previous_star:
            star_change = current_star - previous_star
            if star_change > 0:
                narrative_parts.append(f"{hospital_name} improved overall performance (+{star_change:.1f}★ since {self._get_previous_release(current_release)}).")
            elif star_change < 0:
                narrative_parts.append(f"{hospital_name} declined overall performance ({star_change:.1f}★ since {self._get_previous_release(current_release)}).")
            else:
                narrative_parts.append(f"{hospital_name} maintained stable overall performance.")
        else:
            narrative_parts.append(f"{hospital_name} performance analysis:")
        
        # Growth trend
        trend_direction = growth_data['trend_direction']
        if trend_direction == 'Improving':
            narrative_parts.append("The hospital shows an improving trend with consistent growth.")
        elif trend_direction == 'Declining':
            narrative_parts.append("The hospital shows a declining trend requiring attention.")
        else:
            narrative_parts.append("The hospital maintains stable performance.")
        
        # Domain-specific highlights
        improving_domains = [domain for domain, data in domain_trends.items() 
                           if data['trend'] == 'Improving' and data['confidence'] in ['High', 'Medium']]
        declining_domains = [domain for domain, data in domain_trends.items() 
                           if data['trend'] == 'Declining' and data['confidence'] in ['High', 'Medium']]
        
        if improving_domains:
            domain_list = " and ".join(improving_domains)
            narrative_parts.append(f"Notable improvements in {domain_list}.")
        
        if declining_domains:
            domain_list = " and ".join(declining_domains)
            narrative_parts.append(f"Areas needing attention: {domain_list}.")
        
        return " ".join(narrative_parts)
    
    def _get_hospital_star_history(self, ccn: str, current_release: str, lookback_periods: int) -> pd.DataFrame:
        """Get historical star ratings for a hospital."""
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT release, star_rating 
            FROM hospital_star 
            WHERE ccn = ? AND release <= ? AND star_rating IS NOT NULL
            ORDER BY release DESC 
            LIMIT ?
            """
            df = con.execute(query, [ccn, current_release, lookback_periods]).df()
            return df.sort_values('release')  # Sort ascending for trend analysis
        finally:
            con.close()
    
    def _get_domain_trend_data(self, ccn: str, domain: str, current_release: str, lookback_periods: int) -> pd.DataFrame:
        """Get historical domain metrics for trend analysis."""
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT release, AVG(value) as avg_value
            FROM hospital_metrics 
            WHERE ccn = ? AND domain = ? AND release <= ? AND value IS NOT NULL
            GROUP BY release
            ORDER BY release DESC 
            LIMIT ?
            """
            df = con.execute(query, [ccn, domain, current_release, lookback_periods]).df()
            return df.sort_values('release')  # Sort ascending for trend analysis
        finally:
            con.close()
    
    def _get_hospital_name(self, ccn: str) -> str:
        """Get hospital name for a CCN."""
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT facility_name 
            FROM hospital_star 
            WHERE ccn = ? 
            LIMIT 1
            """
            result = con.execute(query, [ccn]).df()
            return result.iloc[0]['facility_name'] if not result.empty else f"Hospital {ccn}"
        finally:
            con.close()
    
    def _get_current_star_rating(self, ccn: str, release: str) -> Optional[float]:
        """Get current star rating for a hospital."""
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT star_rating 
            FROM hospital_star 
            WHERE ccn = ? AND release = ?
            """
            result = con.execute(query, [ccn, release]).df()
            return result.iloc[0]['star_rating'] if not result.empty else None
        finally:
            con.close()
    
    def _get_previous_star_rating(self, ccn: str, current_release: str) -> Optional[float]:
        """Get previous star rating for a hospital."""
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT star_rating 
            FROM hospital_star 
            WHERE ccn = ? AND release < ?
            ORDER BY release DESC 
            LIMIT 1
            """
            result = con.execute(query, [ccn, current_release]).df()
            return result.iloc[0]['star_rating'] if not result.empty else None
        finally:
            con.close()
    
    def _get_previous_release(self, current_release: str) -> str:
        """Get the previous release."""
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT DISTINCT release 
            FROM hospital_star 
            WHERE release < ?
            ORDER BY release DESC 
            LIMIT 1
            """
            result = con.execute(query, [current_release]).df()
            return result.iloc[0]['release'] if not result.empty else current_release
        finally:
            con.close()
    
    def analyze_all_hospitals(self, release: str) -> pd.DataFrame:
        """
        Analyze insights for all hospitals in a release.
        
        Returns DataFrame with growth indices, domain trends, and narratives.
        """
        logger.info(f"Analyzing insights for release {release}")
        
        # Get all hospitals with data for this release
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            query = """
            SELECT DISTINCT ccn, facility_name
            FROM hospital_star 
            WHERE release = ? AND star_rating IS NOT NULL
            """
            hospitals = con.execute(query, [release]).df()
        finally:
            con.close()
        
        if hospitals.empty:
            logger.warning(f"No hospitals found for release {release}")
            return pd.DataFrame()
        
        logger.info(f"Analyzing {len(hospitals)} hospitals")
        
        # Analyze each hospital
        insights_data = []
        
        for _, hospital in hospitals.iterrows():
            ccn = hospital['ccn']
            
            try:
                # Calculate growth index
                growth_data = self.calculate_growth_index(ccn, release)
                
                # Analyze domain trends
                domain_trends = self.analyze_domain_trends(ccn, release)
                
                # Generate narrative
                narrative = self.generate_narrative(ccn, release)
                
                # Compile insights
                insight = {
                    'ccn': ccn,
                    'facility_name': hospital['facility_name'],
                    'release': release,
                    'growth_index': growth_data['growth_index'],
                    'trend_direction': growth_data['trend_direction'],
                    'confidence': growth_data['confidence'],
                    'narrative': narrative,
                    'analyzed_at': datetime.now().isoformat()
                }
                
                # Add domain-specific data
                for domain, trend_data in domain_trends.items():
                    insight[f'{domain.lower()}_trend'] = trend_data['trend']
                    insight[f'{domain.lower()}_change_rate'] = trend_data['change_rate']
                    insight[f'{domain.lower()}_direction'] = trend_data['direction']
                
                insights_data.append(insight)
                
            except Exception as e:
                logger.warning(f"Failed to analyze hospital {ccn}: {e}")
        
        return pd.DataFrame(insights_data)
    
    def save_insights(self, insights_df: pd.DataFrame) -> None:
        """Save insights analysis to DuckDB."""
        if insights_df.empty:
            logger.info("No insights to save")
            return
        
        con = duckdb.connect(self.db_path)
        try:
            # Create table if not exists
            con.execute("""
                CREATE TABLE IF NOT EXISTS hospital_insights (
                    ccn VARCHAR,
                    facility_name VARCHAR,
                    release VARCHAR,
                    growth_index DOUBLE,
                    trend_direction VARCHAR,
                    confidence VARCHAR,
                    narrative TEXT,
                    mortality_trend VARCHAR,
                    mortality_change_rate DOUBLE,
                    mortality_direction VARCHAR,
                    readmission_trend VARCHAR,
                    readmission_change_rate DOUBLE,
                    readmission_direction VARCHAR,
                    patientexperience_trend VARCHAR,
                    patientexperience_change_rate DOUBLE,
                    patientexperience_direction VARCHAR,
                    safety_trend VARCHAR,
                    safety_change_rate DOUBLE,
                    safety_direction VARCHAR,
                    timely_trend VARCHAR,
                    timely_change_rate DOUBLE,
                    timely_direction VARCHAR,
                    analyzed_at TIMESTAMP
                )
            """)
            
            # Insert or replace insights
            con.register("df_insights", insights_df)
            con.execute("""
                INSERT OR REPLACE INTO hospital_insights 
                SELECT * FROM df_insights
            """)
            
            logger.info(f"Saved insights for {len(insights_df)} hospitals")
            
        finally:
            con.close()
