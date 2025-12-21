# 관리자 페이지 트러블슈팅 가이드

## 🔍 정상 작동 확인 방법

### 1. 브라우저 개발자 도구로 확인

#### 단계별 확인
1. **개발자 도구 열기**
   - Windows/Linux: `F12` 또는 `Ctrl + Shift + I`
   - Mac: `Cmd + Option + I`

2. **Network 탭 확인**
   - 개발자 도구에서 "Network" 탭 선택
   - 페이지 새로고침 (`Cmd/Ctrl + R`)
   - `data-status` 요청 찾기

3. **요청 상태 확인**
   ```
   GET http://127.0.0.1:8000/admin/data-status
   Status: 200 OK (정상)
   Status: 401 Unauthorized (로그인 필요)
   Status: 500 Internal Server Error (서버 오류)
   ```

4. **응답 데이터 확인**
   - `data-status` 요청 클릭
   - "Response" 탭 선택
   - 다음과 같은 JSON이 보여야 함:
   ```json
   {
     "stocks": 0,
     "etfs": 0,
     "bonds": 0,
     "deposits": 0,
     "total": 0
   }
   ```

#### Console 탭 확인
1. 개발자 도구의 "Console" 탭 선택
2. 에러 메시지 확인:
   ```javascript
   // 정상: 에러 없음

   // 에러 예시:
   Failed to fetch data status: AxiosError: Network Error
   Failed to fetch data status: Request failed with status code 401
   ```

---

### 2. 백엔드 서버 로그 확인

#### 터미널에서 확인
백엔드 서버가 실행 중인 터미널을 확인:

```bash
# 정상 요청 로그
INFO:     127.0.0.1:50000 - "GET /admin/data-status HTTP/1.1" 200 OK

# 에러 로그
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  ...
```

---

### 3. 직접 API 테스트

#### cURL로 테스트
```bash
# 1. 로그인하여 토큰 받기
TOKEN=$(curl -X POST "http://127.0.0.1:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test1234" \
  2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. 데이터 현황 조회
curl -X GET "http://127.0.0.1:8000/admin/data-status" \
  -H "Authorization: Bearer $TOKEN"

# 정상 응답 예시:
# {"stocks":0,"etfs":0,"bonds":0,"deposits":0,"total":0}
```

#### 브라우저에서 직접 테스트
Swagger UI 사용:
```
1. http://127.0.0.1:8000/docs 접속
2. "Admin" 섹션 확장
3. "GET /admin/data-status" 클릭
4. "Try it out" 클릭
5. "Execute" 클릭
6. 응답 확인
```

---

## 🐛 일반적인 문제 및 해결 방법

### 문제 1: "데이터 로딩 중..." 계속 표시

#### 원인
- 백엔드 서버가 실행되지 않음
- 네트워크 에러
- CORS 문제

#### 확인 방법
```bash
# 백엔드 서버 상태 확인
curl http://127.0.0.1:8000/health

# 정상: {"status":"healthy"}
# 에러: curl: (7) Failed to connect to 127.0.0.1 port 8000
```

#### 해결 방법
```bash
# 백엔드 서버 시작
cd /Users/changrim/KingoPortfolio/backend
source /Users/changrim/KingoPortfolio/venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

### 문제 2: "401 Unauthorized" 에러

#### 원인
- JWT 토큰이 만료됨
- 로그인하지 않음

#### 확인 방법
브라우저 개발자 도구 > Console:
```javascript
localStorage.getItem('access_token')
// null이면 로그인 안 됨
// 값이 있으면 토큰 존재
```

#### 해결 방법
1. 로그아웃 후 재로그인
2. 또는 `/login` 페이지로 이동하여 로그인

---

### 문제 3: DB에 데이터가 0개

#### 원인
- 데이터를 아직 수집하지 않음 (정상)
- 데이터 수집 실패

#### 확인 방법
```bash
# SQLite DB 직접 확인
cd /Users/changrim/KingoPortfolio/backend
sqlite3 kingo.db

# SQL 실행
SELECT COUNT(*) FROM stocks;
SELECT COUNT(*) FROM etfs;
SELECT COUNT(*) FROM bonds;
SELECT COUNT(*) FROM deposit_products;

