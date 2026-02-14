# Phase 10 Backlog — 검증·안정화 단계

작성일: 2026-01-24

---

## 1. 목표

"기능이 아니라 신뢰" 확보

- 경계 케이스 테스트 강화
- 오류·예외 처리 보강
- 로그·감사 추적 정교화
- 결과 문구 Safe Guard 강화

---

## 2. Epic 1: 결과 문구 Safe Guard 강화 (P0 - Critical) ✅ 완료

**목적**: 투자 자문/권유로 오인될 수 있는 표현 제거

**완료일**: 2026-01-24

### Story 1.1: 매수/매도 신호 표현 제거 (quant_analyzer.py)

| ID | 파일 | 라인 | 현재 표현 | 수정 방향 |
|----|------|------|----------|----------|
| SG-001 | quant_analyzer.py | 108 | "골든크로스 발생 (매수 신호)" | "골든크로스 발생 (상승 추세)" |
| SG-002 | quant_analyzer.py | 110 | "데드크로스 발생 (매도 신호)" | "데드크로스 발생 (하락 추세)" |
| SG-003 | quant_analyzer.py | 148 | "과매수 (매도 검토)" | "과매수 구간" |
| SG-004 | quant_analyzer.py | 150 | "과매도 (매수 검토)" | "과매도 구간" |
| SG-005 | quant_analyzer.py | 194 | "상단 밴드 돌파 (과매수)" | "상단 밴드 돌파" |
| SG-006 | quant_analyzer.py | 196 | "하단 밴드 이탈 (과매도)" | "하단 밴드 이탈" |
| SG-007 | quant_analyzer.py | 266 | "골든크로스 (매수 신호)" | "골든크로스 (상승 추세)" |
| SG-008 | quant_analyzer.py | 268 | "데드크로스 (매도 신호)" | "데드크로스 (하락 추세)" |

### Story 1.2: 투자 행동 가이드 표현 제거 (qualitative_analyzer.py)

| ID | 파일 | 라인 | 현재 표현 | 수정 방향 |
|----|------|------|----------|----------|
| SG-010 | qualitative_analyzer.py | 246 | "비중 확대 검토 (단, 과매수 주의)" | "상승 모멘텀 관찰됨" |
| SG-011 | qualitative_analyzer.py | 254 | "현재 비중 유지 또는 소폭 확대" | "긍정적 신호 관찰됨" |
| SG-012 | qualitative_analyzer.py | 267 | "관망 고려, 급격한 매매 자제" | "변동성 확대 관찰됨" |
| SG-013 | qualitative_analyzer.py | 273 | "비중 축소 검토 또는 손절 준비" | "부정적 신호 관찰됨" |
| SG-014 | qualitative_analyzer.py | 281 | "비중 축소 강력 권고 (리스크 관리)" | "위험 신호 다수 관찰됨" |
| SG-015 | qualitative_analyzer.py | 248 | "뉴스 볼륨 급증 → 단기 변동성 확대 예상" | "뉴스 볼륨 급증 관찰됨" |
| SG-016 | qualitative_analyzer.py | 283 | "악재 연속 발생 → 추가 하락 가능성" | "악재 연속 발생 관찰됨" |
| SG-017 | qualitative_analyzer.py | 293 | "추가 악재 발생시 하락 가속 가능" | "부정적 뉴스 누적됨" |

### Story 1.3: Claude 서비스 fallback 응답 수정 (claude_service.py)

| ID | 파일 | 라인 | 현재 표현 | 수정 방향 |
|----|------|------|----------|----------|
| SG-020 | claude_service.py | 181 | "예측 가능한 수익을 추구하는 성향" | "일정한 현금 흐름 학습에 관심있는 성향" |
| SG-021 | claude_service.py | 182 | "포트폴리오를 구성하시는 것을 권장합니다" | "포트폴리오 학습을 고려해볼 수 있습니다" |
| SG-022 | claude_service.py | 192 | "주식 비중은 60-70%로 제한하세요" | "일반적으로 주식 비중 60-70%가 학습 사례로 사용됩니다" |

### Story 1.4: Frontend 컴포넌트 수정

| ID | 파일 | 라인 | 현재 표현 | 수정 방향 |
|----|------|------|----------|----------|
| SG-030 | Valuation.jsx | 68-69 | "매수 검토", "매도 검토" 라벨 | "저평가 구간", "고평가 구간" |
| SG-031 | QuantAnalysis.jsx | 59-60 | positiveKeywords에 '매수', negativeKeywords에 '매도' | 삭제 |

---

## 3. Epic 2: 오류·예외 처리 보강 (P1 - High) ✅ 완료

**목적**: Silent failure 제거, 일관된 예외 처리

**완료일**: 2026-01-24

### Story 2.1: Bare except 제거

