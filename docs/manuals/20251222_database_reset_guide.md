# 데이터베이스 초기화 옵션 가이드
최초작성일자: 2025-12-22
최종수정일자: 2026-01-18

## 📌 개요

서버 재시작 시 데이터베이스를 초기화할지 여부를 환경변수로 제어할 수 있습니다.

## 🔧 설정 방법

### 환경변수

`.env` 파일에 다음 설정을 추가하세요:

```bash
RESET_DB_ON_STARTUP=false
```

### 설정값

- **`false`** (기본값): 테이블이 없을 때만 생성, 기존 데이터 보존
  - 프로덕션 환경에 권장
  - 사용자 계정, 수집된 종목 데이터 등이 서버 재시작 후에도 유지됨

- **`true`**: 서버 시작 시마다 모든 테이블 삭제 후 재생성
  - 개발/테스트 환경에서만 사용
  - ⚠️ **경고**: 모든 데이터가 삭제됩니다!

## 📋 사용 예시

### 프로덕션 환경 (데이터 보존)

```bash
# .env 파일
RESET_DB_ON_STARTUP=false
```

서버 재시작 시:
```
✅ Database initialized (tables created if not exists)
✅ Database initialized successfully
```

### 개발 환경 (데이터 리셋)

```bash
# .env 파일
RESET_DB_ON_STARTUP=true
```

서버 재시작 시:
```
⚠️ Database tables dropped (RESET_DB_ON_STARTUP=true)
✅ Database initialized (tables created if not exists)
✅ Database initialized successfully
```

## ⚠️ 주의사항

1. **프로덕션에서는 절대 `true`로 설정하지 마세요**
   - 모든 사용자 계정이 삭제됩니다
   - 수집된 모든 종목 데이터가 삭제됩니다
   - 투자 진단 기록이 삭제됩니다

2. **개발 중에도 신중하게 사용하세요**
   - 테스트 데이터를 유지하려면 `false`로 설정
   - 깨끗한 상태에서 시작하려면 `true`로 설정

3. **환경변수 미설정 시**
   - 기본값은 `false`
   - 데이터가 보존됩니다

## 🛠️ 수동으로 데이터베이스 리셋하기

서버를 재시작하지 않고 데이터베이스를 리셋하려면:

```bash
# 방법 1: DB 파일 삭제
cd /Users/changrim/KingoPortfolio/backend
rm kingo.db
# 서버 재시작하면 새로운 DB가 생성됨

# 방법 2: 환경변수를 일시적으로 설정하고 서버 재시작
RESET_DB_ON_STARTUP=true uvicorn app.main:app --reload
```

## 💡 Tips

### 데이터 백업

중요한 데이터가 있는 경우 백업:

```bash
cp backend/kingo.db backend/kingo.db.backup
```

### 데이터 복원

```bash
cp backend/kingo.db.backup backend/kingo.db
```

### 특정 테이블만 삭제

Python 스크립트로 특정 테이블만 삭제할 수 있습니다:

```python
from app.database import engine, SessionLocal
from app.models.alpha_vantage import AlphaVantageStock

# 특정 모델의 테이블만 삭제
AlphaVantageStock.__table__.drop(engine)

# 또는 DB 세션으로 데이터만 삭제
db = SessionLocal()
db.query(AlphaVantageStock).delete()
db.commit()
db.close()
```

## 📊 데이터 현황 확인

현재 데이터베이스 상태 확인:

```python
from app.database import SessionLocal
from app.models.alpha_vantage import AlphaVantageStock
from app.models.user import User
from app.models.securities import Stock, ETF

db = SessionLocal()
print(f"사용자: {db.query(User).count()}명")
print(f"미국 주식: {db.query(AlphaVantageStock).count()}개")
print(f"한국 주식: {db.query(Stock).count()}개")
print(f"ETF: {db.query(ETF).count()}개")
db.close()
```

## 🔍 관련 파일

- `/Users/changrim/KingoPortfolio/backend/app/config.py` - 환경변수 로드
- `/Users/changrim/KingoPortfolio/backend/app/main.py` - `init_db()` 함수
- `/Users/changrim/KingoPortfolio/backend/.env.example` - 환경변수 예시
