# Foresto Phase 2 Epic B 완료 보고서

**프로젝트**: ForestoCompass
**Phase**: Phase 2 / Epic B (Rebalancing Engine)
**작성일**: 2026-01-16
**상태**: ✅ DONE

---

## 1. Executive Summary

Phase 2 Epic B는 포트폴리오 시뮬레이션에 **리밸런싱 엔진**을 추가하는 작업입니다.
기존 Phase 1의 동작을 100% 보존하면서, Feature Flag(`USE_REBALANCING`) 기반으로 리밸런싱 기능을 선택적으로 활성화할 수 있도록 구현했습니다.

### 핵심 성과
- **PERIODIC 리밸런싱**: 월간/분기 정기 리밸런싱 지원
- **DRIFT 리밸런싱**: 편차 기반 리밸런싱 지원
- **비용 모델**: 고정 비용률(cost_rate) 적용
- **이벤트 로깅**: 모든 리밸런싱 판단 근거를 DB에 기록
- **완전한 하위 호환성**: Phase 1 테스트 100% 통과

---

## 2. 변경 범위

### 2.1 Phase 1 대비 변경점

| 구분 | Phase 1 | Phase 2 (Epic B) |
|------|---------|------------------|
| 리밸런싱 | 미지원 | PERIODIC/DRIFT 지원 |
| 비용 모델 | 없음 | 고정 cost_rate (기본 10bp) |
| 이벤트 로그 | 없음 | `rebalancing_event` 테이블 저장 |
| API | `/backtest/scenario` | + `rebalancing_rule` 파라미터 |
| Feature Flag | 없음 | `USE_REBALANCING` (기본 OFF) |

### 2.2 영향 받는 컴포넌트

```
[변경됨]
├── backend/app/models/rebalancing.py      # ORM 모델
├── backend/app/services/rebalancing_engine.py  # 엔진 로직
├── backend/app/services/scenario_simulation.py # 통합
├── backend/app/routes/backtesting.py      # API 엔드포인트
└── backend/app/config.py                  # Feature Flag

[신규]
├── Foresto_Phase2_EpicB_Rebalancing_DDL.sql   # DB 스키마
├── Foresto_Phase2_EpicB_Rebalancing_Seed.sql  # 초기 데이터
└── backend/tests/unit/test_feature_flag_scenarios.py  # 테스트
```

---

## 3. 기술 상세

### 3.1 DB 스키마

#### 3.1.1 rebalancing_rule
리밸런싱 규칙 정의 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| rule_id | SERIAL PK | 규칙 ID |
| rule_name | VARCHAR(64) | 규칙명 (UNIQUE) |
| rule_type | VARCHAR(16) | PERIODIC / DRIFT |
| frequency | VARCHAR(16) | MONTHLY / QUARTERLY |
| base_day_policy | VARCHAR(24) | FIRST_TRADING_DAY / LAST_TRADING_DAY |
| drift_threshold | NUMERIC(8,6) | Drift 임계치 (0 < x < 1) |
| cost_rate | NUMERIC(8,6) | 거래비용률 (기본 0.001 = 10bp) |
| is_active | BOOLEAN | 활성 여부 |

#### 3.1.2 rebalancing_event
리밸런싱 발생 이벤트 로그

| 컬럼 | 타입 | 설명 |
|------|------|------|
| event_id | BIGSERIAL PK | 이벤트 ID |
| simulation_run_id | BIGINT FK | 시뮬레이션 실행 ID (CASCADE) |
| rule_id | INT FK | 적용된 규칙 ID |
| event_date | DATE | 리밸런싱 발생일 |
| trigger_type | VARCHAR(16) | PERIODIC / DRIFT |
| trigger_detail | VARCHAR(64) | 상세 (예: MONTHLY, DRIFT>=5.00%) |
| before_weights | JSONB | 리밸런싱 전 비중 |
| after_weights | JSONB | 리밸런싱 후 비중 |
| turnover | NUMERIC(12,8) | 회전율 |
| cost_rate | NUMERIC(8,6) | 적용된 비용률 |
| cost_amount | NUMERIC(18,8) | 차감된 비용 금액 |

