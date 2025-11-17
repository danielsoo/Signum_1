# Interactive Search Guide

## Quick Start

```bash
cd provider/hospital
python -m hospital.cli search
```

## Features

### 1. Hospital Search
Enter hospital name, city, state, and postal code

Example:
```
병원명: Mayo Clinic
도시: Rochester
주: MN
우편번호: 55905
```

### 2. Doctor Search  
Search for doctors by name and specialty

### 3. Filtered Search
Search by location and specialty filters

## Supported Scenarios

### Scenario 1: Complete Search
- Google ✅ → NPPES ✅ → CMS ✅
- Full comprehensive report

### Scenario 2: Google Only
- Google ✅ → NPPES ❌
- Limited report (no CMS data)

### Scenario 3: NPPES Fallback
- Google ❌ → NPPES ✅ → CMS ✅
- Full report (no Google data)

### Scenario 4: Google Only (unverified)
- Google ✅ → NPPES ❌
- Google info only

## Unit Display

All metrics now show clear units:
- Mortality: "X.X deaths per 100 patients"
- Readmission: "XX.X% re-admission rate"
- Safety: "X.X complications per 1,000 patients"
- Patient Experience: "XX.X% satisfaction score"
- Timely Care: "XX.X% timely delivery rate"

## Output Format

```
==============================================================================
검색 결과: X개 병원 발견
==============================================================================

1. Hospital Name [CCN: XXXXXX]
   주소: ...
   Google: ⭐ X.X/5.0
   CMS 의료 품질: ⭐ X.X/5.0

==============================================================================
상세 분석: Hospital Name
==============================================================================

📊 종합 정보
- CMS 의료 품질: X.X/5.0
- 일관성 점수: X.XX/1.0

📈 도메인별 성과 (단위 정보 포함)
- Mortality: X.X deaths per 100 patients
- Readmission: XX.X% re-admission rate
- Safety: X.X complications per 1,000 patients
- Patient Experience: XX.X% satisfaction score
- Timely Care: XX.X% timely delivery rate

⚠️ 위험 분석
- 고위험 지표: X개 발견 / 없음
```

## All Scenarios Covered

1. ✅ Complete search (all sources)
2. ✅ Google only (NPPES verified)
3. ✅ NPPES fallback (Google failed)
4. ✅ Regional search (city/state/postal)
5. ✅ Specialty search (Cardiology, etc.)
6. ✅ Doctor search with hospital affiliations
7. ✅ Filtered search (multiple criteria)
8. ✅ Multiple results selection
9. ✅ Error handling for all cases
10. ✅ Clear unit display for all metrics
