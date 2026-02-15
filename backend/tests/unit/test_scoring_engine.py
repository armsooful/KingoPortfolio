"""
ScoringEngine 단위 테스트 — 순수 로직 (DB 불필요)

_score_financial, _score_valuation, _score_technical, _score_risk,
_determine_grade, _generate_summary 정적 메서드를 dict 입출력으로 테스트.
"""
import pytest
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
