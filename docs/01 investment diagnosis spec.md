# 📊 투자성향 진단 시스템 - 기술 스펙

**프로젝트**: FinPortfolio Phase 2 - MVP  
**목표**: 투자성향 진단 시스템 (목업)  
**개발 기간**: 1-2주  
**개발자**: 1명 (풀스택)  
**스택**: FastAPI + React + SQLite

---

## 1. 프로젝트 개요

### 1.1 목표
사용자가 간단한 설문(5-10분)을 통해 자신의 투자성향을 진단받는 시스템

### 1.2 MVP 범위
```
✅ 사용자 회원가입/로그인
✅ 투자성향 진단 설문 (15개 문항)
✅ 자동 점수 계산
✅ 결과 화면 (보수/중도/적극 3가지)
✅ 결과 재시작
❌ 소셜 로그인 (추후)
❌ 추천 포트폴리오 표시 (다음 단계)
```

### 1.3 사용자 여정
```
홈페이지
    ↓
회원가입 / 로그인
    ↓
투자성향 진단 설문 시작
    ↓
15개 문항 답변 (5분)
    ↓
결과 화면 (투자성향 + 점수 + 설명)
    ↓
결과 저장 + 재진단 가능
```

---

## 2. 기술 아키텍처

### 2.1 스택 선택 (목업용)

| 계층 | 기술 | 이유 |
|------|------|------|
| **Backend** | FastAPI (Python) | 빠른 개발, 자동 API 문서화 |
| **Database** | SQLite | 배포 간단, 로컬 테스트 용이 |
| **Frontend** | React 18 | 반응형, 빠른 개발 |
| **Hosting** | Render.com (무료) | 빠른 배포 |
| **인증** | JWT | 간단, 보안성 우수 |

### 2.2 폴더 구조
```
finportfolio-diagnosis/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI 메인 앱
│   │   ├── models.py             # SQLAlchemy 모델
│   │   ├── schemas.py            # Pydantic 스키마
│   │   ├── database.py           # DB 설정
│   │   ├── auth.py               # JWT 인증
│   │   ├── crud.py               # DB 쿼리
│   │   └── routes/
│   │       ├── auth.py           # 회원가입, 로그인
│   │       ├── survey.py         # 설문 관련 API
│   │       └── diagnosis.py      # 진단 결과 API
│   ├── requirements.txt
│   ├── .env.example
│   └── Procfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthPage.jsx      # 회원가입/로그인
│   │   │   ├── SurveyPage.jsx    # 설문 페이지
│   │   │   └── ResultPage.jsx    # 결과 페이지
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Survey.jsx
│   │   │   └── Result.jsx
│   │   ├── services/
│   │   │   └── api.js            # API 호출
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   └── .env.example
├── README.md
├── docker-compose.yml
└── .gitignore
```

---

## 3. 데이터베이스 설계

### 3.1 ERD (Entity Relationship Diagram)

```
┌─────────────────┐
│     Users       │
├─────────────────┤
│ id (PK)         │
│ email           │
│ password_hash   │
│ created_at      │
│ updated_at      │
└─────────────────┘
        ↓ 1:N
        
┌──────────────────────────┐
│    Diagnoses             │
├──────────────────────────┤
│ id (PK)                  │
│ user_id (FK)             │
│ investment_type          │ (보수/중도/적극)
│ score                    │ (0-10)
│ confidence               │ (신뢰도)
│ monthly_investment       │ (월 투자액)
│ created_at               │
│ updated_at               │
└──────────────────────────┘
        ↓ 1:N
        
┌──────────────────────────┐
│   DiagnosisAnswers       │
├──────────────────────────┤
│ id (PK)                  │
│ diagnosis_id (FK)        │
│ question_id              │
│ answer_value             │ (1-5 점수)
│ created_at               │
└──────────────────────────┘
```

### 3.2 SQL 테이블 정의

```sql
-- Users 테이블
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Diagnoses 테이블
CREATE TABLE diagnoses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    investment_type VARCHAR(20),  -- 'conservative', 'moderate', 'aggressive'
    score FLOAT,                   -- 0-10
    confidence FLOAT,              -- 0-1
    monthly_investment INTEGER,    -- 월 투자액 (만원)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DiagnosisAnswers 테이블
CREATE TABLE diagnosis_answers (
    id TEXT PRIMARY KEY,
    diagnosis_id TEXT NOT NULL REFERENCES diagnoses(id),
    question_id INTEGER NOT NULL,
    answer_value INTEGER,  -- 1-5
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SurveyQuestions 테이블 (static)
CREATE TABLE survey_questions (
    id INTEGER PRIMARY KEY,
    category VARCHAR(50),  -- 'experience', 'duration', 'risk', 'goal', 'amount'
    question TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    weight_a FLOAT,
    weight_b FLOAT,
    weight_c FLOAT
);
```

