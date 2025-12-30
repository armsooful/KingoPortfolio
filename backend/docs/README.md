# KingoPortfolio 문서 인덱스

KingoPortfolio 백엔드 프로젝트의 모든 문서는 성격에 따라 다음과 같이 분류되어 있습니다.

---

## 📁 문서 구조

```
docs/
├── development/     # 개발 프로세스 및 프로젝트 관리 문서
├── guides/          # 기능별 사용 가이드
└── reference/       # 기술 레퍼런스 및 API 명세
```

---

## 📚 개발 문서 (development/)

프로젝트 관리, 개발 프로세스, 테스트 관련 문서

| 문서 | 설명 | 용도 |
|------|------|------|
| [PROJECT_STATUS.md](development/PROJECT_STATUS.md) | 프로젝트 현황 및 로드맵 | 프로젝트 전체 개요 파악 |
| [CHANGELOG.md](development/CHANGELOG.md) | 버전별 변경 이력 | 릴리스 노트 및 변경사항 추적 |
| [TESTING.md](development/TESTING.md) | 테스트 전략 및 실행 가이드 | 테스트 작성 및 실행 방법 |
| [SESSION_SUMMARY_*.md](development/) | 개발 세션별 상세 요약 | 특정 개발 기간의 작업 내용 |

### 주요 사용 시나리오
- **신규 개발자 온보딩**: PROJECT_STATUS.md로 시작
- **기능 구현 전**: CHANGELOG.md로 이전 변경사항 확인
- **테스트 작성**: TESTING.md 참조
- **이전 작업 파악**: SESSION_SUMMARY 파일 검토

---

## 📖 사용 가이드 (guides/)

기능별 사용 방법 및 구현 가이드

| 문서 | 기능 | 대상 독자 |
|------|------|-----------|
| [PROFILE.md](guides/PROFILE.md) | 사용자 프로필 관리 | 백엔드/프론트엔드 개발자 |
| [PASSWORD_RESET.md](guides/PASSWORD_RESET.md) | 비밀번호 재설정 | 백엔드/프론트엔드 개발자 |
| [EXPORT.md](guides/EXPORT.md) | 데이터 내보내기 (CSV/Excel) | 백엔드 개발자 |
| [SEO.md](guides/SEO.md) | SEO 최적화 전략 | 프론트엔드/마케팅 |
| [RATE_LIMITING.md](guides/RATE_LIMITING.md) | API Rate Limiting | 백엔드 개발자 |

### 주요 사용 시나리오
- **새 기능 구현**: 해당 기능의 가이드 문서 참조
- **API 통합**: 프론트엔드 개발자가 백엔드 기능 이해
- **문제 해결**: 각 가이드의 "문제 해결" 섹션 활용

---

## 📋 기술 레퍼런스 (reference/)

API 명세, 시스템 아키텍처, 기술 상세 문서

| 문서 | 내용 | 참조 빈도 |
|------|------|-----------|
| [API_DOCUMENTATION.md](reference/API_DOCUMENTATION.md) | 전체 API 엔드포인트 명세 | ⭐⭐⭐⭐⭐ |
| [RBAC_IMPLEMENTATION.md](reference/RBAC_IMPLEMENTATION.md) | 역할 기반 접근 제어 | ⭐⭐⭐⭐ |
| [ERROR_HANDLING.md](reference/ERROR_HANDLING.md) | 에러 핸들링 시스템 | ⭐⭐⭐ |

### 주요 사용 시나리오
- **API 호출**: API_DOCUMENTATION.md로 엔드포인트 확인
- **권한 구현**: RBAC_IMPLEMENTATION.md 참조
- **에러 처리**: ERROR_HANDLING.md로 표준 에러 코드 확인

---

## 🚀 빠른 시작 가이드

### 1. 처음 시작하는 개발자

```
1. README.md (프로젝트 루트) - 프로젝트 개요
2. docs/development/PROJECT_STATUS.md - 현재 상태 파악
3. docs/reference/API_DOCUMENTATION.md - API 구조 이해
4. 관심 기능의 docs/guides/*.md - 구체적 구현 방법
```

### 2. 기능 구현 시작

```
1. docs/development/CHANGELOG.md - 최근 변경사항 확인
2. docs/guides/[해당기능].md - 기능별 가이드 읽기
3. docs/reference/API_DOCUMENTATION.md - API 엔드포인트 확인
4. docs/development/TESTING.md - 테스트 작성
```

### 3. 버그 수정

```
1. docs/reference/ERROR_HANDLING.md - 에러 코드 확인
2. 관련 docs/guides/*.md - 기능 이해
3. docs/development/TESTING.md - 테스트 실행
```

