# Foresto Phase 2 – Epic C(사용자 커스텀 포트폴리오) 상세 설계
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

**문서명**: Foresto_Phase2_EpicC_사용자포트폴리오_상세설계  
**작성일**: 2026-01-16  
**버전**: 1.0.0  
**상태**: Draft (구현 착수용)

---

## 0. 전제(Phase 1/2 의존성)

### 0.1 Phase 1 산출물(존재 가정)
- 시뮬레이션 실행/저장:
  - `simulation_run`, `simulation_path`, `simulation_summary`
- 입력 데이터:
  - `daily_return`(자산군/자산 단위 수익률 소스)
- 캐시:
  - `request_hash` 기반 결과 재사용

### 0.2 Phase 2 산출물(존재 가정)
- Epic B:
  - `rebalancing_rule`, `rebalancing_event`
- Epic D:
  - `analysis_result` (KPI 캐시)

### 0.3 Epic C 원칙
- **개별 종목 입력 금지**(Phase 2 범위) → 자산군/모델 포트폴리오만 허용
- 사용자 입력은 **시뮬레이션 파라미터**로만 사용(투자 판단/추천 금지)
- 재현성: 동일 입력은 동일 결과(캐시/해시)
- Phase 1 테이블 변경 금지(필요 시 확장 테이블 신설)

---

## 1. 목적과 범위

### 1.1 목적
사용자가 자산군 비중을 직접 정의하여,
- 시나리오 템플릿을 “확장”한 커스텀 포트폴리오를 생성/저장하고
- 해당 커스텀 포트폴리오로 시뮬레이션(리밸런싱 포함)을 실행하며
- Epic D 성과 분석을 통해 비교/해석 가능

하도록 한다.

### 1.2 범위(In-Scope)
- 커스텀 포트폴리오 정의(자산군 + 비중)
- 입력 검증(합=100%, 최소/최대 비중, 허용 자산군)
- 시뮬레이션 실행 연결:
  - (선택) `rebalancing_rule_id` 적용 가능
- 조회/버전 관리(최소):
  - 포트폴리오 목록/상세 조회
  - (선택) 수정 시 새 버전 생성

### 1.3 제외(Out-of-Scope)
- 개별 종목(티커) 수준 사용자 입력
- 사용자 성향/목표 기반 추천 또는 자동 구성
- 실제 주문/계좌 연계
- UI/프론트(백엔드/API까지만)

---

## 2. 핵심 개념 모델

### 2.1 Portfolio Template vs Custom Portfolio
- **Template(시나리오 템플릿)**:
  - 시스템 제공 기본 포트폴리오(예: DEFENSIVE/GROWTH 등)
- **Custom Portfolio(사용자 정의)**:
  - 사용자가 비중을 직접 입력한 포트폴리오
  - Template을 기반으로 확장(연결)할 수 있음(옵션)

### 2.2 자산군(Asset Class) 표준
- 시스템 내부 표준 코드(예시):
  - `EQUITY`, `BOND`, `CASH`, `GOLD`, `ALT`
- JSON 키, 저장 테이블, API 응답에서 **동일 코드 사용**(표준화 필수)

---

## 3. 데이터 모델(권장 DDL 설계)

> Phase 2에서는 “사용자” 개념이 이미 시스템에 존재한다고 가정한다.  
> 사용자 테이블이 없다면 `owner_key`(문자열)로 대체 가능.

### 3.1 테이블: custom_portfolio
- 커스텀 포트폴리오의 메타 정보

**주요 필드(권장)**
- `portfolio_id` (PK)
- `owner_user_id` (또는 owner_key)
- `portfolio_name`
- `base_template_id` (nullable)  — 템플릿 기반 확장 시
- `is_active`
- `created_at`, `updated_at`

### 3.2 테이블: custom_portfolio_weight
- 포트폴리오의 자산군별 비중(정규화)

**주요 필드(권장)**
- `portfolio_id` (FK)
- `asset_class_code`
- `target_weight` (0~1)
- (복합 PK) `(portfolio_id, asset_class_code)`

### 3.3 버전 관리(선택)
- 단순 정책(권장):
  - 수정은 기존 row update
- 더 안전한 정책(선택):
  - `portfolio_version` 도입
  - 수정 시 신규 version 생성(재현성 강화)

Phase 2 기본값: **버전 없이 update 허용**, 단 request_hash에 weights 포함하여 시뮬레이션 재현성은 유지.

---

## 4. 입력 검증 규칙(필수)

### 4.1 비중 검증
- 합계:
  - `sum(weights) == 1.0` (허용 오차 epsilon 예: 1e-6)
- 범위:
  - 각 weight는 `0 <= w <= 1`
- 최소 구성:
  - 최소 2개 자산군 이상(정책 선택)
- 금지:
  - 허용되지 않은 asset_class_code 입력 시 400

