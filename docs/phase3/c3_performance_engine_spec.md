# C-3 성과 계산 엔진 상세 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 입력 정의
- 대상 타입: PORTFOLIO / ACCOUNT / ASSET_CLASS
- 성과 타입: LIVE / SIM / BACK
- 기간 타입: DAILY / MONTHLY / CUMULATIVE
- 입력 데이터
  - 가격: 종가(CLOSE) 또는 최근 유효 가격
  - 거래 비용: 수수료 포함 여부
  - 세금: 기본 미반영 (플래그)
  - 배당/이자: 선택 반영 (플래그)
  - FX: snapshot_id 기반 환율 적용

## 2. 산식 정의

### 2.1 Period Return
- 기간 수익률
- `(종료 가치 - 시작 가치) / 시작 가치`

### 2.2 Cumulative Return
- 누적 수익률
- `(현재 가치 / 최초 가치) - 1`

### 2.3 Annualized Return
- 연환산 수익률
- `((1 + cumulative_return) ^ (365 / 기간일수)) - 1`

### 2.4 Volatility
- 일간 수익률 표준편차 연환산
- `std(daily_return) * sqrt(252)`

### 2.5 MDD
- 기간 중 최대 낙폭
- `min((value / peak_value) - 1)`

### 2.6 Sharpe Ratio
- `(annualized_return - rf) / volatility`

### 2.7 Sortino Ratio
- `(annualized_return - rf) / downside_volatility`

## 3. 처리 흐름

1) 입력 데이터 로딩
- snapshot_id 기준 가격/FX/배당 조회

2) 정합성 검증
- C-2 Validation Rule 적용
- FAIL 발생 시 execution FAILED

3) 성과 계산
- 기간별 수익률/리스크 계산
- 산출 근거 저장 (performance_basis)

4) 벤치마크 비교
- 동일 기간 benchmark 수익률 계산
- 초과 수익률 저장 (benchmark_result)

5) 저장 및 버전
- 결과는 불변 저장 (performance_result)
- 버전 관리: result_version 연계

## 4. 출력 정의

- 내부 API
  - 성과 타입(LIVE/SIM/BACK) 모두 제공
  - 근거/파라미터 포함

- 사용자 API
  - LIVE만 제공
  - 요약 + 면책 문구 포함

## 5. 예외/오류 코드

- C3-PF-001: 데이터 부족
- C3-PF-002: 산식 오류
- C3-PF-003: 벤치마크 미존재

## 6. 재현성 확보

- execution_id + snapshot_ids + calc_params + code_version 기록
- 동일 입력 재실행 시 동일 결과 보장
