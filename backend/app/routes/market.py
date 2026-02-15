"""
시장 데이터 API 라우터
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yfinance as yf
from anthropic import Anthropic
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pykrx import stock

from app.database import get_db

logger = logging.getLogger(__name__)
from app.models.user import User
from app.routes.auth import get_current_user
from app.utils.http_client import get_with_retry

router = APIRouter(prefix="/api/market", tags=["market"])


def fetch_naver_finance_news(limit: int = 5) -> List[Dict[str, str]]:
    """
    네이버 금융에서 한국 경제 관련 최신 뉴스 크롤링
    """
    try:
        # 네이버 금융 뉴스 URL - 국내증시 섹션 (해외 뉴스 제외)
        # section_id=101: 증권, section_id2=258: 시황
        url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = get_with_retry(url, headers=headers, timeout=2.0, retries=2)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        news_list = []

        # 뉴스 목록 파싱 - dd.articleSubject 내의 a 태그
        # 필터링을 고려해서 limit의 3배 정도 수집
        news_items = soup.select('dd.articleSubject a')

        for item in news_items[:limit * 3]:
            try:
                title = item.get('title', '').strip()
                link = item.get('href', '')

                if title and link:
                    # § 문자를 &section으로 수정 (네이버 HTML 엔티티 오류 수정)
                    link = link.replace('§ion_id', '&section_id')

                    # 상대 URL을 절대 URL로 변환
                    full_url = urljoin('https://finance.naver.com', link)

                    # 언론사와 시간 정보 가져오기
                    # dd 태그의 부모 li를 찾아서 wdate 정보 추출
                    parent_dd = item.find_parent('dd')
                    source = '네이버 뉴스'  # 모든 뉴스를 네이버 뉴스로 표기
                    published_at = '방금 전'

                    if parent_dd:
                        parent_li = parent_dd.find_parent('li')
                        if parent_li:
                            # 날짜 정보 찾기
                            date_span = parent_li.find('span', class_='wdate')
                            if date_span:
                                published_at = date_span.text.strip()

                    # 한국 경제 관련 뉴스만 필터링 (해외 뉴스 제외)
                    exclude_keywords = ['미국', '중국', '일본', '유럽', '달러', '엔화', '위안화',
                                       '나스닥', '다우', 'S&P', '홍콩', '상하이', '닛케이',
                                       '월가', '백악관', '연준', 'Fed', 'ECB', '바이든', '트럼프']

                    # 제목에 해외 키워드가 있으면 제외
                    if any(keyword in title for keyword in exclude_keywords):
                        continue

                    news_list.append({
                        'title': title,
                        'source': source,
                        'publishedAt': published_at,
                        'url': full_url
                    })

                    # 필요한 개수만큼 수집되면 중단
                    if len(news_list) >= limit:
                        break

            except Exception as e:
                logger.warning("뉴스 파싱 오류: %s", e)
                continue

        # 뉴스가 없으면 기본 Mock 데이터 반환
        if not news_list:
            return get_mock_news()

        return news_list[:limit]

    except Exception as e:
        logger.error("네이버 금융 뉴스 크롤링 실패: %s", e)
        return get_mock_news()


def get_mock_news() -> List[Dict[str, str]]:
    """
    Mock 뉴스 데이터 (크롤링 실패 시 대체용)
    """
    return [
        {
            "title": "미 연준 금리 동결 전망... 국내 증시 영향은?",
            "source": "한국경제",
            "publishedAt": "2시간 전",
            "url": "#"
        },
        {
            "title": "삼성전자, AI 반도체 신제품 공개",
            "source": "전자신문",
            "publishedAt": "4시간 전",
            "url": "#"
        },
        {
            "title": "KOSPI 2650 돌파... 외국인 매수세 지속",
            "source": "연합뉴스",
            "publishedAt": "5시간 전",
            "url": "#"
        }
    ]


def get_top_stocks_by_change(limit: int = 5) -> tuple:
    """
    pykrx를 사용하여 실시간 상승/하락 종목 조회

    Returns:
        tuple: (top_gainers, top_losers)
    """
    try:
        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")

        # 주말이면 가장 최근 거래일 찾기
        max_attempts = 7
        for i in range(max_attempts):
            try:
                date_to_check = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                # KOSPI 전체 종목 OHLCV 조회 시도
                test_df = stock.get_market_ohlcv_by_date(
                    date_to_check,
                    date_to_check,
                    "005930"  # 삼성전자 테스트
                )
                if not test_df.empty:
                    today = date_to_check
                    break
            except Exception as e:
                logger.debug(f"거래일 탐색 중 (날짜: {date_to_check}): {e}")
                continue

        # 전일 대비 등락률 계산을 위해 전일 거래일 찾기
        yesterday = today
        for i in range(1, 8):
            try:
                yesterday = (datetime.strptime(today, "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d")
                test_df = stock.get_market_ohlcv_by_date(
                    yesterday,
                    yesterday,
                    "005930"
                )
                if not test_df.empty:
                    break
            except Exception as e:
                logger.debug(f"전일 거래일 탐색 중 (날짜: {yesterday}): {e}")
                continue

        # 주요 종목 리스트 (거래량 많은 대표 종목)
        major_tickers = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "051910",  # LG화학
            "006400",  # 삼성SDI
            "035720",  # 카카오
            "028260",  # 삼성물산
            "105560",  # KB금융
            "055550",  # 신한지주
            "096770",  # SK이노베이션
            "003670",  # 포스코퓨처엠
            "000270",  # 기아
            "005380",  # 현대차
            "012330",  # 현대모비스
            "017670",  # SK텔레콤
            "068270",  # 셀트리온
            "207940",  # 삼성바이오로직스
            "032830",  # 삼성생명
            "005935",  # 삼성전자우
            "015760",  # 한국전력
        ]

        all_stocks = []

        for ticker in major_tickers:
            try:
                # 오늘/어제 데이터 조회
                df = stock.get_market_ohlcv_by_date(
                    yesterday,
                    today,
                    ticker
                )

                if len(df) >= 2:
                    today_price = df.iloc[-1]['종가']
                    yesterday_price = df.iloc[-2]['종가']
                    change_percent = ((today_price - yesterday_price) / yesterday_price) * 100

                    ticker_name = stock.get_market_ticker_name(ticker)

                    all_stocks.append({
                        "symbol": ticker,
                        "name": ticker_name,
                        "price": int(today_price),
                        "change": round(change_percent, 2)
                    })
            except Exception as e:
                logger.warning("%s 조회 실패: %s", ticker, e)
                continue

        if not all_stocks:
            return get_mock_stocks()

        # 상승/하락 정렬
        all_stocks_sorted = sorted(all_stocks, key=lambda x: x['change'], reverse=True)

        top_gainers = all_stocks_sorted[:limit]
        top_losers = all_stocks_sorted[-limit:][::-1]  # 하락률 높은 순으로

        return top_gainers, top_losers

    except Exception as e:
        logger.error("실시간 종목 데이터 조회 실패: %s", e)
        # Mock 데이터 반환
        return get_mock_stocks()


def get_mock_stocks() -> tuple:
    """
    Mock 종목 데이터 (API 실패 시 대체용)
    """
    top_gainers = [
        {"symbol": "005930", "name": "삼성전자", "price": 78500, "change": 3.5},
        {"symbol": "000660", "name": "SK하이닉스", "price": 145000, "change": 4.2},
        {"symbol": "035420", "name": "NAVER", "price": 245000, "change": 2.8}
    ]

    top_losers = [
        {"symbol": "051910", "name": "LG화학", "price": 425000, "change": -2.3},
        {"symbol": "006400", "name": "삼성SDI", "price": 485000, "change": -1.8},
        {"symbol": "028260", "name": "삼성물산", "price": 128000, "change": -1.5}
    ]

    return top_gainers, top_losers


def calculate_market_sentiment(indices: List[Dict]) -> Dict[str, Any]:
    """
    시장 심리 분석 및 신호등 색상 결정
    """
    kospi = next((idx for idx in indices if idx['name'] == 'KOSPI'), None)
    kosdaq = next((idx for idx in indices if idx['name'] == 'KOSDAQ'), None)

    if not kospi:
        return {"color": "yellow", "status": "중립", "emoji": "🟡"}

    # 평균 변화율 계산
    changes = [idx['changePercent'] for idx in indices if 'changePercent' in idx]
    avg_change = sum(changes) / len(changes) if changes else 0

    # 신호등 색상 결정
    if avg_change > 0.5:  # 0.5% 이상 상승
        return {"color": "green", "status": "긍정적", "emoji": "🟢"}
    elif avg_change < -0.5:  # 0.5% 이상 하락
        return {"color": "red", "status": "위험", "emoji": "🔴"}
    else:  # -0.5% ~ 0.5%
        return {"color": "yellow", "status": "중립", "emoji": "🟡"}


def generate_market_summary(indices: List[Dict], top_gainers: List[Dict], top_losers: List[Dict]) -> Dict[str, Any]:
    """
    AI를 사용하여 시장 상황을 초보자가 이해할 수 있는 문장으로 요약
    """
    try:
        # Anthropic API 키 확인
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return generate_simple_summary(indices, top_gainers, top_losers)

        client = Anthropic(api_key=api_key)

        # 데이터 요약 생성
        indices_summary = "\n".join([
            f"- {idx['name']}: {idx['value']} ({'+' if idx['change'] >= 0 else ''}{idx['changePercent']}%)"
            for idx in indices
        ])

        gainers_summary = ", ".join([stock['name'] for stock in top_gainers[:3]])
        losers_summary = ", ".join([stock['name'] for stock in top_losers[:3]])

        prompt = f"""다음은 오늘의 주식 시장 데이터입니다:

