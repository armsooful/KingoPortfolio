# API 기반 종목 정보 수집 & DB 적재 가이드
최초작성일자: 2025-12-19
최종수정일자: 2026-01-18

## 개요

KingoPortfolio는 yfinance API를 사용하여 한국 주식 및 ETF 정보를 실시간으로 수집하고 데이터베이스에 저장합니다.

## 시스템 아키텍처

```
┌─────────────────┐
│  yfinance API   │ ← 실시간 주식/ETF 데이터
└────────┬────────┘
         │
         ↓
┌────────────────────┐
│  DataCollector     │ ← 데이터 수집
│  DataClassifier    │ ← 투자성향 분류
└────────┬───────────┘
         │
         ↓
┌────────────────────┐
│  DataLoaderService │ ← DB 적재 로직
└────────┬───────────┘
         │
         ↓
┌────────────────────┐
│  PostgreSQL/SQLite │ ← 데이터 저장
│  - stocks          │
│  - etfs            │
│  - bonds           │
│  - deposit_products│
└────────────────────┘
```

## 수집 대상 종목

### 한국 주식 (13개)
- 삼성전자 (005930.KS)
- LG전자 (066570.KS)
- 카카오 (035720.KS)
- POSCO홀딩스 (005490.KS)
- 기아 (000270.KS)
- HMM (011200.KS)
- 현대모비스 (012330.KS)
- 삼성물산 (028260.KS)
- POSCO스틸리온 (003670.KS)
- SK텔레콤 (017670.KS)
- LG (003550.KS)
- 신한지주 (055550.KS)
- 하나금융지주 (086790.KS)

### 한국 ETF (5개)
- KODEX 배당성장 (161510.KS)
- TIGER 200 (102110.KS)
- KODEX 200 (069500.KS)
- KOTRADER S&P500 (360200.KS)
- KODEX 인버스 (114800.KS)

### 채권 & 예적금
- 수동 입력 데이터 (API 없음)
- 채권 3종, 예적금 3종

## 수집 데이터 필드

### 주식 (Stock)
```python
{
    "ticker": "005930.KS",           # 종목 코드
    "name": "삼성전자",               # 종목명
    "sector": "Technology",          # 섹터
    "market": "KOSPI",               # 시장
    "current_price": 71000.0,        # 현재가
    "market_cap": 425000000,         # 시가총액 (백만원)
    "pe_ratio": 15.2,                # PER
    "pb_ratio": 1.3,                 # PBR
    "dividend_yield": 2.5,           # 배당수익률 (%)
    "ytd_return": 15.3,              # 연초대비 수익률 (%)
    "one_year_return": 22.1,         # 1년 수익률 (%)
    "risk_level": "medium",          # 위험도 (low/medium/high)
    "investment_type": "moderate",   # 투자성향
    "category": "기술주",             # 카테고리
    "last_updated": "2025-12-19..."  # 최종 업데이트
}
```

### ETF
```python
{
    "ticker": "069500.KS",
    "name": "KODEX 200",
    "etf_type": "equity",            # equity/bond/commodity/reits
    "current_price": 35000.0,
    "aum": 5000000,                  # 순자산 (백만원)
    "expense_ratio": 0.15,           # 보수 (%)
    "ytd_return": 12.5,
    "one_year_return": 18.2,
    "risk_level": "medium"
}
```

## 데이터 수집 방법

### 1. 관리자 페이지 UI (권장)

#### 접근 방법
```
1. 로그인: http://localhost:5173/login
2. 관리자 페이지: http://localhost:5173/admin
```

#### 기능
- **전체 데이터 수집**: 주식 + ETF + 채권 + 예적금
- **주식만 수집**: 13개 주식 정보만 업데이트
- **ETF만 수집**: 5개 ETF 정보만 업데이트
- **DB 현황 확인**: 현재 저장된 종목 수 확인

