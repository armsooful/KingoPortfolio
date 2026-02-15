"""
Claude AI 서비스 모듈
투자성향 진단 결과에 대한 AI 분석 및 맞춤 설명 생성
"""

import logging
from typing import List, Dict
import anthropic
from app.config import settings
from app.schemas import DiagnosisAnswerRequest

logger = logging.getLogger(__name__)


class ClaudeService:
    """Claude AI를 사용한 투자성향 분석 서비스"""

    def __init__(self):
        """Claude API 클라이언트 초기화"""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")

        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key
        )

    def analyze_investment_profile(
        self,
        answers: List[DiagnosisAnswerRequest],
        investment_type: str,
        score: float,
        confidence: float,
        monthly_investment: int = None
    ) -> Dict[str, str]:
        """
        투자성향 진단 결과를 Claude AI가 분석하여 개인화된 설명 생성

        Args:
            answers: 사용자의 설문 답변 목록
            investment_type: 진단된 투자 성향 (conservative, moderate, aggressive)
            score: 진단 점수 (0-10)
            confidence: 신뢰도 (0-1)
            monthly_investment: 월 투자 가능액

        Returns:
            Dict containing:
                - personalized_analysis: 개인화된 투자성향 분석
                - investment_advice: 투자 조언
                - risk_warning: 위험 주의사항
        """

        # 프롬프트 구성
        prompt = self._build_analysis_prompt(
            answers, investment_type, score, confidence, monthly_investment
        )

        try:
            # Claude API 호출
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 응답 파싱
            response_text = message.content[0].text
            parsed_response = self._parse_response(response_text)

            return parsed_response

        except Exception as e:
            logger.error("Claude API 호출 실패: %s", e)
            # 에러 시 기본 응답 반환
            return self._get_fallback_response(investment_type)

    def _build_analysis_prompt(
        self,
        answers: List[DiagnosisAnswerRequest],
        investment_type: str,
        score: float,
        confidence: float,
        monthly_investment: int = None
    ) -> str:
        """Claude AI에게 보낼 프롬프트 구성"""

        # 투자 성향 한글명
        type_names = {
            "conservative": "보수형",
            "moderate": "중도형",
            "aggressive": "적극형"
        }

        # 답변 요약
        answer_summary = "\n".join([
            f"- 문항 {ans.question_id}: {ans.answer_value}점"
            for ans in answers
        ])

        prompt = f"""당신은 전문 금융 자산관리사(FP)입니다. 사용자의 투자성향 진단 결과를 분석하여 개인화된 조언을 제공해주세요.

## 진단 결과
- 투자 성향: {type_names.get(investment_type, investment_type)}
- 종합 점수: {score}/10
- 신뢰도: {confidence*100:.0f}%
{"- 월 투자 가능액: " + str(monthly_investment) + "만원" if monthly_investment else ""}

## 설문 응답 내역
{answer_summary}

## 요청사항
다음 3가지 항목으로 구성된 분석을 제공해주세요:

1. **개인화된 투자성향 분석** (300자 이내)
   - 사용자의 답변 패턴을 바탕으로 구체적인 투자 성향 설명
   - 강점과 주의할 점을 균형있게 서술
   - 친근하고 이해하기 쉬운 톤으로 작성

2. **투자 조언** (400자 이내)
   - 해당 투자성향에 적합한 구체적인 투자 전략
   - 학습용 예시 자산 배분 및 투자 상품군
   - 단계별 실행 가이드

3. **위험 주의사항** (200자 이내)
   - 투자 시 반드시 주의해야 할 리스크
   - 피해야 할 투자 행동
   - 위험 관리 방법

응답 형식:
[분석]
(개인화된 투자성향 분석 내용)

[조언]
(투자 조언 내용)

[주의사항]
(위험 주의사항 내용)

친절하고 전문적이되 지나치게 격식적이지 않은 톤으로 작성해주세요."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, str]:
        """Claude의 응답을 파싱하여 구조화된 데이터로 변환"""

        result = {
            "personalized_analysis": "",
            "investment_advice": "",
            "risk_warning": ""
        }

        try:
            # [분석], [조언], [주의사항] 섹션으로 분리
            parts = response_text.split("[")

            for part in parts:
                if part.startswith("분석]"):
                    result["personalized_analysis"] = part.replace("분석]", "").strip()
                elif part.startswith("조언]"):
                    result["investment_advice"] = part.replace("조언]", "").strip()
                elif part.startswith("주의사항]"):
                    result["risk_warning"] = part.replace("주의사항]", "").strip()

            # 섹션이 제대로 파싱되지 않은 경우 전체 텍스트를 분석에 할당
            if not result["personalized_analysis"]:
                result["personalized_analysis"] = response_text.strip()

        except Exception as e:
            logger.warning("응답 파싱 실패: %s", e)
            result["personalized_analysis"] = response_text.strip()

        return result

    def _get_fallback_response(self, investment_type: str) -> Dict[str, str]:
        """Claude API 호출 실패 시 기본 응답 반환"""

        fallback_responses = {
            "conservative": {
                "personalized_analysis": "변동성이 낮은 자산 증식을 선호하시는 보수형 학습 성향입니다. 원금 보존을 최우선으로 하며, 일정한 현금 흐름 학습에 관심있는 성향입니다.",
                "investment_advice": "채권형 펀드, 예적금, CMA 등 변동성이 낮은 상품 위주의 포트폴리오 학습을 고려해볼 수 있습니다. 일반적으로 주식은 20% 이하로 구성되는 사례가 많습니다.",
                "risk_warning": "변동성을 낮추더라도 인플레이션을 고려해야 합니다. 지나치게 보수적인 투자는 실질 자산 가치 하락을 초래할 수 있습니다."
            },
            "moderate": {
                "personalized_analysis": "안정성과 수익성의 균형을 추구하시는 중도형 투자자십니다. 적절한 위험을 감수하면서도 자산 보호를 중요하게 생각하는 균형잡힌 투자 성향입니다.",
                "investment_advice": "주식 40%, 채권 30%, 현금성 자산 20%, 대체투자 10%의 균형잡힌 포트폴리오 구성을 학습해보세요. 정기적인 리밸런싱으로 위험을 관리하세요.",
                "risk_warning": "시장 변동성에 흔들리지 않는 투자 원칙이 필요합니다. 단기 수익에 집착하지 말고 중장기 관점을 유지하세요."
            },
            "aggressive": {
                "personalized_analysis": "높은 수익을 추구하시는 적극형 학습 성향입니다. 시장 변동성을 감내할 수 있으며, 성장 가능성이 높은 투자 기회에 관심이 있는 성향입니다.",
                "investment_advice": "성장주, 기술주, 신흥시장 등 공격적인 포트폴리오 구성을 학습할 수 있습니다. 일반적으로 주식 비중 60-70%가 학습 사례로 사용됩니다.",
                "risk_warning": "높은 수익 추구는 높은 손실 위험을 동반합니다. 레버리지 상품은 신중하게 접근하고, 전체 자산의 일정 부분은 변동성이 낮은 자산으로 보유하는 것이 일반적입니다."
            }
        }

        return fallback_responses.get(investment_type, fallback_responses["moderate"])


# 싱글톤 인스턴스
_claude_service = None

def get_claude_service() -> ClaudeService:
    """Claude 서비스 싱글톤 인스턴스 반환"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
