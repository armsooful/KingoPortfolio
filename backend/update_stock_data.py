#!/usr/bin/env python3
"""
주식 데이터 수집 및 업데이트 스크립트
pykrx를 사용하여 한국 주식시장 데이터를 수집합니다.
"""

import sys
from datetime import datetime, timedelta
from pykrx import stock
from app.database import SessionLocal
from app.models.securities import Stock
from sqlalchemy import func

# 섹터 매핑 (한국 업종 → 표준 섹터)
SECTOR_MAPPING = {
    "반도체": "IT",
    "전기전자": "IT",
    "컴퓨터": "IT",
    "소프트웨어": "IT",
    "통신장비": "IT",
    "인터넷": "IT",
    "게임": "IT",
    "전자장비": "IT",

    "은행": "금융",
    "증권": "금융",
    "보험": "금융",
    "금융": "금융",
    "지주회사": "금융",

    "자동차": "자동차",
    "운송": "자동차",
    "운송장비": "자동차",

    "화학": "화학",
    "정유": "화학",
    "화장품": "화학",

    "제약": "헬스케어",
    "바이오": "헬스케어",
    "의료기기": "헬스케어",
    "병원": "헬스케어",

    "식품": "필수소비재",
    "음료": "필수소비재",
    "담배": "필수소비재",

    "유통": "소비재",
    "백화점": "소비재",
    "미디어": "소비재",
    "엔터테인먼트": "소비재",
    "의류": "소비재",

    "건설": "산업재",
    "조선": "산업재",
    "기계": "산업재",
    "철강": "산업재",
    "항공": "산업재",

    "전기": "에너지",
    "가스": "에너지",
    "전력": "에너지",

    "2차전지": "2차전지",
    "배터리": "2차전지",
}

# KOSPI/KOSDAQ 주요 종목 리스트 (시가총액 상위)
MAJOR_TICKERS = [
    # 대형주
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "373220",  # LG에너지솔루션
    "207940",  # 삼성바이오로직스
    "005380",  # 현대차
    "000270",  # 기아
    "051910",  # LG화학
    "006400",  # 삼성SDI
    "035420",  # NAVER
    "035720",  # 카카오
    "068270",  # 셀트리온
    "028260",  # 삼성물산
    "105560",  # KB금융
    "055550",  # 신한지주
    "012330",  # 현대모비스
    "066570",  # LG전자
    "096770",  # SK이노베이션
    "003550",  # LG
    "017670",  # SK텔레콤
    "034730",  # SK

    # 중형주 (우량주)
    "009150",  # 삼성전기
    "018260",  # 삼성에스디에스
    "032830",  # 삼성생명
    "086790",  # 하나금융지주
    "024110",  # 기업은행
    "316140",  # 우리금융지주
    "000810",  # 삼성화재
    "033780",  # KT&G
    "011170",  # 롯데케미칼
    "010130",  # 고려아연
    "009830",  # 한화솔루션
    "015760",  # 한국전력
    "032640",  # LG유플러스
    "030200",  # KT
    "000720",  # 현대건설

    # 성장주
    "247540",  # 에코프로비엠
    "086520",  # 에코프로
    "003670",  # 포스코퓨처엠
    "161390",  # 한국타이어앤테크놀로지
    "011200",  # HMM
    "010140",  # 삼성중공업
    "047810",  # 한국항공우주
    "352820",  # 하이브
    "036570",  # 엔씨소프트
    "251270",  # 넷마블
    "041510",  # 에스엠
    "122870",  # YG엔터테인먼트

    # 배당주
    "010950",  # S-Oil
    "078930",  # GS
    "000080",  # 하이트진로
    "004020",  # 현대제철
]

# 티커-종목명 매핑 (pykrx 2026년 미지원 대응)
TICKER_NAMES = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스",
    "005380": "현대차",
    "000270": "기아",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "035420": "NAVER",
    "035720": "카카오",
    "068270": "셀트리온",
    "028260": "삼성물산",
    "105560": "KB금융",
    "055550": "신한지주",
    "012330": "현대모비스",
    "066570": "LG전자",
    "096770": "SK이노베이션",
    "003550": "LG",
    "017670": "SK텔레콤",
    "034730": "SK",
    "009150": "삼성전기",
    "018260": "삼성에스디에스",
    "032830": "삼성생명",
    "086790": "하나금융지주",
    "024110": "기업은행",
    "316140": "우리금융지주",
    "000810": "삼성화재",
    "033780": "KT&G",
    "011170": "롯데케미칼",
    "010130": "고려아연",
    "009830": "한화솔루션",
    "015760": "한국전력",
    "032640": "LG유플러스",
    "030200": "KT",
    "000720": "현대건설",
    "247540": "에코프로비엠",
    "086520": "에코프로",
    "003670": "포스코퓨처엠",
    "161390": "한국타이어앤테크놀로지",
    "011200": "HMM",
    "010140": "삼성중공업",
    "047810": "한국항공우주",
    "352820": "하이브",
    "036570": "엔씨소프트",
    "251270": "넷마블",
    "041510": "에스엠",
    "122870": "와이지엔터테인먼트",
    "010950": "S-Oil",
    "078930": "GS",
    "000080": "하이트진로",
    "004020": "현대제철",
}