#### 사용 예시
```
1. "전체 데이터 수집" 버튼 클릭
2. 확인 팝업에서 "확인"
3. 1-2분 대기
4. 결과 확인:
   - 주식: 성공 13, 업데이트 0, 실패 0
   - ETF: 성공 5, 업데이트 0, 실패 0
   - 채권: 성공 3, 업데이트 0
   - 예적금: 성공 3, 업데이트 0
```

### 2. API 직접 호출

#### 전체 데이터 수집
```bash
TOKEN="your-jwt-token"

curl -X POST "http://127.0.0.1:8000/admin/load-data" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**응답 예시**:
```json
{
  "status": "success",
  "message": "데이터 적재 완료",
  "results": {
    "stocks": {
      "success": 13,
      "failed": 0,
      "updated": 0
    },
    "etfs": {
      "success": 5,
      "failed": 0,
      "updated": 0
    },
    "bonds": {
      "success": 3,
      "failed": 0,
      "updated": 0
    },
    "deposits": {
      "success": 3,
      "failed": 0,
      "updated": 0
    }
  }
}
```

#### 주식만 수집
```bash
curl -X POST "http://127.0.0.1:8000/admin/load-stocks" \
  -H "Authorization: Bearer $TOKEN"
```

#### ETF만 수집
```bash
curl -X POST "http://127.0.0.1:8000/admin/load-etfs" \
  -H "Authorization: Bearer $TOKEN"
```

#### DB 현황 확인
```bash
curl -X GET "http://127.0.0.1:8000/admin/data-status" \
  -H "Authorization: Bearer $TOKEN"
```

**응답**:
```json
{
  "stocks": 13,
  "etfs": 5,
  "bonds": 3,
  "deposits": 3,
  "total": 24
}
```

### 3. Python 스크립트로 수집

```python
# backend/scripts/update_data.py
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.data_loader import DataLoaderService

