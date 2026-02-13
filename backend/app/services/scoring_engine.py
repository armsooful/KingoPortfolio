# backend/app/services/scoring_engine.py

"""
Foresto Compass Score — 종합 투자 학습 점수 (0-100)

3개 기존 분석 서비스의 결과를 종합하여 단일 점수를 산출:
- FinancialAnalyzer.analyze_stock()   → 재무 점수 (30%)
- ValuationAnalyzer.compare_multiples() → 밸류에이션 점수 (20%)
- QuantAnalyzer.comprehensive_quant_analysis() → 기술 점수 (30%) + 리스크 점수 (20%)

⚠️ 교육 목적 참고 정보이며 투자 권유가 아닙니다.
"""

from typing import Dict, Optional, List, Tuple
from sqlalchemy.orm import Session
import logging

from app.services.financial_analyzer import FinancialAnalyzer
from app.services.valuation import ValuationAnalyzer
from app.services.quant_analyzer import QuantAnalyzer

logger = logging.getLogger(__name__)

DISCLAIMER = "교육 목적 참고 정보이며 투자 권유가 아닙니다"

GRADE_TABLE = [
    (90, "S",  "최상위 — 매우 우수"),
    (80, "A+", "상위 — 우수"),
    (70, "A",  "양호"),
    (60, "B+", "보통 이상"),
    (50, "B",  "보통"),
    (40, "C+", "주의"),
    (30, "C",  "약세"),
    (20, "D",  "위험"),
    (0,  "F",  "매우 위험"),
]


