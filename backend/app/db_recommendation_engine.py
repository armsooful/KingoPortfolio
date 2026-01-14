# backend/app/db_recommendation_engine.py

"""
⚠️ 교육 목적: 본 모듈은 투자 전략 학습용 상품 정보 조회 도구입니다.
투자 권유·추천·자문·일임 서비스를 제공하지 않습니다.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.securities import Stock, ETF, Bond, DepositProduct
from app.config import settings
from app.db_recommendation_dummy import DummyDataProvider
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DBProductSampler:
    """DB 기반 샘플 상품 조회 엔진 (교육용)"""

    @staticmethod
    def get_recommended_stocks(
        db: Session,
        investment_type: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        전략 유형별 샘플 주식 조회 (교육용)

        ⚠️ 본 메서드는 학습용 샘플 데이터를 제공하며, 투자 권유가 아닙니다.
        """

        # Feature Flag 체크
        if not settings.feature_recommendation_engine:
            logger.info(f"🚫 Recommendation Engine DISABLED - returning dummy stock data for {investment_type}")
            return DummyDataProvider.get_dummy_stocks(investment_type, limit)
        
        # 투자성향에 맞는 주식 쿼리
        stocks = db.query(Stock).filter(
            and_(
                Stock.investment_type.contains(investment_type),
                Stock.is_active == True
            )
        ).order_by(Stock.dividend_yield.desc()).limit(limit).all()
        
        return [
            {
                "id": stock.id,
                "ticker": stock.ticker,
                "name": stock.name,
                "category": stock.category,
                "current_price": stock.current_price,
                "pe_ratio": stock.pe_ratio,
                "pb_ratio": stock.pb_ratio,
                "dividend_yield": stock.dividend_yield,
                "ytd_return": stock.ytd_return,
                "one_year_return": stock.one_year_return,
                "risk_level": stock.risk_level,
                "reason": f"{stock.category} - {stock.name}",
                "expected_return": f"{stock.one_year_return:.1f}%"
            }
            for stock in stocks
        ]
    
    @staticmethod
    def get_recommended_etfs(
        db: Session,
        investment_type: str,
        limit: int = 2
    ) -> List[Dict]:
        """투자성향에 맞는 ETF 추천"""
        
        etfs = db.query(ETF).filter(
            and_(
                ETF.investment_type.contains(investment_type),
                ETF.is_active == True
            )
        ).order_by(ETF.one_year_return.desc()).limit(limit).all()
        
        return [
            {
                "id": etf.id,
                "ticker": etf.ticker,
                "name": etf.name,
                "category": etf.category,
                "etf_type": etf.etf_type,
                "current_price": etf.current_price,
                "aum": etf.aum,
                "expense_ratio": etf.expense_ratio,
                "ytd_return": etf.ytd_return,
                "one_year_return": etf.one_year_return,
                "risk_level": etf.risk_level,
                "reason": f"{etf.category} - 분산 투자",
                "expected_return": f"{etf.one_year_return:.1f}%"
            }
            for etf in etfs
        ]
    
    @staticmethod
    def get_recommended_bonds(
        db: Session,
        investment_type: str,
        limit: int = 2
    ) -> List[Dict]:
        """투자성향에 맞는 채권 추천"""
        
        bonds = db.query(Bond).filter(
            and_(
                Bond.investment_type.contains(investment_type),
                Bond.is_active == True
            )
        ).order_by(Bond.interest_rate.desc()).limit(limit).all()
        
        return [
            {
                "id": bond.id,
                "name": bond.name,
                "bond_type": bond.bond_type,
                "issuer": bond.issuer,
                "interest_rate": bond.interest_rate,
                "maturity_years": bond.maturity_years,
                "credit_rating": bond.credit_rating,
                "risk_level": bond.risk_level,
                "minimum_investment": bond.minimum_investment,
                "reason": f"{bond.bond_type} - 안정적 수익",
                "expected_return": f"{bond.interest_rate:.1f}%"
            }
            for bond in bonds
        ]
    
    @staticmethod
    def get_recommended_deposits(
        db: Session,
        limit: int = 1
    ) -> List[Dict]:
        """추천 예금 상품"""
        
        deposits = db.query(DepositProduct).filter(
            DepositProduct.is_active == True
        ).order_by(DepositProduct.interest_rate.desc()).limit(limit).all()
        
        return [
            {
                "id": deposit.id,
                "name": deposit.name,
                "bank": deposit.bank,
                "product_type": deposit.product_type,
                "interest_rate": deposit.interest_rate,
                "term_months": deposit.term_months,
                "minimum_investment": deposit.minimum_investment,
                "reason": f"{deposit.bank} - 유동성 확보",
                "expected_return": f"{deposit.interest_rate:.1f}%"
            }
            for deposit in deposits
        ]
    
    @staticmethod
    def get_all_recommendations(
        db: Session,
        investment_type: str
    ) -> Dict:
        """모든 추천 상품 조회"""
        
        return {
            "recommended_stocks": DBRecommendationEngine.get_recommended_stocks(db, investment_type),
            "recommended_etfs": DBRecommendationEngine.get_recommended_etfs(db, investment_type),
            "recommended_bonds": DBRecommendationEngine.get_recommended_bonds(db, investment_type),
            "recommended_deposits": DBRecommendationEngine.get_recommended_deposits(db),
        }