# KingoPortfolio 사용 매뉴얼 모음
최초작성일자: 2025-12-21
최종수정일자: 2026-01-18

이 폴더는 KingoPortfolio 프로젝트의 모든 사용 매뉴얼과 가이드 문서를 포함합니다.

## 📚 목차

### 시작하기
- [20251220_quick_start.md](20251220_quick_start.md) - 빠른 시작 가이드

### 핵심 기능 가이드
- [20251219_data_collection_guide.md](20251219_data_collection_guide.md) - 데이터 수집 전체 가이드
- [20251221_progress_monitoring_guide.md](20251221_progress_monitoring_guide.md) - 실시간 진행 상황 모니터링
- [20251220_database_guide.md](20251220_database_guide.md) - 데이터베이스 조회 및 관리

### 관리자 기능
- [20251219_admin_troubleshooting.md](20251219_admin_troubleshooting.md) - 관리자 페이지 문제 해결

### 인증 및 보안
- [20251221_login_fix_summary.md](20251221_login_fix_summary.md) - 로그인 버그 수정 내역
- [20251220_login_debug_guide.md](20251220_login_debug_guide.md) - 로그인 문제 디버깅

### API 및 통합
- [20251219_claude_api_setup.md](20251219_claude_api_setup.md) - Claude API 설정 가이드

### 테스트 및 검증
- [20251219_test_guide.md](20251219_test_guide.md) - 테스트 가이드
- [20251220_verification_guide.md](20251220_verification_guide.md) - 검증 가이드

### 기술 문서
- [20251220_yfinance_fix_summary.md](20251220_yfinance_fix_summary.md) - yfinance 라이브러리 수정 내역

## 📂 문서 분류

### 사용자 매뉴얼
1. 20251220_quick_start.md
2. 20251219_data_collection_guide.md
3. 20251221_progress_monitoring_guide.md
4. 20251220_database_guide.md

### 관리자 매뉴얼
1. 20251219_admin_troubleshooting.md
2. 20251220_login_debug_guide.md

### 개발자 문서
1. 20251219_claude_api_setup.md
2. 20251219_test_guide.md
3. 20251220_verification_guide.md
4. 20251221_login_fix_summary.md
5. 20251220_yfinance_fix_summary.md

## 🔧 스크립트 및 도구

모든 실행 스크립트는 `/scripts/` 폴더로 이동되었습니다:
- `scripts/start_servers.sh` - 서버 시작 스크립트
- `scripts/view_db.sh` - 데이터베이스 조회 스크립트
- `scripts/check_system.sh` - 시스템 점검 스크립트
- `scripts/test_*.py` - 테스트 스크립트들

## 📖 추천 읽기 순서

### 처음 사용하는 경우
1. [20251220_quick_start.md](20251220_quick_start.md) - 프로젝트 시작
2. [20251219_data_collection_guide.md](20251219_data_collection_guide.md) - 데이터 수집 방법
3. [20251220_database_guide.md](20251220_database_guide.md) - 데이터 확인 방법

### 문제가 발생한 경우
1. [20251219_admin_troubleshooting.md](20251219_admin_troubleshooting.md) - 일반적인 문제
2. [20251220_login_debug_guide.md](20251220_login_debug_guide.md) - 로그인 문제

### 개발자인 경우
1. [20251219_test_guide.md](20251219_test_guide.md) - 테스트 방법
2. [20251220_verification_guide.md](20251220_verification_guide.md) - 검증 절차
3. 기술 문서들 (20251221_login_fix_summary.md, 20251220_yfinance_fix_summary.md)

## 🆕 최근 업데이트

- **2024-12-21**: 20251221_progress_monitoring_guide.md - 실시간 진행 상황 모니터링 기능 추가
- **2024-12-20**: 20251221_login_fix_summary.md - 로그인 email/username 매핑 문제 수정
- **2024-12-20**: 20251220_yfinance_fix_summary.md - yfinance datetime 호환성 문제 해결
- **2024-12-20**: 20251220_database_guide.md - 데이터베이스 조회 가이드 추가

---

**문서 위치**: `/docs/manuals/`
**스크립트 위치**: `/scripts/`
**프로젝트 루트 README**: `/20251221_manuals_index.md`
