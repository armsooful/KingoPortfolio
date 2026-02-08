# backend/app/services/data_loader.py

from sqlalchemy.orm import Session
from app.models.securities import ETF, DepositProduct, ProductRecommendation
from app.progress_tracker import progress_tracker
import FinanceDataReader as fdr
from datetime import datetime
from typing import Dict, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

class DataLoaderService:
    """DB에 종목 데이터 적재"""

    @staticmethod
    def _fetch_etf_data(ticker: str, name: str) -> Optional[Dict]:
        """pykrx ohlcv로 ETF 데이터 수집 (스레드 안전, DB 접근 없음)."""
        from pykrx import stock as krx_stock
        from datetime import datetime, timedelta

        today = datetime.now().strftime('%Y%m%d')
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        year_start = datetime.now().replace(month=1, day=1).strftime('%Y%m%d')

        try:
            df = krx_stock.get_market_ohlcv(one_year_ago, today, ticker)
            if df.empty:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                df = krx_stock.get_market_ohlcv(one_year_ago, yesterday, ticker)
            if df.empty:
                return None
        except Exception as e:
            logger.warning(f"pykrx ohlcv 호출 실패: {ticker} — {e}")
            return None

        current_price = float(df['종가'].iloc[-1])

        # 1년 수익률
        one_year_return = None
        if len(df) > 1:
            one_year_return = float(((df['종가'].iloc[-1] - df['종가'].iloc[0]) / df['종가'].iloc[0]) * 100)

        # YTD 수익률 (연초 이후 데이터만)
        ytd_return = None
        ytd_df = df.loc[year_start:]
        if len(ytd_df) > 1:
            ytd_return = float(((ytd_df['종가'].iloc[-1] - ytd_df['종가'].iloc[0]) / ytd_df['종가'].iloc[0]) * 100)

        return {
            "current_price": current_price,
            "aum": None,            # pykrx 미제공 — 별도 파이프라인에서 처리 가능
            "expense_ratio": None,  # pykrx 미제공 — 별도 파이프라인에서 처리 가능
            "ytd_return": ytd_return,
            "one_year_return": one_year_return,
        }

    @staticmethod
    def load_etfs(db: Session, task_id: str = None) -> dict:
        """ETF 데이터 적재 (pykrx ohlcv)

        Returns:
            적재 결과 {success: int, failed: int, updated: int}
        """
        if not task_id:
            task_id = f"etfs_{uuid.uuid4().hex[:8]}"

        # fdr로 전체 한국 ETF 종목 로드
        listing = fdr.StockListing("ETF/KR")
        etfs_list = list(listing[["Symbol", "Name"]].itertuples(index=False, name=None))
        total_count = len(etfs_list)

        progress_tracker.start_task(task_id, total_count, f"ETF 데이터 수집 ({total_count}종목)")

        result = {"success": 0, "failed": 0, "updated": 0}

        # Phase 1: pykrx를 ThreadPoolExecutor로 동시 호출
        from concurrent.futures import ThreadPoolExecutor, as_completed

        fetched: Dict[str, Optional[Dict]] = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            future_to_ticker = {
                pool.submit(DataLoaderService._fetch_etf_data, ticker, name): ticker
                for ticker, name in etfs_list
            }
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    fetched[ticker] = future.result()
                except Exception as e:
                    logger.error(f"pykrx ETF fetch 실패: {ticker} — {e}")
                    fetched[ticker] = None

        # Phase 2: 단일 스레드로 DB upsert (100건씩 batch commit)
        _BATCH_SIZE = 100
        pending = 0
        for idx, (ticker, name) in enumerate(etfs_list, 1):
            progress_tracker.update_progress(
                task_id, current=idx, current_item=f"{name} ({ticker})", success=None
            )

            data = fetched.get(ticker)
            if data is None:
                result["failed"] += 1
                progress_tracker.update_progress(
                    task_id, current=idx, current_item=f"{name} ({ticker})",
                    success=False, error=f"{name} 데이터 수집 실패"
                )
                continue

            try:
                etf_type = "equity" if "주식" in name else "bond" if "채권" in name else "balanced"
                risk_level = "medium" if etf_type == "balanced" else "low" if etf_type == "bond" else "high"

                existing_etf = db.query(ETF).filter(ETF.ticker == ticker).first()

                if existing_etf:
                    existing_etf.current_price = data.get("current_price")
                    if data.get("aum") is not None:
                        existing_etf.aum = data.get("aum")
                    if data.get("expense_ratio") is not None:
                        existing_etf.expense_ratio = data.get("expense_ratio")
                    existing_etf.ytd_return = data.get("ytd_return")
                    existing_etf.one_year_return = data.get("one_year_return")
                    existing_etf.last_updated = datetime.utcnow()
                    result["updated"] += 1
                else:
                    db.add(ETF(
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
                        category=name,
                    ))
                    result["success"] += 1

                pending += 1
                progress_tracker.update_progress(
                    task_id, current=idx, current_item=f"{name} ({ticker})", success=True
                )

                if pending >= _BATCH_SIZE:
                    db.commit()
                    pending = 0

            except Exception as e:
                logger.error(f"ETF upsert 실패: {ticker} — {e}")
                result["failed"] += 1
                db.rollback()
                pending = 0
                progress_tracker.update_progress(
                    task_id, current=idx, current_item=f"{name} ({ticker})",
                    success=False, error=str(e)
                )

        if pending > 0:
            db.commit()

        progress_tracker.complete_task(task_id, "completed")
        result["task_id"] = task_id

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
            "etfs": DataLoaderService.load_etfs(db),
            "deposits": DataLoaderService.load_deposit_products(db),
        }
        
        logger.info(f"Data loading completed: {results}")
        return results
