# Phase 3-C / 사용자 기능(U-1) 기능 명세 최종본
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
U-1은 사용자에게 **행동을 유도하지 않으면서** 포트폴리오 현황과 성과의 **이해를 돕는 정보**를 제공한다.
모든 기능은 조회(Read-only)이며 결과를 변경하지 않는다.

---

## 2. 범위

### In-Scope
- 포트폴리오 구성/비중 조회
- 기간 수익률(1M/3M/6M/YTD) 및 누적 수익률 조회
- 벤치마크 대비 수익률(가능 시) 노출
- 기준일/출처/산식 요약 제공
- 신뢰 설명 패널(Why Panel) 제공

### Out-of-Scope
- 종목 추천/교체/리밸런싱 제안
- 매매/행동 유도 CTA
- 사용자 입력을 통한 결과 변경
- SIM/BACK 성과 노출

---

## 3. 사용자 시나리오
- 사용자는 포트폴리오 요약을 조회한다.
- 사용자는 성과 기간을 선택해 성과를 확인한다.
- 사용자는 성과 산식/반영 요소를 이해한다.
- 사용자는 기준일/출처와 계산 시점 정보를 확인한다.

---

## 4. API 명세 (Read-only)

### 4.1 포트폴리오 현황 조회
- **GET** `/api/v1/portfolios/{portfolio_id}/summary`
- 인증: 로그인 사용자(get_current_user)
- 캐시: `Cache-Control: public, max-age=300`

**응답 필드**
- `portfolio_id`, `portfolio_name`
- `as_of_date`, `data_source`, `data_source_summary`
- `is_reference`, `is_stale`, `is_version_active`
- `warning_message`, `status_message`
- `assets[]` (asset_class, weight)

---

### 4.2 성과 조회
- **GET** `/api/v1/portfolios/{portfolio_id}/performance`
- 인증: 로그인 사용자(get_current_user)
- 캐시: `Cache-Control: public, max-age=300`
- 파라미터: `period` (optional, 1M/3M/6M/YTD)

**응답 필드**
- `portfolio_id`, `as_of_date`
- `performance_type` = "LIVE"
- `returns` (1M/3M/6M/YTD)
- `selected_period`, `selected_return`
- `cumulative_return`, `benchmark_return`
- `is_reference`, `is_stale`
- `warning_message`, `status_message`

---

### 4.3 성과 해석 정보
- **GET** `/api/v1/portfolios/{portfolio_id}/performance/explanation`
- 인증: 로그인 사용자(get_current_user)
- 캐시: `Cache-Control: public, max-age=300`

**응답 필드**
- `portfolio_id`, `as_of_date`
- `calculation` (예: 종가 기준 누적 수익률 계산)
- `factors` (fees/fx/dividend)
- `price_basis` (close)
- `disclaimer[]`
- `is_reference`, `is_stale`
- `warning_message`, `status_message`

---

### 4.4 신뢰 설명 패널(Why Panel)
- **GET** `/api/v1/portfolios/{portfolio_id}/explain/why`
- 인증: 로그인 사용자(get_current_user)
- 캐시: `Cache-Control: public, max-age=300`

**응답 필드**
- `title`
- `portfolio_id`, `as_of_date`, `calculated_at`
- `data_snapshot`, `note`
- `disclaimer[]`
- `is_reference`, `is_stale`
- `warning_message`, `status_message`

---

## 5. 표현/규제 가이드

### 5.1 필수 문구
- "본 정보는 투자 권유가 아닙니다."
- "과거 성과는 미래 수익을 보장하지 않습니다."
- "참고용 정보 제공 목적입니다."

### 5.2 금지 문구
- "추천", "지금 투자하세요", "수익이 예상됩니다"

---

## 6. 데이터/보안 기준
- LIVE 성과만 노출
- active result_version 연계
- 관리자 API와 네임스페이스 분리
- 사용자 입력으로 결과 변경 불가

---

## 7. 오류/지연 처리
- 데이터 미산출 시 `is_reference=true` 및 안내 문구 제공
- 기준일 지연 시 `is_stale=true` 및 경고 배지 노출
- 시스템 오류는 사용자 친화 메시지로 일괄 처리

---

## 8. 완료 기준
- U-1 모든 엔드포인트는 GET-only
- LIVE 성과만 노출
- 기준일/출처/산식 설명 제공
- 금지 문구 미노출
- 관리자 기능과 분리

---

## 9. 참조 문서
- U-1 상세 설계: docs/phase3/20260118_phase3c_user_epic_u1_readonly_user_features_detailed_design.md
- U-1 API 설계: docs/phase3/20260118_u1_user_feature_api_design.md
- U-1 검증 체크리스트: docs/phase3/20260118_u1_test_checklist.md