def get_stock_fundamental_data(ticker: str, market: str = "KOSPI") -> dict:
    """종목의 기본 정보 및 재무지표를 가져옵니다."""
    try:
        # 2026년 데이터가 없으므로 2025년 말 데이터 사용
        today = datetime(2025, 12, 31)  # 최근 영업일
        yesterday = today - timedelta(days=1)

        # 최근 30일 데이터
        start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")

        # 종목명 가져오기
        name = TICKER_NAMES.get(ticker, ticker)

        # OHLCV 데이터
        df_ohlcv = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
        if df_ohlcv.empty or len(df_ohlcv) == 0:
            print(f"  ⚠️  {ticker} {name}: OHLCV 데이터 없음")
            return None

        current_price = float(df_ohlcv.iloc[-1]['종가'])

        # 시가총액 (최근 날짜)
        df_cap = stock.get_market_cap_by_date(start_date, end_date, ticker)
        market_cap = None
        if not df_cap.empty:
            market_cap = float(df_cap.iloc[-1]['시가총액']) / 100000000  # 억원 단위

        # PER, PBR, 배당수익률 (하드코딩 - pykrx API 한계로 인한 임시 조치)
        # 2025년 12월 기준 대략적인 값
        fundamental_data = {
            "005930": {"per": 10.5, "pbr": 1.2, "div": 2.5},  # 삼성전자
            "000660": {"per": 8.0, "pbr": 1.8, "div": 1.5},   # SK하이닉스
            "373220": {"per": 25.0, "pbr": 2.5, "div": 0.5},  # LG에너지솔루션
            "207940": {"per": 35.0, "pbr": 7.0, "div": 0.3},  # 삼성바이오로직스
            "005380": {"per": 5.0, "pbr": 0.5, "div": 3.0},   # 현대차
            "000270": {"per": 4.5, "pbr": 0.6, "div": 3.5},   # 기아
            "051910": {"per": 12.0, "pbr": 0.9, "div": 2.0},  # LG화학
            "006400": {"per": 20.0, "pbr": 2.0, "div": 1.0},  # 삼성SDI
            "035420": {"per": 15.0, "pbr": 1.5, "div": 0.3},  # NAVER
            "035720": {"per": 20.0, "pbr": 1.8, "div": 0.2},  # 카카오
            "068270": {"per": 18.0, "pbr": 3.0, "div": 0.5},  # 셀트리온
            "105560": {"per": 6.0, "pbr": 0.5, "div": 4.5},   # KB금융
            "055550": {"per": 6.5, "pbr": 0.5, "div": 5.0},   # 신한지주
            "012330": {"per": 6.0, "pbr": 0.7, "div": 2.5},   # 현대모비스
            "066570": {"per": 12.0, "pbr": 1.0, "div": 1.5},  # LG전자
            "017670": {"per": 8.0, "pbr": 0.8, "div": 4.0},   # SK텔레콤
            "030200": {"per": 9.0, "pbr": 0.7, "div": 5.0},   # KT
            "033780": {"per": 7.0, "pbr": 0.9, "div": 5.5},   # KT&G
            "086790": {"per": 7.0, "pbr": 0.6, "div": 4.0},   # 하나금융지주
            "316140": {"per": 5.5, "pbr": 0.4, "div": 5.0},   # 우리금융지주
        }

        if ticker in fundamental_data:
            data = fundamental_data[ticker]
            pe_ratio = data["per"]
            pb_ratio = data["pbr"]
            dividend_yield = data["div"]
        else:
            # 기본값 (업종 평균 추정)
            pe_ratio = 12.0
            pb_ratio = 1.2
            dividend_yield = 1.5

        # 1년 전 가격 (수익률 계산)
        one_year_ago = (today - timedelta(days=365)).strftime("%Y%m%d")
        df_year = stock.get_market_ohlcv_by_date(one_year_ago, one_year_ago, ticker)
        one_year_return = None
        if not df_year.empty:
            old_price = float(df_year.iloc[0]['종가'])
            one_year_return = ((current_price - old_price) / old_price) * 100

        # YTD 수익률
        ytd_start = datetime(today.year, 1, 1).strftime("%Y%m%d")
        df_ytd = stock.get_market_ohlcv_by_date(ytd_start, ytd_start, ticker)
        ytd_return = None
        if not df_ytd.empty:
            ytd_price = float(df_ytd.iloc[0]['종가'])
            ytd_return = ((current_price - ytd_price) / ytd_price) * 100

        # 업종 정보
        sector_raw = None
        try:
            # KRX에서 업종 정보 가져오기
            tickers = stock.get_market_ticker_list(market=market)
            if ticker in tickers:
                # 간접적으로 업종 추정 (ETF나 다른 방법 필요)
                sector_raw = "기타"  # 기본값
        except Exception as e:
            print(f"  ⚠️ {ticker} 업종 정보 조회 실패: {e}")
            sector_raw = "기타"

        return {
            "ticker": ticker,
            "name": name,
            "market": market,
            "current_price": current_price,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "dividend_yield": dividend_yield,
            "ytd_return": ytd_return,
            "one_year_return": one_year_return,
            "sector": sector_raw,
        }

    except Exception as e:
        print(f"  ❌ {ticker} 데이터 수집 실패: {e}")
        return None

