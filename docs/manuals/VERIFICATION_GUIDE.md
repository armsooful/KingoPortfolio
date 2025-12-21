# 데이터 수집 수정 검증 가이드

## 🎯 수정 완료 사항

1. ✅ **yfinance 버전 업그레이드**: 0.2.32 → 0.2.66
2. ✅ **datetime 오류 수정**: `period="1y"` 파라미터 사용
3. ✅ **데이터 수집 성공**: 주식 13개, ETF 5개, 채권 3개, 예적금 3개
4. ✅ **백엔드 서버 실행 중**: http://127.0.0.1:8000
5. ⏳ **프론트엔드 시작 중**: http://localhost:5173

## 📋 검증 단계

### 1단계: 서버 상태 확인

```bash
# 백엔드 상태 확인
curl http://127.0.0.1:8000/health
# 예상 결과: {"status":"healthy"}

# 프론트엔드 확인 (5초 후)
curl http://localhost:5173
# 예상 결과: HTML 응답
```

### 2단계: 웹 UI에서 확인

1. **브라우저 열기**: http://localhost:5173/login

2. **로그인**:
   - 기존 계정으로 로그인
   - 또는 회원가입: http://localhost:5173/signup

3. **관리자 페이지 접속**:
   - 상단 네비게이션에서 "🔧 관리자" 클릭
   - URL: http://localhost:5173/admin

4. **데이터 현황 확인**:
   ```
   📊 현재 데이터 현황
   주식: 13개
   ETF: 5개
   채권: 3개
   예적금: 3개
   ```

### 3단계: 데이터 재수집 테스트 (선택)

관리자 페이지에서:

1. **"📈 주식 데이터만 수집"** 클릭
2. 확인 팝업에서 "확인"
3. 1-2분 대기
4. 결과 확인:
   ```
   ✅ 주식 데이터 적재 완료
   stocks: 성공 0, 업데이트 13, 실패 0
   ```

### 4단계: 브라우저 개발자 도구 확인

1. **개발자 도구 열기**: `F12` (Windows) 또는 `Cmd+Option+I` (Mac)

2. **Console 탭 확인**:
   - ✅ 에러 없음 (React Router 경고 제거됨)
   - ✅ 데이터 로딩 성공 메시지

3. **Network 탭 확인**:
   - `GET /admin/data-status` → Status: 200 OK
   - Response:
     ```json
     {
       "stocks": 13,
       "etfs": 5,
       "bonds": 3,
       "deposits": 3,
       "total": 24
     }
     ```

## 🔍 예상 결과

### 관리자 페이지 화면

```
🔧 관리자 콘솔
종목 정보 수집 및 데이터 관리

📊 현재 데이터 현황
┌────────┬────────┬────────┬────────┐
│  13    │   5    │   3    │   3    │
│ 주식   │  ETF   │  채권  │ 예적금 │
└────────┴────────┴────────┴────────┘

🔄 데이터 수집
[📦 전체 데이터 수집]
[📈 주식 데이터만 수집]
[📊 ETF 데이터만 수집]

💡 yfinance API로 실시간 종목 정보를 수집합니다 (1-2분 소요)
```

### 데이터 수집 성공 메시지

```
✅ 데이터 적재 완료
stocks: 성공 0, 업데이트 13, 실패 0
etfs: 성공 0, 업데이트 5, 실패 0
bonds: 성공 0, 업데이트 3, 실패 0
deposits: 성공 0, 업데이트 3, 실패 0
```

## ❌ 문제 발생 시

### 문제 1: "데이터 로딩 중..." 계속 표시

**해결**:
```bash
# 백엔드 로그 확인
tail -f /tmp/claude/-Users-changrim-KingoPortfolio/tasks/b1b5792.output

# 백엔드 재시작
pkill -f uvicorn
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 문제 2: 데이터 수집 실패

**원인**: yfinance 버전 문제

**해결**:
```bash
# yfinance 버전 확인
/Users/changrim/KingoPortfolio/venv/bin/pip show yfinance
# Version: 0.2.66 이상이어야 함

# 버전이 낮으면 업그레이드
/Users/changrim/KingoPortfolio/venv/bin/pip install --upgrade yfinance
```

### 문제 3: 401 Unauthorized

**원인**: JWT 토큰 만료

**해결**:
1. 로그아웃
2. 재로그인

### 문제 4: CORS 에러

**확인**:
브라우저 Console에서:
```
Access to XMLHttpRequest at 'http://127.0.0.1:8000/...' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**해결**:
[backend/app/main.py](backend/app/main.py)의 CORS 설정 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 명령줄 테스트

### 단일 주식 데이터 테스트

```bash
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/python -c "
from app.data_collector import DataCollector

result = DataCollector.fetch_stock_data('005930', '삼성전자')
if result:
    print(f'✅ {result[\"name\"]}: {result[\"current_price\"]:,.0f}원')
else:
    print('❌ 실패')
"
```

**예상 출력**:
```
✅ 삼성전자: 106,300원
```

### 전체 데이터 수집 테스트

```bash
/Users/changrim/KingoPortfolio/venv/bin/python -c "
from app.database import SessionLocal
from app.services.data_loader import DataLoaderService
from app.models.securities import Stock, ETF, Bond, DepositProduct

db = SessionLocal()
try:
    # 데이터 수집
    results = DataLoaderService.load_all_data(db)

    # 결과 출력
    print('=== 수집 결과 ===')
    for category, result in results.items():
        print(f'{category}: 성공 {result[\"success\"]}, 업데이트 {result[\"updated\"]}, 실패 {result.get(\"failed\", 0)}')

    # DB 현황 확인
    print('\\n=== DB 현황 ===')
    print(f'주식: {db.query(Stock).count()}개')
    print(f'ETF: {db.query(ETF).count()}개')
    print(f'채권: {db.query(Bond).count()}개')
    print(f'예적금: {db.query(DepositProduct).count()}개')
finally:
    db.close()
"
```

**예상 출력**:
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

## 📊 DB 직접 확인

```bash
cd /Users/changrim/KingoPortfolio/backend
sqlite3 kingo.db

-- 주식 데이터 확인
SELECT name, current_price, last_updated FROM stocks LIMIT 5;

-- 전체 카운트
SELECT
  (SELECT COUNT(*) FROM stocks) as 주식,
  (SELECT COUNT(*) FROM etfs) as ETF,
  (SELECT COUNT(*) FROM bonds) as 채권,
  (SELECT COUNT(*) FROM deposit_products) as 예적금;

.exit
```

## 🎉 성공 기준

다음 조건이 모두 만족되면 **수정 완료**:

- ✅ 백엔드 `/health` 응답 정상
- ✅ 관리자 페이지 접속 가능
- ✅ 데이터 현황: 주식 13개, ETF 5개, 채권 3개, 예적금 3개
- ✅ 데이터 수집 버튼 클릭 시 성공 메시지 표시
- ✅ 브라우저 Console에 에러 없음
- ✅ Network 탭에서 API 요청 200 OK

## 📚 관련 문서

- [YFINANCE_FIX_SUMMARY.md](YFINANCE_FIX_SUMMARY.md) - 수정 내용 상세
- [DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md) - 데이터 수집 가이드
- [ADMIN_TROUBLESHOOTING.md](ADMIN_TROUBLESHOOTING.md) - 트러블슈팅

---

**작성일**: 2024-12-20
**버전**: 1.0