| ID | 파일 | 라인 | 문제 | 수정 방향 |
|----|------|------|------|----------|
| EH-001 | update_stock_data.py | 273 | bare except 사용 | 구체적 예외 + 로깅 |
| EH-002 | simulation_store.py | 430 | bare except 사용 | ValueError/TypeError + 로깅 |
| EH-003 | market.py | 159 | bare except 사용 | 구체적 예외 + 로깅 |
| EH-004 | market.py | 174 | bare except 사용 | 구체적 예외 + 로깅 |
| EH-005 | batch_jobs.py | 104 | bare except 사용 | Exception + 로깅 |

### Story 2.2: Exception swallowing 제거

| ID | 파일 | 라인 | 문제 | 수정 방향 |
|----|------|------|------|----------|
| EH-010 | custom_portfolio_simulation.py | 295,309 | empty pass | 로깅 추가 또는 re-raise |
| EH-011 | analysis_store.py | 224 | empty pass | 로깅 추가 |
| EH-012 | audit_log_service.py | 47 | empty pass | 로깅 추가 |

### Story 2.3: Routes 로깅 추가

| ID | 파일 | 문제 | 수정 방향 |
|----|------|------|----------|
| EH-020 | market.py | logger 미사용 | logger 설정 및 예외 로깅 |
| EH-021 | batch_jobs.py | print 사용 | logger로 교체 |
| EH-022 | portfolio.py | logger 미설정 | logger 설정 |
| EH-023 | portfolio_custom.py | logger 미설정 | logger 설정 |
| EH-024 | portfolio_public.py | logger 미설정 | logger 설정 |

---

## 4. Epic 3: 경계 케이스 테스트 강화 (P2 - Medium) ✅ 완료

**목적**: 엣지 케이스 커버리지 확대

**완료일**: 2026-01-24
**테스트 파일**: `backend/tests/e2e/test_phase10_edge_cases.py`

### Story 3.1: Phase 7 평가 엣지 케이스

| ID | 테스트 케이스 | 우선순위 |
|----|--------------|----------|
| TC-001 | 대형 포트폴리오 (50+ 종목) | High |
| TC-002 | 동일 비중 포트폴리오 | Medium |
| TC-003 | 데이터 갭 기간 | High |
| TC-004 | 극단적 가격 변동성 | Medium |

### Story 3.2: 데이터 품질 엣지 케이스

| ID | 테스트 케이스 | 우선순위 |
|----|--------------|----------|
| TC-010 | NULL 값 처리 | High |
| TC-011 | 중복 날짜 | High |
| TC-012 | 날짜 순서 오류 | High |
| TC-013 | 거래량 0 처리 | Medium |

### Story 3.3: 포트폴리오 비교 엣지 케이스

| ID | 테스트 케이스 | 우선순위 |
|----|--------------|----------|
| TC-020 | 3개 이상 포트폴리오 비교 | Medium |
| TC-021 | 다른 유형 포트폴리오 비교 | Medium |
| TC-022 | 평가 기간 불일치 | Medium |

---

## 5. Epic 4: 로그·감사 추적 정교화 (P2 - Medium) ✅ 완료

**목적**: 운영 가시성 향상

**완료일**: 2026-01-24
**구현 파일**:
- `backend/app/utils/structured_logging.py` (구조화된 로깅 유틸리티)
- `backend/app/services/audit_log_service.py` (감사 로그 확장)
- `backend/app/routes/phase7_evaluation.py` (로깅 적용)

### Story 4.1: 구조화된 로깅 표준화

- [x] 모든 서비스에 request_id 포함 (`StructuredLogger`, `request_context`)
- [x] 예외 로깅에 context 정보 포함 (`log_error_with_context`)
- [x] 성능 메트릭 로깅 추가 (`log_performance`, `@log_performance` 데코레이터)

### Story 4.2: 감사 로그 확장

- [x] 평가 실행 감사 로그 (`log_evaluation`)
- [x] 설정 변경 감사 로그 (`log_config_change` - 기존)
- [x] 에러 발생 감사 로그 (`log_error`)

---

## 6. 우선순위 요약

| 우선순위 | Epic | Story 수 | 예상 항목 |
|----------|------|---------|----------|
| P0 (Critical) | Epic 1: Safe Guard | 4 | 24개 수정 |
| P1 (High) | Epic 2: 예외 처리 | 3 | 14개 수정 |
| P2 (Medium) | Epic 3: 테스트 | 3 | 12개 테스트 |
| P2 (Medium) | Epic 4: 로깅 | 2 | 표준화 |

---

## 7. 완료 기준

### Phase 10 완료 조건

- [x] Epic 1 모든 항목 수정 완료 (2026-01-24)
- [x] Epic 2 모든 항목 수정 완료 (2026-01-24)
- [x] Epic 3 엣지 케이스 테스트 추가 (2026-01-24)
- [x] Epic 4 로그·감사 추적 정교화 (2026-01-24)
- [x] bare except 0건
- [x] 매수/매도 관련 표현 0건
- [x] 투자 권유 표현 0건
- [x] 예외 swallowing 0건

### Phase 10 완료! 🎉

---

## 8. 버전 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-01-24 | 최초 작성 |
| v1.1 | 2026-01-24 | Epic 1, 2, 3 완료 표시 |
| v1.2 | 2026-01-24 | Epic 4 완료, Phase 10 완료 |
