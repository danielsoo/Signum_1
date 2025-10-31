# 🔥 새로운 API 사용법

## 개요

Signum_1 CMS 시스템에 새로운 통합 API가 추가되었습니다:

1. **HospitalSearchEngine**: 병원명/주소로 CCN 검색
2. **RiskAnalyzer**: 위험 지표 분석 및 경고 생성
3. **RatingComparator**: Google vs CMS 별점 비교 분석
4. **UnifiedHospitalService**: 전체 통합 서비스

---

## 📖 사용 예시

### 1. 기본 병원 검색

```python
from Signum_1.cms import UnifiedHospitalService

service = UnifiedHospitalService()

# 병원명으로 검색 및 평가
result = service.search_and_evaluate("Mayo Clinic Rochester")

print(result)
# {
#   "search_results": [...],
#   "selected": {"ccn": "390048", "facility_name": "Mayo Clinic Rochester"},
#   "evaluation": {...}
# }
```

### 2. CCN으로 상세 조회

```python
from Signum_1.cms import UnifiedHospitalService

service = UnifiedHospitalService()

# CCN으로 모든 데이터 조회
ccn = "390048"
data = service.get_hospital_data(ccn)

# 기본 정보
print(data["basic_info"])

# 성장 추세
print(data["insights"])

# 위험 경고
for alert in data["risk_alerts"]:
    print(f"{alert['severity']}: {alert['message']}")

# 도메인별 메트릭
for domain, metrics in data["domain_metrics"].items():
    print(f"{domain}: {metrics}")
```

### 3. Google 데이터와 비교 분석

```python
from Signum_1.cms import UnifiedHospitalService

service = UnifiedHospitalService()

# Google 검색 결과
google_data = {
    "rating": 4.8,
    "user_rating_count": 8543
}

# CMS 데이터와 비교
evaluation = service.get_hospital_data("390048", google_data)

# 별점 비교 결과
comp = evaluation["rating_comparison"]
print(f"일관성: {comp['consistency']}")
print(f"신뢰도: {comp['confidence']}")
print(f"분석: {comp['analysis']}")
```

### 4. 위험 지표 체크

```python
from Signum_1.cms import RiskAnalyzer

analyzer = RiskAnalyzer()

# 위험 분석
alerts = analyzer.analyze_all_risks("390048")

for alert in alerts:
    print(f"[{alert['severity']}] {alert['domain']}: {alert['message']}")
```

### 5. 통합 검색 흐름 (Google + NPPES + CMS)

```python
# 1. Google에서 병원 검색 (free_provider_apis 사용)
from free_provider_apis.google.places_client_v1 import PlacesV1Client

google_client = PlacesV1Client()
results = google_client.search_text("Mayo Clinic Rochester")
place = results["places"][0]

# 2. NPPES에서 CCN 찾기 (free_provider_apis 사용)
from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient

# NPPES로 검색하여 병원 찾기
nppes_client = NPPESClient()
nppes_result = nppes_client.search(organization_name="Mayo Clinic Rochester")

# CCN 추출
cms_pdc = CMSPDCClient()
ccns = [a["ccn"] for a in cms_pdc.get_hospital_affiliations_by_npi(npi) if a.get("ccn")]

# 3. CMS 데이터 조회 (Signum_1)
from Signum_1.cms import UnifiedHospitalService

service = UnifiedHospitalService()
evaluation = service.get_hospital_data(ccns[0], {
    "rating": place.get("rating"),
    "user_rating_count": place.get("userRatingCount")
})

# 4. 결과 통합
print(f"""
병원: {evaluation['basic_info']['facility_name']}
Google 평점: {place['rating']}/5.0
CMS 의료 품질: {evaluation['basic_info']['current_rating']}/5.0
위험 경고: {len(evaluation['risk_alerts'])}개
성장 추세: {evaluation['insights']['trend_direction']}
""")
```

---

## 🔧 API 레퍼런스

### UnifiedHospitalService

#### `search_and_evaluate(query, state=None)`
병원명으로 검색하고 평가

**Returns:**
```python
{
    "search_results": List[Dict],  # 검색 결과 목록
    "selected": Dict,              # 선택된 병원 정보
    "evaluation": Dict             # 평가 결과
}
```

#### `get_hospital_data(ccn, google_data=None)`
CCN으로 모든 데이터 조회

**Returns:**
```python
{
    "basic_info": {...},           # 기본 정보
    "history": {...},              # 히스토리
    "insights": {...},             # 성장 추세
    "domain_metrics": {...},       # 도메인별 메트릭
    "risk_alerts": [...],           # 위험 경고
    "rating_comparison": {...}     # 별점 비교 (Google 데이터 제공 시)
}
```

#### `get_summary(ccn, google_data=None)`
요약 메시지 생성

**Returns:** `str` - 평가 요약 텍스트

---

### HospitalSearchEngine

#### `search_by_name(name, state=None)`
병원명으로 검색

#### `search_by_address(city, state=None)`
주소로 검색

#### `get_by_ccn(ccn)`
CCN으로 정확히 찾기

#### `get_latest_star_rating(ccn)`
최신 별점 가져오기

---

### RiskAnalyzer

#### `analyze_all_risks(ccn)`
모든 위험 지표 분석

**Returns:**
```python
[
    {
        "severity": "high|medium|low",
        "domain": "Mortality|Readmission|Safety",
        "message": "경고 메시지",
        "value": 4.2,
        "national_comparison": "Above|Below|Same"
    }
]
```

#### `get_domain_metrics(ccn)`
도메인별 메트릭

**Returns:**
```python
{
    "Mortality": {"latest_value": 2.5, ...},
    "Readmission": {...},
    ...
}
```

---

### RatingComparator

#### `compare_ratings(google_rating, cms_rating)`
Google vs CMS 별점 비교

**Returns:**
```python
{
    "google_rating": 4.8,
    "cms_rating": 4.5,
    "difference": 0.3,
    "consistency": "high|medium|low",
    "analysis": "...",
    "confidence": 0.93
}
```

---

## 📝 주의사항

1. **DuckDB 필수**: `warehouse/hospital.duckdb` 파일이 있어야 합니다
2. **ETL 완료**: 먼저 `python -m cms.cli learn` 실행 필요
3. **데이터 존재**: 검색하려는 병원이 CMS 데이터에 있어야 합니다

---

## 🚀 빠른 시작

```bash
# 1. 데이터 로드
cd Signum_1
python -m cms.cli learn

# 2. Python에서 사용
python
>>> from cms import UnifiedHospitalService
>>> service = UnifiedHospitalService()
>>> result = service.search_and_evaluate("Mayo Clinic")
>>> print(result)
```
