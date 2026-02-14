# 회원가입 및 프로필 완성 유도 구현 보고서

## 1. 개요

### 목적
이메일만으로 간소하게 회원가입한 뒤, 추가 프로필 정보(이름, 연령대, 투자경험, 위험성향)를 자연스럽게 입력하도록 유도하여 **맞춤 서비스 활성화율**을 높인다.

### 배경
- 기존에는 회원가입 시 이름, 연령대 등 모든 정보를 한 번에 입력해야 했음
- 가입 허들을 낮추기 위해 **이메일+비밀번호만으로 가입 가능**하도록 간소화 완료
- 간소화 후 추가 정보 입력률이 낮아질 위험 → 다중 터치포인트를 통한 유도 필요

---

## 2. 아키텍처

### 전체 흐름

```
회원가입 (이메일+비밀번호)
    │
    ▼
대시보드 진입
    │
    ├─ [자동] ProfileCompletionModal 표시 (세션 내 1회)
    │       ├─ "맞춤 학습 시작하기" → 프로필 저장 → 모달/배너/배지 숨김
    │       └─ "다음에 할게요" → 모달 닫힘, sessionStorage 플래그 저장
    │
    ├─ [상시] 프로필 완성 배너 (대시보드 상단)
    │       └─ "프로필 완성하기" 버튼 → 모달 재표시
    │
    └─ [상시] 헤더 "프로필 입력하기" 태그
            └─ 클릭 → /profile 페이지 이동
```

### 구성 요소

| 구성 요소 | 위치 | 역할 |
|-----------|------|------|
| `ProfileCompletionModal` | 모달 (오버레이) | 미입력 필드를 즉시 입력받는 폼 |
| 프로필 완성 배너 | 대시보드 상단 | 프로그레스 바 + CTA 버튼으로 지속 유도 |
| 프로필 입력하기 태그 | 헤더 (전체 페이지) | 어느 페이지에서든 프로필 페이지로 유도 |

---

## 3. 백엔드 API

### `GET /auth/profile/completion-status`

프로필 완성도를 조회하는 API. 프론트엔드의 모든 유도 UI가 이 API를 기반으로 동작한다.

**응답 예시 (미완성):**
```json
{
  "is_complete": false,
  "completion_percent": 0,
  "filled_count": 0,
  "total_count": 4,
  "missing_fields": [
    { "field": "name", "label": "이름" },
    { "field": "age_group", "label": "연령대" },
    { "field": "investment_experience", "label": "투자 경험" },
    { "field": "risk_tolerance", "label": "위험 성향" }
  ]
}
```

**필수 필드 (4개):**

| 필드 | 설명 | 입력 방식 |
|------|------|-----------|
| `name` | 이름 | 텍스트 입력 |
| `age_group` | 연령대 | 선택 (10대~60대 이상) |
| `investment_experience` | 투자 경험 | 선택 (없음/1년 미만/1~3년/3년 이상) |
| `risk_tolerance` | 위험 성향 | 선택 (안정형/중립형/적극형) |

### `PUT /auth/profile`

프로필 정보를 업데이트하는 API. 모달의 "맞춤 학습 시작하기" 버튼이 호출한다.

---

## 4. 프론트엔드 구현

### 4-1. 회원가입 페이지 (`SignupPage.jsx`)

**입력 필드:** 이메일, 비밀번호, 비밀번호 확인 (3개만)

- 가입 성공 시 자동 로그인 + `/dashboard`로 이동
- 추가 정보는 대시보드에서 유도

### 4-2. ProfileCompletionModal (`ProfileCompletionModal.jsx`)

재사용 가능한 모달 컴포넌트. 대시보드와 설문 페이지에서 공유.

**주요 기능:**
- `getProfileCompletionStatus()` 호출하여 미입력 필드만 동적으로 폼 생성
- 프로그레스 바로 완성도 시각화
- 혜택 안내 3가지 체크리스트 표시
- 저장 성공 시 `onComplete` 콜백으로 부모 컴포넌트 상태 업데이트

**동기부여 문구:**
- 타이틀: "30초면 나만의 투자 학습이 시작됩니다"
- 혜택 리스트:
  - 내 성향에 맞는 포트폴리오 시뮬레이션
  - 맞춤 종목 스크리닝 및 Compass Score
  - 투자 학습 진단 리포트 제공
- CTA 버튼: "맞춤 학습 시작하기"

### 4-3. 대시보드 자동 모달 + 배너 (`MarketDashboardPage.jsx`)

**자동 모달 로직:**
```
useEffect → getProfileCompletionStatus()
  → is_complete === false?
    → sessionStorage에 'profile_modal_dismissed' 없으면 → 모달 표시
    → 있으면 → 모달 미표시 (배너만 표시)
```

- `sessionStorage` 사용: 브라우저 탭 닫으면 초기화 → 다음 방문 시 다시 모달 표시
- 모달 닫기("다음에 할게요" 또는 X 버튼) → 플래그 저장 → 세션 내 재표시 없음

**프로필 완성 배너:**
- 프로필 미완성 시 대시보드 헤더 아래에 상시 표시
- 구성: 안내 문구 + 프로그레스 바 + "프로필 완성하기" 버튼
- 버튼 클릭 → ProfileCompletionModal 재표시
- 프로필 완성 시 자동 숨김