def main():
    db = SessionLocal()
    try:
        print("데이터 수집 시작...")
        results = DataLoaderService.load_all_data(db)

        print("\n=== 수집 결과 ===")
        for category, result in results.items():
            print(f"{category}: 성공 {result['success']}, "
                  f"업데이트 {result['updated']}, "
                  f"실패 {result['failed']}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

실행:
```bash
cd /Users/changrim/KingoPortfolio/backend
python scripts/update_data.py
```

## 데이터 분류 로직

### 위험도 분류
```python
def classify_risk(pe_ratio, dividend_yield):
    if pe_ratio and pe_ratio < 15 and dividend_yield and dividend_yield > 3:
        return "low"      # 저위험: 낮은 PER + 높은 배당
    elif pe_ratio and pe_ratio > 30:
        return "high"     # 고위험: 높은 PER
    else:
        return "medium"   # 중위험: 나머지
```

### 투자성향 매핑
```python
def classify_investment_type(risk_level, dividend_yield):
    types = []

    if risk_level == "low":
        types.append("conservative")  # 보수형

    if risk_level == "medium":
        types.append("moderate")      # 중도형

    if risk_level == "high" or (dividend_yield and dividend_yield < 1):
        types.append("aggressive")    # 적극형

    return types
```

### 카테고리 분류
```python
def classify_category(name, sector):
    if "배당" in name or "리츠" in name:
        return "배당주"
    elif "삼성" in name or "LG" in name or "카카오" in name:
        return "기술주"
    elif "금융" in name or "은행" in name:
        return "금융주"
    elif "POSCO" in name or "철강" in name:
        return "산업주"
    else:
        return "기타"
```

## 데이터 업데이트 주기

### 수동 업데이트
- 관리자 페이지에서 버튼 클릭
- 즉시 최신 데이터로 업데이트

### 자동 업데이트 (향후 구현)
```python
# backend/app/scheduler.py (예정)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=9, minute=0)  # 매일 오전 9시
async def update_stock_data():
    db = SessionLocal()
    try:
        DataLoaderService.load_korean_stocks(db)
        DataLoaderService.load_etfs(db)
    finally:
        db.close()
```

## 데이터 활용

### 추천 시스템
```python
# 투자성향별 추천 종목 조회
from app.db_recommendation_engine import DBRecommendationEngine

# 보수형 투자자용 주식 추천
stocks = DBRecommendationEngine.get_recommended_stocks(
    db,
    investment_type="conservative",
    limit=3
)

# ETF 추천
etfs = DBRecommendationEngine.get_recommended_etfs(
    db,
    investment_type="moderate",
    limit=2
)
```

### API 엔드포인트
```bash
# 진단 후 추천 상품 조회
GET /diagnosis/me/products
Authorization: Bearer {token}

# 응답
{
  "diagnosis_id": "uuid",
  "investment_type": "moderate",
  "recommended_stocks": [
    {
      "ticker": "005930.KS",
      "name": "삼성전자",
      "current_price": 71000,
      "dividend_yield": 2.5,
      "expected_return": "8-12%"
    }
  ],
  "recommended_etfs": [...],
  "recommended_bonds": [...],
  "recommended_deposits": [...]
}
```

## 트러블슈팅

### 1. "No module named 'yfinance'"
```bash
pip install yfinance==0.2.32
```

### 2. 데이터 수집 실패 (일부 종목)
**원인**:
- yfinance API 제한
- 잘못된 티커 코드
- 네트워크 문제

**해결**:
- 개별 종목 재수집
- 로그 확인: 백엔드 터미널에서 에러 메시지 확인

### 3. "401 Unauthorized"
**원인**: JWT 토큰 만료

**해결**:
```bash
# 재로그인
POST /token
{
  "username": "user@example.com",
  "password": "password"
}
```

### 4. 데이터가 업데이트되지 않음
**확인**:
```python
# DB에서 직접 확인
from app.database import SessionLocal
from app.models.securities import Stock

db = SessionLocal()
stock = db.query(Stock).filter(Stock.ticker == "005930.KS").first()
print(f"Last updated: {stock.last_updated}")
```

## API 제한 사항

### yfinance
- **요청 제한**: 명시적 제한 없음 (과도한 호출 시 차단 가능)
- **권장**: 1회 수집 후 최소 1시간 간격
- **데이터 지연**: 실시간이 아닌 15-20분 지연 데이터

### 대안 API (향후)
- **한국거래소 API**: 실시간 데이터 (인증 필요)
- **네이버 금융**: 웹 스크래핑
- **Investing.com API**: 글로벌 데이터

## 데이터베이스 스키마

### stocks 테이블
```sql
CREATE TABLE stocks (
    id TEXT PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50),
    market VARCHAR(20),
    current_price FLOAT,
    market_cap BIGINT,
    pe_ratio FLOAT,
    pb_ratio FLOAT,
    dividend_yield FLOAT,
    ytd_return FLOAT,
    one_year_return FLOAT,
    risk_level VARCHAR(20),
    investment_type VARCHAR(100),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### etfs 테이블
```sql
CREATE TABLE etfs (
    id TEXT PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    etf_type VARCHAR(20),
    current_price FLOAT,
    aum BIGINT,
    expense_ratio FLOAT,
    ytd_return FLOAT,
    one_year_return FLOAT,
    risk_level VARCHAR(20),
    investment_type VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 모니터링

### 수집 성공률 확인
```sql
-- 최근 업데이트된 종목
SELECT name, last_updated
FROM stocks
ORDER BY last_updated DESC
LIMIT 10;

-- 업데이트 실패 종목 (24시간 이상 미업데이트)
SELECT name, last_updated
FROM stocks
WHERE last_updated < datetime('now', '-24 hours');
```

### 로그 확인
```bash
# 백엔드 서버 로그
tail -f backend.log | grep "DataCollector"
```

## 참고 자료

- [yfinance 공식 문서](https://pypi.org/project/yfinance/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [FastAPI 백그라운드 작업](https://fastapi.tiangolo.com/tutorial/background-tasks/)

---

**작성일**: 2025-12-19
**버전**: 1.0
