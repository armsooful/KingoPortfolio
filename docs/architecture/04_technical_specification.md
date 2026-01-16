# ForestoCompass 기술 명세서

**문서 버전**: 1.0
**작성일**: 2026-01-16
**대상**: 운영팀, 감사팀, 개발팀, 인프라팀

---

## 1. 시스템 구성

### 1.1 컴포넌트 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ForestoCompass 아키텍처                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │  Frontend   │   │   Backend   │   │  Database   │               │
│  │  (React)    │◄─►│  (FastAPI)  │◄─►│ (PostgreSQL)│               │
│  └─────────────┘   └─────────────┘   └─────────────┘               │
│        │                 │                 │                        │
│        │                 │                 │                        │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │   Vercel    │   │   Railway   │   │   Railway   │               │
│  │   (CDN)     │   │  (Server)   │   │    (DB)     │               │
│  └─────────────┘   └─────────────┘   └─────────────┘               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 기술 스택 상세

| 계층 | 기술 | 버전 | 라이선스 |
|------|------|------|----------|
| Frontend | React | 18.x | MIT |
| Frontend | TypeScript | 5.x | Apache 2.0 |
| Frontend | Vite | 5.x | MIT |
| Backend | Python | 3.9+ | PSF |
| Backend | FastAPI | 0.100+ | MIT |
| Backend | SQLAlchemy | 2.x | MIT |
| Backend | Pydantic | 2.x | MIT |
| Database | PostgreSQL | 15+ | PostgreSQL |
| Auth | JWT (PyJWT) | 2.x | MIT |

---

## 2. 데이터베이스 스키마

### 2.1 Phase 1 테이블

```sql
-- 시뮬레이션 실행 기록
simulation_run (
    run_id BIGSERIAL PRIMARY KEY,
    request_hash VARCHAR(64) NOT NULL,
    engine_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
)

-- NAV 경로 (일별 자산가치)
simulation_path (
    path_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES simulation_run(run_id),
    path_date DATE NOT NULL,
    nav NUMERIC(20,4) NOT NULL,
    daily_return NUMERIC(10,6)
)

-- 시나리오 정의
scenario (
    scenario_id VARCHAR(20) PRIMARY KEY,
    scenario_name VARCHAR(100),
    description TEXT
)
```

### 2.2 Phase 2 테이블

```sql
-- Epic B: 리밸런싱 규칙
rebalancing_rule (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(50) NOT NULL,
    rule_type VARCHAR(20) NOT NULL,  -- PERIODIC, DRIFT
    frequency VARCHAR(20),            -- MONTHLY, QUARTERLY
    drift_threshold NUMERIC(5,4),
    cost_rate NUMERIC(6,4) DEFAULT 0.001,
    is_active BOOLEAN DEFAULT TRUE
)

-- Epic B: 리밸런싱 이벤트
rebalancing_event (
    event_id BIGSERIAL PRIMARY KEY,
    simulation_run_id BIGINT REFERENCES simulation_run(run_id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    trigger_type VARCHAR(20),
    turnover NUMERIC(10,6),
    cost_amount NUMERIC(20,4)
)

-- Epic D: 성과 분석 결과
analysis_result (
    analysis_id BIGSERIAL PRIMARY KEY,
    simulation_run_id BIGINT REFERENCES simulation_run(run_id) ON DELETE CASCADE,
    rf_annual NUMERIC(8,6) DEFAULT 0.0,
    annualization_factor INTEGER DEFAULT 252,
    metrics_json JSONB NOT NULL,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(simulation_run_id, rf_annual, annualization_factor)
)
```

---

## 3. API 명세

### 3.1 인증 API

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/auth/login` | POST | 로그인 (JWT 발급) |
| `/auth/register` | POST | 회원가입 |
| `/auth/me` | GET | 현재 사용자 정보 |

### 3.2 시뮬레이션 API

| 엔드포인트 | 메서드 | 설명 | Rate Limit |
|------------|--------|------|------------|
| `/backtest/scenario` | POST | 시나리오 시뮬레이션 | 5/hour |
| `/backtest/scenario/{id}/path` | GET | NAV 경로 조회 | 30/min |
| `/backtest/run` | POST | 백테스트 실행 | 5/hour |
| `/backtest/compare` | POST | 포트폴리오 비교 | 5/hour |

### 3.3 리밸런싱 API (Phase 2)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/backtest/rebalancing/rules` | GET | 규칙 목록 |
| `/backtest/rebalancing/rules/{id}` | GET | 규칙 상세 |
| `/backtest/scenario/{run_id}/rebalancing-events` | GET | 이벤트 조회 |

### 3.4 성과 분석 API (Phase 2)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/backtest/analysis/run/{run_id}` | GET | KPI 조회 |
| `/backtest/analysis/compare` | GET | 두 시뮬레이션 비교 |

---

## 4. Feature Flag 설정

### 4.1 환경변수