def map_sector(company_name: str, raw_sector: str) -> str:
    """회사명과 원시 섹터를 기반으로 표준 섹터로 매핑합니다."""

    # 회사명 기반 매핑 (우선순위 높음)
    if "반도체" in company_name or "하이닉스" in company_name:
        return "반도체"
    elif "바이오" in company_name or "셀트리온" in company_name or "제약" in company_name:
        return "헬스케어"
    elif "은행" in company_name or "금융" in company_name or "증권" in company_name or "KB" in company_name or "신한" in company_name or "하나" in company_name or "우리" in company_name:
        return "금융"
    elif "자동차" in company_name or "현대차" in company_name or "기아" in company_name or "모비스" in company_name:
        return "자동차"
    elif "전자" in company_name or "삼성전자" in company_name or "LG전자" in company_name:
        return "IT"
    elif "NAVER" in company_name or "네이버" in company_name:
        return "IT"  # NAVER 명시적 매핑
    elif "카카오" in company_name:
        return "IT"  # 카카오 명시적 매핑
    elif "엔씨" in company_name or "넷마블" in company_name:
        return "IT"
    elif "엔터" in company_name or "하이브" in company_name or "에스엠" in company_name or "YG" in company_name:
        return "소비재"
    elif "화학" in company_name or "LG화학" in company_name or "롯데케미칼" in company_name:
        return "화학"
    elif "배터리" in company_name or "에너지솔루션" in company_name or "SDI" in company_name or "에코프로" in company_name:
        return "2차전지"
    elif "통신" in company_name or "텔레콤" in company_name or "KT" in company_name or "유플러스" in company_name:
        return "IT"
    elif "건설" in company_name:
        return "산업재"
    elif "전력" in company_name or "한국전력" in company_name:
        return "에너지"

    # 원시 섹터 매핑
    for key, value in SECTOR_MAPPING.items():
        if key in raw_sector:
            return value

    return "기타"

def classify_risk_level(pe_ratio, pb_ratio, dividend_yield, one_year_return) -> str:
    """리스크 레벨을 분류합니다."""
    risk_score = 0

    # 변동성이 높은 경우 (수익률 기반)
    if one_year_return and abs(one_year_return) > 50:
        risk_score += 2
    elif one_year_return and abs(one_year_return) > 30:
        risk_score += 1

    # 밸류에이션이 높은 경우
    if pe_ratio and pe_ratio > 30:
        risk_score += 2
    elif pe_ratio and pe_ratio > 20:
        risk_score += 1

    # 배당이 없는 경우
    if not dividend_yield or dividend_yield < 1:
        risk_score += 1

    if risk_score >= 4:
        return "high"
    elif risk_score >= 2:
        return "medium"
    else:
        return "low"

def update_stock_database():
    """[DEPRECATED] load_stocks_from_fdr()로 대체됨.
    POST /admin/load-stocks 엔드포인트를 사용하세요."""
    raise NotImplementedError(
        "update_stock_database()는 더 사용되지 않습니다. "
        "POST /admin/load-stocks 엔드포인트를 사용하세요."
    )

if __name__ == "__main__":
    update_stock_database()
