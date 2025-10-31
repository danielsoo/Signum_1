# 🔄 백업: 코드 재구축 시 참고 정보 (NPPES 포함)

## 📦 필수 패키지 목록

```
requests
python-dotenv
duckdb
numpy
pandas
scipy
scikit-learn
typer
rich
jinja2
pyarrow
python-dateutil
```

---

## ⚙️ 중앙 설정 (CONFIG) - 가장 중요!

### free_provider_apis/common/config.py 구조

```python
CONFIG = {
    "http": {
        "timeout": 25,
        "max_retries": 2,
        "backoff_base": 1.5,
        "backoff_factor": 2.0,
        "jitter": 0.4,
        "user_agent": "Signum-FreeProviderSmoke/1.0 (contact@example.com)",
    },
    
    "limits": {
        "nppes":   {"rps": 5,  "bucket": 5,  "daily": 1000},
        "cms":     {"rps": 5,  "bucket": 5,  "daily": 5000},
        "google_maps": {"rps": 8, "bucket": 8, "daily": 10000},
    },
    
    "nppes": {
        "base_url": "https://npiregistry.cms.hhs.gov/api/",
        "version": "2.1",
    },
    
    "cms_pdc": {
        "doctors_affiliations_url": "https://data.cms.gov/provider-data/api/1/datastore/query/27ea-46a8/0",
        "hospitals_quality_url": "https://data.cms.gov/provider-data/api/1/datastore/query/hospital-general-information/0"
    },
    
    "google_maps": {
        "api_key": os.getenv("GOOGLE_MAPS_API_KEY", ""),
    }
}
```

### Import 방법
```python
from free_provider_apis.common.config import CONFIG
```

---

## 🔌 Import 패턴 (중요!)

### 상대 Import만 사용 (Signum_1/cms 내부)
```python
# ✅ 올바름
from .search_engine import HospitalSearchEngine
from .risk_analyzer import RiskAnalyzer
from .rating_comparator import RatingComparator

# ❌ 절대 import 사용 안 함
# from search_engine import HospitalSearchEngine
```

### free_provider_apis 경로 계산
```python
from pathlib import Path
import sys

current_file = Path(__file__).resolve()
# Signum_1/cms/interactive_search.py 기준
signum_root = current_file.parent.parent.parent  # cms -> Signum_1 -> signum
free_apis_path = signum_root / "free_provider_apis"

# sys.path에 추가
if str(signum_root) not in sys.path:
    sys.path.insert(0, str(signum_root))

# Import
from free_provider_apis.google.places_client_v1 import PlacesV1Client
from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient
from free_provider_apis.common.config import CONFIG
```

### .env 파일 로드
```python
from dotenv import load_dotenv

env_file = free_apis_path / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=str(env_file), override=True)
```

---

## 🏛️ NPPES API 통합 (핵심!)

### NPPESClient 사용법

```python
from free_provider_apis.government.clients_free import NPPESClient

nppes_client = NPPESClient()

# 병원 검색
result = nppes_client.search(
    organization_name="Mayo Clinic",
    state="MN",
    city="Rochester",
    limit=10
)

# 결과 정규화 (중요!)
items = NPPESClient.normalize(result)

# NPI 추출
for item in items:
    npi = item.get("npi")
    name = item.get("name")
    # ... 사용
```

### NPPESClient.search() 파라미터
```python
taxonomy_description: Optional[str] = None,  # 전문과
state: Optional[str] = None,
city: Optional[str] = None,
first_name: Optional[str] = None,  # 개인 의사용
last_name: Optional[str] = None,
organization_name: Optional[str] = None,  # 병원명
number: Optional[str] = None,  # NPI 번호 (10자리)
postal_code: Optional[str] = None,
enumeration_type: Optional[str] = None,  # "NPI-1" (개인) or "NPI-2" (기관)
limit: int = 3,
skip: int = 0,
```

### Rate Limiting
```python
# NPPESClient는 자동으로 rate limit 적용
# CONFIG["limits"]["nppes"] 설정 사용
# - rps: 5 requests per second
# - bucket: 5 token bucket
# - daily: 1000 daily quota
```

---

