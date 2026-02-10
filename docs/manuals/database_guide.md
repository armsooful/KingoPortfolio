# 📊 데이터베이스 조회 가이드
최초작성일자: 2025-12-20
최종수정일자: 2026-01-18

## 데이터베이스 위치

**파일 경로**: `/Users/changrim/KingoPortfolio/backend/kingo.db`

**타입**: SQLite 3.x

## 🚀 빠른 조회 (편리한 스크립트)

### 1. 모든 데이터 한눈에 보기
```bash
./view_db.sh all
```

**출력 예시**:
```
📊 전체 데이터 현황
주식: 13개, ETF: 5개, 채권: 3개, 예적금: 3개, 사용자: 26명

📈 주식 (상위 5개)
티커     종목명    현재가     시총(조)
005930  삼성전자   106,300   710
000660  LG전자    547,000   377
...

📊 ETF (전체)
티커     ETF명              현재가
102110  KODEX 배당성장      57,170
...
```

### 2. 개별 테이블 조회

```bash
# 주식 데이터 (13개)
./view_db.sh stocks

# ETF 데이터 (5개)
./view_db.sh etfs

# 채권 데이터 (3개)
./view_db.sh bonds

# 예적금 데이터 (3개)
./view_db.sh deposits

# 사용자 목록
./view_db.sh users

# 데이터 개수만 확인
./view_db.sh count
```

## 📋 저장된 테이블 목록

1. **stocks** - 주식 데이터 (13개)
2. **etfs** - ETF 데이터 (5개)
3. **bonds** - 채권 데이터 (3개)
4. **deposit_products** - 예적금 상품 (3개)
5. **users** - 사용자 계정
6. **diagnoses** - 투자성향 진단 결과
7. **diagnosis_answers** - 진단 답변 내역
8. **survey_questions** - 설문 문항
9. **product_recommendations** - 추천 상품 (미사용)

## 🔍 SQLite CLI로 직접 조회

### 데이터베이스 접속
```bash
cd /Users/changrim/KingoPortfolio/backend
sqlite3 kingo.db
```

### 기본 명령어

```sql
-- 테이블 목록 보기
.tables

-- 테이블 구조 확인
.schema stocks

-- 보기 좋은 출력 형식
.mode box
.headers on

-- 주식 데이터 조회
SELECT * FROM stocks LIMIT 5;

-- ETF 데이터 조회
SELECT * FROM etfs;

-- 특정 종목 검색
SELECT * FROM stocks WHERE name LIKE '%삼성%';

-- 데이터 개수 확인
SELECT COUNT(*) FROM stocks;

-- 종료
.exit
```

### 유용한 쿼리

#### 1. 시가총액 상위 5개 주식
```sql
SELECT
  ticker,
  name,
  CAST(current_price as INT) as 현재가,
  CAST(market_cap/1000000000000 as INT) as 시총조
FROM stocks
ORDER BY market_cap DESC
LIMIT 5;
```

#### 2. 배당 수익률 높은 주식
```sql
SELECT
  name,
  dividend_yield,
  risk_level
FROM stocks
WHERE dividend_yield IS NOT NULL
ORDER BY dividend_yield DESC;
```

#### 3. 투자성향별 종목 수
```sql
SELECT
  investment_type,
  COUNT(*) as 종목수
FROM stocks
GROUP BY investment_type;
```

#### 4. 연초 대비 수익률 순위
```sql
SELECT
  name,
  ROUND(ytd_return, 2) as '연초수익률(%)'
FROM stocks
WHERE ytd_return IS NOT NULL
ORDER BY ytd_return DESC;
```

#### 5. 모든 금융상품 개수
```sql
SELECT
  (SELECT COUNT(*) FROM stocks) as 주식,
  (SELECT COUNT(*) FROM etfs) as ETF,
  (SELECT COUNT(*) FROM bonds) as 채권,
  (SELECT COUNT(*) FROM deposit_products) as 예적금;
```

## 📊 현재 저장된 데이터

### 주식 (13개)
| 티커 | 종목명 | 현재가 | 시가총액(조) | 카테고리 |
|------|--------|--------|--------------|----------|
| 005930 | 삼성전자 | 106,300 | 710 | 기술주 |
| 000660 | LG전자 | 547,000 | 377 | 기술주 |
| 000270 | 기아 | 121,000 | 46 | 기타주 |
| 028260 | 삼성물산 | 249,000 | 40 | 기타주 |
| 055550 | 신한지주 | 77,300 | 37 | 기타주 |
| 012330 | 현대모비스 | 366,500 | 32 | 기타주 |
| 035720 | 카카오 | 58,200 | 25 | 기술주 |
| 086790 | 하나금융지주 | 92,400 | 25 | 금융주 |
| 005490 | POSCO홀딩스 | 302,500 | 22 | 기타주 |
| 011200 | HMM | 20,550 | 19 | 기타주 |
| 003550 | LG | 81,700 | 12 | 기타주 |
| 017670 | SK텔레콤 | 53,500 | 11 | 기타주 |
| 004020 | 현대제철 | 30,550 | 4 | 기타주 |

