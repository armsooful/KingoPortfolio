from typing import List, Dict
from app.schemas import DiagnosisAnswerRequest, DiagnosisCharacteristics


# ⚠️ 법적 검토 완료 (2026-01-11): 투자자문업 위반 요소 제거
# 진단 결과는 교육 목적 학습 성향 분석이며, 투자 권유·추천이 아닙니다.

# 학습 성향 프로필 및 시뮬레이션 예시
DIAGNOSIS_PROFILES = {
    "conservative": {
        "title": "안정성 중심 학습 성향",
        "description": "안정적인 자산 운용 전략을 학습하고자 하는 성향입니다. 변동성이 낮은 자산에 대한 이해를 우선적으로 쌓고자 합니다.",
        "characteristics": [
            "손실 위험에 민감한 편입니다",
            "안정적인 자산 운용 방식을 선호합니다",
            "낮은 변동성 자산에 관심이 있습니다",
            "채권, 예적금, 머니마켓 등을 학습 대상으로 고려합니다",
            "장기적 관점의 자산 보존 전략에 관심이 있습니다"
        ],
        "recommended_ratio": {
            "stocks": 20,
            "bonds": 35,
            "money_market": 30,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "4-5% (과거 평균 참고치)"
    },
    "moderate": {
        "title": "균형형 학습 성향",
        "description": "안정성과 성장성의 균형을 이해하고자 하는 학습 성향입니다. 다양한 자산군에 대한 폭넓은 학습을 원합니다.",
        "characteristics": [
            "적정 수준의 위험 요소를 학습 대상으로 고려합니다",
            "안정성과 성장성의 조화에 관심이 있습니다",
            "중간 수준의 변동성을 학습하고자 합니다",
            "주식과 채권의 혼합 전략을 이해하고 싶어합니다",
            "중기(3-5년) 관점의 전략 학습을 선호합니다"
        ],
        "recommended_ratio": {
            "stocks": 40,
            "bonds": 25,
            "money_market": 20,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "6-8% (과거 평균 참고치)"
    },
    "aggressive": {
        "title": "성장성 중심 학습 성향",
        "description": "성장성 높은 자산군의 특성을 학습하고자 하는 성향입니다. 높은 변동성 자산에 대한 이해를 쌓고자 합니다.",
        "characteristics": [
            "높은 수익률 자산의 특성을 이해하고 싶습니다",
            "일정 수준의 손실 시나리오를 학습 대상으로 고려합니다",
            "높은 변동성 자산군에 대해 학습하고자 합니다",
            "성장주와 신흥시장을 학습 대상으로 고려합니다",
            "장기적 관점의 자산 형성 전략에 관심이 있습니다"
        ],
        "recommended_ratio": {
            "stocks": 60,
            "bonds": 15,
            "money_market": 10,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "9-12% (과거 평균 참고치)"
    }
}


def calculate_diagnosis(answers: List[DiagnosisAnswerRequest]) -> tuple[str, float, float]:
    """
    설문 응답을 바탕으로 투자성향 계산
    
    Args:
        answers: 진단 답변 목록
    
    Returns:
        tuple: (투자성향, 점수, 신뢰도)
            - 투자성향: 'conservative', 'moderate', 'aggressive'
            - 점수: 0-10 (보수=1-3.3, 중도=3.4-6.6, 적극=6.7-10)
            - 신뢰도: 0-1 (일관성 점수)
    """
    
    if not answers or len(answers) == 0:
        raise ValueError("No answers provided")
    
    # 답변 값의 평균 계산
    total_value = sum(ans.answer_value for ans in answers)
    num_answers = len(answers)
    average_value = total_value / num_answers
    
    # 점수를 0-10 범위로 변환
    # 가정: 각 문항은 1-5 범위의 값을 가짐
    # 1-5 범위 → 0-10 범위로 정규화
    score = (average_value - 1) * 2.5  # (1-5) → (0-10)
    score = round(score, 2)
    
    # 투자성향 분류
    if score < 3.33:
        investment_type = "conservative"
    elif score < 6.67:
        investment_type = "moderate"
    else:
        investment_type = "aggressive"
    
    # 신뢰도 계산 (일관성)
    # 표준편차가 낮을수록 신뢰도 높음 (0.7-1.0 범위)
    confidence = calculate_confidence(answers)
    
    return investment_type, score, confidence


def calculate_confidence(answers: List[DiagnosisAnswerRequest]) -> float:
    """
    답변의 일관성을 바탕으로 신뢰도 계산
    
    일관성이 높으면 신뢰도 높음 (0.7-1.0)
    """
    if len(answers) < 2:
        return 0.75
    
    values = [ans.answer_value for ans in answers]
    avg = sum(values) / len(values)
    
    # 표준편차 계산
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    
    # 표준편차를 신뢰도로 변환
    # std_dev가 0에 가까우면 신뢰도 1.0
    # std_dev가 2 이상이면 신뢰도 0.7
    confidence = 1.0 - min(std_dev / 10, 0.3)
    confidence = round(confidence, 2)
    
    return confidence


def get_diagnosis_profile(investment_type: str) -> DiagnosisCharacteristics:
    """
    투자성향에 따른 상세 프로필 조회
    
    Args:
        investment_type: 'conservative', 'moderate', 'aggressive'
    
    Returns:
        DiagnosisCharacteristics: 투자성향 프로필
    """
    profile = DIAGNOSIS_PROFILES.get(investment_type)
    
    if not profile:
        raise ValueError(f"Invalid investment type: {investment_type}")
    
    return DiagnosisCharacteristics(
        title=profile["title"],
        description=profile["description"],
        characteristics=profile["characteristics"],
        recommended_ratio=profile["recommended_ratio"],
        expected_annual_return=profile["expected_annual_return"]
    )


def build_diagnosis_response(
    diagnosis_id: str,
    investment_type: str,
    score: float,
    confidence: float,
    monthly_investment: int = None,
    created_at = None
):
    """
    진단 결과 응답 빌더
    """
    profile = get_diagnosis_profile(investment_type)
    
    return {
        "diagnosis_id": diagnosis_id,
        "investment_type": investment_type,
        "score": score,
        "confidence": confidence,
        "monthly_investment": monthly_investment,
        "description": profile.description,
        "characteristics": profile.characteristics,
        "recommended_ratio": profile.recommended_ratio,
        "expected_annual_return": profile.expected_annual_return,
        "created_at": created_at
    }