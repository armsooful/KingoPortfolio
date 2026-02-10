# 증분 시계열 데이터 적재 설계서

## 개요

stocks 테이블에 등록된 전체 종목을 대상으로 5년치 시계열 데이터(OHLCV)를 stock_price_daily 테이블에 적재한다.
이미 적재된 종목은 마지막 적재일 이후부터만 수집하여 부하를 줄인다.

## 배경

| 항목 | 값 |
|------|-----|
| 활성 종목 (stocks) | ~2,886개 |
| 5년치 예상 레코드 (전종목) | ~346만건 (2,886 x 1,200거래일) |
| 데이터 소스 | pykrx (KRX 공식 데이터) |
| 대상 테이블 | stock_price_daily |

## 아키텍처

### 데이터 흐름

```
stocks 테이블 → 종목 목록 조회
                    ↓
stock_price_daily → 종목별 MAX(trade_date) 조회
                    ↓
            종목별 수집 기간 계산
            (신규: 5년 전 ~ 오늘 / 증분: 마지막일+1 ~ 오늘 / 스킵: 이미 최신)
                    ↓
            ThreadPoolExecutor (4 workers)
                    ↓
            pykrx get_market_ohlcv() → load_daily_prices_batch()
                    ↓
            stock_price_daily (ON CONFLICT DO UPDATE)
```

### 핵심 로직

1. **종목별 마지막 적재일 1회 쿼리**: `GROUP BY ticker` + 기존 인덱스 활용
2. **수집 기간 분류**: 신규(5년치), 증분(delta), 스킵(최신)
3. **병렬 수집**: ThreadPoolExecutor + 워커별 독립 DB 세션
4. **배치 upsert**: PostgreSQL `ON CONFLICT DO UPDATE` (500건 단위)
5. **진행률 추적**: progress_tracker → ProgressModal 실시간 표시

## API

### `POST /admin/pykrx/load-stocks-incremental`

**Request Body**:
```json
{
  "default_days": 1825,
  "num_workers": 4,
  "market": null
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "incremental_xxxx",
  "message": "증분 적재 시작 (대상: 2886종목, ...)",
  "stats": {
    "total_stocks": 2886,
    "existing_tickers": 34,
    "new_stocks_estimate": 2852,
    "default_days": 1825,
    "num_workers": 4,
    "market": "전체"
  }
}
```

## 부하 관리

| 항목 | 설정 | 이유 |
|------|------|------|
| 스레드 수 | 4 (기본값) | 8GB MacBook, Zoom 동시 실행 |
| pykrx 호출 간격 | 0.1초 sleep | KRX 서버 부하 방지 |
| 배치 크기 | 500건/chunk | PostgreSQL 메모리 최적 |
| 진행률 업데이트 | 10건마다 1회 | 프론트엔드 폴링 부하 감소 |

## 예상 소요 시간

| 시나리오 | 소요 시간 |
|---------|-----------|
| 첫 실행 (2,852 신규 종목) | ~4-6시간 |
| 매일 증분 (전종목 1일분) | ~10-30분 |
| 시장별 분할 (KOSPI만) | ~2-3시간 |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/app/services/pykrx_loader.py` | `load_all_stocks_incremental()` 추가 |
| `backend/app/routes/admin.py` | `POST /admin/pykrx/load-stocks-incremental` 추가, `IncrementalLoadRequest` 모델 |
| `frontend/src/services/api.js` | `loadStocksIncremental()` 함수 추가 |
| `frontend/src/pages/DataManagementPage.jsx` | 증분 적재 UI 섹션 추가 |
