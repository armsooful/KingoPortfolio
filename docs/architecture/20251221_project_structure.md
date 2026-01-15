# 📂 KingoPortfolio 프로젝트 구조 정리

## ✅ 정리 완료 (2025-12-21)

프로젝트의 모든 파일과 문서가 체계적으로 정리되었습니다.

## 📊 정리 결과

### Before (정리 전)
```
KingoPortfolio/
├── ❌ 11개 매뉴얼 파일들이 루트에 흩어져 있음
├── ❌ 6개 스크립트 파일들이 루트에 있음
├── ❌ 중복 파일 (README_수정완료.md)
└── ❌ 사용하지 않는 파일 (cleanup_imports.py)
```

### After (정리 후)
```
KingoPortfolio/
├── ✅ README.md (업데이트됨)
├── ✅ Dockerfile
│
├── docs/
│   ├── manuals/              # 📚 모든 매뉴얼 (12개)
│   │   ├── README.md         # 매뉴얼 인덱스
│   │   ├── QUICK_START.md
│   │   ├── DATA_COLLECTION_GUIDE.md
│   │   ├── PROGRESS_MONITORING_GUIDE.md
│   │   ├── DATABASE_GUIDE.md
│   │   ├── ADMIN_TROUBLESHOOTING.md
│   │   ├── LOGIN_DEBUG_GUIDE.md
│   │   ├── LOGIN_FIX_SUMMARY.md
│   │   ├── CLAUDE_API_SETUP.md
│   │   ├── TEST_GUIDE.md
│   │   ├── VERIFICATION_GUIDE.md
│   │   └── YFINANCE_FIX_SUMMARY.md
│   │
│   └── 20251217/             # 프로젝트 문서
│
├── scripts/                  # 🛠️ 모든 스크립트 (7개)
│   ├── README.md             # 스크립트 가이드
│   ├── start_servers.sh      # 서버 시작
│   ├── view_db.sh            # DB 조회
│   ├── check_system.sh       # 시스템 점검
│   ├── test_api.py           # API 테스트
│   ├── test_data_collector.py
│   └── test_data_classifier.py
│
├── backend/
│   └── app/
│
└── frontend/
    └── src/
```

## 🗑️ 삭제된 파일

### 1. 중복/불필요 파일
- ❌ `README_수정완료.md` - 중복 README
- ❌ `backend/cleanup_imports.py` - 사용하지 않는 스크립트

## 📁 이동된 파일

### 매뉴얼 (루트 → docs/manuals/)
1. ✅ ADMIN_TROUBLESHOOTING.md
2. ✅ CLAUDE_API_SETUP.md
3. ✅ DATABASE_GUIDE.md
4. ✅ DATA_COLLECTION_GUIDE.md
5. ✅ LOGIN_DEBUG_GUIDE.md
6. ✅ LOGIN_FIX_SUMMARY.md
7. ✅ PROGRESS_MONITORING_GUIDE.md
8. ✅ QUICK_START.md
9. ✅ TEST_GUIDE.md
10. ✅ VERIFICATION_GUIDE.md
11. ✅ YFINANCE_FIX_SUMMARY.md

### 스크립트 (루트 → scripts/)
1. ✅ check_system.sh
2. ✅ start_servers.sh
3. ✅ view_db.sh
4. ✅ test_api.py
5. ✅ test_data_classifier.py
6. ✅ test_data_collector.py

## 📝 생성된 파일

### 인덱스/가이드 파일
1. ✅ `docs/manuals/README.md` - 매뉴얼 인덱스 및 사용 가이드
2. ✅ `scripts/README.md` - 스크립트 사용 가이드
3. ✅ `PROJECT_STRUCTURE.md` - 이 파일

## 🔄 업데이트된 파일

### README.md
- ✅ 프로젝트 구조 섹션 업데이트
- ✅ 새로운 파일들 (progress_tracker.py, ProgressBar.jsx 등) 반영
- ✅ docs/manuals, scripts 폴더 추가
- ✅ "추가 리소스" 섹션 개선
- ✅ 최근 변경사항 업데이트 (2025-12-21)

## 📚 사용 방법

### 1. 매뉴얼 찾기

모든 매뉴얼은 `docs/manuals/` 폴더에 있습니다:

```bash
# 인덱스 확인
cat docs/manuals/README.md

# 빠른 시작 가이드
cat docs/manuals/QUICK_START.md

# 데이터 수집 가이드
cat docs/manuals/DATA_COLLECTION_GUIDE.md
```

### 2. 스크립트 실행

모든 스크립트는 `scripts/` 폴더에 있습니다:

```bash
# 서버 시작
./scripts/start_servers.sh

# DB 조회
./scripts/view_db.sh all

# 시스템 점검
./scripts/check_system.sh

# API 테스트
/Users/changrim/KingoPortfolio/venv/bin/python scripts/test_api.py
```

## 🎯 폴더별 용도

