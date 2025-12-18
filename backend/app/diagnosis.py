from typing import List, Dict
from app.schemas import DiagnosisAnswerRequest, DiagnosisCharacteristics


# 진단 결과 설명 및 추천 포트폴리오
DIAGNOSIS_PROFILES = {
    "conservative": {
        "title": "보수형 투자자",
        "description": "안정적인 자산 증식을 원하시는 보수형 투자자입니다. 손실을 최소화하고 꾸준한 수익을 추구합니다.",
        "characteristics": [
            "자산 손실에 민감합니다",
            "안정적인 수익을 선호합니다",
            "낮은 변동성을 추구합니다",
            "주로 채권, 적금, CMA 등에 관심이 있습니다",
            "장기 안정적 자산 증식이 목표입니다"
        ],
        "recommended_ratio": {
            "stocks": 20,
            "bonds": 35,
            "money_market": 30,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "4-5%"
    },
    "moderate": {
        "title": "중도형 투자자",
        "description": "안정성과 수익성을 모두 추구하는 균형잡힌 투자자입니다. 적절한 위험을 감수하여 수익을 창출하려고 합니다.",
        "characteristics": [
            "적정 수준의 위험을 감수할 수 있습니다",
            "안정성과 수익성의 균형을 원합니다",
            "중간 정도의 변동성을 견딜 수 있습니다",
            "주식과 채권을 적절히 혼합하고 싶어합니다",
            "3-5년의 중기 투자 계획을 선호합니다"
        ],
        "recommended_ratio": {
            "stocks": 40,
            "bonds": 25,
            "money_market": 20,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "6-8%"
    },
    "aggressive": {
        "title": "적극형 투자자",
        "description": "높은 수익을 추구하는 적극적인 투자자입니다. 충분한 위험을 감수하고 성장성을 중시합니다.",
        "characteristics": [
            "높은 수익을 추구합니다",
            "일정한 손실을 감수할 수 있습니다",
            "높은 변동성을 견딜 수 있습니다",
            "주로 성장주와 신흥시장에 관심이 있습니다",
            "장기 자산 증식을 통한 자산 형성이 목표입니다"
        ],
        "recommended_ratio": {
            "stocks": 60,
            "bonds": 15,
            "money_market": 10,
            "gold": 10,
            "other": 5
        },
        "expected_annual_return": "9-12%"
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