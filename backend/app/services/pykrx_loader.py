"""pykrx를 이용한 한국 주식 데이터 수집 서비스"""

from pykrx import stock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.securities import Stock, ETF
import logging

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

    def load_all_popular_stocks(self, db: Session) -> dict:
        """인기 주식 전체 수집"""
        results = {
            'success': 0,
            'updated': 0,
            'failed': 0,
            'details': []
        }

        for ticker, name in self.POPULAR_STOCKS.items():
            result = self.load_stock_data(db, ticker, name)

            if result['success']:
                if result['action'] == 'created':
                    results['success'] += 1
                elif result['action'] == 'updated':
                    results['updated'] += 1
            else:
                results['failed'] += 1

            results['details'].append({
                'ticker': ticker,
                'name': name,
                'result': result
            })

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

    def load_all_popular_etfs(self, db: Session) -> dict:
        """인기 ETF 전체 수집"""
        results = {
            'success': 0,
            'updated': 0,
            'failed': 0,
            'details': []
        }

        for ticker, name in self.POPULAR_ETFS.items():
            result = self.load_etf_data(db, ticker, name)

            if result['success']:
                if result['action'] == 'created':
                    results['success'] += 1
                elif result['action'] == 'updated':
                    results['updated'] += 1
            else:
                results['failed'] += 1

            results['details'].append({
                'ticker': ticker,
                'name': name,
                'result': result
            })

        return results