### `/` (루트)
- **목적**: 프로젝트 메타 파일만 포함
- **파일**:
  - `README.md` - 프로젝트 메인 문서
  - `Dockerfile` - Docker 설정
  - `.gitignore` - Git 설정

### `/docs/manuals/`
- **목적**: 모든 사용 매뉴얼 및 가이드
- **카테고리**:
  - 시작 가이드 (QUICK_START.md)
  - 기능 가이드 (DATA_COLLECTION_GUIDE.md, PROGRESS_MONITORING_GUIDE.md 등)
  - 문제 해결 (ADMIN_TROUBLESHOOTING.md, LOGIN_DEBUG_GUIDE.md)
  - 기술 문서 (YFINANCE_FIX_SUMMARY.md, LOGIN_FIX_SUMMARY.md)

### `/scripts/`
- **목적**: 개발 및 운영 스크립트
- **카테고리**:
  - 서버 관리 (start_servers.sh)
  - DB 관리 (view_db.sh)
  - 테스트 (test_*.py)
  - 시스템 점검 (check_system.sh)

### `/docs/20251217/`
- **목적**: 프로젝트 계획 및 기술 문서
- **파일**:
  - 프로젝트 최종 보고서
  - 기술 아키텍처 문서
  - 운영 및 유지보수 가이드

### `/backend/`
- **목적**: FastAPI 백엔드 소스 코드
- **구조**: 표준 FastAPI 프로젝트 구조

### `/frontend/`
- **목적**: React + Vite 프론트엔드 소스 코드
- **구조**: 표준 React 프로젝트 구조

## 🔍 빠른 참조

### 자주 사용하는 매뉴얼

| 상황 | 매뉴얼 |
|------|--------|
| 프로젝트를 처음 시작할 때 | [QUICK_START.md](docs/manuals/QUICK_START.md) |
| 데이터를 수집하고 싶을 때 | [DATA_COLLECTION_GUIDE.md](docs/manuals/DATA_COLLECTION_GUIDE.md) |
| 진행 상황을 모니터링하고 싶을 때 | [PROGRESS_MONITORING_GUIDE.md](docs/manuals/PROGRESS_MONITORING_GUIDE.md) |
| DB를 확인하고 싶을 때 | [DATABASE_GUIDE.md](docs/manuals/DATABASE_GUIDE.md) |
| 관리자 페이지 문제 | [ADMIN_TROUBLESHOOTING.md](docs/manuals/ADMIN_TROUBLESHOOTING.md) |
| 로그인 문제 | [LOGIN_DEBUG_GUIDE.md](docs/manuals/LOGIN_DEBUG_GUIDE.md) |
| 테스트를 실행하고 싶을 때 | [TEST_GUIDE.md](docs/manuals/TEST_GUIDE.md) |

### 자주 사용하는 스크립트

| 작업 | 명령어 |
|------|--------|
| 서버 시작 | `./scripts/start_servers.sh` |
| 전체 DB 조회 | `./scripts/view_db.sh all` |
| 주식 데이터만 조회 | `./scripts/view_db.sh stocks` |
| 시스템 점검 | `./scripts/check_system.sh` |
| API 테스트 | `python scripts/test_api.py` |

## ✨ 개선 사항

### 1. 명확한 구조
- ✅ 루트 디렉토리가 깔끔해짐 (2개 파일만)
- ✅ 모든 매뉴얼이 한 곳에 모임
- ✅ 모든 스크립트가 한 곳에 모임

### 2. 찾기 쉬움
- ✅ 매뉴얼 인덱스 파일 제공 (docs/manuals/README.md)
- ✅ 스크립트 가이드 제공 (scripts/README.md)
- ✅ 업데이트된 프로젝트 README

### 3. 유지보수 용이
- ✅ 일관된 파일 위치
- ✅ 명확한 역할 구분
- ✅ 중복 파일 제거

## 📌 주의사항

### Git 관련
정리된 파일들을 Git에 반영하려면:

```bash
# 변경사항 확인
git status

# 변경사항 스테이징
git add .

# 커밋
git commit -m "docs: Reorganize project structure

- Move all manuals to docs/manuals/
- Move all scripts to scripts/
- Create index files (README.md) for both folders
- Update main README.md with new structure
- Remove duplicate and unused files"

# 푸시
git push
```

### 링크 업데이트
기존에 루트의 매뉴얼을 참조하던 링크들은 자동으로 업데이트되지 않습니다.
필요시 수동으로 업데이트해야 합니다:

```
Before: ./QUICK_START.md
After:  ./docs/manuals/QUICK_START.md
```

## 🔗 관련 문서

- [메인 README](README.md)
- [매뉴얼 인덱스](docs/manuals/README.md)
- [스크립트 가이드](scripts/README.md)

---

**정리 완료일**: 2025-12-21
**상태**: ✅ 완료
**다음 작업**: Git 커밋 및 푸시