## 🏥 CMS Provider Data Catalog (PDC) 통합

### CMSPDCClient 사용법

```python
from free_provider_apis.government.clients_free import CMSPDCClient

cms_pdc = CMSPDCClient()

# 1. NPI → 병원 소속 정보 (CCN 찾기)
npi = "1234567890"
affiliations = cms_pdc.get_hospital_affiliations_by_npi(npi)

for affil in affiliations:
    ccn = affil.get("ccn")  # 6자리 CCN
    hospital_name = affil.get("hospital_name")
    # ...

# 2. 여러 CCN → 병원 품질 데이터 일괄 조회
ccns = ("390048", "123456", "789012")
hospital_data = cms_pdc.get_hospital_quality_by_ccns(ccns)

for ccn, data in hospital_data.items():
    rating = data.get("overall_rating")
    name = data.get("hospital_name")
    # ...
```

### CMSPDCClient 특이사항

#### get_hospital_affiliations_by_npi()의 강력한 로직
```python
# 여러 필터 스타일 자동 시도:
# 1. direct key: ?npi=1234567890
# 2. filters-style: ?filters[npi]=1234567890
# 3. $where quoted: ?$where=npi='1234567890'
# 4. $where numeric: ?$where=npi=1234567890

# 여러 페이지네이션 스타일:
# - offset
# - $offset
# - page

# 여러 NPI 컬럼명 시도:
# - "npi"
# - "clinician_npi"
# - "npi_number"
# - "provider_npi"

# 중복 페이지 방지 (무한 루프 방지)
# max_pages = 20
```

#### get_hospital_quality_by_ccns() 배치 처리
```python
# 40개씩 배치로 처리
# SoQL IN 쿼리 사용
# lru_cache로 최대 2048개 결과 캐싱
```

---

## 🔄 완전한 Fallback 로직

### 병원 검색 Fallback 체인
```
1. Google Places API 시도
   ↓ 실패
2. NPPES API 시도 (organization_name으로)
   ↓ 실패
3. Database 직접 검색 (HospitalSearchEngine.search_by_name)
```

### CCN 검증 Flow
```
Google 병원명
   ↓
NPPESClient.search(organization_name=...)
   ↓
NPPESClient.normalize() → NPI 추출
   ↓
CMSPDCClient.get_hospital_affiliations_by_npi(npi)
   ↓
CCN 찾기
   ↓
CMS 데이터베이스 조회
```

---

## 🛠️ Rate Limiter & HTTP Utils

### Rate Limiter 구조
```python
from free_provider_apis.government.rate_limiter import CompositeLimiter

# TokenBucket: 초당 요청 제한
# DailyQuota: 일일 할당량
# CompositeLimiter: 둘 다 결합

limiter = CompositeLimiter(
    rps=5.0,        # 초당 5개 요청
    bucket=5,       # 버킷 용량 5
    daily_quota=1000  # 일일 1000개
)

limiter.acquire()  # 사용 전 호출 필수
```

### HTTP Utils
```python
from free_provider_apis.government.http_utils import HttpClient

http = HttpClient()
# 자동 retry 로직:
# - 429 (Rate Limit): Retry-After 헤더 확인
# - 408, 502, 503, 504: Exponential backoff
# - ConnectionError, Timeout: Exponential backoff
# - max_retries: 2회

resp = http.get(url, params={...})
data = http.safe_json(resp)  # JSON 파싱 + 에러 처리
```

---

## 📍 중요한 경로 설정

### 기본 경로 (Signum_1/cms 내부)
```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # Signum_1/
DEFAULT_WAREHOUSE_DIR = PROJECT_ROOT / "warehouse"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
```

### free_provider_apis 경로
```python
# Signum_1/cms/interactive_search.py 기준
current_file = Path(__file__).resolve()
# 파일 위치: signum/Signum_1/cms/interactive_search.py
signum_root = current_file.parent.parent.parent  # signum 루트
free_apis_path = signum_root / "free_provider_apis"
```

---

## 🎯 Google Places API 통합

