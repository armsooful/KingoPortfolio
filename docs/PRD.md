# PRD - Foresto Compass (KingoPortfolio)
작성일: 2026-02-06  
문서 버전: v1.0

## 1. 개요
Foresto Compass는 투자 권유·추천·자문을 제공하지 않는 교육/정보 제공형 포트폴리오 시뮬레이션 및 성과 해석 플랫폼이다.  
사용자가 선택한 구성에 대해 과거 데이터 기반의 분석/비교 결과와 이해를 돕는 해석, 그리고 결과 리포트(PDF)를 제공한다.

## 2. 문제 정의
- 소액 투자자는 적절한 자산 배분과 리스크 이해가 어렵다.
- 성과 지표(CAGR, MDD 등)는 일반 사용자에게 해석이 어렵다.
- 규제 환경에서 “추천”이 아닌 “이해” 중심의 안전한 안내가 필요하다.

## 3. 목표
- 투자 성향 진단을 통해 사용자 상황에 맞는 포트폴리오 구성안을 제시한다.
- 과거 데이터 기반의 성과/리스크를 이해하기 쉬운 언어로 설명한다.
- 결과를 비교/히스토리로 관리하고 PDF 리포트로 제공한다.
- 규제 표현을 준수하며 운영·감사 추적 체계를 제공한다.

## 4. 비목표
- 개별 종목 추천, 매수·매도 판단 제공
- 미래 수익 예측·보장
- 타 사용자/시장 대비 우열 평가 또는 랭킹 제공

## 5. 페르소나
- 초보 투자자: 금융 지식이 낮고 위험 이해가 필요
- 중급 투자자: 포트폴리오 비교·검증 니즈가 있음
- 운영/관리자: 규제 준수, 데이터 품질, 감사 로그 관리 필요

## 6. 핵심 사용자 여정
1. 회원가입/로그인 → 설문 기반 진단 제출 → 결과 확인
2. 포트폴리오 생성/선택 → 시뮬레이션 및 성과 지표 확인
3. 해석(요약/지표별/위험 구간) 확인 → 비교/히스토리 관리
4. PDF 리포트 생성/다운로드

## 7. 기능 요구사항
### 7.1 사용자 기능
- 회원가입/로그인, 프로필 조회/수정
- 15문항 설문 기반 투자 성향 진단(3유형)
- 자동 자산 배분 포트폴리오 제안 및 기대 수익률 안내
- 커스텀 포트폴리오 생성(자산군 비중 설정, 검증 포함)
- 진단/성과 히스토리 저장, 조회, 삭제
- 기간별 비교(2~10개 기간)
- 북마크/사용자 설정(프리셋 등)

### 7.2 시뮬레이션/분석
- 시나리오 기반 시뮬레이션(MIN_VOL/DEFENSIVE/GROWTH)
- 성과 지표 계산(CAGR, Volatility, Sharpe, MDD)
- 롤링 지표, 연도별 성과, 기여도, 드로다운 구간 분석
- 일별 NAV 경로 제공, 캐싱(요청 해시 기반 TTL)
- 리밸런싱 엔진(PERIODIC/DRIFT, Feature Flag)

### 7.3 해석/리포트
- 성과 지표를 자연어로 해석
- 벤치마크 대비 맥락 제공(우열 표현 금지)
- 위험 구간 분석 및 회복 과정 설명
- 기본/프리미엄 PDF 리포트 생성(7페이지 구성)

### 7.4 운영/관리
- 관리자 승인/정정, 관리자 모드 및 권한 제어
- 감사 로그 및 운영 알림 기록
- 데이터 품질/계보 점검
- 배치 작업 이력 추적
- Rate Limit 및 가드 룰 적용

### 7.5 규제/안전 가드
- 금지어/표현 차단(추천·우열·예측)
- 고지 문구 적용(정보 제공 목적, 과거 데이터 기반)
- 권한 분리(RBAC) 및 무권한 차단

## 8. 비기능 요구사항
- 성능: 주요 분석 응답은 사용자 체감 기준 단시간 내 제공
- 가용성: 장애 대응 Runbook, 롤백 절차, 운영 지표/알림 유지
- 보안: 인증/인가(JWT), 비밀번호 해싱(Bcrypt)
- 추적성: 분석 요청-응답의 감사 로그 및 Correlation ID 전파
- 품질: Golden Test 기반 출력 스키마 준수

