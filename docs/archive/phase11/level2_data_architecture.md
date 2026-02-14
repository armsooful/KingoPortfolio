# Level 2 데이터 아키텍처 설계

작성일: 2026-01-24
버전: v1.0

---

## 1. 데이터 소스 확장 계획

### 1.1 Level별 데이터 소스

```
┌──────────────────────────────────────────────────────────────────────┐
│ Level 1 (현재)                                                        │
│ ┌─────────────┐                                                      │
│ │   pykrx     │ → 일별 OHLCV, 지수, PER/PBR/배당률                   │
│ └─────────────┘                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ Level 2 (계획)                                                        │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│ │   pykrx     │  │ DART OpenAPI│  │ KRX 정보    │                   │
│ └─────────────┘  └─────────────┘  └─────────────┘                   │
│        │                │                │                           │
│        ▼                ▼                ▼                           │
│    일별 시세        재무제표          기관/외국인                     │
│    지수             공시 정보         ETF 구성종목                    │
│    기본 지표        배당 이력                                           │
├──────────────────────────────────────────────────────────────────────┤
│ Level 3 (향후)                                                        │
│ ┌─────────────┐  ┌─────────────┐                                    │
│ │ 외부 벤더   │  │ 자체 계산   │                                    │
│ └─────────────┘  └─────────────┘                                    │
│    수급 분석        팩터 지표                                         │
│    센티먼트         커스텀 지수                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Level 2 핵심 데이터 소스

| 소스 | API | 주요 데이터 | 갱신 주기 |
|------|-----|------------|----------|
| **DART OpenAPI** | REST | 재무제표, 공시, 배당 | 분기/수시 |
| **KRX 정보데이터시스템** | 파일/REST | 업종, 기관매매, ETF | 일별 |
| **네이버 금융** | Scraping | 종목 뉴스, 컨센서스 | 일별 |

---

## 2. 확장 가능한 아키텍처

### 2.1 Fetcher 인터페이스 설계

```python
# app/services/fetchers/base_fetcher.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

@dataclass
class FetchResult:
    """데이터 조회 결과"""
    success: bool
    data: List[Dict[str, Any]]
    error_message: Optional[str] = None
    source_id: str = ""
    fetched_at: Optional[date] = None

class BaseFetcher(ABC):
    """데이터 소스 Fetcher 기본 클래스"""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """데이터 소스 ID"""
        pass

    @property
    @abstractmethod
    def supported_data_types(self) -> List[str]:
        """지원하는 데이터 유형 목록"""
        pass

    @abstractmethod
    def fetch(
        self,
        data_type: str,
        params: Dict[str, Any]
    ) -> FetchResult:
        """데이터 조회"""
        pass

    @abstractmethod
    def validate_params(
        self,
        data_type: str,
        params: Dict[str, Any]
    ) -> bool:
        """파라미터 검증"""
        pass
```

### 2.2 Fetcher 구현 예시

```python
# app/services/fetchers/pykrx_fetcher.py
class PykrxFetcher(BaseFetcher):
    source_id = "PYKRX"
    supported_data_types = ["STOCK_OHLCV", "INDEX_OHLCV", "STOCK_INFO", "FUNDAMENTAL"]

# app/services/fetchers/dart_fetcher.py
class DartFetcher(BaseFetcher):
    source_id = "DART"
    supported_data_types = ["FINANCIAL_STATEMENT", "DISCLOSURE", "DIVIDEND_HISTORY"]

# app/services/fetchers/krx_info_fetcher.py
class KrxInfoFetcher(BaseFetcher):
    source_id = "KRX_INFO"
    supported_data_types = ["INSTITUTION_TRADE", "ETF_PORTFOLIO"]
```

### 2.3 Fetcher Factory 패턴

```python
# app/services/fetchers/fetcher_factory.py

class FetcherFactory:
    """Fetcher 팩토리"""

    _fetchers: Dict[str, Type[BaseFetcher]] = {}

    @classmethod
    def register(cls, fetcher_class: Type[BaseFetcher]):
        cls._fetchers[fetcher_class.source_id] = fetcher_class

    @classmethod
    def get_fetcher(cls, source_id: str) -> BaseFetcher:
        if source_id not in cls._fetchers:
            raise ValueError(f"Unknown source: {source_id}")
        return cls._fetchers[source_id]()

    @classmethod
    def get_fetcher_for_data_type(cls, data_type: str) -> List[BaseFetcher]:
        """특정 데이터 유형을 지원하는 모든 Fetcher 반환"""
        return [
            fetcher_class()
            for fetcher_class in cls._fetchers.values()
            if data_type in fetcher_class.supported_data_types
        ]

