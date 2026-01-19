# U-1/U-2 통합 검증 결과

## 범위
- 사용자 플로우 종단 테스트(E2E): `backend/tests/integration`, `backend/tests/smoke`
- 예외·경계 조건: `backend/tests/unit` 전반
- 가드/규제 차단 규칙: `backend/tests/unit/explanation/test_golden.py` 포함

## 실행
- 명령어: `MPLCONFIGDIR=/tmp/matplotlib MPLBACKEND=Agg python3 -m pytest backend/tests -vv -s`
- 실행 위치: `/Users/changrim/KingoPortfolio`

## 결과
- 테스트: 495 passed, 6 skipped
- 소요: 0:04:11
- 커버리지: 48% (htmlcov 생성)

## 비고
- 통합/스모크 테스트는 서비스 전반을 실제 요청 흐름으로 검증함.
- 금지·규제 문구 가드 및 설명 생성 규칙은 골든 테스트로 검증됨.
