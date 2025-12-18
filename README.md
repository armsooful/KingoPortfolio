# KingoPortfolio 👑

> 당신의 투자 성향을 진단하고, 맞춤형 포트폴리오를 추천받으세요.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [빠른 시작](#빠른-시작)
- [개발 가이드](#개발-가이드)
- [배포](#배포)
- [API 문서](#api-문서)
- [기여](#기여)
- [라이선스](#라이선스)

---

## 🎯 프로젝트 소개

**KingoPortfolio**는 AI 기반의 투자 포트폴리오 추천 플랫폼입니다.

사용자의 투자 성향을 정확하게 진단하고, 맞춤형 포트폴리오를 자동으로 추천해줍니다.

### 목표

- **소액 투자자를 위한 맞춤형 포트폴리오 추천**
- **사용하기 쉬운 UI/UX로 금융 접근성 향상**
- **B2C → B2B 확장으로 금융기관 white-label 솔루션 제공**

### KPI

| 항목 | 목표 | 기간 |
|------|------|------|
| 사용자 수 | 500,000명 | 24개월 |
| 관리 자산 | 2.5조 원 | 24개월 |
| 월간 활성사용자(MAU) | 100,000명 | 12개월 |

---

## ✨ 주요 기능

### 🔐 사용자 인증
- 회원가입 / 로그인 (JWT 기반)
- 비밀번호 해싱 (Bcrypt)
- 세션 관리

### 📊 투자 성향 진단
- **15개 문항 설문** (5개 카테고리)
  - 투자 경험
  - 투자 기간
  - 위험성향
  - 금융 지식
  - 투자 규모
- **AI 기반 성향 분류** (3가지 유형)
  - 🛡️ 보수형 (Conservative)
  - ⚖️ 중도형 (Moderate)
  - 🚀 적극형 (Aggressive)

### 💼 맞춤형 포트폴리오
- **자동 자산 배분** (주식, 채권, 머니마켓, 금, 기타)
- **기대 수익률 제시** (연 4-12%)
- **월 투자액 기반 추천**

### 📈 진단 이력 관리
- 과거 진단 결과 저장
- 진단 이력 조회
- 성향 변화 추적

---

## 🛠️ 기술 스택

### Backend
| 항목 | 기술 |
|------|------|
| Framework | FastAPI 0.104.1 |
| Language | Python 3.11 |
| Database | SQLite (dev), PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 |
| Authentication | JWT + Bcrypt |
| API | REST + Swagger/OpenAPI |
| Server | Uvicorn |
| Deployment | Render |

### Frontend
| 항목 | 기술 |
|------|------|
| Framework | React 18 |
| Build Tool | Vite 5 |
| Styling | Tailwind CSS |
| Routing | React Router 6 |
| HTTP Client | Axios |
| State Management | React Context API |
| Deployment | Vercel |

### DevOps
| 항목 | 기술 |
|------|------|
| Version Control | Git / GitHub |
| CI/CD | GitHub Actions (준비 중) |
| Containerization | Docker (선택사항) |
| Monitoring | (준비 중) |

---

## 📂 프로젝트 구조

```
KingoPortfolio/
│
├── backend/                          # FastAPI 백엔드
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 앱 진입점
│   │   ├── config.py               # 설정 (환경변수)
│   │   ├── database.py             # SQLAlchemy 설정
│   │   ├── models.py               # DB 모델 (User, Diagnosis 등)
│   │   ├── schemas.py              # Pydantic 스키마 (요청/응답)
│   │   ├── crud.py                 # 데이터베이스 CRUD 함수
│   │   ├── auth.py                 # JWT 인증 로직
│   │   ├── diagnosis.py            # 진단 알고리즘
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py             # POST /auth/signup, login
│   │       ├── survey.py           # GET /survey/questions
│   │       └── diagnosis.py        # POST /diagnosis/submit
│   ├── requirements.txt             # Python 의존성
│   ├── runtime.txt                  # Python 버전 (3.11)
│   ├── render.yaml                  # Render 배포 설정
│   └── .env.example                 # 환경변수 예시
│
├── frontend/                         # React + Vite 프론트엔드
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx            # 홈페이지
│   │   │   ├── LoginPage.jsx       # 로그인
│   │   │   ├── SignupPage.jsx      # 회원가입
│   │   │   ├── SurveyPage.jsx      # 설문 조사
│   │   │   ├── DiagnosisResultPage.jsx    # 진단 결과
│   │   │   └── DiagnosisHistoryPage.jsx   # 진단 이력
│   │   ├── components/
│   │   │   ├── Header.jsx          # 헤더 (네비게이션)
│   │   │   └── SurveyQuestion.jsx  # 설문 문항 컴포넌트
│   │   ├── services/
│   │   │   └── api.js              # API 통신 (Axios)
│   │   ├── styles/
│   │   │   └── App.css             # CSS 스타일
│   │   ├── App.jsx                 # 메인 App 컴포넌트
│   │   └── main.jsx                # React 진입점
│   ├── public/
│   ├── package.json                 # NPM 의존성
│   ├── vite.config.js              # Vite 설정
│   ├── tailwind.config.js           # Tailwind CSS 설정
│   ├── postcss.config.js            # PostCSS 설정
│   ├── .env.development             # 개발 환경변수
│   ├── .env.production              # 프로덕션 환경변수
│   ├── .gitignore
│   └── README.md
│
├── docs/                            # 문서
│   └── 20251217/                    # 날짜별 문서
│
├── .gitignore                       # Git 무시 파일
├── README.md                        # 이 파일
├── docker-compose.yml               # Docker Compose (선택사항)
└── .github/
    └── workflows/                   # CI/CD (준비 중)
```

---

## 🚀 빠른 시작

### 📋 필수 요소

- Python 3.11+
- Node.js 18+
- npm 또는 yarn
- Git

### 📥 설치

#### 1. 리포지토리 클론

```bash
git clone https://github.com/armsooful/kingo-portfolio.git
cd KingoPortfolio
```

#### 2. 백엔드 설정

```bash
cd backend

# 가상환경 생성 (처음 1회만)
python -m venv venv

# 가상환경 활성화
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 수정 (필요시)

# 서버 실행
python -m uvicorn app.main:app --reload
# 또는
python main.py
```

**결과**: http://localhost:8000

#### 3. 프론트엔드 설정

```bash
cd ../frontend

# 패키지 설치 (처음 1회만)
npm install

# 개발 서버 실행
npm run dev
```

**결과**: http://localhost:5173

#### 4. 테스트

```bash
# 브라우저에서 접속
http://localhost:5173

# API Swagger 문서
http://localhost:8000/docs

# 회원가입 → 설문 → 결과 확인
```

---

## 📖 개발 가이드

### 백엔드 개발

#### 코드 구조

```
backend/app/
├── main.py          # FastAPI 앱, 라우터 포함
├── models.py        # SQLAlchemy 모델 (User, Diagnosis)
├── schemas.py       # Pydantic 스키마 (요청/응답 스펙)
├── crud.py          # 데이터베이스 쿼리 함수
├── auth.py          # JWT 토큰, 비밀번호 해싱
├── diagnosis.py     # 진단 알고리즘 (점수 계산, 성향 분류)
├── config.py        # 설정 (DB URL, 시크릿 키 등)
├── database.py      # SQLAlchemy 엔진 설정
└── routes/
    ├── auth.py      # /auth 엔드포인트
    ├── survey.py    # /survey 엔드포인트
    └── diagnosis.py # /diagnosis 엔드포인트
```

#### 새로운 API 엔드포인트 추가

```python
# backend/app/routes/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/example", tags=["Example"])

@router.get("/")
async def get_examples(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """예시 엔드포인트"""
    return {"message": "Hello"}

# backend/app/main.py에 추가
from app.routes import example
app.include_router(example.router)
```

#### 테스트

```bash
cd backend

# pytest 실행
pytest

# 특정 테스트만
pytest tests/test_auth.py -v

# 커버리지 확인
pytest --cov=app
```

### 프론트엔드 개발

#### 컴포넌트 구조

```
frontend/src/
├── pages/           # 페이지 컴포넌트
├── components/      # 재사용 컴포넌트
├── services/        # API 통신
├── styles/          # CSS/Tailwind
├── App.jsx          # 라우팅 설정
└── main.jsx         # 진입점
```

#### 새로운 페이지 추가

```jsx
// frontend/src/pages/NewPage.jsx
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';

function NewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="container">
      <h1>새 페이지</h1>
      <p>사용자: {user.email}</p>
    </div>
  );
}

export default NewPage;

// frontend/src/App.jsx에 라우트 추가
<Route path="/new" element={<ProtectedRoute><NewPage /></ProtectedRoute>} />
```

#### 환경변수 사용

```jsx
// 백엔드 URL 사용
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API 호출
const response = await axios.get(`${API_URL}/api/endpoint`);
```

#### 빌드

```bash
cd frontend

# 프로덕션 빌드
npm run build

# 빌드 결과 미리보기
npm run preview

# 배포
npm run build && git push
```

---

## 🌐 배포

### 백엔드 배포 (Render)

#### Step 1: Render 계정 생성

- https://render.com 접속
- GitHub 연동

#### Step 2: 웹 서비스 생성

1. "New +" → "Web Service"
2. GitHub 리포 선택
3. 설정:
   - **Name**: `kingo-backend`
   - **Environment**: Python 3
   - **Region**: Singapore (또는 서울)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: `backend`

#### Step 3: 환경변수 설정

Environment 탭에서:

```
DATABASE_URL=postgresql://user:password@host/dbname
SECRET_KEY=your-secret-key-min-32-characters
ALLOWED_ORIGINS=http://localhost:5173,https://kingo-portfolio.vercel.app
```

#### Step 4: 배포

"Deploy" 클릭 → 자동 배포 시작

**결과**: https://kingo-backend.onrender.com

### 프론트엔드 배포 (Vercel)

#### Step 1: Vercel 계정 생성

- https://vercel.com 접속
- GitHub 연동

#### Step 2: 프로젝트 생성

1. "Add New..." → "Project"
2. GitHub 리포 선택
3. 설정:
   - **Framework**: React
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

#### Step 3: 환경변수 설정

Environment Variables에서:

```
VITE_API_URL=https://kingo-backend.onrender.com
```

각 환경 선택:
- ☑️ Preview
- ☑️ Production
- ☑️ Development

#### Step 4: 배포

"Deploy" 클릭 → 자동 배포 시작

**결과**: https://kingo-portfolio.vercel.app

---

## 📚 API 문서

### Swagger UI (권장)

```
https://kingo-backend.onrender.com/docs
```

### ReDoc

```
https://kingo-backend.onrender.com/redoc
```

### 주요 엔드포인트

#### 인증

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/auth/signup` | 회원가입 |
| `POST` | `/auth/login` | 로그인 |
| `GET` | `/auth/me` | 현재 사용자 정보 |

#### 설문

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/survey/questions` | 모든 설문 문항 조회 |
| `GET` | `/survey/questions/{id}` | 특정 문항 조회 |

#### 진단

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/diagnosis/submit` | 설문 제출 및 진단 |
| `GET` | `/diagnosis/me` | 최근 진단 결과 |
| `GET` | `/diagnosis/{id}` | 특정 진단 결과 |
| `GET` | `/diagnosis/history/all` | 진단 이력 조회 |

---

## 🤝 기여

### 기여 방법

1. Fork 하기
2. Feature 브랜치 생성: `git checkout -b feature/amazing-feature`
3. 변경사항 커밋: `git commit -m 'Add amazing feature'`
4. 브랜치 푸시: `git push origin feature/amazing-feature`
5. Pull Request 생성

### 코드 스타일

- **Python**: PEP 8 (Black formatter 사용)
- **JavaScript**: ESLint 규칙 준수
- **Commits**: Conventional Commits 사용

```bash
# 예시
git commit -m "feat: Add new diagnostic feature"
git commit -m "fix: Resolve JWT token validation issue"
git commit -m "docs: Update API documentation"
```

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

---

## 📞 문의 및 지원

### 문제 보고

[GitHub Issues](https://github.com/armsooful/kingo-portfolio/issues)에서 버그를 보고하거나 기능을 제안해주세요.

### 문의

- 📧 이메일: support@kingoportfolio.com
- 💬 Discord: [KingoPortfolio Community](https://discord.gg/...)
- 🐙 GitHub: [@armsooful](https://github.com/armsooful)

---

## 📚 추가 리소스

- [개발 일지](./docs/)
- [API 명세서](https://kingo-backend.onrender.com/docs)
- [배포 가이드](./docs/DEPLOYMENT.md)
- [기여 가이드](./CONTRIBUTING.md)

---

## 🙏 감사의 말

이 프로젝트를 가능하게 해준 모든 분들께 감사합니다.

### 사용된 오픈소스

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)

---

## 🎯 로드맵

### Phase 1 (완료 ✅)
- ✅ 백엔드 API 개발
- ✅ 프론트엔드 기본 UI
- ✅ 진단 알고리즘 구현
- ✅ 배포 (Render, Vercel)

### Phase 2 (진행 중 🔄)
- 🔄 사용자 피드백 수집
- 🔄 성능 최적화
- 🔄 모바일 앱 개발
- 🔄 분석 대시보드

### Phase 3 (계획 📅)
- 📅 B2B 금융기관 파트너십
- 📅 고급 포트폴리오 시뮬레이션
- 📅 AI 추천 개선 (머신러닝)
- 📅 더 많은 자산 클래스 지원

---

## 📊 프로젝트 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| 백엔드 API | ✅ 완성 | 모든 엔드포인트 구현됨 |
| 프론트엔드 | ✅ 완성 | Tailwind CSS 적용 |
| 배포 | ✅ 완성 | Render + Vercel |
| 테스트 | 🔄 진행 중 | 단위 테스트 추가 중 |
| 문서화 | ✅ 진행 중 | API 문서 완료 |
| CI/CD | 📅 예정 | GitHub Actions 설정 예정 |

---

<div align="center">

**Made with ❤️ by [Charlie](https://github.com/armsooful)**

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!

[⬆ 맨 위로](#kingoportfolio-)

</div>

---

## 📌 마지막 업데이트

**날짜**: 2025년 12월 18일  
**버전**: 1.0.0  
**상태**: 프로덕션 준비 완료 ✅