# backend/app/services/financial_analyzer.py

"""
재무 분석 모듈
- 입력: 재무제표, 시가총액, 시계열 데이터
- 출력: 성장률(CAGR), 마진, ROE, 부채비율, FCF 마진, 배당 연속성 등
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import logging
from decimal import Decimal

from app.models.alpha_vantage import AlphaVantageStock, AlphaVantageFinancials, AlphaVantageTimeSeries
from app.models.securities import Stock, ETF

logger = logging.getLogger(__name__)


class FinancialAnalyzer:
    """재무 분석 클래스"""

    @staticmethod
    def calculate_cagr(start_value: float, end_value: float, years: float) -> Optional[float]:
        """
        연평균 성장률(CAGR) 계산
        CAGR = (End Value / Start Value)^(1/years) - 1
        """
        try:
            if start_value <= 0 or end_value <= 0 or years <= 0:
                return None
            cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
            return round(cagr, 2)
        except Exception as e:
            logger.error(f"CAGR calculation failed: {e}")
            return None

    @staticmethod
    def calculate_revenue_cagr(financials: List[AlphaVantageFinancials], years: int = 3) -> Optional[float]:
        """
        매출 CAGR 계산
        - financials: 연도별 재무제표 리스트 (최신순 정렬)
        - years: 계산 기간 (기본 3년)
        """
        try:
            if len(financials) < years + 1:
                return None

            # 연간 보고서만 필터링
            annual_reports = [f for f in financials if f.report_type == 'annual']
            if len(annual_reports) < years + 1:
                return None

            # 최신 매출과 N년 전 매출
            end_revenue = annual_reports[0].revenue
            start_revenue = annual_reports[years].revenue

            if not end_revenue or not start_revenue:
                return None

            return FinancialAnalyzer.calculate_cagr(start_revenue, end_revenue, years)
        except Exception as e:
            logger.error(f"Revenue CAGR calculation failed: {e}")
            return None

    @staticmethod
    def calculate_eps_cagr(db: Session, symbol: str, financials: List[AlphaVantageFinancials], years: int = 3) -> Optional[float]:
        """
        EPS CAGR 계산
        - Alpha Vantage가 연도별 EPS를 제공하지 않으므로 순이익으로 계산
        - EPS = Net Income / Shares Outstanding (발행주식수는 최신값 사용)
        """
        try:
            if len(financials) < years + 1:
                return None

            annual_reports = [f for f in financials if f.report_type == 'annual']
            if len(annual_reports) < years + 1:
                return None

            # Stock 테이블에서 EPS 가져오기 (최신 TTM EPS)
            stock = db.query(AlphaVantageStock).filter(
                AlphaVantageStock.symbol == symbol.upper()
            ).first()

            # 발행주식수가 없으면 순이익으로 대체 계산
            if not stock:
                return None

            # 순이익 기반 EPS 계산 (발행주식수 필요)
            # Alpha Vantage는 SharesOutstanding을 제공하지만 DB에 저장하지 않음
            # 따라서 순이익 CAGR로 대체
            end_net_income = annual_reports[0].net_income
            start_net_income = annual_reports[years].net_income

            if not end_net_income or not start_net_income or start_net_income <= 0:
                return None

            # 순이익 CAGR을 EPS CAGR의 근사치로 사용
            return FinancialAnalyzer.calculate_cagr(start_net_income, end_net_income, years)
        except Exception as e:
            logger.error(f"EPS CAGR calculation failed: {e}")
            return None

    @staticmethod
    def calculate_profit_margins(financial: AlphaVantageFinancials) -> Dict[str, Optional[float]]:
        """
        이익률 계산
        - gross_margin: 매출총이익률 = (gross_profit / revenue) * 100
        - operating_margin: 영업이익률 = (operating_income / revenue) * 100
        - net_margin: 순이익률 = (net_income / revenue) * 100
        """
        try:
            revenue = financial.revenue
            if not revenue or revenue <= 0:
                return {"gross_margin": None, "operating_margin": None, "net_margin": None}

            gross_margin = (financial.gross_profit / revenue * 100) if financial.gross_profit else None
            operating_margin = (financial.operating_income / revenue * 100) if financial.operating_income else None
            net_margin = (financial.net_income / revenue * 100) if financial.net_income else None

            return {
                "gross_margin": round(gross_margin, 2) if gross_margin else None,
                "operating_margin": round(operating_margin, 2) if operating_margin else None,
                "net_margin": round(net_margin, 2) if net_margin else None
            }
        except Exception as e:
            logger.error(f"Profit margins calculation failed: {e}")
            return {"gross_margin": None, "operating_margin": None, "net_margin": None}

    @staticmethod
    def calculate_roe(financial: AlphaVantageFinancials) -> Optional[float]:
        """
        ROE (자기자본이익률) 계산
        ROE = (net_income / total_equity) * 100
        """
        try:
            if not financial.net_income or not financial.total_equity or financial.total_equity <= 0:
                return None
            roe = (financial.net_income / financial.total_equity) * 100
            return round(roe, 2)
        except Exception as e:
            logger.error(f"ROE calculation failed: {e}")
            return None

    @staticmethod
    def calculate_roa(financial: AlphaVantageFinancials) -> Optional[float]:
        """
        ROA (총자산이익률) 계산
        ROA = (net_income / total_assets) * 100
        """
        try:
            if not financial.net_income or not financial.total_assets or financial.total_assets <= 0:
                return None
            roa = (financial.net_income / financial.total_assets) * 100
            return round(roa, 2)
        except Exception as e:
            logger.error(f"ROA calculation failed: {e}")
            return None

    @staticmethod
    def calculate_debt_to_equity(financial: AlphaVantageFinancials) -> Optional[float]:
        """
        부채비율 계산
        Debt-to-Equity = (total_liabilities / total_equity) * 100
        """
        try:
            if not financial.total_liabilities or not financial.total_equity or financial.total_equity <= 0:
                return None
            debt_ratio = (financial.total_liabilities / financial.total_equity) * 100
            return round(debt_ratio, 2)
        except Exception as e:
            logger.error(f"Debt-to-equity calculation failed: {e}")
            return None

    @staticmethod
    def calculate_debt_to_total_debt(financial: AlphaVantageFinancials) -> Optional[float]:
        """
        순부채비율 계산
        Net Debt = (short_term_debt + long_term_debt - cash) / total_equity
        """
        try:
            total_debt = (financial.short_term_debt or 0) + (financial.long_term_debt or 0)
            cash = financial.cash_and_equivalents or 0
            equity = financial.total_equity

            if not equity or equity <= 0:
                return None

            net_debt_ratio = ((total_debt - cash) / equity) * 100
            return round(net_debt_ratio, 2)
        except Exception as e:
            logger.error(f"Net debt ratio calculation failed: {e}")
            return None

    @staticmethod
    def calculate_fcf_margin(financial: AlphaVantageFinancials) -> Optional[float]:
        """
        FCF 마진 계산
        FCF Margin = (free_cash_flow / revenue) * 100
        """
        try:
            if not financial.free_cash_flow or not financial.revenue or financial.revenue <= 0:
                return None
            fcf_margin = (financial.free_cash_flow / financial.revenue) * 100
            return round(fcf_margin, 2)
        except Exception as e:
            logger.error(f"FCF margin calculation failed: {e}")
            return None

    @staticmethod
    def calculate_dividend_consistency(db: Session, symbol: str, years: int = 5) -> Dict[str, any]:
        """
        배당 연속성 분석
        - consecutive_years: 연속 배당 지급 연수
        - dividend_growth_rate: 배당 성장률
        - payout_ratio: 배당성향 = (dividend / net_income) * 100
        """
        try:
            # 최근 N년 재무 데이터 조회
            financials = db.query(AlphaVantageFinancials).filter(
                and_(
                    AlphaVantageFinancials.symbol == symbol.upper(),
                    AlphaVantageFinancials.report_type == 'annual'
                )
            ).order_by(desc(AlphaVantageFinancials.fiscal_date)).limit(years).all()

            if not financials:
                return {
                    "consecutive_years": 0,
                    "dividend_growth_rate": None,
                    "payout_ratio": None,
                    "current_dividend_yield": None
                }

            # Alpha Vantage Stock 데이터에서 현재 배당수익률 가져오기
            stock = db.query(AlphaVantageStock).filter(
                AlphaVantageStock.symbol == symbol.upper()
            ).first()

            # Alpha Vantage는 배당수익률을 소수(0.0037)로 저장 -> % 변환 필요
            current_dividend_yield = None
            if stock and stock.dividend_yield:
                # 0.0037 -> 0.37%
                current_dividend_yield = stock.dividend_yield * 100

            # 배당성향 계산 (최근 연도 기준)
            latest = financials[0]
            payout_ratio = None
            if latest.net_income and latest.net_income > 0 and current_dividend_yield:
                # Payout Ratio = Dividend / Net Income
                # 배당금 = 주가 * 배당수익률 / 100 (근사치)
                # 여기서는 간단히 배당수익률만 기록
                payout_ratio = current_dividend_yield  # 실제로는 더 정확한 계산 필요

            return {
                "consecutive_years": years if current_dividend_yield and current_dividend_yield > 0 else 0,
                "dividend_growth_rate": None,  # 히스토리 데이터 필요
                "payout_ratio": round(payout_ratio, 2) if payout_ratio else None,
                "current_dividend_yield": round(current_dividend_yield, 2) if current_dividend_yield else None
            }
        except Exception as e:
            logger.error(f"Dividend consistency analysis failed: {e}")
            return {
                "consecutive_years": 0,
                "dividend_growth_rate": None,
                "payout_ratio": None,
                "current_dividend_yield": None
            }

    @staticmethod
    def analyze_stock(db: Session, symbol: str) -> Dict[str, any]:
        """
        종합 재무 분석
        - symbol: 종목 심볼 (예: AAPL)
        """
        try:
            logger.info(f"Starting financial analysis for {symbol}")

            # 1. 재무제표 데이터 조회 (최신순)
            financials = db.query(AlphaVantageFinancials).filter(
                AlphaVantageFinancials.symbol == symbol.upper()
            ).order_by(desc(AlphaVantageFinancials.fiscal_date)).all()

            if not financials:
                return {
                    "success": False,
                    "message": f"재무제표 데이터가 없습니다: {symbol}",
                    "symbol": symbol.upper()
                }

            latest_financial = financials[0]

            # 2. 주식 기본 정보 조회
            stock = db.query(AlphaVantageStock).filter(
                AlphaVantageStock.symbol == symbol.upper()
            ).first()

            # 3. 성장률 계산
            revenue_cagr_3y = FinancialAnalyzer.calculate_revenue_cagr(financials, years=3)
            revenue_cagr_5y = FinancialAnalyzer.calculate_revenue_cagr(financials, years=5)
            eps_cagr_3y = FinancialAnalyzer.calculate_eps_cagr(db, symbol, financials, years=3)
            eps_cagr_5y = FinancialAnalyzer.calculate_eps_cagr(db, symbol, financials, years=5)

            # 4. 마진 계산
            margins = FinancialAnalyzer.calculate_profit_margins(latest_financial)

            # 5. 수익성 지표
            roe = FinancialAnalyzer.calculate_roe(latest_financial)
            roa = FinancialAnalyzer.calculate_roa(latest_financial)

            # 6. 부채 비율
            debt_to_equity = FinancialAnalyzer.calculate_debt_to_equity(latest_financial)
            net_debt_ratio = FinancialAnalyzer.calculate_debt_to_total_debt(latest_financial)

            # 7. FCF 마진
            fcf_margin = FinancialAnalyzer.calculate_fcf_margin(latest_financial)

            # 8. 배당 분석
            dividend_analysis = FinancialAnalyzer.calculate_dividend_consistency(db, symbol, years=5)

            # 9. 결과 정리
            result = {
                "success": True,
                "symbol": symbol.upper(),
                "company_name": stock.name if stock else None,
                "analysis_date": datetime.now().isoformat(),
                "latest_fiscal_date": latest_financial.fiscal_date.isoformat(),

                # 성장률
                "growth_metrics": {
                    "revenue_cagr_3y": revenue_cagr_3y,
                    "revenue_cagr_5y": revenue_cagr_5y,
                    "eps_cagr_3y": eps_cagr_3y,
                    "eps_cagr_5y": eps_cagr_5y
                },

                # 이익률
                "profit_margins": {
                    "gross_margin": margins["gross_margin"],
                    "operating_margin": margins["operating_margin"],
                    "net_margin": margins["net_margin"],
                    "fcf_margin": fcf_margin
                },

                # 수익성
                "profitability": {
                    "roe": roe,
                    "roa": roa
                },

                # 재무 건전성
                "financial_health": {
                    "debt_to_equity": debt_to_equity,
                    "net_debt_ratio": net_debt_ratio,
                    "current_ratio": latest_financial.current_ratio
                },

                # 배당
                "dividend_metrics": dividend_analysis,

                # 밸류에이션
                "valuation": {
                    "pe_ratio": stock.pe_ratio if stock else None,
                    "pb_ratio": stock.pb_ratio if stock else None,
                    "peg_ratio": stock.peg_ratio if stock else None,
                    "market_cap": stock.market_cap if stock else None
                },

                # 최신 재무 데이터
                "latest_financials": {
                    "revenue": latest_financial.revenue,
                    "net_income": latest_financial.net_income,
                    "total_assets": latest_financial.total_assets,
                    "total_equity": latest_financial.total_equity,
                    "total_liabilities": latest_financial.total_liabilities,
                    "free_cash_flow": latest_financial.free_cash_flow,
                    "eps": latest_financial.eps
                }
            }

            logger.info(f"Financial analysis completed for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Financial analysis failed for {symbol}: {e}")
            return {
                "success": False,
                "message": f"재무 분석 실패: {str(e)}",
                "symbol": symbol.upper()
            }

    @staticmethod
    def compare_stocks(db: Session, symbols: List[str]) -> Dict[str, any]:
        """
        여러 종목 비교 분석
        - symbols: 비교할 종목 심볼 리스트 (예: ['AAPL', 'GOOGL', 'MSFT'])
        """
        try:
            results = []
            for symbol in symbols:
                analysis = FinancialAnalyzer.analyze_stock(db, symbol)
                if analysis["success"]:
                    results.append(analysis)

            return {
                "success": True,
                "comparison_count": len(results),
                "stocks": results
            }
        except Exception as e:
            logger.error(f"Stock comparison failed: {e}")
            return {
                "success": False,
                "message": f"종목 비교 실패: {str(e)}"
            }

    @staticmethod
    def get_financial_score_v2(db: Session, symbol: str) -> Dict[str, any]:
        """
        개선된 재무 점수 계산 V2 (성숙한 대형주/성장주에 적합)
        - 성장성: 3년+5년 가중 평균 (30점)
        - 수익성: ROE+마진 (30점)
        - 안정성: 부채비율+현금창출력 (25점)
        - 주주환원: 배당+자사주매입 (15점)
        """
        try:
            analysis = FinancialAnalyzer.analyze_stock(db, symbol)
            if not analysis["success"]:
                return analysis

            score = 0
            details = {}

            # 1. 성장성 (30점) - 3년/5년 가중 평균
            growth_score = 0
            revenue_cagr_3y = analysis["growth_metrics"]["revenue_cagr_3y"]
            revenue_cagr_5y = analysis["growth_metrics"]["revenue_cagr_5y"]
            eps_cagr_3y = analysis["growth_metrics"]["eps_cagr_3y"]
            eps_cagr_5y = analysis["growth_metrics"]["eps_cagr_5y"]

            # 매출 CAGR (가중평균: 3Y 40% + 5Y 60%)
            if revenue_cagr_3y is not None and revenue_cagr_5y is not None:
                weighted_revenue_cagr = 0.4 * revenue_cagr_3y + 0.6 * revenue_cagr_5y
                if weighted_revenue_cagr >= 15:
                    growth_score += 15
                elif weighted_revenue_cagr >= 10:
                    growth_score += 12
                elif weighted_revenue_cagr >= 7:
                    growth_score += 9
                elif weighted_revenue_cagr >= 5:
                    growth_score += 6
                elif weighted_revenue_cagr >= 3:  # 성숙 대기업 기준 완화
                    growth_score += 3
            elif revenue_cagr_3y is not None:  # 5년 데이터 없으면 3년만
                if revenue_cagr_3y >= 10:
                    growth_score += 15
                elif revenue_cagr_3y >= 5:
                    growth_score += 10
                elif revenue_cagr_3y >= 3:
                    growth_score += 5

            # EPS CAGR (가중평균: 3Y 40% + 5Y 60%)
            if eps_cagr_3y is not None and eps_cagr_5y is not None:
                weighted_eps_cagr = 0.4 * eps_cagr_3y + 0.6 * eps_cagr_5y
                if weighted_eps_cagr >= 20:
                    growth_score += 15
                elif weighted_eps_cagr >= 15:
                    growth_score += 12
                elif weighted_eps_cagr >= 10:
                    growth_score += 9
                elif weighted_eps_cagr >= 7:
                    growth_score += 6
                elif weighted_eps_cagr >= 5:  # 성숙 대기업 기준 완화
                    growth_score += 3
            elif eps_cagr_3y is not None:
                if eps_cagr_3y >= 15:
                    growth_score += 15
                elif eps_cagr_3y >= 10:
                    growth_score += 10
                elif eps_cagr_3y >= 5:
                    growth_score += 5

            details["growth_score"] = growth_score
            score += growth_score

            # 2. 수익성 (30점) - 동일
            profitability_score = 0
            roe = analysis["profitability"]["roe"]
            net_margin = analysis["profit_margins"]["net_margin"]

            if roe is not None:
                if roe >= 20:
                    profitability_score += 15
                elif roe >= 15:
                    profitability_score += 10
                elif roe >= 10:
                    profitability_score += 5

            if net_margin is not None:
                if net_margin >= 20:
                    profitability_score += 15
                elif net_margin >= 10:
                    profitability_score += 10
                elif net_margin >= 5:
                    profitability_score += 5

            details["profitability_score"] = profitability_score
            score += profitability_score

            # 3. 안정성 (25점) - 개선: 고ROE 기업은 부채비율 기준 완화
            stability_score = 0
            debt_to_equity = analysis["financial_health"]["debt_to_equity"]
            net_debt_ratio = analysis["financial_health"]["net_debt_ratio"]

            # ROE가 높으면 레버리지 전략으로 간주하여 부채비율 기준 완화
            is_high_roe = roe and roe >= 20

            if debt_to_equity is not None:
                if is_high_roe:  # 고ROE 기업용 완화된 기준
                    if debt_to_equity <= 100:
                        stability_score += 15
                    elif debt_to_equity <= 200:
                        stability_score += 12
                    elif debt_to_equity <= 300:
                        stability_score += 9
                    elif debt_to_equity <= 400:
                        stability_score += 6
                else:  # 일반 기업 기준
                    if debt_to_equity <= 50:
                        stability_score += 15
                    elif debt_to_equity <= 100:
                        stability_score += 10
                    elif debt_to_equity <= 150:
                        stability_score += 5

            # 순부채비율로 추가 평가 (현금 보유량 고려)
            if net_debt_ratio is not None:
                if net_debt_ratio <= 0:  # 순현금 보유
                    stability_score += 10
                elif net_debt_ratio <= 50:
                    stability_score += 7
                elif net_debt_ratio <= 100:
                    stability_score += 4

            details["stability_score"] = min(stability_score, 25)  # 최대 25점
            score += min(stability_score, 25)

            # 4. 주주환원 (15점) - 배당 기준만 (자사주 매입 데이터 없음)
            shareholder_return_score = 0
            dividend_yield = analysis["dividend_metrics"]["current_dividend_yield"]

            # 배당수익률
            if dividend_yield is not None and dividend_yield > 0:
                if dividend_yield >= 3:
                    shareholder_return_score += 15
                elif dividend_yield >= 2:
                    shareholder_return_score += 10
                elif dividend_yield >= 1:
                    shareholder_return_score += 7
                elif dividend_yield >= 0.3:  # 성장주는 낮은 배당도 인정
                    shareholder_return_score += 4

            details["shareholder_return_score"] = shareholder_return_score
            score += shareholder_return_score

            # 등급 부여
            if score >= 80:
                grade = "A"
                rating = "매우 우수"
            elif score >= 60:
                grade = "B"
                rating = "우수"
            elif score >= 40:
                grade = "C"
                rating = "보통"
            elif score >= 20:
                grade = "D"
                rating = "주의"
            else:
                grade = "F"
                rating = "위험"

            # 투자 스타일 분류
            investment_style = FinancialAnalyzer._classify_investment_style(analysis)

            return {
                "success": True,
                "symbol": symbol.upper(),
                "total_score": score,
                "grade": grade,
                "rating": rating,
                "score_details": details,
                "investment_style": investment_style,
                "analysis_date": datetime.now().isoformat(),
                "scoring_version": "v2"
            }

        except Exception as e:
            logger.error(f"Financial score V2 calculation failed for {symbol}: {e}")
            return {
                "success": False,
                "message": f"재무 점수 계산 실패: {str(e)}",
                "symbol": symbol.upper()
            }

    @staticmethod
    def _classify_investment_style(analysis: Dict) -> Dict[str, str]:
        """투자 스타일 분류"""
        growth = analysis["growth_metrics"]
        profitability = analysis["profitability"]
        dividend = analysis["dividend_metrics"]

        # 성장률 기준
        revenue_5y = growth.get("revenue_cagr_5y", 0) or 0
        eps_5y = growth.get("eps_cagr_5y", 0) or 0

        # 수익성 기준
        roe = profitability.get("roe", 0) or 0

        # 배당 기준
        div_yield = dividend.get("current_dividend_yield", 0) or 0

        # 스타일 분류
        if revenue_5y >= 10 and eps_5y >= 10:
            if roe >= 20:
                style = "고수익 성장주"
                description = "높은 성장률과 우수한 수익성을 동시에 보유한 프리미엄 성장주"
            else:
                style = "성장주"
                description = "높은 성장률을 보이는 기업"
        elif revenue_5y >= 5 and roe >= 20:
            style = "성숙한 성장주"
            description = "성장은 둔화되었으나 높은 수익성을 유지하는 우량 기업"
        elif div_yield >= 3:
            style = "배당주"
            description = "안정적인 배당을 제공하는 기업"
        elif roe >= 15:
            style = "우량 가치주"
            description = "높은 수익성을 보이는 저평가 기업"
        else:
            style = "일반 기업"
            description = "성장과 수익성이 보통 수준인 기업"

        return {
            "style": style,
            "description": description
        }

    @staticmethod
    def get_financial_score(db: Session, symbol: str) -> Dict[str, any]:
        """
        재무 건전성 점수 계산 (100점 만점) - 기본 버전
        - 성장성: 30점
        - 수익성: 30점
        - 안정성: 25점
        - 배당: 15점
        """
        try:
            analysis = FinancialAnalyzer.analyze_stock(db, symbol)
            if not analysis["success"]:
                return analysis

            score = 0
            details = {}

            # 1. 성장성 (30점)
            growth_score = 0
            revenue_cagr_3y = analysis["growth_metrics"]["revenue_cagr_3y"]
            eps_cagr_3y = analysis["growth_metrics"]["eps_cagr_3y"]

            if revenue_cagr_3y is not None:
                if revenue_cagr_3y >= 20:
                    growth_score += 15
                elif revenue_cagr_3y >= 10:
                    growth_score += 10
                elif revenue_cagr_3y >= 5:
                    growth_score += 5

            if eps_cagr_3y is not None:
                if eps_cagr_3y >= 20:
                    growth_score += 15
                elif eps_cagr_3y >= 10:
                    growth_score += 10
                elif eps_cagr_3y >= 5:
                    growth_score += 5

            details["growth_score"] = growth_score
            score += growth_score

            # 2. 수익성 (30점)
            profitability_score = 0
            roe = analysis["profitability"]["roe"]
            net_margin = analysis["profit_margins"]["net_margin"]

            if roe is not None:
                if roe >= 20:
                    profitability_score += 15
                elif roe >= 15:
                    profitability_score += 10
                elif roe >= 10:
                    profitability_score += 5

            if net_margin is not None:
                if net_margin >= 20:
                    profitability_score += 15
                elif net_margin >= 10:
                    profitability_score += 10
                elif net_margin >= 5:
                    profitability_score += 5

            details["profitability_score"] = profitability_score
            score += profitability_score

            # 3. 안정성 (25점)
            stability_score = 0
            debt_to_equity = analysis["financial_health"]["debt_to_equity"]
            current_ratio = analysis["financial_health"]["current_ratio"]

            if debt_to_equity is not None:
                if debt_to_equity <= 50:
                    stability_score += 15
                elif debt_to_equity <= 100:
                    stability_score += 10
                elif debt_to_equity <= 150:
                    stability_score += 5

            if current_ratio is not None:
                if current_ratio >= 2.0:
                    stability_score += 10
                elif current_ratio >= 1.5:
                    stability_score += 5

            details["stability_score"] = stability_score
            score += stability_score

            # 4. 배당 (15점)
            dividend_score = 0
            dividend_yield = analysis["dividend_metrics"]["current_dividend_yield"]

            if dividend_yield is not None and dividend_yield > 0:
                if dividend_yield >= 3:
                    dividend_score += 15
                elif dividend_yield >= 2:
                    dividend_score += 10
                elif dividend_yield >= 1:
                    dividend_score += 5

            details["dividend_score"] = dividend_score
            score += dividend_score

            # 등급 부여
            if score >= 80:
                grade = "A"
                rating = "매우 우수"
            elif score >= 60:
                grade = "B"
                rating = "우수"
            elif score >= 40:
                grade = "C"
                rating = "보통"
            elif score >= 20:
                grade = "D"
                rating = "주의"
            else:
                grade = "F"
                rating = "위험"

            return {
                "success": True,
                "symbol": symbol.upper(),
                "total_score": score,
                "grade": grade,
                "rating": rating,
                "score_details": details,
                "analysis_date": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Financial score calculation failed for {symbol}: {e}")
            return {
                "success": False,
                "message": f"재무 점수 계산 실패: {str(e)}",
                "symbol": symbol.upper()
            }