---

## 4. API 설계

### 4.1 Authentication API

#### POST /api/auth/signup
**회원가입**
```json
// Request
{
  "email": "user@example.com",
  "password": "password123",
  "name": "김투자"
}

// Response (201)
{
  "id": "uuid-1234",
  "email": "user@example.com",
  "name": "김투자",
  "created_at": "2025-12-13T10:00:00Z"
}

// Error (400)
{
  "detail": "Email already registered"
}
```

#### POST /api/auth/login
**로그인**
```json
// Request
{
  "email": "user@example.com",
  "password": "password123"
}

// Response (200)
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-1234",
    "email": "user@example.com",
    "name": "김투자"
  }
}

// Error (401)
{
  "detail": "Invalid credentials"
}
```

---

### 4.2 Survey API

#### GET /api/survey/questions
**설문 문항 조회**
```json
// Response (200)
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
          "weight": 1
        },
        {
          "value": "B",
          "text": "약간 있습니다 (1-2년)",
          "weight": 2
        },
        {
          "value": "C",
          "text": "충분합니다 (3년 이상)",
          "weight": 3
        }
      ]
    },
    ...
  ]
}
```

#### POST /api/survey/submit
**설문 제출 및 진단 수행**
```json
// Request
{
  "answers": [
    {"question_id": 1, "answer_value": 1},
    {"question_id": 2, "answer_value": 3},
    ...
  ],
  "monthly_investment": 100  // 100만원
}

// Response (201)
{
  "diagnosis_id": "uuid-5678",
  "investment_type": "conservative",
  "score": 3.2,
  "confidence": 0.85,
  "description": "안정적인 자산 증식을 원하시는 보수형 투자자입니다",
  "characteristics": [
    "자산 손실에 민감합니다",
    "안정적인 수익을 선호합니다",
    "낮은 변동성을 추구합니다"
  ],
  "created_at": "2025-12-13T10:10:00Z"
}
```

---

### 4.3 Diagnosis API

#### GET /api/diagnosis/me
**최근 진단 결과 조회**
```json
// Response (200)
{
  "diagnosis_id": "uuid-5678",
  "investment_type": "conservative",
  "score": 3.2,
  "confidence": 0.85,
  "monthly_investment": 100,
  "description": "...",
  "created_at": "2025-12-13T10:10:00Z"
}

// Error (401)
{
  "detail": "Not authenticated"
}
```

#### GET /api/diagnosis/history
**진단 이력 조회**
```json
// Response (200)
{
  "total": 3,
  "diagnoses": [
    {
      "diagnosis_id": "uuid-5678",
      "investment_type": "conservative",
      "score": 3.2,
      "created_at": "2025-12-13T10:10:00Z"
    },
    ...
  ]
}
```

#### POST /api/diagnosis/rediagnose
**재진단**
```json
// Request
{
  "answers": [
    {"question_id": 1, "answer_value": 2},
    ...
  ],
  "monthly_investment": 150
}

// Response (201)
{
  "diagnosis_id": "uuid-9012",
  "investment_type": "moderate",
  "score": 5.5,
  "confidence": 0.90,
  ...
}
```

---

## 5. 진단 알고리즘

### 5.1 설문 문항 (15개)

#### 카테고리 1: 투자 경험도 (1-2문항)
```
Q1. 당신의 투자 경험은?
A) 처음입니다 (가중치: 1)
B) 약간 있습니다 1-2년 (가중치: 2)
C) 충분합니다 3년 이상 (가중치: 3)

Q2. 투자로 손실을 본 경험이 있으신가요?
A) 없습니다 (1)
B) 작은 손실 (2)
C) 큰 손실 (3)
```

#### 카테고리 2: 투자 기간 (1-2문항)
```
Q3. 투자 계획 기간은?
A) 1년 이하 (1)
B) 1-3년 (2)
C) 3-5년 (2.5)
D) 5년 이상 (3)

Q4. 투자 목표는?
A) 안정적 자산 보관 (1)
B) 적당한 자산 증식 (2)
C) 높은 수익 추구 (3)
```

#### 카테고리 3: 위험 성향 (5-6문항)
```
Q5. 포트폴리오가 10% 하락했을 때?
A) 즉시 팔고 싶습니다 (1)
B) 지켜보겠습니다 (2)
C) 오히려 더 사고 싶습니다 (3)

Q6. 자산 변동성을 얼마나 견딜 수 있나요?
A) 거의 못 견딥니다 (1)
B) 어느 정도 견딜 수 있습니다 (2)
C) 충분히 견딜 수 있습니다 (3)

...
```