### ETF (5개)
| 티커 | ETF명 | 현재가 | 연초수익률 |
|------|-------|--------|------------|
| 102110 | KODEX 배당성장 | 57,170 | 80.84% |
| 133690 | TIGER 200 | 164,115 | 20.66% |
| 122630 | KODEX 200 | 42,100 | 196.79% |
| 130680 | CoTrader S&P500 | 3,730 | -11.72% |
| 114800 | KODEX 인버스 | 2,600 | -45.32% |

### 채권 (3개)
| 채권명 | 금리 | 만기 | 신용등급 | 위험도 |
|--------|------|------|----------|--------|
| 국고채 3년물 | 3.5% | 3년 | AAA | low |
| 회사채(A등급) 펀드 | 4.2% | 3년 | A | low |
| 하이일드 채권 펀드 | 6.2% | 3년 | BBB | high |

### 예적금 (3개)
| 상품명 | 은행 | 금리 | 최소가입액 |
|--------|------|------|------------|
| SC제일은행 CMA | SC제일은행 | 3.8% | 0원 |
| 국민은행 정기예금 | 국민은행 | 3.5% | 100,000원 |
| NH투자증권 CMA | NH투자증권 | 4.2% | 0원 |

## 🛠️ 데이터베이스 관리

### 백업
```bash
# 백업 생성
cp backend/kingo.db backend/kingo_backup_$(date +%Y%m%d).db

# 예시: kingo_backup_20241220.db
```

### 복원
```bash
# 백업에서 복원
cp backend/kingo_backup_20241220.db backend/kingo.db
```

### 데이터 초기화 (주의!)
```bash
sqlite3 backend/kingo.db << 'EOF'
DELETE FROM stocks;
DELETE FROM etfs;
DELETE FROM bonds;
DELETE FROM deposit_products;
EOF
```

**초기화 후 데이터 재수집**:
```bash
# 관리자 페이지에서 "전체 데이터 수집" 버튼 클릭
# 또는
cd backend
/Users/changrim/KingoPortfolio/venv/bin/python -c "
from app.database import SessionLocal
from app.services.data_loader import DataLoaderService
db = SessionLocal()
try:
    DataLoaderService.load_all_data(db)
finally:
    db.close()
"
```

## 🔗 관련 도구

### 1. SQLite Browser (GUI)
무료 SQLite GUI 도구:
- **다운로드**: https://sqlitebrowser.org/
- **설치 후**: `File > Open Database` → `kingo.db` 선택
- **기능**: 테이블 조회, 편집, SQL 실행

### 2. VSCode Extension
VSCode에서 SQLite 파일 보기:
- **확장**: "SQLite Viewer" 또는 "SQLite"
- **사용**: `.db` 파일 클릭하면 자동으로 보기

### 3. DataGrip (유료)
JetBrains의 강력한 데이터베이스 도구

## 📚 관련 문서

- [20251219_data_collection_guide.md](data_collection_guide.md) - 데이터 수집 방법
- [20251220_quick_start.md](quick_start.md) - 빠른 시작 가이드
- [README_수정완료.md](../architecture/feature_overview.md) - 시스템 개요

## 💡 팁

### 1. 데이터 최신화
```bash
# 관리자 페이지에서 정기적으로 "전체 데이터 수집" 클릭
# 권장: 1시간 간격 (yfinance API 제한 고려)
```

### 2. 사용자 데이터 확인
```sql
-- 최근 진단 기록
SELECT u.email, d.investment_type, d.created_at
FROM diagnoses d
JOIN users u ON d.user_id = u.id
ORDER BY d.created_at DESC
LIMIT 10;
```

### 3. 성능 확인
```sql
-- 인덱스 확인
SELECT * FROM sqlite_master WHERE type = 'index';

-- 테이블 크기
SELECT
  name,
  COUNT(*) as rows
FROM (
  SELECT 'stocks' as name, COUNT(*) as cnt FROM stocks
  UNION ALL
  SELECT 'etfs', COUNT(*) FROM etfs
  UNION ALL
  SELECT 'users', COUNT(*) FROM users
  UNION ALL
  SELECT 'diagnoses', COUNT(*) FROM diagnoses
);
```

---

**작성일**: 2024-12-20
**버전**: 1.0
**데이터베이스**: SQLite 3.x
**위치**: `/Users/changrim/KingoPortfolio/backend/kingo.db`
