# yfinance 데이터 수집 오류 수정 완료

## 문제 상황

관리자 페이지에서 데이터 수집 시 모든 주식이 실패하는 문제:
```
Failed to get ticker '005930.KS' reason: unsupported operand type(s) for -: 'datetime.datetime' and 'str'
No timezone found, symbol may be delisted
```

## 원인

1. **yfinance 버전 문제**: v0.2.32는 datetime 처리에 버그가 있음
2. **datetime 객체 호환성**: `history(start=datetime, end=datetime)` 사용 시 timezone 오류 발생

## 수정 내용

### 1. yfinance 업그레이드
```bash
# 0.2.32 → 0.2.66으로 업그레이드
pip install --upgrade yfinance
```

**수정 파일**: [backend/requirements.txt](backend/requirements.txt)
```diff
- yfinance==0.2.32
+ yfinance>=0.2.66
```

### 2. 데이터 수집 로직 개선

**수정 파일**: [backend/app/data_collector.py](backend/app/data_collector.py)

#### 변경 사항:
- `history(start=datetime, end=datetime)` → `history(period="1y")` 사용
- datetime 객체 대신 문자열 period 파라미터 사용 (1y = 1년)
- None 체크 강화 및 에러 핸들링 개선

#### Before:
```python
end_date = datetime.now()
start_date = end_date - timedelta(days=365)
hist = stock.history(start=start_date, end=end_date)
current_price = hist['Close'].iloc[-1] if not hist.empty else 0
```

#### After:
```python
hist = stock.history(period="1y")
current_price = hist['Close'].iloc[-1] if not hist.empty else None

if current_price is None:
    logger.warning(f"No price data for {ticker}")
    return None
```

### 3. 데이터 로더 서비스 수정

**수정 파일**: [backend/app/services/data_loader.py](backend/app/services/data_loader.py)

채권 및 예적금 로딩 함수에서 반환값에 `"updated"` 키 추가:
```python
result = {"success": 0, "failed": 0, "updated": 0}
```

## 테스트 결과

### 단일 주식 테스트
```bash
✅ 성공!
종목: 삼성전자
현재가: 106,300원
시가총액: 710,730,651,271,168
섹터: Technology
```

### 전체 데이터 수집 테스트
```
=== 수집 결과 ===
stocks: 성공 0, 업데이트 13, 실패 0
etfs: 성공 0, 업데이트 5, 실패 0
bonds: 성공 0, 업데이트 3, 실패 0
deposits: 성공 0, 업데이트 3, 실패 0

=== DB 현황 ===
주식: 13개
ETF: 5개
채권: 3개
예적금: 3개
```

✅ **모든 데이터 수집 성공!**

## 사용 방법

### 1. 웹 UI에서 데이터 수집

1. 로그인: http://localhost:5173/login
2. 관리자 페이지 접속: http://localhost:5173/admin
3. "📦 전체 데이터 수집" 버튼 클릭
4. 1-2분 대기
5. 데이터 현황 확인:
   - 주식: 13개
   - ETF: 5개
   - 채권: 3개
   - 예적금: 3개

### 2. 명령줄에서 데이터 수집

```bash
cd /Users/changrim/KingoPortfolio/backend

# Python 스크립트로 실행
/Users/changrim/KingoPortfolio/venv/bin/python -c "
from app.database import SessionLocal
from app.services.data_loader import DataLoaderService

db = SessionLocal()
try:
    results = DataLoaderService.load_all_data(db)
    print(results)
finally:
    db.close()
"
```

### 3. API로 데이터 수집 (cURL)

```bash
# 1. 로그인
TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=YOUR_EMAIL&password=YOUR_PASSWORD" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. 전체 데이터 수집
curl -X POST "http://127.0.0.1:8000/admin/load-data" \
  -H "Authorization: Bearer $TOKEN"

# 3. 데이터 현황 확인
curl -X GET "http://127.0.0.1:8000/admin/data-status" \
  -H "Authorization: Bearer $TOKEN"
```

## 수집되는 한국 주식 (13개)

1. 삼성전자 (005930.KS)
2. LG전자 (000660.KS)
3. 카카오 (035720.KS)
4. POSCO홀딩스 (005490.KS)
5. 기아 (000270.KS)
6. HMM (011200.KS)
7. 현대모비스 (012330.KS)
8. 삼성물산 (028260.KS)
9. 현대제철 (004020.KS)
10. SK텔레콤 (017670.KS)
11. LG (003550.KS)
12. 신한지주 (055550.KS)
13. 하나금융지주 (086790.KS)

## 수집되는 ETF (5개)

1. KODEX 배당성장 (102110.KS)
2. TIGER 200 (133690.KS)
3. KODEX 200 (122630.KS)
4. CoTrader S&P500 (130680.KS)
5. KODEX 인버스 (114800.KS)

## 주의사항

### yfinance API 제한
- 과도한 요청 시 일시적으로 차단될 수 있음
- 권장: 1시간 간격으로 데이터 수집
- 데이터는 실시간이 아닌 15-20분 지연

### 데이터 업데이트 주기
- **수동 업데이트**: 관리자 페이지에서 버튼 클릭
- **자동 업데이트**: 향후 스케줄러 구현 예정 (매일 오전 9시 자동 수집)

## 트러블슈팅

### 1. "No price data" 경고
일부 종목에서 가격 데이터를 가져올 수 없는 경우:
- 해당 종목이 상장폐지되었을 수 있음
- Yahoo Finance API에서 해당 티커를 지원하지 않을 수 있음
- 나중에 재시도

### 2. 여전히 datetime 에러 발생
```bash
# yfinance 버전 확인
/Users/changrim/KingoPortfolio/venv/bin/pip show yfinance

# 0.2.66 이상이어야 함
# 아니면 수동 업그레이드:
/Users/changrim/KingoPortfolio/venv/bin/pip install --upgrade yfinance
```

### 3. DB 데이터 초기화 (필요시)
```bash
cd /Users/changrim/KingoPortfolio/backend
sqlite3 kingo.db

# 모든 종목 데이터 삭제
DELETE FROM stocks;
DELETE FROM etfs;
DELETE FROM bonds;
DELETE FROM deposit_products;

.exit
```

## 관련 문서

- [DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md) - 전체 데이터 수집 가이드
- [ADMIN_TROUBLESHOOTING.md](ADMIN_TROUBLESHOOTING.md) - 관리자 페이지 트러블슈팅
- [yfinance 공식 문서](https://pypi.org/project/yfinance/)

## 완료 상태

- ✅ yfinance 버전 업그레이드 (0.2.32 → 0.2.66)
- ✅ datetime 처리 로직 수정 (period 파라미터 사용)
- ✅ 데이터 수집 테스트 성공 (주식 13개, ETF 5개)
- ✅ DB 저장 확인 완료
- ✅ 백엔드 API 정상 작동
- ✅ 관리자 페이지 UI 연동 완료

---

**수정일**: 2024-12-20
**수정자**: Claude Code
**버전**: 1.1
