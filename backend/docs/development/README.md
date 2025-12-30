# 개발 문서 (Development)

프로젝트 관리, 개발 프로세스, 테스트 관련 문서 모음

---

## 📑 문서 목록

### [PROJECT_STATUS.md](PROJECT_STATUS.md)
**프로젝트 현황 및 로드맵**

- 프로젝트 전체 개요
- 현재 구현된 기능 (8개 카테고리)
- 기술 스택
- 프로젝트 구조
- 테스트 현황 (143개 테스트)
- 다음 단계 (우선순위별)
- 알려진 이슈

**대상**: 전체 팀, 신규 개발자
**업데이트 빈도**: 주요 기능 추가/변경 시

---

### [CHANGELOG.md](CHANGELOG.md)
**버전별 변경 이력**

- 버전별 변경사항 (Added, Changed, Fixed, Security)
- 파일 통계
- 의존성 변경
- 마이그레이션 기록

**대상**: 전체 팀
**업데이트 빈도**: 매 릴리스

---

### [TESTING.md](TESTING.md)
**테스트 전략 및 실행 가이드**

- 테스트 구조
- 테스트 실행 방법
- 픽스처 사용법
- 커버리지 확인
- CI/CD 통합

**대상**: 백엔드 개발자
**업데이트 빈도**: 테스트 전략 변경 시

---

### [SESSION_SUMMARY_YYYY-MM-DD.md](SESSION_SUMMARY_2025-12-29.md)
**개발 세션별 상세 요약**

- 세션 목표 및 완료 작업
- 코드 통계
- 문제 해결 과정
- 배운 점
- 다음 세션 계획

**대상**: 개발 팀, 프로젝트 관리자
**생성 시점**: 주요 개발 세션 완료 후

---

## 🎯 사용 시나리오

### 신규 개발자 온보딩
1. PROJECT_STATUS.md 읽기 (전체 프로젝트 파악)
2. 최신 SESSION_SUMMARY 읽기 (최근 작업 이해)
3. TESTING.md로 테스트 환경 설정

### 기능 개발 시작 전
1. CHANGELOG.md로 관련 기능의 변경 이력 확인
2. PROJECT_STATUS.md의 "다음 단계" 섹션 확인
3. 해당 기능의 guides/ 문서 읽기

### 버그 수정 시
1. CHANGELOG.md에서 해당 기능의 이전 변경사항 확인
2. PROJECT_STATUS.md의 "알려진 이슈" 확인
3. TESTING.md로 관련 테스트 실행

### 릴리스 준비
1. CHANGELOG.md 업데이트
2. PROJECT_STATUS.md 업데이트 (테스트 현황, 알려진 이슈)
3. 새로운 SESSION_SUMMARY 작성 (선택)

---

## 📝 문서 작성 가이드

### PROJECT_STATUS.md 업데이트 시기
- ✅ 새로운 주요 기능 추가
- ✅ 기술 스택 변경
- ✅ 프로젝트 구조 변경
- ✅ 테스트 통계 변경 (주요 변경 시)
- ✅ 다음 단계 우선순위 변경

### CHANGELOG.md 작성 규칙
```markdown
## [버전] - YYYY-MM-DD

### Added
- 완전히 새로운 기능

### Changed
- 기존 기능 변경

### Deprecated
- 곧 제거될 기능

### Removed
- 제거된 기능

### Fixed
- 버그 수정

### Security
- 보안 관련 변경
```

### TESTING.md 업데이트 시기
- ✅ 새로운 테스트 전략 도입
- ✅ 테스트 구조 변경
- ✅ 새로운 픽스처 추가
- ✅ CI/CD 설정 변경

### SESSION_SUMMARY 작성 시기
- ✅ 주요 기능 구현 완료 후
- ✅ 대규모 리팩토링 후
- ✅ 프로젝트 마일스톤 달성 후
- ✅ 주요 버그 수정 완료 후

---

## 🔍 빠른 참조

### 프로젝트 현황 확인
```bash
# 전체 프로젝트 상태
cat PROJECT_STATUS.md | grep "##"

# 테스트 현황
cat PROJECT_STATUS.md | grep -A 20 "테스트 현황"

# 알려진 이슈
cat PROJECT_STATUS.md | grep -A 10 "알려진 이슈"
```

### 최신 변경사항 확인
```bash
# 최신 버전 변경사항
head -n 50 CHANGELOG.md

# 특정 기능 변경 이력
grep -A 5 "프로필" CHANGELOG.md
```

### 테스트 실행
```bash
# TESTING.md에서 테스트 명령어 추출
grep "pytest" TESTING.md
```

---

## 📊 문서 통계

| 문서 | 라인 수 | 용량 | 마지막 업데이트 |
|------|---------|------|-----------------|
| PROJECT_STATUS.md | 620줄 | 27KB | 2025-12-29 |
| CHANGELOG.md | 350줄 | 8KB | 2025-12-29 |
| TESTING.md | 300줄 | 9KB | 2024-12-20 |
| SESSION_SUMMARY_2025-12-29.md | 800줄 | 16KB | 2025-12-29 |

---

**마지막 업데이트**: 2025-12-29
