# 문서 작성 및 관리 가이드

KingoPortfolio 프로젝트의 문서 작성 규칙 및 관리 방법

---

## 📁 문서 구조

```
backend/
├── README.md                    # 프로젝트 메인 문서
└── docs/
    ├── README.md                # 문서 인덱스
    ├── DOCUMENTATION_GUIDE.md   # 이 문서
    ├── development/             # 개발 프로세스 문서
    │   ├── README.md
    │   ├── PROJECT_STATUS.md
    │   ├── CHANGELOG.md
    │   ├── TESTING.md
    │   └── SESSION_SUMMARY_*.md
    ├── guides/                  # 기능별 사용 가이드
    │   ├── README.md
    │   ├── PROFILE.md
    │   ├── PASSWORD_RESET.md
    │   ├── EXPORT.md
    │   ├── SEO.md
    │   └── RATE_LIMITING.md
    └── reference/               # 기술 레퍼런스
        ├── README.md
        ├── API_DOCUMENTATION.md
        ├── RBAC_IMPLEMENTATION.md
        └── ERROR_HANDLING.md
```

---

## 📝 문서 분류 기준

### 1. development/ - 개발 프로세스 문서

**저장할 문서**:
- ✅ 프로젝트 전체 현황 및 로드맵
- ✅ 버전 변경 이력 (CHANGELOG)
- ✅ 테스트 전략 및 가이드
- ✅ 개발 세션 요약
- ✅ CI/CD 설정
- ✅ 배포 가이드
- ✅ 개발 워크플로우

**저장하지 말아야 할 문서**:
- ❌ 특정 기능의 사용법
- ❌ API 명세
- ❌ 기술 상세 (아키텍처, 알고리즘 등)

### 2. guides/ - 기능별 사용 가이드

**저장할 문서**:
- ✅ 특정 기능의 구현 및 사용 방법
- ✅ 튜토리얼 및 예제
- ✅ 모범 사례 (Best Practices)
- ✅ 문제 해결 (Troubleshooting)
- ✅ 통합 가이드 (프론트엔드/백엔드)

**저장하지 말아야 할 문서**:
- ❌ API 명세만 있는 문서
- ❌ 프로젝트 관리 문서
- ❌ 순수 기술 레퍼런스

### 3. reference/ - 기술 레퍼런스

**저장할 문서**:
- ✅ API 명세
- ✅ 데이터베이스 스키마
- ✅ 시스템 아키텍처
- ✅ 알고리즘 설명
- ✅ 코드 컨벤션
- ✅ 기술 상세 문서

**저장하지 말아야 할 문서**:
- ❌ 사용 방법이 주인 문서
- ❌ 프로젝트 관리 문서

---

## 📄 파일 명명 규칙

### 일반 규칙
- **대문자 스네이크 케이스** 사용: `PROFILE.md`, `API_DOCUMENTATION.md`
- **명확하고 설명적인 이름** 사용
- **약어 최소화**: 명확한 의미 전달

### 특수 파일

| 파일 유형 | 명명 규칙 | 예시 |
|-----------|-----------|------|
| 메인 README | `README.md` | `README.md` |
| 세션 요약 | `SESSION_SUMMARY_YYYY-MM-DD.md` | `SESSION_SUMMARY_2025-12-29.md` |
| 버전 관리 | `CHANGELOG.md` | `CHANGELOG.md` |
| 기능 가이드 | `[기능명].md` | `PROFILE.md`, `EXPORT.md` |
| 기술 문서 | `[시스템명]_[타입].md` | `API_DOCUMENTATION.md` |

---

## ✍️ 문서 작성 템플릿

### 가이드 문서 템플릿 (guides/)

