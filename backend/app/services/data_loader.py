# backend/app/services/data_loader.py

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.securities import Stock, ETF, Bond, DepositProduct, ProductRecommendation
from app.data_collector import DataCollector, DataClassifier
from app.progress_tracker import progress_tracker
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

class DataLoaderService:
    """DB에 종목 데이터 적재"""

    @staticmethod
    def load_korean_stocks(db: Session, task_id: str = None) -> dict:
        """한국 주식 데이터 적재

        Returns:
            적재 결과 {success: int, failed: int, updated: int}
        """
        # task_id가 없으면 생성
        if not task_id:
            task_id = f"stocks_{uuid.uuid4().hex[:8]}"

        stocks_list = list(DataCollector.KOREAN_STOCKS.items())
        total_count = len(stocks_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, "주식 데이터 수집")

        result = {"success": 0, "failed": 0, "updated": 0}

        for idx, (ticker, name) in enumerate(stocks_list, 1):
            try:
                # 현재 처리 중인 종목 업데이트
                progress_tracker.update_progress(
                    task_id,
                    current=idx - 1,
                    current_item=f"{name} ({ticker})"
                )

                # API에서 데이터 수집
                data = DataCollector.fetch_stock_data(ticker, name)
                if not data:
                    result["failed"] += 1
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        success=False,
                        error=f"{name} 데이터 수집 실패"
                    )
                    continue
                
                # 위험도 분류
                risk_level = DataClassifier.classify_risk(
                    data.get("pe_ratio"),
                    data.get("dividend_yield")
                )
                
                # 투자성향 분류
                investment_types = DataClassifier.classify_investment_type(
                    risk_level,
                    data.get("dividend_yield")
                )
                
                # 범주 분류
                category = DataClassifier.classify_category(name, data.get("sector"))
                
                # 기존 데이터 확인
                existing_stock = db.query(Stock).filter(
                    Stock.ticker == ticker
                ).first()
                
                if existing_stock:
                    # 업데이트
                    existing_stock.current_price = data.get("current_price")
                    existing_stock.market_cap = data.get("market_cap")
                    existing_stock.pe_ratio = data.get("pe_ratio")
                    existing_stock.pb_ratio = data.get("pb_ratio")
                    existing_stock.dividend_yield = data.get("dividend_yield")
                    existing_stock.ytd_return = data.get("ytd_return")
                    existing_stock.one_year_return = data.get("one_year_return")
                    existing_stock.last_updated = datetime.utcnow()
                    result["updated"] += 1
                else:
                    # 새로 생성
                    stock = Stock(
                        ticker=ticker,
                        name=name,
                        sector=data.get("sector"),
                        market="KOSPI",
                        current_price=data.get("current_price"),
                        market_cap=data.get("market_cap"),
                        pe_ratio=data.get("pe_ratio"),
                        pb_ratio=data.get("pb_ratio"),
                        dividend_yield=data.get("dividend_yield"),
                        ytd_return=data.get("ytd_return"),
                        one_year_return=data.get("one_year_return"),
                        risk_level=risk_level,
                        investment_type=",".join(investment_types),
                        category=category,
                        description=f"{name} ({category})"
                    )
                    db.add(stock)
                    result["success"] += 1
                
                db.commit()
                logger.info(f"Successfully processed {ticker}: {name}")

                # 성공 업데이트
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    success=True
                )

            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")
                result["failed"] += 1
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    success=False,
                    error=str(e)
                )
                db.rollback()

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")
        result["task_id"] = task_id

        return result
    
    @staticmethod
    def load_etfs(db: Session) -> dict:
        """ETF 데이터 적재"""
        result = {"success": 0, "failed": 0, "updated": 0}
        
        for ticker, name in DataCollector.KOREAN_ETFS.items():
            try:
                # API에서 데이터 수집
                data = DataCollector.fetch_etf_data(ticker, name)
                if not data:
                    result["failed"] += 1
                    continue
                
                # ETF 타입 결정
                etf_type = "equity" if "주식" in name else "bond" if "채권" in name else "balanced"
                
                # 위험도 결정
                risk_level = "medium" if etf_type == "balanced" else "low" if etf_type == "bond" else "high"
                
                # 기존 데이터 확인
                existing_etf = db.query(ETF).filter(
                    ETF.ticker == ticker
                ).first()
                
                if existing_etf:
                    existing_etf.current_price = data.get("current_price")
                    existing_etf.aum = data.get("aum")
                    existing_etf.expense_ratio = data.get("expense_ratio")
                    existing_etf.ytd_return = data.get("ytd_return")
                    existing_etf.one_year_return = data.get("one_year_return")
                    existing_etf.last_updated = datetime.utcnow()
                    result["updated"] += 1
                else:
                    etf = ETF(
                        ticker=ticker,
                        name=name,
                        etf_type=etf_type,
                        current_price=data.get("current_price"),
                        aum=data.get("aum"),
                        expense_ratio=data.get("expense_ratio"),
                        ytd_return=data.get("ytd_return"),
                        one_year_return=data.get("one_year_return"),
                        risk_level=risk_level,
                        investment_type="conservative,moderate,aggressive",
                        category=name
                    )
                    db.add(etf)
                    result["success"] += 1
                
                db.commit()
                logger.info(f"Successfully processed ETF {ticker}: {name}")
                
            except Exception as e:
                logger.error(f"Error processing ETF {ticker}: {str(e)}")
                result["failed"] += 1
                db.rollback()
        
        return result
    
    @staticmethod
    def load_bonds(db: Session) -> dict:
        """채권 데이터 적재 (수동)"""
        bonds = [
            {
                "name": "국고채 3년물",
                "bond_type": "government",
                "interest_rate": 3.5,
                "maturity_years": 3,
                "credit_rating": "AAA",
                "risk_level": "low",
                "investment_type": "conservative,moderate,aggressive"
            },
            {
                "name": "회사채(A등급) 펀드",
                "bond_type": "corporate",
                "interest_rate": 4.2,
                "maturity_years": 3,
                "credit_rating": "A",
                "risk_level": "low",
                "investment_type": "conservative,moderate"
            },
            {
                "name": "하이일드 채권 펀드",
                "bond_type": "high_yield",
                "interest_rate": 6.2,
                "maturity_years": 3,
                "credit_rating": "BBB",
                "risk_level": "high",
                "investment_type": "aggressive"
            },
        ]
        
        result = {"success": 0, "failed": 0, "updated": 0}

        for bond_data in bonds:
            try:
                existing = db.query(Bond).filter(
                    Bond.name == bond_data["name"]
                ).first()

                if not existing:
                    bond = Bond(**bond_data)
                    db.add(bond)
                    result["success"] += 1
                else:
                    result["updated"] += 1

                db.commit()
            except Exception as e:
                logger.error(f"Error loading bond: {str(e)}")
                result["failed"] += 1
                db.rollback()

        return result
    
    @staticmethod
    def load_deposit_products(db: Session) -> dict:
        """예금 상품 적재 (수동)"""
        products = [
            {
                "name": "SC제일은행 CMA",
                "bank": "SC제일은행",
                "product_type": "cma",
                "interest_rate": 3.8,
                "minimum_investment": 0
            },
            {
                "name": "국민은행 정기예금",
                "bank": "국민은행",
                "product_type": "deposit",
                "interest_rate": 3.5,
                "term_months": 12,
                "minimum_investment": 100000
            },
            {
                "name": "NH투자증권 CMA",
                "bank": "NH투자증권",
                "product_type": "cma",
                "interest_rate": 4.2,
                "minimum_investment": 0
            },
        ]
        
        result = {"success": 0, "failed": 0, "updated": 0}

        for product_data in products:
            try:
                existing = db.query(DepositProduct).filter(
                    DepositProduct.name == product_data["name"]
                ).first()

                if not existing:
                    product = DepositProduct(**product_data)
                    db.add(product)
                    result["success"] += 1
                else:
                    result["updated"] += 1

                db.commit()
            except Exception as e:
                logger.error(f"Error loading product: {str(e)}")
                result["failed"] += 1
                db.rollback()

        return result
    
    @staticmethod
    def load_all_data(db: Session) -> dict:
        """모든 데이터 적재"""
        results = {
            "stocks": DataLoaderService.load_korean_stocks(db),
            "etfs": DataLoaderService.load_etfs(db),
            "bonds": DataLoaderService.load_bonds(db),
            "deposits": DataLoaderService.load_deposit_products(db),
        }
        
        logger.info(f"Data loading completed: {results}")
        return results