## 9. 성공 지표(KPI)
- 사용자 수 500,000명(24개월)
- 관리 자산 2.5조 원(24개월)
- 월간 활성사용자(MAU) 100,000명(12개월)

## 10. 범위 및 로드맵(현황)
- Phase 1~3: 시뮬레이션 인프라, 고급 분석, 해석/리포트 완료
- Phase 7: 과거 데이터 기반 포트폴리오 평가 공개 완료
- Phase 8-A: 분석 깊이 확장 완료
- Phase 8-B: 입력 다양성 확장 조건부 완료(데이터 적재 후 성공 케이스 재검증 필요)
- Phase 8-C: 운영·상용화 미착수

## 11. 의존성
- 시장 데이터/가격 데이터 적재 및 품질 검증
- 규제 표현 검수 프로세스 유지
- 운영 모니터링/알림 인프라

## 12. 리스크
- 데이터 적재 지연 시 입력 확장 기능 검증 지연
- 규제 표현 변경 시 UX/문구 재검증 필요
- 비교 UI에서 우열/점수 노출 위험

## 13. 오픈 이슈/결정 필요
- Phase 8-C 요금제 및 사용량 제한 정책
- 데이터 적재 일정 및 성공 케이스 재검증 계획
- 전체 범위 금지어 스캔 주기와 책임자 확정

## 14. 참고 문서
- `README.md`
- `docs/feature_overview.md`
- `docs/reports/project_progress_report.md`

## 15. 세부 유저 스토리
- US-01: 초보 투자자로서 설문을 제출하고 내 투자 성향을 확인하고 싶다, 그래서 내 리스크 성향을 이해할 수 있다.
- US-02: 사용자로서 기본/자동 포트폴리오 제안을 보고 싶다, 그래서 내 상황에 맞는 구성안을 참고할 수 있다.
- US-03: 사용자로서 커스텀 비중을 입력하고 검증된 포트폴리오를 만들고 싶다, 그래서 내가 원하는 구성으로 분석을 받을 수 있다.
- US-04: 사용자로서 포트폴리오 성과 지표와 위험 지표를 확인하고 싶다, 그래서 결과를 수치로 이해할 수 있다.
- US-05: 사용자로서 성과 해석 문구를 읽고 싶다, 그래서 지표를 쉽게 이해할 수 있다.
- US-06: 사용자로서 위험 구간(드로다운)과 회복 과정을 보고 싶다, 그래서 손실과 회복의 맥락을 이해할 수 있다.
- US-07: 사용자로서 기간별 결과를 비교하고 싶다, 그래서 동일 사용자 범위에서 변화 흐름을 파악할 수 있다.
- US-08: 사용자로서 분석 결과를 저장/조회/삭제하고 싶다, 그래서 내 히스토리를 관리할 수 있다.
- US-09: 사용자로서 결과를 PDF 리포트로 내려받고 싶다, 그래서 결과를 보관하거나 공유할 수 있다.
- US-10: 운영자로서 관리자 승인/정정과 감사 로그를 확인하고 싶다, 그래서 규제 준수와 추적성을 보장할 수 있다.
- US-11: 운영자로서 금지 표현이 노출되지 않도록 가드가 동작하길 원한다, 그래서 규제 리스크를 줄일 수 있다.
- US-12: 운영자로서 데이터 품질과 계보 정보를 확인하고 싶다, 그래서 결과 신뢰성을 확보할 수 있다.

## 16. 수용 기준
- AC-01: 설문 제출 후 3가지 유형 중 하나로 분류되며 결과 화면에 노출된다.
- AC-02: 자동 포트폴리오 제안은 자산군 비중 합계가 1이고 허용 코드만 사용한다.
- AC-03: 커스텀 비중 입력 시 합계 1 미만/초과는 오류로 처리되며 저장되지 않는다.
- AC-04: 성과 지표(CAGR, Volatility, Sharpe, MDD)가 결과 화면에 표시된다.
- AC-05: 해석 문구는 금지어/우열/예측 표현을 포함하지 않는다.
- AC-06: 위험 구간 분석에는 최대 낙폭 구간과 회복 정보가 포함된다.
- AC-07: 기간 비교는 2~10개 기간 선택을 지원하며 동일 사용자 범위에서만 비교된다.
- AC-08: 히스토리는 저장/조회/삭제 CRUD가 가능하다.
- AC-09: PDF 리포트는 기본/프리미엄 두 가지 형태로 생성된다.
- AC-10: 관리자 기능은 권한이 없는 사용자에게 노출되지 않는다.
- AC-11: 감사 로그는 주요 분석 요청/응답에 대해 기록된다.
- AC-12: Golden Test 출력 스키마를 준수한다.

