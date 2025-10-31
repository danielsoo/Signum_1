# 올바른 실행 방법

## 문제
터미널에서 `python3 -m cms.cli search`를 실행하면 시스템 Python(requests 없음)이 사용됩니다.

## 해결
가상 환경의 Python을 직접 사용하세요:

```bash
# Signum_1 폴더에서
cd provider/hospital

# 가상 환경의 python으로 실행
../.venv/bin/python -m hospital.cli search
```

또는 가상 환경을 활성화하고:
```bash
cd provider/hospital
source ../.venv/bin/activate
python -m hospital.cli search  # python3 아님, python만!
```

## 차이점
- ❌ `python3` → 시스템 Python (requests 없음)
- ✅ `../.venv/bin/python` → 가상 환경 Python (requests 있음)
- ✅ `python` (after activate) → 가상 환경 Python

## 빠른 테스트
```bash
cd provider/hospital
../.venv/bin/python -m hospital.cli search
```

이렇게 실행하면 모든 패키지가 정상적으로 import됩니다!