### 4-4. 헤더 프로필 태그 (`Header.jsx`)

- 프로필 미완성 시 사용자 이름 아래에 **"프로필 입력하기"** 빨간색 태그 표시
- 데스크탑 헤더 + 모바일 드로어 양쪽에 적용
- 클릭 시 `/profile` 페이지로 이동
- `useEffect`에서 `getProfileCompletionStatus()` 호출, `[user]` 의존성

---

## 5. 수정 파일 목록

### 프론트엔드

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/pages/SignupPage.jsx` | 이메일+비밀번호만으로 간소화 |
| `frontend/src/components/ProfileCompletionModal.jsx` | 동기부여 문구 강화 (혜택 리스트, CTA 버튼) |
| `frontend/src/styles/ProfileCompletionModal.css` | 혜택 리스트 스타일 추가 |
| `frontend/src/pages/MarketDashboardPage.jsx` | 자동 모달 + 프로필 배너 추가 |
| `frontend/src/styles/MarketDashboard.css` | 배너 스타일 + 모바일 반응형 |
| `frontend/src/components/Header.jsx` | 프로필 미완성 태그 추가 (데스크탑+모바일) |
| `frontend/src/styles/App.css` | 태그 스타일 (`.profile-incomplete-tag`) |
| `frontend/src/services/api.js` | `getProfileCompletionStatus`, `updateProfile` (기존) |

### 백엔드

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/routes/auth.py` | `GET /auth/profile/completion-status` (기존) |
| `backend/app/routes/auth.py` | `PUT /auth/profile` (기존) |
| `backend/app/schemas.py` | `UpdateProfileRequest` 스키마 (기존) |
| `backend/app/models/user.py` | `age_group`, `investment_experience`, `risk_tolerance` 필드 (기존) |

---

## 6. 사용자 시나리오

### 시나리오 1: 신규 가입 → 즉시 프로필 입력

```
1. 이메일+비밀번호로 회원가입
2. 대시보드 자동 이동
3. ProfileCompletionModal 자동 표시
4. 이름/연령대/투자경험/위험성향 입력
5. "맞춤 학습 시작하기" 클릭
6. → 프로필 저장, 모달 닫힘, 배너 숨김, 헤더 태그 숨김
```

### 시나리오 2: 신규 가입 → 나중에 입력

```
1. 이메일+비밀번호로 회원가입
2. 대시보드 자동 이동
3. ProfileCompletionModal 자동 표시
4. "다음에 할게요" 클릭 → 모달 닫힘
5. 대시보드 상단에 프로필 완성 배너 표시 (프로그레스 바 + CTA)
6. 헤더에 "프로필 입력하기" 태그 표시
7. (나중에) 배너 "프로필 완성하기" 클릭 → 모달 재표시
8. 또는 헤더 태그 클릭 → /profile 페이지에서 입력
```

### 시나리오 3: 재방문 (프로필 미완성)

```
1. 로그인 → 대시보드
2. sessionStorage 초기화됨 → 모달 자동 표시 (세션당 1회)
3. 배너 + 헤더 태그 상시 표시
```

---

## 7. 검증 결과

브라우저 E2E 테스트 (Playwright) 수행 완료:

| 테스트 항목 | 결과 |
|------------|------|
| 신규 가입 후 대시보드에서 자동 모달 표시 | PASS |
| 모달 "다음에 할게요" 클릭 → 모달 닫힘 | PASS |
| 모달 닫힌 후 배너 표시 (프로그레스 바 + CTA) | PASS |
| 배너 "프로필 완성하기" 클릭 → 모달 재표시 | PASS |
| 모달에서 프로필 입력 후 저장 → 배너+태그 모두 숨김 | PASS |
| 헤더에 "프로필 입력하기" 태그 표시 (데스크탑) | PASS |
| 헤더 태그 클릭 → `/profile` 이동 | PASS |
| 프로필 완성 후 새로고침 → 배너/태그 없음 | PASS |
| `npm run build` 성공 | PASS |

---

## 8. 유도 터치포인트 요약

사용자가 프로필을 입력할 수 있는 경로는 총 **4개**:

| # | 터치포인트 | 타이밍 | 동작 |
|---|-----------|--------|------|
| 1 | 대시보드 자동 모달 | 가입 직후 / 매 세션 첫 방문 | 모달에서 바로 입력 |
| 2 | 대시보드 프로필 배너 | 대시보드 방문 시 상시 | 버튼 클릭 → 모달 표시 |
| 3 | 헤더 "프로필 입력하기" 태그 | 모든 페이지 상시 | 클릭 → /profile 이동 |
| 4 | 설문 시작 시 모달 | 투자성향진단 시작 전 | 모달에서 바로 입력 |

---

## 9. 향후 개선 방향

- **이메일 유도**: 가입 후 24시간 내 프로필 미완성 시 이메일 리마인더 발송
- **점진적 공개**: 프로필 항목을 한 번에 4개가 아닌, 기능 사용 시점에 1개씩 요청
- **프로필 완성 보상**: 완성 시 활동 점수(Activity Points) 지급으로 VIP 티어 연동
- **A/B 테스트**: 모달 vs 인라인 폼, 문구 변형 테스트로 전환율 최적화