## 17. MVP 범위
- 회원가입/로그인, 설문 기반 투자 성향 진단
- 자동 포트폴리오 제안 및 기본 성과 지표 제공
- 시나리오 기반 시뮬레이션과 기본 성과 분석(CAGR, Volatility, Sharpe, MDD)
- 성과 해석(요약, 지표별) 및 위험 구간 설명
- 히스토리 저장/조회/삭제 및 기간 비교(2~10개)
- 기본/프리미엄 PDF 리포트 생성
- 규제 가드(금지어/고지 문구) 및 감사 로그 기록

## 18. 스토리 우선순위(MoSCoW)
- Must: US-01, US-02, US-03, US-04, US-05, US-06, US-08, US-09, US-10, US-11
- Should: US-07, US-12
- Could: 북마크/프리셋 고도화, 고급 비교 뷰 확장
- Won't (Now): 실시간 알림 기반 리밸런싱 추천, 종목 수준 최적화 제안

## 19. 비즈니스 규칙
- BR-01: 모든 결과는 과거 데이터 기반이며 미래 성과 예측 표현을 금지한다.
- BR-02: 추천, 우열, 랭킹, 점수화 표현은 노출하지 않는다.
- BR-03: 커스텀 포트폴리오 비중 합계는 반드시 1이어야 하며 허용 자산군 코드만 사용한다.
- BR-04: 동일 사용자 범위 내에서만 비교가 가능하다.
- BR-05: 관리자 기능은 RBAC 권한을 가진 사용자만 접근 가능하다.
- BR-06: 분석 요청/응답은 감사 로그에 기록되어야 한다.
- BR-07: 출력은 Golden Test 스키마를 준수해야 한다.
- BR-08: 기본/프리미엄 리포트는 고지 문구를 반드시 포함한다.

## 20. 테스트 케이스
- TC-01: 설문 제출 후 결과 화면에 3유형 중 하나가 표시된다(AC-01).
- TC-02: 자동 포트폴리오 제안 결과의 자산군 비중 합계가 1이다(AC-02).
- TC-03: 커스텀 비중 합계가 1이 아닐 경우 저장이 실패하고 오류가 표시된다(AC-03).
- TC-04: 결과 화면에 CAGR, Volatility, Sharpe, MDD가 표시된다(AC-04).
- TC-05: 해석 문구에 금지어/우열/예측 표현이 포함되지 않는다(AC-05).
- TC-06: 위험 구간 분석에 최대 낙폭 구간과 회복 정보가 포함된다(AC-06).
- TC-07: 기간 비교에서 1개 또는 11개 이상 선택 시 오류가 표시된다(AC-07).
- TC-08: 히스토리 저장/조회/삭제가 정상 동작한다(AC-08).
- TC-09: PDF 리포트가 기본/프리미엄 형태로 생성된다(AC-09).
- TC-10: 관리자 권한이 없는 사용자는 관리자 기능에 접근할 수 없다(AC-10).
- TC-11: 주요 분석 요청/응답이 감사 로그에 기록된다(AC-11).
- TC-12: Golden Test 스키마 검증이 통과한다(AC-12).

