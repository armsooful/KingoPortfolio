# Phase 3-C / Epic C-4 구현 작업 티켓
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

- 범위: 관리자 통제 (Admin & Controls)

## C4-T01: DDL 스키마 설계
- RBAC/감사/승인/정정 테이블 정의
- 산출물: `docs/phase3/c4_ddl_schema.sql`, `docs/phase3/c4_ddl_schema.md`

## C4-T02: RBAC 모델 구현
- 역할/권한 매핑, 관리자 권한 확인 로직 추가
- 산출물: `backend/app/services/admin_rbac_service.py`

## C4-T03: 관리자 감사 로그 서비스
- 관리자 변경 API 호출 시 감사 로그 기록
- 산출물: `backend/app/services/admin_audit_service.py`

## C4-T04: 승인 워크플로우 구현
- 승인 요청/승인/거절/실행 상태 관리
- 산출물: `backend/app/services/admin_approval_service.py`

## C4-T05: 수동 정정(Adjustment) 처리
- 정정 요청 생성 및 승인 연계
- 산출물: `backend/app/services/admin_adjustment_service.py`

## C4-T06: 관리자 API 확장
- RBAC 기반 접근 제어, reason 필수, idempotency_key 지원
- 산출물: `backend/app/routes/admin_controls.py`

## C4-T07: 통합 테스트
- RBAC 권한 매트릭스, 승인 플로우, 감사 로그 생성 검증
- 산출물: `backend/tests/integration/test_admin_controls.py`

---

## 작업 순서 제안
1) DDL → 2) RBAC → 3) 감사 로그 → 4) 승인 → 5) 정정 → 6) API → 7) 통합 테스트
