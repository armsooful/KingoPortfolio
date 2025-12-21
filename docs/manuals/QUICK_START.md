# 🚀 빠른 시작 가이드

## ✅ 현재 상태

모든 시스템이 정상 작동 중입니다!

- ✅ **백엔드**: http://127.0.0.1:8000 (실행 중)
- ✅ **프론트엔드**: http://localhost:5173 (실행 중)
- ✅ **데이터베이스**: 24개 종목 저장됨 (주식 13, ETF 5, 채권 3, 예적금 3)
- ✅ **yfinance**: v0.2.66 (datetime 오류 수정 완료)

## 📱 관리자 페이지 사용하기

### 1단계: 웹사이트 접속

브라우저에서 http://localhost:5173 열기

### 2단계: 로그인

- **기존 사용자**: 이메일/비밀번호로 로그인
- **신규 사용자**: "회원가입" 클릭하여 계정 생성

### 3단계: 관리자 페이지 접속

로그인 후, 상단 네비게이션 바에서 **"🔧 관리자"** 클릭

### 4단계: 데이터 현황 확인

관리자 페이지에서 다음 정보를 확인:

```
📊 현재 데이터 현황
┌────────┬────────┬────────┬────────┐
│   13   │   5    │   3    │   3    │
│  주식  │  ETF   │  채권  │ 예적금 │
└────────┴────────┴────────┴────────┘
```

### 5단계: 데이터 수집 테스트 (선택)

1. **"📈 주식 데이터만 수집"** 버튼 클릭
2. 확인 팝업에서 **"확인"**
3. 1-2분 대기 (실시간 API 호출)
4. 성공 메시지 확인:
   ```
   ✅ 주식 데이터 적재 완료
   stocks: 성공 0, 업데이트 13, 실패 0
   ```

## 🎯 주요 기능

### 전체 데이터 수집
모든 종목 정보를 한 번에 업데이트:
- 주식 13개 (삼성전자, LG전자, 카카오 등)
- ETF 5개 (KODEX 200, TIGER 200 등)
- 채권 3개 (국고채, 회사채 등)
- 예적금 3개 (CMA, 정기예금 등)

### 개별 데이터 수집
- **주식만**: 13개 한국 주식 업데이트
- **ETF만**: 5개 ETF 업데이트

### 실시간 데이터
yfinance API를 통해 다음 정보를 실시간으로 수집:
- 현재가
- 시가총액
- PER, PBR
- 배당수익률
- 연초 대비 수익률
- 1년 수익률

## 🐛 트러블슈팅

### "데이터 로딩 중..." 계속 표시

**원인**: 백엔드 연결 문제

**해결**:
```bash
# 시스템 상태 확인
./check_system.sh

# 백엔드가 꺼져있으면 재시작
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### "401 Unauthorized" 에러

**원인**: JWT 토큰 만료

**해결**:
1. 브라우저에서 로그아웃
2. 다시 로그인

### 데이터 수집 실패

**원인**: yfinance API 일시적 문제

**해결**:
1. 5-10분 후 재시도
2. 인터넷 연결 확인
3. yfinance API 제한 (1시간 간격 권장)

## 📊 수집되는 종목 목록

### 한국 주식 (13개)
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

### ETF (5개)
1. KODEX 배당성장 (102110.KS)
2. TIGER 200 (133690.KS)
3. KODEX 200 (122630.KS)
4. CoTrader S&P500 (130680.KS)
5. KODEX 인버스 (114800.KS)

## 🔧 시스템 명령어

### 시스템 상태 확인
```bash
./check_system.sh
```

### 백엔드 시작
```bash
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 프론트엔드 시작
```bash
cd /Users/changrim/KingoPortfolio/frontend
npm run dev
```

### 데이터 직접 수집 (명령줄)
```bash
cd /Users/changrim/KingoPortfolio/backend
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

## 📚 자세한 문서

- **[YFINANCE_FIX_SUMMARY.md](YFINANCE_FIX_SUMMARY.md)**: yfinance 오류 수정 내역
- **[VERIFICATION_GUIDE.md](VERIFICATION_GUIDE.md)**: 상세 검증 가이드
- **[DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md)**: 데이터 수집 전체 가이드
- **[ADMIN_TROUBLESHOOTING.md](ADMIN_TROUBLESHOOTING.md)**: 관리자 페이지 트러블슈팅

## 🎉 완료!

이제 KingoPortfolio 관리자 시스템을 사용할 수 있습니다.

**다음 단계**:
1. 브라우저에서 http://localhost:5173 접속
2. 로그인 후 "🔧 관리자" 메뉴 클릭
3. 데이터 현황 확인 및 수집 테스트

**질문이나 문제가 있으면 관련 문서를 참고하세요!**

---

**작성일**: 2024-12-20
**버전**: 1.0
**상태**: ✅ 시스템 정상 작동