## 20-1. 테스트 케이스 상세(API/화면/스키마)
| Test ID | 엔드포인트 | 화면명 | 예상 응답 스키마 | 자동 예시 키 |
| --- | --- | --- | --- | --- |
| TC-01 | `POST /api/diagnosis/submit` | `SurveyPage.jsx`, `DiagnosisResultPage.jsx` | `DiagnosisResponse` (diagnosis_id, investment_type, score, confidence, characteristics, scenario_ratio, created_at) | `docs/generated_schema_examples.json#endpoints.POST /api/diagnosis/submit` |
| TC-02 | `POST /portfolio/generate` | `PortfolioRecommendationPage.jsx` | `PortfolioResponse` (allocation, portfolio, statistics, simulation_notes) | `docs/generated_schema_examples.json#endpoints.POST /portfolio/generate` |
| TC-03 | `POST /portfolio/custom` | `PortfolioBuilderPage.jsx` | `{success, portfolio:{portfolio_id, portfolio_name, weights, is_active, created_at}}` | `docs/generated_schema_examples.json#endpoints.POST /portfolio/custom` |
| TC-04 | `GET /api/v1/portfolios/{portfolio_id}/performance`, `GET /api/v1/portfolios/{portfolio_id}/metrics/{metric_key}` | `PortfolioExplanationPage.jsx` | `{success,data:{returns,cumulative_return,benchmark_return}}`, `{success,data:{metric_key,value,formatted_value}}` | `docs/generated_schema_examples.json#endpoints.GET /api/v1/portfolios/{portfolio_id}/performance`, `docs/generated_schema_examples.json#endpoints.GET /api/v1/portfolios/{portfolio_id}/metrics/{metric_key}` |
| TC-05 | `POST /api/v1/analysis/explain` | `PortfolioExplanationPage.jsx` | `AnalysisExplainResponse` (summary, performance_explanation[], risk_periods[], disclaimer) | `docs/generated_schema_examples.json#endpoints.POST /api/v1/analysis/explain` |
| TC-06 | `POST /api/v1/analysis/explain` | `PortfolioExplanationPage.jsx` | `AnalysisExplainResponse` (risk_periods[]) | `docs/generated_schema_examples.json#endpoints.POST /api/v1/analysis/explain` |
| TC-07 | `POST /api/v1/analysis/compare-periods` | `PortfolioComparisonPage.jsx` | `{period_count, period_explanations[], comparison_analysis, disclaimer}` | `docs/generated_schema_examples.json#endpoints.POST /api/v1/analysis/compare-periods` |
| TC-08 | `POST /api/v1/analysis/history`, `GET /api/v1/analysis/history`, `DELETE /api/v1/analysis/history/{history_id}` | `ReportHistoryPage.jsx` | `HistoryResponse`, `{items,total,skip,limit}` | `docs/generated_schema_examples.json#endpoints.POST /api/v1/analysis/history` |
| TC-09 | `POST /api/v1/analysis/explain/pdf`, `POST /api/v1/analysis/premium-report/pdf` | `ReportPage.jsx` | `application/pdf` 스트림 | `docs/generated_schema_examples.json#endpoints.POST /api/v1/analysis/explain/pdf` |
| TC-10 | 예: `POST /api/v1/admin/data-load/stock-prices` | `AdminPage.jsx` | `403 Forbidden` (비권한) | `docs/generated_schema_examples.json#endpoints.POST /api/v1/admin/data-load/stock-prices` |
| TC-11 | `POST /api/v1/events` | `AdminPage.jsx` | `{success,data:{event_id,event_type,path,status,occurred_at}}` | `docs/generated_schema_examples.json#endpoints.POST /api/v1/events` |
| TC-12 | 출력 스키마 검증: `docs/phase8/output_schema_v3.json` | (N/A) | Output Schema v3 (period, metrics, disclaimer_version, extensions.*) | `docs/generated_schema_examples.json#schemas.docs/phase8/output_schema_v3.json` |

## 20-2. 테스트 케이스 응답 JSON 예시(스키마 정합)
자동 생성 스니펫: `scripts/generate_schema_examples.py` → `docs/generated_schema_examples.json`
TC-01 (`POST /api/diagnosis/submit`) 예시
```json
{
  "diagnosis_id": "diag_123",
  "investment_type": "moderate",
  "score": 6.5,
  "confidence": 0.78,
  "monthly_investment": 50,
  "description": "균형형 성향입니다.",
  "characteristics": ["안정성과 성장의 균형"],
  "scenario_ratio": {
    "MIN_VOL": 0.4,
    "DEFENSIVE": 0.3,
    "GROWTH": 0.3
  },
  "reference_only": {
    "historical_avg_return": "연 4~7%",
    "disclaimer": "과거 데이터 기반 참고 정보입니다."
  },
  "created_at": "2026-02-06T12:00:00Z",
  "ai_analysis": null
}
```

