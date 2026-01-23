# backend/app/services/report_generator.py

"""
종합 리포트 생성 모듈
- 재무 분석, 밸류에이션, 퀀트 분석 결과 통합
- 점수화 및 등급화 (매수/매도 권고 없음)
- 객관적 평가 및 비교 분석
"""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.services.financial_analyzer import FinancialAnalyzer
from app.services.valuation import ValuationAnalyzer
from app.services.quant_analyzer import QuantAnalyzer
from app.services.qualitative_analyzer import QualitativeAnalyzer

logger = logging.getLogger(__name__)


class ReportGenerator:
    """종합 리포트 생성 클래스"""

    # 평가 등급 기준
    RATING_LEVELS = {
        "excellent": {"min": 80, "label": "상위", "description": "상위 20%"},
        "good": {"min": 60, "label": "양호", "description": "상위 40%"},
        "average": {"min": 40, "label": "보통", "description": "중간 40%"},
        "below_average": {"min": 20, "label": "낮음", "description": "하위 40%"},
        "poor": {"min": 0, "label": "미흡", "description": "하위 20%"}
    }

    @staticmethod
    def _get_rating_from_score(score: float) -> Dict[str, str]:
        """
        점수를 등급으로 변환
        - 매수/매도 권고 없이 객관적 등급만 제공
        """
        if score >= 80:
            return {"level": "상위", "range": "상위 20%", "color": "#4caf50"}
        elif score >= 60:
            return {"level": "양호", "range": "상위 40%", "color": "#8bc34a"}
        elif score >= 40:
            return {"level": "보통", "range": "중간 40%", "color": "#ff9800"}
        elif score >= 20:
            return {"level": "낮음", "range": "하위 40%", "color": "#ff5722"}
        else:
            return {"level": "미흡", "range": "하위 20%", "color": "#f44336"}

    @staticmethod
    def _categorize_valuation(comparison_data: Dict) -> Dict[str, str]:
        """
        밸류에이션 결과를 범주화
        - "저평가/적정/고평가" 등급 (매수/매도 권고 없음)
        """
        if not comparison_data or "overall_valuation" not in comparison_data:
            return {"category": "데이터 부족", "description": "평가 불가"}

        valuation = comparison_data["overall_valuation"]

        if valuation == "저평가":
            return {
                "category": "업종 평균 대비 저평가",
                "description": "현재 주가가 업종 평균 멀티플 대비 낮은 수준",
                "color": "#4caf50"
            }
        elif valuation == "고평가":
            return {
                "category": "업종 평균 대비 고평가",
                "description": "현재 주가가 업종 평균 멀티플 대비 높은 수준",
                "color": "#f44336"
            }
        else:
            return {
                "category": "업종 평균 수준",
                "description": "현재 주가가 업종 평균과 유사한 수준",
                "color": "#ff9800"
            }

    @staticmethod
    def _categorize_financial_health(score: int) -> Dict[str, str]:
        """
        재무 건전성을 범주화
        """
        if score >= 70:
            return {
                "category": "재무 건전성 상위",
                "description": "높은 성장성, 수익성, 안정성을 보유",
                "tier": "상위",
                "color": "#4caf50"
            }
        elif score >= 50:
            return {
                "category": "재무 건전성 양호",
                "description": "평균 이상의 재무 지표",
                "tier": "중상위",
                "color": "#8bc34a"
            }
        elif score >= 30:
            return {
                "category": "재무 건전성 보통",
                "description": "평균적인 재무 지표",
                "tier": "중간",
                "color": "#ff9800"
            }
        else:
            return {
                "category": "재무 건전성 개선 필요",
                "description": "낮은 성장성 또는 높은 부채",
                "tier": "하위",
                "color": "#f44336"
            }

    @staticmethod
    def _categorize_risk_level(volatility: float, mdd: float, sharpe: float) -> Dict[str, str]:
        """
        리스크 수준을 범주화
        - 변동성, 최대낙폭, 샤프비율 종합
        """
        # 리스크 점수 계산 (0-100)
        risk_score = 0

        # 변동성 평가 (낮을수록 좋음)
        if volatility < 15:
            risk_score += 35
        elif volatility < 25:
            risk_score += 25
        elif volatility < 35:
            risk_score += 15
        else:
            risk_score += 5

        # MDD 평가 (낮을수록 좋음)
        if abs(mdd) < 10:
            risk_score += 35
        elif abs(mdd) < 20:
            risk_score += 25
        elif abs(mdd) < 30:
            risk_score += 15
        else:
            risk_score += 5

        # 샤프 비율 평가 (높을수록 좋음)
        if sharpe > 2:
            risk_score += 30
        elif sharpe > 1:
            risk_score += 20
        elif sharpe > 0:
            risk_score += 10

        # 범주화
        if risk_score >= 80:
            return {
                "category": "저위험",
                "description": "낮은 변동성, 제한적 낙폭, 높은 위험 대비 수익",
                "level": "1단계",
                "color": "#4caf50"
            }
        elif risk_score >= 60:
            return {
                "category": "중저위험",
                "description": "보통 수준의 변동성과 낙폭",
                "level": "2단계",
                "color": "#8bc34a"
            }
        elif risk_score >= 40:
            return {
                "category": "중위험",
                "description": "평균적인 변동성과 낙폭",
                "level": "3단계",
                "color": "#ff9800"
            }
        elif risk_score >= 20:
            return {
                "category": "중고위험",
                "description": "높은 변동성 또는 큰 낙폭",
                "level": "4단계",
                "color": "#ff5722"
            }
        else:
            return {
                "category": "고위험",
                "description": "매우 높은 변동성과 큰 낙폭",
                "level": "5단계",
                "color": "#f44336"
            }

    @staticmethod
    def _categorize_market_performance(alpha: float, beta: float) -> Dict[str, str]:
        """
        시장 대비 성과를 범주화
        """
        # 알파 기준
        if alpha > 5:
            alpha_desc = "시장 대비 높은 초과 수익"
        elif alpha > 0:
            alpha_desc = "시장 대비 양의 초과 수익"
        elif alpha > -5:
            alpha_desc = "시장과 유사한 성과"
        else:
            alpha_desc = "시장 대비 낮은 성과"

        # 베타 기준
        if beta > 1.2:
            beta_desc = "시장보다 높은 변동성 (공격적)"
        elif beta > 0.8:
            beta_desc = "시장과 유사한 변동성"
        else:
            beta_desc = "시장보다 낮은 변동성 (방어적)"

        # 종합 카테고리
        if alpha > 0 and beta > 1.0:
            category = "공격적 고성과"
        elif alpha > 0 and beta <= 1.0:
            category = "방어적 고성과"
        elif alpha <= 0 and beta > 1.0:
            category = "공격적 저성과"
        else:
            category = "방어적"

        return {
            "category": category,
            "alpha_description": alpha_desc,
            "beta_description": beta_desc,
            "alpha_value": alpha,
            "beta_value": beta
        }

    @staticmethod
    def _categorize_news_sentiment(sentiment_score: float) -> Dict[str, str]:
        """
        뉴스 감성 점수를 카테고리로 변환
        - 매수/매도 권고 없이 객관적 감성만 표시
        """
        if sentiment_score > 0.35:
            return {
                "category": "매우 긍정적",
                "description": "최근 뉴스가 매우 긍정적인 감성을 보이고 있습니다",
                "color": "#4caf50"
            }
        elif sentiment_score > 0.15:
            return {
                "category": "긍정적",
                "description": "최근 뉴스가 긍정적인 감성을 보이고 있습니다",
                "color": "#8bc34a"
            }
        elif sentiment_score > -0.15:
            return {
                "category": "중립적",
                "description": "최근 뉴스가 중립적인 감성을 보이고 있습니다",
                "color": "#ff9800"
            }
        elif sentiment_score > -0.35:
            return {
                "category": "부정적",
                "description": "최근 뉴스가 부정적인 감성을 보이고 있습니다",
                "color": "#ff5722"
            }
        else:
            return {
                "category": "매우 부정적",
                "description": "최근 뉴스가 매우 부정적인 감성을 보이고 있습니다",
                "color": "#f44336"
            }

    @staticmethod
    def generate_comprehensive_report(
        db: Session,
        symbol: str,
        market_symbol: str = "SPY",
        days: int = 252
    ) -> Dict:
        """
        종합 리포트 생성
        - 재무 분석, 밸류에이션, 퀀트 분석 결과 통합
        - 점수화 및 등급화 (매수/매도 권고 없음)
        """
        report = {
            "symbol": symbol.upper(),
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": days,
            "benchmark": market_symbol.upper(),
            "disclaimer": "본 리포트는 투자 권고가 아닌 객관적 분석 정보입니다. 투자 결정은 본인의 판단과 책임하에 이루어져야 합니다."
        }

        # 1. 재무 분석
        try:
            financial_score = FinancialAnalyzer.get_financial_score_v2(db, symbol)

            if financial_score and "success" in financial_score and financial_score["success"]:
                report["financial_analysis"] = {
                    "total_score": financial_score["total_score"],
                    "grade": financial_score["grade"],
                    "rating": financial_score["rating"],
                    "investment_style": financial_score.get("investment_style"),
                    "score_details": financial_score["score_details"],
                    "health_category": ReportGenerator._categorize_financial_health(
                        financial_score["total_score"]
                    )
                }
            else:
                report["financial_analysis"] = {"error": "재무 데이터 부족"}
        except Exception as e:
            logger.error(f"Financial analysis failed: {e}")
            report["financial_analysis"] = {"error": str(e)}

        # 2. 밸류에이션
        try:
            valuation = ValuationAnalyzer.comprehensive_valuation(db, symbol)

            if valuation:
                # 멀티플 비교
                if "multiple_comparison" in valuation:
                    report["valuation"] = {
                        "multiples": valuation["multiple_comparison"],
                        "category": ReportGenerator._categorize_valuation(
                            valuation["multiple_comparison"]
                        )
                    }

                # DCF 중립 시나리오
                if "dcf_valuation" in valuation and "scenarios" in valuation["dcf_valuation"]:
                    neutral_dcf = valuation["dcf_valuation"]["scenarios"].get("중립적")
                    if neutral_dcf and "upside_downside" in neutral_dcf:
                        report["valuation"]["dcf_neutral"] = {
                            "fair_value": neutral_dcf.get("fair_value_per_share"),
                            "current_price": neutral_dcf.get("current_price"),
                            "upside_downside": neutral_dcf.get("upside_downside")
                        }

                # 종합 평가
                if "summary" in valuation:
                    report["valuation"]["summary"] = valuation["summary"]
        except Exception as e:
            logger.error(f"Valuation analysis failed: {e}")
            report["valuation"] = {"error": str(e)}

        # 3. 퀀트/리스크 분석
        try:
            quant = QuantAnalyzer.comprehensive_quant_analysis(db, symbol, market_symbol, days)

            if quant and "error" not in quant:
                # 리스크 지표
                risk_metrics = quant.get("risk_metrics", {})
                volatility = risk_metrics.get("volatility", 0)
                mdd_data = risk_metrics.get("max_drawdown", {})
                mdd = mdd_data.get("max_drawdown", 0) if isinstance(mdd_data, dict) else 0
                sharpe_data = risk_metrics.get("sharpe_ratio", {})
                sharpe = sharpe_data.get("sharpe_ratio", 0) if isinstance(sharpe_data, dict) else 0

                report["risk_analysis"] = {
                    "volatility": volatility,
                    "max_drawdown": mdd,
                    "sharpe_ratio": sharpe,
                    "risk_category": ReportGenerator._categorize_risk_level(
                        volatility, mdd, sharpe
                    )
                }

                # 시장 대비 성과
                market_comp = quant.get("market_comparison", {})
                if market_comp:
                    beta_data = market_comp.get("beta", {})
                    alpha_data = market_comp.get("alpha", {})

                    if beta_data and alpha_data and "error" not in beta_data and "error" not in alpha_data:
                        beta = beta_data.get("beta", 1.0)
                        alpha = alpha_data.get("alpha", 0.0)

                        report["market_performance"] = ReportGenerator._categorize_market_performance(
                            alpha, beta
                        )

                # 기술적 신호
                tech_indicators = quant.get("technical_indicators", {})
                if tech_indicators:
                    signals = []

                    # 이동평균 신호
                    ma_data = tech_indicators.get("moving_averages", {})
                    if ma_data and "signal" in ma_data:
                        signals.append({
                            "indicator": "이동평균",
                            "signal": ma_data["signal"]
                        })

                    # RSI 신호
                    rsi_data = tech_indicators.get("rsi", {})
                    if rsi_data and "status" in rsi_data:
                        signals.append({
                            "indicator": "RSI",
                            "signal": rsi_data["status"],
                            "value": rsi_data.get("rsi")
                        })

                    # MACD 신호
                    macd_data = tech_indicators.get("macd", {})
                    if macd_data and "status" in macd_data:
                        signals.append({
                            "indicator": "MACD",
                            "signal": macd_data["status"]
                        })

                    report["technical_signals"] = signals
        except Exception as e:
            logger.error(f"Quant analysis failed: {e}")
            report["risk_analysis"] = {"error": str(e)}

        # 4. 뉴스 감성 분석 (Qualitative - News Sentiment)
        try:
            news_sentiment = QualitativeAnalyzer.get_comprehensive_news_analysis(symbol)

            if news_sentiment and "error" not in news_sentiment:
                report["news_sentiment"] = {
                    "sentiment": news_sentiment.get("sentiment", "중립"),
                    "sentiment_score": news_sentiment.get("sentiment_score", 0),
                    "positive_factors": news_sentiment.get("positive_factors", []),
                    "negative_factors": news_sentiment.get("negative_factors", []),
                    "key_issues": news_sentiment.get("key_issues", []),
                    "summary": news_sentiment.get("summary", ""),
                    "news_count": news_sentiment.get("news_count", 0),
                    "recent_news": news_sentiment.get("recent_news", [])[:3],  # 최근 3개만
                    "category": ReportGenerator._categorize_news_sentiment(
                        news_sentiment.get("sentiment_score", 0)
                    )
                }
        except Exception as e:
            logger.error(f"News sentiment analysis failed: {e}")
            report["news_sentiment"] = {"error": str(e), "sentiment": "중립"}

        # 5. 종합 평가 (Overall Assessment)
        report["overall_assessment"] = ReportGenerator._generate_overall_assessment(report)

        return report

    @staticmethod
    def _generate_overall_assessment(report: Dict) -> Dict:
        """
        종합 평가 생성
        - 각 분석 결과를 종합하여 객관적 평가
        """
        assessment = {
            "strengths": [],
            "concerns": [],
            "summary": ""
        }

        # 재무 분석 평가
        if "financial_analysis" in report and "total_score" in report["financial_analysis"]:
            score = report["financial_analysis"]["total_score"]
            category = report["financial_analysis"]["health_category"]["category"]

            if score >= 60:
                assessment["strengths"].append(f"재무 건전성: {category}")
            elif score < 40:
                assessment["concerns"].append(f"재무 건전성: {category}")

        # 밸류에이션 평가
        if "valuation" in report and "category" in report["valuation"]:
            val_category = report["valuation"]["category"]["category"]
            assessment["strengths"].append(f"밸류에이션: {val_category}")

        # 리스크 평가
        if "risk_analysis" in report and "risk_category" in report["risk_analysis"]:
            risk_cat = report["risk_analysis"]["risk_category"]

            if risk_cat["category"] in ["저위험", "중저위험"]:
                assessment["strengths"].append(f"리스크: {risk_cat['category']} ({risk_cat['level']})")
            elif risk_cat["category"] in ["고위험", "중고위험"]:
                assessment["concerns"].append(f"리스크: {risk_cat['category']} ({risk_cat['level']})")

        # 시장 성과 평가
        if "market_performance" in report:
            perf = report["market_performance"]
            if perf.get("alpha_value", 0) > 0:
                assessment["strengths"].append(f"시장 대비 성과: {perf['alpha_description']}")
            elif perf.get("alpha_value", 0) < -5:
                assessment["concerns"].append(f"시장 대비 성과: {perf['alpha_description']}")

        # 뉴스 감성 평가
        if "news_sentiment" in report and "category" in report["news_sentiment"]:
            sentiment = report["news_sentiment"]
            sentiment_cat = sentiment["category"]["category"]

            if sentiment_cat in ["매우 긍정적", "긍정적"]:
                assessment["strengths"].append(f"뉴스 감성: {sentiment_cat}")
            elif sentiment_cat in ["매우 부정적", "부정적"]:
                assessment["concerns"].append(f"뉴스 감성: {sentiment_cat}")

        # 요약 생성
        strength_count = len(assessment["strengths"])
        concern_count = len(assessment["concerns"])

        if strength_count > concern_count * 2:
            assessment["summary"] = "전반적으로 양호한 지표를 보이고 있습니다."
        elif concern_count > strength_count * 2:
            assessment["summary"] = "일부 지표에서 개선이 필요합니다."
        else:
            assessment["summary"] = "긍정적 요소와 개선 필요 요소가 혼재되어 있습니다."

        return assessment

    @staticmethod
    def generate_comparison_report(db: Session, symbols: List[str]) -> Dict:
        """
        여러 종목 비교 리포트
        - 최대 5개 종목까지 비교
        """
        if len(symbols) > 5:
            return {"error": "최대 5개 종목까지 비교 가능합니다"}

        comparison = {
            "symbols": [s.upper() for s in symbols],
            "generated_at": datetime.now().isoformat(),
            "stocks": []
        }

        for symbol in symbols:
            try:
                # 각 종목의 간략 리포트
                financial = FinancialAnalyzer.get_financial_score_v2(db, symbol.upper())
                valuation = ValuationAnalyzer.compare_multiples(db, symbol.upper())

                stock_data = {
                    "symbol": symbol.upper(),
                    "financial_score": financial.get("total_score") if financial and financial.get("success") else None,
                    "financial_grade": financial.get("grade") if financial and financial.get("success") else None,
                    "valuation": valuation.get("overall_valuation") if valuation else None,
                    "pe_ratio": valuation.get("pe_comparison", {}).get("current") if valuation else None,
                    "pb_ratio": valuation.get("pb_comparison", {}).get("current") if valuation else None
                }

                comparison["stocks"].append(stock_data)
            except Exception as e:
                logger.error(f"Comparison failed for {symbol}: {e}")
                comparison["stocks"].append({
                    "symbol": symbol.upper(),
                    "error": str(e)
                })

        return comparison
