# backend/app/services/alpha_vantage_client.py

import time
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from app.config import settings
from app.utils.http_client import get_with_retry

logger = logging.getLogger(__name__)


class AlphaVantageClient:
    """Alpha Vantage API 클라이언트

    무료 플랜: 25 requests/day, 5 requests/minute
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.alpha_vantage_api_key
        if not self.api_key:
            raise ValueError("Alpha Vantage API key가 설정되지 않았습니다.")

        self.request_count = 0
        self.last_request_time = None
        self.rate_limit_delay = 12  # 5 requests/minute = 12초 간격

    def _make_request(self, params: Dict) -> Optional[Dict]:
        """API 요청 (Rate limit 고려)"""
        # Rate limiting
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                logger.info(f"Rate limit: {sleep_time:.1f}초 대기 중...")
                time.sleep(sleep_time)

        params['apikey'] = self.api_key

        try:
            response = get_with_retry(self.BASE_URL, params=params, timeout=2.0, retries=2)
            response.raise_for_status()

            self.last_request_time = time.time()
            self.request_count += 1

            data = response.json()

            # API 에러 체크
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API Error: {data['Error Message']}")
                return None

            if "Note" in data:  # Rate limit 초과
                logger.warning(f"Alpha Vantage Rate Limit: {data['Note']}")
                return None

            return data

        except Exception as e:
            logger.error(f"Alpha Vantage API 요청 실패: {str(e)}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """실시간 시세 조회 (GLOBAL_QUOTE)

        Returns:
            {
                'symbol': 'IBM',
                'price': 150.25,
                'change': 2.15,
                'change_percent': '1.45%',
                'volume': 3450000,
                ...
            }
        """
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        }

        data = self._make_request(params)
        if not data or 'Global Quote' not in data:
            return None

        quote = data['Global Quote']
        if not quote:
            return None

        try:
            return {
                'symbol': quote.get('01. symbol'),
                'price': float(quote.get('05. price', 0)),
                'open': float(quote.get('02. open', 0)),
                'high': float(quote.get('03. high', 0)),
                'low': float(quote.get('04. low', 0)),
                'volume': int(quote.get('06. volume', 0)),
                'previous_close': float(quote.get('08. previous close', 0)),
                'change': float(quote.get('09. change', 0)),
                'change_percent': quote.get('10. change percent', '0%').rstrip('%'),
                'latest_trading_day': quote.get('07. latest trading day'),
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Quote 데이터 파싱 오류: {str(e)}")
            return None

    def get_company_overview(self, symbol: str) -> Optional[Dict]:
        """기업 개요 조회 (재무지표 포함)

        Returns:
            {
                'symbol': 'IBM',
                'name': 'International Business Machines',
                'sector': 'Technology',
                'market_cap': 150000000000,
                'pe_ratio': 25.5,
                'dividend_yield': 0.045,
                ...
            }
        """
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }

        data = self._make_request(params)
        if not data or not data.get('Symbol'):
            return None

        # 안전한 float 변환 헬퍼 함수
        def safe_float(value, default=0.0):
            """문자열 'None', None, 빈 문자열 등을 안전하게 float로 변환"""
            if value is None or value == '' or value == 'None':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        try:
            return {
                'symbol': data.get('Symbol'),
                'name': data.get('Name'),
                'description': data.get('Description'),
                'exchange': data.get('Exchange'),
                'sector': data.get('Sector'),
                'industry': data.get('Industry'),
                'market_cap': safe_float(data.get('MarketCapitalization')),
                'pe_ratio': safe_float(data.get('PERatio')),
                'peg_ratio': safe_float(data.get('PEGRatio')),
                'pb_ratio': safe_float(data.get('PriceToBookRatio')),
                'dividend_yield': safe_float(data.get('DividendYield')),
                'eps': safe_float(data.get('EPS')),
                'beta': safe_float(data.get('Beta')),
                'week_52_high': safe_float(data.get('52WeekHigh')),
                'week_52_low': safe_float(data.get('52WeekLow')),
                'day_50_ma': safe_float(data.get('50DayMovingAverage')),
                'day_200_ma': safe_float(data.get('200DayMovingAverage')),
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Overview 데이터 파싱 오류: {str(e)}")
            return None

    def get_daily_time_series(self, symbol: str, outputsize: str = 'compact') -> Optional[Dict]:
        """일별 시계열 데이터 조회

        Args:
            symbol: 주식 심볼
            outputsize: 'compact' (최근 100일) or 'full' (20년)

        Returns:
            {
                '2024-01-15': {
                    'open': 150.0,
                    'high': 152.0,
                    'low': 149.5,
                    'close': 151.5,
                    'volume': 1000000
                },
                ...
            }
        """
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize
        }

        data = self._make_request(params)
        if not data or 'Time Series (Daily)' not in data:
            return None

        time_series = data['Time Series (Daily)']

        try:
            result = {}
            for date_str, values in time_series.items():
                result[date_str] = {
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['5. volume'])
                }
            return result
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Time series 데이터 파싱 오류: {str(e)}")
            return None

    def get_income_statement(self, symbol: str) -> Optional[List[Dict]]:
        """손익계산서 조회

        Returns:
            [
                {
                    'fiscal_date': '2024-12-31',
                    'revenue': 100000000,
                    'gross_profit': 40000000,
                    'operating_income': 25000000,
                    'net_income': 20000000,
                    ...
                },
                ...
            ]
        """
        params = {
            'function': 'INCOME_STATEMENT',
            'symbol': symbol
        }

        data = self._make_request(params)
        if not data:
            return None

        result = []

        # Annual reports
        for report in data.get('annualReports', []):
            try:
                result.append({
                    'fiscal_date': report.get('fiscalDateEnding'),
                    'report_type': 'annual',
                    'revenue': float(report.get('totalRevenue', 0) or 0),
                    'cost_of_revenue': float(report.get('costOfRevenue', 0) or 0),
                    'gross_profit': float(report.get('grossProfit', 0) or 0),
                    'operating_income': float(report.get('operatingIncome', 0) or 0),
                    'net_income': float(report.get('netIncome', 0) or 0),
                    'ebitda': float(report.get('ebitda', 0) or 0),
                    'eps': float(report.get('reportedEPS', 0) or 0),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Income statement 파싱 오류: {str(e)}")
                continue

        # Quarterly reports
        for report in data.get('quarterlyReports', [])[:4]:  # 최근 4분기
            try:
                result.append({
                    'fiscal_date': report.get('fiscalDateEnding'),
                    'report_type': 'quarterly',
                    'revenue': float(report.get('totalRevenue', 0) or 0),
                    'cost_of_revenue': float(report.get('costOfRevenue', 0) or 0),
                    'gross_profit': float(report.get('grossProfit', 0) or 0),
                    'operating_income': float(report.get('operatingIncome', 0) or 0),
                    'net_income': float(report.get('netIncome', 0) or 0),
                    'ebitda': float(report.get('ebitda', 0) or 0),
                    'eps': float(report.get('reportedEPS', 0) or 0),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Income statement 파싱 오류: {str(e)}")
                continue

        return result if result else None

    def get_balance_sheet(self, symbol: str) -> Optional[List[Dict]]:
        """재무상태표 조회"""
        params = {
            'function': 'BALANCE_SHEET',
            'symbol': symbol
        }

        data = self._make_request(params)
        if not data:
            return None

        result = []

        # Annual reports
        for report in data.get('annualReports', []):
            try:
                result.append({
                    'fiscal_date': report.get('fiscalDateEnding'),
                    'report_type': 'annual',
                    'total_assets': float(report.get('totalAssets', 0) or 0),
                    'total_liabilities': float(report.get('totalLiabilities', 0) or 0),
                    'total_equity': float(report.get('totalShareholderEquity', 0) or 0),
                    'cash_and_equivalents': float(report.get('cashAndCashEquivalentsAtCarryingValue', 0) or 0),
                    'short_term_debt': float(report.get('shortTermDebt', 0) or 0),
                    'long_term_debt': float(report.get('longTermDebt', 0) or 0),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Balance sheet 파싱 오류: {str(e)}")
                continue

        return result if result else None

    def get_cash_flow(self, symbol: str) -> Optional[List[Dict]]:
        """현금흐름표 조회"""
        params = {
            'function': 'CASH_FLOW',
            'symbol': symbol
        }

        data = self._make_request(params)
        if not data:
            return None

        result = []

        # Annual reports
        for report in data.get('annualReports', []):
            try:
                result.append({
                    'fiscal_date': report.get('fiscalDateEnding'),
                    'report_type': 'annual',
                    'operating_cash_flow': float(report.get('operatingCashflow', 0) or 0),
                    'investing_cash_flow': float(report.get('cashflowFromInvestment', 0) or 0),
                    'financing_cash_flow': float(report.get('cashflowFromFinancing', 0) or 0),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Cash flow 파싱 오류: {str(e)}")
                continue

        return result if result else None

    def search_symbol(self, keywords: str) -> Optional[List[Dict]]:
        """심볼 검색

        Returns:
            [
                {
                    'symbol': 'IBM',
                    'name': 'International Business Machines',
                    'type': 'Equity',
                    'region': 'United States',
                    'currency': 'USD'
                },
                ...
            ]
        """
        params = {
            'function': 'SYMBOL_SEARCH',
            'keywords': keywords
        }

        data = self._make_request(params)
        if not data or 'bestMatches' not in data:
            return None

        matches = []
        for match in data['bestMatches']:
            matches.append({
                'symbol': match.get('1. symbol'),
                'name': match.get('2. name'),
                'type': match.get('3. type'),
                'region': match.get('4. region'),
                'currency': match.get('8. currency'),
            })

        return matches if matches else None
