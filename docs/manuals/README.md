# KingoPortfolio 사용 매뉴얼 모음

이 폴더는 KingoPortfolio 프로젝트의 모든 사용 매뉴얼과 가이드 문서를 포함합니다.

## 📚 목차

### 시작하기
- [QUICK_START.md](QUICK_START.md) - 빠른 시작 가이드

### 핵심 기능 가이드
- [DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md) - 데이터 수집 전체 가이드
- [PROGRESS_MONITORING_GUIDE.md](PROGRESS_MONITORING_GUIDE.md) - 실시간 진행 상황 모니터링
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - 데이터베이스 조회 및 관리

### 관리자 기능
- [ADMIN_TROUBLESHOOTING.md](ADMIN_TROUBLESHOOTING.md) - 관리자 페이지 문제 해결

### 인증 및 보안
- [LOGIN_FIX_SUMMARY.md](LOGIN_FIX_SUMMARY.md) - 로그인 버그 수정 내역
- [LOGIN_DEBUG_GUIDE.md](LOGIN_DEBUG_GUIDE.md) - 로그인 문제 디버깅

### API 및 통합
- [CLAUDE_API_SETUP.md](CLAUDE_API_SETUP.md) - Claude API 설정 가이드

### 테스트 및 검증
- [TEST_GUIDE.md](TEST_GUIDE.md) - 테스트 가이드
- [VERIFICATION_GUIDE.md](VERIFICATION_GUIDE.md) - 검증 가이드

### 기술 문서
- [YFINANCE_FIX_SUMMARY.md](YFINANCE_FIX_SUMMARY.md) - yfinance 라이브러리 수정 내역

## 📂 문서 분류

### 사용자 매뉴얼
1. QUICK_START.md
2. DATA_COLLECTION_GUIDE.md
3. PROGRESS_MONITORING_GUIDE.md
4. DATABASE_GUIDE.md

### 관리자 매뉴얼
1. ADMIN_TROUBLESHOOTING.md
2. LOGIN_DEBUG_GUIDE.md

### 개발자 문서
1. CLAUDE_API_SETUP.md
2. TEST_GUIDE.md
3. VERIFICATION_GUIDE.md
4. LOGIN_FIX_SUMMARY.md
5. YFINANCE_FIX_SUMMARY.md

## 🔧 스크립트 및 도구

모든 실행 스크립트는 `/scripts/` 폴더로 이동되었습니다:
- `scripts/start_servers.sh` - 서버 시작 스크립트
- `scripts/view_db.sh` - 데이터베이스 조회 스크립트
- `scripts/check_system.sh` - 시스템 점검 스크립트
- `scripts/test_*.py` - 테스트 스크립트들

## 📖 추천 읽기 순서

### 처음 사용하는 경우
1. [QUICK_START.md](QUICK_START.md) - 프로젝트 시작
2. [DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md) - 데이터 수집 방법
3. [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - 데이터 확인 방법

### 문제가 발생한 경우
1. [ADMIN_TROUBLESHOOTING.md](ADMIN_TROUBLESHOOTING.md) - 일반적인 문제
2. [LOGIN_DEBUG_GUIDE.md](LOGIN_DEBUG_GUIDE.md) - 로그인 문제

### 개발자인 경우
1. [TEST_GUIDE.md](TEST_GUIDE.md) - 테스트 방법
2. [VERIFICATION_GUIDE.md](VERIFICATION_GUIDE.md) - 검증 절차
3. 기술 문서들 (LOGIN_FIX_SUMMARY.md, YFINANCE_FIX_SUMMARY.md)

## 🆕 최근 업데이트

- **2024-12-21**: PROGRESS_MONITORING_GUIDE.md - 실시간 진행 상황 모니터링 기능 추가
- **2024-12-20**: LOGIN_FIX_SUMMARY.md - 로그인 email/username 매핑 문제 수정
- **2024-12-20**: YFINANCE_FIX_SUMMARY.md - yfinance datetime 호환성 문제 해결
- **2024-12-20**: DATABASE_GUIDE.md - 데이터베이스 조회 가이드 추가

---

**문서 위치**: `/docs/manuals/`
**스크립트 위치**: `/scripts/`
**프로젝트 루트 README**: `/README.md`