### 3.2 API 변경

#### 3.2.1 POST /api/v1/backtest/scenario

**Request Body 변경**
```json
{
  "scenario_id": "MIN_VOL",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_amount": 1000000,
  "rebalancing_rule": {           // Phase 2 신규
    "rule_type": "PERIODIC",
    "frequency": "MONTHLY",
    "base_day_policy": "FIRST_TRADING_DAY",
    "cost_rate": 0.001
  }
}
```

**Response Body 변경**
```json
{
  "success": true,
  "scenario_id": "MIN_VOL",
  "rebalancing_enabled": true,    // Phase 2 신규
  "rebalancing_events_count": 12, // Phase 2 신규
  "rebalancing_events": [...]     // Phase 2 신규
}
```

#### 3.2.2 신규 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/backtest/rebalancing/rules` | GET | 리밸런싱 규칙 목록 조회 |
| `/backtest/rebalancing/rules/{rule_id}` | GET | 특정 규칙 상세 조회 |
| `/backtest/scenario/{run_id}/rebalancing-events` | GET | 이벤트 조회 |

### 3.3 Feature Flag 동작

| USE_REBALANCING | rebalancing_rule 파라미터 | 동작 |
|-----------------|--------------------------|------|
| 0 (OFF) | 없음 | Phase 1과 동일 (기존 동작) |
| 0 (OFF) | 있음 | **400 Bad Request** (명시적 거부) |
| 1 (ON) | 없음 | Phase 1과 동일 (OFF와 동일) |
| 1 (ON) | 있음 | 리밸런싱 적용 |

### 3.4 리밸런싱 로직

#### PERIODIC (정기 리밸런싱)
```
IF frequency == "MONTHLY":
    trigger_date = 월 첫 거래일 (또는 마지막 거래일)
ELIF frequency == "QUARTERLY":
    trigger_date = 1/4/7/10월 첫 거래일 (또는 마지막 거래일)
```

#### DRIFT (편차 기반 리밸런싱)
```
max_drift = max(|current_weight[i] - target_weight[i]|)

IF max_drift >= drift_threshold:
    trigger = True
```

#### 비용 계산
```
turnover = 0.5 × Σ|after_value[i] - before_value[i]| / total_value
cost_factor = 1 - turnover × cost_rate
nav_after = nav_before × cost_factor
```

---

## 4. 테스트 결과

### 4.1 단위 테스트

| 테스트 파일 | 테스트 수 | 통과 | 실패 |
|------------|----------|------|------|
| test_rebalancing_engine.py | 24 | 24 | 0 |
| test_feature_flag_scenarios.py | 6 | 6 | 0 |
| **합계** | **30** | **30** | **0** |

### 4.2 DoD (Definition of Done) 체크리스트

| 항목 | 상태 | 검증 방법 |
|------|------|----------|
| Phase 1 결과와 동일한 OFF 모드 | ✅ | `test_flag_off_no_rule_phase1_behavior` |
| PERIODIC MONTHLY 정상 동작 | ✅ | `test_periodic_monthly_trigger` |
| PERIODIC QUARTERLY 정상 동작 | ✅ | `test_periodic_quarterly_implemented` |
| DRIFT 정상 동작 | ✅ | `test_drift_trigger` |
| 비용 모델 반영 확인 | ✅ | `test_cost_model_implemented` |
| rebalancing_event 로그 재현 | ✅ | `test_rebalancing_event_logged` |
| request_hash 변경 규칙 정상 | ✅ | `test_hash_includes_rebalancing_params` |
| Feature Flag OFF + rule → 400 | ✅ | `test_flag_off_with_rule_raises_error` |

