# 올바른 사용 방법

## 문제점
터미널에서 `python3 -m cms.cli search`를 실행하면 시스템 Python이 사용됩니다.
하지만 패키지는 가상 환경(.venv)에 설치되어 있습니다.

## 해결 방법

### 방법 1: 가상 환경 활성화 후 실행
```bash
cd provider/hospital
source ../.venv/bin/activate  # 또는 .venv/bin/activate
python -m hospital.cli search
```

### 방법 2: 가상 환경의 Python 직접 사용
```bash
cd provider/hospital
../.venv/bin/python3 -m cms.cli search
```

## 가상 환경 확인
```bash
# 가상 환경이 활성화되어 있으면 프롬프트 앞에 (.venv) 표시
(.venv) younsoopark@YounSooui-MacBookAir Signum_1 % python -m hospital.cli search
```

## 패키지 설치 확인
가상 환경에서 다음 패키지가 설치되어 있는지 확인:
```bash
pip list | grep -E "(requests|dotenv|duckdb)"
```

## 빠른 시작
```bash
# Signum_1 폴더에서
source ../.venv/bin/activate  # 가상 환경 활성화
python -m hospital.cli search      # 실행
```

프롬프트 앞에 `(.venv)`이 보이면 올바르게 활성화된 것입니다!
