# KingoPortfolio Backend

**AI 기반 투자 성향 진단 및 맞춤형 포트폴리오 추천 플랫폼**

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [빠른 시작](#빠른-시작)
- [문서](#문서)
- [API 엔드포인트](#api-엔드포인트)
- [테스트](#테스트)
- [배포](#배포)
- [기여](#기여)

---

## 프로젝트 개요

KingoPortfolio는 사용자의 투자 성향을 AI로 분석하고, 맞춤형 포트폴리오를 추천하는 플랫폼입니다.

### 핵심 가치
- 🤖 **AI 기반 분석**: Claude AI를 활용한 정교한 투자 성향 분석
- 📊 **실시간 데이터**: Alpha Vantage 및 pykrx를 통한 실시간 주가 데이터
- 💰 **전문적인 분석**: DCF, DDM, 멀티플 밸류에이션 및 퀀트 분석
- 🔐 **안전한 인증**: JWT 기반 인증 및 RBAC 권한 관리
- 📁 **데이터 내보내기**: CSV/Excel 형식으로 진단 결과 다운로드
- 🚦 **API 보호**: Rate Limiting으로 브루트 포스 및 남용 방지

---

## 주요 기능

### 1. 인증 및 사용자 관리
- ✅ 회원가입/로그인 (JWT)
- ✅ 비밀번호 재설정 (이메일 토큰)
- ✅ 프로필 관리 (조회/수정/삭제)
- ✅ 비밀번호 변경
- ✅ RBAC (user, premium, admin)

### 2. 투자 성향 진단
- ✅ 6가지 질문 기반 설문
- ✅ AI 기반 투자 성향 분석
- ✅ 맞춤형 포트폴리오 추천
- ✅ 진단 이력 관리

### 3. 금융 데이터 분석
- ✅ 실시간 주가 데이터 수집
- ✅ 밸류에이션 분석 (DCF, DDM, 멀티플)
- ✅ 퀀트 분석 (베타, 샤프 비율, RSI)
- ✅ 뉴스 감성 분석

### 4. 데이터 내보내기
- ✅ CSV 다운로드
- ✅ Excel 다운로드 (스타일링)
- ✅ 진단 이력 일괄 내보내기

### 5. 관리자 기능
- ✅ 데이터 수집 관리
- ✅ 사용자 관리
- ✅ 시스템 모니터링

### 6. 보안 및 최적화
- ✅ API Rate Limiting (slowapi)
- ✅ CORS 설정
- ✅ 에러 핸들링
- ✅ SEO 최적화 랜딩 페이지

---

## 빠른 시작

### 사전 요구사항
- Python 3.11+
- SQLite (개발) 또는 PostgreSQL (프로덕션)
- Redis (프로덕션 Rate Limiting)

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/KingoPortfolio.git
cd KingoPortfolio/backend

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 SECRET_KEY 등 설정

# 5. 데이터베이스 초기화
python -c "from app.database import init_db; init_db()"

# 6. 마이그레이션 실행
python scripts/add_user_name_column.py
python scripts/migrate_user_roles.py

# 7. 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 환경변수

필수 환경변수 (`.env` 파일):

```env
# Database
DATABASE_URL=sqlite:///./kingo.db

# JWT
SECRET_KEY=your-secret-key-here-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys (선택)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
CLAUDE_API_KEY=your-claude-api-key

# Rate Limiting (프로덕션)
REDIS_URL=redis://localhost:6379

# 진행 로그
PROGRESS_HISTORY_LIMIT=200
```

---

## 문서

### 📚 개발 문서 (docs/development/)
- [**PROJECT_STATUS.md**](docs/development/PROJECT_STATUS.md) - 프로젝트 현황 및 로드맵
- [**CHANGELOG.md**](docs/development/CHANGELOG.md) - 버전 변경 이력
- [**TESTING.md**](docs/development/TESTING.md) - 테스트 가이드
- [**SESSION_SUMMARY_2025-12-29.md**](docs/development/SESSION_SUMMARY_2025-12-29.md) - 최근 개발 세션 요약

### 📖 사용 가이드 (docs/guides/)
- [**PROFILE.md**](docs/guides/PROFILE.md) - 사용자 프로필 관리 가이드
- [**PASSWORD_RESET.md**](docs/guides/PASSWORD_RESET.md) - 비밀번호 재설정 가이드
- [**EXPORT.md**](docs/guides/EXPORT.md) - 데이터 내보내기 (CSV/Excel)
- [**SEO.md**](docs/guides/SEO.md) - SEO 최적화 전략
- [**RATE_LIMITING.md**](docs/guides/RATE_LIMITING.md) - API Rate Limiting

### 📋 기술 레퍼런스 (docs/reference/)
- [**API_DOCUMENTATION.md**](docs/reference/API_DOCUMENTATION.md) - API 명세
- [**RBAC_IMPLEMENTATION.md**](docs/reference/RBAC_IMPLEMENTATION.md) - 역할 기반 접근 제어
- [**ERROR_HANDLING.md**](docs/reference/ERROR_HANDLING.md) - 에러 핸들링 시스템

---

## API 엔드포인트

### 인증 (Authentication)
```
POST   /auth/signup              # 회원가입
POST   /auth/login               # 로그인
POST   /auth/refresh             # 토큰 갱신
POST   /auth/forgot-password     # 비밀번호 재설정 요청
POST   /auth/reset-password      # 비밀번호 재설정
GET    /auth/profile             # 프로필 조회
PUT    /auth/profile             # 프로필 수정
PUT    /auth/change-password     # 비밀번호 변경
DELETE /auth/account             # 계정 삭제
```

### 진단 (Diagnosis)
```
POST   /diagnosis/submit                    # 진단 제출
GET    /diagnosis/history                   # 진단 이력
GET    /diagnosis/{id}                      # 진단 상세
GET    /diagnosis/{id}/export/csv           # CSV 내보내기
GET    /diagnosis/{id}/export/excel         # Excel 내보내기
GET    /diagnosis/history/export/csv        # 이력 CSV 내보내기
```

### 관리자 (Admin) - 인증 필요
```
GET    /admin/data-status                   # 데이터 상태
POST   /admin/collect-all                   # 전체 데이터 수집
GET    /admin/progress/{task_id}            # 진행 상황
GET    /admin/securities                    # 종목 목록
```

### 금융 분석 (Analysis) - 관리자 전용
```
GET    /analysis/financial/{ticker}         # 재무 분석
GET    /analysis/quant/{ticker}             # 퀀트 분석
GET    /analysis/valuation/{ticker}         # 밸류에이션
```

### 공개 (Public)
```
GET    /                                    # SEO 랜딩 페이지
GET    /robots.txt                          # 크롤러 규칙
GET    /sitemap.xml                         # 사이트맵
GET    /docs                                # API 문서 (Swagger)
GET    /health                              # 헬스 체크
```

자세한 내용은 [API_DOCUMENTATION.md](API_DOCUMENTATION.md)를 참조하세요.

---

## 테스트

### 테스트 실행

```bash
# 전체 테스트 (Rate Limit 간섭 있음)
pytest

# 특정 모듈
pytest tests/unit/test_auth.py

# 특정 테스트 클래스 (권장)
pytest tests/unit/test_auth.py::TestProfileEndpoints -v

# 커버리지 포함
pytest --cov=app --cov-report=html

# 상세 출력
pytest -v --tb=short
```

### 테스트 통계
- **총 테스트**: 143개
- **통과**: 108개 (75.5%)
- **스킵**: 3개
- **코드 커버리지**: 38%

자세한 내용은 [TESTING.md](TESTING.md)를 참조하세요.

---

## 배포

### 개발 환경
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션 환경

#### Docker 배포
```bash
# Docker 이미지 빌드
docker build -t kingo-portfolio-backend .

# 컨테이너 실행
docker run -d -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/kingo \
  -e SECRET_KEY=your-secret-key \
  -e REDIS_URL=redis://redis:6379 \
  kingo-portfolio-backend
```

#### 직접 배포
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. Gunicorn으로 실행
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 필수 설정 (프로덕션)
- ✅ Redis 설정 (Rate Limiting)
- ✅ PostgreSQL 설정 (SQLite 대신)
- ✅ HTTPS 인증서
- ✅ 환경변수 설정
- ✅ CORS 도메인 설정
- ✅ 로그 설정

자세한 내용은 [PROJECT_STATUS.md#배포](PROJECT_STATUS.md#서버-실행)를 참조하세요.

---

## 프로젝트 구조

```
backend/
├── app/
│   ├── routes/            # API 엔드포인트
│   │   ├── auth.py        # 인증 (회원가입, 로그인, 프로필)
│   │   ├── diagnosis.py   # 진단 (제출, 이력, 내보내기)
│   │   ├── admin.py       # 관리자 (데이터 수집, 모니터링)
│   │   └── survey.py      # 설문 (질문 관리)
│   ├── services/          # 비즈니스 로직
│   │   ├── alpha_vantage_client.py    # Alpha Vantage API
│   │   ├── alpha_vantage_loader.py    # 데이터 로더
│   │   ├── financial_analyzer.py      # 재무 분석
│   │   ├── pykrx_loader.py            # 한국 주식 데이터
│   │   ├── quant_analyzer.py          # 퀀트 분석
│   │   ├── valuation.py               # 밸류에이션
│   │   └── claude_service.py          # Claude AI 통합
│   ├── utils/             # 유틸리티
│   │   └── export.py      # CSV/Excel 생성
│   ├── templates/         # HTML 템플릿
│   │   └── landing.html   # SEO 랜딩 페이지
│   ├── models/            # 데이터베이스 모델
│   │   ├── user.py        # 사용자
│   │   ├── securities.py  # 증권
│   │   └── alpha_vantage.py  # Alpha Vantage 데이터
│   ├── auth.py            # JWT 인증
│   ├── crud.py            # CRUD 작업
│   ├── database.py        # DB 연결
│   ├── diagnosis.py       # 진단 로직
│   ├── error_handlers.py  # 에러 핸들러
│   ├── exceptions.py      # 커스텀 예외
│   ├── main.py            # FastAPI 앱
│   ├── rate_limiter.py    # Rate Limiting
│   └── schemas.py         # Pydantic 스키마
├── tests/
│   ├── unit/              # 단위 테스트
│   │   ├── test_auth.py
│   │   ├── test_profile.py
│   │   ├── test_export.py
│   │   ├── test_rate_limiting.py
│   │   └── ...
│   └── integration/       # 통합 테스트
├── scripts/               # 마이그레이션 스크립트
│   ├── add_user_name_column.py
│   └── migrate_user_roles.py
├── *.md                   # 문서 (12개)
├── requirements.txt       # 의존성
├── .env.example           # 환경변수 예제
└── kingo.db              # SQLite DB
```

---

## 기술 스택

### Backend Framework
- **FastAPI** 0.104+ - 고성능 웹 프레임워크
- **Uvicorn** - ASGI 서버
- **Pydantic** - 데이터 검증

### Database
- **SQLAlchemy** - ORM
- **SQLite** (개발) / **PostgreSQL** (프로덕션)
- **Alembic** - 마이그레이션 (추후)

### Authentication & Security
- **PyJWT** - JWT 토큰
- **bcrypt** - 비밀번호 해싱
- **slowapi** - Rate Limiting
- **python-multipart** - 파일 업로드

### Data & Analysis
- **pandas** - 데이터 분석
- **numpy** - 수치 계산
- **pykrx** - 한국 주식 데이터
- **yfinance** - 글로벌 주식 데이터
- **openpyxl** - Excel 생성

### External APIs
- **Alpha Vantage** - 주가 데이터
- **Claude AI** - 투자 성향 분석 (선택)

### Testing
- **pytest** - 테스트 프레임워크
- **pytest-cov** - 코드 커버리지
- **faker** - 테스트 데이터 생성

### Documentation
- **Swagger UI** - API 문서 (자동 생성)
- **ReDoc** - API 문서 (대체)

---

## 개발 팀

### 기여자
- **Claude Code (AI Assistant)** - 백엔드 개발, 문서화, 테스트

### 연락처
- Email: support@kingo-portfolio.com
- GitHub: https://github.com/yourusername/KingoPortfolio
- 문서: [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 기여 가이드

### 이슈 제출
버그 리포트나 기능 제안은 [GitHub Issues](https://github.com/yourusername/KingoPortfolio/issues)를 통해 제출해주세요.

### Pull Request
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### 커밋 메시지 규칙
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 변경
style: 코드 포맷팅 (기능 변경 없음)
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드 프로세스 등 기타 변경
```

---

## 변경 이력

최신 변경사항은 [CHANGELOG.md](CHANGELOG.md)를 참조하세요.

### 최근 릴리스

#### [1.0.0] - 2025-12-29
- ✅ 사용자 프로필 관리 시스템
- ✅ CSV/Excel 데이터 내보내기
- ✅ SEO 최적화 랜딩 페이지
- ✅ API Rate Limiting
- ✅ 종합 문서 작성 (12개 문서, 5,424줄)

---

## FAQ

### Q: 프로덕션 배포는 어떻게 하나요?
A: [PROJECT_STATUS.md#서버-실행](PROJECT_STATUS.md#서버-실행) 섹션을 참조하세요. Redis, PostgreSQL, HTTPS 설정이 필요합니다.

### Q: 테스트가 실패하는데 어떻게 하나요?
A: Rate Limit 간섭 문제일 수 있습니다. 테스트 클래스별로 개별 실행해보세요:
```bash
pytest tests/unit/test_auth.py::TestProfileEndpoints -v
```

### Q: API Rate Limit을 비활성화할 수 있나요?
A: 테스트 환경에서만 가능하도록 향후 추가 예정입니다. 현재는 `app/rate_limiter.py`에서 `default_limits`를 높게 설정하세요.

### Q: Claude AI 없이도 작동하나요?
A: 네, Claude API 키가 없어도 기본 진단 로직으로 작동합니다. 다만 AI 분석 기능은 제한됩니다.

---

## 감사의 말

- **FastAPI** - 훌륭한 웹 프레임워크
- **Alpha Vantage** - 금융 데이터 제공
- **pykrx** - 한국 주식 데이터
- **slowapi** - Rate Limiting 라이브러리

---

**KingoPortfolio** - AI 기반 투자 성향 진단 플랫폼 🚀

*마지막 업데이트: 2025-12-29*
