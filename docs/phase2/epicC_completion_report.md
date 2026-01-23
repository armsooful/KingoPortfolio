# Phase 2 Epic C 완료 보고서
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

**프로젝트**: ForestoCompass (KingoPortfolio)
**작성일**: 2026-01-16
**작성자**: Claude Opus 4.5
**Epic**: C - 사용자 커스텀 포트폴리오

---

## 1. 요약

사용자가 자산군 비중을 직접 정의하여 시뮬레이션을 실행할 수 있는
**커스텀 포트폴리오** 기능을 구현 완료했습니다.

---

## 2. 구현 범위

### 2.1 완료된 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| 포트폴리오 CRUD | 생성/조회/수정/삭제(soft) | ✅ 완료 |
| 비중 검증 | 합계=1, 범위 0~1, 허용 코드 | ✅ 완료 |
| 시뮬레이션 실행 | 커스텀 비중으로 NAV 계산 | ✅ 완료 |
| request_hash | weights 포함 (재현성) | ✅ 완료 |
| 권한 제어 | owner 기반 접근 제어 | ✅ 완료 |
| Epic B 연동 | rebalancing_rule_id 지원 | ✅ 완료 |
| Epic D 연동 | KPI 계산 통합 | ✅ 완료 |

### 2.2 제외된 기능 (Out-of-Scope)

- 개별 종목(티커) 수준 입력
- 사용자 성향 기반 자동 구성
- 실제 주문/계좌 연계
- UI/프론트엔드

---

## 3. 산출물 목록

### 3.1 DDL

| 파일 | 설명 |
|------|------|
| `db/ddl/phase2_epicC_custom_portfolio_ddl.sql` | 테이블 DDL |

### 3.2 ORM 모델

| 파일 | 설명 |
|------|------|
| `backend/app/models/custom_portfolio.py` | ORM 모델 |

**테이블:**
- `custom_portfolio`: 포트폴리오 메타 정보
- `custom_portfolio_weight`: 자산군별 비중
- `asset_class_master`: 허용된 자산군 코드

### 3.3 서비스

| 파일 | 설명 |
|------|------|
| `backend/app/services/custom_portfolio_service.py` | CRUD + 검증 |
| `backend/app/services/custom_portfolio_simulation.py` | 시뮬레이션 엔진 |

### 3.4 API 라우터

| 파일 | 설명 |
|------|------|
| `backend/app/routes/portfolio_custom.py` | REST API |

### 3.5 테스트

| 파일 | 테스트 수 |
|------|----------|
| `backend/tests/unit/test_custom_portfolio.py` | 30+ |

---

## 4. API 엔드포인트

### 4.1 포트폴리오 CRUD

```
GET    /portfolio/asset-classes           # 허용된 자산군 목록
POST   /portfolio/custom                  # 포트폴리오 생성
GET    /portfolio/custom                  # 목록 조회
GET    /portfolio/custom/{id}             # 상세 조회
PUT    /portfolio/custom/{id}             # 수정
DELETE /portfolio/custom/{id}             # 삭제
```

### 4.2 시뮬레이션

```
POST   /portfolio/custom/simulate         # 시뮬레이션 실행
GET    /portfolio/custom/{id}/simulate/path  # NAV 경로 조회
```

---

## 5. 입력 검증 규칙

### 5.1 비중 검증

| 규칙 | 조건 |
|------|------|
| 합계 | `sum(weights) == 1.0` (오차 1e-6) |
| 범위 | `0 <= weight <= 1` |
| 최소 자산군 | 1개 이상 |
| 허용 코드 | EQUITY, BOND, CASH, GOLD, ALT |

### 5.2 API 요청 예시

```json
POST /portfolio/custom
{
  "portfolio_name": "My Balanced",
  "weights": {
    "EQUITY": 0.6,
    "BOND": 0.3,
    "CASH": 0.1
  },
  "description": "60/30/10 포트폴리오"
}
```

---

## 6. 시뮬레이션 연동

### 6.1 request_hash 포함 항목

```python
hash_input = {
    "type": "custom_portfolio",
    "portfolio_id": portfolio_id,
    "weights": "BOND:0.3000|CASH:0.1000|EQUITY:0.6000",  # 정렬
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_nav": 1.0,
    "rebalancing_rule_id": None,
    "engine_version": "1.0.0",
}
```

### 6.2 Epic B 연동

```json
POST /portfolio/custom/simulate
{
  "portfolio_id": 101,
  "start_date": "2020-01-01",
  "end_date": "2025-12-31",
  "initial_nav": 1.0,
  "rebalancing_rule_id": 1  // Epic B 규칙
}
```

### 6.3 Epic D 연동

시뮬레이션 결과에 KPI 자동 계산:

```json
{
  "kpi_metrics": {
    "cagr": 0.0823,
    "volatility": 0.1245,
    "sharpe": 0.66,
    "mdd": -0.1523
  }
}
```

---

## 7. DoD (Definition of Done) 체크리스트

- [x] 커스텀 포트폴리오 저장/조회 API 제공
- [x] weights 검증 (합/범위/코드) 완비
- [x] 커스텀 포트폴리오로 시뮬레이션 실행 가능 (run_id 반환)
- [x] request_hash에 weights 포함 (재현성)
- [x] 권한 (본인 소유) 통제
- [x] Phase 1/2 기존 기능 무영향

---

## 8. 테스트 결과

| 테스트 클래스 | 테스트 항목 |
|--------------|------------|
| TestValidateWeights | 10개 |
| TestNormalizeWeights | 3개 |
| TestGetWeightsHashString | 3개 |
| TestGenerateCustomPortfolioHash | 4개 |
| TestCalculatePortfolioNavPath | 4개 |
| TestCalculateRiskMetrics | 3개 |
| TestGenerateFallbackPath | 3개 |
| TestDoDChecklist | 4개 |

---

## 9. 규제 준수

### 9.1 금지 표현

- API 응답에 "추천", "유리", "최적" 표현 없음

### 9.2 면책 문구

```
"과거 데이터 기반 시뮬레이션이며, 미래 수익을 보장하지 않습니다."
```

---

## 10. 다음 단계

| Epic | 설명 | 우선순위 |
|------|------|----------|
| Epic E | 고급 비용 모델 (슬리피지, 마켓 임팩트) | P2 |
| Epic F | HYBRID 리밸런싱 (PERIODIC + DRIFT) | P2 |

---

**Epic C 상태: DONE** (2026-01-16 완료)

---

*본 보고서는 Epic C 구현의 공식 완료 문서입니다.*
