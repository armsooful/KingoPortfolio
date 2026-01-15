# Foresto Compass 🌲

> 투자 전략 학습을 위한 교육용 포트폴리오 시뮬레이션 플랫폼

⚠️ **법적 고지**: 본 서비스는 교육 및 정보 제공 목적의 플랫폼이며, 투자 권유·추천·자문·일임을 제공하지 않습니다.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-336791?logo=postgresql)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Phase](https://img.shields.io/badge/Phase-1%20Completed-success)](docs/phase1/20260115_phase1_completion_report.md)

---

## 📋 목차

- [프로젝트 소개](#프로젝트-소개)
- [현재 상태](#현재-상태)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [빠른 시작](#빠른-시작)
- [개발 가이드](#개발-가이드)
- [문서](#문서)
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

## 📊 현재 상태

### Phase 1 완료 (2026-01-15) ✅

시뮬레이션 인프라 구축이 완료되었습니다.

| 구분 | 상태 | 설명 |
|------|------|------|
| PostgreSQL DDL | ✅ | 파티셔닝 포함 스키마 설계 |
| ORM 모델 | ✅ | simulation_run, simulation_path, simulation_summary |
| 시나리오 시뮬레이션 | ✅ | MIN_VOL, DEFENSIVE, GROWTH |
| 캐싱 레이어 | ✅ | request_hash 기반 7일 TTL |
| 운영 스크립트 | ✅ | 파티션 관리, TTL 정리, 품질 리포트 |

**DoD (Definition of Done)**:
- ✅ DDL 문서와 실제 코드 스키마 일치
- ✅ simulation_store가 sim_run/path/summary에 정상 저장
- ✅ Phase 0 API 응답 형식과 호환
- ✅ Feature flag(USE_SIM_STORE)로 전환 가능

> 📄 상세 보고서: [Phase 1 완료 보고서](docs/phase1/20260115_phase1_completion_report.md)

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

### 📊 시나리오 시뮬레이션 (Phase 1)
- **3가지 시나리오** 지원
  - MIN_VOL: 변동성 최소화
  - DEFENSIVE: 방어형
  - GROWTH: 성장형
- **손실/회복 지표 중심** 리스크 분석
  - MDD (최대 낙폭)
  - 최대 회복 기간
  - 최악의 1개월/3개월 수익률
- **캐싱 지원**: 동일 요청 7일 캐시
- **일별 NAV 경로** 제공

---

## 🛠️ 기술 스택

### Backend
| 항목 | 기술 |
|------|------|
| Framework | FastAPI 0.104.1 |
| Language | Python 3.11 |
| Database | PostgreSQL 14+ (파티셔닝 지원) |
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
│   │   ├── data_collector.py       # yfinance 데이터 수집
│   │   ├── progress_tracker.py     # 진행 상황 추적
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # POST /auth/signup, login
│   │   │   ├── survey.py           # GET /survey/questions
│   │   │   ├── diagnosis.py        # POST /diagnosis/submit
│   │   │   └── admin.py            # 관리자 기능
│   │   ├── services/
│   │   │   └── data_loader.py      # 데이터 로딩 서비스
│   │   └── models/
│   │       └── financial_products.py  # 금융상품 모델
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
│   │   │   ├── DiagnosisHistoryPage.jsx   # 진단 이력
│   │   │   └── AdminPage.jsx       # 관리자 페이지
│   │   ├── components/
│   │   │   ├── Header.jsx          # 헤더 (네비게이션)
│   │   │   ├── SurveyQuestion.jsx  # 설문 문항 컴포넌트
│   │   │   └── ProgressBar.jsx     # 진행률 표시 컴포넌트
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
├── docs/                            # 📚 문서
│   ├── README.md                   # 문서 인덱스
│   ├── architecture/               # 설계 및 아키텍처
│   ├── changelogs/                 # 변경 이력
│   ├── compliance/                 # 법적 준수 및 면책
│   ├── deployment/                 # 배포 가이드
│   ├── development/                # 개발 가이드
│   ├── legacy/                     # 과거 문서 아카이브
│   ├── manuals/                    # 운영 매뉴얼
│   └── phase1/                     # Phase 1 관련 문서
│
├── scripts/                         # 🛠️ 유틸리티 스크립트
│   ├── README.md                   # 스크립트 가이드
│   ├── start_servers.sh            # 서버 시작
│   ├── view_db.sh                  # DB 조회
│   ├── check_system.sh             # 시스템 점검
│   ├── create_partitions.py        # 파티션 생성 (Phase 1)
│   ├── cleanup_simulations.py      # 시뮬레이션 정리 (Phase 1)
│   ├── quality_report.py           # 품질 리포트 (Phase 1)
│   └── test_api.py                 # API 테스트
│
├── .gitignore                       # Git 무시 파일
├── README.md                        # 이 파일
├── Dockerfile                       # Docker 설정
└── .claude/                         # Claude Code 설정
    └── settings.local.json
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

## 📚 문서

프로젝트 문서는 [docs/](docs/) 폴더에 카테고리별로 정리되어 있습니다.

| 폴더 | 설명 |
|------|------|
| [architecture/](docs/architecture/) | 설계 및 아키텍처 문서 |
| [changelogs/](docs/changelogs/) | 변경 이력 및 릴리스 노트 |
| [compliance/](docs/compliance/) | 법적 준수 및 면책 조항 |
| [deployment/](docs/deployment/) | 배포 및 인프라 가이드 |
| [development/](docs/development/) | 개발 가이드 및 백로그 |
| [manuals/](docs/manuals/) | 운영 매뉴얼 |
| [phase1/](docs/phase1/) | Phase 1 관련 문서 |

> 📄 전체 문서 목록: [docs/README.md](docs/README.md)

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

#### 시나리오 시뮬레이션 (Phase 1)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/backtest/scenario` | 시나리오 시뮬레이션 실행 |
| `GET` | `/backtest/scenario/{id}/path` | NAV 경로 조회 |
| `GET` | `/scenarios` | 시나리오 목록 조회 |
| `GET` | `/scenarios/{id}` | 시나리오 상세 정보 |

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

### 📖 사용 매뉴얼
- [빠른 시작 가이드](docs/manuals/QUICK_START.md)
- [데이터베이스 가이드](docs/manuals/DATABASE_GUIDE.md)
- [테스트 가이드](docs/manuals/TEST_GUIDE.md)

전체 매뉴얼 목록: [docs/manuals/README.md](docs/manuals/README.md)

### 🛠️ 유틸리티 스크립트

```bash
# 서버 시작
./scripts/start_servers.sh

# 파티션 생성 (Phase 1)
python scripts/create_partitions.py --months 6

# 시뮬레이션 정리 (Phase 1)
python scripts/cleanup_simulations.py --dry-run

# 품질 리포트 (Phase 1)
python scripts/quality_report.py --output report.md
```

전체 스크립트 가이드: [scripts/README.md](scripts/README.md)

### 🔗 기타 리소스
- [문서 인덱스](docs/README.md)
- [API 명세서](https://kingo-backend.onrender.com/docs)
- [Phase 1 완료 보고서](docs/phase1/20260115_phase1_completion_report.md)

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

### Phase 0 (완료 ✅) - 기본 인프라
- ✅ 백엔드 API 개발
- ✅ 프론트엔드 기본 UI
- ✅ 진단 알고리즘 구현
- ✅ 배포 (Render, Vercel)

### Phase 1 (완료 ✅) - 시뮬레이션 인프라
- ✅ PostgreSQL DDL (파티셔닝)
- ✅ ORM 모델 (sim_run, sim_path, sim_summary)
- ✅ 시나리오 시뮬레이션 API
- ✅ 캐싱 레이어 (request_hash 기반)
- ✅ 운영 스크립트 (파티션, TTL, 품질)

### Phase 2 (계획 📅) - 실데이터 연동
- 📅 일봉가격/일간수익률 적재
- 📅 실제 DB 기반 시뮬레이션
- 📅 pykrx/Alpha Vantage 연동

### Phase 3 (계획 📅) - 고도화
- 📅 B2B 금융기관 파트너십
- 📅 AI 추천 개선 (머신러닝)
- 📅 더 많은 자산 클래스 지원

---

## 📊 프로젝트 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| 백엔드 API | ✅ 완성 | Phase 1 시나리오 시뮬레이션 포함 |
| 프론트엔드 | ✅ 완성 | Tailwind CSS 적용 |
| 배포 | ✅ 완성 | Render + Vercel |
| 데이터베이스 | ✅ 완성 | PostgreSQL 파티셔닝 지원 |
| 문서화 | ✅ 완성 | 카테고리별 정리 완료 |
| 운영 스크립트 | ✅ 완성 | 파티션/TTL/품질 리포트 |

---

<div align="center">

**Made with ❤️ by [Charlie](https://github.com/armsooful)**

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!

[⬆ 맨 위로](#kingoportfolio-)

</div>

---

## 📌 마지막 업데이트

**날짜**: 2026년 1월 15일
**버전**: 1.1.0 (Phase 1 완료)
**상태**: 프로덕션 준비 완료 ✅

### 최근 변경사항 (2026-01-15)
- ✅ **Phase 1 완료**: 시뮬레이션 인프라 구축
- ✅ PostgreSQL DDL 설계 (파티셔닝 포함)
- ✅ 시나리오 시뮬레이션 API (`POST /backtest/scenario`)
- ✅ 운영 스크립트 추가 (파티션 생성, TTL 정리, 품질 리포트)
- ✅ 문서 재구성 (카테고리별 서브폴더, 날짜 prefix)

### 관련 문서
- [Phase 1 완료 보고서](docs/phase1/20260115_phase1_completion_report.md)
- [Phase 1 백로그 티켓](docs/phase1/20260115_phase1_backlog_tickets.md)
- [문서 인덱스](docs/README.md)