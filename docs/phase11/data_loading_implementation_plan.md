# 실 데이터 적재 로직 구현 계획

작성일: 2026-01-24
버전: v1.0

---

## 1. 구현 범위

### 1.1 제약 조건 (Level 1)

| 항목 | 허용 | 금지 |
|------|------|------|
| 데이터 유형 | 과거 일별 시세 | 실시간, 장중 데이터 |
| 갱신 방식 | 수동 트리거 (Admin) | 자동 스케줄러 |
| 기준일 | 명시적 as_of_date 필수 | 암묵적 현재 시점 |
| 데이터 소스 | pykrx (KRX 과거 데이터) | 실시간 API |

### 1.2 구현 모듈

```
backend/app/services/
├── real_data_loader.py      # 메인 적재 서비스
├── pykrx_fetcher.py         # pykrx 연동 래퍼
├── data_quality_validator.py # 품질 검증
└── batch_manager.py         # 배치 관리

backend/app/routes/
└── admin_data_load.py       # Admin 전용 API
```

---

## 2. 구현 단계

### Phase 1: pykrx 연동 래퍼 (pykrx_fetcher.py)

**목적**: pykrx 라이브러리를 감싸서 일관된 인터페이스 제공

```python
class PykrxFetcher:
    def fetch_stock_ohlcv(ticker: str, start: date, end: date) -> List[Dict]
    def fetch_index_ohlcv(index_code: str, start: date, end: date) -> List[Dict]
    def fetch_stock_info(ticker: str, as_of: date) -> Dict
    def fetch_market_tickers(market: str, as_of: date) -> List[str]
```

### Phase 2: 배치 관리 (batch_manager.py)

**목적**: 적재 배치 생성, 상태 관리, 완료 처리

```python
class BatchManager:
    def create_batch(batch_type: str, source_id: str, as_of: date, ...) -> DataLoadBatch
    def start_batch(batch_id: int) -> None
    def complete_batch(batch_id: int, stats: Dict) -> None
    def fail_batch(batch_id: int, error: str) -> None
```

### Phase 3: 품질 검증 (data_quality_validator.py)

**목적**: 적재 전 데이터 품질 검증

```python
class DataQualityValidator:
    def validate_ohlcv(record: Dict) -> List[QualityIssue]
    def validate_stock_info(record: Dict) -> List[QualityIssue]
    def log_quality_issues(batch_id: int, issues: List) -> None
```

### Phase 4: 메인 적재 서비스 (real_data_loader.py)

**목적**: 전체 적재 프로세스 조율

```python
class RealDataLoader:
    def load_stock_prices(tickers: List[str], start: date, end: date, as_of: date) -> BatchResult
    def load_index_prices(codes: List[str], start: date, end: date, as_of: date) -> BatchResult
    def load_stock_info(tickers: List[str], as_of: date) -> BatchResult
```

### Phase 5: Admin API (admin_data_load.py)

**목적**: 관리자 전용 데이터 적재 엔드포인트

```
POST /api/v1/admin/data-load/stock-prices
POST /api/v1/admin/data-load/index-prices
POST /api/v1/admin/data-load/stock-info
GET  /api/v1/admin/data-load/batches
GET  /api/v1/admin/data-load/batches/{batch_id}
```

---

## 3. 상세 설계

### 3.1 적재 프로세스 흐름

```
1. Admin API 호출 (수동)
     ↓
2. 입력 검증
   - as_of_date 필수
   - start_date <= end_date <= as_of_date
   - end_date <= today
     ↓
3. 배치 생성 (status=PENDING)
     ↓
4. pykrx로 데이터 조회
     ↓
5. 품질 검증
   - DQ-001: close_price > 0
   - DQ-002: volume >= 0
   - DQ-003: high >= low
   - DQ-006: |change_rate| <= 30 (경고)
     ↓
6. DB 적재 (bulk insert)
     ↓
7. 배치 완료 (status=SUCCESS, 통계 기록)
```

### 3.2 에러 처리

| 에러 유형 | 처리 방식 |
|----------|----------|
| pykrx 조회 실패 | 배치 FAILED, 상세 오류 기록 |
| 품질 검증 ERROR | 해당 레코드 스킵, 로그 기록 |
| 품질 검증 WARNING | 레코드 적재, 품질 플래그 표시 |
| DB 적재 실패 | 롤백, 배치 FAILED |

### 3.3 품질 플래그

| 플래그 | 의미 |
|--------|------|
| NORMAL | 정상 데이터 |
| ADJUSTED | 수정 주가 적용 |
| ESTIMATED | 추정치 (결측 보간) |
| WARNING | 경고 있음 (이상치 가능성) |

---

## 4. 체크리스트

### Phase 1: pykrx 연동 ✅ 완료
- [x] PykrxFetcher 클래스 구현
- [x] fetch_stock_ohlcv 구현
- [x] fetch_index_ohlcv 구현
- [x] fetch_stock_info 구현
- [x] 에러 핸들링 (네트워크, 데이터 없음)

### Phase 2: 배치 관리 ✅ 완료
- [x] BatchManager 클래스 구현
- [x] create_batch 구현
- [x] start/complete/fail_batch 구현
- [x] 배치 상태 조회

### Phase 3: 품질 검증 ✅ 완료
- [x] DataQualityValidator 클래스 구현
- [x] OHLCV 검증 규칙 구현
- [x] 검증 결과 로깅

### Phase 4: 메인 적재 서비스 ✅ 완료
- [x] RealDataLoader 클래스 구현
- [x] load_stock_prices 구현
- [x] load_index_prices 구현
- [x] 트랜잭션 관리

### Phase 5: Admin API ✅ 완료
- [x] 라우터 생성
- [x] 스키마 정의
- [x] 엔드포인트 구현
- [x] 권한 검증 (admin only)

### Phase 6: 테스트 ✅ 완료
- [x] 단위 테스트 작성
- [ ] 통합 테스트 작성 (추후)
- [x] 품질 검증 테스트

---

## 5. 일정

| 단계 | 항목 | 예상 작업량 |
|------|------|------------|
| 1 | pykrx 연동 | 중 |
| 2 | 배치 관리 | 소 |
| 3 | 품질 검증 | 중 |
| 4 | 메인 적재 | 대 |
| 5 | Admin API | 중 |
| 6 | 테스트 | 중 |

---

## 6. 버전 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-01-24 | 최초 작성 |
| v1.1 | 2026-01-24 | 구현 완료 - 모든 Phase 완료 |
