# Alpha Vantage 데이터 적재 가이드

## 📊 Alpha Vantage란?

Alpha Vantage는 주식, ETF, 외환, 암호화폐 등 다양한 금융 데이터를 무료로 제공하는 API 플랫폼입니다.

### 주요 기능
- 실시간 & 과거 시세 데이터
- 재무제표 (손익계산서, 재무상태표, 현금흐름표)
- 기술적 지표 60+개
- 미국 및 글로벌 주식 지원

### 제한사항
- **무료 플랜**: 25 requests/day, 5 requests/minute
- Rate limit: 약 12초 간격으로 요청 필요

---

## 🔑 API 키 발급

1. [Alpha Vantage 홈페이지](https://www.alphavantage.co/support/#api-key) 접속
2. 이메일 주소 입력 후 무료 API 키 발급
3. 발급받은 API 키를 `.env` 파일에 저장

```bash
# backend/.env
ALPHA_VANTAGE_API_KEY=your-api-key-here
```

---

## 📂 데이터 모델

### 1. AlphaVantageStock (미국 주식)
- 주식 시세 및 기업 정보
- PER, PBR, 배당수익률 등 재무 지표
- 52주 최고/최저가, 이동평균선

### 2. AlphaVantageFinancials (재무제표)
- 손익계산서: 매출, 영업이익, 순이익, EPS
- 재무상태표: 총자산, 총부채, 자본
- 현금흐름표: 영업/투자/재무 현금흐름
- 자동 계산 비율: ROE, ROA, 부채비율, 순이익률

### 3. AlphaVantageETF (미국 ETF)
- ETF 시세 및 운용 정보
- AUM (운용자산), 운용수수료
- 수익률 데이터

### 4. AlphaVantageTimeSeries (시계열 데이터)
- 일별 OHLCV 데이터
- 최근 100일 또는 전체 20년

---

## 🚀 사용 방법

### 1. 관리자 페이지에서 데이터 수집

#### 방법 A: 전체 수집
```
1. 로그인 후 관리자 페이지 접속
2. "Alpha Vantage" 섹션으로 스크롤
3. "🇺🇸 미국 주식 전체 수집" 버튼 클릭
```

**주의**: 인기 종목 20개를 수집하므로 약 5-10분 소요 (12초 간격)

#### 방법 B: 특정 종목 수집
```
1. "특정 종목 검색 & 적재" 입력창에 심볼 입력 (예: AAPL)
2. "📈 시세 수집" 버튼 클릭: 현재가 + 기업 정보 수집
3. "📊 재무제표 수집" 버튼 클릭: 재무제표 수집
```

---

### 2. API로 직접 호출

#### 전체 미국 주식 수집
```bash
POST http://localhost:8000/admin/alpha-vantage/load-all-stocks
Authorization: Bearer {token}
```

#### 특정 주식 수집
```bash
POST http://localhost:8000/admin/alpha-vantage/load-stock/AAPL
Authorization: Bearer {token}
```

#### 재무제표 수집
```bash
POST http://localhost:8000/admin/alpha-vantage/load-financials/AAPL
Authorization: Bearer {token}
```

#### 수집된 데이터 조회
```bash
GET http://localhost:8000/admin/alpha-vantage/stocks
Authorization: Bearer {token}
```

#### 재무제표 조회
```bash
GET http://localhost:8000/admin/alpha-vantage/financials/AAPL
Authorization: Bearer {token}
```

#### 데이터 통계
```bash
GET http://localhost:8000/admin/alpha-vantage/data-status
Authorization: Bearer {token}
```

---

## 📋 수집 가능한 주식 목록

### 기술주 (Tech Giants)
- AAPL: Apple Inc.
- MSFT: Microsoft Corporation
- GOOGL: Alphabet Inc. Class A
- AMZN: Amazon.com Inc.
- META: Meta Platforms Inc.
- NVDA: NVIDIA Corporation
- TSLA: Tesla Inc.

### 금융
- JPM: JPMorgan Chase & Co.
- BAC: Bank of America Corp
- WFC: Wells Fargo & Company

### 헬스케어
- JNJ: Johnson & Johnson
- UNH: UnitedHealth Group Inc.
- PFE: Pfizer Inc.

### 소비재
- KO: The Coca-Cola Company
- PEP: PepsiCo Inc.
- WMT: Walmart Inc.

### 산업
- BA: Boeing Company
- CAT: Caterpillar Inc.

### 에너지
- XOM: Exxon Mobil Corporation
- CVX: Chevron Corporation

### ETF
- SPY: SPDR S&P 500 ETF Trust
- QQQ: Invesco QQQ Trust
- DIA: SPDR Dow Jones Industrial Average ETF
- IWM: iShares Russell 2000 ETF
- VTI: Vanguard Total Stock Market ETF

---

## ⚠️ 주의사항

### Rate Limiting
- 무료 플랜: 25 requests/day, 5 requests/minute
- 전체 수집 시 12초 간격으로 자동 대기
- 하루 25개 종목만 수집 가능

### API 키 관리
- API 키는 절대 GitHub에 업로드하지 마세요
- `.env` 파일을 `.gitignore`에 추가
- 프로덕션에서는 환경변수로 설정

### 데이터 갱신
- 실시간 데이터가 아닌 15-20분 지연 데이터
- 재무제표는 분기/연간 단위로 업데이트
- 매일 최신 데이터로 갱신 권장

---

## 🛠️ 트러블슈팅

### 1. "Alpha Vantage API key가 설정되지 않았습니다" 오류
```bash
# .env 파일 확인
cat backend/.env

# API 키가 없으면 추가
echo "ALPHA_VANTAGE_API_KEY=your-key-here" >> backend/.env

# 서버 재시작
uvicorn app.main:app --reload
```

### 2. Rate Limit 초과
```json
{
  "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute..."
}
```

**해결책**:
- 무료 플랜은 하루 25개 종목 제한
- 다음 날까지 기다리거나 유료 플랜 구독

### 3. 종목 심볼을 찾을 수 없음
```json
{
  "Error Message": "Invalid API call..."
}
```

**해결책**:
- 정확한 심볼 확인 (예: AAPL, MSFT)
- [Yahoo Finance](https://finance.yahoo.com/)에서 심볼 검색

---

## 📚 참고 자료

- [Alpha Vantage 공식 문서](https://www.alphavantage.co/documentation/)
- [Alpha Vantage API Explorer](https://www.alphavantage.co/query?)
- [Python alpha_vantage 라이브러리](https://github.com/RomelTorres/alpha_vantage)

---

## 💡 Tips

### 효율적인 데이터 수집
1. **선택적 수집**: 필요한 종목만 수집
2. **스케줄링**: 매일 특정 시간에 자동 수집 (cron job)
3. **캐싱**: DB에 저장된 데이터 재사용

### 재무 분석 활용
- ROE (자기자본이익률): 15% 이상이 우수
- ROA (총자산이익률): 5% 이상이 우수
- 부채비율: 100% 이하가 안정적
- 순이익률: 10% 이상이 우수

### 포트폴리오 구성
- 미국 주식으로 글로벌 분산 투자
- S&P 500 ETF (SPY) 활용
- 기술주 + 안정주 조합
