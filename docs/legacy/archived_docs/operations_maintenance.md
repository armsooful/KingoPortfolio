# 🛠️ **KingoPortfolio 운영 및 유지보수 가이드**
최초작성일자: 2025-12-18
최종수정일자: 2026-01-18

## 목차
1. [일일 운영 체크리스트](#일일-운영-체크리스트)
2. [모니터링 및 로깅](#모니터링-및-로깅)
3. [문제 해결 가이드](#문제-해결-가이드)
4. [백업 및 복구](#백업-및-복구)
5. [성능 최적화](#성능-최적화)
6. [보안 유지](#보안-유지)

---

# 📅 일일 운영 체크리스트

## 매일 확인할 것

### 오전 (10:00 AM)

```
☐ 백엔드 상태 확인
  curl https://kingo-backend.onrender.com/health
  → 예상: {"status": "healthy", ...}

☐ 프론트엔드 상태 확인
  브라우저에서 Vercel URL 접속
  → 예상: 페이지 로드 성공

☐ API 응답시간 확인
  - Render 대시보드 → Metrics
  - 평균 응답시간 < 1초 확인

☐ 에러 로그 확인
  - Render 로그 → 지난 24시간
  - 500 에러 확인
```

### 오후 (14:00 PM)

```
☐ 데이터베이스 크기 확인
  - Render SSH 접속 후 확인
  - SELECT COUNT(*) FROM users;

☐ 활성 사용자 모니터링
  - Render 로그 → API 호출 통계

☐ 성능 지표 확인
  - CPU 사용률 < 30%
  - 메모리 사용률 < 50%
```

### 저녁 (18:00 PM)

```
☐ 배포 상태 확인
  - GitHub 커밋 상태
  - Render/Vercel 배포 완료 여부

☐ 사용자 피드백 확인
  - 에러 리포트
  - 기능 요청사항
```

---

# 📊 모니터링 및 로깅

## Render 모니터링

### 1. 실시간 로그 확인

**URL**: https://dashboard.render.com
**Steps**:
1. FinPortfolio-Backend 선택
2. **Logs** 탭 클릭
3. 실시간 스트리밍 확인

### 주요 로그 패턴

```
# ✅ 정상 시작
✅ CORS Allowed Origins: [...]
✅ Database initialized successfully
INFO: Uvicorn running on http://0.0.0.0:10000

# ⚠️ 경고 (무해)
(trapped) error reading bcrypt version  # 알려진 이슈

# 🔴 에러 (조치 필요)
ERROR: Application startup failed
SQLAlchemy: connection refused
```

### 2. 지표 모니터링

**URL**: https://dashboard.render.com
**Steps**:
1. FinPortfolio-Backend 선택
2. **Metrics** 탭 클릭
3. 다음 지표 확인:

| 지표 | 목표 | 경고선 | 위험선 |
|-----|------|--------|--------|
| CPU 사용률 | <20% | >30% | >50% |
| 메모리 사용률 | <30% | >50% | >80% |
| API 응답시간 | <500ms | >1000ms | >2000ms |
| 에러율 | 0% | >1% | >5% |

### 3. 배포 모니터링

**Steps**:
1. Render 대시보드
2. **Deploys** 탭 클릭
3. 최근 배포 상태 확인

```
✅ 배포 성공
- Status: "Live"
- Time: < 5분

🟡 배포 중
- Status: "Building" 또는 "Deploying"
- Time: 진행 중

🔴 배포 실패
- Status: "Failed"
- 로그에서 에러 메시지 확인
```

---

## Vercel 모니터링

### 1. 배포 상태

**URL**: https://vercel.com/dashboard
**Steps**:
1. 프로젝트 선택
2. **Deployments** 탭
3. 최근 배포 상태 확인

### 2. 분석 데이터

**URL**: https://vercel.com/dashboard → Analytics
- 방문자 수
- 최대 응답시간
- 빌드 시간

---

# 🔧 문제 해결 가이드

## 문제 1: 백엔드 502 Bad Gateway

### 증상
```
프론트엔드에서 API 호출 시:
502 Bad Gateway
```

### 원인 진단

```bash
# Step 1: 헬스 체크
curl https://kingo-backend.onrender.com/health

# 응답이 없으면:
# → 서버 다운 또는 슬립 상태
# → Render 대시보드 확인

# 응답이 오류면:
# → 앱 크래시
# → Render 로그 확인
```

### 해결 방법

```bash
# 1단계: Render 대시보드에서 로그 확인
https://dashboard.render.com → Logs

# 2단계: 에러 메시지 검색
"ERROR" 또는 "Exception"

# 3단계: 원인에 따라 조치
- ImportError → requirements.txt 확인
- SyntaxError → 코드 문법 확인
- Database error → 데이터베이스 연결 확인

# 4단계: 강제 재배포
Render → Manual Deploy → Deploy latest commit
```

---

## 문제 2: CORS 에러

### 증상
```
브라우저 콘솔:
Access to XMLHttpRequest at 'https://kingo-backend.onrender.com/auth/signup' 
from origin 'https://kingo-portfolio-*.vercel.app' has been blocked by CORS policy
```

### 원인 진단

```bash
# Step 1: 허용된 origin 확인
curl -H "Origin: https://kingo-portfolio-*.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     https://kingo-backend.onrender.com/auth/signup -v

# Step 2: Render 환경변수 확인
https://dashboard.render.com → Settings → Environment
ALLOWED_ORIGINS 값 확인
```

### 해결 방법

```bash
# 1단계: Render 환경변수 수정
ALLOWED_ORIGINS = https://kingo-portfolio-5oy16z2so-changrims-projects.vercel.app

# 2단계: 저장 및 재배포
Save → Render 자동 재배포

# 3단계: 테스트
프론트엔드에서 요청 재시도
```

---

## 문제 3: 데이터베이스 에러

### 증상
```
회원가입/로그인 시:
500 Internal Server Error

Render 로그:
SQLAlchemy: column "xxx" does not exist
```

### 원인 진단

```bash
# 문제: 모델 정의와 데이터베이스 스키마 불일치

# 확인 사항:
1. models.py에서 컬럼명 확인
2. crud.py에서 사용 중인 속성명 확인
3. 일치 여부 검증
```

### 해결 방법

```python
# models.py
class User(Base):
    hashed_password = Column(String(255))  # ✅ 올바른 이름

# crud.py
db_user = User(
    hashed_password=hashed_password  # ✅ 일치
)
```

---

## 문제 4: 느린 응답시간

### 증상
```
API 응답시간이 5초 이상 소요
→ 사용자 경험 악화
```

### 원인 진단

```bash
# 1단계: Render Metrics 확인
- CPU 사용률 확인 (>50%?)
- 메모리 사용률 확인 (>80%?)
- I/O 대기시간 확인

# 2단계: 느린 쿼리 확인
Render 로그에서 쿼리 실행시간 확인
```

### 해결 방법

```python
# 1. 데이터베이스 인덱스 추가
class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)  # 추가

# 2. 쿼리 최적화
# ❌ 나쁜 예
for question in questions:
    answers = db.query(Answer).filter(...).all()  # N+1 쿼리

# ✅ 좋은 예
questions_with_answers = db.query(Question).options(
    joinedload(Question.answers)
).all()

# 3. 캐싱 추가 (향후)
from functools import lru_cache

@lru_cache(maxsize=100)
def get_survey_questions():
    ...
```

---

# 💾 백업 및 복구

## 데이터베이스 백업

### SQLite 백업 (수동)

```bash
# 1. Render SSH 접속
ssh -i ~/.ssh/render_key ubuntu@your-instance

# 2. 데이터베이스 파일 다운로드
sftp -i ~/.ssh/render_key ubuntu@your-instance
> get kingo.db ~/backup/kingo_$(date +%Y%m%d).db

# 3. 로컬에 저장
ls -lh ~/backup/
```

### 자동 백업 설정 (향후)

```bash
# GitHub Actions 활용
name: Daily Backup
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 02:00

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Backup database
        run: |
          # 데이터베이스 다운로드
          # GitHub로 업로드
```

---

## 데이터베이스 복구

### 복구 절차

```bash
# 1. 현재 데이터베이스 백업
cp kingo.db kingo.db.old

# 2. 백업 파일 복원
cp kingo_20251201.db kingo.db

# 3. Render 재시작
Render 대시보드 → Manual Restart

# 4. 복구 확인
curl https://kingo-backend.onrender.com/health
```

---

# ⚡ 성능 최적화

## 1. 데이터베이스 쿼리 최적화

### 인덱스 추가

```python
# models.py
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)  # 검색 최적화
    created_at = Column(DateTime, index=True)  # 시간 범위 검색 최적화

class Diagnosis(Base):
    __tablename__ = "diagnoses"
    user_id = Column(String, ForeignKey("users.id"), index=True)  # JOIN 최적화
```

### 쿼리 최적화

```python
# ❌ N+1 쿼리 문제
diagnoses = db.query(Diagnosis).all()
for diag in diagnoses:
    print(diag.user.email)  # 매번 쿼리!

# ✅ 조인 최적화
from sqlalchemy.orm import joinedload
diagnoses = db.query(Diagnosis).options(
    joinedload(Diagnosis.user)
).all()

# ✅ 배치 처리
user_ids = [d.user_id for d in diagnoses]
users = db.query(User).filter(User.id.in_(user_ids)).all()
```

---

## 2. 캐싱 전략

### 응답 캐싱 (향후)

```python
from fastapi import Response

@router.get("/survey/questions")
async def get_questions(response: Response):
    # 1시간 캐시
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    questions = get_all_survey_questions()
    return {"total": len(questions), "questions": questions}
```

### 세션 캐싱 (향후)

```python
# Redis를 사용한 세션 캐싱
from redis import Redis

redis_client = Redis(host='localhost', port=6379)

@router.post("/auth/login")
async def login(credentials: UserLogin):
    # 토큰 생성
    token = create_access_token(...)
    
    # Redis에 저장
    redis_client.setex(
        f"token:{token}",
        1800,  # 30분
        json.dumps({"user_id": user.id})
    )
    
    return {"access_token": token}
```

---

## 3. API 응답 시간 최적화

### 쿼리 타임아웃 설정

```python
# sqlalchemy 연결 설정
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,  # 30초 타임아웃
    connect_args={"timeout": 10}  # SQLite 타임아웃
)
```

### 응답 압축

```python
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

---

# 🔐 보안 유지

## 1. 정기 보안 검사

### 주간 (매주 월요일)

```
☐ 의존성 업데이트 확인
  pip list --outdated
  
☐ 보안 취약점 검사
  pip-audit
  safety check
  
☐ 환경변수 보안 확인
  - SECRET_KEY 복잡도
  - ALLOWED_ORIGINS 최신화
```

### 월간 (매월 1일)

```
☐ 암호 정책 검토
  - 최소 8자 유지
  - 72바이트 제한 확인
  
☐ 접근 권한 검토
  - Render 팀 권한
  - GitHub 권한
  
☐ API 키 로테이션
  - SECRET_KEY 변경 계획
```

---

## 2. 보안 업데이트

### 취약점 발견 시 대응

```bash
# 1단계: 영향도 평가
- 심각도: 높음/중간/낮음
- 영향 범위: 모든 사용자?

# 2단계: 업데이트
pip install --upgrade vulnerable_package

# 3단계: 테스트
pytest tests/

# 4단계: 배포
git add requirements.txt
git commit -m "Security: update vulnerable package"
git push origin main
```

---

## 3. 감사 로그

### 로그인 시도 기록 (향후)

```python
@router.post("/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(...)
    
    # 감사 로그 기록
    audit_log = AuditLog(
        user_id=user.id if user else None,
        action="login_attempt",
        email=credentials.email,
        status="success" if user else "failed",
        ip_address=request.client.host,
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return {"access_token": token}
```

---

## 4. 보안 헤더 설정

### HTTP 보안 헤더 추가

```python
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

# 📞 지원 및 연락처

## 긴급 연락처

| 상황 | 연락처 | 응답시간 |
|-----|--------|---------|
| 서비스 다운 | 개발자 | 즉시 |
| 보안 문제 | 개발자 | 1시간 |
| 버그 리포트 | GitHub Issues | 24시간 |
| 기능 요청 | GitHub Discussions | 48시간 |

---

**이 가이드는 KingoPortfolio 운영 및 유지보수에 필요한 모든 정보를 제공합니다.**

마지막 업데이트: 2025-12-17
