# 🏗️ **KingoPortfolio 아키텍처 및 기술 상세 문서**

## 목차
1. [시스템 아키텍처](#시스템-아키텍처)
2. [데이터베이스 설계](#데이터베이스-설계)
3. [API 명세](#api-명세)
4. [코드 구조](#코드-구조)
5. [배포 환경](#배포-환경)

---

# 🏗️ 시스템 아키텍처

## 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    외부 사용자                              │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
   │ 브라우저 │     │스마트폰 │     │ 태블릿  │
   └────┬────┘     └────┬────┘     └────┬────┘
        │                │                │
        └────────────────┼────────────────┘
                         │ HTTPS
        ┌────────────────▼────────────────┐
        │   Vercel (프론트엔드)           │
        │   - React + Vite               │
        │   - 번들링 & CDN 배포          │
        └────────────────┬────────────────┘
                         │ API 호출
                         │ (HTTPS)
        ┌────────────────▼────────────────┐
        │   Render (백엔드)               │
        │   - FastAPI                    │
        │   - Python 3.11                │
        │                                │
        │  ┌──────────────────────────┐  │
        │  │  API 라우터              │  │
        │  │  - /auth                 │  │
        │  │  - /survey               │  │
        │  │  - /diagnosis            │  │
        │  └──────────────────────────┘  │
        │            │                   │
        │  ┌─────────▼──────────────┐   │
        │  │  비즈니스 로직 (CRUD)   │   │
        │  │  - 사용자 관리         │   │
        │  │  - 설문 처리           │   │
        │  │  - 진단 계산           │   │
        │  └─────────┬──────────────┘   │
        │            │                   │
        │  ┌─────────▼──────────────┐   │
        │  │  SQLAlchemy ORM        │   │
        │  │  - 모델 정의           │   │
        │  │  - 데이터 매핑         │   │
        │  └─────────┬──────────────┘   │
        └────────────┼───────────────────┘
                     │
        ┌────────────▼────────────┐
        │  SQLite Database        │
        │  - users                │
        │  - survey_questions     │
        │  - diagnoses            │
        │  - diagnosis_answers    │
        └─────────────────────────┘
```

## 아키텍처 특징

### 계층 구조 (Layered Architecture)

```
┌─────────────────────────────────────┐
│      프레젠테이션 계층              │
│      (React + Vercel)               │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      API 계층                       │
│      (FastAPI 라우터)               │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      비즈니스 로직 계층              │
│      (CRUD, 진단 계산)              │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      데이터 접근 계층                │
│      (SQLAlchemy ORM)               │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      데이터베이스 계층              │
│      (SQLite)                       │
└─────────────────────────────────────┘
```

---

# 🗄️ 데이터베이스 설계

## ER 다이어그램

```
┌──────────────────────┐
│        User          │
├──────────────────────┤
│ id (PK)              │
│ email (UNIQUE)       │
│ hashed_password      │
│ name                 │
│ created_at           │
│ updated_at           │
└──────────┬───────────┘
           │
           │ 1:N
           │
┌──────────▼───────────┐
│     Diagnosis        │
├──────────────────────┤
│ id (PK)              │
│ user_id (FK)         │
│ investment_type      │
│ score                │
│ confidence           │
│ monthly_investment   │
│ created_at           │
│ updated_at           │
└──────────┬───────────┘
           │
           │ 1:N
           │
┌──────────▼───────────┐
│  DiagnosisAnswer     │
├──────────────────────┤
│ id (PK)              │
│ diagnosis_id (FK)    │
│ question_id          │
│ answer_value (1-5)   │
│ created_at           │
└──────────────────────┘


┌──────────────────────┐
│   SurveyQuestion     │
├──────────────────────┤
│ id (PK)              │
│ category             │
│ question             │
│ option_a             │
│ option_b             │
│ option_c (NULL OK)   │
│ weight_a             │
│ weight_b             │
│ weight_c (NULL OK)   │
│ created_at           │
└──────────────────────┘
```

## 테이블 상세 설명

### users 테이블

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**용도**: 사용자 기본 정보 저장
**관계**: Diagnosis 1:N

---

### survey_questions 테이블

```sql
CREATE TABLE survey_questions (
    id INTEGER PRIMARY KEY,
    category VARCHAR(50) NOT NULL,  -- 'experience', 'duration', 'risk', 'knowledge', 'amount'
    question VARCHAR(255) NOT NULL,
    option_a VARCHAR(100) NOT NULL,
    option_b VARCHAR(100) NOT NULL,
    option_c VARCHAR(100) NULL,
    weight_a FLOAT NOT NULL,        -- 선택지별 점수
    weight_b FLOAT NOT NULL,
    weight_c FLOAT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**용도**: 설문 문항 데이터 저장
**특징**: 
- 총 15개 자동 생성
- 5가지 카테고리
- 각 카테고리별 2-3개 문항

---

### diagnoses 테이블

```sql
CREATE TABLE diagnoses (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id VARCHAR(36) NOT NULL,  -- FK
    investment_type VARCHAR(20) NOT NULL,  -- 'conservative', 'moderate', 'aggressive'
    score FLOAT NOT NULL,          -- 0-10 점수
    confidence FLOAT NOT NULL,     -- 0-1 신뢰도
    monthly_investment INTEGER NULL,  -- 월 투자액 (만원)
    notes TEXT NULL,               -- 추가 메모
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**용도**: 진단 결과 저장
**특징**:
- 사용자당 여러 진단 기록
- 시간별 변화 추적 가능

---

### diagnosis_answers 테이블

```sql
CREATE TABLE diagnosis_answers (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    diagnosis_id VARCHAR(36) NOT NULL,  -- FK
    question_id INTEGER NOT NULL,
    answer_value INTEGER NOT NULL,  -- 1-5
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id) ON DELETE CASCADE
);
```

**용도**: 진단 답변 상세 저장
**특징**:
- 진단별 15개 답변 저장
- 추후 분석을 위한 원본 데이터 보관

---

# 📡 API 명세

## 인증 API

### POST /auth/signup - 회원가입

```http
POST https://kingo-backend.onrender.com/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123456",  # 최소 8자, 최대 72바이트
  "name": "사용자"
}
```

**응답 (201 Created)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "사용자",
    "created_at": "2025-12-17T00:00:00"
  }
}
```

**에러 응답**
```json
{
  "detail": "Email already registered"  # 400
}
```

---

### POST /auth/login - 로그인

```http
POST https://kingo-backend.onrender.com/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123456"
}
```

**응답 (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "사용자",
    "created_at": "2025-12-17T00:00:00"
  }
}
```

---

## 설문 API

### GET /survey/questions - 설문 조회

```http
GET https://kingo-backend.onrender.com/survey/questions
```

**응답 (200 OK)**
```json
{
  "total": 15,
  "questions": [
    {
      "id": 1,
      "category": "experience",
      "question": "당신의 투자 경험은?",
      "options": [
        {
          "value": "A",
          "text": "처음입니다 (투자 경험 없음)",
          "weight": 1.0
        },
        {
          "value": "B",
          "text": "약간 있습니다 (1-2년)",
          "weight": 2.0
        },
        {
          "value": "C",
          "text": "충분합니다 (3년 이상)",
          "weight": 3.0
        }
      ]
    },
    ...
  ]
}
```

---

## 진단 API

### POST /diagnosis/submit - 진단 제출

```http
POST https://kingo-backend.onrender.com/diagnosis/submit
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "answers": [
    {
      "question_id": 1,
      "answer_value": 1
    },
    {
      "question_id": 2,
      "answer_value": 2
    },
    ...
  ],
  "monthly_investment": 100  # 월 투자액 (만원), 선택사항
}
```

**응답 (201 Created)**
```json
{
  "diagnosis_id": "550e8400-e29b-41d4-a716-446655440001",
  "investment_type": "moderate",
  "score": 5.5,
  "confidence": 0.85,
  "monthly_investment": 100,
  "description": "안정성과 수익성을 모두 추구하는 균형잡힌 투자자입니다...",
  "characteristics": [
    "적정 수준의 위험을 감수할 수 있습니다",
    "안정성과 수익성의 균형을 원합니다",
    ...
  ],
  "recommended_ratio": {
    "stocks": 40,
    "bonds": 25,
    "money_market": 20,
    "gold": 10,
    "other": 5
  },
  "expected_annual_return": "6-8%",
  "created_at": "2025-12-17T00:00:00"
}
```

---

### GET /diagnosis/me - 최근 진단 조회

```http
GET https://kingo-backend.onrender.com/diagnosis/me
Authorization: Bearer {access_token}
```

**응답 (200 OK)**
```json
{
  "diagnosis_id": "550e8400-e29b-41d4-a716-446655440001",
  "investment_type": "moderate",
  "score": 5.5,
  "confidence": 0.85,
  ...
}
```

---

# 📁 코드 구조

## 백엔드 디렉토리 구조

```
FinPortfolio-Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 초기화, 라우터 연결
│   ├── config.py               # 환경변수 및 설정
│   ├── database.py             # SQLAlchemy 설정
│   ├── auth.py                 # JWT, bcrypt 인증 로직
│   ├── models.py               # SQLAlchemy 모델
│   ├── schemas.py              # Pydantic 스키마
│   ├── crud.py                 # 데이터베이스 CRUD 작업
│   ├── diagnosis.py            # 진단 계산 로직
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py             # 인증 엔드포인트
│   │   ├── survey.py           # 설문 엔드포인트
│   │   └── diagnosis.py        # 진단 엔드포인트
│   │
│   └── (other files)
│
├── requirements.txt            # 패키지 의존성
├── Procfile                    # Render 배포 설정
├── runtime.txt                 # Python 버전
├── .gitignore
├── README.md
└── kingo.db                    # SQLite 데이터베이스
```

## 주요 파일 역할

### main.py
```python
# FastAPI 앱 초기화
app = FastAPI(title="KingoPortfolio")

# CORS 미들웨어 추가
app.add_middleware(CORSMiddleware, ...)

# 라우터 등록
app.include_router(auth.router)
app.include_router(survey.router)
app.include_router(diagnosis.router)

# 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: DB 생성, 설문 초기화
    init_db()
    yield
    # 종료: 리소스 정리
```

### models.py
```python
class User(Base):
    __tablename__ = "users"
    id: String = Column(String, primary_key=True)
    email: String = Column(String(100), unique=True)
    hashed_password: String = Column(String(255))
    name: String = Column(String(50), nullable=True)
    diagnoses = relationship("Diagnosis", ...)

class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: String = Column(String, primary_key=True)
    user_id: String = Column(String, ForeignKey("users.id"))
    investment_type: String = Column(String(20))
    score: Float = Column(Float)
    confidence: Float = Column(Float)
    user = relationship("User", back_populates="diagnoses")
```

### auth.py
```python
# 비밀번호 해시
def hash_password(password: str) -> str:
    if len(password.encode('utf-8')) > 72:
        raise ValueError("72바이트 초과")
    return pwd_context.hash(password)

# JWT 토큰 생성
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, settings.algorithm)
    return encoded_jwt
```

### crud.py
```python
# 사용자 생성
def create_user(db: Session, user_create: UserCreate):
    hashed_password = hash_password(user_create.password)
    db_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        name=user_create.name
    )
    db.add(db_user)
    db.commit()
    return db_user