#### 카테고리 4: 금융 지식 (2-3문항)
```
Q11. 금융상품에 대해 얼마나 알고 있나요?
A) 거의 모릅니다 (1)
B) 기본 개념 정도 압니다 (2)
C) 깊이 있게 알고 있습니다 (3)
```

#### 카테고리 5: 월 투자 가능액 (1문항)
```
Q15. 월 투자 가능액은?
A) 10-50만원 (1)
B) 50-300만원 (2)
C) 300만원 이상 (3)
```

### 5.2 점수 계산 로직

```python
def calculate_investment_type(answers: List[Answer]) -> DiagnosisResult:
    """
    설문 응답을 바탕으로 투자성향 계산
    
    Process:
    1. 각 카테고리별 가중 평균 계산
    2. 카테고리별 점수를 종합해 최종 점수 계산
    3. 점수에 따라 투자성향 분류
    4. 신뢰도 계산
    """
    
    # 1. 카테고리별 점수 계산
    category_scores = {}
    for category in ['experience', 'duration', 'risk', 'knowledge', 'amount']:
        scores = [ans.value for ans in answers if ans.category == category]
        category_scores[category] = sum(scores) / len(scores) if scores else 0
    
    # 2. 최종 점수 (카테고리 가중 평균)
    weights = {
        'experience': 0.15,   # 경험 15%
        'duration': 0.15,     # 기간 15%
        'risk': 0.40,         # 위험성향 40% (가장 중요)
        'knowledge': 0.15,    # 지식 15%
        'amount': 0.15        # 투자액 15%
    }
    
    final_score = sum(
        category_scores[cat] * weight 
        for cat, weight in weights.items()
    )
    
    # 3. 투자성향 분류
    if final_score < 2.5:
        investment_type = "conservative"  # 보수형
    elif final_score < 4.5:
        investment_type = "moderate"      # 중도형
    else:
        investment_type = "aggressive"    # 적극형
    
    # 4. 신뢰도 (일관성 평가)
    # 카테고리 내 표준편차가 낮을수록 신뢰도 높음
    consistency = calculate_consistency(category_scores)
    confidence = 0.7 + (consistency * 0.3)  # 0.7-1.0
    
    return DiagnosisResult(
        investment_type=investment_type,
        score=final_score,
        confidence=confidence,
        category_scores=category_scores
    )
```

### 5.3 결과 해석

```python
DIAGNOSIS_DESCRIPTIONS = {
    "conservative": {
        "title": "보수형 투자자",
        "description": "안정적인 자산 증식을 원하시는 보수형 투자자입니다",
        "characteristics": [
            "자산 손실에 민감합니다",
            "안정적인 수익을 선호합니다",
            "낮은 변동성을 추구합니다",
            "주로 채권, 적금, CMA 등에 관심이 있습니다"
        ],
        "recommended_ratio": {
            "stocks": 20,
            "bonds": 35,
            "money_market": 30,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "4-5%"
    },
    "moderate": {
        "title": "중도형 투자자",
        "description": "안정성과 수익성을 모두 추구하는 균형잡힌 투자자입니다",
        "characteristics": [
            "적정 수준의 위험을 감수할 수 있습니다",
            "안정성과 수익성의 균형을 원합니다",
            "중간 정도의 변동성을 견딜 수 있습니다",
            "주식과 채권을 적절히 혼합하고 싶어합니다"
        ],
        "recommended_ratio": {
            "stocks": 40,
            "bonds": 25,
            "money_market": 20,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "6-8%"
    },
    "aggressive": {
        "title": "적극형 투자자",
        "description": "높은 수익을 추구하는 적극적인 투자자입니다",
        "characteristics": [
            "높은 수익을 추구합니다",
            "일정한 손실을 감수할 수 있습니다",
            "높은 변동성을 견딜 수 있습니다",
            "주로 성장주와 신흥시장에 관심이 있습니다"
        ],
        "recommended_ratio": {
            "stocks": 60,
            "bonds": 15,
            "money_market": 10,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "9-12%"
    }
}
```

---

## 6. Frontend UI/UX

### 6.1 페이지 흐름