```markdown
# [기능명] 가이드

**마지막 업데이트**: YYYY-MM-DD
**버전**: X.X.X
**작성자**: [팀/개인명]

---

## 📋 목차

1. [개요](#개요)
2. [주요 기능](#주요-기능)
3. [사용 방법](#사용-방법)
4. [API 엔드포인트](#api-엔드포인트)
5. [예제 코드](#예제-코드)
6. [문제 해결](#문제-해결)
7. [보안 고려사항](#보안-고려사항)
8. [관련 문서](#관련-문서)

---

## 개요

[기능에 대한 간단한 설명]

### 주요 특징
- 특징 1
- 특징 2

---

## 주요 기능

### 1. [기능 1]
[설명]

### 2. [기능 2]
[설명]

---

## 사용 방법

### 1. [단계 1]
[설명 및 코드]

### 2. [단계 2]
[설명 및 코드]

---

## API 엔드포인트

### [엔드포인트 1]

**HTTP Method**: POST
**Path**: `/api/endpoint`
**인증**: 필요

#### 요청 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| param1 | string | O | 설명 |

#### 응답
```json
{
  "status": "success",
  "data": { ... }
}
```

---

## 예제 코드

### Python (Backend)
```python
# 예제 코드
```

### JavaScript (Frontend)
```javascript
// 예제 코드
```

---

## 문제 해결

### 문제 1: [문제 설명]
**원인**: [원인 설명]
**해결**: [해결 방법]

---

## 보안 고려사항

1. [보안 사항 1]
2. [보안 사항 2]

---

## 관련 문서

- [문서 1](링크)
- [문서 2](링크)

---

**작성자**: [이름]
**마지막 업데이트**: YYYY-MM-DD
```

### 레퍼런스 문서 템플릿 (reference/)

```markdown
# [시스템/API명] 레퍼런스

**버전**: X.X.X
**마지막 업데이트**: YYYY-MM-DD

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [API 명세](#api-명세)
4. [기술 상세](#기술-상세)
5. [참고 자료](#참고-자료)

---

## 개요

[시스템/API 개요]

---

## 아키텍처

[아키텍처 다이어그램 및 설명]

---

## API 명세

### [카테고리 1]

#### [엔드포인트 1]
- **Method**: GET/POST/PUT/DELETE
- **Path**: `/api/path`
- **설명**: [설명]
- **권한**: user/premium/admin
- **Rate Limit**: X/hour

##### 요청
```json
{
  "param": "value"
}
```

##### 응답
```json
{
  "data": { ... }
}
```

---

## 기술 상세

### [주제 1]
[상세 설명]

---

## 참고 자료

- [공식 문서](링크)
- [관련 문서](링크)

---

**작성자**: [이름]
**마지막 업데이트**: YYYY-MM-DD
```

---

## 🎨 문서 스타일 가이드

### 마크다운 기본 규칙

```markdown
# H1: 문서 제목만 사용
## H2: 주요 섹션
### H3: 하위 섹션
#### H4: 상세 항목

**굵게**: 중요한 용어
*기울임*: 강조
`코드`: 인라인 코드
```

### 코드 블록

````markdown
```python
# Python 코드
def example():
    pass
```

```bash
# 셸 명령어
pytest tests/
```
````

### 표 작성

```markdown
| 컬럼1 | 컬럼2 | 컬럼3 |
|-------|-------|-------|
| 값1   | 값2   | 값3   |
```

### 링크

```markdown
# 상대 경로 (같은 저장소)
[문서 이름](../guides/PROFILE.md)

# 절대 경로 (외부)
[FastAPI 문서](https://fastapi.tiangolo.com/)

# 앵커 링크 (같은 문서)
[섹션으로 이동](#섹션-제목)
```

### 이모지 사용

```markdown
## 📚 카테고리 제목
- ✅ 완료된 항목
- ⚠️ 주의사항
- ❌ 금지 사항
- 🔍 팁/노트
```

---

## 📅 문서 업데이트 규칙

### 즉시 업데이트해야 하는 경우

#### 1. API 변경
- ✅ `reference/API_DOCUMENTATION.md` 업데이트 (필수)
- ✅ 관련 `guides/*.md` 업데이트
- ✅ `development/CHANGELOG.md`에 기록

#### 2. 새 기능 추가
- ✅ `guides/` 폴더에 새 가이드 작성
- ✅ `reference/API_DOCUMENTATION.md` 추가
- ✅ 각 폴더의 `README.md` 업데이트
- ✅ `development/CHANGELOG.md`에 기록
- ✅ 프로젝트 루트 `README.md` 업데이트

#### 3. 버전 릴리스
- ✅ `development/CHANGELOG.md` 업데이트
- ✅ `development/PROJECT_STATUS.md` 업데이트
- ✅ 버전 번호 통일 (코드, 문서, README)

