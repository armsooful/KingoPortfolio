# backend/app/data_collector.py

import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class DataCollector:
    """외부 API에서 종목 데이터 수집"""
    
    # 수집할 한국 주식 (KOSPI)
    KOREAN_STOCKS = {
        # 전자/반도체
        "005930": "삼성전자",
        "000660": "SK하이닉스",
        "051910": "LG화학",
        "006400": "삼성SDI",
        "035420": "NAVER",
        "035720": "카카오",

        # 자동차
        "005380": "현대차",
        "000270": "기아",
        "012330": "현대모비스",

        # 금융
        "055550": "신한지주",
        "086790": "하나금융지주",
        "105560": "KB금융",
        "032830": "삼성생명",

        # 통신
        "017670": "SK텔레콤",
        "030200": "KT",
        "032640": "LG유플러스",

        # 철강/화학
        "005490": "POSCO홀딩스",
        "004020": "현대제철",
        "009830": "한화솔루션",

        # 유통/서비스
        "000120": "CJ대한통운",
        "028260": "삼성물산",
        "011200": "HMM",

        # 에너지
        "096770": "SK이노베이션",
        "034730": "SK",

        # 제약/바이오
        "207940": "삼성바이오로직스",
        "068270": "셀트리온",
        "326030": "SK바이오팜",

        # 기타
        "003550": "LG",
        "004170": "신세계",
        "011170": "롯데케미칼",
    }
    
    # 수집할 ETF
    KOREAN_ETFS = {
        # 국내 주식 ETF
        "102110": "KODEX 배당성장",
        "133690": "TIGER 200",
        "122630": "KODEX 200",
        "114800": "KODEX 인버스",
        "091160": "KODEX 반도체",
        "091180": "KODEX 자동차",
        "091170": "KODEX 은행",

        # 해외 주식 ETF
        "130680": "TIGER 미국S&P500",
        "360750": "TIGER 미국나스닥100",
        "143850": "TIGER 미국다우존스30",
        "261240": "KODEX 미국나스닥100TR",
        "379800": "KODEX 미국S&P500TR",

        # 섹터 ETF
        "117700": "KODEX 2차전지산업",
        "244580": "KODEX 2차전지핵심소재Fn",
        "228790": "KODEX 2차전지&전기차",
        "381180": "TIGER AI",
        "367770": "TIGER 2차전지테마",

        # 채권 ETF
        "148070": "KOSEF 국고채10년",
        "153130": "KODEX 단기채권",
        "130730": "KOSEF 국고채3년",

        # 기타 테마 ETF
        "227540": "TIGER 200IT",
        "227550": "TIGER 200건설",
        "182490": "TIGER 200에너지화학",
    }
    
    @staticmethod
    def fetch_stock_data(ticker: str, name: str) -> Dict:
        """yfinance에서 주식 데이터 수집

        Args:
            ticker: 티커 (예: 005930.KS)
            name: 종목명

        Returns:
            주식 데이터 딕셔너리
        """
        try:
            # yfinance에서 데이터 가져오기
            stock = yf.Ticker(f"{ticker}.KS")

            # 최근 1년 데이터 - period 사용 (datetime 문제 회피)
            hist = stock.history(period="1y")

            # 정보
            info = stock.info

            # 현재가
            current_price = hist['Close'].iloc[-1] if not hist.empty else None

            # 수익률 계산
            if not hist.empty and len(hist) > 1:
                ytd_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                one_year_return = ytd_return
            else:
                ytd_return = None
                one_year_return = None

            if ytd_return is not None:
                ytd_return = float(ytd_return)
            if one_year_return is not None:
                one_year_return = float(one_year_return)

            # 데이터가 없으면 None 반환
            if current_price is None:
                logger.warning(f"No price data for {ticker}")
                return None

            return {
                "ticker": ticker,
                "name": name,
                "current_price": float(current_price),
                "market_cap": info.get('marketCap', 0),
                "pe_ratio": info.get('trailingPE', None),
                "pb_ratio": info.get('priceToBook', None),
                "dividend_yield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else None,
                "ytd_return": ytd_return,
                "one_year_return": one_year_return,
                "sector": info.get('sector', 'Unknown'),
                "last_updated": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
            return None
    
    @staticmethod
    def fetch_etf_data(ticker: str, name: str) -> Dict:
        """ETF 데이터 수집

        Args:
            ticker: ETF 티커
            name: ETF명

        Returns:
            ETF 데이터 딕셔너리
        """
        try:
            etf = yf.Ticker(f"{ticker}.KS")

            # 최근 1년 데이터 - period 사용 (datetime 문제 회피)
            hist = etf.history(period="1y")

            info = etf.info
            current_price = hist['Close'].iloc[-1] if not hist.empty else None

            if not hist.empty and len(hist) > 1:
                ytd_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                one_year_return = ytd_return
            else:
                ytd_return = None
                one_year_return = None

            if ytd_return is not None:
                ytd_return = float(ytd_return)
            if one_year_return is not None:
                one_year_return = float(one_year_return)

            # 데이터가 없으면 None 반환
            if current_price is None:
                logger.warning(f"No price data for ETF {ticker}")
                return None

            return {
                "ticker": ticker,
                "name": name,
                "current_price": float(current_price),
                "aum": info.get('aum', 0),
                "expense_ratio": info.get('expenseRatio', 0),
                "ytd_return": ytd_return,
                "one_year_return": one_year_return,
                "last_updated": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Failed to fetch ETF data for {ticker}: {str(e)}")
            return None
    
    @staticmethod
    def fetch_naver_stock_data(ticker: str) -> Dict:
        """Naver Finance에서 상세 정보 수집 (선택)
        
        Args:
            ticker: 티커 (예: 005930)
            
        Returns:
            상세 정보
        """
        try:
            url = f"https://finance.naver.com/item/main.naver?code={ticker}"
            # Beautiful Soup으로 파싱 (구현 생략)
            # 실제 구현 시 웹 스크래핑 라이브러리 사용
            pass
        except Exception as e:
            logger.error(f"Failed to fetch Naver data for {ticker}: {str(e)}")
            return None


class DataClassifier:
    """수집한 데이터를 분류 및 태깅"""
    
    @staticmethod
    def classify_risk(pe_ratio: float = None, dividend_yield: float = None) -> str:
        """위험 수준 분류"""
        if pe_ratio and pe_ratio < 10:
            return "low"
        elif dividend_yield and dividend_yield > 5:
            return "low"
        elif pe_ratio and pe_ratio > 30:
            return "high"
        else:
            return "medium"
    
    @staticmethod
    def classify_investment_type(risk_level: str, dividend_yield: float = None) -> List[str]:
        """투자성향별 분류"""
        types = []
        
        if risk_level == "low":
            types.append("conservative")
            types.append("moderate")
        elif risk_level == "medium":
            types.append("moderate")
            types.append("aggressive")
        else:
            types.append("aggressive")
        
        if dividend_yield and dividend_yield > 4:
            types.insert(0, "conservative")
        
        return list(set(types))
    
    @staticmethod
    def classify_category(name: str, sector: str = None) -> str:
        """종목 분류"""
        keywords = {
            "배당": "배당주",
            "전자": "기술주",
            "카카오": "기술주",
            "네이버": "기술주",
            "반도체": "기술주",
            "금융": "금융주",
            "에너지": "에너지주",
            "소비": "소비재주",
            "건설": "건설주",
            "화학": "화학주",
        }
        
        for keyword, category in keywords.items():
            if keyword in name or (sector and keyword in sector):
                return category
        
        return "기타주"
