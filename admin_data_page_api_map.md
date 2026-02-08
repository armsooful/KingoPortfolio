# /admin/data 버튼 → API 매핑

이 문서는 `http://localhost:5173/admin/data` 페이지에서 각 버튼이 호출하는 API를 정리한 것입니다.

## 데이터 수집

| 버튼/액션 | HTTP | API |
|---|---|---|
| 📦 전체 데이터 | POST | `/admin/load-data` |
| 📈 주식 데이터 | POST | `/admin/load-stocks` |
| 📊 ETF 데이터 | POST | `/admin/load-etfs` |

## Alpha Vantage - 미국 주식 데이터

| 버튼/액션 | HTTP | API |
|---|---|---|
| 🇺🇸 미국 주식 전체 수집 | POST | `/admin/alpha-vantage/load-all-stocks` |
| 📊 미국 ETF 전체 수집 | POST | `/admin/alpha-vantage/load-all-etfs` |
| 📈 시계열 데이터 수집 (Compact) | POST | `/admin/alpha-vantage/load-all-timeseries?outputsize=compact` |
| 📈 시세 수집 (특정 심볼) | POST | `/admin/alpha-vantage/load-stock/{symbol}` |
| 📊 재무제표 수집 (특정 심볼) | POST | `/admin/alpha-vantage/load-financials/{symbol}` |

## pykrx - 한국 주식 시계열 데이터

| 버튼/액션 | HTTP | API |
|---|---|---|
| 📊 시계열 데이터 수집 (단일 종목) | POST | `/admin/krx-timeseries/load-stock/{ticker}?days={days}` |
| 🚀 일괄 수집 시작 | POST | `/admin/krx-timeseries/load-all-stocks?days={days}&limit={limit}` |

## pykrx - 한국 주식 기본 정보

| 버튼/액션 | HTTP | API |
|---|---|---|
| 🇰🇷 한국 주식 전체 수집 | POST | `/admin/pykrx/load-all-stocks` |
| 📊 한국 ETF 전체 수집 | POST | `/admin/pykrx/load-all-etfs` |
| 📈 주식 수집 (특정 종목) | POST | `/admin/pykrx/load-stock/{ticker}` |
| 📊 ETF 수집 (특정 종목) | POST | `/admin/pykrx/load-etf/{ticker}` |

## pykrx - 재무 지표 데이터

| 버튼/액션 | HTTP | API |
|---|---|---|
| 📈 재무 지표 전체 수집 | POST | `/admin/pykrx/load-all-financials` |
| 📊 개별종목 재무 지표 수집 | POST | `/admin/pykrx/load-financials/{ticker}` |

## 배당/기업액션/채권/재무제표

| 버튼/액션 | HTTP | API |
|---|---|---|
| 배당 이력 적재 (FSC) | POST | `/admin/fsc/load-dividends` |
| 기업 액션 적재 | POST | `/admin/dart/load-corporate-actions` |
| 채권 기본정보 적재 | POST | `/admin/fsc/load-bonds` |
| 재무제표 적재 (DART) | POST | `/admin/dart/load-financials?fiscal_year=...&report_type=...&limit=...` |

## FinanceDataReader 종목 마스터

| 버튼/액션 | HTTP | API |
|---|---|---|
| FDR 종목 마스터 적재 | POST | `/admin/fdr/load-stock-listing` |

## 데이터 조회 탭

| 버튼/액션 | HTTP | API |
|---|---|---|
| 📈 주식 | GET | `/admin/stocks?skip=0&limit=100` |
| 📊 ETF | GET | `/admin/etfs?skip=0&limit=100` |
| 💰 채권 | GET | `/admin/bonds?skip=0&limit=100` |
| 🏦 예적금 | GET | `/admin/deposits?skip=0&limit=100` |

## 진행 상황 모달 폴링

| 용도 | HTTP | API |
|---|---|---|
| Progress 모달 폴링 | GET | `/admin/progress/{task_id}` |
