# backend/app/data_collector.py

import os
import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# FSC API 설정
FSC_DIVIDEND_API_URL = "http://apis.data.go.kr/1160100/service/GetStocDiviInfoService/getDiviInfo"

class DataCollector:
    """외부 API에서 종목 데이터 수집"""

    # FSC API 회사명 별칭 (FSC API에서 다른 명칭 사용 시)
    FSC_COMPANY_NAME_ALIAS = {
        # 영문 -> 한글 정식명칭
        "NAVER": "네이버",
        "KT": "케이티",
        "HMM": "에이치엠엠",
        "POSCO홀딩스": "포스코홀딩스",
        # SK 계열
        "SK하이닉스": "에스케이하이닉스",
        # 지주회사
        "신한지주": "신한금융지주",
        # CJ 계열
        "CJ대한통운": "씨제이대한통운",
    }

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

    # 법인등록번호(crno) 매핑 캐시
    KOREAN_STOCKS_CRNO: Dict[str, str] = {}
    _crno_loaded = False

    @staticmethod
    def get_crno(ticker: str, company_name: Optional[str] = None) -> str:
        """종목코드로 crno 조회

        1. 캐시 확인
        2. CSV 파일 확인
        3. FSC API 조회 (회사명 필요)

        Args:
            ticker: 종목코드 (005930)
            company_name: 회사명 (삼성전자) - FSC API 조회 시 필요

        Returns:
            crno (법인등록번호) 또는 빈 문자열
        """
        # 캐시 로드
        if not DataCollector._crno_loaded:
            DataCollector._load_crno_mapping()
            DataCollector._crno_loaded = True

        # 캐시에서 조회
        if ticker in DataCollector.KOREAN_STOCKS_CRNO:
            return DataCollector.KOREAN_STOCKS_CRNO[ticker]

        # 회사명이 없으면 KOREAN_STOCKS에서 조회
        if not company_name:
            company_name = DataCollector.KOREAN_STOCKS.get(ticker)

        # 여전히 회사명이 없으면 KRX API로 조회
        if not company_name:
            company_name = DataCollector._fetch_company_name_from_krx(ticker)

        # 회사명이 있으면 FSC API로 조회
        if company_name:
            crno = DataCollector._fetch_crno_from_fsc(company_name, ticker)
            if crno:
                DataCollector.KOREAN_STOCKS_CRNO[ticker] = crno
                return crno

        return ""

    @staticmethod
    def _load_crno_mapping() -> None:
        """CSV에서 crno 매핑 로드"""
        import csv
        from pathlib import Path

        csv_path = os.getenv("STOCK_CRNO_CSV_PATH", "data/stock_crno.csv")
        path = Path(csv_path)
        if not path.exists():
            logger.debug(f"crno 매핑 파일 없음: {csv_path}")
            return
        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = (row.get("ticker") or row.get("code") or "").strip()
                    crno = (row.get("crno") or "").strip()
                    if ticker and crno:
                        DataCollector.KOREAN_STOCKS_CRNO[ticker] = crno
            logger.info(f"crno 매핑 {len(DataCollector.KOREAN_STOCKS_CRNO)}건 로드")
        except Exception as e:
            logger.warning(f"crno 매핑 로드 실패: {e}")

    @staticmethod
    def _fetch_crno_from_fsc(company_name: str, ticker: Optional[str] = None) -> Optional[str]:
        """FSC API에서 회사명으로 crno 조회

        Args:
            company_name: 회사명 (삼성전자)
            ticker: 종목코드 (옵션, ISIN 매칭용)

        Returns:
            crno 또는 None
        """
        api_key = os.getenv("FSC_DATA_GO_KR_API_KEY", "")
        if not api_key:
            logger.debug("FSC API 키 없음, crno 조회 스킵")
            return None

        # FSC API용 회사명 변환 (별칭 -> 정식명칭)
        fsc_company_name = DataCollector.FSC_COMPANY_NAME_ALIAS.get(company_name, company_name)

        try:
            params = {
                "serviceKey": api_key,
                "pageNo": 1,
                "numOfRows": 10,
                "resultType": "json",
                "stckIssuCmpyNm": fsc_company_name,
            }

            response = requests.get(FSC_DIVIDEND_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            body = data.get("response", {}).get("body", {})
            items = body.get("items", {}).get("item", [])
            if isinstance(items, dict):
                items = [items]

            if not items:
                logger.debug(f"FSC API: {company_name} 조회 결과 없음")
                return None

            # ticker가 있으면 ISIN으로 매칭 시도
            if ticker:
                for item in items:
                    isin = item.get("isinCd", "")
                    # ISIN에서 종목코드 추출 (KR7005930003 -> 005930)
                    if isin and len(isin) >= 9:
                        isin_ticker = isin[3:9]
                        if isin_ticker == ticker:
                            crno = item.get("crno")
                            if crno:
                                logger.info(f"FSC API: {company_name}({ticker}) crno={crno}")
                                return crno

            # 첫 번째 결과 반환
            crno = items[0].get("crno")
            if crno:
                logger.info(f"FSC API: {company_name} crno={crno}")
            return crno

        except Exception as e:
            logger.warning(f"FSC API crno 조회 실패 ({company_name}): {e}")
            return None

    # 회사명 캐시 (ticker -> company_name)
    _company_name_cache: Dict[str, str] = {}

    @staticmethod
    def _fetch_company_name_from_krx(ticker: str) -> Optional[str]:
        """pykrx를 사용하여 종목코드로 회사명 조회

        Args:
            ticker: 종목코드 (005930)

        Returns:
            회사명 또는 None
        """
        # 캐시 확인
        if ticker in DataCollector._company_name_cache:
            return DataCollector._company_name_cache[ticker]

        try:
            from pykrx import stock as pykrx_stock

            # pykrx로 종목명 조회
            company_name = pykrx_stock.get_market_ticker_name(ticker)

            if company_name:
                # 캐시에 저장
                DataCollector._company_name_cache[ticker] = company_name
                logger.info(f"pykrx: {ticker} -> {company_name}")
                return company_name

            logger.debug(f"pykrx: {ticker} 종목 없음")
            return None

        except Exception as e:
            logger.warning(f"pykrx 회사명 조회 실패 ({ticker}): {e}")
            return None

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
    def fetch_stock_data(ticker: str, name: str, market: Optional[str] = None) -> Dict:
        """yfinance에서 주식 데이터 수집

        Args:
            ticker: 티커 (예: 005930.KS)
            name: 종목명

        Returns:
            주식 데이터 딕셔너리
        """
        try:
            # yfinance에서 데이터 가져오기
            suffix = ".KS"
            if market == "KOSDAQ":
                suffix = ".KQ"
            stock = yf.Ticker(f"{ticker}{suffix}")

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

            # crno 조회 (FSC API 또는 캐시)
            crno = DataCollector.get_crno(ticker, name)

            return {
                "ticker": ticker,
                "name": name,
                "crno": crno,  # 법인등록번호
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
