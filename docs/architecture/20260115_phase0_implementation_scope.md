# Phase 0 현재 구현 코드 범위 정리 (현행 코드 기준)
최초작성일자: 2026-01-15
최종수정일자: 2026-01-18

작성일: 2026-01-15

본 문서는 제공된 코드베이스(`ForestoCompass.zip` → `KingoPortfolio-main/`)에서 **Phase 0(정렬 단계)**와 직접적으로 연관되는 **현재 구현 코드 범위**를 파일 단위로 인벤토리화한 것이다.
Phase 0의 목표(추천 차단/설명 중심/손실·회복 KPI 우선/재현성 최소요건)가 **완료되었음을 의미하지 않는다**. 여기서는 **현재 코드에서 해당 기능이 걸쳐 있는 위치**를 정리한다.

## 1. Phase 0 범위에 해당하는 구현 모듈(Backend)

### 1.1 추천/선정(Recommendation/Selection) 계열 (규제·신뢰 리스크 핵심)

|파일|주요 책임|핵심 함수/메서드|비고|
|---|---|---|---|
|`backend/app/db_recommendation_engine.py`|DB 기반 상품 샘플링/추천 후보 조회|`DBProductSampler.get_recommended_*`, `get_all_recommendations`|**추천 실행의 관문**|
|`backend/app/services/portfolio_engine.py`|성향/선호 기반 포트폴리오 생성 및 종목/ETF/채권/예금 선정|`PortfolioEngine.generate_portfolio`, `_select_*`, `_calculate_*_score`, `_generate_stock_rationale`, `_generate_recommendations`|**선정/점수화/사유 생성** 포함|

### 1.2 성향 진단/설문 입력 (Phase 0에서는 1급 입력에서 2급 기능으로 격하 대상)

|파일|주요 책임|비고|
|---|---|---|
|`backend/app/diagnosis.py`|설문/입력 기반 진단 계산(보수/중립/공격 등)|현행 플로우의 시작점|
|`backend/app/routes/diagnosis.py`|진단 제출/조회/이력/내 상품/내보내기 API|`POST /submit`, `GET /me`, `GET /{diagnosis_id}` 등|
|`backend/app/routes/survey.py`|설문 문항 제공/제출|`GET /questions`, `POST /submit`|
|`backend/app/main.py`|설문 문항 상수(`SURVEY_QUESTIONS`) 포함|설문 중심 UX 고착 가능 지점|

### 1.3 포트폴리오 생성/시뮬레이션/백테스트 (Phase 0 KPI 전환의 적용 지점)

|파일|주요 책임|비고|
|---|---|---|
|`backend/app/routes/portfolio.py`|포트폴리오 생성/리밸런싱/시뮬레이션 API|`POST /generate`, `POST /simulate` 등이 **추천/예상수익**과 연결될 수 있음|
|`backend/app/routes/backtesting.py`|백테스트 실행/비교/메트릭 API|`POST /run`, `POST /compare`|
|`backend/app/services/backtesting.py`|백테스트 계산 로직|결과 지표를 **손실·회복 중심**으로 재정렬/확장해야 하는 위치|
|`backend/app/services/quant_analyzer.py`|리스크/수익 지표 계산(예: MDD)|MDD는 존재하나 **회복기간/최악 지속**은 별도 보강 필요|

### 1.4 리포트/설명 출력 (Phase 0에서 ‘설명 중심’ 전환 대상)

|파일|주요 책임|비고|
|---|---|---|
|`backend/app/routes/pdf_report.py`|PDF 리포트 라우터|설명형 리포트로 확장 가능한 기반|
|`backend/app/services/report_generator.py`|리포트 콘텐츠 생성|어휘/지표 우선순위 조정 지점|
|`backend/app/services/pdf_report_generator.py`|PDF 생성 로직|시각화/지표 표기 교체 지점|

## 2. Phase 0 범위에 해당하는 구현 모듈(Frontend)

|파일|주요 화면/컴포넌트|비고|
|---|---|---|
|`frontend/src/pages/BacktestPage.jsx`|백테스트 실행/결과 화면|지표 표기 순서를 **손실·회복 우선**으로 재배치 대상|
|`frontend/src/components/QuantAnalysis.jsx`|정량 분석/리스크 지표 표시|MDD 표시는 있으나 ‘회복기간’ 등 핵심 KPI 보강 필요|
|`frontend/src/components/InvestmentReport.jsx`|투자 리포트 UI|‘추천/예상’ 어휘 및 노출 점검 대상|
|`frontend/src/components/Valuation.jsx`|가치평가/시나리오(DCF/DDM) UI|투자 추천으로 오인되는 카피/표현 점검 필요|

## 3. Phase 0 관련 문서(정책/용어/고지)

