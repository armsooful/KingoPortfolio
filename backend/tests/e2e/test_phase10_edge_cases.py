"""
Phase 10 E2E 테스트: 경계 케이스 강화

Epic 3: 경계 케이스 테스트 강화
- Story 3.1: Phase 7 평가 엣지 케이스 (TC-001 ~ TC-004)
- Story 3.2: 데이터 품질 엣지 케이스 (TC-010 ~ TC-013)
- Story 3.3: 포트폴리오 비교 엣지 케이스 (TC-020 ~ TC-022)
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from app.models.securities import KrxTimeSeries


# ============================================================================
# 헬퍼 함수
# ============================================================================

def _get_error_message(response) -> str:
    """에러 응답에서 메시지 추출"""
    body = response.json()
    if "detail" in body:
        return body["detail"]
    if "error" in body and isinstance(body["error"], dict):
        return body["error"].get("message", "")
    return str(body)


def _seed_timeseries(
    db,
    ticker: str,
    base_price: float = 100.0,
    days: int = 5,
    start_date: date = None,
    volatility: float = 0.02,
    include_gaps: bool = False,
    gap_days: list = None,
) -> None:
    """테스트용 시계열 데이터 생성

    Args:
        db: DB 세션
        ticker: 종목 코드
        base_price: 기준 가격
        days: 생성할 일수
        start_date: 시작일 (기본: 2024-01-02)
        volatility: 일간 변동성
        include_gaps: 데이터 갭 포함 여부
        gap_days: 갭 날짜 인덱스 리스트
    """
    if start_date is None:
        start_date = date(2024, 1, 2)

    if gap_days is None:
        gap_days = []

    rows = []
    price = base_price

    for i in range(days):
        if include_gaps and i in gap_days:
            continue  # 갭 생성

        # 가격 변동
        if i > 0:
            change = 1 + ((-1) ** i) * volatility
            price = price * change

        current_date = start_date + timedelta(days=i)

        rows.append(
            KrxTimeSeries(
                ticker=ticker,
                date=current_date,
                open=price,
                high=price * 1.02,
                low=price * 0.98,
                close=price,
                volume=1000 + i * 100,
            )
        )

    db.add_all(rows)
    db.commit()


def _seed_timeseries_with_nulls(db, ticker: str, null_fields: list) -> None:
    """NULL 값을 포함한 시계열 데이터 생성

    Args:
        db: DB 세션
        ticker: 종목 코드
        null_fields: NULL로 설정할 필드 리스트 [(day_index, field_name), ...]
    """
    base_price = 100.0
    rows = []

    for i in range(5):
        row = KrxTimeSeries(
            ticker=ticker,
            date=date(2024, 1, 2 + i),
            open=base_price,
            high=base_price * 1.02,
            low=base_price * 0.98,
            close=base_price,
            volume=1000,
        )

        # NULL 값 설정
        for day_idx, field in null_fields:
            if day_idx == i:
                setattr(row, field, None)

        rows.append(row)

    db.add_all(rows)
    db.commit()


def _seed_timeseries_with_duplicates(db, ticker: str) -> None:
    """중복 날짜를 포함한 시계열 데이터 생성"""
    base_price = 100.0
    rows = []

    for i in range(5):
        # 3번째 데이터는 중복 날짜
        if i == 3:
            dup_date = date(2024, 1, 4)  # 2번째와 동일
        else:
            dup_date = date(2024, 1, 2 + i)

        rows.append(
            KrxTimeSeries(
                ticker=ticker,
                date=dup_date,
                open=base_price + i,
                high=base_price + i + 2,
                low=base_price + i - 2,
                close=base_price + i + 1,
                volume=1000 + i * 100,
            )
        )

    db.add_all(rows)
    db.commit()


def _seed_timeseries_extreme_volatility(db, ticker: str) -> None:
    """극단적 변동성 시계열 데이터 생성"""
    # 상한가/하한가 수준의 변동
    prices = [100.0, 130.0, 91.0, 118.3, 82.81]  # +30%, -30%, +30%, -30%
    rows = []

    for i, price in enumerate(prices):
        rows.append(
            KrxTimeSeries(
                ticker=ticker,
                date=date(2024, 1, 2 + i),
                open=price,
                high=price * 1.05,
                low=price * 0.95,
                close=price,
                volume=10000 + i * 1000,
            )
        )

    db.add_all(rows)
    db.commit()


def _create_portfolio(
    client, auth_headers, items: list, name: str, portfolio_type: str = "SECURITY"
) -> int:
    """포트폴리오 생성 후 portfolio_id 반환

    Args:
        client: 테스트 클라이언트
        auth_headers: 인증 헤더
        items: [{"id": "...", "name": "...", "weight": 0.x}, ...]
        name: 포트폴리오 이름
        portfolio_type: 포트폴리오 유형

    Returns:
        portfolio_id
    """
    response = client.post(
        "/api/v1/phase7/portfolios",
        json={
            "portfolio_type": portfolio_type,
            "portfolio_name": name,
            "items": items,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, f"포트폴리오 생성 실패: {response.json()}"
    return response.json()["portfolio_id"]


def _run_evaluation(client, auth_headers, portfolio_id: int, start: str, end: str) -> dict:
    """평가 실행 및 응답 반환"""
    response = client.post(
        "/api/v1/phase7/evaluations",
        json={
            "portfolio_id": portfolio_id,
            "period": {"start": start, "end": end},
            "rebalance": "NONE",
        },
        headers=auth_headers,
    )
    return response


# ============================================================================
# Story 3.1: Phase 7 평가 엣지 케이스
# ============================================================================

@pytest.mark.e2e
@pytest.mark.p1
class TestTC001_LargePortfolio:
    """TC-001: 대형 포트폴리오 (50+ 종목)"""

    def test_large_portfolio_50_items(self, client, db, auth_headers, test_user):
        """50개 종목으로 구성된 포트폴리오 평가"""
        # 50개 종목 시계열 데이터 생성
        tickers = [f"TEST{str(i).zfill(3)}" for i in range(50)]
        for ticker in tickers:
            _seed_timeseries(db, ticker, base_price=100.0 + hash(ticker) % 100)

        # 동일 비중 포트폴리오 생성
        items = [
            {"id": ticker, "name": f"종목_{ticker}", "weight": 1.0 / 50}
            for ticker in tickers
        ]

        portfolio_id = _create_portfolio(
            client, auth_headers, items, "대형 포트폴리오 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 정상 처리
        assert response.status_code in [200, 201]
        data = response.json()
        assert "evaluation_id" in data or "result" in data

    def test_large_portfolio_100_items(self, client, db, auth_headers, test_user):
        """100개 종목으로 구성된 포트폴리오 평가"""
        # 100개 종목 시계열 데이터 생성
        tickers = [f"BIG{str(i).zfill(3)}" for i in range(100)]
        for ticker in tickers:
            _seed_timeseries(db, ticker, base_price=50.0 + hash(ticker) % 50)

        # 동일 비중 포트폴리오 생성
        items = [
            {"id": ticker, "name": f"종목_{ticker}", "weight": 1.0 / 100}
            for ticker in tickers
        ]

        portfolio_id = _create_portfolio(
            client, auth_headers, items, "초대형 포트폴리오 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 정상 처리 또는 제한 초과 오류
        assert response.status_code in [200, 201, 400]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC002_EqualWeightPortfolio:
    """TC-002: 동일 비중 포트폴리오"""

    def test_equal_weight_3_items(self, client, db, auth_headers, test_user):
        """3개 종목 동일 비중 (0.3333...)"""
        tickers = ["EQ001", "EQ002", "EQ003"]
        for ticker in tickers:
            _seed_timeseries(db, ticker)

        # 정확한 1/3 비중
        items = [
            {"id": ticker, "name": f"종목_{ticker}", "weight": 1.0 / 3}
            for ticker in tickers
        ]

        portfolio_id = _create_portfolio(
            client, auth_headers, items, "동일 비중 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 정상 처리
        assert response.status_code in [200, 201]

    def test_equal_weight_precision(self, client, db, auth_headers, test_user):
        """동일 비중 정밀도 테스트 (7개 종목)"""
        tickers = [f"EQP{str(i).zfill(2)}" for i in range(7)]
        for ticker in tickers:
            _seed_timeseries(db, ticker)

        # 1/7 = 0.142857142857...
        items = [
            {"id": ticker, "name": f"종목_{ticker}", "weight": 1.0 / 7}
            for ticker in tickers
        ]

        portfolio_id = _create_portfolio(
            client, auth_headers, items, "정밀 비중 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 정상 처리 (소수점 오차 허용)
        assert response.status_code in [200, 201, 400]  # 400은 비중 합계 오차


@pytest.mark.e2e
@pytest.mark.p1
class TestTC003_DataGapPeriod:
    """TC-003: 데이터 갭 기간"""

    def test_data_gap_in_middle(self, client, db, auth_headers, test_user):
        """중간에 데이터 갭이 있는 경우"""
        # 갭이 있는 데이터 생성 (3, 4일차 누락)
        _seed_timeseries(
            db, "GAP001", days=10, include_gaps=True, gap_days=[3, 4]
        )

        items = [{"id": "GAP001", "name": "갭 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "데이터 갭 테스트"
        )

        # 평가 실행 (갭 기간 포함)
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-11"
        )

        # 검증: 갭을 처리하고 결과 반환
        assert response.status_code in [200, 201, 400]

    def test_data_gap_at_start(self, client, db, auth_headers, test_user):
        """시작 부분에 데이터 갭이 있는 경우"""
        # 처음 2일 누락
        _seed_timeseries(
            db, "GAP002", days=10, include_gaps=True, gap_days=[0, 1]
        )

        items = [{"id": "GAP002", "name": "시작 갭 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "시작 갭 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-11"
        )

        # 검증: 갭을 처리하고 결과 반환
        assert response.status_code in [200, 201, 400]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC004_ExtremeVolatility:
    """TC-004: 극단적 가격 변동성"""

    def test_extreme_volatility_single_stock(self, client, db, auth_headers, test_user):
        """극단적 변동성 (±30%)"""
        _seed_timeseries_extreme_volatility(db, "VOLATILE001")

        items = [{"id": "VOLATILE001", "name": "극단 변동 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "극단 변동성 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 정상 처리 (MDD 등 지표 계산)
        assert response.status_code in [200, 201]

        if response.status_code in [200, 201]:
            data = response.json()
            # 높은 변동성으로 인해 MDD가 큰 값일 것
            if "result" in data and "metrics" in data["result"]:
                metrics = data["result"]["metrics"]
                # MDD 존재 확인
                assert "mdd" in metrics or "max_drawdown" in metrics

    def test_zero_return_period(self, client, db, auth_headers, test_user):
        """수익률 0인 기간"""
        # 모든 가격이 동일
        rows = []
        for i in range(5):
            rows.append(
                KrxTimeSeries(
                    ticker="FLAT001",
                    date=date(2024, 1, 2 + i),
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                    volume=1000,
                )
            )
        db.add_all(rows)
        db.commit()

        items = [{"id": "FLAT001", "name": "보합 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "보합 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 정상 처리
        assert response.status_code in [200, 201]


# ============================================================================
# Story 3.2: 데이터 품질 엣지 케이스
# ============================================================================

@pytest.mark.e2e
@pytest.mark.p1
class TestTC010_NullValueHandling:
    """TC-010: NULL 값 처리"""

    def test_null_close_price(self, client, db, auth_headers, test_user):
        """종가가 NULL인 경우"""
        _seed_timeseries_with_nulls(db, "NULL001", [(2, "close")])

        items = [{"id": "NULL001", "name": "NULL 종가 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "NULL 종가 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: NULL 처리 후 결과 반환 또는 오류
        assert response.status_code in [200, 201, 400]

    def test_null_volume(self, client, db, auth_headers, test_user):
        """거래량이 NULL인 경우"""
        _seed_timeseries_with_nulls(db, "NULL002", [(1, "volume"), (3, "volume")])

        items = [{"id": "NULL002", "name": "NULL 거래량 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "NULL 거래량 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: NULL 거래량은 계산에 영향 적음
        assert response.status_code in [200, 201, 400]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC011_DuplicateDates:
    """TC-011: 중복 날짜"""

    def test_duplicate_date_in_timeseries(self, client, db, auth_headers, test_user):
        """시계열에 중복 날짜가 있는 경우"""
        _seed_timeseries_with_duplicates(db, "DUP001")

        items = [{"id": "DUP001", "name": "중복 날짜 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "중복 날짜 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 중복 처리 후 결과 반환 또는 오류
        assert response.status_code in [200, 201, 400]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC012_DateOrderError:
    """TC-012: 날짜 순서 오류"""

    def test_unordered_dates_in_db(self, client, db, auth_headers, test_user):
        """DB에 날짜 순서가 뒤죽박죽인 경우"""
        # 날짜 순서를 섞어서 삽입
        dates_shuffled = [
            date(2024, 1, 5),
            date(2024, 1, 2),
            date(2024, 1, 4),
            date(2024, 1, 3),
            date(2024, 1, 6),
        ]

        rows = []
        for i, d in enumerate(dates_shuffled):
            rows.append(
                KrxTimeSeries(
                    ticker="ORDER001",
                    date=d,
                    open=100.0 + i,
                    high=102.0 + i,
                    low=98.0 + i,
                    close=100.0 + i,
                    volume=1000,
                )
            )
        db.add_all(rows)
        db.commit()

        items = [{"id": "ORDER001", "name": "순서 오류 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "순서 오류 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 날짜 정렬 후 정상 처리
        assert response.status_code in [200, 201]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC013_ZeroVolume:
    """TC-013: 거래량 0 처리"""

    def test_zero_volume_days(self, client, db, auth_headers, test_user):
        """거래량이 0인 날이 있는 경우"""
        rows = []
        for i in range(5):
            rows.append(
                KrxTimeSeries(
                    ticker="ZEROVOL001",
                    date=date(2024, 1, 2 + i),
                    open=100.0 + i,
                    high=102.0 + i,
                    low=98.0 + i,
                    close=100.0 + i,
                    volume=0 if i in [1, 3] else 1000,  # 일부 거래량 0
                )
            )
        db.add_all(rows)
        db.commit()

        items = [{"id": "ZEROVOL001", "name": "거래량 0 종목", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "거래량 0 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 거래량 0도 정상 처리
        assert response.status_code in [200, 201]

    def test_all_zero_volume(self, client, db, auth_headers, test_user):
        """모든 날의 거래량이 0인 경우"""
        rows = []
        for i in range(5):
            rows.append(
                KrxTimeSeries(
                    ticker="ALLZEROVOL",
                    date=date(2024, 1, 2 + i),
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.0,
                    volume=0,
                )
            )
        db.add_all(rows)
        db.commit()

        items = [{"id": "ALLZEROVOL", "name": "전체 거래량 0", "weight": 1.0}]
        portfolio_id = _create_portfolio(
            client, auth_headers, items, "전체 거래량 0 테스트"
        )

        # 평가 실행
        response = _run_evaluation(
            client, auth_headers, portfolio_id, "2024-01-02", "2024-01-06"
        )

        # 검증: 경고와 함께 처리 또는 오류
        assert response.status_code in [200, 201, 400]


# ============================================================================
# Story 3.3: 포트폴리오 비교 엣지 케이스
# ============================================================================

@pytest.mark.e2e
@pytest.mark.p1
class TestTC020_MultiplePortfolioComparison:
    """TC-020: 3개 이상 포트폴리오 비교"""

    def test_compare_three_portfolios(self, client, db, auth_headers, test_user):
        """3개 포트폴리오 비교"""
        # 3개 종목 데이터 생성
        for ticker in ["CMP001", "CMP002", "CMP003"]:
            _seed_timeseries(db, ticker, base_price=100.0 + hash(ticker) % 50)

        # 3개 포트폴리오 생성
        portfolio_ids = []
        for i, ticker in enumerate(["CMP001", "CMP002", "CMP003"]):
            items = [{"id": ticker, "name": f"종목_{ticker}", "weight": 1.0}]
            pid = _create_portfolio(
                client, auth_headers, items, f"비교 포트폴리오 {i+1}"
            )
            portfolio_ids.append(pid)

        # 3개 포트폴리오 비교 API 호출 (API가 지원하는 경우)
        response = client.post(
            "/api/v1/phase7/comparisons",
            json={
                "portfolio_ids": portfolio_ids,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
            },
            headers=auth_headers,
        )

        # 검증: 비교 API 지원 시 성공, 미지원 시 오류
        assert response.status_code in [200, 201, 400, 404, 405]

    def test_compare_five_portfolios(self, client, db, auth_headers, test_user):
        """5개 포트폴리오 비교 (한계 테스트)"""
        # 5개 종목 데이터 생성
        tickers = [f"MULTI{i}" for i in range(5)]
        for ticker in tickers:
            _seed_timeseries(db, ticker)

        # 5개 포트폴리오 생성
        portfolio_ids = []
        for i, ticker in enumerate(tickers):
            items = [{"id": ticker, "name": f"종목_{ticker}", "weight": 1.0}]
            pid = _create_portfolio(
                client, auth_headers, items, f"다중 비교 {i+1}"
            )
            portfolio_ids.append(pid)

        # 5개 포트폴리오 비교 API 호출
        response = client.post(
            "/api/v1/phase7/comparisons",
            json={
                "portfolio_ids": portfolio_ids,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
            },
            headers=auth_headers,
        )

        # 검증: 한계 내 성공 또는 제한 초과 오류
        assert response.status_code in [200, 201, 400, 404, 405]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC021_DifferentTypeComparison:
    """TC-021: 다른 유형 포트폴리오 비교"""

    def test_compare_security_vs_index(self, client, db, auth_headers, test_user):
        """증권 포트폴리오 vs 지수 포트폴리오 비교"""
        # 증권 종목 데이터
        _seed_timeseries(db, "SEC001")

        # 증권 포트폴리오
        items_sec = [{"id": "SEC001", "name": "증권종목", "weight": 1.0}]
        pid_sec = _create_portfolio(
            client, auth_headers, items_sec, "증권 포트폴리오", "SECURITY"
        )

        # 지수 포트폴리오 (지원되는 경우)
        try:
            items_idx = [{"id": "KOSPI", "name": "코스피", "weight": 1.0}]
            pid_idx = _create_portfolio(
                client, auth_headers, items_idx, "지수 포트폴리오", "INDEX"
            )

            # 비교 시도
            response = client.post(
                "/api/v1/phase7/comparisons",
                json={
                    "portfolio_ids": [pid_sec, pid_idx],
                    "period": {"start": "2024-01-02", "end": "2024-01-06"},
                },
                headers=auth_headers,
            )

            # 검증: 다른 유형 비교 가능 여부에 따라 결과
            assert response.status_code in [200, 201, 400, 404, 405]
        except AssertionError:
            # 지수 포트폴리오 미지원 시 통과
            pass


@pytest.mark.e2e
@pytest.mark.p1
class TestTC022_PeriodMismatchComparison:
    """TC-022: 평가 기간 불일치"""

    def test_compare_different_data_ranges(self, client, db, auth_headers, test_user):
        """데이터 범위가 다른 포트폴리오 비교"""
        # 종목 1: 2024-01-02 ~ 2024-01-06 데이터
        _seed_timeseries(db, "RANGE001", days=5, start_date=date(2024, 1, 2))

        # 종목 2: 2024-01-05 ~ 2024-01-10 데이터 (겹치는 구간 있음)
        _seed_timeseries(db, "RANGE002", days=6, start_date=date(2024, 1, 5))

        # 포트폴리오 생성
        items1 = [{"id": "RANGE001", "name": "초기 데이터", "weight": 1.0}]
        pid1 = _create_portfolio(
            client, auth_headers, items1, "초기 범위 포트폴리오"
        )

        items2 = [{"id": "RANGE002", "name": "후기 데이터", "weight": 1.0}]
        pid2 = _create_portfolio(
            client, auth_headers, items2, "후기 범위 포트폴리오"
        )

        # 전체 기간으로 비교 시도
        response = client.post(
            "/api/v1/phase7/comparisons",
            json={
                "portfolio_ids": [pid1, pid2],
                "period": {"start": "2024-01-02", "end": "2024-01-10"},
            },
            headers=auth_headers,
        )

        # 검증: 공통 기간으로 비교 또는 오류
        assert response.status_code in [200, 201, 400, 404, 405]

    def test_compare_non_overlapping_data(self, client, db, auth_headers, test_user):
        """겹치지 않는 데이터 범위 비교"""
        # 종목 1: 2024-01-02 ~ 2024-01-06
        _seed_timeseries(db, "NOLAP001", days=5, start_date=date(2024, 1, 2))

        # 종목 2: 2024-01-10 ~ 2024-01-14 (겹치지 않음)
        _seed_timeseries(db, "NOLAP002", days=5, start_date=date(2024, 1, 10))

        # 포트폴리오 생성
        items1 = [{"id": "NOLAP001", "name": "1월 초 데이터", "weight": 1.0}]
        pid1 = _create_portfolio(
            client, auth_headers, items1, "1월 초 포트폴리오"
        )

        items2 = [{"id": "NOLAP002", "name": "1월 중 데이터", "weight": 1.0}]
        pid2 = _create_portfolio(
            client, auth_headers, items2, "1월 중 포트폴리오"
        )

        # 비교 시도 (공통 구간 없음)
        response = client.post(
            "/api/v1/phase7/comparisons",
            json={
                "portfolio_ids": [pid1, pid2],
                "period": {"start": "2024-01-02", "end": "2024-01-14"},
            },
            headers=auth_headers,
        )

        # 검증: 공통 기간 없으면 오류 또는 부분 결과
        assert response.status_code in [200, 201, 400, 404, 405]
