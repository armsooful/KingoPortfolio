"""
포트폴리오 백테스팅 서비스

과거 데이터를 기반으로 포트폴리오의 성과를 시뮬레이션하고 검증합니다.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import math

from app.models.alpha_vantage import AlphaVantageTimeSeries
from app.models.securities import Stock, ETF
from app.models.real_data import StockPriceDaily


class BacktestingEngine:
    """백테스팅 엔진"""

    def __init__(self, db: Session):
        self.db = db
        self._backtest_start_date: Optional[datetime] = None
        self._price_cache: Dict[str, Dict[date, float]] = {}  # ticker -> {date -> price}

    def run_backtest(
        self,
        portfolio: Dict,
        start_date: datetime,
        end_date: datetime,
        initial_investment: int,
        rebalance_frequency: str = "quarterly"  # monthly, quarterly, yearly, none
    ) -> Dict:
        """
        포트폴리오 백테스트 실행

        Args:
            portfolio: 포트폴리오 구성 (allocation, securities)
            start_date: 시작 날짜
            end_date: 종료 날짜
            initial_investment: 초기 투자 금액
            rebalance_frequency: 리밸런싱 주기

        Returns:
            백테스트 결과 (수익률, 변동성, 샤프 비율, 일별 가치 등)
        """
        # 백테스트 기간 검증
        if end_date <= start_date:
            raise ValueError("종료 날짜는 시작 날짜보다 커야 합니다")

        days = (end_date - start_date).days
        if days < 30:
            raise ValueError("백테스트 기간은 최소 30일 이상이어야 합니다")

        # 백테스트 시작일 저장 (채권/예금 이자 계산용)
        self._backtest_start_date = start_date

        # 포트폴리오 초기 구성
        current_portfolio = self._initialize_portfolio(
            portfolio, initial_investment
        )

        # 가격 데이터 일괄 프리로드 (성능 최적화)
        self._preload_prices(current_portfolio, start_date, end_date)

        # 일별 시뮬레이션
        daily_values = []
        current_date = start_date
        last_rebalance_date = start_date

        while current_date <= end_date:
            # 일별 포트폴리오 가치 계산
            daily_value = self._calculate_portfolio_value(
                current_portfolio, current_date
            )

            daily_values.append({
                "date": current_date.isoformat(),
                "value": daily_value,
                "return": ((daily_value - initial_investment) / initial_investment) * 100
            })

            # 리밸런싱 체크
            if self._should_rebalance(current_date, last_rebalance_date, rebalance_frequency):
                current_portfolio = self._rebalance_portfolio(
                    portfolio, daily_value, current_date
                )
                last_rebalance_date = current_date

            current_date += timedelta(days=1)

        # 성과 지표 계산
        metrics = self._calculate_metrics(
            daily_values, initial_investment, days
        )

        # B-1: 손실/회복 지표를 top-level로, 수익률 지표는 historical_observation으로
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_investment": initial_investment,
            "final_value": daily_values[-1]["value"],
            # 손실/회복 지표 (top-level) - Foresto 핵심 KPI
            "risk_metrics": {
                "max_drawdown": metrics["max_drawdown"],
                "max_recovery_days": metrics.get("max_recovery_days", None),
                "worst_1m_return": metrics.get("worst_1m_return", None),
                "worst_3m_return": metrics.get("worst_3m_return", None),
                "volatility": metrics["volatility"],
            },
            # 과거 관측치 (historical_observation) - 수익률 중심 지표
            "historical_observation": {
                "total_return": metrics["total_return"],
                "cagr": metrics["annualized_return"],
                "sharpe_ratio": metrics["sharpe_ratio"],
            },
            # 레거시 호환성 (프론트엔드 기존 코드 지원)
            "total_return": metrics["total_return"],
            "annualized_return": metrics["annualized_return"],
            "volatility": metrics["volatility"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "max_drawdown": metrics["max_drawdown"],
            "daily_values": daily_values,
            "rebalance_frequency": rebalance_frequency,
            "number_of_rebalances": metrics["rebalances"]
        }

    def _initialize_portfolio(self, portfolio: Dict, amount: int) -> Dict:
        """포트폴리오 초기 구성"""
        # 중첩 구조 처리 (generate 응답 전체가 넘어올 경우)
        if "portfolio" in portfolio and isinstance(portfolio["portfolio"], dict):
            portfolio = portfolio["portfolio"]

        holdings = {}

        # 주식
        for stock in portfolio.get("stocks", []):
            holdings[f"stock_{stock['ticker']}"] = {
                "type": "stock",
                "ticker": stock["ticker"],
                "shares": stock["shares"],
                "initial_price": stock["current_price"]
            }

        # ETF
        for etf in portfolio.get("etfs", []):
            holdings[f"etf_{etf['ticker']}"] = {
                "type": "etf",
                "ticker": etf["ticker"],
                "shares": etf["shares"],
                "initial_price": etf["current_price"]
            }

        # 채권 (단순 이자 계산)
        for bond in portfolio.get("bonds", []):
            holdings[f"bond_{bond['id']}"] = {
                "type": "bond",
                "id": bond["id"],
                "amount": bond["invested_amount"],
                "annual_rate": bond["interest_rate"]
            }

        # 예금
        for deposit in portfolio.get("deposits", []):
            holdings[f"deposit_{deposit['id']}"] = {
                "type": "deposit",
                "id": deposit["id"],
                "amount": deposit["invested_amount"],
                "annual_rate": deposit["interest_rate"]
            }

        return holdings

    def _calculate_portfolio_value(
        self, portfolio: Dict, date: datetime
    ) -> float:
        """특정 날짜의 포트폴리오 가치 계산"""
        total_value = 0

        for key, holding in portfolio.items():
            if holding["type"] in ["stock", "etf"]:
                # 주식/ETF: 현재가 × 주식 수
                # 실제로는 과거 가격 데이터 필요 (여기서는 시뮬레이션)
                price = self._get_historical_price(
                    holding["ticker"],
                    holding["type"],
                    date,
                    holding["initial_price"]
                )
                total_value += price * holding["shares"]

            elif holding["type"] in ["bond", "deposit"]:
                # 채권/예금: 원금 + 경과 이자 (백테스트 시작일 기준)
                days_held = (date - self._backtest_start_date).days
                if days_held < 0:
                    days_held = 0

                daily_rate = holding["annual_rate"] / 365 / 100
                interest = holding["amount"] * daily_rate * days_held
                total_value += holding["amount"] + interest

        return total_value

    def _preload_prices(self, portfolio: Dict, start_date: datetime, end_date: datetime):
        """백테스트 기간의 모든 가격 데이터를 일괄 로드하여 캐시"""
        self._price_cache = {}
        start_d = start_date.date() if isinstance(start_date, datetime) else start_date
        end_d = end_date.date() if isinstance(end_date, datetime) else end_date

        tickers = []
        for key, holding in portfolio.items():
            if holding["type"] in ["stock", "etf"]:
                tickers.append(holding["ticker"])

        if not tickers:
            return

        # KRX 종목 (6자리 숫자) 일괄 로드
        krx_tickers = [t for t in tickers if t.isdigit() and len(t) == 6]
        if krx_tickers:
            rows = self.db.query(
                StockPriceDaily.ticker,
                StockPriceDaily.trade_date,
                StockPriceDaily.close_price
            ).filter(
                and_(
                    StockPriceDaily.ticker.in_(krx_tickers),
                    StockPriceDaily.trade_date >= start_d,
                    StockPriceDaily.trade_date <= end_d
                )
            ).all()

            for ticker, trade_date, close_price in rows:
                if ticker not in self._price_cache:
                    self._price_cache[ticker] = {}
                self._price_cache[ticker][trade_date] = float(close_price)

        # 미국 종목 일괄 로드
        us_tickers = [t for t in tickers if not (t.isdigit() and len(t) == 6)]
        if us_tickers:
            rows = self.db.query(
                AlphaVantageTimeSeries.symbol,
                AlphaVantageTimeSeries.date,
                AlphaVantageTimeSeries.adjusted_close,
                AlphaVantageTimeSeries.close
            ).filter(
                and_(
                    AlphaVantageTimeSeries.symbol.in_(us_tickers),
                    AlphaVantageTimeSeries.date >= start_d,
                    AlphaVantageTimeSeries.date <= end_d
                )
            ).all()

            for symbol, d, adj_close, close in rows:
                if symbol not in self._price_cache:
                    self._price_cache[symbol] = {}
                self._price_cache[symbol][d] = adj_close or close

    def _get_historical_price(
        self, ticker: str, security_type: str, target_date: datetime, initial_price: float
    ) -> float:
        """
        과거 가격 데이터 조회 (캐시 우선)

        1순위: 프리로드된 캐시
        2순위: 캐시 내 가장 가까운 과거 날짜
        3순위: 현재가 기반 시뮬레이션
        """
        query_date = target_date.date() if isinstance(target_date, datetime) else target_date

        # 1. 캐시에서 정확한 날짜 조회
        if ticker in self._price_cache:
            cache = self._price_cache[ticker]
            if query_date in cache:
                return cache[query_date]

            # 가장 가까운 과거 날짜 찾기 (주말/공휴일 대비)
            past_dates = [d for d in cache if d <= query_date]
            if past_dates:
                nearest = max(past_dates)
                return cache[nearest]

        # 2. Fallback: 시뮬레이션 (캐시에 데이터 없는 경우)
        days_from_now = (datetime.now() - target_date).days
        if days_from_now <= 0:
            return initial_price

        import random
        random.seed(f"{ticker}_{target_date.isoformat()}")
        daily_change = random.uniform(-0.005, 0.005)
        cumulative_change = 1 + (daily_change * days_from_now * 0.1)

        return initial_price * cumulative_change

    def _should_rebalance(
        self, current_date: datetime, last_rebalance: datetime, frequency: str
    ) -> bool:
        """리밸런싱 필요 여부 판단"""
        if frequency == "none":
            return False

        days_since_rebalance = (current_date - last_rebalance).days

        if frequency == "monthly" and days_since_rebalance >= 30:
            return True
        elif frequency == "quarterly" and days_since_rebalance >= 90:
            return True
        elif frequency == "yearly" and days_since_rebalance >= 365:
            return True

        return False

    def _rebalance_portfolio(
        self, target_portfolio: Dict, current_value: float, date: datetime
    ) -> Dict:
        """포트폴리오 리밸런싱"""
        # 목표 비율대로 재구성
        return self._initialize_portfolio(target_portfolio, int(current_value))

    def _calculate_metrics(
        self, daily_values: List[Dict], initial_investment: int, days: int
    ) -> Dict:
        """성과 지표 계산"""
        final_value = daily_values[-1]["value"]

        # 총 수익률
        total_return = ((final_value - initial_investment) / initial_investment) * 100

        # 연환산 수익률
        years = days / 365.25
        annualized_return = ((final_value / initial_investment) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 일별 수익률 계산
        daily_returns = []
        for i in range(1, len(daily_values)):
            prev_value = daily_values[i - 1]["value"]
            curr_value = daily_values[i]["value"]
            if prev_value == 0:
                daily_returns.append(0)
                continue
            daily_return = ((curr_value - prev_value) / prev_value) * 100
            daily_returns.append(daily_return)

        # 변동성 (일별 수익률의 표준편차 × √252)
        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            daily_volatility = math.sqrt(variance)
            annualized_volatility = daily_volatility * math.sqrt(252)  # 252 영업일
        else:
            annualized_volatility = 0

        # 샤프 비율 (무위험 수익률 2% 가정)
        risk_free_rate = 2.0
        if annualized_volatility > 0:
            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        else:
            sharpe_ratio = 0

        # 최대 낙폭 (Maximum Drawdown) 및 회복 기간
        max_value = initial_investment
        max_drawdown = 0
        max_drawdown_start = 0
        max_recovery_days = 0
        current_drawdown_start = 0
        in_drawdown = False

        for i, value_data in enumerate(daily_values):
            current_value = value_data["value"]
            if current_value > max_value:
                # 신고가 갱신 - 낙폭에서 회복
                if in_drawdown:
                    recovery_days = i - current_drawdown_start
                    if recovery_days > max_recovery_days:
                        max_recovery_days = recovery_days
                    in_drawdown = False
                max_value = current_value
            else:
                drawdown = ((max_value - current_value) / max_value) * 100
                if drawdown > 0 and not in_drawdown:
                    # 낙폭 시작
                    in_drawdown = True
                    current_drawdown_start = i
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_start = current_drawdown_start

        # 최악의 1개월/3개월 수익률 계산
        worst_1m_return = 0
        worst_3m_return = 0

        if len(daily_values) >= 22:  # 약 1개월 (영업일 기준)
            for i in range(22, len(daily_values)):
                base_value = daily_values[i-22]["value"]
                if base_value == 0:
                    continue
                period_return = ((daily_values[i]["value"] - base_value) / base_value) * 100
                if period_return < worst_1m_return:
                    worst_1m_return = period_return

        if len(daily_values) >= 66:  # 약 3개월 (영업일 기준)
            for i in range(66, len(daily_values)):
                base_value = daily_values[i-66]["value"]
                if base_value == 0:
                    continue
                period_return = ((daily_values[i]["value"] - base_value) / base_value) * 100
                if period_return < worst_3m_return:
                    worst_3m_return = period_return

        return {
            "total_return": round(total_return, 2),
            "annualized_return": round(annualized_return, 2),
            "volatility": round(annualized_volatility, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "max_recovery_days": max_recovery_days if max_recovery_days > 0 else None,
            "worst_1m_return": round(worst_1m_return, 2) if worst_1m_return < 0 else None,
            "worst_3m_return": round(worst_3m_return, 2) if worst_3m_return < 0 else None,
            "rebalances": 0  # TODO: 실제 리밸런싱 횟수 카운트
        }

    def compare_portfolios(
        self,
        portfolios: List[Dict],
        start_date: datetime,
        end_date: datetime,
        initial_investment: int
    ) -> Dict:
        """
        여러 포트폴리오 비교

        Args:
            portfolios: 비교할 포트폴리오 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            initial_investment: 초기 투자 금액

        Returns:
            각 포트폴리오의 백테스트 결과 및 비교 지표
        """
        results = []

        for i, portfolio in enumerate(portfolios):
            backtest_result = self.run_backtest(
                portfolio,
                start_date,
                end_date,
                initial_investment,
                rebalance_frequency="quarterly"
            )
            backtest_result["portfolio_name"] = portfolio.get("name", f"Portfolio {i+1}")
            results.append(backtest_result)

        # 최고 성과 포트폴리오 찾기
        best_return = max(results, key=lambda x: x["total_return"])
        best_sharpe = max(results, key=lambda x: x["sharpe_ratio"])
        lowest_risk = min(results, key=lambda x: x["volatility"])

        return {
            "comparison": results,
            "best_return": best_return["portfolio_name"],
            "best_risk_adjusted": best_sharpe["portfolio_name"],
            "lowest_risk": lowest_risk["portfolio_name"]
        }


def run_simple_backtest(
    investment_type: str,
    investment_amount: int,
    period_years: int = 1,
    db: Session = None
) -> Dict:
    """
    간단한 백테스트 실행 (헬퍼 함수)

    Args:
        investment_type: 투자 성향
        investment_amount: 투자 금액
        period_years: 백테스트 기간 (년)
        db: DB 세션

    Returns:
        백테스트 결과
    """
    from app.services.portfolio_engine import create_default_portfolio

    # 포트폴리오 생성
    portfolio = create_default_portfolio(
        db=db,
        investment_type=investment_type,
        investment_amount=investment_amount
    )

    # 백테스트 기간 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_years * 365)

    # 백테스트 실행
    engine = BacktestingEngine(db)
    result = engine.run_backtest(
        portfolio=portfolio["portfolio"],
        start_date=start_date,
        end_date=end_date,
        initial_investment=investment_amount,
        rebalance_frequency="quarterly"
    )

    return result