TC-02 (`POST /portfolio/generate`) 예시
```json
{
  "investment_type": "moderate",
  "total_investment": 10000000,
  "allocation": {
    "stocks": {"ratio": 40, "amount": 4000000, "min_ratio": 30, "max_ratio": 50},
    "etfs": {"ratio": 20, "amount": 2000000, "min_ratio": 15, "max_ratio": 25},
    "bonds": {"ratio": 25, "amount": 2500000, "min_ratio": 20, "max_ratio": 30},
    "deposits": {"ratio": 15, "amount": 1500000, "min_ratio": 10, "max_ratio": 20}
  },
  "portfolio": {
    "stocks": [],
    "etfs": [],
    "bonds": [],
    "deposits": []
  },
  "statistics": {
    "total_investment": 10000000,
    "actual_invested": 9800000,
    "cash_reserve": 200000,
    "expected_annual_return": 7.5,
    "portfolio_risk": "medium",
    "diversification_score": 80,
    "total_items": 8,
    "asset_breakdown": {
      "stocks_count": 3,
      "etfs_count": 2,
      "bonds_count": 2,
      "deposits_count": 1
    }
  },
  "simulation_notes": ["시나리오 기반 포트폴리오 구성 예시입니다."]
}
```

TC-03 (`POST /portfolio/custom`) 예시
```json
{
  "success": true,
  "portfolio": {
    "portfolio_id": 101,
    "owner_user_id": 12,
    "portfolio_name": "My Custom",
    "description": "테스트",
    "base_template_id": null,
    "is_active": true,
    "created_at": "2026-02-06T12:00:00Z",
    "updated_at": "2026-02-06T12:00:00Z",
    "weights": {
      "EQUITY": 0.5,
      "BOND": 0.3,
      "CASH": 0.2
    }
  },
  "message": "포트폴리오가 생성되었습니다."
}
```

TC-04 (`GET /api/v1/portfolios/{portfolio_id}/performance`) 예시
```json
{
  "success": true,
  "data": {
    "portfolio_id": 101,
    "as_of_date": "2026-02-05",
    "performance_type": "LIVE",
    "returns": {"1M": 0.012, "3M": 0.035, "6M": 0.054, "YTD": 0.021},
    "selected_period": "3M",
    "selected_return": 0.035,
    "cumulative_return": 0.125,
    "benchmark_return": 0.11,
    "is_reference": false,
    "is_stale": false,
    "warning_message": null,
    "status_message": null
  }
}
```

TC-04 (`GET /api/v1/portfolios/{portfolio_id}/metrics/{metric_key}`) 예시
```json
{
  "success": true,
  "data": {
    "portfolio_id": 101,
    "metric_key": "cagr",
    "metric_label": "연복리수익률",
    "as_of_date": "2026-02-05",
    "value": 0.085,
    "formatted_value": "8.50%",
    "definition": "기간 동안의 성과를 설명하기 위한 지표입니다.",
    "formula": "(종료 가치 / 시작 가치)^(1/년수) - 1",
    "factors": ["fees", "dividend"],
    "notes": ["과거 성과이며 미래 수익을 보장하지 않습니다."],
    "is_reference": false,
    "is_stale": false,
    "warning_message": null,
    "status_message": null
  }
}
```

TC-05 (`POST /api/v1/analysis/explain`) 예시
```json
{
  "summary": "지난 1년간 연평균 8.5% 수익을 기록했습니다.",
  "performance_explanation": [
    {
      "metric": "CAGR",
      "value": 0.085,
      "formatted_value": "+8.50%",
      "description": "연평균 8.5%의 수익률을 기록했습니다.",
      "context": "CAGR은 장기 수익 흐름을 보여줍니다.",
      "level": "moderate"
    }
  ],
  "risk_explanation": "중간 수준의 변동성을 보였습니다.",
  "risk_periods": [],
  "comparison": null,
  "disclaimer": "본 분석은 과거 데이터에 기반한 참고 정보입니다."
}
```

TC-06 (`POST /api/v1/analysis/explain`) 예시
```json
{
  "summary": "요약 문구",
  "performance_explanation": [],
  "risk_explanation": "위험 구간이 존재했습니다.",
  "risk_periods": [
    {
      "period_type": "MAX_DRAWDOWN",
      "start_date": "2024-03-01",
      "end_date": "2024-06-15",
      "description": "최대 낙폭 구간입니다.",
      "severity": "HIGH"
    }
  ],
  "comparison": null,
  "disclaimer": "과거 데이터 기반 참고 정보입니다."
}
```