|파일|내용|비고|
|---|---|---|
|`DISCLAIMER_AND_TERMINOLOGY_SUMMARY.md`|면책/용어 요약|문구는 있으나 **행동(추천 실행)** 차단이 우선|
|`TERMINOLOGY_GUIDE.md`|권장 용어/금지 용어 가이드|프론트/백 응답 필드 네이밍에 반영 필요|
|`README.md`|프로젝트 소개/포지셔닝|‘추천 플랫폼’ 뉘앙스 문구 존재 시 수정 대상|

## 4. 현재 코드 기준 Phase 0 ‘미구현/부재’ 항목(중요)

아래는 Phase 0 목표 대비 **코드상 명확한 구현 흔적이 확인되지 않는 항목**이다(현행 zip 기준).
- **추천/선정 로직 차단용 Feature Flag**(예: `FEATURE_RECOMMENDATION_ENGINE=0`) 부재
- **시나리오 기반 API**(예: `GET /scenarios`, `POST /simulations/run`) 부재
- **재현성 표준**: `request_hash` 생성 및 결과 캐시/재사용(sim_run/sim_path/sim_summary) 구조 부재
- **금지어(추천/권유) 스캔 자동화**(CI/테스트) 부재(문서 가이드는 존재)

## 5. 라우터(Endpoint) 인벤토리 (Phase 0 영향 범위)

### 5.1 Portfolio 라우터: `backend/app/routes/portfolio.py`

- `POST /generate`
- `POST /rebalance/{diagnosis_id}`
- `GET /asset-allocation/{investment_type}`
- `GET /available-sectors`
- `POST /simulate`

### 5.2 Backtesting 라우터: `backend/app/routes/backtesting.py`

- `POST /run`
- `POST /compare`
- `GET /metrics/{investment_type}`

### 5.3 Diagnosis 라우터: `backend/app/routes/diagnosis.py`

- `POST /submit`
- `GET /me`
- `GET /{diagnosis_id}`
- `GET /history/all`
- `GET /me/products`
- `GET /{diagnosis_id}/export/csv`
- `GET /{diagnosis_id}/export/excel`
- `GET /history/export/csv`

### 5.4 Survey 라우터: `backend/app/routes/survey.py`

- `GET /questions`
- `POST /submit`

### 5.5 PDF Report 라우터: `backend/app/routes/pdf_report.py`

- `GET /portfolio-pdf`
- `GET /diagnosis-pdf/{diagnosis_id}`
- `GET /preview`

## 6. 요약: Phase 0 코드 변경이 집중될 파일 TOP 10

1. `backend/app/services/portfolio_engine.py`
2. `backend/app/db_recommendation_engine.py`
3. `backend/app/routes/portfolio.py`
4. `backend/app/diagnosis.py`
5. `backend/app/routes/diagnosis.py`
6. `backend/app/routes/backtesting.py`
7. `backend/app/services/backtesting.py`
8. `backend/app/services/quant_analyzer.py`
9. `frontend/src/pages/BacktestPage.jsx`
10. `frontend/src/components/QuantAnalysis.jsx`

---

### 부록 A. 파일 메타데이터(크기/수정일)

|파일|크기(bytes)|수정일시|
|---|---:|---|
|`backend/app/db_recommendation_engine.py`|5722|2026-01-12T14:38:33|
|`backend/app/services/portfolio_engine.py`|30146|2026-01-12T14:38:33|
|`backend/app/diagnosis.py`|6900|2026-01-12T14:38:33|
|`backend/app/routes/portfolio.py`|10018|2026-01-12T14:38:33|
|`backend/app/routes/diagnosis.py`|15022|2026-01-12T14:38:33|
|`backend/app/routes/backtesting.py`|8586|2026-01-12T14:38:33|
|`backend/app/services/backtesting.py`|14872|2026-01-12T14:38:33|
|`backend/app/services/quant_analyzer.py`|21427|2026-01-12T14:38:33|
|`backend/app/routes/pdf_report.py`|7111|2026-01-12T14:38:33|
|`backend/app/services/report_generator.py`|22015|2026-01-12T14:38:33|
|`backend/app/services/pdf_report_generator.py`|18366|2026-01-12T14:38:33|
|`backend/app/main.py`|17220|2026-01-12T14:38:33|
|`frontend/src/pages/BacktestPage.jsx`|13713|2026-01-12T14:38:33|
|`frontend/src/components/QuantAnalysis.jsx`|14272|2026-01-12T14:38:33|
|`frontend/src/components/InvestmentReport.jsx`|22378|2026-01-12T14:38:33|
|`frontend/src/components/Valuation.jsx`|13174|2026-01-12T14:38:33|
|`DISCLAIMER_AND_TERMINOLOGY_SUMMARY.md`|6755|2026-01-12T14:38:33|
|`TERMINOLOGY_GUIDE.md`|7553|2026-01-12T14:38:33|
|`README.md`|19666|2026-01-12T14:38:33|
