# backend/app/services/valuation.py

"""
밸류에이션 모듈
- 단순 멀티플 비교: PER/PBR/배당수익률 vs 업종/시장 평균
- DCF 모델 (시나리오별)
- 배당할인모형 (DDM)
"""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
from decimal import Decimal

from app.models.alpha_vantage import AlphaVantageStock, AlphaVantageFinancials
from app.models.securities import Stock, StockFinancials

logger = logging.getLogger(__name__)


# 업종별 평균 멀티플 (2024-2025 기준, S&P 500 참고)
INDUSTRY_MULTIPLES = {
    # Technology
    "Technology": {
        "avg_pe": 28.5,
        "avg_pb": 6.2,
        "avg_div_yield": 0.8,
        "description": "기술 및 소프트웨어"
    },
    "Software": {
        "avg_pe": 32.0,
        "avg_pb": 7.5,
        "avg_div_yield": 0.5,
        "description": "소프트웨어 및 클라우드"
    },
    "Semiconductors": {
        "avg_pe": 25.0,
        "avg_pb": 5.8,
        "avg_div_yield": 1.2,
        "description": "반도체"
    },

    # Consumer
    "Consumer Discretionary": {
        "avg_pe": 22.0,
        "avg_pb": 4.5,
        "avg_div_yield": 1.5,
        "description": "임의소비재"
    },
    "Consumer Staples": {
        "avg_pe": 20.0,
        "avg_pb": 4.0,
        "avg_div_yield": 2.5,
        "description": "필수소비재"
    },

    # Finance
    "Financial Services": {
        "avg_pe": 15.0,
        "avg_pb": 1.8,
        "avg_div_yield": 2.8,
        "description": "금융서비스"
    },
    "Banks": {
        "avg_pe": 12.0,
        "avg_pb": 1.2,
        "avg_div_yield": 3.5,
        "description": "은행"
    },

    # Healthcare
    "Healthcare": {
        "avg_pe": 18.5,
        "avg_pb": 3.8,
        "avg_div_yield": 1.8,
        "description": "헬스케어"
    },
    "Pharmaceuticals": {
        "avg_pe": 16.0,
        "avg_pb": 3.2,
        "avg_div_yield": 2.5,
        "description": "제약"
    },

    # Industrial
    "Industrials": {
        "avg_pe": 19.0,
        "avg_pb": 3.5,
        "avg_div_yield": 2.0,
        "description": "산업재"
    },

    # Energy
    "Energy": {
        "avg_pe": 12.0,
        "avg_pb": 1.5,
        "avg_div_yield": 3.8,
        "description": "에너지"
    },

    # Utilities
    "Utilities": {
        "avg_pe": 17.0,
        "avg_pb": 1.8,
        "avg_div_yield": 3.2,
        "description": "유틸리티"
    },

    # Real Estate
    "Real Estate": {
        "avg_pe": 25.0,
        "avg_pb": 1.6,
        "avg_div_yield": 3.5,
        "description": "부동산"
    },

    # Communication
    "Communication Services": {
        "avg_pe": 18.0,
        "avg_pb": 2.8,
        "avg_div_yield": 1.2,
        "description": "통신서비스"
    },

    # Materials
    "Materials": {
        "avg_pe": 16.0,
        "avg_pb": 2.2,
        "avg_div_yield": 2.5,
        "description": "소재"
    },
}

# S&P 500 전체 시장 평균
MARKET_AVERAGE = {
    "avg_pe": 21.0,
    "avg_pb": 4.0,
    "avg_div_yield": 1.6,
    "description": "S&P 500 평균"
}


