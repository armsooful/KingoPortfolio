# 데이터 품질 정책 (Phase 1)

> 작성일: 2026-01-15
> 적용 대상: daily_price, daily_return 테이블

## 1. 결측 데이터 처리 기준

### 1.1 휴장일 (Market Holiday)

| 구분 | 처리 방식 |
|------|----------|
| 주말 (토/일) | 데이터 없음 (정상) |
| 공휴일 | 데이터 없음 (정상) |
| 임시휴장 | 데이터 없음 (정상) |

**원칙**: 휴장일에는 데이터를 적재하지 않음. 시뮬레이션 엔진에서 전일 데이터를 사용.

### 1.2 결측 데이터 (Missing Data)

| 상황 | 처리 방식 | data_quality |
|------|----------|--------------|
| 거래 정지 | 전일 종가 사용 | `MISSING` |
| 상장 전 | 데이터 없음 | N/A |
| 데이터 소스 오류 | 재시도 후 스킵 | `MISSING` |

### 1.3 data_quality 필드 값

| 값 | 설명 |
|----|------|
| `OK` | 정상 데이터 |
| `MISSING` | 원본 데이터 없음 (전일 데이터 사용) |
| `IMPUTED` | 보간법으로 생성된 데이터 (향후 구현) |

---

## 2. 일봉가격 (daily_price) 적재 기준

### 2.1 필수 필드

| 필드 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| instrument_id | ✅ | - | 금융상품 ID |
| trade_date | ✅ | - | 거래일자 |
| close_price | ✅ | - | 종가 |
| open_price | ❌ | NULL | 시가 |
| high_price | ❌ | NULL | 고가 |
| low_price | ❌ | NULL | 저가 |
| volume | ❌ | NULL | 거래량 |
| adj_close_price | ❌ | NULL | 조정 종가 |
| load_id | ❌ | NULL | 적재 이력 ID |

### 2.2 적재 주기

| 환경 | 주기 | 시간 |
|------|------|------|
| 개발 | 수동 | - |
| 운영 | 일 1회 | 장 마감 후 (15:30 이후) |

### 2.3 데이터 소스 우선순위

1. **pykrx** (KRX 종목): 무료, 한국 시장
2. **Alpha Vantage** (미국 종목): API 제한 있음
3. **CSV 수동 업로드**: 백업/테스트용

---

## 3. 일간수익률 (daily_return) 생성 기준

### 3.1 계산 공식

```
daily_return = (close_price[t] - close_price[t-1]) / close_price[t-1]
log_return = ln(close_price[t] / close_price[t-1])
```

### 3.2 처리 규칙

| 상황 | 처리 |
|------|------|
| 첫 거래일 | 수익률 = 0 |
| 전일 데이터 없음 | 수익률 = NULL, data_quality = `MISSING` |
| 분할/배당 | adj_close_price 사용 권장 |

### 3.3 생성 시점

- **트리거**: daily_price 적재 후 자동 실행 (P1-B3)
- **배치**: 매일 장 마감 후

---

## 4. 데이터 검증 쿼리

### 4.1 결측일 확인

```sql
-- 특정 종목의 결측일 확인 (영업일 기준)
WITH date_series AS (
    SELECT generate_series(
        '2025-01-01'::date,
        '2025-12-31'::date,
        '1 day'::interval
    )::date AS trade_date
),
business_days AS (
    SELECT trade_date
    FROM date_series
    WHERE EXTRACT(DOW FROM trade_date) NOT IN (0, 6)  -- 주말 제외
)
SELECT bd.trade_date
FROM business_days bd
LEFT JOIN daily_price dp
    ON dp.trade_date = bd.trade_date
    AND dp.instrument_id = 1  -- 특정 종목
WHERE dp.trade_date IS NULL
ORDER BY bd.trade_date;
```

### 4.2 이상치 확인

```sql
-- 일간 변동률 10% 이상인 데이터
SELECT
    im.ticker,
    dp.trade_date,
    dp.close_price,
    LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date) AS prev_close,
    (dp.close_price - LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date))
    / NULLIF(LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date), 0) * 100 AS change_pct
FROM daily_price dp
JOIN instrument_master im ON dp.instrument_id = im.instrument_id
HAVING ABS(change_pct) > 10
ORDER BY ABS(change_pct) DESC;
```

### 4.3 적재 현황 리포트

```sql
-- 종목별 적재 현황
SELECT
    im.ticker,
    im.name_ko,
    COUNT(dp.trade_date) AS total_days,
    MIN(dp.trade_date) AS first_date,
    MAX(dp.trade_date) AS last_date,
    MAX(dp.trade_date) - MIN(dp.trade_date) + 1 AS expected_days
FROM instrument_master im
LEFT JOIN daily_price dp ON im.instrument_id = dp.instrument_id
WHERE im.is_active = TRUE
GROUP BY im.instrument_id, im.ticker, im.name_ko
ORDER BY im.ticker;
```

---

## 5. 에러 처리

### 5.1 적재 실패 시

1. **source_load_history**에 `FAILED` 상태 기록
2. **error_message**에 상세 내용 저장
3. 운영팀에 알림 (향후 구현)

### 5.2 재시도 정책

| 오류 유형 | 재시도 | 대기 시간 |
|----------|--------|----------|
| 네트워크 오류 | 3회 | 5초 |
| API Rate Limit | 1회 | 60초 |
| 데이터 없음 | 0회 | - |

---

## 관련 문서

- [DB 설정 가이드](./db_setup.md)
- [API 스냅샷](./api_snapshot_simulation.md)
- [Phase 1 백로그](../Foresto_Phase1_작업티켓_백로그.md)

---

**검증 담당**: Claude Code
**마지막 업데이트**: 2026-01-15
