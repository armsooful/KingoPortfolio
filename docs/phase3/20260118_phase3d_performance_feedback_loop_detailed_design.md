# Phase 3-D / 성과·피드백 루프 상세 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 문서 상태
- 상태: LOCKED
- 승인: 2026-01-18
- 비고: 범위/스키마/지표/프로세스 초안 고정

## 1. 개요
Phase 3-D는 사용자 피드백과 성과/설명 품질 지표를 연결하여 **개선 루프를 운영 가능하게 설계**한다. 자동 학습/자동 반영은 제외하고, 운영 승인 기반의 통제 가능한 프로세스를 제공한다.

---

## 2. 목표
- 사용자 피드백 수집/분류/반영 경로 정의
- 설명 품질 지표를 측정하고 개선 우선순위화
- 운영자가 승인 가능한 변경 프로세스 구축

---

## 3. 범위

### In-Scope
- 피드백 이벤트 정의 및 API
- 피드백 저장 스키마 및 상태 전이
- 품질 지표 정의 및 계산 기준
- 운영 프로세스(분류/검토/승인/반영)

### Out-of-Scope
- 자동 학습/자동 문구 교체
- 개인화 추천/행동 유도
- SIM/BACK 성과 노출

---

## 4. 피드백 이벤트 설계

### 4.1 이벤트 타입
- `HELPFUL` (도움됨)
- `NOT_HELPFUL` (도움되지 않음)
- `REPORT` (부적절/오해 소지)
- `ERROR` (오류/데이터 이상 제보)

### 4.2 공통 필드
- `event_id` (UUID)
- `event_version` ("v1")
- `occurred_at` (UTC ISO-8601)
- `user_id`
- `portfolio_id`
- `view_name` (summary/performance/explanation/why)
- `feedback_type`
- `reason_code` (optional)
- `comment` (optional, 길이 제한 200자)
- `request_id` (optional)

### 4.3 민감 정보 기준
- 이메일/전화/계좌/실명 입력 금지
- `comment`는 저장 전 마스킹 규칙 적용

---

## 5. 저장 스키마 (초안)

### 5.1 feedback_event
- `event_id` (PK)
- `event_version`
- `occurred_at`
- `user_id`
- `portfolio_id`
- `view_name`
- `feedback_type`
- `reason_code`
- `comment`
- `status` (NEW/REVIEW/APPROVED/REJECTED)
- `created_at`

### 5.2 feedback_review
- `review_id` (PK)
- `event_id` (FK)
- `reviewer_id`
- `decision` (APPROVE/REJECT/NEEDS_INFO)
- `decision_reason`
- `created_at`

---

## 6. 품질 지표 정의

### 6.1 정량 지표
- 도움됨 비율 = HELPFUL / (HELPFUL + NOT_HELPFUL)
- 신고 비율 = REPORT / 전체 피드백
- 오류 제보 비율 = ERROR / 전체 피드백
- 금지 문구 위반율 = 가드 위반 건 / 전체 텍스트 검사 건

### 6.2 경보 기준(초안)
- 신고 비율 5% 이상 → Warning
- 오류 제보 3건/일 이상 → Warning, 10건/일 이상 → Critical

---

## 7. 운영 프로세스

### 7.1 분류
- NEW → REVIEW
- 자동 분류는 태깅만 수행

### 7.2 검토/승인
- 운영자 또는 품질 담당자가 검토
- 변경 반영은 승인 후 진행

### 7.3 반영/기록
- 승인 건은 변경 이력 기록
- 변경은 릴리즈 노트에 반영

---

## 8. API 설계 (초안)
- **POST** `/api/v1/feedback`
- **GET** `/admin/feedback?status=NEW`
- **POST** `/admin/feedback/{event_id}/review`

---

## 9. 보안/권한
- 사용자: 피드백 등록만 가능
- 관리자: 조회/승인/거절 가능
- 감사 로그 필수

---

## 10. 완료 기준
- 피드백 이벤트 스키마 확정
- 운영 프로세스 승인 절차 문서화
- 품질 지표/임계치 합의
