# 변경 이력 - 2026년 1월 15일 (Phase 0 정렬)
최초작성일자: 2026-01-15
최종수정일자: 2026-01-18

## 📋 작업 요약

자본시장법 준수를 위한 **Phase 0 정렬 단계**를 완료했습니다.
- 추천/권유 기능 완전 제거
- 시나리오 기반 학습 전환
- 손실·회복 KPI 최상위 배치
- 결과 재현성 인프라 구축

---

## 🚫 1. 추천/선정 기능 차단

### Feature Flag 비활성화
- **`FEATURE_RECOMMENDATION_ENGINE`**: 기본값 `"0"` (OFF)
- OFF 상태에서 추천 엔진 코드 경로 실행 불가
- 더미 데이터만 반환 (학습용 예시)

### 금지어 제거 (E-1)
**변경된 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `backend/app/utils/export.py` | "추천 자산 배분" → "학습 시나리오 자산 배분" |
| `backend/app/models/securities.py` | "상품 추천 규칙" → "상품 매칭 규칙" |
| `backend/app/routes/admin_portfolio.py` | "추천될 가능성" → "매칭 점수가 높은" |
| `backend/app/routes/admin.py` | "투자 추천 포함" → "가치 평가 참고치 포함" |
| `backend/app/services/portfolio_engine.py` | "포트폴리오 추천 결과" → "포트폴리오 시뮬레이션 결과" |
| `backend/app/services/claude_service.py` | "추천합니다" → "학습해보세요" |
| `backend/app/services/qualitative_analyzer.py` | "관망 추천" → "관망 고려" |

### 금지어 스캔 스크립트 (E-1)
- **`scripts/forbidden_terms_check.sh`**: 자동화된 규제 준수 검사
- **`docs/forbidden_terms.md`**: 금지어 목록 및 대체 표현 문서화
- 예외 패턴: 부정문, 면책 조항, 테스트 코드 자동 필터링

**커밋**: `1b4d7fd`, `7d0a1e3`

---

## 📊 2. KPI 재정렬 (B-1 스펙)

### 백엔드 응답 구조 변경
```json
{
  "risk_metrics": {
    "max_drawdown": 8.5,
    "max_recovery_days": 45,
    "worst_1m_return": -5.2,
    "worst_3m_return": -7.8,
    "volatility": 12.3
  },
  "historical_observation": {
    "total_return": 5.0,
    "cagr": 5.0,
    "sharpe_ratio": 0.85
  }
}
```

### 프론트엔드 UI 변경
- **손실/회복 지표**: 결과 화면 최상단 강조 표시
- **수익률 지표**: "과거 수익률 (참고용)" 라벨, 하단 배치
- **면책 문구**: "과거 수익률은 미래 성과를 보장하지 않습니다"

**관련 파일:**
- `backend/app/services/backtesting.py`: B-1 스펙 구현
- `frontend/src/pages/BacktestPage.jsx`: UI 재배치

---

## 🎯 3. 시나리오 기반 플로우 전환

### 설문 격하 (C-3)
- **Header.jsx**: "설문조사" → "용어학습" (선택적 도구)
- **DiagnosisResultPage.jsx**: Primary CTA를 시나리오로 변경
- **ScenarioSimulationPage.jsx**: 설문 없이 직접 시뮬레이션 가능

### 시나리오 API
- **`GET /scenarios`**: 인증 없이 접근 가능
- **`GET /scenarios/{id}`**: 상세 정보 + disclaimer 포함
- 모든 시나리오에 규제 안전 문구 필수 포함

**관련 파일:**
- `backend/app/routes/scenarios.py`: 3개 관리형 시나리오 (MIN_VOL, DEFENSIVE, GROWTH)

---

## 🔄 4. 재현성 인프라 (D-1, D-2)

### 시뮬레이션 캐싱 (D-1)
- **요청 해시**: SHA-256 기반 64자리 해시
- **캐시 테이블**: `simulation_cache` (TTL 7일)
- **동일 입력 → 동일 결과**: `cache_hit: true` 반환

### 엔진 버전 추적 (D-2)
- **`ENGINE_VERSION`**: 환경변수 설정 (기본값 `1.0.0`)
- **응답 포함**: 모든 백테스트 응답에 `engine_version` 필드

**관련 파일:**
- `backend/app/services/simulation_cache.py`: 캐싱 로직
- `backend/app/models/portfolio.py`: `SimulationCache` 모델
- `backend/app/config.py`: `engine_version` 설정

**커밋**: `a33e1b1`, `249c5aa`

---

## ✅ 5. 스모크 테스트 (E-2)

### 시나리오 API 테스트
- `GET /scenarios` 200 + 스키마 검증
- 자산 배분 합계 100% 검증
- disclaimer 존재 검증

### 시뮬레이션 API 테스트
- 인증/입력 검증 (401, 400, 422)
- B-1 스펙 검증 (risk_metrics, historical_observation)
- 캐싱 동작 검증 (cache_hit, request_hash, engine_version)

**관련 파일:**
- `backend/tests/smoke/test_scenarios_api.py`
- `backend/tests/smoke/test_simulation_api.py`

**커밋**: `0e21649`

---

## 📁 커밋 히스토리

| 해시 | 설명 |
|------|------|
| `7d0a1e3` | fix: Remove forbidden terms from codebase (Phase 0 compliance) |
| `0e21649` | test: Add smoke tests for scenarios and simulation APIs (E-2) |
| `1b4d7fd` | feat: Add forbidden terms scanner for compliance (E-1) |
| `249c5aa` | feat: Add engine version tracking to simulation responses (D-2) |
| `a33e1b1` | feat: Add simulation result caching with request hash (D-1) |

---

## 🎯 Phase 0 검증 체크리스트

- [x] **1.1 추천/선정 차단**: Feature Flag OFF, 금지어 0건
- [x] **1.2 KPI 재정렬**: 손실/회복 지표 최상단, 수익률 "참고용"
- [x] **1.3 시나리오 플로우**: 설문 없이 시나리오 → 시뮬레이션 가능
- [x] **1.4 재현성**: 동일 해시, 캐시 히트, engine_version 포함

**Phase 0 완료일**: 2026-01-15