### 주기적 업데이트

#### 월간 (권장)
- `development/PROJECT_STATUS.md` 검토 및 업데이트
- 알려진 이슈 목록 업데이트
- 문서 링크 검증

#### 분기별 (권장)
- 모든 문서 리뷰
- 오래된 정보 제거
- 예제 코드 검증

---

## ✅ 문서 품질 체크리스트

### 작성 전
- [ ] 적절한 폴더 선택 (development/guides/reference)
- [ ] 기존 유사 문서 확인
- [ ] 템플릿 선택

### 작성 중
- [ ] 명확한 제목 및 목차
- [ ] 코드 예제 포함 (실행 가능)
- [ ] 스크린샷/다이어그램 (필요시)
- [ ] 관련 문서 링크
- [ ] 마지막 업데이트 날짜 기록

### 작성 후
- [ ] 마크다운 문법 검증
- [ ] 링크 유효성 확인
- [ ] 코드 예제 테스트
- [ ] 폴더별 README에 추가
- [ ] CHANGELOG에 기록 (필요시)
- [ ] 팀원 리뷰 요청

---

## 🔍 문서 검색 및 관리

### 문서 찾기

```bash
# 키워드로 검색
grep -r "프로필" docs/

# 특정 폴더에서 검색
grep -r "API" docs/guides/

# 파일명으로 검색
find docs/ -name "*PROFILE*"
```

### 문서 통계

```bash
# 문서 개수
find docs/ -name "*.md" | wc -l

# 라인 수
find docs/ -name "*.md" -exec wc -l {} + | tail -1

# 용량
du -sh docs/
```

### 깨진 링크 확인

```bash
# markdown-link-check 사용 (설치 필요)
npm install -g markdown-link-check
find docs/ -name "*.md" -exec markdown-link-check {} \;
```

---

## 🚀 새 문서 작성 워크플로우

### 1. 기획 단계
```
1. 문서 목적 명확히 하기
2. 대상 독자 정의
3. 적절한 카테고리 선택 (development/guides/reference)
4. 기존 관련 문서 확인
```

### 2. 작성 단계
```
1. 템플릿 복사
2. 목차 작성
3. 본문 작성 (예제 코드 포함)
4. 관련 문서 링크
5. 마지막 업데이트 날짜 기록
```

### 3. 검토 단계
```
1. 마크다운 문법 확인
2. 코드 예제 실행 테스트
3. 링크 유효성 확인
4. 맞춤법 검사
5. 동료 리뷰
```

### 4. 배포 단계
```
1. 파일 저장 (적절한 폴더)
2. 폴더별 README에 추가
3. 프로젝트 루트 README 업데이트 (필요시)
4. CHANGELOG에 기록 (새 기능/중요 변경)
5. Git commit 및 push
```

---

## 📊 문서 메트릭

### 목표 지표
- 📄 **문서 커버리지**: 모든 주요 기능에 가이드 존재
- 🔗 **링크 유효성**: 95% 이상
- 📅 **최신성**: 3개월 이내 업데이트
- ✍️ **코드 예제**: 모든 가이드에 실행 가능한 예제

### 현재 통계 (2025-12-29)
- 총 문서: 16개
- 총 라인 수: 5,424줄
- 총 용량: 169KB
- 카테고리:
  - development/: 4개 (+ 1 README)
  - guides/: 5개 (+ 1 README)
  - reference/: 3개 (+ 1 README)
  - docs/: 2개 (README, GUIDE)

---

## 🛠️ 문서 도구

### 추천 에디터
- **VS Code**: Markdown 플러그인
- **Typora**: WYSIWYG 마크다운 에디터
- **Obsidian**: 문서 연결 및 그래프 시각화

### 유용한 플러그인 (VS Code)
- Markdown All in One
- Markdown Preview Enhanced
- markdownlint
- Markdown Link Updater

### 다이어그램 도구
- Mermaid (코드로 다이어그램)
- draw.io
- Excalidraw

---

## 📞 문의 및 지원

### 문서 관련 이슈
- GitHub Issues에 `documentation` 라벨로 등록
- PR 제출 (문서 개선)

### 문서 작성 도움
- Backend Team에 문의
- 기존 문서 참고
- 템플릿 활용

---

**작성자**: Backend Team
**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