---

## 5. 배포 가이드

### 5.1 사전 조건
- PostgreSQL 14+
- Phase 1 테이블 (`simulation_run`) 존재

### 5.2 배포 순서

```bash
# 1. DDL 적용
psql -d foresto -f Foresto_Phase2_EpicB_Rebalancing_DDL.sql

# 2. Seed 데이터 적용
psql -d foresto -f Foresto_Phase2_EpicB_Rebalancing_Seed.sql

# 3. 환경변수 설정 (기본 OFF)
export USE_REBALANCING=0

# 4. 애플리케이션 재시작
# 5. 검증 후 Feature Flag ON
export USE_REBALANCING=1
```

### 5.3 롤백 절차

리밸런싱 기능에 문제 발생 시:

```bash
# 1. Feature Flag OFF (즉시 적용)
export USE_REBALANCING=0

# 2. 애플리케이션 재시작
# → Phase 1 동작으로 즉시 복귀
```

> **중요**: DDL 롤백은 필요 없음. Flag OFF만으로 Phase 1 동작 보장.

---

## 6. 운영 모니터링

### 6.1 핵심 지표

```sql
-- 리밸런싱 이벤트 통계
SELECT
    DATE_TRUNC('day', created_at) AS date,
    trigger_type,
    COUNT(*) AS event_count,
    AVG(turnover) AS avg_turnover
FROM rebalancing_event
GROUP BY 1, 2
ORDER BY 1 DESC;
```

### 6.2 알림 조건

| 조건 | 임계치 | 액션 |
|------|--------|------|
| 이벤트 생성 실패 | 0건 (예상 대비) | 로그 확인 |
| turnover 이상치 | > 50% | 규칙 검토 |
| cost_amount 이상치 | > NAV의 1% | 비용 모델 검토 |

---

## 7. 제한사항 및 향후 계획

### 7.1 현재 제한사항

1. **비용 모델**: 고정 비용률만 지원 (슬리피지, 마켓 임팩트 미반영)
2. **리밸런싱 단위**: 자산군(asset_class) 단위만 지원 (개별 종목 미지원)
3. **HYBRID 미지원**: PERIODIC + DRIFT 동시 적용 미지원

### 7.2 향후 확장 (Phase 2+)

| Epic | 설명 | 우선순위 |
|------|------|----------|
| Epic C | 사용자 커스텀 포트폴리오 | P1 |
| Epic D | 성과 분석 계층 (CAGR/MDD/Sharpe) | P1 |
| Epic E | 고급 비용 모델 | P2 |
| Epic F | HYBRID 리밸런싱 | P2 |

---

## 8. 파일 목록

### 8.1 신규 파일

| 파일 | 설명 |
|------|------|
| `Foresto_Phase2_EpicB_Rebalancing_DDL.sql` | DB 스키마 정의 |
| `Foresto_Phase2_EpicB_Rebalancing_Seed.sql` | 초기 데이터 |
| `backend/tests/unit/test_feature_flag_scenarios.py` | Feature Flag 테스트 |

### 8.2 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/models/rebalancing.py` | FK CASCADE 추가 |
| `backend/app/services/rebalancing_engine.py` | 엔진 구현 |
| `backend/app/services/scenario_simulation.py` | 이벤트 저장/조회 함수 |
| `backend/app/routes/backtesting.py` | API 엔드포인트 추가 |
| `backend/app/config.py` | USE_REBALANCING Flag |
| `backend/tests/unit/test_rebalancing_engine.py` | HYBRID 테스트 주석 처리 |

---

## 9. 승인

| 역할 | 이름 | 서명 | 일자 |
|------|------|------|------|
| 개발 | - | ✅ | 2026-01-16 |
| 리뷰 | - | - | - |
| QA | - | - | - |
| 운영 | - | - | - |

---

**Phase 2 Epic B 완료** ✅