```python
from free_provider_apis.google.places_client_v1 import PlacesV1Client
from free_provider_apis.google.feature_flags import enable

enable("text_search")
client = PlacesV1Client(strict=False)

result = client.search_text(
    query,
    fields=[
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount"
    ]
)

places = result.get("places", [])
```

---

## 📐 거리 계산 (Haversine 공식)
```python
import math

def calculate_distance(coord1: tuple, coord2: tuple) -> float:
    """두 좌표 간 거리 계산 (마일)"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 3959.0  # 지구 반지름 (마일)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2)**2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance
```

---

## 🔍 검색 로직 구조

### Hospital Search Engine
```python
from .search_engine import HospitalSearchEngine

engine = HospitalSearchEngine(warehouse_dir)

# 병원명으로 검색
results = engine.search_by_name("Mayo Clinic", state="MN")

# 주소로 검색
results = engine.search_by_address("Rochester", state="MN")

# CCN으로 정확히 찾기
hospital = engine.get_by_ccn("390048")

# 최신 별점
rating = engine.get_latest_star_rating("390048")
```

### Risk Analyzer
```python
from .risk_analyzer import RiskAnalyzer

analyzer = RiskAnalyzer(warehouse_dir)

# 모든 위험 지표 분석
alerts = analyzer.analyze_all_risks("390048")

# 도메인별 메트릭
metrics = analyzer.get_domain_metrics("390048")
```

---

## ⚠️ 해결했던 문제들

1. **Import 오류**: 절대 import → 상대 import로 변경
2. **경로 문제**: `Path(__file__).resolve().parents[]` 사용
3. **.env 로드**: `free_apis_path / ".env"` 경로 설정
4. **가상 환경**: `../.venv/bin/python` 사용
5. **Rate Limiting**: CONFIG의 limits 사용
6. **HTTP Retry**: HttpClient의 자동 retry 로직 활용

---

## 📝 환경 변수

```bash
# HTTP 설정
export HTTP_TIMEOUT="25"
export HTTP_MAX_RETRIES="2"

# Rate Limiting
export NPPES_RPS="5"
export NPPES_BUCKET="5"
export NPPES_DAILY="1000"
export CMS_RPS="5"
export CMS_BUCKET="5"
export CMS_DAILY="5000"

# 경로 설정
export CMS_WAREHOUSE_DIR="/path/to/warehouse"
export CMS_REPORTS_DIR="/path/to/reports"

# API 키
export GOOGLE_MAPS_API_KEY="your-key-here"
```

---

## 🔗 중요한 파일 구조

```
signum/
├── free_provider_apis/         # 외부 API 클라이언트
│   ├── common/
│   │   └── config.py           # ⭐ 중앙 설정 (매우 중요!)
│   ├── google/
│   │   ├── places_client_v1.py
│   │   ├── feature_flags.py
│   │   └── usage_tracker.py
│   └── government/
│       ├── clients_free.py     # ⭐ NPPESClient, CMSPDCClient
│       ├── http_utils.py       # ⭐ HttpClient (retry 로직)
│       └── rate_limiter.py    # ⭐ Rate limiting
└── Signum_1/
    ├── cms/
    │   ├── interactive_search.py
    │   ├── search_engine.py
    │   ├── risk_analyzer.py
    │   └── ...
    └── warehouse/
```

---

## 🚀 실행 방법

```bash
# 가상 환경 사용 (중요!)
cd Signum_1
../.venv/bin/python -m cms.cli search

# 또는 가상 환경 활성화 후
source ../.venv/bin/activate
python -m cms.cli search
```

---

## 💡 핵심 포인트

1. **CONFIG는 중앙 집중식**: `free_provider_apis/common/config.py`에서 모든 설정 관리
2. **Rate Limiting 필수**: 모든 API 호출 전 `limiter.acquire()` 호출
3. **Fallback 체인**: Google → NPPES → Database 순서
4. **CMSPDCClient의 강력한 pagination**: 여러 스타일 자동 시도
5. **NPPESClient.normalize()**: 반드시 사용하여 정규화된 데이터 얻기
6. **경로 계산**: `Path(__file__).resolve().parents[]` 패턴 기억
7. **상대 import**: Signum_1/cms 내부에서는 항상 `.` 사용

