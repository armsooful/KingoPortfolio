# KingoPortfolio 스크립트 모음

이 폴더는 KingoPortfolio 프로젝트의 유틸리티 스크립트와 테스트 파일을 포함합니다.

## 📁 스크립트 목록

### 서버 관리
- **start_servers.sh** - 백엔드 및 프론트엔드 서버 시작
  ```bash
  ./scripts/start_servers.sh
  ```

### 데이터베이스 관리
- **view_db.sh** - 데이터베이스 조회 및 확인
  ```bash
  ./scripts/view_db.sh all        # 모든 데이터 조회
  ./scripts/view_db.sh stocks     # 주식 데이터만
  ./scripts/view_db.sh users      # 사용자 목록
  ./scripts/view_db.sh schema     # 스키마 확인
  ```

### 시스템 점검
- **check_system.sh** - 시스템 환경 및 의존성 확인
  ```bash
  ./scripts/check_system.sh
  ```

### 코드 품질
- **forbidden_terms_check.sh** - 금지어 스캔 (규제 준수)
  ```bash
  ./scripts/forbidden_terms_check.sh
  ```

### 테스트 스크립트
- **test_api.py** - API 엔드포인트 테스트
  ```bash
  cd /Users/changrim/KingoPortfolio
  /Users/changrim/KingoPortfolio/venv/bin/python scripts/test_api.py
  ```

- **test_data_collector.py** - 데이터 수집 기능 테스트
  ```bash
  /Users/changrim/KingoPortfolio/venv/bin/python scripts/test_data_collector.py
  ```

- **test_data_classifier.py** - 데이터 분류 기능 테스트
  ```bash
  /Users/changrim/KingoPortfolio/venv/bin/python scripts/test_data_classifier.py
  ```

## 🚀 빠른 사용법

### 1. 프로젝트 시작
```bash
# 서버 시작
./scripts/start_servers.sh
```

### 2. 데이터베이스 확인
```bash
# 전체 데이터 개수 확인
./scripts/view_db.sh count

# 주식 데이터 상세 조회
./scripts/view_db.sh stocks
```

### 3. 시스템 점검
```bash
# 환경 확인
./scripts/check_system.sh
```

### 4. API 테스트
```bash
# API 엔드포인트 테스트
/Users/changrim/KingoPortfolio/venv/bin/python scripts/test_api.py
```

## 📝 스크립트 설명

### start_servers.sh
백엔드(FastAPI)와 프론트엔드(Vite) 서버를 자동으로 시작합니다.

**기능**:
- 기존 실행 중인 서버 확인 및 종료
- 백엔드 서버 시작 (포트 8000)
- 프론트엔드 서버 시작 안내 (포트 5173)

### view_db.sh
SQLite 데이터베이스를 쉽게 조회할 수 있는 인터랙티브 스크립트입니다.

**기능**:
- 전체/개별 테이블 조회
- 데이터 개수 확인
- 스키마 확인

### check_system.sh
시스템 환경과 필요한 의존성이 올바르게 설치되었는지 확인합니다.

**확인 항목**:
- Python 버전
- Node.js/npm 버전
- 가상환경 활성화 상태
- 필수 패키지 설치 여부

### test_api.py
FastAPI 백엔드의 주요 엔드포인트를 테스트합니다.

**테스트 항목**:
- 회원가입 API
- 로그인 API
- 인증 토큰 검증
- 관리자 기능

### test_data_collector.py
yfinance를 사용한 데이터 수집 기능을 테스트합니다.

**테스트 항목**:
- 주식 데이터 수집
- ETF 데이터 수집
- 데이터 유효성 검증

### test_data_classifier.py
투자 상품 분류 및 추천 로직을 테스트합니다.

**테스트 항목**:
- 위험도 분류
- 상품 추천 알고리즘
- 포트폴리오 구성

### forbidden_terms_check.sh
자본시장법 준수를 위해 금지된 용어("추천", "보장" 등)를 코드에서 검사합니다.

**기능**:
- frontend/src 및 backend/app 디렉토리 스캔
- 금지어 목록은 docs/forbidden_terms.md에서 관리
- 면책 조항, 부정문 등 예외 자동 필터링
- CI/pre-commit 연동 가능

**사용법**:
```bash
# 전체 검사
./scripts/forbidden_terms_check.sh

# 특정 디렉토리만 검사
./scripts/forbidden_terms_check.sh frontend/src
```

**pre-commit 훅 설정** (선택):
```bash
# .git/hooks/pre-commit 파일 생성
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/forbidden_terms_check.sh
EOF
chmod +x .git/hooks/pre-commit
```

## ⚙️ 실행 권한 설정

스크립트 실행 권한이 필요한 경우:

```bash
chmod +x scripts/*.sh
```

## 🔗 관련 문서

- [빠른 시작 가이드](../manuals/QUICK_START.md)
- [데이터베이스 가이드](../manuals/DATABASE_GUIDE.md)
- [테스트 가이드](../manuals/TEST_GUIDE.md)

---

**위치**: `/scripts/`
**프로젝트 루트**: `/`