class ValuationAnalyzer:
    """밸류에이션 분석 클래스"""

    @staticmethod
    def get_industry_multiples(industry: str) -> Dict:
        """
        업종별 평균 멀티플 조회
        """
        # 정확히 일치하는 업종 찾기
        if industry in INDUSTRY_MULTIPLES:
            return INDUSTRY_MULTIPLES[industry]

        # 부분 일치 시도
        for ind_key, ind_data in INDUSTRY_MULTIPLES.items():
            if industry.lower() in ind_key.lower() or ind_key.lower() in industry.lower():
                return ind_data

        # 기본값: 시장 평균
        return MARKET_AVERAGE

    @staticmethod
    def compare_multiples(db: Session, symbol: str) -> Dict:
        """
        멀티플 비교 분석
        - PER, PBR, 배당수익률을 업종/시장 평균과 비교
        - 한국 주식과 미국 주식 모두 지원
        """
        # 한국 주식인지 확인 (숫자로만 구성된 경우)
        is_korean_stock = symbol.isdigit()

        if is_korean_stock:
            # 한국 주식 조회
            stock = db.query(Stock).filter(Stock.ticker == symbol).first()
            if not stock:
                raise ValueError(f"한국 주식 {symbol}을 찾을 수 없습니다")

            # 현재 종목 멀티플
            current_pe = stock.pe_ratio
            current_pb = stock.pb_ratio
            current_div_yield = stock.dividend_yield if stock.dividend_yield else 0
            company_name = stock.name
            sector = stock.sector or "Market"
            industry = sector
        else:
            # 미국 주식 조회
            stock = db.query(AlphaVantageStock).filter(
                AlphaVantageStock.symbol == symbol.upper()
            ).first()

            if not stock:
                raise ValueError(f"Stock {symbol} not found")

            # 현재 종목 멀티플
            current_pe = stock.pe_ratio
            current_pb = stock.pb_ratio
            current_div_yield = (stock.dividend_yield * 100) if stock.dividend_yield else 0
            company_name = stock.name
            sector = stock.sector or "Market"
            industry = stock.industry

        # 업종별 평균 멀티플 가져오기
        industry_avg = ValuationAnalyzer.get_industry_multiples(sector)

        # 비교 분석
        pe_comparison = None
        pb_comparison = None
        div_comparison = None

        if current_pe and industry_avg["avg_pe"]:
            pe_diff = ((current_pe - industry_avg["avg_pe"]) / industry_avg["avg_pe"]) * 100
            pe_comparison = {
                "current": round(current_pe, 2),
                "industry_avg": industry_avg["avg_pe"],
                "market_avg": MARKET_AVERAGE["avg_pe"],
                "vs_industry": round(pe_diff, 2),
                "vs_market": round(((current_pe - MARKET_AVERAGE["avg_pe"]) / MARKET_AVERAGE["avg_pe"]) * 100, 2),
                "status": "고평가" if pe_diff > 20 else "저평가" if pe_diff < -20 else "적정"
            }

        if current_pb and industry_avg["avg_pb"]:
            pb_diff = ((current_pb - industry_avg["avg_pb"]) / industry_avg["avg_pb"]) * 100
            pb_comparison = {
                "current": round(current_pb, 2),
                "industry_avg": industry_avg["avg_pb"],
                "market_avg": MARKET_AVERAGE["avg_pb"],
                "vs_industry": round(pb_diff, 2),
                "vs_market": round(((current_pb - MARKET_AVERAGE["avg_pb"]) / MARKET_AVERAGE["avg_pb"]) * 100, 2),
                "status": "고평가" if pb_diff > 20 else "저평가" if pb_diff < -20 else "적정"
            }

        if current_div_yield and industry_avg["avg_div_yield"]:
            div_diff = ((current_div_yield - industry_avg["avg_div_yield"]) / industry_avg["avg_div_yield"]) * 100
            div_comparison = {
                "current": round(current_div_yield, 2),
                "industry_avg": industry_avg["avg_div_yield"],
                "market_avg": MARKET_AVERAGE["avg_div_yield"],
                "vs_industry": round(div_diff, 2),
                "vs_market": round(((current_div_yield - MARKET_AVERAGE["avg_div_yield"]) / MARKET_AVERAGE["avg_div_yield"]) * 100, 2),
                "status": "높음" if div_diff > 20 else "낮음" if div_diff < -20 else "적정"
            }

        return {
            "symbol": symbol.upper() if not is_korean_stock else symbol,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "industry_description": industry_avg.get("description", ""),
            "pe_comparison": pe_comparison,
            "pb_comparison": pb_comparison,
            "dividend_yield_comparison": div_comparison,
            "overall_valuation": ValuationAnalyzer._determine_overall_valuation(
                pe_comparison, pb_comparison, div_comparison
            ),
            "korean_stock": is_korean_stock
        }

    @staticmethod
    def _determine_overall_valuation(pe_comp, pb_comp, div_comp) -> str:
        """전체 밸류에이션 판단"""
        scores = []

        if pe_comp:
            if pe_comp["status"] == "고평가":
                scores.append(-1)
            elif pe_comp["status"] == "저평가":
                scores.append(1)
            else:
                scores.append(0)

        if pb_comp:
            if pb_comp["status"] == "고평가":
                scores.append(-1)
            elif pb_comp["status"] == "저평가":
                scores.append(1)
            else:
                scores.append(0)

        if div_comp:
            if div_comp["status"] == "높음":
                scores.append(1)
            elif div_comp["status"] == "낮음":
                scores.append(-1)
            else:
                scores.append(0)

        if not scores:
            return "데이터 부족"

        avg_score = sum(scores) / len(scores)

        if avg_score > 0.5:
            return "저평가"
        elif avg_score < -0.5:
            return "고평가"
        else:
            return "적정 평가"

    @staticmethod
    def dcf_valuation(db: Session, symbol: str) -> Dict:
        """
        DCF (Discounted Cash Flow) 밸류에이션
        - 보수적 가정으로 3가지 시나리오 제공
        - 한국 주식은 현금흐름 데이터 부족으로 지원하지 않음
        """
        # 한국 주식인지 확인
        is_korean_stock = symbol.isdigit()

        if is_korean_stock:
            stock = db.query(Stock).filter(Stock.ticker == symbol).first()
            if not stock:
                raise ValueError(f"한국 주식 {symbol}을 찾을 수 없습니다")

            return {
                "symbol": symbol,
                "company_name": stock.name,
                "korean_stock": True,
                "error": "한국 주식은 DCF 분석을 지원하지 않습니다",
                "message": "pykrx는 현금흐름표 데이터를 제공하지 않아 DCF 분석이 불가능합니다. 멀티플 비교를 참고하세요."
            }

        # 미국 주식 DCF 분석
        stock = db.query(AlphaVantageStock).filter(
            AlphaVantageStock.symbol == symbol.upper()
        ).first()

        if not stock:
            raise ValueError(f"Stock {symbol} not found")

        # 최근 5년 재무제표 가져오기
        financials = db.query(AlphaVantageFinancials).filter(
            AlphaVantageFinancials.symbol == symbol.upper(),
            AlphaVantageFinancials.report_type == "annual"
        ).order_by(desc(AlphaVantageFinancials.fiscal_date)).limit(5).all()

        if len(financials) < 3:
            raise ValueError("충분한 재무 데이터가 없습니다 (최소 3년 필요)")

        # FCF (Free Cash Flow) 계산
        # free_cash_flow가 있으면 사용, 없으면 operating_cash_flow를 근사값으로 사용
        latest = financials[0]
        fcf = latest.free_cash_flow if latest.free_cash_flow else latest.operating_cash_flow

        if not fcf or fcf <= 0:
            return {
                "symbol": symbol.upper(),
                "error": "FCF 데이터가 없거나 음수입니다",
                "message": "현금흐름이 부족하여 DCF 분석이 어렵습니다"
            }

        # 과거 FCF 성장률 계산
        fcf_growth_rates = []
        for i in range(len(financials) - 1):
            current_fcf = financials[i].free_cash_flow if financials[i].free_cash_flow else financials[i].operating_cash_flow
            prev_fcf = financials[i+1].free_cash_flow if financials[i+1].free_cash_flow else financials[i+1].operating_cash_flow

            if current_fcf and prev_fcf and prev_fcf > 0:
                growth = ((current_fcf / prev_fcf) - 1) * 100
                fcf_growth_rates.append(growth)

        avg_fcf_growth = sum(fcf_growth_rates) / len(fcf_growth_rates) if fcf_growth_rates else 0

        # 시나리오별 가정
        scenarios = {
            "보수적": {
                "growth_rate": min(avg_fcf_growth * 0.5, 5.0),  # 과거 성장률의 50%, 최대 5%
                "terminal_growth": 2.0,
                "discount_rate": 10.0,
                "description": "낮은 성장률, 높은 할인율"
            },
            "중립적": {
                "growth_rate": min(avg_fcf_growth * 0.7, 8.0),  # 과거 성장률의 70%, 최대 8%
                "terminal_growth": 2.5,
                "discount_rate": 9.0,
                "description": "중간 성장률, 중간 할인율"
            },
            "낙관적": {
                "growth_rate": min(avg_fcf_growth, 12.0),  # 과거 성장률 유지, 최대 12%
                "terminal_growth": 3.0,
                "discount_rate": 8.0,
                "description": "높은 성장률, 낮은 할인율"
            }
        }

        # 시나리오별 DCF 계산
        results = {}
        projection_years = 5

        for scenario_name, assumptions in scenarios.items():
            growth_rate = assumptions["growth_rate"] / 100
            terminal_growth = assumptions["terminal_growth"] / 100
            discount_rate = assumptions["discount_rate"] / 100

            # 5년간 FCF 예측
            projected_fcf = []
            current_fcf = fcf

            for year in range(1, projection_years + 1):
                current_fcf = current_fcf * (1 + growth_rate)
                discounted_fcf = current_fcf / ((1 + discount_rate) ** year)
                projected_fcf.append({
                    "year": year,
                    "fcf": round(current_fcf, 2),
                    "discounted_fcf": round(discounted_fcf, 2)
                })

            # Terminal Value 계산
            terminal_fcf = current_fcf * (1 + terminal_growth)
            terminal_value = terminal_fcf / (discount_rate - terminal_growth)
            discounted_terminal_value = terminal_value / ((1 + discount_rate) ** projection_years)

            # 총 기업 가치
            sum_discounted_fcf = sum(p["discounted_fcf"] for p in projected_fcf)
            enterprise_value = sum_discounted_fcf + discounted_terminal_value

            # 주당 가치 (순부채 반영)
            net_debt = 0
            total_debt = 0
            if latest.short_term_debt:
                total_debt += latest.short_term_debt
            if latest.long_term_debt:
                total_debt += latest.long_term_debt
            if total_debt and latest.cash_and_equivalents:
                net_debt = total_debt - latest.cash_and_equivalents

            equity_value = enterprise_value - net_debt
            shares_outstanding = stock.market_cap / stock.current_price if stock.market_cap and stock.current_price else None

            fair_value_per_share = equity_value / shares_outstanding if shares_outstanding else None

            results[scenario_name] = {
                "assumptions": assumptions,
                "base_fcf": round(fcf, 2),
                "avg_fcf_growth": round(avg_fcf_growth, 2),
                "projected_fcf": projected_fcf,
                "terminal_value": round(terminal_value, 2),
                "discounted_terminal_value": round(discounted_terminal_value, 2),
                "enterprise_value": round(enterprise_value, 2),
                "net_debt": round(net_debt, 2),
                "equity_value": round(equity_value, 2),
                "shares_outstanding": round(shares_outstanding, 2) if shares_outstanding else None,
                "fair_value_per_share": round(fair_value_per_share, 2) if fair_value_per_share else None,
                "current_price": round(stock.current_price, 2) if stock.current_price else None,
                "upside_downside": round(((fair_value_per_share / stock.current_price - 1) * 100), 2) if fair_value_per_share and stock.current_price else None
            }

        return {
            "symbol": symbol.upper(),
            "company_name": stock.name,
            "method": "DCF (Discounted Cash Flow)",
            "scenarios": results
        }

    @staticmethod
    def dividend_discount_model(db: Session, symbol: str) -> Dict:
        """
        배당할인모형 (DDM - Dividend Discount Model)
        - Gordon Growth Model 사용
        - 안정적인 배당을 지급하는 기업에 적합
        - 한국 주식은 배당 성장률 데이터 부족으로 지원하지 않음
        """
        # 한국 주식인지 확인
        is_korean_stock = symbol.isdigit()

        if is_korean_stock:
            stock = db.query(Stock).filter(Stock.ticker == symbol).first()
            if not stock:
                raise ValueError(f"한국 주식 {symbol}을 찾을 수 없습니다")

            return {
                "symbol": symbol,
                "company_name": stock.name,
                "korean_stock": True,
                "error": "한국 주식은 DDM 분석을 지원하지 않습니다",
                "message": "pykrx는 배당 성장률 데이터를 제공하지 않아 DDM 분석이 불가능합니다. 현재 배당수익률은 멀티플 비교에서 확인하세요."
            }

        # 미국 주식 DDM 분석
        stock = db.query(AlphaVantageStock).filter(
            AlphaVantageStock.symbol == symbol.upper()
        ).first()

        if not stock:
            raise ValueError(f"Stock {symbol} not found")

        # 배당 데이터 확인
        current_dividend_yield = (stock.dividend_yield * 100) if stock.dividend_yield else 0

        if not current_dividend_yield or current_dividend_yield < 0.1:
            return {
                "symbol": symbol.upper(),
                "error": "배당금이 없거나 너무 낮습니다",
                "message": "배당할인모형은 안정적인 배당 지급 기업에만 적용 가능합니다"
            }

        # 현재 주가와 배당금
        current_price = stock.current_price
        annual_dividend = current_price * (stock.dividend_yield) if current_price and stock.dividend_yield else 0

        if not annual_dividend:
            return {
                "symbol": symbol.upper(),
                "error": "배당금 계산 실패",
                "message": "배당 데이터가 불충분합니다"
            }

        # 재무제표에서 배당 성장률 추정
        financials = db.query(AlphaVantageFinancials).filter(
            AlphaVantageFinancials.symbol == symbol.upper(),
            AlphaVantageFinancials.report_type == "annual"
        ).order_by(desc(AlphaVantageFinancials.fiscal_date)).limit(5).all()

        # 순이익 성장률을 배당 성장률 대용으로 사용
        growth_rates = []
        for i in range(len(financials) - 1):
            current_ni = financials[i].net_income
            prev_ni = financials[i+1].net_income

            if current_ni and prev_ni and prev_ni > 0:
                growth = ((current_ni / prev_ni) - 1) * 100
                growth_rates.append(growth)

        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 3.0

        # 시나리오별 가정
        scenarios = {
            "보수적": {
                "dividend_growth": min(avg_growth * 0.5, 3.0),
                "required_return": 10.0,
                "description": "낮은 성장률, 높은 요구수익률"
            },
            "중립적": {
                "dividend_growth": min(avg_growth * 0.7, 5.0),
                "required_return": 9.0,
                "description": "중간 성장률, 중간 요구수익률"
            },
            "낙관적": {
                "dividend_growth": min(avg_growth, 7.0),
                "required_return": 8.0,
                "description": "높은 성장률, 낮은 요구수익률"
            }
        }

        # 시나리오별 계산
        results = {}

        for scenario_name, assumptions in scenarios.items():
            g = assumptions["dividend_growth"] / 100
            r = assumptions["required_return"] / 100

            if r <= g:
                results[scenario_name] = {
                    "assumptions": assumptions,
                    "error": "요구수익률이 성장률보다 낮아 계산 불가",
                    "message": "Gordon Growth Model은 성장률 < 요구수익률 조건 필요"
                }
                continue

            # Gordon Growth Model: P = D1 / (r - g)
            next_dividend = annual_dividend * (1 + g)
            fair_value = next_dividend / (r - g)

            results[scenario_name] = {
                "assumptions": assumptions,
                "current_dividend": round(annual_dividend, 2),
                "next_dividend": round(next_dividend, 2),
                "fair_value": round(fair_value, 2),
                "current_price": round(current_price, 2),
                "upside_downside": round(((fair_value / current_price - 1) * 100), 2),
                "implied_return": round((next_dividend / current_price + g) * 100, 2)
            }

        return {
            "symbol": symbol.upper(),
            "company_name": stock.name,
            "method": "DDM (Dividend Discount Model - Gordon Growth)",
            "current_dividend_yield": round(current_dividend_yield, 2),
            "avg_earnings_growth": round(avg_growth, 2),
            "scenarios": results,
            "note": "안정적인 배당 성장 기업에 적합한 모델입니다"
        }

    @staticmethod
    def comprehensive_valuation(db: Session, symbol: str) -> Dict:
        """
        종합 밸류에이션 분석
        - 멀티플 비교, DCF, DDM 통합
        """
        result = {
            "symbol": symbol.upper(),
            "timestamp": str(datetime.now())
        }

        # 1. 멀티플 비교
        try:
            result["multiple_comparison"] = ValuationAnalyzer.compare_multiples(db, symbol)
        except Exception as e:
            logger.error(f"Multiple comparison failed for {symbol}: {e}")
            result["multiple_comparison"] = {"error": str(e)}

        # 2. DCF
        try:
            result["dcf_valuation"] = ValuationAnalyzer.dcf_valuation(db, symbol)
        except Exception as e:
            logger.error(f"DCF valuation failed for {symbol}: {e}")
            result["dcf_valuation"] = {"error": str(e)}

        # 3. DDM
        try:
            result["ddm_valuation"] = ValuationAnalyzer.dividend_discount_model(db, symbol)
        except Exception as e:
            logger.error(f"DDM valuation failed for {symbol}: {e}")
            result["ddm_valuation"] = {"error": str(e)}

        # 종합 평가
        result["summary"] = ValuationAnalyzer._generate_summary(result)

        return result

    @staticmethod
    def _generate_summary(result: Dict) -> Dict:
        """종합 평가 요약 생성"""
        summary = {
            "valuations": [],
            "recommendation": ""
        }

        # 멀티플 비교 요약
        if "multiple_comparison" in result and "overall_valuation" in result["multiple_comparison"]:
            summary["valuations"].append({
                "method": "멀티플 비교",
                "result": result["multiple_comparison"]["overall_valuation"]
            })

        # DCF 요약 (중립 시나리오)
        if "dcf_valuation" in result and "scenarios" in result["dcf_valuation"]:
            neutral = result["dcf_valuation"]["scenarios"].get("중립적")
            if neutral and "upside_downside" in neutral:
                upside = neutral["upside_downside"]
                valuation = "저평가" if upside > 20 else "고평가" if upside < -20 else "적정 평가"
                summary["valuations"].append({
                    "method": "DCF (중립)",
                    "result": valuation,
                    "upside": upside
                })

        # DDM 요약 (중립 시나리오)
        if "ddm_valuation" in result and "scenarios" in result["ddm_valuation"]:
            neutral = result["ddm_valuation"]["scenarios"].get("중립적")
            if neutral and "upside_downside" in neutral:
                upside = neutral["upside_downside"]
                valuation = "저평가" if upside > 20 else "고평가" if upside < -20 else "적정 평가"
                summary["valuations"].append({
                    "method": "DDM (중립)",
                    "result": valuation,
                    "upside": upside
                })

        # 종합 추천
        undervalued_count = sum(1 for v in summary["valuations"] if v["result"] == "저평가")
        overvalued_count = sum(1 for v in summary["valuations"] if v["result"] == "고평가")

        if undervalued_count >= 2:
            summary["recommendation"] = "매수 검토"
        elif overvalued_count >= 2:
            summary["recommendation"] = "매도 검토"
        else:
            summary["recommendation"] = "중립 (추가 분석 필요)"

        return summary


from datetime import datetime