# 종료
.exit
```

#### 해결 방법
관리자 페이지에서 "전체 데이터 수집" 버튼 클릭

---

### 문제 4: 데이터 수집 실패

#### 원인
- yfinance API 에러
- 네트워크 문제
- 잘못된 티커 코드

#### 확인 방법
백엔드 터미널 로그 확인:
```
ERROR: Error processing 005930.KS: ...
```

#### 해결 방법
1. 개별 종목 재수집 시도
2. 인터넷 연결 확인
3. yfinance 패키지 업데이트:
```bash
pip install --upgrade yfinance
```

---

### 문제 5: CORS 에러

#### 증상
브라우저 Console:
```
Access to XMLHttpRequest at 'http://127.0.0.1:8000/admin/data-status'
from origin 'http://localhost:5173' has been blocked by CORS policy
```

#### 확인 방법
백엔드 `main.py`의 CORS 설정 확인

#### 해결 방법
`backend/app/main.py` 수정:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # 추가 origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🧪 단계별 디버깅 체크리스트

### Step 1: 백엔드 서버 확인
```bash
# 서버 실행 확인
curl http://127.0.0.1:8000/health

# ✅ 정상: {"status":"healthy"}
# ❌ 실패: 서버 시작 필요
```

### Step 2: 로그인 확인
```javascript
// 브라우저 Console
console.log(localStorage.getItem('access_token'))

// ✅ 정상: "eyJhbGciOiJIUzI1NiIs..."
// ❌ 실패: null → 로그인 필요
```

### Step 3: API 요청 확인
```bash
# 개발자 도구 Network 탭
# GET /admin/data-status 요청 확인

# ✅ 정상: Status 200, Response 있음
# ❌ 실패: Status 401/500, 에러 메시지 확인
```

### Step 4: 데이터베이스 확인
```bash
# DB 파일 존재 확인
ls -la /Users/changrim/KingoPortfolio/backend/kingo.db

# ✅ 정상: 파일 존재
# ❌ 실패: 파일 없음 → 서버 재시작
```

### Step 5: 데이터 수집 테스트
```bash
# 주식 1개만 수집 테스트
curl -X POST "http://127.0.0.1:8000/admin/load-stocks" \
  -H "Authorization: Bearer $TOKEN"

# ✅ 정상: {"status":"success", "message":"주식 데이터 적재 완료", ...}
# ❌ 실패: 에러 메시지 확인
```

---

## 📊 정상 작동 시 예상 결과

### 초기 상태 (데이터 없음)
```
📊 현재 데이터 현황
주식: 0개
ETF: 0개
채권: 0개
예적금: 0개
```

### 전체 데이터 수집 후
```
📊 현재 데이터 현황
주식: 13개
ETF: 5개
채권: 3개
예적금: 3개

✅ 데이터 적재 완료
stocks: 성공 13, 업데이트 0, 실패 0
etfs: 성공 5, 업데이트 0, 실패 0
bonds: 성공 3, 업데이트 0
deposits: 성공 3, 업데이트 0
```

---

## 🔧 빠른 진단 명령어

### 올인원 진단 스크립트
```bash
#!/bin/bash
echo "=== KingoPortfolio 관리자 페이지 진단 ==="

echo -e "\n1. 백엔드 서버 확인..."
curl -s http://127.0.0.1:8000/health && echo " ✅" || echo " ❌ 서버 실행 필요"

echo -e "\n2. 프론트엔드 확인..."
curl -s http://localhost:5173 > /dev/null && echo " ✅" || echo " ❌ 프론트엔드 실행 필요"

echo -e "\n3. 데이터베이스 확인..."
[ -f /Users/changrim/KingoPortfolio/backend/kingo.db ] && echo " ✅" || echo " ❌ DB 파일 없음"

echo -e "\n4. 로그인 확인..."
[ -n "$(sqlite3 /Users/changrim/KingoPortfolio/backend/kingo.db 'SELECT COUNT(*) FROM users' 2>/dev/null)" ] && echo " ✅" || echo " ⚠️  사용자 없음"

echo -e "\n5. 종목 데이터 확인..."
sqlite3 /Users/changrim/KingoPortfolio/backend/kingo.db << EOF
SELECT
  '주식: ' || COUNT(*) FROM stocks
UNION ALL
SELECT 'ETF: ' || COUNT(*) FROM etfs
UNION ALL
SELECT '채권: ' || COUNT(*) FROM bonds
UNION ALL
SELECT '예적금: ' || COUNT(*) FROM deposit_products;
EOF

echo -e "\n진단 완료!"
```

저장 후 실행:
```bash
chmod +x diagnose.sh
./diagnose.sh
```

---

## 📞 추가 지원

### 로그 수집
문제 발생 시 다음 정보를 수집:

1. **브라우저 Console 로그**
   - 개발자 도구 > Console > 전체 복사

2. **백엔드 로그**
   - 터미널 출력 복사

3. **Network 요청**
   - 개발자 도구 > Network > 실패한 요청 > Copy as cURL

4. **데이터베이스 상태**
   ```bash
   sqlite3 kingo.db ".schema" > schema.txt
   sqlite3 kingo.db "SELECT COUNT(*) FROM stocks" > counts.txt
   ```

---

**작성일**: 2025-12-19
**버전**: 1.0
