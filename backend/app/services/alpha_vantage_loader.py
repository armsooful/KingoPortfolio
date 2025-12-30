# backend/app/services/alpha_vantage_loader.py

from sqlalchemy.orm import Session
from app.models.alpha_vantage import (
    AlphaVantageStock,
    AlphaVantageFinancials,
    AlphaVantageETF,
    AlphaVantageTimeSeries
)
from app.services.alpha_vantage_client import AlphaVantageClient
from app.progress_tracker import progress_tracker
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


class AlphaVantageDataLoader:
    """Alpha Vantage 데이터를 DB에 적재하는 서비스"""

    # 미국 대표 주식 심볼 (예시)
    POPULAR_US_STOCKS = {
        # 기술주 (Tech Giants)
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation',
        'GOOGL': 'Alphabet Inc. Class A',
        'AMZN': 'Amazon.com Inc.',
        'META': 'Meta Platforms Inc.',
        'NVDA': 'NVIDIA Corporation',
        'TSLA': 'Tesla Inc.',

        # 금융
        'JPM': 'JPMorgan Chase & Co.',
        'BAC': 'Bank of America Corp',
        'WFC': 'Wells Fargo & Company',

        # 헬스케어
        'JNJ': 'Johnson & Johnson',
        'UNH': 'UnitedHealth Group Inc.',
        'PFE': 'Pfizer Inc.',

        # 소비재
        'KO': 'The Coca-Cola Company',
        'PEP': 'PepsiCo Inc.',
        'WMT': 'Walmart Inc.',

        # 산업
        'BA': 'Boeing Company',
        'CAT': 'Caterpillar Inc.',

        # 에너지
        'XOM': 'Exxon Mobil Corporation',
        'CVX': 'Chevron Corporation',
    }

    # 미국 대표 ETF
    POPULAR_US_ETFS = {
        'SPY': 'SPDR S&P 500 ETF Trust',
        'QQQ': 'Invesco QQQ Trust',
        'DIA': 'SPDR Dow Jones Industrial Average ETF',
        'IWM': 'iShares Russell 2000 ETF',
        'VTI': 'Vanguard Total Stock Market ETF',
        'VOO': 'Vanguard S&P 500 ETF',
        'AGG': 'iShares Core U.S. Aggregate Bond ETF',
        'VNQ': 'Vanguard Real Estate ETF',
    }

    def __init__(self, api_key: str = None):
        self.client = AlphaVantageClient(api_key)

    def load_stock_data(self, db: Session, symbol: str, name: str = None) -> dict:
        """주식 데이터 적재 (시세 + 기업 정보)

        Args:
            db: DB 세션
            symbol: 주식 심볼 (예: AAPL)
            name: 회사명 (선택)

        Returns:
            {"success": bool, "message": str}
        """
        try:
            logger.info(f"Loading data for {symbol}...")

            # 1. 실시간 시세 조회
            quote = self.client.get_quote(symbol)
            if not quote:
                return {"success": False, "message": f"{symbol} 시세 조회 실패"}

            # 2. 기업 개요 조회 (재무지표 포함)
            overview = self.client.get_company_overview(symbol)
            if not overview:
                return {"success": False, "message": f"{symbol} 기업 정보 조회 실패"}

            # 3. 위험도 & 투자성향 분류
            risk_level = self._classify_risk(overview.get('beta', 1.0), overview.get('pe_ratio', 0))
            investment_type = self._classify_investment_type(risk_level, overview.get('dividend_yield', 0))
            category = self._classify_category(overview.get('market_cap', 0), overview.get('sector', ''))

            # 4. DB 저장/업데이트
            existing_stock = db.query(AlphaVantageStock).filter(
                AlphaVantageStock.symbol == symbol
            ).first()

            if existing_stock:
                # 업데이트
                existing_stock.name = overview.get('name') or name or existing_stock.name
                existing_stock.exchange = overview.get('exchange')
                existing_stock.sector = overview.get('sector')
                existing_stock.industry = overview.get('industry')
                existing_stock.current_price = quote.get('price')
                existing_stock.open_price = quote.get('open')
                existing_stock.high_price = quote.get('high')
                existing_stock.low_price = quote.get('low')
                existing_stock.volume = quote.get('volume')
                existing_stock.previous_close = quote.get('previous_close')
                existing_stock.change = quote.get('change')
                existing_stock.change_percent = float(quote.get('change_percent', 0))
                existing_stock.market_cap = overview.get('market_cap')
                existing_stock.pe_ratio = overview.get('pe_ratio')
                existing_stock.peg_ratio = overview.get('peg_ratio')
                existing_stock.pb_ratio = overview.get('pb_ratio')
                existing_stock.dividend_yield = overview.get('dividend_yield')
                existing_stock.eps = overview.get('eps')
                existing_stock.beta = overview.get('beta')
                existing_stock.week_52_high = overview.get('week_52_high')
                existing_stock.week_52_low = overview.get('week_52_low')
                existing_stock.day_50_ma = overview.get('day_50_ma')
                existing_stock.day_200_ma = overview.get('day_200_ma')
                existing_stock.risk_level = risk_level
                existing_stock.investment_type = investment_type
                existing_stock.category = category
                existing_stock.description = overview.get('description')
                existing_stock.last_updated = datetime.utcnow()
                action = "updated"
            else:
                # 새로 생성
                stock = AlphaVantageStock(
                    symbol=symbol,
                    name=overview.get('name') or name or symbol,
                    exchange=overview.get('exchange'),
                    sector=overview.get('sector'),
                    industry=overview.get('industry'),
                    current_price=quote.get('price'),
                    open_price=quote.get('open'),
                    high_price=quote.get('high'),
                    low_price=quote.get('low'),
                    volume=quote.get('volume'),
                    previous_close=quote.get('previous_close'),
                    change=quote.get('change'),
                    change_percent=float(quote.get('change_percent', 0)),
                    market_cap=overview.get('market_cap'),
                    pe_ratio=overview.get('pe_ratio'),
                    peg_ratio=overview.get('peg_ratio'),
                    pb_ratio=overview.get('pb_ratio'),
                    dividend_yield=overview.get('dividend_yield'),
                    eps=overview.get('eps'),
                    beta=overview.get('beta'),
                    week_52_high=overview.get('week_52_high'),
                    week_52_low=overview.get('week_52_low'),
                    day_50_ma=overview.get('day_50_ma'),
                    day_200_ma=overview.get('day_200_ma'),
                    risk_level=risk_level,
                    investment_type=investment_type,
                    category=category,
                    description=overview.get('description'),
                )
                db.add(stock)
                action = "created"

            db.commit()
            logger.info(f"Successfully {action} {symbol}")

            return {
                "success": True,
                "message": f"{symbol} 데이터 {action}",
                "action": action,
                "symbol": symbol
            }

        except Exception as e:
            logger.error(f"Error loading {symbol}: {str(e)}")
            db.rollback()
            return {"success": False, "message": f"{symbol} 적재 실패: {str(e)}"}

    def load_financials(self, db: Session, symbol: str) -> dict:
        """재무제표 데이터 적재 (손익계산서, 재무상태표, 현금흐름표)"""
        try:
            logger.info(f"Loading financials for {symbol}...")

            # 1. 손익계산서
            income_statements = self.client.get_income_statement(symbol)
            if not income_statements:
                return {"success": False, "message": f"{symbol} 손익계산서 조회 실패"}

            # 2. 재무상태표
            balance_sheets = self.client.get_balance_sheet(symbol)

            # 3. 현금흐름표
            cash_flows = self.client.get_cash_flow(symbol)

            # 4. DB 저장 (손익계산서 기준으로 결합)
            saved_count = 0
            for income in income_statements:
                fiscal_date = datetime.strptime(income['fiscal_date'], '%Y-%m-%d').date()
                report_type = income['report_type']

                # 같은 회계연도의 재무상태표 찾기
                balance = next(
                    (b for b in balance_sheets if b['fiscal_date'] == income['fiscal_date']),
                    None
                ) if balance_sheets else None

                # 같은 회계연도의 현금흐름표 찾기
                cash_flow = next(
                    (c for c in cash_flows if c['fiscal_date'] == income['fiscal_date']),
                    None
                ) if cash_flows else None

                # 기존 데이터 확인
                existing = db.query(AlphaVantageFinancials).filter(
                    AlphaVantageFinancials.symbol == symbol,
                    AlphaVantageFinancials.fiscal_date == fiscal_date,
                    AlphaVantageFinancials.report_type == report_type
                ).first()

                # 재무비율 계산
                roe = None
                roa = None
                debt_to_equity = None
                profit_margin = None

                if balance:
                    total_equity = balance.get('total_equity', 0)
                    total_assets = balance.get('total_assets', 0)
                    total_liabilities = balance.get('total_liabilities', 0)
                    net_income = income.get('net_income', 0)
                    revenue = income.get('revenue', 0)

                    if total_equity and total_equity != 0:
                        roe = (net_income / total_equity) * 100  # ROE (%)
                    if total_assets and total_assets != 0:
                        roa = (net_income / total_assets) * 100  # ROA (%)
                    if total_equity and total_equity != 0:
                        debt_to_equity = (total_liabilities / total_equity) * 100  # 부채비율 (%)
                    if revenue and revenue != 0:
                        profit_margin = (net_income / revenue) * 100  # 순이익률 (%)

                if existing:
                    # 업데이트
                    existing.revenue = income.get('revenue')
                    existing.cost_of_revenue = income.get('cost_of_revenue')
                    existing.gross_profit = income.get('gross_profit')
                    existing.operating_income = income.get('operating_income')
                    existing.net_income = income.get('net_income')
                    existing.ebitda = income.get('ebitda')
                    existing.eps = income.get('eps')

                    if balance:
                        existing.total_assets = balance.get('total_assets')
                        existing.total_liabilities = balance.get('total_liabilities')
                        existing.total_equity = balance.get('total_equity')
                        existing.cash_and_equivalents = balance.get('cash_and_equivalents')
                        existing.short_term_debt = balance.get('short_term_debt')
                        existing.long_term_debt = balance.get('long_term_debt')

                    if cash_flow:
                        existing.operating_cash_flow = cash_flow.get('operating_cash_flow')
                        existing.investing_cash_flow = cash_flow.get('investing_cash_flow')
                        existing.financing_cash_flow = cash_flow.get('financing_cash_flow')

                    existing.roe = roe
                    existing.roa = roa
                    existing.debt_to_equity = debt_to_equity
                    existing.profit_margin = profit_margin
                    existing.last_updated = datetime.utcnow()

                else:
                    # 새로 생성
                    financial = AlphaVantageFinancials(
                        symbol=symbol,
                        fiscal_date=fiscal_date,
                        report_type=report_type,
                        revenue=income.get('revenue'),
                        cost_of_revenue=income.get('cost_of_revenue'),
                        gross_profit=income.get('gross_profit'),
                        operating_income=income.get('operating_income'),
                        net_income=income.get('net_income'),
                        ebitda=income.get('ebitda'),
                        eps=income.get('eps'),
                        total_assets=balance.get('total_assets') if balance else None,
                        total_liabilities=balance.get('total_liabilities') if balance else None,
                        total_equity=balance.get('total_equity') if balance else None,
                        cash_and_equivalents=balance.get('cash_and_equivalents') if balance else None,
                        short_term_debt=balance.get('short_term_debt') if balance else None,
                        long_term_debt=balance.get('long_term_debt') if balance else None,
                        operating_cash_flow=cash_flow.get('operating_cash_flow') if cash_flow else None,
                        investing_cash_flow=cash_flow.get('investing_cash_flow') if cash_flow else None,
                        financing_cash_flow=cash_flow.get('financing_cash_flow') if cash_flow else None,
                        roe=roe,
                        roa=roa,
                        debt_to_equity=debt_to_equity,
                        profit_margin=profit_margin,
                    )
                    db.add(financial)

                saved_count += 1

            db.commit()
            logger.info(f"Successfully loaded {saved_count} financial records for {symbol}")

            return {
                "success": True,
                "message": f"{symbol} 재무제표 {saved_count}건 저장",
                "count": saved_count
            }

        except Exception as e:
            logger.error(f"Error loading financials for {symbol}: {str(e)}")
            db.rollback()
            return {"success": False, "message": f"{symbol} 재무제표 적재 실패: {str(e)}"}

    def load_all_popular_stocks(self, db: Session, task_id: str = None) -> dict:
        """인기 미국 주식 전체 적재

        Returns:
            적재 결과 {success: int, failed: int, updated: int, created: int, errors: list}
        """
        # task_id가 없으면 생성
        if not task_id:
            task_id = f"us_stocks_{uuid.uuid4().hex[:8]}"

        stocks_list = list(self.POPULAR_US_STOCKS.items())
        total_count = len(stocks_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, "미국 주식 데이터 수집")

        results = {
            "success": 0,
            "failed": 0,
            "updated": 0,
            "created": 0,
            "errors": []
        }

        for idx, (symbol, name) in enumerate(stocks_list, 1):
            try:
                # 현재 처리 중인 항목 표시 (카운트 증가 없이)
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol})",
                    success=None
                )

                result = self.load_stock_data(db, symbol, name)
                if result['success']:
                    results['success'] += 1
                    if result.get('action') == 'updated':
                        results['updated'] += 1
                    else:
                        results['created'] += 1

                    # 성공 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({symbol})",
                        success=True
                    )
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{symbol}: {result['message']}")

                    # 실패 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({symbol})",
                        success=False,
                        error=result['message']
                    )

            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                results['failed'] += 1
                results['errors'].append(f"{symbol}: {str(e)}")
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol})",
                    success=False,
                    error=str(e)
                )

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")
        results["task_id"] = task_id

        return results

    def load_all_popular_etfs(self, db: Session, task_id: str = None) -> dict:
        """인기 미국 ETF 전체 적재 (간단 버전)

        Returns:
            적재 결과 {success: int, failed: int, updated: int, created: int, errors: list}
        """
        # task_id가 없으면 생성
        if not task_id:
            task_id = f"us_etfs_{uuid.uuid4().hex[:8]}"

        etfs_list = list(self.POPULAR_US_ETFS.items())
        total_count = len(etfs_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, "미국 ETF 데이터 수집")

        results = {
            "success": 0,
            "failed": 0,
            "updated": 0,
            "created": 0,
            "errors": []
        }

        for idx, (symbol, name) in enumerate(etfs_list, 1):
            try:
                # 현재 처리 중인 항목 표시 (카운트 증가 없이)
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol})",
                    success=None
                )

                quote = self.client.get_quote(symbol)
                if not quote:
                    results['failed'] += 1
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({symbol})",
                        success=False,
                        error=f"{symbol} 시세 조회 실패"
                    )
                    continue

                existing = db.query(AlphaVantageETF).filter(
                    AlphaVantageETF.symbol == symbol
                ).first()

                if existing:
                    existing.current_price = quote.get('price')
                    existing.volume = quote.get('volume')
                    existing.change_percent = float(quote.get('change_percent', 0))
                    existing.last_updated = datetime.utcnow()
                    results['updated'] += 1
                else:
                    etf = AlphaVantageETF(
                        symbol=symbol,
                        name=name,
                        etf_type='equity',
                        current_price=quote.get('price'),
                        volume=quote.get('volume'),
                        change_percent=float(quote.get('change_percent', 0)),
                        risk_level='medium',
                        investment_type='moderate',
                        category='Index Fund',
                    )
                    db.add(etf)
                    results['created'] += 1

                db.commit()
                results['success'] += 1

                # 성공 업데이트
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol})",
                    success=True
                )

            except Exception as e:
                logger.error(f"Error loading ETF {symbol}: {str(e)}")
                results['failed'] += 1
                results['errors'].append(f"{symbol}: {str(e)}")
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol})",
                    success=False,
                    error=str(e)
                )
                db.rollback()

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")
        results["task_id"] = task_id

        return results

    def load_time_series_data(self, db: Session, symbol: str, outputsize: str = 'compact') -> dict:
        """시계열 데이터 적재

        Args:
            db: DB 세션
            symbol: 주식 심볼
            outputsize: 'compact' (최근 100일) or 'full' (20년)

        Returns:
            {"success": bool, "message": str, "count": int}
        """
        try:
            logger.info(f"Loading time series data for {symbol} ({outputsize})...")

            # API로부터 시계열 데이터 조회
            time_series_data = self.client.get_daily_time_series(symbol, outputsize)
            if not time_series_data:
                return {"success": False, "message": f"{symbol} 시계열 데이터 조회 실패"}

            saved_count = 0
            updated_count = 0

            for date_str, values in time_series_data.items():
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                    # 기존 데이터 확인
                    existing = db.query(AlphaVantageTimeSeries).filter(
                        AlphaVantageTimeSeries.symbol == symbol.upper(),
                        AlphaVantageTimeSeries.date == date_obj
                    ).first()

                    if existing:
                        # 업데이트
                        existing.open = values['open']
                        existing.high = values['high']
                        existing.low = values['low']
                        existing.close = values['close']
                        existing.volume = values['volume']
                        existing.last_updated = datetime.utcnow()
                        updated_count += 1
                    else:
                        # 신규 생성
                        time_series = AlphaVantageTimeSeries(
                            symbol=symbol.upper(),
                            date=date_obj,
                            open=values['open'],
                            high=values['high'],
                            low=values['low'],
                            close=values['close'],
                            volume=values['volume']
                        )
                        db.add(time_series)
                        saved_count += 1

                except Exception as e:
                    logger.warning(f"Error processing date {date_str}: {str(e)}")
                    continue

            db.commit()
            total = saved_count + updated_count
            logger.info(f"{symbol} 시계열 데이터 저장 완료 (신규: {saved_count}, 업데이트: {updated_count})")

            return {
                "success": True,
                "message": f"{symbol} 시계열 데이터 적재 완료",
                "count": total,
                "saved": saved_count,
                "updated": updated_count
            }

        except Exception as e:
            logger.error(f"Error loading time series for {symbol}: {str(e)}")
            db.rollback()
            return {"success": False, "message": f"{symbol} 시계열 데이터 적재 실패: {str(e)}"}

    def load_all_time_series(self, db: Session, task_id: str = None, outputsize: str = 'compact') -> dict:
        """인기 주식 & ETF 전체 시계열 데이터 적재

        Returns:
            적재 결과 {success: int, failed: int, total_records: int, errors: list}
        """
        # task_id가 없으면 생성
        if not task_id:
            task_id = f"us_timeseries_{uuid.uuid4().hex[:8]}"

        # 주식 + ETF 통합 리스트
        all_symbols = {**self.POPULAR_US_STOCKS, **self.POPULAR_US_ETFS}
        symbols_list = list(all_symbols.items())
        total_count = len(symbols_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, "미국 주식/ETF 시계열 데이터 수집")

        results = {
            "success": 0,
            "failed": 0,
            "total_records": 0,
            "errors": []
        }

        for idx, (symbol, name) in enumerate(symbols_list, 1):
            try:
                # 현재 처리 중인 항목 표시
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol}) 시계열",
                    success=None
                )

                result = self.load_time_series_data(db, symbol, outputsize)
                if result['success']:
                    results['success'] += 1
                    results['total_records'] += result.get('count', 0)

                    # 성공 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({symbol}) 시계열",
                        success=True
                    )
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{symbol}: {result['message']}")

                    # 실패 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({symbol}) 시계열",
                        success=False,
                        error=result['message']
                    )

            except Exception as e:
                logger.error(f"Error processing time series for {symbol}: {str(e)}")
                results['failed'] += 1
                results['errors'].append(f"{symbol}: {str(e)}")
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({symbol}) 시계열",
                    success=False,
                    error=str(e)
                )

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")
        results["task_id"] = task_id

        return results

    # Helper methods
    def _classify_risk(self, beta: float, pe_ratio: float) -> str:
        """위험도 분류"""
        if beta < 0.8 and pe_ratio < 20:
            return 'low'
        elif beta > 1.5 or pe_ratio > 30:
            return 'high'
        else:
            return 'medium'

    def _classify_investment_type(self, risk_level: str, dividend_yield: float) -> str:
        """투자성향 분류"""
        types = []
        if risk_level == 'low' or dividend_yield > 0.03:
            types.append('conservative')
        if risk_level in ['low', 'medium']:
            types.append('moderate')
        if risk_level in ['medium', 'high']:
            types.append('aggressive')
        return ','.join(types) if types else 'moderate'

    def _classify_category(self, market_cap: float, sector: str) -> str:
        """카테고리 분류"""
        if market_cap > 200_000_000_000:
            return 'Large Cap'
        elif market_cap > 10_000_000_000:
            return 'Mid Cap'
        elif market_cap > 2_000_000_000:
            return 'Small Cap'
        else:
            return 'Growth'
