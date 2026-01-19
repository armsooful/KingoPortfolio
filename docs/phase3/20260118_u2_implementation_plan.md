# Phase 3-C / U-2 구현 계획
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
U-2 API 설계를 기반으로 구현 순서, 데이터 소스, 검증 항목을 통합 정리한다.

---

## 2. 구현 범위 요약
- 성과 히스토리 조회 API
- 기간 비교 보기 API
- 지표 상세 보기 API
- 북마크 저장/조회 API

---

## 3. 구현 순서
1) 공통 유틸 (active result_version 조회, 엔터티 ID 매핑)
2) 성과 히스토리 조회 API
3) 기간 비교 보기 API
4) 지표 상세 보기 API
5) 북마크 저장/조회 API
6) 문구 가드/금지어 필터 확인
7) 테스트/검증

---

## 4. 데이터 소스
- `performance_result` (period_return, cumulative_return, annualized_return, volatility, mdd, sharpe_ratio, sortino_ratio)
- `performance_basis` (price_basis, include_fee/include_tax/include_dividend)
- `result_version` (active)
- `custom_portfolio` (소유/활성 상태 검증)
- `bookmark` (U-2 신규 테이블)

---

## 5. 공통 규칙
- LIVE 성과만 노출
- Read-only (GET) 외 저장은 북마크만 허용
- active result_version 기준
- 금지 문구/행동 유도 표현 차단
- 사용자 소유 포트폴리오만 접근 가능

---

## 6. API별 체크리스트

### 6.1 성과 히스토리
- interval 매핑(DAILY/WEEKLY/MONTHLY)
- 기간 필터(from/to) 검증
- 정렬/limit 적용

### 6.2 기간 비교
- 좌/우 기간 검증
- 결과 없음 처리 및 status_message
- 요약 문구는 설명형

### 6.3 지표 상세
- metric_key 매핑
- 값 null 처리 및 상태 메시지
- basis 정보 노출

### 6.4 북마크
- 중복 추가 409
- 타인 포트폴리오 403
- 목록 캐시 비활성화(no-store)

---

## 7. 테스트/검증
- Read-only 보장 테스트
- LIVE 성과만 노출 테스트
- 금지 문구 차단 테스트
- 오류/지연 처리 메시지 검증

---

## 8. 관련 설계 문서
- 성과 히스토리: docs/phase3/20260118_u2_performance_history_api_design.md
- 기간 비교: docs/phase3/20260118_u2_period_comparison_api_design.md
- 지표 상세: docs/phase3/20260118_u2_metric_detail_api_design.md
- 북마크: docs/phase3/20260118_u2_bookmark_design.md
