"""pykrx를 이용한 한국 주식 데이터 수집 서비스"""

from pykrx import stock
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import MetaData, Table, func
from app.models.securities import Stock, ETF, StockFinancials
from app.models.real_data import StockPriceDaily
from app.progress_tracker import progress_tracker
from app.database import SessionLocal
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import uuid
import pandas as pd
import threading
import time

logger = logging.getLogger(__name__)


class PyKrxDataLoader:
    """pykrx를 이용한 한국 주식 데이터 로더"""

    # 인기 대형주 (시가총액 상위)
    POPULAR_STOCKS = {
        '005930': '삼성전자',
        '000660': 'SK하이닉스',
        '005490': 'POSCO홀딩스',
        '035420': 'NAVER',
        '000270': '기아',
        '051910': 'LG화학',
        '006400': '삼성SDI',
        '035720': '카카오',
        '012330': '현대모비스',
        '028260': '삼성물산',
        '207940': '삼성바이오로직스',
        '005380': '현대차',
        '068270': '셀트리온',
        '323410': '카카오뱅크',
        '003670': '포스코퓨처엠',
        '096770': 'SK이노베이션',
        '017670': 'SK텔레콤',
        '009150': '삼성전기',
        '034730': 'SK',
        '018260': '삼성에스디에스'
    }

    # 인기 ETF
    POPULAR_ETFS = {
        '069500': 'KODEX 200',
        '152100': 'KODEX 200선물인버스2X',
        '114800': 'KODEX 인버스',
        '229200': 'KODEX 코스닥150',
        '252670': 'KODEX 200선물레버리지',
        '102110': 'TIGER 200',
        '233740': 'KODEX 코스닥150레버리지',
        '122630': 'KODEX 레버리지',
        '251340': 'KODEX 코스닥150선물인버스',
        '091160': 'KODEX 반도체'
    }

    def __init__(self):
        """초기화"""
        self.today = datetime.now().strftime('%Y%m%d')

    def _get_market_for_ticker(self, ticker: str) -> str:
        """종목 코드로 시장 구분 (KOSPI/KOSDAQ)"""
        try:
            # KOSPI 종목 리스트에서 확인
            kospi_tickers = stock.get_market_ticker_list(self.today, market="KOSPI")
            if ticker in kospi_tickers:
                return "KOSPI"

            # KOSDAQ 종목 리스트에서 확인
            kosdaq_tickers = stock.get_market_ticker_list(self.today, market="KOSDAQ")
            if ticker in kosdaq_tickers:
                return "KOSDAQ"

            return "UNKNOWN"
        except Exception as e:
            logger.error(f"Market detection failed for {ticker}: {e}")
            return "UNKNOWN"

    def _classify_risk_level(self, per: float = None, pbr: float = None, volatility: float = None) -> str:
        """위험도 분류"""
        # 간단한 분류 로직 (향후 고도화 가능)
        if per and pbr:
            if per > 30 or pbr > 3:
                return "high"
            elif per > 15 or pbr > 1.5:
                return "medium"
            else:
                return "low"
        return "medium"

    def _classify_investment_type(self, risk_level: str) -> str:
        """투자 성향 분류"""
        if risk_level == "low":
            return "conservative"
        elif risk_level == "medium":
            return "moderate"
        else:
            return "aggressive"

    def _classify_category(self, sector: str = None, market_cap: float = None) -> str:
        """카테고리 분류"""
        categories = []

        # 시가총액 기준
        if market_cap:
            if market_cap >= 10_000_000_000_000:  # 10조 이상
                categories.append("대형주")
            elif market_cap >= 1_000_000_000_000:  # 1조 이상
                categories.append("중형주")
            else:
                categories.append("소형주")

        # 섹터 기준
        if sector:
            if "반도체" in sector or "전자" in sector:
                categories.append("기술주")
            elif "금융" in sector or "은행" in sector:
                categories.append("금융주")
            elif "화학" in sector or "제약" in sector:
                categories.append("화학/제약")

        return ", ".join(categories) if categories else "일반주"

    def load_stock_data(self, db: Session, ticker: str, name: str = None) -> dict:
        """특정 주식 데이터 수집"""
        try:
            logger.info(f"Loading stock data for {ticker}")

            # 1. 기본 정보
            if not name:
                name = stock.get_market_ticker_name(ticker)

            market = self._get_market_for_ticker(ticker)

            # 2. 현재가 및 시가총액
            try:
                df_ohlcv = stock.get_market_ohlcv(self.today, self.today, ticker)
                if df_ohlcv.empty:
                    # 오늘 데이터가 없으면 최근 영업일 데이터 사용
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    df_ohlcv = stock.get_market_ohlcv(yesterday, yesterday, ticker)

                current_price = float(df_ohlcv['종가'].iloc[-1]) if not df_ohlcv.empty else None
            except Exception as e:
                logger.warning(f"OHLCV data not available for {ticker}: {e}")
                current_price = None

            # 3. 시가총액
            try:
                df_cap = stock.get_market_cap(self.today, self.today, ticker)
                if df_cap.empty:
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    df_cap = stock.get_market_cap(yesterday, yesterday, ticker)

                market_cap = float(df_cap['시가총액'].iloc[-1]) if not df_cap.empty else None
            except Exception as e:
                logger.warning(f"Market cap not available for {ticker}: {e}")
                market_cap = None

            # 4. 재무 지표 (PER, PBR, 배당수익률)
            try:
                df_fundamental = stock.get_market_fundamental(self.today, self.today, ticker)
                if df_fundamental.empty:
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    df_fundamental = stock.get_market_fundamental(yesterday, yesterday, ticker)

                if not df_fundamental.empty:
                    per = float(df_fundamental['PER'].iloc[-1]) if 'PER' in df_fundamental.columns else None
                    pbr = float(df_fundamental['PBR'].iloc[-1]) if 'PBR' in df_fundamental.columns else None
                    dividend_yield = float(df_fundamental['DIV'].iloc[-1]) if 'DIV' in df_fundamental.columns else None
                else:
                    per = pbr = dividend_yield = None
            except Exception as e:
                logger.warning(f"Fundamental data not available for {ticker}: {e}")
                per = pbr = dividend_yield = None

            # 5. 수익률 계산 (1년, YTD)
            try:
                one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
                df_year = stock.get_market_ohlcv(one_year_ago, self.today, ticker)

                if not df_year.empty and len(df_year) > 1:
                    start_price = float(df_year['종가'].iloc[0])
                    end_price = float(df_year['종가'].iloc[-1])
                    one_year_return = ((end_price - start_price) / start_price) * 100
                else:
                    one_year_return = None

                # YTD 수익률
                year_start = datetime.now().replace(month=1, day=1).strftime('%Y%m%d')
                df_ytd = stock.get_market_ohlcv(year_start, self.today, ticker)

                if not df_ytd.empty and len(df_ytd) > 1:
                    ytd_start = float(df_ytd['종가'].iloc[0])
                    ytd_end = float(df_ytd['종가'].iloc[-1])
                    ytd_return = ((ytd_end - ytd_start) / ytd_start) * 100
                else:
                    ytd_return = None
            except Exception as e:
                logger.warning(f"Return calculation failed for {ticker}: {e}")
                one_year_return = ytd_return = None

            # 6. 섹터 정보 (간단히 이름에서 추출 또는 기본값)
            sector = self._guess_sector(name)

            # 7. 분류
            risk_level = self._classify_risk_level(per, pbr)
            investment_type = self._classify_investment_type(risk_level)
            category = self._classify_category(sector, market_cap)

            # 8. DB 저장 또는 업데이트
            crno = None
            try:
                from app.data_collector import DataCollector
                crno = DataCollector.get_crno(ticker)
            except Exception:
                crno = None
            existing = db.query(Stock).filter(Stock.ticker == ticker).first()

            if existing:
                # 업데이트
                existing.name = name
                existing.market = market
                existing.sector = sector
                existing.current_price = current_price
                existing.market_cap = market_cap
                existing.pe_ratio = per
                existing.pb_ratio = pbr
                existing.dividend_yield = dividend_yield
                existing.ytd_return = ytd_return
                existing.one_year_return = one_year_return
                existing.risk_level = risk_level
                existing.investment_type = investment_type
                existing.category = category
                if crno and not existing.crno:
                    existing.crno = crno
                existing.last_updated = datetime.utcnow()

                db.commit()
                db.refresh(existing)

                return {
                    'success': True,
                    'message': f'{name} ({ticker}) 데이터 업데이트 완료',
                    'action': 'updated'
                }
            else:
                # 신규 생성
                new_stock = Stock(
                    ticker=ticker,
                    name=name,
                    market=market,
                    sector=sector,
                    crno=crno or None,
                    current_price=current_price,
                    market_cap=market_cap,
                    pe_ratio=per,
                    pb_ratio=pbr,
                    dividend_yield=dividend_yield,
                    ytd_return=ytd_return,
                    one_year_return=one_year_return,
                    risk_level=risk_level,
                    investment_type=investment_type,
                    category=category,
                    description=f"{name} - {market} 상장 종목"
                )

                db.add(new_stock)
                db.commit()
                db.refresh(new_stock)

                return {
                    'success': True,
                    'message': f'{name} ({ticker}) 데이터 수집 완료',
                    'action': 'created'
                }

        except Exception as e:
            logger.error(f"Failed to load stock {ticker}: {str(e)}")
            db.rollback()
            return {
                'success': False,
                'message': f'주식 데이터 수집 실패: {str(e)}',
                'action': 'failed'
            }

    def _guess_sector(self, name: str) -> str:
        """이름에서 섹터 추측"""
        if "전자" in name or "반도체" in name:
            return "전자/반도체"
        elif "화학" in name:
            return "화학"
        elif "금융" in name or "은행" in name:
            return "금융"
        elif "자동차" in name or "현대차" in name or "기아" in name:
            return "자동차"
        elif "바이오" in name or "제약" in name:
            return "바이오/제약"
        elif "통신" in name or "텔레콤" in name:
            return "통신"
        else:
            return "기타"

    def load_all_popular_stocks(self, db: Session, task_id: str = None) -> dict:
        """인기 주식 전체 수집"""
        # task_id가 없으면 생성
        if not task_id:
            task_id = f"pykrx_stocks_{uuid.uuid4().hex[:8]}"

        stocks_list = list(self.POPULAR_STOCKS.items())
        total_count = len(stocks_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, "pykrx 한국 주식 데이터 수집")

        results = {
            'success': 0,
            'updated': 0,
            'failed': 0,
            'details': [],
            'task_id': task_id
        }

        for idx, (ticker, name) in enumerate(stocks_list, 1):
            try:
                # 현재 처리 중인 항목 표시
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker})",
                    success=None
                )

                result = self.load_stock_data(db, ticker, name)

                if result['success']:
                    if result['action'] == 'created':
                        results['success'] += 1
                    elif result['action'] == 'updated':
                        results['updated'] += 1

                    # 성공 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker})",
                        success=True
                    )
                else:
                    results['failed'] += 1
                    # 실패 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker})",
                        success=False,
                        error=result.get('message', '데이터 수집 실패')
                    )

                results['details'].append({
                    'ticker': ticker,
                    'name': name,
                    'result': result
                })

            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")
                results['failed'] += 1
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker})",
                    success=False,
                    error=str(e)
                )

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")

        return results

    def load_etf_data(self, db: Session, ticker: str, name: str = None) -> dict:
        """ETF 데이터 수집"""
        try:
            logger.info(f"Loading ETF data for {ticker}")

            # 1. 기본 정보
            if not name:
                try:
                    ticker_name = stock.get_market_ticker_name(ticker)
                    # name이 DataFrame이나 빈 값이면 None으로 처리
                    if isinstance(ticker_name, str) and ticker_name.strip():
                        name = ticker_name
                    else:
                        name = f"ETF_{ticker}"
                except Exception as e:
                    logger.warning(f"Failed to get ETF name for {ticker}: {e}")
                    name = f"ETF_{ticker}"

            # 2. 현재가
            try:
                df_ohlcv = stock.get_market_ohlcv(self.today, self.today, ticker)
                if df_ohlcv.empty:
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    df_ohlcv = stock.get_market_ohlcv(yesterday, yesterday, ticker)

                current_price = float(df_ohlcv['종가'].iloc[-1]) if not df_ohlcv.empty else None
            except Exception as e:
                logger.warning(f"OHLCV data not available for ETF {ticker}: {e}")
                current_price = None

            # 3. 수익률
            try:
                one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
                df_year = stock.get_market_ohlcv(one_year_ago, self.today, ticker)

                if not df_year.empty and len(df_year) > 1:
                    start_price = float(df_year['종가'].iloc[0])
                    end_price = float(df_year['종가'].iloc[-1])
                    one_year_return = ((end_price - start_price) / start_price) * 100
                else:
                    one_year_return = None

                year_start = datetime.now().replace(month=1, day=1).strftime('%Y%m%d')
                df_ytd = stock.get_market_ohlcv(year_start, self.today, ticker)

                if not df_ytd.empty and len(df_ytd) > 1:
                    ytd_start = float(df_ytd['종가'].iloc[0])
                    ytd_end = float(df_ytd['종가'].iloc[-1])
                    ytd_return = ((ytd_end - ytd_start) / ytd_start) * 100
                else:
                    ytd_return = None
            except Exception as e:
                logger.warning(f"Return calculation failed for ETF {ticker}: {e}")
                one_year_return = ytd_return = None

            # 4. ETF 타입 및 분류
            etf_type = self._guess_etf_type(name)
            risk_level = self._guess_etf_risk(name)
            investment_type = self._classify_investment_type(risk_level)
            category = self._guess_etf_category(name)

            # 5. DB 저장 또는 업데이트
            existing = db.query(ETF).filter(ETF.ticker == ticker).first()

            if existing:
                existing.name = name
                existing.current_price = current_price
                existing.ytd_return = ytd_return
                existing.one_year_return = one_year_return
                existing.etf_type = etf_type
                existing.risk_level = risk_level
                existing.investment_type = investment_type
                existing.category = category
                existing.last_updated = datetime.utcnow()

                db.commit()
                db.refresh(existing)

                return {
                    'success': True,
                    'message': f'{name} ({ticker}) ETF 데이터 업데이트 완료',
                    'action': 'updated'
                }
            else:
                new_etf = ETF(
                    ticker=ticker,
                    name=name,
                    current_price=current_price,
                    ytd_return=ytd_return,
                    one_year_return=one_year_return,
                    etf_type=etf_type,
                    risk_level=risk_level,
                    investment_type=investment_type,
                    category=category,
                    description=f"{name} ETF"
                )

                db.add(new_etf)
                db.commit()
                db.refresh(new_etf)

                return {
                    'success': True,
                    'message': f'{name} ({ticker}) ETF 데이터 수집 완료',
                    'action': 'created'
                }

        except Exception as e:
            logger.error(f"Failed to load ETF {ticker}: {str(e)}")
            db.rollback()
            return {
                'success': False,
                'message': f'ETF 데이터 수집 실패: {str(e)}',
                'action': 'failed'
            }

    def _guess_etf_type(self, name: str) -> str:
        """ETF 타입 추측"""
        if "채권" in name or "bond" in name.lower():
            return "bond"
        elif "원자재" in name or "금" in name or "commodity" in name.lower():
            return "commodity"
        elif "리츠" in name or "reit" in name.lower():
            return "reits"
        else:
            return "equity"

    def _guess_etf_risk(self, name: str) -> str:
        """ETF 위험도 추측"""
        if "레버리지" in name or "2X" in name:
            return "high"
        elif "인버스" in name or "inverse" in name.lower():
            return "high"
        elif "채권" in name:
            return "low"
        else:
            return "medium"

    def _guess_etf_category(self, name: str) -> str:
        """ETF 카테고리 추측"""
        if "200" in name:
            return "KOSPI200 추종"
        elif "코스닥" in name or "KOSDAQ" in name:
            return "코스닥 추종"
        elif "레버리지" in name:
            return "레버리지"
        elif "인버스" in name:
            return "인버스"
        elif "반도체" in name:
            return "반도체"
        else:
            return "일반"

    def load_all_popular_etfs(self, db: Session, task_id: str = None) -> dict:
        """전체 ETF 종목 수집 (KRX ETF 마켓 전체)"""
        if not task_id:
            task_id = f"pykrx_etfs_{uuid.uuid4().hex[:8]}"

        # KRX에서 동적으로 전체 ETF 종목 코드 조회
        try:
            all_etf_tickers = stock.get_market_ticker_list(self.today, market="ETF")
            logger.info(f"Fetched {len(all_etf_tickers)} ETF tickers from KRX")
        except Exception as e:
            logger.warning(f"Failed to fetch ETF ticker list, falling back to popular ETFs: {e}")
            all_etf_tickers = list(self.POPULAR_ETFS.keys())

        total_count = len(all_etf_tickers)

        progress_tracker.start_task(task_id, total_count, f"pykrx 한국 ETF 전체 수집 ({total_count}종목)")

        results = {
            'success': 0,
            'updated': 0,
            'failed': 0,
            'details': [],
            'task_id': task_id,
            'total_fetched': total_count
        }

        for idx, ticker in enumerate(all_etf_tickers, 1):
            try:
                # 종목명 조회
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if not isinstance(name, str) or not name.strip():
                        name = f"ETF_{ticker}"
                except Exception:
                    name = f"ETF_{ticker}"

                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker})",
                    success=None
                )

                result = self.load_etf_data(db, ticker, name)

                if result['success']:
                    if result['action'] == 'created':
                        results['success'] += 1
                    elif result['action'] == 'updated':
                        results['updated'] += 1

                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker})",
                        success=True
                    )
                else:
                    results['failed'] += 1
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker})",
                        success=False,
                        error=result.get('message', 'ETF 데이터 수집 실패')
                    )

                results['details'].append({
                    'ticker': ticker,
                    'name': name,
                    'result': result
                })

            except Exception as e:
                logger.error(f"Error processing ETF {ticker}: {str(e)}")
                results['failed'] += 1
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=ticker,
                    success=False,
                    error=str(e)
                )

        progress_tracker.complete_task(task_id, "completed")

        return results

    def load_stock_financials(self, db: Session, ticker: str, name: str = None) -> dict:
        """특정 주식의 재무제표 데이터 수집"""
        try:
            logger.info(f"Loading financial data for {ticker}")

            # 기본 정보
            if not name:
                name = stock.get_market_ticker_name(ticker)

            # 최근 영업일 기준으로 데이터 수집 (연말 기준이 아닌 최근 데이터)
            # pykrx는 실제 재무제표를 제공하지 않고 PER, PBR, EPS, BPS, DIV만 제공
            try:
                # 최근 3개월 데이터 조회 (연말 기준이 아닌 가용한 최근 데이터)
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

                df = stock.get_market_fundamental_by_date(
                    start_date, end_date, ticker
                )

                if df.empty:
                    logger.warning(f"No fundamental data available for {ticker}")
                    return {
                        'success': False,
                        'message': f'{name} ({ticker}) 재무 지표 데이터 없음 (pykrx는 재무제표 상세 데이터를 제공하지 않습니다)',
                        'action': 'failed'
                    }

                # 가장 최근 데이터 사용
                latest_data = df.iloc[-1]
                latest_date = df.index[-1]

                per = latest_data.get('PER', None)
                pbr = latest_data.get('PBR', None)
                eps = latest_data.get('EPS', None)
                bps = latest_data.get('BPS', None)
                div_yield = latest_data.get('DIV', None)

                # 시가총액 데이터로 재무 지표 역산
                cap_end = end_date
                cap_start = start_date
                df_cap = stock.get_market_cap_by_date(cap_start, cap_end, ticker)

                if df_cap.empty:
                    logger.warning(f"No market cap data for {ticker}")
                    return {
                        'success': False,
                        'message': f'{name} ({ticker}) 시가총액 데이터 없음',
                        'action': 'failed'
                    }

                cap_latest = df_cap.iloc[-1]
                market_cap = cap_latest.get('시가총액', 0)
                shares = cap_latest.get('상장주식수', 0)

                # 재무 데이터 계산 (추정치)
                # 순이익 = EPS * 상장주식수
                net_income = eps * shares if eps and shares else None

                # 자본총계 = BPS * 상장주식수
                total_equity = bps * shares if bps and shares else None

                # PBR을 이용한 자본총계 재계산 (더 정확)
                if pbr and pbr > 0 and market_cap and market_cap > 0:
                    calc_equity = market_cap / pbr
                    if not total_equity or abs(total_equity - calc_equity) / calc_equity > 0.1:
                        total_equity = calc_equity

                # 간단한 추정 (부채비율을 1.0으로 가정 - 실제 데이터 없음)
                total_assets = total_equity * 2 if total_equity else None
                total_liabilities = total_assets - total_equity if total_assets and total_equity else None

                # 재무 비율 계산
                roe = (net_income / total_equity * 100) if net_income and total_equity and total_equity > 0 else None
                roa = (net_income / total_assets * 100) if net_income and total_assets and total_assets > 0 else None
                debt_to_equity = (total_liabilities / total_equity) if total_liabilities and total_equity and total_equity > 0 else None

                # DB 저장 (최근 데이터 기준)
                fiscal_date = latest_date.date() if hasattr(latest_date, 'date') else latest_date

                existing = db.query(StockFinancials).filter(
                    StockFinancials.ticker == ticker,
                    StockFinancials.fiscal_date == fiscal_date,
                    StockFinancials.report_type == 'recent'
                ).first()

                if existing:
                    # 업데이트
                    existing.net_income = net_income
                    existing.total_assets = total_assets
                    existing.total_liabilities = total_liabilities
                    existing.total_equity = total_equity
                    existing.roe = roe
                    existing.roa = roa
                    existing.debt_to_equity = debt_to_equity
                    existing.last_updated = datetime.utcnow()

                    db.commit()
                    logger.info(f"Updated financial data for {ticker} - {fiscal_date}")

                    return {
                        'success': True,
                        'message': f'{name} ({ticker}) 재무 지표 업데이트 완료 (최근 데이터: {fiscal_date})',
                        'action': 'completed',
                        'details': {'success': 0, 'updated': 1, 'failed': 0}
                    }
                else:
                    # 신규 생성
                    financial = StockFinancials(
                        ticker=ticker,
                        fiscal_date=fiscal_date,
                        report_type='recent',
                        net_income=net_income,
                        total_assets=total_assets,
                        total_liabilities=total_liabilities,
                        total_equity=total_equity,
                        roe=roe,
                        roa=roa,
                        debt_to_equity=debt_to_equity
                    )
                    db.add(financial)
                    db.commit()
                    logger.info(f"Saved new financial data for {ticker} - {fiscal_date}")

                    return {
                        'success': True,
                        'message': f'{name} ({ticker}) 재무 지표 수집 완료 (최근 데이터: {fiscal_date})',
                        'action': 'completed',
                        'details': {'success': 1, 'updated': 0, 'failed': 0}
                    }

            except Exception as e:
                logger.error(f"Failed to process financial data for {ticker}: {str(e)}", exc_info=True)
                db.rollback()
                return {
                    'success': False,
                    'message': f'{name} ({ticker}) 재무 지표 처리 실패: {str(e)}',
                    'action': 'failed'
                }

        except Exception as e:
            logger.error(f"Failed to load financials for {ticker}: {str(e)}", exc_info=True)
            db.rollback()
            return {
                'success': False,
                'message': f'재무 지표 수집 실패: {str(e)}',
                'action': 'failed'
            }

    def load_all_stock_financials(self, db: Session, task_id: str = None) -> dict:
        """인기 주식 전체 재무제표 수집"""
        # task_id가 없으면 생성
        if not task_id:
            task_id = f"pykrx_financials_{uuid.uuid4().hex[:8]}"

        stocks_list = list(self.POPULAR_STOCKS.items())
        total_count = len(stocks_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, "pykrx 한국 주식 재무제표 수집")

        results = {
            'success': 0,
            'updated': 0,
            'failed': 0,
            'details': [],
            'task_id': task_id
        }

        for idx, (ticker, name) in enumerate(stocks_list, 1):
            try:
                # 현재 처리 중인 항목 표시
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker}) 재무제표",
                    success=None
                )

                result = self.load_stock_financials(db, ticker, name)

                if result['success']:
                    # 상세 결과에서 카운트 추출
                    if 'details' in result:
                        results['success'] += result['details'].get('success', 0)
                        results['updated'] += result['details'].get('updated', 0)
                        results['failed'] += result['details'].get('failed', 0)
                    else:
                        results['success'] += 1

                    # 성공 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker}) 재무제표",
                        success=True
                    )
                else:
                    results['failed'] += 1
                    # 실패 업데이트
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker}) 재무제표",
                        success=False,
                        error=result.get('message', '재무제표 수집 실패')
                    )

                results['details'].append({
                    'ticker': ticker,
                    'name': name,
                    'result': result
                })

            except Exception as e:
                logger.error(f"Error processing financials for {ticker}: {str(e)}")
                results['failed'] += 1
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker}) 재무제표",
                    success=False,
                    error=str(e)
                )

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")

        return results

    # ========================================================================
    # stock_price_daily 테이블 적재
    # ========================================================================

    def load_daily_prices(
        self,
        db: Session,
        ticker: str,
        start_date: str,
        end_date: str,
        name: str = None,
        source_id: str = 'PYKRX',
    ) -> Dict[str, Any]:
        """특정 종목의 일별 시세를 stock_price_daily 테이블에 적재 (순차 N+1 방식)

        Args:
            db: SQLAlchemy Session
            ticker: 종목코드 (예: '005930')
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            name: 종목명 (선택)
            source_id: 데이터 소스 ID (기본 'PYKRX')

        Returns:
            dict: {'success': bool, 'message': str, 'inserted': int, 'updated': int}
        """
        try:
            if not name:
                name = stock.get_market_ticker_name(ticker) or ticker

            logger.info(f"Loading daily prices for {name} ({ticker}): {start_date} ~ {end_date}")

            # pykrx로 OHLCV 데이터 조회
            df = stock.get_market_ohlcv(start_date, end_date, ticker)

            if df.empty:
                logger.warning(f"No price data for {ticker} in {start_date} ~ {end_date}")
                return {
                    'success': True,
                    'message': f'{name} ({ticker}) 해당 기간 데이터 없음',
                    'inserted': 0,
                    'updated': 0
                }

            inserted = 0
            updated = 0

            for trade_date_idx, row in df.iterrows():
                if hasattr(trade_date_idx, 'date'):
                    td = trade_date_idx.date()
                elif isinstance(trade_date_idx, str):
                    td = datetime.strptime(trade_date_idx, '%Y-%m-%d').date()
                else:
                    td = trade_date_idx

                existing = db.query(StockPriceDaily).filter(
                    StockPriceDaily.ticker == ticker,
                    StockPriceDaily.trade_date == td,
                    StockPriceDaily.source_id == source_id,
                ).first()

                if existing:
                    existing.open_price = Decimal(str(row['시가'])) if pd.notna(row['시가']) else Decimal('0')
                    existing.high_price = Decimal(str(row['고가'])) if pd.notna(row['고가']) else Decimal('0')
                    existing.low_price = Decimal(str(row['저가'])) if pd.notna(row['저가']) else Decimal('0')
                    existing.close_price = Decimal(str(row['종가'])) if pd.notna(row['종가']) else Decimal('0')
                    existing.volume = int(row['거래량']) if pd.notna(row['거래량']) else 0
                    existing.change_rate = Decimal(str(row['등락률'])) if '등락률' in row and pd.notna(row['등락률']) else None
                    updated += 1
                else:
                    new_record = StockPriceDaily(
                        ticker=ticker,
                        trade_date=td,
                        open_price=Decimal(str(row['시가'])) if pd.notna(row['시가']) else Decimal('0'),
                        high_price=Decimal(str(row['고가'])) if pd.notna(row['고가']) else Decimal('0'),
                        low_price=Decimal(str(row['저가'])) if pd.notna(row['저가']) else Decimal('0'),
                        close_price=Decimal(str(row['종가'])) if pd.notna(row['종가']) else Decimal('0'),
                        volume=int(row['거래량']) if pd.notna(row['거래량']) else 0,
                        change_rate=Decimal(str(row['등락률'])) if '등락률' in row and pd.notna(row['등락률']) else None,
                        source_id=source_id,
                        as_of_date=td,
                        quality_flag='NORMAL',
                    )
                    db.add(new_record)
                    inserted += 1

            db.commit()

            logger.info(f"Loaded {inserted} new, {updated} updated records for {ticker}")
            return {
                'success': True,
                'message': f'{name} ({ticker}) 시세 적재 완료: 신규 {inserted}건, 업데이트 {updated}건',
                'inserted': inserted,
                'updated': updated
            }

        except Exception as e:
            logger.error(f"Failed to load daily prices for {ticker}: {str(e)}")
            db.rollback()
            return {
                'success': False,
                'message': f'{ticker} 시세 적재 실패: {str(e)}',
                'inserted': 0,
                'updated': 0
            }

    def load_daily_prices_batch(
        self,
        db: Session,
        ticker: str,
        start_date: str,
        end_date: str,
        name: str = None,
        batch_size: int = 500,
        source_id: str = 'PYKRX',
        batch_id: int = None,
    ) -> Dict[str, Any]:
        """일별 시세 배치 적재 (PostgreSQL ON CONFLICT 사용)

        stock_price_daily 테이블에 적재.
        PostgreSQL의 INSERT ... ON CONFLICT DO UPDATE를 사용하여
        N+1 쿼리 문제를 단일 쿼리로 해결합니다.

        Args:
            db: SQLAlchemy Session
            ticker: 종목코드 (예: '005930')
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            name: 종목명 (선택, 로깅용)
            batch_size: 배치 크기 (기본 500, 대용량 시 분할 처리)
            source_id: 데이터 소스 ID (기본 'PYKRX')
            batch_id: 배치 ID (선택)

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'inserted': int,
                'updated': int
            }
        """
        try:
            if not name:
                name = stock.get_market_ticker_name(ticker) or ticker

            logger.info(f"[BATCH] Loading {name} ({ticker}): {start_date}~{end_date}")

            # 1. pykrx로 OHLCV 데이터 조회
            df = stock.get_market_ohlcv(start_date, end_date, ticker)

            if df.empty:
                logger.warning(f"[BATCH] No price data for {ticker} in {start_date} ~ {end_date}")
                return {
                    'success': True,
                    'message': f'{name} ({ticker}) 해당 기간 데이터 없음',
                    'inserted': 0,
                    'updated': 0
                }

            # 2. 레코드 변환 — stock_price_daily 컬럼 매핑
            records = []
            for trade_date_idx, row in df.iterrows():
                if hasattr(trade_date_idx, 'date'):
                    td = trade_date_idx.date()
                elif isinstance(trade_date_idx, str):
                    td = datetime.strptime(trade_date_idx, '%Y-%m-%d').date()
                else:
                    td = trade_date_idx

                record = {
                    'ticker': ticker,
                    'trade_date': td,
                    'open_price': Decimal(str(row['시가'])) if pd.notna(row['시가']) else Decimal('0'),
                    'high_price': Decimal(str(row['고가'])) if pd.notna(row['고가']) else Decimal('0'),
                    'low_price': Decimal(str(row['저가'])) if pd.notna(row['저가']) else Decimal('0'),
                    'close_price': Decimal(str(row['종가'])) if pd.notna(row['종가']) else Decimal('0'),
                    'volume': int(row['거래량']) if pd.notna(row['거래량']) else 0,
                    'change_rate': Decimal(str(row['등락률'])) if '등락률' in row and pd.notna(row['등락률']) else None,
                    'source_id': source_id,
                    'as_of_date': td,
                    'quality_flag': 'NORMAL',
                }
                if batch_id:
                    record['batch_id'] = batch_id
                records.append(record)

            # 3. PostgreSQL ON CONFLICT 배치 upsert → stock_price_daily
            table = StockPriceDaily.__table__

            total_records = 0
            for i in range(0, len(records), batch_size):
                chunk = records[i:i + batch_size]

                stmt = pg_insert(table).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_stock_price_daily',
                    set_={
                        'open_price': stmt.excluded.open_price,
                        'high_price': stmt.excluded.high_price,
                        'low_price': stmt.excluded.low_price,
                        'close_price': stmt.excluded.close_price,
                        'volume': stmt.excluded.volume,
                        'change_rate': stmt.excluded.change_rate,
                        'updated_at': func.now(),
                    }
                )

                db.execute(stmt)
                total_records += len(chunk)

            db.commit()

            logger.info(f"[BATCH] Loaded {total_records} records for {ticker}")
            return {
                'success': True,
                'message': f'{name} ({ticker}) 배치 upsert 완료: {total_records}건',
                'inserted': total_records,
                'updated': 0  # ON CONFLICT는 insert/update 구분 불가
            }

        except Exception as e:
            logger.error(f"[BATCH] Failed to load daily prices for {ticker}: {str(e)}")
            db.rollback()
            return {
                'success': False,
                'message': f'{ticker} 배치 적재 실패: {str(e)}',
                'inserted': 0,
                'updated': 0
            }

    def load_all_daily_prices(
        self,
        db: Session,
        start_date: str,
        end_date: str,
        tickers: Optional[List[str]] = None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """여러 종목의 일별 시세를 일괄 적재

        Args:
            db: SQLAlchemy Session
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            tickers: 종목코드 리스트 (None이면 POPULAR_STOCKS 사용)
            task_id: 진행률 추적용 태스크 ID

        Returns:
            dict: 적재 결과 요약
        """
        if not task_id:
            task_id = f"pykrx_daily_prices_{uuid.uuid4().hex[:8]}"

        # 대상 종목 결정
        if tickers:
            stocks_list = [(t, stock.get_market_ticker_name(t) or t) for t in tickers]
        else:
            stocks_list = list(self.POPULAR_STOCKS.items())

        total_count = len(stocks_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(task_id, total_count, f"pykrx 일별 시세 수집 ({start_date}~{end_date})")

        results = {
            'success': 0,
            'failed': 0,
            'total_inserted': 0,
            'total_updated': 0,
            'details': [],
            'task_id': task_id
        }

        for idx, (ticker, name) in enumerate(stocks_list, 1):
            try:
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker})",
                    success=None
                )

                result = self.load_daily_prices(db, ticker, start_date, end_date, name)

                if result['success']:
                    results['success'] += 1
                    results['total_inserted'] += result['inserted']
                    results['total_updated'] += result['updated']

                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker})",
                        success=True
                    )
                else:
                    results['failed'] += 1
                    progress_tracker.update_progress(
                        task_id,
                        current=idx,
                        current_item=f"{name} ({ticker})",
                        success=False,
                        error=result.get('message', '시세 적재 실패')
                    )

                results['details'].append({
                    'ticker': ticker,
                    'name': name,
                    'result': result
                })

            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")
                results['failed'] += 1
                progress_tracker.update_progress(
                    task_id,
                    current=idx,
                    current_item=f"{name} ({ticker})",
                    success=False,
                    error=str(e)
                )

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")

        return results

    def load_all_daily_prices_parallel(
        self,
        db: Session,
        start_date: str,
        end_date: str,
        tickers: Optional[List[str]] = None,
        task_id: str = None,
        num_workers: int = 8,
        source_id: str = 'PYKRX',
        batch_id: int = None,
    ) -> Dict[str, Any]:
        """여러 종목의 일별 시세를 병렬로 적재 (성능 최적화)

        Args:
            db: SQLAlchemy Session (메인 스레드용)
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            tickers: 종목코드 리스트 (None이면 POPULAR_STOCKS 사용)
            task_id: 진행률 추적용 태스크 ID
            num_workers: 동시 스레드 수 (기본값 8, CPU 코어 수의 2배 권장)
            source_id: 데이터 소스 ID (기본 'PYKRX')
            batch_id: 배치 ID (선택)

        Returns:
            dict: 적재 결과 요약
        """
        if not task_id:
            task_id = f"pykrx_daily_prices_parallel_{uuid.uuid4().hex[:8]}"

        # 대상 종목 결정
        if tickers:
            stocks_list = [(t, stock.get_market_ticker_name(t) or t) for t in tickers]
        else:
            stocks_list = list(self.POPULAR_STOCKS.items())

        total_count = len(stocks_list)

        # 진행 상황 추적 시작
        progress_tracker.start_task(
            task_id,
            total_count,
            f"pykrx 일별 시세 병렬 수집 ({start_date}~{end_date}, {num_workers}개 스레드)"
        )

        results = {
            'success': 0,
            'failed': 0,
            'total_inserted': 0,
            'total_updated': 0,
            'details': [],
            'task_id': task_id,
            'num_workers': num_workers
        }

        # 스레드 안전한 결과 누적을 위한 Lock
        results_lock = threading.Lock()
        completed_count = [0]  # 뮤터블 카운터

        def fetch_and_load(ticker: str, name: str, ticker_idx: int) -> Dict[str, Any]:
            """스레드 워커: 개별 종목 적재"""
            try:
                # 스레드별 독립 DB 세션
                db_local = SessionLocal()

                try:
                    result = self.load_daily_prices_batch(
                        db_local, ticker, start_date, end_date, name,
                        source_id=source_id, batch_id=batch_id,
                    )

                    # 스레드 안전한 결과 누적
                    with results_lock:
                        completed_count[0] += 1

                        if result['success']:
                            results['success'] += 1
                            results['total_inserted'] += result['inserted']
                            results['total_updated'] += result['updated']
                            success_flag = True
                        else:
                            results['failed'] += 1
                            success_flag = False

                        results['details'].append({
                            'ticker': ticker,
                            'name': name,
                            'result': result
                        })

                        # 5개 항목마다 진행률 업데이트 (오버헤드 감소)
                        if completed_count[0] % 5 == 0 or completed_count[0] == total_count:
                            progress_tracker.update_progress(
                                task_id,
                                current=completed_count[0],
                                current_item=f"{name} ({ticker})",
                                success=success_flag
                            )

                    return {
                        'ticker': ticker,
                        'success': result['success'],
                        'inserted': result['inserted'],
                        'updated': result['updated']
                    }

                finally:
                    db_local.close()

            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")

                with results_lock:
                    completed_count[0] += 1
                    results['failed'] += 1
                    results['details'].append({
                        'ticker': ticker,
                        'name': name,
                        'result': {
                            'success': False,
                            'message': f'{ticker} 시세 적재 실패: {str(e)}',
                            'inserted': 0,
                            'updated': 0
                        }
                    })

                    if completed_count[0] % 5 == 0 or completed_count[0] == total_count:
                        progress_tracker.update_progress(
                            task_id,
                            current=completed_count[0],
                            current_item=f"{name} ({ticker})",
                            success=False,
                            error=str(e)
                        )

                return {
                    'ticker': ticker,
                    'success': False,
                    'inserted': 0,
                    'updated': 0
                }

        # 병렬 처리 시작
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 모든 종목의 작업 제출
            futures = {
                executor.submit(fetch_and_load, ticker, name, idx): (ticker, name)
                for idx, (ticker, name) in enumerate(stocks_list)
            }

            # 완료된 것부터 수집 (순서 무관)
            for future in as_completed(futures):
                ticker, name = futures[future]
                try:
                    _ = future.result()  # 예외 확인용
                except Exception as e:
                    logger.error(f"Future exception for {ticker}: {e}")

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")

        logger.info(
            f"Parallel load completed: success={results['success']}, "
            f"failed={results['failed']}, "
            f"inserted={results['total_inserted']}, "
            f"updated={results['total_updated']}"
        )

        return results

    def load_daily_prices_by_market(
        self,
        db: Session,
        market: str,
        start_date: str,
        end_date: str,
        limit: int = None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """시장별 전체 종목 일별 시세 적재

        Args:
            db: SQLAlchemy Session
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            limit: 최대 종목 수 (테스트용)
            task_id: 진행률 추적용 태스크 ID

        Returns:
            dict: 적재 결과 요약
        """
        if not task_id:
            task_id = f"pykrx_market_prices_{market}_{uuid.uuid4().hex[:8]}"

        # 시장별 종목 리스트 조회
        tickers = []
        if market.upper() == 'ALL':
            tickers.extend(stock.get_market_ticker_list(self.today, market="KOSPI"))
            tickers.extend(stock.get_market_ticker_list(self.today, market="KOSDAQ"))
        else:
            tickers = stock.get_market_ticker_list(self.today, market=market.upper())

        if limit:
            tickers = tickers[:limit]

        logger.info(f"Loading daily prices for {len(tickers)} tickers in {market}")

        return self.load_all_daily_prices(db, start_date, end_date, tickers, task_id)

    def load_all_stocks_incremental(
        self,
        db: Session,
        default_days: int = 1825,
        task_id: str = None,
        num_workers: int = 4,
        source_id: str = 'PYKRX',
        batch_id: int = None,
        market: str = None,
        progress_callback: Callable = None,
    ) -> Dict[str, Any]:
        """stocks 테이블 전체 종목 대상 증분 시계열 적재

        이미 적재된 종목은 마지막 적재일 다음 날부터, 미적재 종목은 default_days 전부터 수집.

        Args:
            db: SQLAlchemy Session (메인 스레드용, 종목 목록 조회)
            default_days: 신규 종목 기본 수집 일수 (기본 1825 = 5년)
            task_id: 진행률 추적용 태스크 ID
            num_workers: 동시 스레드 수 (기본 4, 8GB RAM 환경 고려)
            source_id: 데이터 소스 ID
            batch_id: 배치 ID (선택)
            market: 시장 필터 ('KOSPI', 'KOSDAQ', None=전체)
            progress_callback: 진행 콜백 (count, message)

        Returns:
            dict: 적재 결과 요약
        """
        if not task_id:
            task_id = f"incremental_{uuid.uuid4().hex[:8]}"

        today = date.today()
        today_str = today.strftime('%Y%m%d')

        # Step 1: stocks 테이블에서 활성 종목 조회
        query = db.query(Stock.ticker, Stock.name)
        if market:
            query = query.filter(Stock.market == market.upper())
        all_stocks = query.all()

        if not all_stocks:
            logger.warning("No stocks found in stocks table")
            return {
                'success': 0, 'failed': 0, 'skipped': 0,
                'total_inserted': 0, 'task_id': task_id,
                'details': [], 'message': 'stocks 테이블에 종목이 없습니다'
            }

        # Step 2: 종목별 마지막 적재일 조회 (1회 쿼리)
        last_dates_rows = (
            db.query(
                StockPriceDaily.ticker,
                func.max(StockPriceDaily.trade_date).label('last_date')
            )
            .filter(StockPriceDaily.source_id == source_id)
            .group_by(StockPriceDaily.ticker)
            .all()
        )
        last_dates = {row.ticker: row.last_date for row in last_dates_rows}

        # Step 3: 종목별 수집 기간 계산
        tasks_list = []  # (ticker, name, start_str, end_str, is_incremental)
        skip_count = 0
        new_count = 0
        incremental_count = 0

        default_start = today - timedelta(days=default_days)

        for ticker, name in all_stocks:
            last_date = last_dates.get(ticker)
            if last_date:
                start = last_date + timedelta(days=1)
                if start > today:
                    skip_count += 1
                    continue
                tasks_list.append((ticker, name or ticker, start.strftime('%Y%m%d'), today_str, True))
                incremental_count += 1
            else:
                tasks_list.append((ticker, name or ticker, default_start.strftime('%Y%m%d'), today_str, False))
                new_count += 1

        total_count = len(tasks_list)
        logger.info(
            f"Incremental load: total={len(all_stocks)}, "
            f"new={new_count}, incremental={incremental_count}, skip={skip_count}"
        )

        # 진행 상황 추적 시작
        progress_tracker.start_task(
            task_id,
            total_count,
            f"증분 시계열 적재 (신규 {new_count}, 증분 {incremental_count}, 스킵 {skip_count})"
        )

        if total_count == 0:
            progress_tracker.complete_task(task_id, "completed")
            return {
                'success': 0, 'failed': 0, 'skipped': skip_count,
                'total_inserted': 0, 'task_id': task_id,
                'new_stocks': new_count, 'incremental_stocks': incremental_count,
                'details': [], 'message': '모든 종목이 최신 상태입니다'
            }

        # Step 4: 병렬 수집 + 배치 upsert
        results = {
            'success': 0,
            'failed': 0,
            'skipped': skip_count,
            'total_inserted': 0,
            'new_stocks': new_count,
            'incremental_stocks': incremental_count,
            'details': [],
            'task_id': task_id,
            'num_workers': num_workers,
        }

        results_lock = threading.Lock()
        completed_count = [0]

        def fetch_and_load(ticker: str, name: str, start_str: str, end_str: str, is_incremental: bool):
            """스레드 워커: 개별 종목 증분 적재"""
            try:
                db_local = SessionLocal()
                try:
                    result = self.load_daily_prices_batch(
                        db_local, ticker, start_str, end_str, name,
                        source_id=source_id, batch_id=batch_id,
                    )

                    with results_lock:
                        completed_count[0] += 1
                        current = completed_count[0]

                        if result['success']:
                            results['success'] += 1
                            results['total_inserted'] += result['inserted']
                            success_flag = True
                        else:
                            results['failed'] += 1
                            success_flag = False

                        results['details'].append({
                            'ticker': ticker,
                            'name': name,
                            'incremental': is_incremental,
                            'result': result
                        })

                        # 10건마다 또는 마지막 항목에 진행률 업데이트
                        if current % 10 == 0 or current == total_count:
                            label = "증분" if is_incremental else "신규"
                            progress_tracker.update_progress(
                                task_id,
                                current=current,
                                current_item=f"[{label}] {name} ({ticker})",
                                success=success_flag
                            )

                        if progress_callback and (current % 10 == 0 or current == total_count):
                            progress_callback(current, f"{name} ({ticker})")

                finally:
                    db_local.close()

                # pykrx 호출 간격 (KRX 서버 부하 방지)
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")

                with results_lock:
                    completed_count[0] += 1
                    current = completed_count[0]
                    results['failed'] += 1
                    results['details'].append({
                        'ticker': ticker,
                        'name': name,
                        'incremental': is_incremental,
                        'result': {
                            'success': False,
                            'message': f'{ticker} 적재 실패: {str(e)}',
                            'inserted': 0,
                            'updated': 0
                        }
                    })

                    if current % 10 == 0 or current == total_count:
                        progress_tracker.update_progress(
                            task_id,
                            current=current,
                            current_item=f"{name} ({ticker})",
                            success=False,
                            error=str(e)
                        )

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(
                    fetch_and_load, ticker, name, start_str, end_str, is_inc
                ): ticker
                for ticker, name, start_str, end_str, is_inc in tasks_list
            }

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Future exception for {ticker}: {e}")

        # 작업 완료
        progress_tracker.complete_task(task_id, "completed")

        logger.info(
            f"Incremental load completed: success={results['success']}, "
            f"failed={results['failed']}, skipped={results['skipped']}, "
            f"inserted={results['total_inserted']}"
        )

        return results
