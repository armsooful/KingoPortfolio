# Phase 3-C / U-2 북마크(즐겨찾기) 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
사용자가 관심 있는 포트폴리오를 저장해 빠르게 접근하도록 한다. 결과 변경이나 추천 기능은 제공하지 않는다.

---

## 2. 기능 범위
- 북마크 추가/삭제
- 북마크 목록 조회
- 조회 전용 대상만 저장 (Read-only)

---

## 3. 데이터 스키마 (초안)

### bookmark
- `bookmark_id` (PK)
- `user_id`
- `portfolio_id`
- `created_at`

제약
- `(user_id, portfolio_id)` 유니크

---

## 4. API 설계

### 4.1 북마크 추가
- **POST** `/api/v1/bookmarks`
```json
{ "portfolio_id": 123 }
```

### 4.2 북마크 삭제
- **DELETE** `/api/v1/bookmarks/{portfolio_id}`

### 4.3 북마크 목록
- **GET** `/api/v1/bookmarks`

---

## 5. 규칙/제약
- 북마크는 사용자별로만 조회 가능
- 저장 대상은 본인 소유 포트폴리오만 허용
- Read-only 대상만 저장 (성과/설명 조회 범위)

### 5.1 엣지 케이스
- 동일 portfolio_id 중복 추가: 409
- 존재하지 않는 portfolio_id: 404
- 비활성 포트폴리오: 404
- 타 사용자 포트폴리오: 403

### 5.2 캐시 정책
- 북마크 목록 API는 개인화 데이터이므로 캐시 비활성화
- `Cache-Control: no-store`

---

## 6. 오류 처리
- 잘못된 portfolio_id: 404
- 중복 추가: 409
- 권한 없음: 403