# 진단 생성
def create_diagnosis(db: Session, user_id: str, investment_type: str, score: float, confidence: float):
    diagnosis = Diagnosis(
        user_id=user_id,
        investment_type=investment_type,
        score=score,
        confidence=confidence
    )
    db.add(diagnosis)
    db.commit()
    return diagnosis
```

### diagnosis.py
```python
# 진단 계산
def calculate_diagnosis(answers: List[DiagnosisAnswerRequest]) -> tuple:
    # 답변 값 평균
    avg = sum(ans.answer_value for ans in answers) / len(answers)
    
    # 0-10 범위로 정규화
    score = (avg - 1) * 2.5
    
    # 성향 분류
    if score < 3.33:
        investment_type = "conservative"
    elif score < 6.67:
        investment_type = "moderate"
    else:
        investment_type = "aggressive"
    
    # 신뢰도 계산 (일관성)
    confidence = calculate_confidence(answers)
    
    return investment_type, score, confidence
```

---

# 🚀 배포 환경

## Render 배포 설정

### Procfile
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### runtime.txt
```
python-3.11.14
```

### 환경변수

| 변수명 | 값 | 용도 |
|--------|-----|------|
| SECRET_KEY | (32자 이상) | JWT 서명 |
| ALLOWED_ORIGINS | https://kingo-portfolio-*.vercel.app | CORS |
| DATABASE_URL | (미설정) | SQLite 사용 |

### 배포 프로세스

```
1. GitHub에 코드 푸시
2. Render에서 자동 감지
3. 환경 설정 로드
4. 의존성 설치 (pip install -r requirements.txt)
5. 앱 시작 (uvicorn)
6. https://kingo-backend.onrender.com에서 접속 가능
```

---

## 프론트엔드 배포 (Vercel)

### build 명령어
```bash
npm run build
```

### 배포 프로세스

```
1. GitHub에 코드 푸시
2. Vercel에서 자동 감지
3. Node.js 환경 설정
4. 의존성 설치 (npm install)
5. 빌드 (npm run build)
6. 배포 (CDN 배포)
7. https://kingo-portfolio-*.vercel.app에서 접속 가능
```

---

# 📊 성능 메트릭

## API 응답시간 (목표)

| 엔드포인트 | 목표 | 현재 |
|-----------|------|------|
| GET /survey/questions | <500ms | ~300ms ✅ |
| POST /auth/signup | <1000ms | ~800ms ✅ |
| POST /auth/login | <800ms | ~600ms ✅ |
| POST /diagnosis/submit | <1000ms | ~900ms ✅ |
| GET /diagnosis/me | <500ms | ~400ms ✅ |

## 데이터베이스 크기

| 테이블 | 레코드 수 | 크기 |
|--------|----------|------|
| users | ~0 | ~0KB |
| survey_questions | 15 | ~2KB |
| diagnoses | ~0 | ~0KB |
| diagnosis_answers | ~0 | ~0KB |
| **전체** | **15+** | **~50KB** |

---

**이 문서는 KingoPortfolio의 기술 아키텍처를 상세히 설명합니다.**

마지막 업데이트: 2025-12-17
