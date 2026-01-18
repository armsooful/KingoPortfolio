# Foresto Phase 2 – Epic C 실행 패키지
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

**구성**: Epic C DDL + 구현 작업 티켓 세트(JIRA 스타일)  
**작성일**: 2026-01-16  
**버전**: 1.0.0  
**상태**: Ready for Implementation  

---

## 0. 전제 및 원칙
- Phase 1/2 기존 기능 무영향(회귀 테스트 100% 유지)
- 커스텀 포트폴리오는 **자산군 단위**만 허용(개별 종목 입력 금지)
- 사용자 입력은 “시뮬레이션 파라미터”로만 사용(추천/판단 금지)
- 접근 통제: **소유자(owner) 기반**으로 본인 포트폴리오만 조회/수정 가능
- 삭제는 **soft delete(is_active=false)** 권장

---

# Part A) DDL
- 파일: `Foresto_Phase2_EpicC_CustomPortfolio_DDL.sql`
- 테이블:
  - `custom_portfolio`
  - `custom_portfolio_weight`
- 핵심:
  - (owner_user_id, portfolio_name) UNIQUE
  - (portfolio_id, asset_class_code) PK
  - weight 합=1.0 검증은 애플리케이션 레이어(서비스)에서 강제

---

# Part B) 구현 작업 티켓 (JIRA 스타일)

## Epic C 목표
- 사용자가 자산군 비중을 저장/조회/수정할 수 있음
- 해당 포트폴리오로 시뮬레이션 실행(run_id 반환)
- request_hash에 weights 포함하여 재현성 보장

---

## C-0 공통 DoD
- [ ] 추천/판단 문구/로직 0%
- [ ] 입력 검증(합/범위/허용 코드) 완비
- [ ] owner 기반 접근 통제(타인 포트폴리오 접근 차단)
- [ ] Phase 1/2 기존 테스트 100% 유지
- [ ] request_hash에 weights 포함(정렬/정규화)

---

## P2-C1 (DB) Epic C DDL 적용 및 마이그레이션 등록
**타입**: Task / DB  
**우선순위**: P0  

**작업**
- [ ] DDL 적용
- [ ] 마이그레이션 스크립트 등록(다운/업 포함)
- [ ] 권한 부여 확인

**DoD**
- [ ] 테이블 2개 생성 및 인덱스 확인

---

## P2-C2 (Model) ORM 모델/리포지토리 추가
**타입**: Task / Backend  
**우선순위**: P0  

**대상**
- `custom_portfolio` 모델
- `custom_portfolio_weight` 모델
- repository(store) 레이어

**DoD**
- [ ] CRUD 기본 동작 단위 테스트(최소 create/read)

---

## P2-C3 (Service) weights 검증 로직 구현
**타입**: Story / Backend  
**우선순위**: P0  

**요구사항**
- [ ] asset_class_code 허용 목록 검증(시스템 설정으로 관리 권장)
- [ ] 각 weight 0~1 범위 검증
- [ ] 합계 1.0 검증(epsilon=1e-6)
- [ ] 최소 자산군 개수(정책 선택: 기본 2개 이상 권장)

**DoD**
- [ ] 정상/오류 케이스 단위 테스트

---

## P2-C4 (API) 커스텀 포트폴리오 생성 API
**타입**: Story / API  
**우선순위**: P0  

**Endpoint**
- `POST /api/v1/portfolio/custom`

**요구사항**
- [ ] owner_user_id는 인증 컨텍스트에서 주입(요청 body에서 받지 않음)
- [ ] weights JSON 입력을 정규화하여 weight 테이블에 저장
- [ ] (owner, name) UNIQUE 위반 시 409

**DoD**
- [ ] 생성 후 portfolio_id 반환

---

## P2-C5 (API) 포트폴리오 목록/상세 조회 API
**타입**: Story / API  
**우선순위**: P1  

**Endpoints**
- `GET /api/v1/portfolio/custom`
- `GET /api/v1/portfolio/custom/{portfolio_id}`

**요구사항**
- [ ] 본인(owner) 포트폴리오만 조회
- [ ] 상세에는 weights 포함
- [ ] is_active=false는 기본 제외(옵션으로 include_inactive)

**DoD**
- [ ] 목록/상세 정상 응답

---

## P2-C6 (API) 포트폴리오 수정 API (PUT)
**타입**: Story / API  
**우선순위**: P1  

**Endpoint**
- `PUT /api/v1/portfolio/custom/{portfolio_id}`

**요구사항**
- [ ] owner 확인
- [ ] 이름/weights 변경 가능
- [ ] weights 변경 시 기존 row delete+insert 또는 upsert(원자성 확보)
- [ ] updated_at 갱신

**DoD**
- [ ] 수정 후 조회 시 반영 확인

---

## P2-C7 (API) 포트폴리오 비활성화(soft delete)
**타입**: Task / API  
**우선순위**: P2  

**Endpoint**
- `DELETE /api/v1/portfolio/custom/{portfolio_id}`  (실제 delete 금지)
- 동작: is_active=false

**DoD**
- [ ] 목록에서 제외됨

---

## P2-C8 (Integration) 커스텀 포트폴리오 시뮬레이션 실행 API
**타입**: Story / API  
**우선순위**: P0  

**Endpoint (권장)**
- `POST /api/v1/backtest/custom-portfolio`

**요구사항**
- [ ] 입력: portfolio_id, start_date, end_date, initial_nav, (optional) rebalancing_rule_id
- [ ] portfolio_id → target_weights 로드
- [ ] 기존 시뮬레이션 엔진 호출(Phase 1/2 공용)
- [ ] request_hash에 weights 포함(정렬/정규화 필수)
- [ ] 결과: simulation_run_id 반환

**DoD**
- [ ] E2E: 생성 → 실행 → run_id 반환

---

## P2-C9 (Security) owner 기반 접근 통제 적용
**타입**: Task / Security  
**우선순위**: P0  

**요구사항**
- [ ] 상세/수정/삭제/실행에서 owner 검사
- [ ] 불일치 시 403

**DoD**
- [ ] 타인 portfolio_id 접근 차단 테스트

---

## P2-C10 (Hash) weights 정규화 및 request_hash 반영
**타입**: Task  
**우선순위**: P0  

**요구사항**
- [ ] asset_class_code 정렬(lexicographic) 후 해시 입력 구성
- [ ] float 표현 정규화(소수점 자리수 고정 또는 Decimal 사용)
- [ ] 동일 weights 입력은 항상 동일 hash

**DoD**
- [ ] 동치 입력(순서 다른 JSON)도 같은 hash

---

## P2-C11 (Testing) 통합/회귀 테스트 추가
**타입**: Task / QA  
**우선순위**: P1  

**요구사항**
- [ ] Epic C API 스모크
- [ ] 시뮬레이션 실행 스모크
- [ ] Epic D KPI 조회까지 e2e(선택)

**DoD**
- [ ] CI에서 안정적으로 통과

---

## 1차 스프린트 권장 범위(최소 가동)
- P2-C1, P2-C2, P2-C3, P2-C4, P2-C8, P2-C9, P2-C10

---

## 부록: 허용 asset_class_code (초기값 예시)
- EQUITY
- BOND
- CASH
- GOLD
- ALT

> 운영에서는 config/DB 테이블로 관리하는 것을 권장.

---