### 4. 프론트엔드 통합

```
1. docs/reference/API_DOCUMENTATION.md - API 명세
2. docs/guides/PROFILE.md - 프로필 기능
3. docs/guides/PASSWORD_RESET.md - 비밀번호 재설정
4. docs/reference/RBAC_IMPLEMENTATION.md - 권한 체계
```

---

## 📝 문서 작성 규칙

### 파일 명명 규칙

| 폴더 | 파일명 형식 | 예시 |
|------|------------|------|
| development/ | `대문자_스네이크_케이스.md` | `PROJECT_STATUS.md` |
| development/ | `SESSION_SUMMARY_YYYY-MM-DD.md` | `SESSION_SUMMARY_2025-12-29.md` |
| guides/ | `대문자_스네이크_케이스.md` | `PROFILE.md` |
| reference/ | `대문자_스네이크_케이스.md` | `API_DOCUMENTATION.md` |

### 문서 분류 기준

#### development/ 에 들어갈 문서
- ✅ 프로젝트 전체 현황
- ✅ 버전 변경 이력
- ✅ 테스트 전략
- ✅ 개발 세션 요약
- ✅ CI/CD 설정
- ✅ 배포 가이드

#### guides/ 에 들어갈 문서
- ✅ 특정 기능의 사용 방법
- ✅ 구현 가이드
- ✅ 튜토리얼
- ✅ 모범 사례 (Best Practices)
- ✅ 문제 해결 (Troubleshooting)

#### reference/ 에 들어갈 문서
- ✅ API 명세
- ✅ 데이터베이스 스키마
- ✅ 시스템 아키텍처
- ✅ 기술 상세 (예: RBAC, 에러 핸들링)
- ✅ 코드 컨벤션

### 문서 템플릿

#### 가이드 문서 (guides/)
```markdown
# [기능명] 가이드

## 개요
[기능 설명]

## 주요 기능
- 기능 1
- 기능 2

## 사용 방법
### 1. [단계 1]
### 2. [단계 2]

## API 엔드포인트
### [엔드포인트 1]

## 예제 코드

## 문제 해결

## 관련 문서
```

#### 레퍼런스 문서 (reference/)
```markdown
# [시스템/API명] 레퍼런스

## 개요

## 아키텍처

## API 명세
### [엔드포인트 1]
- Method:
- Path:
- Parameters:
- Response:

## 기술 상세

## 참고 자료
```

---

## 🔍 검색 팁

### 키워드로 문서 찾기

```bash
# 모든 문서에서 키워드 검색
grep -r "키워드" docs/

# 특정 카테고리에서만 검색
grep -r "인증" docs/guides/

# 파일명으로 검색
find docs/ -name "*PROFILE*"
```

### 자주 찾는 주제별 문서

| 주제 | 문서 |
|------|------|
| 인증/로그인 | guides/PROFILE.md, reference/RBAC_IMPLEMENTATION.md |
| 데이터 내보내기 | guides/EXPORT.md |
| API 사용법 | reference/API_DOCUMENTATION.md |
| 테스트 | development/TESTING.md |
| 에러 처리 | reference/ERROR_HANDLING.md |
| SEO | guides/SEO.md |
| Rate Limiting | guides/RATE_LIMITING.md |

---

## 📊 문서 통계

- **총 문서 수**: 13개
- **총 라인 수**: 5,424줄
- **총 용량**: 약 135KB

### 카테고리별 통계

| 카테고리 | 문서 수 | 평균 라인 수 |
|----------|---------|--------------|
| development/ | 4개 | 약 600줄 |
| guides/ | 5개 | 약 500줄 |
| reference/ | 3개 | 약 400줄 |

---

## 🔄 문서 업데이트 규칙

### 1. 새 기능 추가 시
- guides/ 폴더에 새 가이드 문서 작성
- reference/API_DOCUMENTATION.md 업데이트
- development/CHANGELOG.md에 기록

### 2. 버전 릴리스 시
- development/CHANGELOG.md 업데이트
- development/PROJECT_STATUS.md 업데이트
- README.md 버전 번호 업데이트

### 3. 버그 수정 시
- development/CHANGELOG.md에 기록
- 관련 가이드 문서의 "문제 해결" 섹션 업데이트

### 4. API 변경 시
- reference/API_DOCUMENTATION.md 업데이트 (필수)
- 관련 guides/*.md 업데이트
- development/CHANGELOG.md에 기록

---

## 📞 문서 관련 문의

문서 관련 개선 사항이나 오류 발견 시:
- GitHub Issues 등록
- 문서 수정 PR 제출

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**관리자**: Backend Team