class ScoringEngine:
    """Foresto Compass Score — 종합 투자 학습 점수 (0-100)"""

    WEIGHTS = {
        "financial": 0.30,
        "valuation": 0.20,
        "technical": 0.30,
        "risk": 0.20,
    }

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_compass_score(db: Session, ticker: str) -> Dict:
        """메인 진입점 — 4개 카테고리 점수를 집계하여 종합 점수 반환"""
        try:
            # ── 1. 3개 분석기 호출 ──
            financial_result = None
            valuation_result = None
            quant_result = None

            try:
                financial_result = FinancialAnalyzer.analyze_stock(db, ticker)
                if not financial_result.get("success"):
                    financial_result = None
            except Exception as e:
                logger.warning(f"Financial analysis failed for {ticker}: {e}")

            try:
                valuation_result = ValuationAnalyzer.compare_multiples(db, ticker)
            except Exception as e:
                logger.warning(f"Valuation analysis failed for {ticker}: {e}")

            try:
                quant_result = QuantAnalyzer.comprehensive_quant_analysis(db, ticker)
                if "error" in quant_result:
                    quant_result = None
            except Exception as e:
                logger.warning(f"Quant analysis failed for {ticker}: {e}")

            # ── 2. 각 카테고리별 sub-score 계산 ──
            categories = {}
            data_availability = {}

            # Financial (30%)
            fin_score = ScoringEngine._score_financial(financial_result)
            categories["financial"] = fin_score
            data_availability["financial"] = fin_score is not None

            # Valuation (20%)
            val_score = ScoringEngine._score_valuation(valuation_result)
            categories["valuation"] = val_score
            data_availability["valuation"] = val_score is not None

            # Technical (30%)
            tech_score = ScoringEngine._score_technical(quant_result)
            categories["technical"] = tech_score
            data_availability["technical"] = tech_score is not None

            # Risk (20%)
            risk_score = ScoringEngine._score_risk(quant_result)
            categories["risk"] = risk_score
            data_availability["risk"] = risk_score is not None

            # ── 3. 가중 평균 → compass_score ──
            available = {k: v for k, v in categories.items() if v is not None}
            if not available:
                return {"error": "분석 가능한 데이터가 없습니다"}

            # 가중치 재분배 (N/A 카테고리 제외)
            weights = ScoringEngine.WEIGHTS
            total_weight = sum(weights[k] for k in available)
            compass_score = sum(
                available[k]["score"] * (weights[k] / total_weight)
                for k in available
            )
            compass_score = round(compass_score, 1)

            # ── 4. 등급 판정 + 요약 ──
            grade, grade_desc = ScoringEngine._determine_grade(compass_score)

            # 카테고리별 등급 부여
            for cat_data in categories.values():
                if cat_data is not None:
                    cat_grade, _ = ScoringEngine._determine_grade(cat_data["score"])
                    cat_data["grade"] = cat_grade

            # 카테고리에 가중치 라벨 추가
            weight_labels = {"financial": "30%", "valuation": "20%", "technical": "30%", "risk": "20%"}
            for k, cat_data in categories.items():
                if cat_data is not None:
                    cat_data["weight"] = weight_labels[k]

            # 회사명 추출
            company_name = None
            if financial_result:
                company_name = financial_result.get("company_name")
            if not company_name and valuation_result:
                company_name = valuation_result.get("company_name")

            summary = ScoringEngine._generate_summary(categories, data_availability)

            commentary = ScoringEngine._generate_commentary(
                ticker=ticker,
                company_name=company_name,
                compass_score=compass_score,
                grade=grade,
                categories=categories,
                financial_result=financial_result,
                valuation_result=valuation_result,
                quant_result=quant_result,
            )

            return {
                "ticker": ticker,
                "company_name": company_name,
                "compass_score": compass_score,
                "grade": grade,
                "grade_description": grade_desc,
                "summary": summary,
                "commentary": commentary,
                "categories": {
                    k: v if v is not None else {"score": None, "weight": weight_labels[k], "grade": "N/A", "details": {}, "reason": "데이터 부족"}
                    for k, v in categories.items()
                },
                "data_availability": data_availability,
                "disclaimer": DISCLAIMER,
            }

        except Exception as e:
            logger.error(f"Compass score calculation failed for {ticker}: {e}")
            return {"error": f"Compass Score 계산 실패: {str(e)}"}

    # ------------------------------------------------------------------
    # Category scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_financial(analysis: Optional[Dict]) -> Optional[Dict]:
        """재무 점수 계산 (0-100)

        | 지표       | 배점 | 기준                                    |
        |-----------|------|-----------------------------------------|
        | ROE       | 30   | ≥15%→30, ≥10%→24, ≥5%→16, ≥0%→8, <0→0  |
        | 영업이익률 | 25   | ≥20%→25, ≥10%→20, ≥5%→13, ≥0%→6, <0→0  |
        | 부채비율   | 25   | ≤50%→25, ≤100%→20, ≤200%→13, ≤400%→6   |
        | 순이익률   | 20   | ≥15%→20, ≥10%→16, ≥5%→10, ≥0%→4, <0→0  |
        """
        if analysis is None:
            return None

        scoring_items: List[Tuple[str, float, float]] = []  # (name, max_points, earned)

        # ROE
        roe = analysis.get("profitability", {}).get("roe")
        if roe is not None:
            if roe >= 15:
                pts = 30
            elif roe >= 10:
                pts = 24
            elif roe >= 5:
                pts = 16
            elif roe >= 0:
                pts = 8
            else:
                pts = 0
            scoring_items.append(("ROE", 30, pts))

        # 영업이익률
        op_margin = analysis.get("profit_margins", {}).get("operating_margin")
        if op_margin is not None:
            if op_margin >= 20:
                pts = 25
            elif op_margin >= 10:
                pts = 20
            elif op_margin >= 5:
                pts = 13
            elif op_margin >= 0:
                pts = 6
            else:
                pts = 0
            scoring_items.append(("영업이익률", 25, pts))

        # 부채비율
        debt_ratio = analysis.get("financial_health", {}).get("debt_to_equity")
        if debt_ratio is not None:
            if debt_ratio <= 50:
                pts = 25
            elif debt_ratio <= 100:
                pts = 20
            elif debt_ratio <= 200:
                pts = 13
            elif debt_ratio <= 400:
                pts = 6
            else:
                pts = 0
            scoring_items.append(("부채비율", 25, pts))

        # 순이익률
        net_margin = analysis.get("profit_margins", {}).get("net_margin")
        if net_margin is not None:
            if net_margin >= 15:
                pts = 20
            elif net_margin >= 10:
                pts = 16
            elif net_margin >= 5:
                pts = 10
            elif net_margin >= 0:
                pts = 4
            else:
                pts = 0
            scoring_items.append(("순이익률", 20, pts))

        if not scoring_items:
            return None

        # 재정규화: available 배점 기준 100점 환산
        total_max = sum(item[1] for item in scoring_items)
        total_earned = sum(item[2] for item in scoring_items)
        score = round((total_earned / total_max) * 100, 1) if total_max > 0 else 0

        return {
            "score": score,
            "details": {name: {"max": mx, "earned": earned} for name, mx, earned in scoring_items},
        }

    @staticmethod
    def _score_valuation(multiples: Optional[Dict]) -> Optional[Dict]:
        """밸류에이션 점수 계산 (0-100)

        | 지표        | 배점 | 기준                                  |
        |------------|------|---------------------------------------|
        | PER vs 업종 | 50   | 저평가→50, 적정→30, 고평가→10          |
        | PBR vs 업종 | 50   | 저평가→50, 적정→30, 고평가→10          |
        """
        if multiples is None:
            return None

        scoring_items: List[Tuple[str, float, float]] = []

        # PER
        pe_comp = multiples.get("pe_comparison")
        if pe_comp and "vs_industry" in pe_comp:
            pct = pe_comp["vs_industry"]
            if pct < -20:
                pts = 50   # 저평가
            elif pct <= 20:
                pts = 30   # 적정
            else:
                pts = 10   # 고평가
            scoring_items.append(("PER vs 업종", 50, pts))

        # PBR
        pb_comp = multiples.get("pb_comparison")
        if pb_comp and "vs_industry" in pb_comp:
            pct = pb_comp["vs_industry"]
            if pct < -20:
                pts = 50
            elif pct <= 20:
                pts = 30
            else:
                pts = 10
            scoring_items.append(("PBR vs 업종", 50, pts))

        if not scoring_items:
            return None

        total_max = sum(item[1] for item in scoring_items)
        total_earned = sum(item[2] for item in scoring_items)
        score = round((total_earned / total_max) * 100, 1) if total_max > 0 else 0

        return {
            "score": score,
            "details": {name: {"max": mx, "earned": earned} for name, mx, earned in scoring_items},
        }

    @staticmethod
    def _score_technical(quant: Optional[Dict]) -> Optional[Dict]:
        """기술 점수 계산 (0-100)

        추세 (40점): MA정배열 20 + ADX 20
        모멘텀 (40점): RSI 15 + Stochastic 10 + MACD 15
        위치/거래량 (20점): 52주위치 10 + OBV 10
        """
        if quant is None:
            return None

        indicators = quant.get("technical_indicators", {})
        if not indicators:
            return None

        scoring_items: List[Tuple[str, float, float]] = []

        # ── 추세 (40점) ──

        # MA 정배열 (20점)
        ma_align = indicators.get("ma_alignment", {})
        if "alignment" in ma_align:
            alignment = ma_align["alignment"]
            if alignment == "정배열":
                pts = 20
            elif alignment == "혼조":
                pts = 10
            else:  # 역배열
                pts = 0
            scoring_items.append(("MA 정배열", 20, pts))

        # ADX (20점)
        adx_data = indicators.get("adx", {})
        if "adx" in adx_data:
            adx_val = adx_data["adx"]
            direction = adx_data.get("direction", "")
            is_uptrend = "상승" in direction

            if adx_val > 25 and is_uptrend:
                pts = 20   # 강추세 + 상승
            elif adx_val > 25 and not is_uptrend:
                pts = 8    # 강추세 + 하락
            elif adx_val > 20:
                pts = 12   # 약추세
            else:
                pts = 5    # 횡보
            scoring_items.append(("ADX", 20, pts))

        # ── 모멘텀 (40점) ──

        # RSI (15점)
        rsi_data = indicators.get("rsi", {})
        if "rsi" in rsi_data:
            rsi = rsi_data["rsi"]
            if 40 <= rsi <= 60:
                pts = 15   # 중립 (안정)
            elif 30 <= rsi < 40 or 60 < rsi <= 70:
                pts = 10
            elif rsi < 30:
                pts = 12   # 과매도 (반등 가능성)
            else:  # > 70
                pts = 5    # 과매수
            scoring_items.append(("RSI", 15, pts))

        # Stochastic (10점)
        stoch = indicators.get("stochastic", {})
        if "k" in stoch:
            k = stoch["k"]
            if 20 <= k <= 80:
                pts = 10   # 중립
            elif k < 20:
                pts = 8    # 과매도
            else:  # > 80
                pts = 3    # 과매수
            scoring_items.append(("Stochastic", 10, pts))

        # MACD (15점)
        macd_data = indicators.get("macd", {})
        if "status" in macd_data:
            status = macd_data["status"]
            if "골든크로스" in status:
                pts = 15
            elif "상승" in status:
                pts = 12
            elif "하락" in status:
                pts = 5
            else:  # 데드크로스
                pts = 2
            scoring_items.append(("MACD", 15, pts))

        # ── 위치/거래량 (20점) ──

        # 52주 위치 (10점)
        w52 = indicators.get("week52_position", {})
        if "position" in w52:
            pos = w52["position"]
            if 40 <= pos <= 70:
                pts = 10
            elif 20 <= pos < 40 or 70 < pos <= 80:
                pts = 7
            elif pos < 20:
                pts = 5    # 저점
            else:  # > 80
                pts = 4    # 고점
            scoring_items.append(("52주 위치", 10, pts))

        # OBV (10점)
        obv_data = indicators.get("obv", {})
        if "trend" in obv_data and obv_data["trend"] != "데이터 부족":
            trend = obv_data["trend"]
            if "상승" in trend:
                pts = 10
            elif "중립" in trend:
                pts = 5
            else:  # 하락
                pts = 2
            scoring_items.append(("OBV 추세", 10, pts))

        if not scoring_items:
            return None

        total_max = sum(item[1] for item in scoring_items)
        total_earned = sum(item[2] for item in scoring_items)
        score = round((total_earned / total_max) * 100, 1) if total_max > 0 else 0

        return {
            "score": score,
            "details": {name: {"max": mx, "earned": earned} for name, mx, earned in scoring_items},
        }

    @staticmethod
    def _score_risk(quant: Optional[Dict]) -> Optional[Dict]:
        """리스크 점수 계산 (0-100, 높을수록 리스크 낮음 = 좋음)

        | 지표        | 배점 | 기준                                         |
        |------------|------|----------------------------------------------|
        | 변동성(연율) | 35   | <20%→35, <30%→28, <50%→18, <80%→8, ≥80%→0   |
        | MDD        | 35   | >-10%→35, >-20%→28, >-30%→18, >-50%→8, ≤-50%→0 |
        | 샤프비율    | 30   | >2.0→30, >1.0→24, >0→15, >-1.0→6, ≤-1.0→0  |
        """
        if quant is None:
            return None

        risk = quant.get("risk_metrics", {})
        if not risk:
            return None

        scoring_items: List[Tuple[str, float, float]] = []

        # 변동성 (연율화)
        volatility = risk.get("volatility")
        if volatility is not None and not isinstance(volatility, dict):
            if volatility < 20:
                pts = 35
            elif volatility < 30:
                pts = 28
            elif volatility < 50:
                pts = 18
            elif volatility < 80:
                pts = 8
            else:
                pts = 0
            scoring_items.append(("변동성(연율)", 35, pts))

        # MDD
        mdd_data = risk.get("max_drawdown", {})
        if isinstance(mdd_data, dict) and "max_drawdown" in mdd_data:
            mdd = mdd_data["max_drawdown"]  # 음수
            if mdd > -10:
                pts = 35
            elif mdd > -20:
                pts = 28
            elif mdd > -30:
                pts = 18
            elif mdd > -50:
                pts = 8
            else:
                pts = 0
            scoring_items.append(("MDD", 35, pts))

        # 샤프비율
        sharpe_data = risk.get("sharpe_ratio", {})
        if isinstance(sharpe_data, dict) and "sharpe_ratio" in sharpe_data:
            sharpe = sharpe_data["sharpe_ratio"]
            if sharpe > 2.0:
                pts = 30
            elif sharpe > 1.0:
                pts = 24
            elif sharpe > 0:
                pts = 15
            elif sharpe > -1.0:
                pts = 6
            else:
                pts = 0
            scoring_items.append(("샤프비율", 30, pts))

        if not scoring_items:
            return None

        total_max = sum(item[1] for item in scoring_items)
        total_earned = sum(item[2] for item in scoring_items)
        score = round((total_earned / total_max) * 100, 1) if total_max > 0 else 0

        return {
            "score": score,
            "details": {name: {"max": mx, "earned": earned} for name, mx, earned in scoring_items},
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_grade(score: float) -> Tuple[str, str]:
        """점수 → 등급 + 설명"""
        for threshold, grade, desc in GRADE_TABLE:
            if score >= threshold:
                return grade, desc
        return "F", "매우 위험"

    @staticmethod
    def _generate_commentary(
        ticker: str,
        company_name: Optional[str],
        compass_score: float,
        grade: str,
        categories: Dict,
        financial_result: Optional[Dict],
        valuation_result: Optional[Dict],
        quant_result: Optional[Dict],
    ) -> str:
        """지표 값을 참조하는 3~5문장 한국어 해설 자동 생성"""
        name = company_name or ticker
        parts = [f"{name}({ticker})의 Compass Score는 {compass_score}점({grade}등급)입니다."]

        # ── 재무 ──
        fin = categories.get("financial")
        if fin and fin.get("score") is not None and financial_result:
            roe = financial_result.get("profitability", {}).get("roe")
            op_margin = financial_result.get("profit_margins", {}).get("operating_margin")
            debt = financial_result.get("financial_health", {}).get("debt_to_equity")
            metrics = []
            if roe is not None:
                metrics.append(f"ROE {roe:.1f}%")
            if op_margin is not None:
                metrics.append(f"영업이익률 {op_margin:.1f}%")
            if debt is not None:
                metrics.append(f"부채비율 {debt:.0f}%")
            score = fin["score"]
            if score >= 70:
                desc = "재무 건전성이 우수하며"
            elif score >= 50:
                desc = "재무 상태가 양호하며"
            else:
                desc = "재무 개선이 필요하며"
            if metrics:
                parts.append(f"{desc}({', '.join(metrics)}),")

        # ── 밸류에이션 ──
        val = categories.get("valuation")
        if val and val.get("score") is not None and valuation_result:
            pe_comp = valuation_result.get("pe_comparison") or {}
            pb_comp = valuation_result.get("pb_comparison") or {}
            pe_vs = pe_comp.get("vs_industry")
            pb_vs = pb_comp.get("vs_industry")
            score = val["score"]
            if score >= 70:
                val_desc = "저평가 매력이 있습니다"
            elif score >= 50:
                val_desc = "적정 수준의 밸류에이션입니다"
            else:
                val_desc = "고평가 구간에 위치해 있습니다"
            detail_parts = []
            if pe_vs is not None:
                direction = "낮아" if pe_vs < 0 else "높아"
                detail_parts.append(f"업종 대비 PER이 {abs(pe_vs):.0f}% {direction}")
            if pb_vs is not None:
                direction = "낮아" if pb_vs < 0 else "높아"
                detail_parts.append(f"PBR이 {abs(pb_vs):.0f}% {direction}")
            if detail_parts:
                parts.append(f"{' '.join(detail_parts)} {val_desc}.")
            else:
                parts.append(f"{val_desc}.")

        # ── 기술 ──
        tech = categories.get("technical")
        if tech and tech.get("score") is not None and quant_result:
            indicators = quant_result.get("technical_indicators", {})
            tech_details = []
            ma_align = indicators.get("ma_alignment", {})
            if "alignment" in ma_align:
                tech_details.append(f"MA {ma_align['alignment']}")
            adx_data = indicators.get("adx", {})
            if "adx" in adx_data:
                tech_details.append(f"ADX {adx_data['adx']:.0f}")
            rsi_data = indicators.get("rsi", {})
            if "rsi" in rsi_data:
                rsi = rsi_data["rsi"]
                if rsi > 70:
                    tech_details.append(f"RSI {rsi:.0f}(과매수)")
                elif rsi < 30:
                    tech_details.append(f"RSI {rsi:.0f}(과매도)")
                else:
                    tech_details.append(f"RSI {rsi:.0f}")
            macd_data = indicators.get("macd", {})
            if "status" in macd_data:
                tech_details.append(f"MACD {macd_data['status']}")
            score = tech["score"]
            if score >= 70:
                trend = "강한 상승 추세가 확인됩니다"
            elif score >= 50:
                trend = "보합세를 보이고 있습니다"
            else:
                trend = "약세 흐름이 나타나고 있습니다"
            if tech_details:
                parts.append(f"기술적으로 {' + '.join(tech_details)}로 {trend}.")
            else:
                parts.append(f"기술적으로 {trend}.")

        # ── 리스크 ──
        risk = categories.get("risk")
        if risk and risk.get("score") is not None and quant_result:
            risk_metrics = quant_result.get("risk_metrics", {})
            risk_details = []
            vol = risk_metrics.get("volatility")
            if vol is not None and not isinstance(vol, dict):
                risk_details.append(f"연율 변동성 {vol:.1f}%")
            mdd_data = risk_metrics.get("max_drawdown", {})
            if isinstance(mdd_data, dict) and "max_drawdown" in mdd_data:
                risk_details.append(f"MDD {mdd_data['max_drawdown']:.1f}%")
            sharpe_data = risk_metrics.get("sharpe_ratio", {})
            if isinstance(sharpe_data, dict) and "sharpe_ratio" in sharpe_data:
                risk_details.append(f"샤프비율 {sharpe_data['sharpe_ratio']:.2f}")
            score = risk["score"]
            if score >= 70:
                risk_desc = "리스크는 안정적 수준입니다"
            elif score >= 50:
                risk_desc = "리스크는 보통 수준입니다"
            else:
                risk_desc = "리스크 관리에 주의가 필요합니다"
            if risk_details:
                parts.append(f"{', '.join(risk_details)}로 {risk_desc}.")
            else:
                parts.append(f"{risk_desc}.")

        return " ".join(parts)

    @staticmethod
    def _generate_summary(categories: Dict, availability: Dict) -> str:
        """각 카테고리 핵심 시그널 조합으로 요약 문장 생성"""
        signals = []

        # 재무
        fin = categories.get("financial")
        if fin and fin.get("score") is not None:
            s = fin["score"]
            if s >= 70:
                signals.append("우량 재무")
            elif s >= 50:
                signals.append("양호한 재무")
            else:
                signals.append("재무 개선 필요")

        # 밸류에이션
        val = categories.get("valuation")
        if val and val.get("score") is not None:
            s = val["score"]
            if s >= 70:
                signals.append("저평가 매력")
            elif s >= 50:
                signals.append("적정 밸류에이션")
            else:
                signals.append("고평가 주의")

        # 기술
        tech = categories.get("technical")
        if tech and tech.get("score") is not None:
            s = tech["score"]
            if s >= 70:
                signals.append("강한 상승 추세")
            elif s >= 50:
                signals.append("보합 추세")
            else:
                signals.append("약세 추세")

        # 리스크
        risk = categories.get("risk")
        if risk and risk.get("score") is not None:
            s = risk["score"]
            if s >= 70:
                signals.append("안정적 리스크")
            elif s >= 50:
                signals.append("보통 리스크")
            else:
                signals.append("높은 리스크")

        if not signals:
            return "분석 데이터 부족"

        return " + ".join(signals)
