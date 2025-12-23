"""
정성적 분석 모듈 (AI 기반)
- 뉴스 감성 분석
- 재무제표 질적 평가
"""

import os
from typing import Dict, List, Optional
from anthropic import Anthropic
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class QualitativeAnalyzer:
    """AI 기반 정성적 분석"""

    @staticmethod
    def fetch_news_from_alpha_vantage(symbol: str, limit: int = 10) -> List[Dict]:
        """
        Alpha Vantage News Sentiment API로 뉴스 가져오기
        """
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            return []

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": api_key,
            "limit": limit
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "feed" not in data:
                return []

            news_items = []
            for item in data["feed"][:limit]:
                news_items.append({
                    "title": item.get("title", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "time_published": item.get("time_published", ""),
                    "source": item.get("source", ""),
                    # Alpha Vantage의 감성 점수도 포함
                    "overall_sentiment_score": item.get("overall_sentiment_score", 0),
                    "overall_sentiment_label": item.get("overall_sentiment_label", "Neutral")
                })

            return news_items

        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    @staticmethod
    def analyze_news_sentiment(symbol: str, news_articles: List[Dict]) -> Dict:
        """
        뉴스 기사들의 감성을 Claude AI로 분석
        """
        if not news_articles:
            return {
                "symbol": symbol,
                "error": "뉴스 데이터가 없습니다",
                "sentiment": "중립",
                "news_count": 0
            }

        # Anthropic API 키 확인
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # API 키가 없으면 Alpha Vantage 감성만 사용
            return QualitativeAnalyzer._analyze_with_av_sentiment(symbol, news_articles)

        try:
            client = Anthropic(api_key=api_key)

            # 뉴스 텍스트 준비 (최근 10개)
            news_text = "\n\n".join([
                f"[{i+1}] {article['title']}\n요약: {article['summary'][:200]}..."
                for i, article in enumerate(news_articles[:10])
            ])

            prompt = f"""다음은 {symbol} 종목에 대한 최근 뉴스입니다.

{news_text}

다음 형식으로 JSON 형태로 분석해주세요:

{{
  "overall_sentiment": "긍정/중립/부정 중 하나",
  "sentiment_score": -1.0에서 1.0 사이의 숫자 (-1: 매우 부정, 0: 중립, 1: 매우 긍정),
  "positive_factors": ["긍정 요인1", "긍정 요인2", "긍정 요인3"],
  "negative_factors": ["부정 요인1", "부정 요인2"],
  "key_issues": ["투자자가 주목해야 할 핵심 이슈1", "이슈2"],
  "summary": "1-2문장 요약"
}}

**중요 규칙**:
1. 투자 권고(매수/매도)는 절대 하지 마세요
2. 객관적 사실만 분석하세요
3. JSON 형식만 출력하세요 (다른 텍스트 없이)"""

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # JSON 파싱
            import json
            analysis_text = response.content[0].text.strip()

            # JSON 추출 (```json ... ``` 형태로 올 수 있음)
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0].strip()

            analysis = json.loads(analysis_text)

            return {
                "symbol": symbol,
                "sentiment": analysis.get("overall_sentiment", "중립"),
                "sentiment_score": analysis.get("sentiment_score", 0),
                "positive_factors": analysis.get("positive_factors", []),
                "negative_factors": analysis.get("negative_factors", []),
                "key_issues": analysis.get("key_issues", []),
                "summary": analysis.get("summary", ""),
                "news_count": len(news_articles),
                "analyzed_at": datetime.utcnow().isoformat(),
                "disclaimer": "본 분석은 AI 기반 정성적 평가이며, 투자 권고가 아닙니다."
            }

        except Exception as e:
            print(f"Error in AI analysis: {e}")
            # AI 분석 실패시 Alpha Vantage 감성으로 대체
            return QualitativeAnalyzer._analyze_with_av_sentiment(symbol, news_articles)

    @staticmethod
    def _analyze_with_av_sentiment(symbol: str, news_articles: List[Dict]) -> Dict:
        """
        Alpha Vantage의 감성 점수를 사용한 간단 분석
        """
        if not news_articles:
            return {
                "symbol": symbol,
                "sentiment": "중립",
                "sentiment_score": 0,
                "news_count": 0
            }

        # 평균 감성 점수 계산
        sentiment_scores = [
            article.get("overall_sentiment_score", 0)
            for article in news_articles
        ]
        avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        # 감성 레이블 결정
        if avg_score > 0.15:
            sentiment = "긍정"
        elif avg_score < -0.15:
            sentiment = "부정"
        else:
            sentiment = "중립"

        # 긍정/부정 뉴스 추출
        positive_news = [
            article["title"] for article in news_articles
            if article.get("overall_sentiment_score", 0) > 0.15
        ][:3]

        negative_news = [
            article["title"] for article in news_articles
            if article.get("overall_sentiment_score", 0) < -0.15
        ][:3]

        return {
            "symbol": symbol,
            "sentiment": sentiment,
            "sentiment_score": round(avg_score, 3),
            "positive_factors": positive_news,
            "negative_factors": negative_news,
            "key_issues": ["최근 뉴스 기반 감성 분석"],
            "summary": f"최근 {len(news_articles)}개 뉴스의 평균 감성: {sentiment}",
            "news_count": len(news_articles),
            "analyzed_at": datetime.utcnow().isoformat(),
            "method": "Alpha Vantage Sentiment (Claude AI 미사용)",
            "disclaimer": "본 분석은 뉴스 감성 평가이며, 투자 권고가 아닙니다."
        }

    @staticmethod
    def get_comprehensive_news_analysis(symbol: str) -> Dict:
        """
        종합 뉴스 감성 분석 (데이터 수집 + AI 분석)
        """
        # 1. 뉴스 가져오기
        news_articles = QualitativeAnalyzer.fetch_news_from_alpha_vantage(symbol, limit=10)

        if not news_articles:
            return {
                "symbol": symbol,
                "error": "뉴스를 가져올 수 없습니다",
                "sentiment": "중립",
                "news_count": 0
            }

        # 2. AI 분석
        analysis = QualitativeAnalyzer.analyze_news_sentiment(symbol, news_articles)

        # 3. 최근 뉴스 목록 추가
        analysis["recent_news"] = [
            {
                "title": article["title"],
                "source": article["source"],
                "time_published": article["time_published"],
                "url": article["url"]
            }
            for article in news_articles[:5]  # 최근 5개만
        ]

        return analysis
