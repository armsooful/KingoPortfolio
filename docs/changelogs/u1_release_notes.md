# Release Notes / U-1 사용자 기능 (Phase 3-C)
작성일자: 2026-01-18

## 1. 개요
U-1 읽기 전용 사용자 기능을 공개한다. 본 릴리즈는 사용자 행동 유도 없이 포트폴리오 현황과 성과 정보를 조회할 수 있도록 한다.

---

## 2. 신규 API

### 포트폴리오 현황 조회
- **GET** `/api/v1/portfolios/{portfolio_id}/summary`
- 자산 구성/비중, 기준일, 출처 제공

### 성과 조회
- **GET** `/api/v1/portfolios/{portfolio_id}/performance`
- 기간 수익률(1M/3M/6M/YTD), 누적 수익률, 벤치마크 대비 수익률 제공

### 성과 해석 정보
- **GET** `/api/v1/portfolios/{portfolio_id}/performance/explanation`
- 산식 요약 및 반영 요소 설명 제공

### 신뢰 설명 패널(Why Panel)
- **GET** `/api/v1/portfolios/{portfolio_id}/explain/why`
- 계산 시점/기준일/스냅샷 요약 제공

---

## 3. 사용자 화면 변경 요약
- 포트폴리오 요약 화면: 기준일, 데이터 출처, 참고용 배지 표시
- 성과 화면: 기간 선택 및 LIVE 성과만 노출
- 성과 해석 화면: 산식/반영 요소 설명 및 필수 면책 문구 표시
- Why Panel: 계산 시점과 데이터 스냅샷 안내

---

## 4. 제약 및 유의사항
- 모든 엔드포인트는 GET 전용(Read-only)
- SIM/BACK 성과는 사용자 UI에 노출되지 않음
- 금지 문구/행동 유도 문구 차단 기준 적용

---

## 5. 관련 문서
- U-1 기능 명세 최종본: docs/phase3/20260118_u1_feature_spec_final.md
- U-1 검증 체크리스트: docs/phase3/20260118_u1_test_checklist.md