```bash
# Phase 1 플래그
USE_SIM_STORE=0           # PostgreSQL 시뮬레이션 저장 (0=SQLite, 1=PostgreSQL)
USE_SCENARIO_DB=0         # DB 기반 시나리오 (0=폴백, 1=DB)

# Phase 2 플래그
USE_REBALANCING=0         # 리밸런싱 기능 (0=OFF, 1=ON)
DEFAULT_COST_RATE=0.001   # 기본 거래비용률 (10bp)
MISSING_DATA_POLICY=SKIP  # 결측 데이터 정책 (SKIP, ZERO_RETURN)

# 비활성화된 플래그
FEATURE_RECOMMENDATION_ENGINE=0  # 추천 엔진 (항상 OFF)
```

### 4.2 플래그 상태 확인

```python
# config.py에서 출력
print(f"🚩 Feature Flag - Rebalancing (Phase 2): {'ENABLED' if use_rebalancing else 'DISABLED (Default)'}")
```

---

## 5. 보안 설정

### 5.1 인증/인가

| 항목 | 설정 |
|------|------|
| 토큰 유형 | JWT (HS256) |
| 토큰 만료 | 30분 |
| 비밀번호 해싱 | bcrypt |
| API Key (B2B) | SHA-256 해시 |

### 5.2 Rate Limiting

| 엔드포인트 유형 | 제한 |
|----------------|------|
| AI 분석 (시뮬레이션) | 5회/시간 |
| 데이터 조회 | 30회/분 |
| 인증 | 10회/분 |

### 5.3 CORS 설정

```python
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://kingo-portfolio-*.vercel.app",
]
```

---

## 6. 로깅 및 모니터링

### 6.1 로그 레벨

| 환경 | 레벨 | 출력 |
|------|------|------|
| Development | DEBUG | 콘솔 |
| Production | INFO | 파일 + 콘솔 |
| Error | ERROR | 파일 + 알림 |

### 6.2 로그 포맷

```python
logging.info(f"Scenario simulation - scenario: {scenario_id}, hash: {request_hash[:8]}..., cache_hit: {cache_hit}")
```

### 6.3 추적 정보

| 필드 | 설명 |
|------|------|
| `request_hash` | 요청 고유 식별자 |
| `engine_version` | 계산 엔진 버전 |
| `cache_hit` | 캐시 사용 여부 |
| `calculated_at` | 계산 시점 |

---

## 7. 배포 구성

### 7.1 환경별 설정

| 환경 | Frontend | Backend | Database |
|------|----------|---------|----------|
| Development | localhost:5173 | localhost:8000 | SQLite |
| Staging | Vercel Preview | Railway Dev | Railway Dev |
| Production | Vercel | Railway | Railway |

### 7.2 배포 프로세스

```
1. 코드 푸시 → GitHub
2. CI/CD 트리거 → Vercel/Railway
3. 자동 빌드/테스트
4. 환경별 배포
```

---

## 8. 장애 대응

### 8.1 폴백 전략

| 상황 | 폴백 동작 |
|------|-----------|
| DB 연결 실패 | SQLite 폴백 (dev) |
| 시나리오 DB 없음 | 하드코딩된 시나리오 |
| 리밸런싱 테이블 없음 | 프리셋 규칙 반환 |
| 캐시 미스 | 실시간 계산 |

### 8.2 헬스체크

```bash
# 헬스체크 엔드포인트
GET /health
GET /api/v1/health

# 응답
{ "status": "healthy", "version": "1.0.0" }
```

---

## 9. 성능 지표

### 9.1 목표 SLA

| 지표 | 목표 |
|------|------|
| 가동률 | 99.9% |
| API 응답 시간 (p50) | < 200ms |
| API 응답 시간 (p99) | < 1000ms |
| 시뮬레이션 계산 | < 3s |

### 9.2 캐싱 전략

| 데이터 | 캐시 TTL | 저장소 |
|--------|----------|--------|
| 시뮬레이션 결과 | 7일 | PostgreSQL |
| 성과 분석 | 영구 (파라미터별) | PostgreSQL |
| 시나리오 데이터 | 영구 | PostgreSQL |

---

## 10. 감사 체크리스트

### 10.1 보안 점검

- [ ] JWT 시크릿 키 정기 교체
- [ ] 환경변수 암호화 확인
- [ ] Rate Limit 로그 검토
- [ ] 비정상 접근 패턴 모니터링

### 10.2 규제 준수 점검

- [ ] 금지 용어 검색 (추천/유리/최적)
- [ ] 면책 문구 표시 확인
- [ ] Feature Flag 상태 확인
- [ ] 감사 로그 보관 확인

### 10.3 운영 점검

- [ ] 백업 정상 동작
- [ ] 헬스체크 응답 확인
- [ ] 에러 로그 검토
- [ ] 성능 지표 모니터링

---

*본 문서는 운영/감사 목적의 공식 기술 명세서입니다.*
