# 테스트 커버리지 확대 계획

## 현황
- 전체 커버리지: 39% (380 tests)
- 고커버리지: scoring_engine(98%), valuation(96%), quant_analyzer(78%), portfolio_engine(70%)
- **저커버리지 핵심 파일 (비즈니스 임팩트 순)**:

| 파일 | 현재 | 라인수 | 난이도 |
|------|------|--------|--------|
| `routes/stock_detail.py` | 0% | 269 | 쉬움 — DB mock만 필요 |
| `routes/market.py` | 11% | 246 | 중 — yfinance/pykrx mock |
| `services/backtesting.py` | 10% | 199 | 중 — 순수 계산 로직 |
| `services/scenario_simulation.py` | 9% | 198 | 어려움 — DB raw SQL |

## 전략
외부 API(yfinance, pykrx, Claude) 의존 코드는 `unittest.mock.patch`로 격리.
DB 의존 코드는 기존 `conftest.py` fixture(`db`, `client`, `test_admin`, `admin_headers`) 활용.

## 작업 단위 (3 batch, 순차 진행)

### Batch 1: stock_detail.py 엔드포인트 (쉬움, 0%→80%+ 목표)
**파일**: `tests/unit/test_stock_detail.py` (신규)
- `GET /{ticker}` — 종목 존재(with 시계열+통계) / 미존재(404)
- `POST /{ticker}/ai-commentary` — DB 캐시 히트(24h 이내) / 캐시 미스 → ScoringEngine mock / API키 미설정 fallback / Claude 에러 fallback + ai_error 필드
- `GET /search/ticker-list` — 검색어 없음 / 있음 / 결과 없음

### Batch 2: backtesting.py 순수 계산 (중, 10%→60%+ 목표)
**파일**: `tests/unit/test_backtesting_engine.py` (신규)
- `run_backtest` 입력 검증 — 기간 역순 ValueError, 30일 미만 ValueError
- `_calculate_metrics` — 수익률/변동성/샤프/MDD 계산 정확성
- `_should_rebalance` — monthly/quarterly/yearly/none 각 케이스
- `_initialize_portfolio` / `_get_price` — mock DB로 가격 반환

### Batch 3: market.py 유틸 함수 (중, 11%→50%+ 목표)
**파일**: `tests/unit/test_market.py` (신규)
- `calculate_market_sentiment` — 긍정(>0.5%)/부정(<-0.5%)/중립
- `generate_simple_summary` — KOSPI 상승/하락/보합 텍스트
- `get_mock_news` / `get_mock_stocks` — 정적 데이터 반환 확인
- `fetch_naver_finance_news` — httpx mock (성공/실패→mock 반환)

## 예상 추가 테스트 수: ~45개
## 신규 파일: 3개

## 검증
```bash
pytest backend/tests/unit/ -m unit --tb=short -q
```