주요 지수:
{indices_summary}

오늘 많이 오른 종목: {gainers_summary}
오늘 많이 내린 종목: {losers_summary}

위 데이터를 바탕으로 주식 투자를 처음 시작하는 초보자가 이해할 수 있도록 오늘의 시장 상황을 2-3문장으로 쉽게 요약해주세요. 전문용어는 피하고, 일상적인 언어로 설명해주세요.

예시 스타일:
"오늘 한국 증시는 좋은 흐름을 보였어요. 삼성전자와 같은 대형주들이 힘을 받으면서 코스피가 올랐습니다. 미국 증시도 함께 상승하면서 전반적으로 긍정적인 분위기예요."
"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        summary_text = message.content[0].text.strip()
        sentiment = calculate_market_sentiment(indices)

        return {
            "text": summary_text,
            "sentiment": sentiment
        }

    except Exception as e:
        logger.error("AI 요약 생성 실패: %s", e)
        return generate_simple_summary(indices, top_gainers, top_losers)


def generate_simple_summary(indices: List[Dict], top_gainers: List[Dict], top_losers: List[Dict]) -> Dict[str, Any]:
    """
    AI 없이 간단한 템플릿 기반 요약 생성
    """
    kospi = next((idx for idx in indices if idx['name'] == 'KOSPI'), None)
    kosdaq = next((idx for idx in indices if idx['name'] == 'KOSDAQ'), None)

    if not kospi:
        return {
            "text": "오늘의 시장 데이터를 불러오는 중입니다.",
            "sentiment": {"color": "yellow", "status": "중립", "emoji": "🟡"}
        }

    kospi_direction = "상승" if kospi['changePercent'] > 0 else "하락" if kospi['changePercent'] < 0 else "보합"
    kosdaq_direction = "올랐고" if kosdaq and kosdaq['changePercent'] > 0 else "내렸고" if kosdaq and kosdaq['changePercent'] < 0 else "보합을 보였고"

    mood = "긍정적인" if kospi['changePercent'] > 0 else "조심스러운" if kospi['changePercent'] < 0 else "관망하는"

    summary = f"오늘 한국 증시는 {kospi_direction} 마감했습니다. "
    summary += f"코스피는 {abs(kospi['changePercent']):.2f}% {kospi_direction}했고, 코스닥은 {kosdaq_direction if kosdaq else '변동이 있었습니다'}. "

    if top_gainers:
        summary += f"{top_gainers[0]['name']} 같은 종목들이 상승세를 보였습니다. "

    summary += f"전반적으로 {mood} 분위기입니다."

    sentiment = calculate_market_sentiment(indices)

    return {
        "text": summary,
        "sentiment": sentiment
    }


