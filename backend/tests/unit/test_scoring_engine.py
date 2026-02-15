"""
ScoringEngine 단위 테스트 — 순수 로직 (DB 불필요)

_score_financial, _score_valuation, _score_technical, _score_risk,
_determine_grade, _generate_summary, _generate_commentary 정적 메서드를 dict 입출력으로 테스트.
calculate_compass_score는 3개 분석기를 mock하여 오케스트레이션 테스트.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.scoring_engine import ScoringEngine, GRADE_TABLE


# ============================================================================
# _determine_grade
# ============================================================================

@pytest.mark.unit
class TestDetermineGrade:
    """등급 판정 경계값 테스트"""

    @pytest.mark.parametrize("score,expected_grade", [
        (100, "S"), (95, "S"), (90, "S"),   # S: ≥90
        (89.9, "A+"), (85, "A+"), (80, "A+"),  # A+: ≥80
        (79, "A"), (75, "A"), (70, "A"),     # A: ≥70
        (69, "B+"), (65, "B+"), (60, "B+"),  # B+: ≥60
        (59, "B"), (55, "B"), (50, "B"),     # B: ≥50
        (49, "C+"), (45, "C+"), (40, "C+"), # C+: ≥40
        (39, "C"), (35, "C"), (30, "C"),     # C: ≥30
        (29, "D"), (25, "D"), (20, "D"),     # D: ≥20
        (19, "F"), (10, "F"), (0, "F"),      # F: <20
    ])
    def test_grade_boundaries(self, score, expected_grade):
        grade, desc = ScoringEngine._determine_grade(score)
        assert grade == expected_grade, f"score={score} → expected {expected_grade}, got {grade}"


# ============================================================================
# _score_financial
# ============================================================================

@pytest.mark.unit
class TestScoreFinancial:
    """재무 점수 계산 테스트"""

    def test_none_input(self):
        """None 입력 → None 반환"""
        assert ScoringEngine._score_financial(None) is None

    def test_empty_analysis(self):
        """빈 분석 결과 → None (scoring_items 없음)"""
        result = ScoringEngine._score_financial({})
        assert result is None

    def test_perfect_score(self):
        """모든 지표 최상위 구간 → 100점"""
        analysis = {
            "profitability": {"roe": 20},
            "profit_margins": {"operating_margin": 25, "net_margin": 18},
            "financial_health": {"debt_to_equity": 30},
        }
        result = ScoringEngine._score_financial(analysis)
        assert result is not None
        assert result["score"] == 100.0

    def test_worst_score(self):
        """모든 지표 최하위 구간 → 0점"""
        analysis = {
            "profitability": {"roe": -5},
            "profit_margins": {"operating_margin": -3, "net_margin": -2},
            "financial_health": {"debt_to_equity": 500},
        }
        result = ScoringEngine._score_financial(analysis)
        assert result is not None
        assert result["score"] == 0.0

    def test_roe_tiers(self):
        """ROE 구간별 점수 (30점 배점)"""
        tiers = [
            (15, 30), (10, 24), (5, 16), (0, 8), (-1, 0),
        ]
        for roe_val, expected_pts in tiers:
            analysis = {"profitability": {"roe": roe_val}}
            result = ScoringEngine._score_financial(analysis)
            assert result["details"]["ROE"]["earned"] == expected_pts, \
                f"ROE={roe_val} → expected {expected_pts}, got {result['details']['ROE']['earned']}"

    def test_operating_margin_tiers(self):
        """영업이익률 구간별 점수 (25점 배점)"""
        tiers = [
            (20, 25), (10, 20), (5, 13), (0, 6), (-1, 0),
        ]
        for val, expected_pts in tiers:
            analysis = {"profit_margins": {"operating_margin": val}}
            result = ScoringEngine._score_financial(analysis)
            assert result["details"]["영업이익률"]["earned"] == expected_pts

    def test_debt_ratio_tiers(self):
        """부채비율 구간별 점수 (25점 배점)"""
        tiers = [
            (50, 25), (100, 20), (200, 13), (400, 6), (401, 0),
        ]
        for val, expected_pts in tiers:
            analysis = {"financial_health": {"debt_to_equity": val}}
            result = ScoringEngine._score_financial(analysis)
            assert result["details"]["부채비율"]["earned"] == expected_pts

    def test_net_margin_tiers(self):
        """순이익률 구간별 점수 (20점 배점)"""
        tiers = [
            (15, 20), (10, 16), (5, 10), (0, 4), (-1, 0),
        ]
        for val, expected_pts in tiers:
            analysis = {"profit_margins": {"net_margin": val}}
            result = ScoringEngine._score_financial(analysis)
            assert result["details"]["순이익률"]["earned"] == expected_pts

    def test_partial_data_normalization(self):
        """일부 지표만 있으면 available 배점 기준 100점 환산"""
        analysis = {"profitability": {"roe": 15}}  # ROE만 30/30 → 100점
        result = ScoringEngine._score_financial(analysis)
        assert result["score"] == 100.0

    def test_mixed_score(self):
        """중간 구간 조합 → 점수 범위 확인"""
        analysis = {
            "profitability": {"roe": 12},          # 24/30
            "profit_margins": {"operating_margin": 15, "net_margin": 8},  # 20/25, 10/20
            "financial_health": {"debt_to_equity": 150},  # 13/25
        }
        result = ScoringEngine._score_financial(analysis)
        # (24 + 20 + 13 + 10) / (30 + 25 + 25 + 20) * 100 = 67/100 = 67.0
        assert result["score"] == 67.0


# ============================================================================
# _score_valuation
# ============================================================================

@pytest.mark.unit
class TestScoreValuation:
    """밸류에이션 점수 계산 테스트"""

    def test_none_input(self):
        assert ScoringEngine._score_valuation(None) is None

    def test_empty_multiples(self):
        assert ScoringEngine._score_valuation({}) is None

    def test_undervalued(self):
        """PER/PBR 모두 저평가 → 100점"""
        multiples = {
            "pe_comparison": {"vs_industry": -30},
            "pb_comparison": {"vs_industry": -25},
        }
        result = ScoringEngine._score_valuation(multiples)
        assert result["score"] == 100.0

    def test_overvalued(self):
        """PER/PBR 모두 고평가 → 20점"""
        multiples = {
            "pe_comparison": {"vs_industry": 50},
            "pb_comparison": {"vs_industry": 40},
        }
        result = ScoringEngine._score_valuation(multiples)
        assert result["score"] == 20.0  # (10+10)/(50+50)*100

    def test_fair_value(self):
        """적정 범위 → 60점"""
        multiples = {
            "pe_comparison": {"vs_industry": 0},
            "pb_comparison": {"vs_industry": 10},
        }
        result = ScoringEngine._score_valuation(multiples)
        assert result["score"] == 60.0  # (30+30)/100*100

    def test_per_only(self):
        """PER만 있을 경우 정규화"""
        multiples = {
            "pe_comparison": {"vs_industry": -30},
        }
        result = ScoringEngine._score_valuation(multiples)
        assert result["score"] == 100.0  # 50/50*100

    def test_per_threshold_boundary(self):
        """PER vs_industry 경계값 테스트"""
        # -20 is boundary: pct <= 20 → 적정(30점)
        multiples = {"pe_comparison": {"vs_industry": -20}}
        result = ScoringEngine._score_valuation(multiples)
        assert result["details"]["PER vs 업종"]["earned"] == 30

        # -21 → 저평가(50점)
        multiples = {"pe_comparison": {"vs_industry": -21}}
        result = ScoringEngine._score_valuation(multiples)
        assert result["details"]["PER vs 업종"]["earned"] == 50


# ============================================================================
# _score_technical
# ============================================================================

@pytest.mark.unit
class TestScoreTechnical:
    """기술 점수 계산 테스트"""

    def test_none_input(self):
        assert ScoringEngine._score_technical(None) is None

    def test_empty_indicators(self):
        assert ScoringEngine._score_technical({}) is None
        assert ScoringEngine._score_technical({"technical_indicators": {}}) is None

    def test_full_bullish(self):
        """모든 지표 강세 → 높은 점수"""
        quant = {
            "technical_indicators": {
                "ma_alignment": {"alignment": "정배열"},
                "adx": {"adx": 30, "direction": "상승 추세"},
                "rsi": {"rsi": 50},
                "stochastic": {"k": 50},
                "macd": {"status": "골든크로스 감지"},
                "week52_position": {"position": 55},
                "obv": {"trend": "상승"},
            }
        }
        result = ScoringEngine._score_technical(quant)
        assert result["score"] >= 90

    def test_full_bearish(self):
        """모든 지표 약세 → 낮은 점수"""
        quant = {
            "technical_indicators": {
                "ma_alignment": {"alignment": "역배열"},
                "adx": {"adx": 30, "direction": "하락 추세"},
                "rsi": {"rsi": 75},
                "stochastic": {"k": 85},
                "macd": {"status": "데드크로스"},
                "week52_position": {"position": 90},
                "obv": {"trend": "하락"},
            }
        }
        result = ScoringEngine._score_technical(quant)
        assert result["score"] <= 30

    def test_ma_alignment_scoring(self):
        """MA 정배열/혼조/역배열 점수"""
        for alignment, expected in [("정배열", 20), ("혼조", 10), ("역배열", 0)]:
            quant = {"technical_indicators": {"ma_alignment": {"alignment": alignment}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["MA 정배열"]["earned"] == expected

    def test_rsi_zones(self):
        """RSI 구간별 점수"""
        cases = [
            (50, 15),   # 40-60: 중립
            (35, 10),   # 30-40
            (65, 10),   # 60-70
            (25, 12),   # <30: 과매도
            (75, 5),    # >70: 과매수
        ]
        for rsi_val, expected in cases:
            quant = {"technical_indicators": {"rsi": {"rsi": rsi_val}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["RSI"]["earned"] == expected, \
                f"RSI={rsi_val} → expected {expected}"

    def test_adx_scenarios(self):
        """ADX + direction 조합별 점수"""
        cases = [
            (30, "상승 추세", 20),  # 강추세 + 상승
            (30, "하락 추세", 8),   # 강추세 + 하락
            (22, "상승 추세", 12),  # 약추세
            (15, "횡보", 5),        # 횡보
        ]
        for adx_val, direction, expected in cases:
            quant = {"technical_indicators": {"adx": {"adx": adx_val, "direction": direction}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["ADX"]["earned"] == expected

    def test_obv_data_insufficient(self):
        """OBV 데이터 부족 → 무시"""
        quant = {"technical_indicators": {"obv": {"trend": "데이터 부족"}}}
        result = ScoringEngine._score_technical(quant)
        assert result is None  # scoring_items가 빈 리스트


# ============================================================================
# _score_risk
# ============================================================================

@pytest.mark.unit
class TestScoreRisk:
    """리스크 점수 계산 테스트"""

    def test_none_input(self):
        assert ScoringEngine._score_risk(None) is None

    def test_empty_metrics(self):
        assert ScoringEngine._score_risk({}) is None
        assert ScoringEngine._score_risk({"risk_metrics": {}}) is None

    def test_low_risk(self):
        """낮은 리스크 → 높은 점수"""
        quant = {
            "risk_metrics": {
                "volatility": 15,
                "max_drawdown": {"max_drawdown": -5},
                "sharpe_ratio": {"sharpe_ratio": 2.5},
            }
        }
        result = ScoringEngine._score_risk(quant)
        assert result["score"] == 100.0

    def test_high_risk(self):
        """높은 리스크 → 0점"""
        quant = {
            "risk_metrics": {
                "volatility": 90,
                "max_drawdown": {"max_drawdown": -60},
                "sharpe_ratio": {"sharpe_ratio": -1.5},
            }
        }
        result = ScoringEngine._score_risk(quant)
        assert result["score"] == 0.0

    def test_volatility_tiers(self):
        """변동성 구간별 점수 (35점 배점)"""
        cases = [(15, 35), (25, 28), (40, 18), (70, 8), (85, 0)]
        for vol, expected in cases:
            quant = {"risk_metrics": {"volatility": vol}}
            result = ScoringEngine._score_risk(quant)
            assert result["details"]["변동성(연율)"]["earned"] == expected

    def test_mdd_tiers(self):
        """MDD 구간별 점수 (35점 배점)"""
        cases = [(-5, 35), (-15, 28), (-25, 18), (-40, 8), (-55, 0)]
        for mdd, expected in cases:
            quant = {"risk_metrics": {"max_drawdown": {"max_drawdown": mdd}}}
            result = ScoringEngine._score_risk(quant)
            assert result["details"]["MDD"]["earned"] == expected

    def test_sharpe_tiers(self):
        """샤프비율 구간별 점수 (30점 배점)"""
        cases = [(2.5, 30), (1.5, 24), (0.5, 15), (-0.5, 6), (-1.5, 0)]
        for sharpe, expected in cases:
            quant = {"risk_metrics": {"sharpe_ratio": {"sharpe_ratio": sharpe}}}
            result = ScoringEngine._score_risk(quant)
            assert result["details"]["샤프비율"]["earned"] == expected

    def test_volatility_dict_ignored(self):
        """volatility가 dict인 경우 무시"""
        quant = {"risk_metrics": {"volatility": {"some": "data"}}}
        result = ScoringEngine._score_risk(quant)
        assert result is None


# ============================================================================
# _generate_summary
# ============================================================================

@pytest.mark.unit
class TestGenerateSummary:
    """요약 텍스트 생성 테스트"""

    def test_all_categories_high(self):
        """모든 카테고리 고점수 → 긍정적 시그널"""
        categories = {
            "financial": {"score": 80},
            "valuation": {"score": 75},
            "technical": {"score": 85},
            "risk": {"score": 70},
        }
        availability = {k: True for k in categories}
        summary = ScoringEngine._generate_summary(categories, availability)
        assert "우량 재무" in summary
        assert "저평가 매력" in summary
        assert "강한 상승 추세" in summary
        assert "안정적 리스크" in summary

    def test_all_categories_low(self):
        """모든 카테고리 저점수 → 경고 시그널"""
        categories = {
            "financial": {"score": 30},
            "valuation": {"score": 20},
            "technical": {"score": 25},
            "risk": {"score": 35},
        }
        availability = {k: True for k in categories}
        summary = ScoringEngine._generate_summary(categories, availability)
        assert "재무 개선 필요" in summary
        assert "고평가 주의" in summary
        assert "약세 추세" in summary
        assert "높은 리스크" in summary

    def test_middle_range(self):
        """중간 구간 → 보통/양호 시그널"""
        categories = {
            "financial": {"score": 55},
            "valuation": {"score": 60},
            "technical": {"score": 50},
            "risk": {"score": 65},
        }
        availability = {k: True for k in categories}
        summary = ScoringEngine._generate_summary(categories, availability)
        assert "양호한 재무" in summary
        assert "적정 밸류에이션" in summary
        assert "보합 추세" in summary
        assert "보통 리스크" in summary

    def test_partial_data(self):
        """일부 카테고리만 있는 경우"""
        categories = {
            "financial": {"score": 80},
            "valuation": None,
            "technical": None,
            "risk": None,
        }
        availability = {"financial": True, "valuation": False, "technical": False, "risk": False}
        summary = ScoringEngine._generate_summary(categories, availability)
        assert "우량 재무" in summary
        assert "+" not in summary  # 하나뿐이니 + 없음

    def test_no_data(self):
        """데이터 없음"""
        categories = {k: None for k in ["financial", "valuation", "technical", "risk"]}
        availability = {k: False for k in categories}
        summary = ScoringEngine._generate_summary(categories, availability)
        assert summary == "분석 데이터 부족"


# ============================================================================
# 가중치 재분배 로직 (calculate_compass_score 내부)
# ============================================================================

@pytest.mark.unit
class TestWeightRedistribution:
    """가중치 재분배 로직 검증 — 직접 계산 시뮬레이션"""

    def test_all_categories_weighted(self):
        """4개 카테고리 모두 있을 때 정규 가중치"""
        weights = ScoringEngine.WEIGHTS
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_weight_redistribution_one_missing(self):
        """1개 카테고리 N/A → 나머지 3개로 100% 분배"""
        weights = ScoringEngine.WEIGHTS
        available = {"financial": {"score": 80}, "technical": {"score": 70}, "risk": {"score": 60}}

        total_weight = sum(weights[k] for k in available)
        compass = sum(
            available[k]["score"] * (weights[k] / total_weight)
            for k in available
        )
        # financial: 80*0.30/0.80 + technical: 70*0.30/0.80 + risk: 60*0.20/0.80
        expected = 80 * (0.30 / 0.80) + 70 * (0.30 / 0.80) + 60 * (0.20 / 0.80)
        assert compass == pytest.approx(expected)
        # 합산 가중치가 1.0
        redistributed = sum(weights[k] / total_weight for k in available)
        assert redistributed == pytest.approx(1.0)

    def test_weight_redistribution_only_one(self):
        """1개 카테고리만 있으면 해당 점수가 곧 compass_score"""
        weights = ScoringEngine.WEIGHTS
        available = {"risk": {"score": 55}}
        total_weight = sum(weights[k] for k in available)
        compass = sum(
            available[k]["score"] * (weights[k] / total_weight)
            for k in available
        )
        assert compass == pytest.approx(55.0)


# ============================================================================
# _score_technical — 세부 지표별 테스트 추가
# ============================================================================

@pytest.mark.unit
class TestScoreTechnicalDetails:
    """기술 점수 세부 지표 개별 테스트"""

    def test_stochastic_zones(self):
        """Stochastic K 구간별 점수 (10점 배점)"""
        cases = [
            (50, 10),   # 20-80: 중립
            (15, 8),    # <20: 과매도
            (85, 3),    # >80: 과매수
        ]
        for k_val, expected in cases:
            quant = {"technical_indicators": {"stochastic": {"k": k_val}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["Stochastic"]["earned"] == expected, \
                f"K={k_val} → expected {expected}"

    def test_stochastic_boundaries(self):
        """Stochastic 경계값"""
        # k=20 → 중립(10점)
        quant = {"technical_indicators": {"stochastic": {"k": 20}}}
        result = ScoringEngine._score_technical(quant)
        assert result["details"]["Stochastic"]["earned"] == 10

        # k=80 → 중립(10점)
        quant = {"technical_indicators": {"stochastic": {"k": 80}}}
        result = ScoringEngine._score_technical(quant)
        assert result["details"]["Stochastic"]["earned"] == 10

    def test_macd_statuses(self):
        """MACD status별 점수 (15점 배점)"""
        cases = [
            ("골든크로스 감지", 15),
            ("상승 추세 지속", 12),
            ("하락 전환 가능성", 5),
            ("데드크로스", 2),
        ]
        for status, expected in cases:
            quant = {"technical_indicators": {"macd": {"status": status}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["MACD"]["earned"] == expected, \
                f"status='{status}' → expected {expected}"

    def test_week52_position_zones(self):
        """52주 위치 구간별 점수 (10점 배점)"""
        cases = [
            (55, 10),   # 40-70
            (30, 7),    # 20-40
            (75, 7),    # 70-80
            (10, 5),    # <20
            (90, 4),    # >80
        ]
        for pos, expected in cases:
            quant = {"technical_indicators": {"week52_position": {"position": pos}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["52주 위치"]["earned"] == expected, \
                f"position={pos} → expected {expected}"

    def test_obv_trends(self):
        """OBV 추세별 점수 (10점 배점)"""
        cases = [
            ("상승", 10),
            ("중립", 5),
            ("하락", 2),
        ]
        for trend, expected in cases:
            quant = {"technical_indicators": {"obv": {"trend": trend}}}
            result = ScoringEngine._score_technical(quant)
            assert result["details"]["OBV 추세"]["earned"] == expected

    def test_partial_indicators(self):
        """일부 지표만 있을 때 정규화"""
        quant = {
            "technical_indicators": {
                "rsi": {"rsi": 50},       # 15/15
                "stochastic": {"k": 50},  # 10/10
            }
        }
        result = ScoringEngine._score_technical(quant)
        # (15 + 10) / (15 + 10) * 100 = 100
        assert result["score"] == 100.0


# ============================================================================
# _generate_commentary
# ============================================================================

@pytest.mark.unit
class TestGenerateCommentary:
    """해설 자동 생성 테스트"""

    def _categories(self, fin=80, val=70, tech=65, risk=60):
        """카테고리 dict 생성 헬퍼"""
        cats = {}
        if fin is not None:
            cats["financial"] = {"score": fin}
        else:
            cats["financial"] = None
        if val is not None:
            cats["valuation"] = {"score": val}
        else:
            cats["valuation"] = None
        if tech is not None:
            cats["technical"] = {"score": tech}
        else:
            cats["technical"] = None
        if risk is not None:
            cats["risk"] = {"score": risk}
        else:
            cats["risk"] = None
        return cats

    def _financial_result(self, roe=12.0, op_margin=15.0, debt=80.0):
        return {
            "profitability": {"roe": roe},
            "profit_margins": {"operating_margin": op_margin},
            "financial_health": {"debt_to_equity": debt},
        }

    def _valuation_result(self, pe_vs=-25, pb_vs=10):
        return {
            "pe_comparison": {"vs_industry": pe_vs},
            "pb_comparison": {"vs_industry": pb_vs},
        }

    def _quant_result(self, rsi=50, adx=25, alignment="정배열", macd_status="상승 추세",
                       vol=20.0, mdd=-15.0, sharpe=1.2):
        return {
            "technical_indicators": {
                "ma_alignment": {"alignment": alignment},
                "adx": {"adx": adx},
                "rsi": {"rsi": rsi},
                "macd": {"status": macd_status},
            },
            "risk_metrics": {
                "volatility": vol,
                "max_drawdown": {"max_drawdown": mdd},
                "sharpe_ratio": {"sharpe_ratio": sharpe},
            },
        }

    def test_full_commentary(self):
        """모든 카테고리 있을 때 4개 섹션 포함"""
        cats = self._categories()
        commentary = ScoringEngine._generate_commentary(
            ticker="005930", company_name="삼성전자", compass_score=72.5, grade="A",
            categories=cats,
            financial_result=self._financial_result(),
            valuation_result=self._valuation_result(),
            quant_result=self._quant_result(),
        )
        assert "삼성전자(005930)" in commentary
        assert "72.5점" in commentary
        assert "A등급" in commentary
        assert "ROE" in commentary
        assert "영업이익률" in commentary
        assert "PER" in commentary or "PBR" in commentary
        assert "기술적으로" in commentary
        assert "리스크" in commentary

    def test_no_company_name(self):
        """company_name=None → ticker 사용"""
        cats = self._categories(fin=None, val=None, tech=None, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="005930", company_name=None, compass_score=50.0, grade="B",
            categories=cats,
            financial_result=None, valuation_result=None, quant_result=None,
        )
        assert "005930" in commentary
        assert "50.0점" in commentary

    def test_financial_high_score_commentary(self):
        """재무 점수 ≥70 → '재무 건전성이 우수하며'"""
        cats = self._categories(fin=80, val=None, tech=None, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=80.0, grade="A+",
            categories=cats,
            financial_result=self._financial_result(roe=20),
            valuation_result=None, quant_result=None,
        )
        assert "재무 건전성이 우수하며" in commentary

    def test_financial_low_score_commentary(self):
        """재무 점수 < 50 → '재무 개선이 필요하며'"""
        cats = self._categories(fin=30, val=None, tech=None, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=30.0, grade="C",
            categories=cats,
            financial_result=self._financial_result(roe=-5, op_margin=-3),
            valuation_result=None, quant_result=None,
        )
        assert "재무 개선이 필요하며" in commentary

    def test_valuation_overvalued_commentary(self):
        """밸류에이션 점수 < 50 → '고평가 구간'"""
        cats = self._categories(fin=None, val=30, tech=None, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=30.0, grade="C",
            categories=cats,
            financial_result=None,
            valuation_result=self._valuation_result(pe_vs=50, pb_vs=40),
            quant_result=None,
        )
        assert "고평가" in commentary

    def test_technical_strong_uptrend(self):
        """기술 점수 ≥70 → '강한 상승 추세'"""
        cats = self._categories(fin=None, val=None, tech=80, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=80.0, grade="A+",
            categories=cats,
            financial_result=None, valuation_result=None,
            quant_result=self._quant_result(rsi=50, adx=30, alignment="정배열"),
        )
        assert "강한 상승 추세" in commentary

    def test_risk_high_warning(self):
        """리스크 점수 < 50 → '주의가 필요'"""
        cats = self._categories(fin=None, val=None, tech=None, risk=30)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=30.0, grade="C",
            categories=cats,
            financial_result=None, valuation_result=None,
            quant_result=self._quant_result(vol=80, mdd=-55, sharpe=-1.5),
        )
        assert "주의가 필요" in commentary

    def test_rsi_overbought_label(self):
        """RSI > 70 → '(과매수)' 라벨"""
        cats = self._categories(fin=None, val=None, tech=50, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=50.0, grade="B",
            categories=cats,
            financial_result=None, valuation_result=None,
            quant_result=self._quant_result(rsi=75),
        )
        assert "과매수" in commentary

    def test_rsi_oversold_label(self):
        """RSI < 30 → '(과매도)' 라벨"""
        cats = self._categories(fin=None, val=None, tech=50, risk=None)
        commentary = ScoringEngine._generate_commentary(
            ticker="TEST", company_name="테스트", compass_score=50.0, grade="B",
            categories=cats,
            financial_result=None, valuation_result=None,
            quant_result=self._quant_result(rsi=25),
        )
        assert "과매도" in commentary


# ============================================================================
# calculate_compass_score — 통합 테스트 (3개 분석기 mock)
# ============================================================================

@pytest.mark.unit
class TestCalculateCompassScore:
    """calculate_compass_score 오케스트레이션 테스트"""

    def _mock_db(self):
        return MagicMock()

    @patch("app.services.scoring_engine.QuantAnalyzer")
    @patch("app.services.scoring_engine.ValuationAnalyzer")
    @patch("app.services.scoring_engine.FinancialAnalyzer")
    def test_all_analyzers_success(self, mock_fin, mock_val, mock_quant):
        """3개 분석기 모두 성공 → 정상 compass score"""
        mock_fin.analyze_stock.return_value = {
            "success": True,
            "company_name": "삼성전자",
            "profitability": {"roe": 15},
            "profit_margins": {"operating_margin": 20, "net_margin": 15},
            "financial_health": {"debt_to_equity": 50},
        }
        mock_val.compare_multiples.return_value = {
            "company_name": "삼성전자",
            "pe_comparison": {"vs_industry": -25},
            "pb_comparison": {"vs_industry": 0},
        }
        mock_quant.comprehensive_quant_analysis.return_value = {
            "technical_indicators": {
                "ma_alignment": {"alignment": "정배열"},
                "adx": {"adx": 30, "direction": "상승 추세"},
                "rsi": {"rsi": 50},
                "stochastic": {"k": 50},
                "macd": {"status": "골든크로스 감지"},
                "week52_position": {"position": 55},
                "obv": {"trend": "상승"},
            },
            "risk_metrics": {
                "volatility": 18,
                "max_drawdown": {"max_drawdown": -8},
                "sharpe_ratio": {"sharpe_ratio": 1.5},
            },
        }

        result = ScoringEngine.calculate_compass_score(self._mock_db(), "005930")

        assert "error" not in result
        assert result["ticker"] == "005930"
        assert result["company_name"] == "삼성전자"
        assert 0 <= result["compass_score"] <= 100
        assert result["grade"] in ["S", "A+", "A", "B+", "B", "C+", "C", "D", "F"]
        assert result["disclaimer"] == "교육 목적 참고 정보이며 투자 권유가 아닙니다"
        assert "categories" in result
        assert all(k in result["categories"] for k in ["financial", "valuation", "technical", "risk"])

    @patch("app.services.scoring_engine.QuantAnalyzer")
    @patch("app.services.scoring_engine.ValuationAnalyzer")
    @patch("app.services.scoring_engine.FinancialAnalyzer")
    def test_all_analyzers_fail(self, mock_fin, mock_val, mock_quant):
        """3개 분석기 모두 실패 → error 반환"""
        mock_fin.analyze_stock.side_effect = Exception("DB error")
        mock_val.compare_multiples.side_effect = Exception("DB error")
        mock_quant.comprehensive_quant_analysis.side_effect = Exception("DB error")

        result = ScoringEngine.calculate_compass_score(self._mock_db(), "005930")

        assert "error" in result

    @patch("app.services.scoring_engine.QuantAnalyzer")
    @patch("app.services.scoring_engine.ValuationAnalyzer")
    @patch("app.services.scoring_engine.FinancialAnalyzer")
    def test_partial_data_weight_redistribution(self, mock_fin, mock_val, mock_quant):
        """재무만 성공 → 가중치 재분배 (재무 100%)"""
        mock_fin.analyze_stock.return_value = {
            "success": True,
            "company_name": "테스트기업",
            "profitability": {"roe": 15},
            "profit_margins": {"operating_margin": 20, "net_margin": 15},
            "financial_health": {"debt_to_equity": 50},
        }
        mock_val.compare_multiples.side_effect = Exception("No data")
        mock_quant.comprehensive_quant_analysis.return_value = {"error": "데이터 부족"}

        result = ScoringEngine.calculate_compass_score(self._mock_db(), "TEST")

        assert "error" not in result
        # 재무만 100점이면 compass_score도 100점 (유일한 카테고리)
        assert result["compass_score"] == 100.0
        assert result["data_availability"]["financial"] is True
        assert result["data_availability"]["valuation"] is False
        assert result["data_availability"]["technical"] is False
        assert result["data_availability"]["risk"] is False

    @patch("app.services.scoring_engine.QuantAnalyzer")
    @patch("app.services.scoring_engine.ValuationAnalyzer")
    @patch("app.services.scoring_engine.FinancialAnalyzer")
    def test_financial_not_success(self, mock_fin, mock_val, mock_quant):
        """FinancialAnalyzer.success=False → 재무 N/A"""
        mock_fin.analyze_stock.return_value = {"success": False}
        mock_val.compare_multiples.return_value = {
            "pe_comparison": {"vs_industry": -30},
            "pb_comparison": {"vs_industry": -25},
        }
        mock_quant.comprehensive_quant_analysis.return_value = {"error": "no data"}

        result = ScoringEngine.calculate_compass_score(self._mock_db(), "TEST")

        assert "error" not in result
        assert result["data_availability"]["financial"] is False
        assert result["data_availability"]["valuation"] is True

    @patch("app.services.scoring_engine.QuantAnalyzer")
    @patch("app.services.scoring_engine.ValuationAnalyzer")
    @patch("app.services.scoring_engine.FinancialAnalyzer")
    def test_grade_and_category_grades(self, mock_fin, mock_val, mock_quant):
        """각 카테고리에 grade 필드가 부여되는지 확인"""
        mock_fin.analyze_stock.return_value = {
            "success": True,
            "profitability": {"roe": 15},
            "profit_margins": {"operating_margin": 20, "net_margin": 15},
            "financial_health": {"debt_to_equity": 50},
        }
        mock_val.compare_multiples.side_effect = Exception("N/A")
        mock_quant.comprehensive_quant_analysis.side_effect = Exception("N/A")

        result = ScoringEngine.calculate_compass_score(self._mock_db(), "TEST")

        fin_cat = result["categories"]["financial"]
        assert "grade" in fin_cat
        assert "weight" in fin_cat
        assert fin_cat["weight"] == "30%"

        # N/A 카테고리는 기본 구조
        val_cat = result["categories"]["valuation"]
        assert val_cat["score"] is None
        assert val_cat["grade"] == "N/A"