# 등록
FetcherFactory.register(PykrxFetcher)
FetcherFactory.register(DartFetcher)
FetcherFactory.register(KrxInfoFetcher)
```

---

## 3. Level 2 추가 테이블 설계

### 3.1 재무제표 (DART)

```sql
CREATE TABLE financial_statement (
    statement_id    BIGSERIAL    PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL,
    fiscal_year     INTEGER      NOT NULL,
    fiscal_quarter  INTEGER      NOT NULL,  -- 1, 2, 3, 4 (연간은 4)
    report_type     VARCHAR(20)  NOT NULL,  -- 'ANNUAL', 'QUARTERLY'

    -- 손익계산서
    revenue                 BIGINT,         -- 매출액
    operating_income        BIGINT,         -- 영업이익
    net_income             BIGINT,         -- 당기순이익

    -- 재무상태표
    total_assets           BIGINT,         -- 자산총계
    total_liabilities      BIGINT,         -- 부채총계
    total_equity           BIGINT,         -- 자본총계

    -- 현금흐름표
    operating_cash_flow    BIGINT,
    investing_cash_flow    BIGINT,
    financing_cash_flow    BIGINT,

    -- 주요 비율
    roe                    DECIMAL(8,4),   -- ROE (%)
    roa                    DECIMAL(8,4),   -- ROA (%)
    debt_ratio             DECIMAL(8,4),   -- 부채비율 (%)

    -- 데이터 거버넌스
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER      REFERENCES data_load_batch(batch_id),
    as_of_date      DATE         NOT NULL,
    dart_rcept_no   VARCHAR(20),            -- DART 접수번호

    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_financial_statement UNIQUE (ticker, fiscal_year, fiscal_quarter, source_id)
);

CREATE INDEX idx_fin_stmt_ticker ON financial_statement(ticker);
CREATE INDEX idx_fin_stmt_fiscal ON financial_statement(fiscal_year, fiscal_quarter);
```

### 3.2 배당 이력 (DART)

```sql
CREATE TABLE dividend_history (
    dividend_id     BIGSERIAL    PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL,
    fiscal_year     INTEGER      NOT NULL,

    -- 배당 정보
    dividend_type       VARCHAR(20)  NOT NULL,  -- 'CASH', 'STOCK', 'INTERIM'
    dividend_per_share  DECIMAL(18,2),          -- 주당 배당금
    dividend_rate       DECIMAL(8,4),           -- 배당률 (%)
    dividend_yield      DECIMAL(8,4),           -- 배당수익률 (%)

    -- 배당 일정
    record_date         DATE,                   -- 배당 기준일
    payment_date        DATE,                   -- 배당 지급일
    ex_dividend_date    DATE,                   -- 배당락일

    -- 데이터 거버넌스
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER      REFERENCES data_load_batch(batch_id),
    as_of_date      DATE         NOT NULL,

    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_dividend_history UNIQUE (ticker, fiscal_year, dividend_type, source_id)
);

CREATE INDEX idx_dividend_ticker ON dividend_history(ticker);
CREATE INDEX idx_dividend_year ON dividend_history(fiscal_year);
```

### 3.3 기관/외국인 매매 (KRX)

```sql
CREATE TABLE institution_trade (
    trade_id        BIGSERIAL    PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL,
    trade_date      DATE         NOT NULL,

    -- 기관 매매
    institution_buy         BIGINT,  -- 기관 매수 (주)
    institution_sell        BIGINT,  -- 기관 매도 (주)
    institution_net         BIGINT,  -- 기관 순매수

    -- 외국인 매매
    foreign_buy             BIGINT,
    foreign_sell            BIGINT,
    foreign_net             BIGINT,

    -- 개인 매매
    individual_buy          BIGINT,
    individual_sell         BIGINT,
    individual_net          BIGINT,

    -- 외국인 보유
    foreign_holding_shares  BIGINT,  -- 외국인 보유 주식수
    foreign_holding_ratio   DECIMAL(8,4),  -- 외국인 지분율 (%)

    -- 데이터 거버넌스
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER      REFERENCES data_load_batch(batch_id),
    as_of_date      DATE         NOT NULL,

    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_institution_trade UNIQUE (ticker, trade_date, source_id)
);

CREATE INDEX idx_inst_trade_ticker ON institution_trade(ticker, trade_date);
CREATE INDEX idx_inst_trade_date ON institution_trade(trade_date);
```

---

## 4. DART OpenAPI 연동 설계

### 4.1 API 개요

| 항목 | 내용 |
|------|------|
| Base URL | `https://opendart.fss.or.kr/api/` |
| 인증 | API Key (crtfc_key) |
| 형식 | JSON / XML |
| 호출 제한 | 10,000건/일 |

### 4.2 주요 엔드포인트

| API | 용도 | 주요 파라미터 |
|-----|------|--------------|
| `/fnlttSinglAcntAll.json` | 단일회사 전체 재무제표 | corp_code, bsns_year, reprt_code |
| `/dvRs.json` | 배당 관련 사항 | corp_code, bsns_year |
| `/corpCode.xml` | 고유번호 목록 | - (전체 목록 다운로드) |
| `/list.json` | 공시 검색 | corp_code, bgn_de, end_de |

### 4.3 DartFetcher 설계

