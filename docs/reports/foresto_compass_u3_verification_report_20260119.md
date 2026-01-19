# Foresto Compass U-3 종합 검증 보고서 (20260119)

## 0. 보고서 정책
- 기존 문서에 추가하지 않음
- 릴리즈 단위 신규 보고서 생성
- 저장 경로: `docs/reports/foresto_compass_u3_verification_report_YYYYMMDD.md`
- 필수 항목 체크리스트는 10번 섹션에 명시

## 1. 검증 범위
- U-1 ~ U-3 사용자 플로우
- Guard 회귀(모의 추천·선정 호출 포함)
- 성능/SLA 확인(k6 기준)

## 2. 환경 정보
- 브랜치: main
- 커밋 SHA: 1351b1961ea0c7d7e8bee5ff407079e0cdfbbe88
- 테스트 러너: python3 -m pytest

## 3. 실행 명령
- Smoke: `MPLCONFIGDIR=/tmp/matplotlib MPLBACKEND=Agg python3 -m pytest -q -m smoke --maxfail=1`
- Integration: `MPLCONFIGDIR=/tmp/matplotlib MPLBACKEND=Agg python3 -m pytest -q -m integration --maxfail=1`
- Integration(재실행, 부분): `python3 -m pytest -q -m integration --maxfail=1` (120s 타임아웃)
- E2E: `MPLCONFIGDIR=/tmp/matplotlib MPLBACKEND=Agg python3 -m pytest -q -m e2e --maxfail=1`
- Guard: `MPLCONFIGDIR=/tmp/matplotlib MPLBACKEND=Agg python3 -m pytest -q -m guard --maxfail=1`
- 성능(k6): 미실행 (k6 미설치)
 - 실행 위치: `/Users/changrim/KingoPortfolio/backend`

## 4. 결과 요약
- Smoke: 통과 (24 passed, 487 deselected)
- Integration: 통과 (75 passed, 6 skipped, 430 deselected)
- Integration(재실행): 부분 실행 후 중단 (120s 타임아웃, `tests/integration/test_admin_controls.py` 진행 중)
- E2E: 통과 (1 passed)
- Guard: 통과 (2 passed)
- 성능/SLA: 미실행 (k6 미설치)

## 5. 실패 케이스 상세
- Integration 재실행이 120s 타임아웃으로 중단됨 (진행 중인 파일: `tests/integration/test_admin_controls.py`)

## 6. 성능 지표
- 미측정 (k6 미설치, Docker 미설치)

## 7. SLA 판정
- 미판정 (성능/SLA 미측정)

## 8. 부하 시나리오(정의)
1. Warm-up: 2분
2. Steady Load: 10분
3. Spike Load: 1~3분

Spike 구간에서 SLA 초과는 허용하되 서비스 불능은 불가로 판정한다.

## 9. 잔여 리스크 및 운영 메모
- k6 기반 부하 테스트 미실행으로 SLA 충족 여부 판단 불가

## 10. 성능 / SLA 검증
- 상태: Deferred
- 사유: k6 미설치로 인한 성능 측정 불가
- 영향: 기능적 무결성에는 영향 없음
- 후속 계획: 운영 전환 전 k6 설치 후 재검증

## 11. 보고서 필수 항목 체크리스트
- 검증 범위 (U-1 ~ U-3)
- 환경 정보 (브랜치, 커밋 SHA, 설정)
- 실행 명령(E2E / Guard / 성능)
- 테스트 결과 요약 (Pass / Fail)
- 실패 케이스 상세(재현 방법 포함)
- 성능 지표(p50/p95/p99, error rate)
- SLA 판정
- 잔여 리스크 및 운영 메모

## 12. U-3 검증 완료 판정 조건
다음 모두 충족 시 U-3 검증 완료로 인정한다.
- Smoke / Integration / E2E 전부 통과
- Guard 테스트 100% 차단 확인
- SLA 기준 충족
- 검증 보고서 작성 및 커밋
