# backend/app/data_collector.py

import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DataCollector:
    """외부 API에서 종목 데이터 수집"""
    
    # 수집할 한국 주식 (KOSPI)
    KOREAN_STOCKS = {
        "005930": "삼성전자",
        "000660": "LG전자",
        "035720": "카카오",
        "005490": "POSCO홀딩스",
        "000270": "기아",
        "011200": "HMM",
        "012330": "현대모비스",
        "028260": "삼성물산",
        "004020": "현대제철",
        "017670": "SK텔레콤",
        "003550": "LG",
        "055550": "신한지주",
        "086790": "하나금융지주",
    }
    
    # 수집할 ETF
    KOREAN_ETFS = {
        "102110": "KODEX 배당성장",
        "133690": "TIGER 200",
        "122630": "KODEX 200",
        "130680": "CoTrader S&P500",
        "114800": "KODEX 인버스",
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
            
            # 최근 1년 데이터
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            hist = stock.history(start=start_date, end=end_date)
            
            # 정보
            info = stock.info
            
            # 현재가
            current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # 수익률 계산
            if not hist.empty and len(hist) > 1:
                ytd_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                one_year_return = ytd_return
            else:
                ytd_return = 0
                one_year_return = 0
            
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
            ETF 데이터 딕셋너리
        """
        try:
            etf = yf.Ticker(f"{ticker}.KS")
            
            # 최근 1년 데이터
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            hist = etf.history(start=start_date, end=end_date)
            
            info = etf.info
            current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            if not hist.empty and len(hist) > 1:
                ytd_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                one_year_return = ytd_return
            else:
                ytd_return = 0
                one_year_return = 0
            
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