TC-07 (`POST /api/v1/analysis/compare-periods`) 예시
```json
{
  "period_count": 2,
  "period_explanations": [
    {
      "period_label": "2023H1",
      "start_date": "2023-01-01",
      "end_date": "2023-06-30",
      "metrics": {
        "cagr": 0.07,
        "volatility": 0.12,
        "mdd": -0.1,
        "sharpe": 0.6
      },
      "explanation": {
        "summary": "요약 문구",
        "performance_explanation": [],
        "risk_explanation": "위험 요약",
        "risk_periods": [],
        "comparison": null,
        "disclaimer": "과거 데이터 기반 참고 정보입니다."
      }
    }
  ],
  "comparison_analysis": {
    "trend": "개선"
  },
  "disclaimer": "본 분석은 투자 권유가 아닙니다."
}
```

TC-08 (`POST /api/v1/analysis/history`) 예시
```json
{
  "history_id": 55,
  "user_id": 12,
  "portfolio_id": 101,
  "portfolio_type": "CUSTOM",
  "period_start": "2023-01-01T00:00:00",
  "period_end": "2024-01-01T00:00:00",
  "input_metrics": {
    "cagr": 0.085,
    "volatility": 0.15,
    "mdd": -0.12,
    "sharpe": 0.75,
    "rf_annual": 0.035,
    "benchmark_name": "KOSPI 200",
    "benchmark_return": 0.065
  },
  "explanation_result": {
    "summary": "요약 문구",
    "performance_explanation": [],
    "risk_explanation": "위험 요약",
    "risk_periods": [],
    "comparison": null,
    "disclaimer": "과거 데이터 기반 참고 정보입니다."
  },
  "report_title": "2023 결과",
  "pdf_downloaded": 0,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

TC-08 (`GET /api/v1/analysis/history`) 예시
```json
{
  "items": [
    {
      "history_id": 55,
      "user_id": 12,
      "portfolio_id": 101,
      "portfolio_type": "CUSTOM",
      "period_start": "2023-01-01T00:00:00",
      "period_end": "2024-01-01T00:00:00",
      "input_metrics": {
        "cagr": 0.085,
        "volatility": 0.15,
        "mdd": -0.12,
        "sharpe": 0.75,
        "rf_annual": 0.035,
        "benchmark_name": "KOSPI 200",
        "benchmark_return": 0.065
      },
      "explanation_result": {
        "summary": "요약 문구",
        "performance_explanation": [],
        "risk_explanation": "위험 요약",
        "risk_periods": [],
        "comparison": null,
        "disclaimer": "과거 데이터 기반 참고 정보입니다."
      },
      "report_title": "2023 결과",
      "pdf_downloaded": 0,
      "created_at": "2026-02-06T12:00:00Z",
      "updated_at": "2026-02-06T12:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

TC-09 (`POST /api/v1/analysis/explain/pdf`) 예시
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="basic_report_20260206_120000.pdf"
```

TC-10 (비권한) 예시
```json
{
  "error": {
    "code": "ADMIN_ONLY",
    "message": "관리자 권한이 필요합니다",
    "status": 403
  }
}
```

TC-11 (`POST /api/v1/events`) 예시
```json
{
  "success": true,
  "data": {
    "event_id": 987,
    "event_type": "PORTFOLIO_ANALYSIS",
    "path": "/portfolio/explain",
    "status": "COMPLETED",
    "reason_code": null,
    "metadata": {"source": "ui"},
    "occurred_at": "2026-02-06T12:00:00Z"
  }
}
```

TC-12 (Output Schema v3) 예시
```json
{
  "period": {"start": "2023-01-01", "end": "2024-01-01"},
  "metrics": {
    "cumulative_return": 0.12,
    "cagr": 0.085,
    "volatility": 0.15,
    "max_drawdown": -0.12
  },
  "disclaimer_version": "v3",
  "extensions": {
    "yearly_returns": [{"year": 2023, "value": 0.08}],
    "drawdown_segments": [
      {"start": "2024-03-01", "end": "2024-06-15", "drawdown": -0.1}
    ]
  }
}
```
