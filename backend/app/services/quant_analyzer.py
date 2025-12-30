# backend/app/services/quant_analyzer.py

"""
퀀트/기술 분석 모듈
- 기술적 지표: 이동평균, 골든크로스, RSI, 볼린저밴드 등
- 리스크 지표: 변동성, 베타, 최대 낙폭, 샤프 비율 등
- 시장 대비 성과: 알파, 트래킹 에러
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import logging
import numpy as np
from decimal import Decimal

from app.models.alpha_vantage import AlphaVantageTimeSeries

logger = logging.getLogger(__name__)


def to_date(dt):
    """datetime 또는 date 객체를 date 객체로 변환"""
    if isinstance(dt, datetime):
        return dt.date()
    return dt


class QuantAnalyzer:
    """퀀트 분석 클래스"""

    @staticmethod
    def get_price_data(db: Session, symbol: str, days: int = 252) -> List[Tuple[datetime, float]]:
        """
        주가 데이터 조회
        - days: 조회 기간 (기본 252일 = 1년)
        - 반환: [(날짜, 종가)] 리스트 (시간순 정렬)
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        time_series = db.query(AlphaVantageTimeSeries).filter(
            AlphaVantageTimeSeries.symbol == symbol.upper(),
            AlphaVantageTimeSeries.date >= cutoff_date
        ).order_by(AlphaVantageTimeSeries.date).all()

        if not time_series:
            return []

        return [(ts.date, float(ts.close)) for ts in time_series]

    @staticmethod
    def calculate_returns(prices: List[Tuple[datetime, float]]) -> List[Tuple[datetime, float]]:
        """
        일간 수익률 계산
        - 반환: [(날짜, 수익률%)] 리스트
        """
        if len(prices) < 2:
            return []

        returns = []
        for i in range(1, len(prices)):
            date = prices[i][0]
            ret = ((prices[i][1] - prices[i-1][1]) / prices[i-1][1]) * 100
            returns.append((date, ret))

        return returns

    # ============================================================
    # 기술적 지표 (Technical Indicators)
    # ============================================================

    @staticmethod
    def calculate_moving_averages(prices: List[Tuple[datetime, float]], periods: List[int] = [20, 50, 200]) -> Dict:
        """
        이동평균선 계산
        - periods: 계산할 기간 리스트 (기본: 20일, 50일, 200일)
        """
        if not prices:
            return {"error": "가격 데이터 없음"}

        result = {
            "current_price": prices[-1][1],
            "moving_averages": {}
        }

        price_values = [p[1] for p in prices]

        for period in periods:
            if len(prices) >= period:
                ma = sum(price_values[-period:]) / period
                result["moving_averages"][f"MA{period}"] = {
                    "value": round(ma, 2),
                    "distance": round(((prices[-1][1] - ma) / ma) * 100, 2)  # 현재가와의 거리(%)
                }

        # 골든크로스/데드크로스 판정 (MA50 vs MA200)
        if "MA50" in result["moving_averages"] and "MA200" in result["moving_averages"]:
            ma50 = result["moving_averages"]["MA50"]["value"]
            ma200 = result["moving_averages"]["MA200"]["value"]

            if len(prices) >= 201:
                # 전일 MA50, MA200 계산
                prev_ma50 = sum(price_values[-51:-1]) / 50
                prev_ma200 = sum(price_values[-201:-1]) / 200

                if ma50 > ma200 and prev_ma50 <= prev_ma200:
                    result["signal"] = "골든크로스 발생 (매수 신호)"
                elif ma50 < ma200 and prev_ma50 >= prev_ma200:
                    result["signal"] = "데드크로스 발생 (매도 신호)"
                elif ma50 > ma200:
                    result["signal"] = "상승 추세 (MA50 > MA200)"
                else:
                    result["signal"] = "하락 추세 (MA50 < MA200)"

        return result

    @staticmethod
    def calculate_rsi(prices: List[Tuple[datetime, float]], period: int = 14) -> Dict:
        """
        RSI (Relative Strength Index) 계산
        - period: 계산 기간 (기본 14일)
        - 0-100 사이 값
        - 70 이상: 과매수, 30 이하: 과매도
        """
        if len(prices) < period + 1:
            return {"error": "데이터 부족"}

        # 가격 변화 계산
        price_changes = []
        for i in range(1, len(prices)):
            change = prices[i][1] - prices[i-1][1]
            price_changes.append(change)

        # 최근 period 동안의 상승/하락 평균
        recent_changes = price_changes[-period:]
        avg_gain = sum([c for c in recent_changes if c > 0]) / period
        avg_loss = abs(sum([c for c in recent_changes if c < 0])) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # RSI 판정
        if rsi >= 70:
            status = "과매수 (매도 검토)"
        elif rsi <= 30:
            status = "과매도 (매수 검토)"
        else:
            status = "중립"

        return {
            "rsi": round(rsi, 2),
            "status": status,
            "period": period
        }

    @staticmethod
    def calculate_bollinger_bands(prices: List[Tuple[datetime, float]], period: int = 20, std_dev: float = 2.0) -> Dict:
        """
        볼린저 밴드 계산
        - period: 이동평균 기간 (기본 20일)
        - std_dev: 표준편차 배수 (기본 2.0)
        """
        if len(prices) < period:
            return {"error": "데이터 부족"}

        price_values = [p[1] for p in prices]
        recent_prices = price_values[-period:]

        # 중간선 (이동평균)
        middle_band = sum(recent_prices) / period

        # 표준편차
        variance = sum([(p - middle_band) ** 2 for p in recent_prices]) / period
        std = variance ** 0.5

        # 상단/하단 밴드
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)

        current_price = prices[-1][1]

        # 밴드 폭 (%)
        bandwidth = ((upper_band - lower_band) / middle_band) * 100

        # %B (현재가의 밴드 내 위치, 0-1 사이)
        percent_b = (current_price - lower_band) / (upper_band - lower_band)

        # 판정
        if current_price > upper_band:
            status = "상단 밴드 돌파 (과매수)"
        elif current_price < lower_band:
            status = "하단 밴드 이탈 (과매도)"
        elif percent_b > 0.8:
            status = "상단 밴드 근접"
        elif percent_b < 0.2:
            status = "하단 밴드 근접"
        else:
            status = "중립 (밴드 내부)"

        return {
            "current_price": round(current_price, 2),
            "upper_band": round(upper_band, 2),
            "middle_band": round(middle_band, 2),
            "lower_band": round(lower_band, 2),
            "bandwidth": round(bandwidth, 2),
            "percent_b": round(percent_b, 2),
            "status": status
        }

    @staticmethod
    def calculate_macd(prices: List[Tuple[datetime, float]], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        MACD (Moving Average Convergence Divergence) 계산
        - fast: 단기 EMA 기간 (기본 12일)
        - slow: 장기 EMA 기간 (기본 26일)
        - signal: 시그널 선 기간 (기본 9일)
        """
        if len(prices) < slow + signal:
            return {"error": "데이터 부족"}

        price_values = [p[1] for p in prices]

        # EMA 계산 함수
        def calculate_ema(values, period):
            multiplier = 2 / (period + 1)
            ema = [sum(values[:period]) / period]  # 첫 EMA는 단순 평균

            for i in range(period, len(values)):
                ema_value = (values[i] - ema[-1]) * multiplier + ema[-1]
                ema.append(ema_value)

            return ema

        # 빠른/느린 EMA
        ema_fast = calculate_ema(price_values, fast)
        ema_slow = calculate_ema(price_values, slow)

        # MACD 라인 (fast EMA - slow EMA)
        macd_line = []
        for i in range(len(ema_slow)):
            idx_fast = i + (slow - fast)
            macd_line.append(ema_fast[idx_fast] - ema_slow[i])

        # 시그널 라인 (MACD의 EMA)
        signal_line = calculate_ema(macd_line, signal)

        # 히스토그램 (MACD - Signal)
        histogram = []
        for i in range(len(signal_line)):
            idx_macd = i + (signal - 1)
            histogram.append(macd_line[idx_macd] - signal_line[i])

        # 현재 값들
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = histogram[-1]

        # 크로스오버 판정
        if len(histogram) >= 2:
            prev_histogram = histogram[-2]
            if current_histogram > 0 and prev_histogram <= 0:
                status = "골든크로스 (매수 신호)"
            elif current_histogram < 0 and prev_histogram >= 0:
                status = "데드크로스 (매도 신호)"
            elif current_histogram > 0:
                status = "상승 추세"
            else:
                status = "하락 추세"
        else:
            status = "중립"

        return {
            "macd": round(current_macd, 2),
            "signal": round(current_signal, 2),
            "histogram": round(current_histogram, 2),
            "status": status
        }

    # ============================================================
    # 리스크 지표 (Risk Metrics)
    # ============================================================

    @staticmethod
    def calculate_volatility(returns: List[Tuple[datetime, float]], annualize: bool = True) -> float:
        """
        변동성 계산
        - 일간 수익률의 표준편차
        - annualize: True면 연율화 (√252)
        """
        if len(returns) < 2:
            return 0.0

        return_values = [r[1] for r in returns]
        mean_return = sum(return_values) / len(return_values)
        variance = sum([(r - mean_return) ** 2 for r in return_values]) / len(return_values)
        volatility = variance ** 0.5

        if annualize:
            volatility *= (252 ** 0.5)  # 연율화

        return round(volatility, 2)

    @staticmethod
    def calculate_max_drawdown(prices: List[Tuple[datetime, float]]) -> Dict:
        """
        최대 낙폭 (MDD - Maximum Drawdown) 계산
        - 고점 대비 최대 하락률
        """
        if len(prices) < 2:
            return {"error": "데이터 부족"}

        price_values = [p[1] for p in prices]

        max_dd = 0
        peak = price_values[0]
        peak_date = prices[0][0]
        trough_date = prices[0][0]

        for i, price in enumerate(price_values):
            if price > peak:
                peak = price
                peak_date = prices[i][0]

            dd = ((price - peak) / peak) * 100
            if dd < max_dd:
                max_dd = dd
                trough_date = prices[i][0]

        return {
            "max_drawdown": round(max_dd, 2),
            "peak_price": round(peak, 2),
            "peak_date": peak_date.strftime("%Y-%m-%d"),
            "trough_date": trough_date.strftime("%Y-%m-%d")
        }

    @staticmethod
    def calculate_beta(
        stock_returns: List[Tuple[datetime, float]],
        market_returns: List[Tuple[datetime, float]]
    ) -> Dict:
        """
        베타 계산 (시장 대비 민감도)
        - Beta = Cov(Stock, Market) / Var(Market)
        - Beta > 1: 시장보다 변동성 큼
        - Beta < 1: 시장보다 변동성 작음
        """
        if len(stock_returns) < 2 or len(market_returns) < 2:
            return {"error": "데이터 부족"}

        # 날짜 매칭
        stock_dict = {to_date(r[0]): r[1] for r in stock_returns}
        market_dict = {to_date(r[0]): r[1] for r in market_returns}

        common_dates = sorted(set(stock_dict.keys()) & set(market_dict.keys()))

        if len(common_dates) < 2:
            return {"error": "공통 날짜 부족"}

        stock_rets = [stock_dict[d] for d in common_dates]
        market_rets = [market_dict[d] for d in common_dates]

        # 평균
        stock_mean = sum(stock_rets) / len(stock_rets)
        market_mean = sum(market_rets) / len(market_rets)

        # 공분산
        covariance = sum([(stock_rets[i] - stock_mean) * (market_rets[i] - market_mean)
                          for i in range(len(common_dates))]) / len(common_dates)

        # 시장 분산
        market_variance = sum([(r - market_mean) ** 2 for r in market_rets]) / len(market_rets)

        if market_variance == 0:
            return {"error": "시장 분산이 0"}

        beta = covariance / market_variance

        # 베타 해석
        if beta > 1.2:
            interpretation = "고변동성 (시장보다 20% 이상 변동)"
        elif beta > 1.0:
            interpretation = "시장보다 다소 높은 변동성"
        elif beta > 0.8:
            interpretation = "시장과 유사한 변동성"
        elif beta > 0:
            interpretation = "시장보다 낮은 변동성"
        else:
            interpretation = "시장과 역상관"

        return {
            "beta": round(beta, 2),
            "interpretation": interpretation
        }

    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[Tuple[datetime, float]],
        risk_free_rate: float = 4.5
    ) -> Dict:
        """
        샤프 비율 계산
        - Sharpe Ratio = (평균 수익률 - 무위험 수익률) / 변동성
        - risk_free_rate: 무위험 수익률 (기본 4.5%, 2024년 미국 국채 10년물 기준)
        """
        if len(returns) < 2:
            return {"error": "데이터 부족"}

        return_values = [r[1] for r in returns]

        # 평균 일간 수익률
        avg_daily_return = sum(return_values) / len(return_values)

        # 연율화 평균 수익률
        avg_annual_return = avg_daily_return * 252

        # 변동성 (연율화)
        mean = avg_daily_return
        variance = sum([(r - mean) ** 2 for r in return_values]) / len(return_values)
        daily_volatility = variance ** 0.5
        annual_volatility = daily_volatility * (252 ** 0.5)

        if annual_volatility == 0:
            return {"error": "변동성이 0"}

        # 샤프 비율
        sharpe = (avg_annual_return - risk_free_rate) / annual_volatility

        # 샤프 비율 해석
        if sharpe > 2:
            interpretation = "우수한 위험 대비 수익"
        elif sharpe > 1:
            interpretation = "양호한 위험 대비 수익"
        elif sharpe > 0:
            interpretation = "보통"
        else:
            interpretation = "무위험 자산보다 낮은 수익"

        return {
            "sharpe_ratio": round(sharpe, 2),
            "avg_annual_return": round(avg_annual_return, 2),
            "annual_volatility": round(annual_volatility, 2),
            "risk_free_rate": risk_free_rate,
            "interpretation": interpretation
        }

    @staticmethod
    def calculate_alpha(
        stock_returns: List[Tuple[datetime, float]],
        market_returns: List[Tuple[datetime, float]],
        risk_free_rate: float = 4.5
    ) -> Dict:
        """
        알파 계산 (시장 대비 초과 수익률)
        - Alpha = 실제 수익률 - (무위험 수익률 + Beta × (시장 수익률 - 무위험 수익률))
        """
        # 베타 계산
        beta_result = QuantAnalyzer.calculate_beta(stock_returns, market_returns)
        if "error" in beta_result:
            return beta_result

        beta = beta_result["beta"]

        # 날짜 매칭
        stock_dict = {to_date(r[0]): r[1] for r in stock_returns}
        market_dict = {to_date(r[0]): r[1] for r in market_returns}
        common_dates = sorted(set(stock_dict.keys()) & set(market_dict.keys()))

        stock_rets = [stock_dict[d] for d in common_dates]
        market_rets = [market_dict[d] for d in common_dates]

        # 평균 일간 수익률
        avg_stock_return = sum(stock_rets) / len(stock_rets)
        avg_market_return = sum(market_rets) / len(market_rets)

        # 연율화
        annual_stock_return = avg_stock_return * 252
        annual_market_return = avg_market_return * 252

        # 알파 = 실제 수익률 - 기대 수익률
        # 기대 수익률 = Rf + Beta × (Rm - Rf)
        expected_return = risk_free_rate + beta * (annual_market_return - risk_free_rate)
        alpha = annual_stock_return - expected_return

        # 알파 해석
        if alpha > 5:
            interpretation = "시장 대비 우수한 초과 수익"
        elif alpha > 0:
            interpretation = "시장 대비 양의 초과 수익"
        elif alpha > -5:
            interpretation = "시장과 유사한 성과"
        else:
            interpretation = "시장 대비 저조한 성과"

        return {
            "alpha": round(alpha, 2),
            "beta": beta,
            "actual_return": round(annual_stock_return, 2),
            "expected_return": round(expected_return, 2),
            "market_return": round(annual_market_return, 2),
            "interpretation": interpretation
        }

    @staticmethod
    def calculate_tracking_error(
        stock_returns: List[Tuple[datetime, float]],
        market_returns: List[Tuple[datetime, float]]
    ) -> Dict:
        """
        트래킹 에러 계산
        - 포트폴리오 수익률과 벤치마크 수익률 차이의 표준편차
        - 낮을수록 벤치마크를 잘 추종
        """
        # 날짜 매칭
        stock_dict = {to_date(r[0]): r[1] for r in stock_returns}
        market_dict = {to_date(r[0]): r[1] for r in market_returns}
        common_dates = sorted(set(stock_dict.keys()) & set(market_dict.keys()))

        if len(common_dates) < 2:
            return {"error": "공통 날짜 부족"}

        # 수익률 차이
        differences = [stock_dict[d] - market_dict[d] for d in common_dates]

        # 평균 차이
        mean_diff = sum(differences) / len(differences)

        # 표준편차
        variance = sum([(d - mean_diff) ** 2 for d in differences]) / len(differences)
        tracking_error = (variance ** 0.5) * (252 ** 0.5)  # 연율화

        # 해석
        if tracking_error < 2:
            interpretation = "매우 낮음 (인덱스 추종)"
        elif tracking_error < 5:
            interpretation = "낮음"
        elif tracking_error < 10:
            interpretation = "보통"
        else:
            interpretation = "높음 (액티브 전략)"

        return {
            "tracking_error": round(tracking_error, 2),
            "avg_difference": round(mean_diff * 252, 2),  # 연율화
            "interpretation": interpretation
        }

    # ============================================================
    # 종합 분석
    # ============================================================

    @staticmethod
    def comprehensive_quant_analysis(
        db: Session,
        symbol: str,
        market_symbol: str = "SPY",
        days: int = 252
    ) -> Dict:
        """
        종합 퀀트 분석
        - 기술적 지표 + 리스크 지표 통합
        """
        # 주가 데이터 조회
        stock_prices = QuantAnalyzer.get_price_data(db, symbol, days)
        market_prices = QuantAnalyzer.get_price_data(db, market_symbol, days)

        if not stock_prices:
            return {"error": f"{symbol} 데이터 없음"}

        # 수익률 계산
        stock_returns = QuantAnalyzer.calculate_returns(stock_prices)
        market_returns = QuantAnalyzer.calculate_returns(market_prices) if market_prices else []

        result = {
            "symbol": symbol.upper(),
            "market_benchmark": market_symbol.upper(),
            "period_days": days,
            "data_points": len(stock_prices),
            "start_date": stock_prices[0][0].strftime("%Y-%m-%d"),
            "end_date": stock_prices[-1][0].strftime("%Y-%m-%d"),
        }

        # 기술적 지표
        result["technical_indicators"] = {
            "moving_averages": QuantAnalyzer.calculate_moving_averages(stock_prices),
            "rsi": QuantAnalyzer.calculate_rsi(stock_prices),
            "bollinger_bands": QuantAnalyzer.calculate_bollinger_bands(stock_prices),
            "macd": QuantAnalyzer.calculate_macd(stock_prices)
        }

        # 리스크 지표
        result["risk_metrics"] = {
            "volatility": QuantAnalyzer.calculate_volatility(stock_returns),
            "max_drawdown": QuantAnalyzer.calculate_max_drawdown(stock_prices),
            "sharpe_ratio": QuantAnalyzer.calculate_sharpe_ratio(stock_returns)
        }

        # 시장 대비 지표
        if market_returns:
            result["market_comparison"] = {
                "beta": QuantAnalyzer.calculate_beta(stock_returns, market_returns),
                "alpha": QuantAnalyzer.calculate_alpha(stock_returns, market_returns),
                "tracking_error": QuantAnalyzer.calculate_tracking_error(stock_returns, market_returns)
            }

        return result