```python
# app/services/fetchers/dart_fetcher.py

class DartFetcher(BaseFetcher):
    """DART OpenAPI Fetcher"""

    BASE_URL = "https://opendart.fss.or.kr/api"

    source_id = "DART"
    supported_data_types = [
        "FINANCIAL_STATEMENT",
        "DIVIDEND",
        "DISCLOSURE",
        "CORP_CODE",
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._corp_code_cache: Dict[str, str] = {}  # ticker -> corp_code

    def fetch_financial_statement(
        self,
        ticker: str,
        fiscal_year: int,
        report_type: str,  # '11013'=1분기, '11012'=반기, '11014'=3분기, '11011'=사업보고서
    ) -> FetchResult:
        """재무제표 조회"""
        corp_code = self._get_corp_code(ticker)

        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": fiscal_year,
            "reprt_code": report_type,
            "fs_div": "CFS",  # 연결재무제표
        }

        response = requests.get(f"{self.BASE_URL}/fnlttSinglAcntAll.json", params=params)
        # ... 파싱 로직

    def fetch_dividend(
        self,
        ticker: str,
        fiscal_year: int,
    ) -> FetchResult:
        """배당 정보 조회"""
        corp_code = self._get_corp_code(ticker)

        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": fiscal_year,
        }

        response = requests.get(f"{self.BASE_URL}/dvRs.json", params=params)
        # ... 파싱 로직
```

### 4.4 DART 데이터 적재 흐름

```
1. Admin API 호출
   POST /api/v1/admin/data-load/financials
   {
     "tickers": ["005930", "000660"],
     "fiscal_year": 2024,
     "report_type": "ANNUAL",
     "as_of_date": "2025-03-31"
   }
     ↓
2. ticker → corp_code 변환
     ↓
3. DART API 호출 (rate limit 고려)
     ↓
4. 응답 파싱 및 정규화
     ↓
5. 품질 검증
     ↓
6. DB 적재
```

---

## 5. 데이터 소스 우선순위 전략

### 5.1 동일 데이터 다중 소스 처리

```python
class DataSourcePriority:
    """데이터 소스 우선순위 관리"""

    # 데이터 유형별 소스 우선순위
    PRIORITY = {
        "STOCK_OHLCV": ["PYKRX", "KRX_INFO", "NAVER"],
        "FINANCIAL_STATEMENT": ["DART", "PYKRX"],
        "DIVIDEND": ["DART", "PYKRX"],
        "INSTITUTION_TRADE": ["KRX_INFO"],
    }

    @classmethod
    def get_primary_source(cls, data_type: str) -> str:
        return cls.PRIORITY.get(data_type, [])[0]

    @classmethod
    def get_fallback_sources(cls, data_type: str) -> List[str]:
        return cls.PRIORITY.get(data_type, [])[1:]
```

### 5.2 크로스 검증

동일 데이터가 여러 소스에서 제공될 경우:

```python
def cross_validate(data_type: str, records: Dict[str, Any]) -> Dict:
    """
    다중 소스 데이터 크로스 검증

    예: PYKRX 재무지표 vs DART 재무제표
    """
    if data_type == "PER":
        pykrx_per = records.get("PYKRX", {}).get("per")
        dart_per = records.get("DART", {}).get("calculated_per")

        if pykrx_per and dart_per:
            diff_ratio = abs(pykrx_per - dart_per) / dart_per
            if diff_ratio > 0.1:  # 10% 이상 차이
                return {
                    "status": "WARNING",
                    "message": f"PER 불일치: PYKRX={pykrx_per}, DART={dart_per}",
                    "recommended": dart_per,  # DART 우선
                }

    return {"status": "OK"}
```

---

## 6. 마이그레이션 계획

### 6.1 단계별 전환

| 단계 | 작업 | 영향 범위 |
|------|------|----------|
| 1 | Level 2 테이블 생성 | DB |
| 2 | DART Fetcher 구현 | Backend |
| 3 | 기존 서비스에 Level 2 데이터 연동 | Backend |
| 4 | 평가 엔진에 재무지표 통합 | Phase 7+ |

### 6.2 하위 호환성

- Level 1 API는 그대로 유지
- Level 2 데이터는 선택적 확장 (`extensions` 필드)
- 기존 `KrxTimeSeries` → `StockPriceDaily` 점진적 전환

---

## 7. 환경 설정

### 7.1 API 키 관리

```python
# .env
DART_API_KEY=your_dart_api_key_here
KRX_INFO_USER=your_krx_user
KRX_INFO_PASSWORD=your_krx_password

# app/config.py
class Settings:
    dart_api_key: str = os.getenv("DART_API_KEY", "")
    krx_info_user: str = os.getenv("KRX_INFO_USER", "")
    krx_info_password: str = os.getenv("KRX_INFO_PASSWORD", "")
```

### 7.2 Rate Limit 관리

```python
class RateLimitManager:
    """API 호출 제한 관리"""

    LIMITS = {
        "DART": {"daily": 10000, "per_second": 1},
        "KRX_INFO": {"daily": 5000, "per_second": 2},
    }

    def can_call(self, source_id: str) -> bool:
        # Redis 또는 메모리 기반 카운터 체크
        pass

    def record_call(self, source_id: str) -> None:
        # 호출 기록
        pass
```

---

## 8. 버전 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-01-24 | 최초 작성 |
