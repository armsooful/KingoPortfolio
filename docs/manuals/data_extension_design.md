# 데이터 확장 설계 (배당/분할/벤치마크)

## 목적
백테스팅 및 포트폴리오 분석을 위한 필수 데이터(배당, 분할/합병, 시가총액, 벤치마크 지수)를 기존 시스템에 확장 적재한다.

## 범위
- 배당 이력 (Dividend)
- 분할/합병 등 주식 액션 (Corporate Actions)
- 벤치마크 지수 (KOSPI/KOSDAQ)
- 시가총액(기존 적재 유지)

## 데이터 소스
- DART: 배당 및 기업 공시 기반 액션 정보
- pykrx: 벤치마크 지수 OHLCV

## 스키마 설계

### 1) 배당 이력 (이미 존재)
테이블: `dividend_history`
- ticker
- fiscal_year
- dividend_type (CASH/STOCK/INTERIM)
- dividend_per_share
- dividend_rate
- dividend_yield
- record_date / payment_date / ex_dividend_date
- source_id / batch_id / as_of_date

### 2) 기업 액션 (신규)
테이블: `corporate_action`
- action_id (PK)
- ticker
- action_type (SPLIT, REVERSE_SPLIT, MERGER, SPINOFF)
- ratio (예: 2.0 → 1:2 분할)
- effective_date
- reference_doc (공시 번호/링크 key)
- source_id / batch_id / as_of_date

### 3) 벤치마크 지수 (이미 존재)
테이블: `index_price_daily`
- index_code
- trade_date
- open/high/low/close/volume
- source_id / batch_id / as_of_date

## 적재 파이프라인 확장

### 배당 이력
- DART fetcher로 `DIVIDEND_HISTORY` 적재
- `RealDataLoader.load_dividend_history()` 유지

### 기업 액션 (분할/합병)
1) DART 공시 목록에서 분할/합병 키워드 필터
2) 공시 상세에서 분할 비율, 효력 발생일 파싱
3) `corporate_action` 테이블 적재
4) 보정 계산 시 `adj_close_price` 재산출 기준으로 사용

### 벤치마크 지수
- 기존 `IndexPriceDaily` 적재 사용
- 비교 기준 지수 코드는 설정 파일로 관리

## 백테스팅 적용 규칙
- 수익률 계산 기본값은 `adj_close_price` 우선
- `adj_close_price`가 NULL이면 `close_price` 사용
- 기업 액션 발생일 이후 구간은 분할 비율 반영

## 운영/검증
- 배치 유형 추가: `DIVIDEND`, `ACTION`
- 샘플 검증: 분할 발생 종목 1~2개 기준
- 배당/분할 이벤트 전후 수익률 비교 테스트 추가

## API 설계 (관리자용)
- `POST /admin/dart/load-dividends` (완료)
- `POST /admin/dart/load-corporate-actions` (신규)

## 개선 필요 사항
- DART 공시 파싱 정확도 확보
- 분할/합병 이벤트의 신뢰 가능한 비율 산출
- 보정 로직 단위 테스트 및 재현성 검증
