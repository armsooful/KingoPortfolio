"""
더미 데이터 제공 모듈 (Feature Flag OFF 시 사용)

⚠️ Recommendation Engine이 비활성화된 경우 사용되는 시나리오 기반 더미 데이터
"""

from typing import List, Dict


class DummyDataProvider:
    """시나리오 기반 더미 데이터 제공자"""

    @staticmethod
    def get_dummy_stocks(investment_type: str, limit: int = 3) -> List[Dict]:
        """시나리오 기반 더미 주식 데이터"""
        dummy_stocks = {
            "conservative": [
                {
                    "id": "dummy_stock_1",
                    "ticker": "SAMPLE1",
                    "name": "교육용 샘플 주식 A",
                    "category": "안정형",
                    "current_price": 50000,
                    "pe_ratio": 10.5,
                    "pb_ratio": 1.2,
                    "dividend_yield": 3.5,
                    "ytd_return": 5.2,
                    "one_year_return": 8.5,
                    "risk_level": "low",
                    "reason": "학습용 예시 데이터",
                    "expected_return": "8.5%"
                }
            ],
            "moderate": [
                {
                    "id": "dummy_stock_2",
                    "ticker": "SAMPLE2",
                    "name": "교육용 샘플 주식 B",
                    "category": "균형형",
                    "current_price": 75000,
                    "pe_ratio": 15.0,
                    "pb_ratio": 1.8,
                    "dividend_yield": 2.0,
                    "ytd_return": 10.5,
                    "one_year_return": 12.0,
                    "risk_level": "medium",
                    "reason": "학습용 예시 데이터",
                    "expected_return": "12.0%"
                }
            ],
            "aggressive": [
                {
                    "id": "dummy_stock_3",
                    "ticker": "SAMPLE3",
                    "name": "교육용 샘플 주식 C",
                    "category": "성장형",
                    "current_price": 100000,
                    "pe_ratio": 25.0,
                    "pb_ratio": 3.5,
                    "dividend_yield": 0.5,
                    "ytd_return": 20.0,
                    "one_year_return": 25.0,
                    "risk_level": "high",
                    "reason": "학습용 예시 데이터",
                    "expected_return": "25.0%"
                }
            ]
        }

        stocks = dummy_stocks.get(investment_type, dummy_stocks["moderate"])
        return stocks[:limit]

    @staticmethod
    def get_dummy_etfs(investment_type: str, limit: int = 2) -> List[Dict]:
        """시나리오 기반 더미 ETF 데이터"""
        return [
            {
                "id": "dummy_etf_1",
                "ticker": "SAMPLEETF",
                "name": "교육용 샘플 ETF",
                "category": "시장추종형",
                "current_price": 10000,
                "ytd_return": 8.0,
                "expense_ratio": 0.05,
                "reason": "학습용 예시 데이터",
                "expected_return": "8.0%"
            }
        ][:limit]

    @staticmethod
    def get_dummy_bonds(investment_type: str, limit: int = 2) -> List[Dict]:
        """시나리오 기반 더미 채권 데이터"""
        return [
            {
                "id": "dummy_bond_1",
                "name": "교육용 샘플 채권",
                "bond_type": "국고채",
                "maturity_date": "2030-12-31",
                "coupon_rate": 3.5,
                "ytm": 3.7,
                "risk_grade": "AAA",
                "reason": "학습용 예시 데이터",
                "expected_return": "3.7%"
            }
        ][:limit]

    @staticmethod
    def get_dummy_deposits(limit: int = 1) -> List[Dict]:
        """시나리오 기반 더미 예금 데이터"""
        return [
            {
                "id": "dummy_deposit_1",
                "name": "교육용 샘플 예금",
                "bank": "샘플 은행",
                "product_type": "정기예금",
                "interest_rate": 3.0,
                "term_months": 12,
                "minimum_investment": 1000000,
                "reason": "학습용 예시 데이터",
                "expected_return": "3.0%"
            }
        ][:limit]