### 4.2 제약 정책(옵션)
- CASH 최소 비중(예: 0 이상)
- 특정 자산군 최대(예: GOLD <= 0.3) 등
> Phase 2 기본: 시스템 제약은 최소화(합/범위/허용 코드만 강제)

---

## 5. 시뮬레이션 연결 설계

### 5.1 기존 시뮬레이션 입력 확장
현재 `POST /api/v1/backtest/scenario`가 시나리오 기반이라면, Epic C는 아래 중 하나로 확장한다.

#### 옵션 A(권장): 별도 엔드포인트 추가
- `POST /api/v1/backtest/custom-portfolio`
  - body에 `portfolio_id` 또는 weights 포함

#### 옵션 B: 기존 엔드포인트 확장
- `POST /api/v1/backtest/scenario`
  - body에 `custom_portfolio_id` 추가(상호 배타)

Phase 2 권장: **옵션 A** (기존 API 영향 최소)

### 5.2 입력 파라미터(권장)
- `portfolio_id`
- `start_date`, `end_date`
- `initial_nav`
- (선택) `rebalancing_rule_id`  — Epic B 연동
- (선택) `rf_annual`  — Epic D 조회 시

### 5.3 request_hash 포함 항목(필수)
- portfolio weights 전체(정렬/정규화하여 포함)
- start/end, initial_nav
- rebalancing_rule_id 및 관련 파라미터
- 결측 처리 정책(Phase 1/2 공통)

---

## 6. API 설계(권장)

### 6.1 커스텀 포트폴리오 CRUD(최소)
> “삭제”는 soft delete(is_active=false) 권장

#### 생성
- `POST /api/v1/portfolio/custom`
- body:
```json
{
  "portfolio_name": "My Balanced",
  "weights": {
    "EQUITY": 0.6,
    "BOND": 0.3,
    "CASH": 0.1
  },
  "base_template_id": null
}
```

#### 조회(목록)
- `GET /api/v1/portfolio/custom`
- 응답: portfolio_id, name, updated_at

#### 조회(상세)
- `GET /api/v1/portfolio/custom/{portfolio_id}`
- 응답: weights 포함

#### 수정
- `PUT /api/v1/portfolio/custom/{portfolio_id}`
- body: name, weights, active 등

### 6.2 커스텀 포트폴리오 시뮬레이션 실행
- `POST /api/v1/backtest/custom-portfolio`
- body:
```json
{
  "portfolio_id": 101,
  "start_date": "2020-01-01",
  "end_date": "2025-12-31",
  "initial_nav": 1.0,
  "rebalancing_rule_id": 1
}
```

### 6.3 성과 분석 조회(Epic D 연동)
- 커스텀 포트폴리오 실행 결과 run_id를 받아
  - `GET /api/v1/analysis/run/{run_id}` 호출

---

## 7. 서비스/모듈 구조(권장)

- `backend/app/services/custom_portfolio_service.py`
  - create/update/get/list
  - validate_weights
- `backend/app/services/custom_portfolio_simulation.py`
  - portfolio_id → target_weights 로드 → 기존 simulation 호출
- `backend/app/routes/portfolio_custom.py` (또는 controller)
- DB layer:
  - `custom_portfolio`, `custom_portfolio_weight` 모델

---

## 8. 보안/권한(필수)

- owner 기반 접근 제어:
  - 본인 포트폴리오만 조회/수정 가능
- Soft delete:
  - is_active=false면 조회에서 제외(옵션: include_inactive)

---

## 9. 테스트 계획(DoD 포함)

### 9.1 단위 테스트
- weights 합계 검증(정상/오류)
- 허용되지 않은 asset_class_code 입력 시 400
- 정렬/정규화 후 request_hash 안정성

### 9.2 통합 테스트
- 포트폴리오 생성 → 조회 → 시뮬레이션 실행 → run_id 생성
- rebalancing_rule_id ON/OFF 비교 실행
- Epic D KPI 조회까지 end-to-end 확인(선택)

### 9.3 회귀 테스트
- 기존 Phase 1/2 시나리오 기반 실행 영향 0

---

## 10. Epic C Definition of Done

- [ ] 커스텀 포트폴리오 저장/조회 API 제공
- [ ] weights 검증(합/범위/코드) 완비
- [ ] 커스텀 포트폴리오로 시뮬레이션 실행 가능(run_id 반환)
- [ ] request_hash에 weights 포함(재현성)
- [ ] 권한(본인 소유) 통제
- [ ] Phase 1/2 기존 기능 무영향

---

## 11. 구현 우선순위(권장)

1) DB DDL + ORM (custom_portfolio / custom_portfolio_weight)  
2) 검증 로직 + CRUD API  
3) 시뮬레이션 실행 API(기존 엔진 연결)  
4) Epic D 조회 연동(문서/가이드)  
5) 버전 관리(필요 시)

---