@router.get("/overview")
async def get_market_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    시장 현황 개요 조회
    - 주요 지수 (KOSPI, KOSDAQ, S&P 500, NASDAQ)
    - 상승/하락 종목
    - 시장 뉴스 (Mock)
    """
    try:
        # 주요 지수 데이터
        indices = []

        # KOSPI
        try:
            kospi = yf.Ticker("^KS11")
            kospi_info = kospi.history(period="2d")
            if not kospi_info.empty and len(kospi_info) >= 2:
                current_price = kospi_info['Close'].iloc[-1]
                prev_close = kospi_info['Close'].iloc[-2]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "KOSPI",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
            elif not kospi_info.empty:
                # 1일치 데이터만 있는 경우 (장 시작 전 등)
                current_price = kospi_info['Close'].iloc[-1]
                indices.append({
                    "name": "KOSPI",
                    "value": round(current_price, 2),
                    "change": 0.0,
                    "changePercent": 0.0,
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning("KOSPI 데이터 조회 실패: %s", e)
            indices.append({
                "name": "KOSPI",
                "value": 2645.85,
                "change": 15.32,
                "changePercent": 0.58,
                "updatedAt": datetime.now().isoformat()
            })

        # KOSDAQ
        try:
            kosdaq = yf.Ticker("^KQ11")
            kosdaq_info = kosdaq.history(period="2d")
            if not kosdaq_info.empty and len(kosdaq_info) >= 2:
                current_price = kosdaq_info['Close'].iloc[-1]
                prev_close = kosdaq_info['Close'].iloc[-2]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "KOSDAQ",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
            elif not kosdaq_info.empty:
                current_price = kosdaq_info['Close'].iloc[-1]
                indices.append({
                    "name": "KOSDAQ",
                    "value": round(current_price, 2),
                    "change": 0.0,
                    "changePercent": 0.0,
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning("KOSDAQ 데이터 조회 실패: %s", e)
            indices.append({
                "name": "KOSDAQ",
                "value": 845.23,
                "change": -3.45,
                "changePercent": -0.41,
                "updatedAt": datetime.now().isoformat()
            })

        # S&P 500
        try:
            sp500 = yf.Ticker("^GSPC")
            sp500_info = sp500.history(period="2d")
            if not sp500_info.empty and len(sp500_info) >= 2:
                current_price = sp500_info['Close'].iloc[-1]
                prev_close = sp500_info['Close'].iloc[-2]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "S&P 500",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
            elif not sp500_info.empty:
                current_price = sp500_info['Close'].iloc[-1]
                indices.append({
                    "name": "S&P 500",
                    "value": round(current_price, 2),
                    "change": 0.0,
                    "changePercent": 0.0,
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning("S&P 500 데이터 조회 실패: %s", e)
            indices.append({
                "name": "S&P 500",
                "value": 4783.45,
                "change": 12.87,
                "changePercent": 0.27,
                "updatedAt": datetime.now().isoformat()
            })

        # NASDAQ
        try:
            nasdaq = yf.Ticker("^IXIC")
            nasdaq_info = nasdaq.history(period="2d")
            if not nasdaq_info.empty and len(nasdaq_info) >= 2:
                current_price = nasdaq_info['Close'].iloc[-1]
                prev_close = nasdaq_info['Close'].iloc[-2]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "NASDAQ",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
            elif not nasdaq_info.empty:
                current_price = nasdaq_info['Close'].iloc[-1]
                indices.append({
                    "name": "NASDAQ",
                    "value": round(current_price, 2),
                    "change": 0.0,
                    "changePercent": 0.0,
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning("NASDAQ 데이터 조회 실패: %s", e)
            indices.append({
                "name": "NASDAQ",
                "value": 15043.97,
                "change": 45.23,
                "changePercent": 0.30,
                "updatedAt": datetime.now().isoformat()
            })

        # 실시간 상승/하락 종목 조회 (pykrx 사용)
        top_gainers, top_losers = get_top_stocks_by_change(limit=3)

        # 네이버 금융 뉴스 크롤링
        news = fetch_naver_finance_news(limit=5)

        # AI 요약 생성
        market_summary = generate_market_summary(indices, top_gainers, top_losers)

        return {
            "summary": market_summary,
            "indices": indices,
            "topGainers": top_gainers,
            "topLosers": top_losers,
            "news": news
        }

    except Exception as e:
        logger.error("Market overview error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"시장 데이터 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/indices/{symbol}")
async def get_index_detail(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    특정 지수의 상세 정보 조회
    """
    symbol_map = {
        "kospi": "^KS11",
        "kosdaq": "^KQ11",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC"
    }

    ticker_symbol = symbol_map.get(symbol.lower())
    if not ticker_symbol:
        raise HTTPException(status_code=404, detail="지수를 찾을 수 없습니다")

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1mo")

        if hist.empty:
            raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다")

        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[0]
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        return {
            "symbol": symbol.upper(),
            "name": symbol.upper(),
            "currentPrice": round(current_price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "high": round(hist['High'].iloc[-1], 2),
            "low": round(hist['Low'].iloc[-1], 2),
            "volume": int(hist['Volume'].iloc[-1]),
            "updatedAt": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Index detail error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"지수 정보 조회 중 오류가 발생했습니다: {str(e)}")
