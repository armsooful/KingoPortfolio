# Foresto Phase 1 데이터베이스 설정 가이드
최초작성일자: 2026-01-15
최종수정일자: 2026-01-18

> 작성일: 2026-01-15
> 대상: PostgreSQL 14+

## 1. 사전 요구사항

### PostgreSQL 설치

```bash
# macOS (Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt-get install postgresql-14

# Docker
docker run -d \
  --name foresto-postgres \
  -e POSTGRES_USER=foresto \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=foresto_dev \
  -p 5432:5432 \
  postgres:14-alpine
```

### 데이터베이스 생성

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 및 사용자 생성
CREATE USER foresto WITH PASSWORD 'your_secure_password';
CREATE DATABASE foresto_dev OWNER foresto;
GRANT ALL PRIVILEGES ON DATABASE foresto_dev TO foresto;

# 확장 모듈 설치 (선택)
\c foresto_dev
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

---

## 2. DDL 적용

### 로컬 환경

```bash
# 프로젝트 루트에서 실행
cd /path/to/KingoPortfolio

# DDL 적용
psql -U foresto -d foresto_dev -f db/ddl/foresto_phase1.sql

# 또는 환경변수 사용
export DATABASE_URL="postgresql://foresto:password@localhost:5432/foresto_dev"
psql $DATABASE_URL -f db/ddl/foresto_phase1.sql
```

### Docker 환경

```bash
# 컨테이너 내부에서 실행
docker exec -i foresto-postgres psql -U foresto -d foresto_dev < db/ddl/foresto_phase1.sql
```

### 적용 확인

```sql
-- 테이블 목록 확인
\dt

-- 파티션 확인
SELECT
    parent.relname AS parent,
    child.relname AS partition
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname IN ('daily_price', 'daily_return', 'simulation_path')
ORDER BY parent.relname, child.relname;

-- 시나리오 데이터 확인
SELECT scenario_id, name_ko, risk_level FROM scenario_definition;
```

---

## 3. 테이블 구조

### 3.1 메타데이터

| 테이블 | 설명 |
|--------|------|
| `model_version_registry` | 엔진/모델 버전 관리 |
| `source_load_history` | 데이터 적재 이력 추적 |

### 3.2 기준정보

| 테이블 | 설명 |
|--------|------|
| `instrument_master` | 금융상품 통합 마스터 (주식/ETF/채권/지수/환율) |

### 3.3 시계열 데이터 (파티션)

| 테이블 | 설명 | 파티션 |
|--------|------|--------|
| `daily_price` | 일봉 가격 | 월별 |
| `daily_return` | 일간 수익률 | 월별 |

### 3.4 시나리오/포트폴리오

| 테이블 | 설명 |
|--------|------|
| `scenario_definition` | 관리형 시나리오 정의 |
| `portfolio_model` | 시나리오별 포트폴리오 모델 |
| `portfolio_allocation` | 포트폴리오 자산 구성비 |

### 3.5 시뮬레이션 결과

| 테이블 | 설명 | 파티션 |
|--------|------|--------|
| `simulation_run` | 시뮬레이션 실행 기록 | - |
| `simulation_path` | 일별 NAV/낙폭 경로 | 월별 |
| `simulation_summary` | 요약 지표 (MDD, CAGR 등) | - |

---

## 4. 파티션 관리

### 신규 파티션 생성

```sql
-- 미래 6개월 파티션 생성 (월초 배치 권장)
SELECT create_monthly_partitions('daily_price', CURRENT_DATE, CURRENT_DATE + INTERVAL '6 months');
SELECT create_monthly_partitions('daily_return', CURRENT_DATE, CURRENT_DATE + INTERVAL '6 months');
SELECT create_monthly_partitions('simulation_path', CURRENT_DATE, CURRENT_DATE + INTERVAL '6 months');
```

### 파티션 현황 확인

```sql
-- 파티션 목록 및 행 수
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'daily_price_%'
   OR tablename LIKE 'daily_return_%'
   OR tablename LIKE 'simulation_path_%'
ORDER BY tablename;
```

### 오래된 파티션 삭제 (TTL)

```sql
-- 3년 이전 데이터 파티션 삭제 예시
DROP TABLE IF EXISTS daily_price_202201;
DROP TABLE IF EXISTS daily_return_202201;
```

---

## 5. 환경 변수 설정

### Backend (.env)

```bash
# PostgreSQL 연결
DATABASE_URL=postgresql://foresto:password@localhost:5432/foresto_dev

# 엔진 버전 (Phase 1)
ENGINE_VERSION=1.0.0

# Feature Flag
FEATURE_RECOMMENDATION_ENGINE=0
```

### Docker Compose

```yaml
services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: foresto
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: foresto_dev
    volumes:
      - ./db/ddl:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
```

---

## 6. 백업/복구

### 백업

```bash
# 전체 백업
pg_dump -U foresto -d foresto_dev -F c -f backup_$(date +%Y%m%d).dump

# 스키마만 백업
pg_dump -U foresto -d foresto_dev --schema-only -f schema_backup.sql

# 특정 테이블만 백업
pg_dump -U foresto -d foresto_dev -t simulation_run -t simulation_summary -f sim_backup.sql
```

### 복구

```bash
# 전체 복구
pg_restore -U foresto -d foresto_dev -c backup_20260115.dump

# SQL 파일 복구
psql -U foresto -d foresto_dev -f schema_backup.sql
```

---

## 7. 모니터링 쿼리

### 테이블 크기

```sql
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS data_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;
```

### 인덱스 사용 현황

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### 캐시 히트율

```sql
SELECT
    relname,
    heap_blks_read,
    heap_blks_hit,
    ROUND(heap_blks_hit::numeric / NULLIF(heap_blks_hit + heap_blks_read, 0) * 100, 2) AS hit_ratio
FROM pg_statio_user_tables
ORDER BY heap_blks_read DESC;
```

---

## 8. 트러블슈팅

### 파티션 없음 오류

```
ERROR: no partition of relation "daily_price" found for row
```

**해결**: 해당 날짜의 파티션 생성

```sql
SELECT create_monthly_partitions('daily_price', '2027-01-01', '2027-07-01');
```

### 구성비 합계 오류

```
ERROR: Portfolio weight sum exceeds 1.0
```

**해결**: `portfolio_allocation` 테이블의 weight 합이 1.0을 초과하지 않도록 조정

### 연결 오류

```
FATAL: password authentication failed for user "foresto"
```

**해결**:
1. `pg_hba.conf`에서 인증 방식 확인
2. 비밀번호 재설정: `ALTER USER foresto WITH PASSWORD 'new_password';`

---

## 관련 문서

- [Phase 1 백로그](../Foresto_Phase1_작업티켓_백로그.md)
- [API 스냅샷](./api_snapshot_simulation.md)
- [변경 이력](../CHANGELOG_20260115_phase0.md)

---

**검증 담당**: Claude Code
**마지막 업데이트**: 2026-01-15