```
┌─────────────────────────────────────┐
│        Home Page                    │
│  (로고 + 소개 + 시작 버튼)          │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   Auth Page                         │
│  (로그인 / 회원가입 탭)             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   Survey Page                       │
│  (15개 문항 순차 표시)              │
│  - Progress Bar (문항 진행도)       │
│  - 각 문항 라디오 버튼 또는 슬라이더│
│  - 다음/이전/완료 버튼             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   Result Page                       │
│  (투자성향 + 점수 + 특징)          │
│  - 투자성향 배지                    │
│  - 종합 점수 게이지                 │
│  - 신뢰도 표시                      │
│  - 특징 리스트                      │
│  - 재진단 / 공유 버튼              │
└─────────────────────────────────────┘
```

### 6.2 UI 컴포넌트

```jsx
// 주요 컴포넌트
<HomePage />           // 홈
<AuthForm />          // 로그인/회원가입
<SurveyForm />        // 설문 폼
  - <Question />      // 개별 문항
  - <ProgressBar />   // 진행도
  - <Navigation />    // 다음/이전/완료
<ResultCard />        // 결과 표시
  - <ScoreGauge />    // 점수 게이지
  - <TypeBadge />     // 투자성향 배지
  - <Characteristics /> // 특징 나열
<Header />            // 상단 네비게이션
<Footer />            // 하단
```

---

## 7. 개발 일정

### Week 1

**Day 1-2: 백엔드 기초**
- [ ] FastAPI 프로젝트 세팅
- [ ] SQLite DB 설정
- [ ] SQLAlchemy ORM 구성
- [ ] 기본 모델 작성 (User, Diagnosis, Answer)

**Day 3: 인증 구현**
- [ ] JWT 토큰 생성/검증
- [ ] 회원가입 API
- [ ] 로그인 API
- [ ] 토큰 갱신 API

**Day 4: 설문 API**
- [ ] 설문 문항 DB 저장
- [ ] GET /api/survey/questions
- [ ] POST /api/survey/submit (진단 로직 포함)

**Day 5: 프론트엔드 기초**
- [ ] React 프로젝트 세팅
- [ ] 라우팅 설정 (React Router)
- [ ] API 호출 설정 (Axios)
- [ ] 기본 레이아웃

### Week 2

**Day 6-7: Frontend - 인증**
- [ ] 회원가입 페이지
- [ ] 로그인 페이지
- [ ] 로그아웃 기능
- [ ] 토큰 저장 (localStorage)

**Day 8-9: Frontend - 설문**
- [ ] 설문 페이지
- [ ] 진행도 바
- [ ] 문항 렌더링
- [ ] 답변 저장

**Day 10: Frontend - 결과**
- [ ] 결과 페이지
- [ ] 점수 게이지
- [ ] 재진단 버튼

**Day 11-12: 테스트 & 배포**
- [ ] 통합 테스트
- [ ] UI/UX 개선
- [ ] Docker 컨테이너화
- [ ] Render.com 배포

---

## 8. 배포 및 호스팅

### 8.1 Docker 설정

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Frontend Dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package.json .
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 8.2 Render.com 배포

```yaml
# render.yaml
services:
  - type: web
    name: finportfolio-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port 8000
    envVars:
      - key: DATABASE_URL
        value: sqlite:///./diagnosis.db

  - type: web
    name: finportfolio-frontend
    env: static
    buildCommand: npm install && npm run build
    staticPublishPath: build
```

---

## 9. 예상 결과물

### 9.1 완성 이미지

```
사용자가 다음을 할 수 있습니다:

1. ✅ 회원가입 (이메일 + 비밀번호)
2. ✅ 로그인
3. ✅ 15개 문항 설문 (5분)
4. ✅ 자동 투자성향 진단
5. ✅ 결과 확인 (보수/중도/적극)
6. ✅ 재진단 가능
7. ✅ 진단 이력 조회
```

### 9.2 API 완성도
```
✅ 인증 API (2개)
✅ 설문 API (3개)
✅ 진단 API (3개)
= 총 8개 엔드포인트
```

### 9.3 데이터베이스
```
✅ Users 테이블
✅ Diagnoses 테이블
✅ DiagnosisAnswers 테이블
✅ SurveyQuestions 테이블
```

---

## 10. 다음 단계 (Phase 2)

이 MVP 이후:

```
✅ 투자성향 진단 완성
    ↓
⏳ 포트폴리오 추천 엔진 개발
    - 3가지 추천 포트폴리오 템플릿
    - 자산군별 상품 DB
    - 추천 로직
    
⏳ 포트폴리오 커스터마이징
    - 슬라이더 조정
    - 실시간 계산
    
⏳ 성과 추적 시뮬레이션
    - 백테스트 데이터
    - 그래프 시각화
```

---

**작성일**: 2025년 12월 13일  
**버전**: 1.0