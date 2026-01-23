from fastapi import APIRouter, Depends
from app.auth import get_current_user

router = APIRouter(prefix="/api/survey", tags=["Survey"])

# ⚠️ 법적 검토 완료 (2026-01-10): 투자자문업 위반 요소 제거
# 본 설문은 교육 및 정보 제공 목적의 자가 점검 도구입니다.
# "투자 목표", "금융상품", "투자 결정", "매수/매도" 등 규제 용어를
# "학습 방향", "시뮬레이션", "전략 탐색" 등 교육 목적 용어로 전면 교체

SURVEY_QUESTIONS = [
    # Q1 - 유지 (법적 문제 없음)
    {
        "id": 1,
        "category": "experience",
        "question": "자산 운용 또는 투자 관련 경험은 어느 정도인가요?",
        "options": [
            {"value": "A", "text": "처음입니다", "weight": 1.0},
            {"value": "B", "text": "약간의 경험이 있습니다", "weight": 2.0},
            {"value": "C", "text": "충분한 경험이 있습니다", "weight": 3.0}
        ]
    },
    # Q2 - 유지 (법적 문제 없음)
    {
        "id": 2,
        "category": "experience",
        "question": "과거 자산 운용 또는 투자 과정에서 손실을 경험한 적이 있나요?",
        "options": [
            {"value": "A", "text": "없습니다", "weight": 1.0},
            {"value": "B", "text": "작은 손실을 경험한 적이 있습니다", "weight": 2.0},
            {"value": "C", "text": "큰 손실을 경험한 적이 있습니다", "weight": 3.0}
        ]
    },
    # Q3 - 수정 (투자 계획 기간 → 학습 시 고려 기간)
    {
        "id": 3,
        "category": "duration",
        "question": "자산 운용을 학습할 때 주로 고려하는 기간은 어느 정도인가요?",
        "options": [
            {"value": "A", "text": "1년 이하", "weight": 1.0},
            {"value": "B", "text": "1~3년", "weight": 2.5},
            {"value": "C", "text": "3년 이상", "weight": 3.0}
        ]
    },
    # Q4 - 수정 (투자 목표 → 전략 학습 방향)
    {
        "id": 4,
        "category": "duration",
        "question": "선호하는 투자 전략 학습 방향은 무엇인가요?",
        "options": [
            {"value": "A", "text": "안정성 중심 전략", "weight": 1.0},
            {"value": "B", "text": "균형형 전략", "weight": 2.0},
            {"value": "C", "text": "성장성 중심 전략", "weight": 3.0}
        ]
    },
    # Q5 - 수정 (포트폴리오 하락 → 하락 시나리오 대응 학습)
    {
        "id": 5,
        "category": "risk",
        "question": "가상 시뮬레이션에서 자산이 10% 하락한 상황을 가정할 때, 학습해 보고 싶은 대응 전략은 무엇인가요?",
        "options": [
            {"value": "A", "text": "손실 제한(리스크 관리) 전략", "weight": 1.0},
            {"value": "B", "text": "관망 전략", "weight": 2.0},
            {"value": "C", "text": "역발상 대응 전략", "weight": 3.0}
        ]
    },
    # Q6 - 유지 (법적 문제 없음)
    {
        "id": 6,
        "category": "risk",
        "question": "자산 가격의 변동성을 어느 정도까지 감내할 수 있다고 느끼시나요?",
        "options": [
            {"value": "A", "text": "거의 감내하기 어렵습니다", "weight": 1.0},
            {"value": "B", "text": "어느 정도는 감내할 수 있습니다", "weight": 2.0},
            {"value": "C", "text": "높은 변동성도 감내할 수 있습니다", "weight": 3.0}
        ]
    },
    # Q7 - 수정 (위험 감수 의향 → 위험 감수 성향)
    {
        "id": 7,
        "category": "risk",
        "question": "자산 운용을 학습할 때 위험 요소를 어느 정도까지 고려할 수 있나요?",
        "options": [
            {"value": "A", "text": "변동성이 낮은 요소 위주로 학습하고 싶습니다", "weight": 1.0},
            {"value": "B", "text": "적정 수준의 위험 요소는 고려할 수 있습니다", "weight": 2.0},
            {"value": "C", "text": "높은 변동성도 학습 대상으로 고려할 수 있습니다", "weight": 3.0}
        ]
    },
    # Q8 - 수정 (투자금 최대 손실 → 손실 범위 인식)
    {
        "id": 8,
        "category": "risk",
        "question": "가상 시나리오에서 고려 가능한 손실 범위는 어느 정도인가요?",
        "options": [
            {"value": "A", "text": "손실은 거의 허용하지 않습니다", "weight": 1.0},
            {"value": "B", "text": "약 10% 이내", "weight": 2.0},
            {"value": "C", "text": "20% 이상도 학습 대상으로 고려할 수 있습니다", "weight": 3.0}
        ]
    },
    # Q9 - 수정 (금융상품 → 일반 투자 지식)
    {
        "id": 9,
        "category": "knowledge",
        "question": "투자와 관련된 일반적인 지식 수준은 어느 정도라고 생각하시나요?",
        "options": [
            {"value": "A", "text": "초보자 수준", "weight": 1.0},
            {"value": "B", "text": "중급자 수준", "weight": 2.0},
            {"value": "C", "text": "고급자 수준", "weight": 3.0}
        ]
    },
    # Q10 - 수정 (투자 결정 → 학습 방식 선호)
    {
        "id": 10,
        "category": "knowledge",
        "question": "투자 전략을 학습할 때 선호하는 방식은 무엇인가요?",
        "options": [
            {"value": "A", "text": "전문가 의견을 참고하며 학습", "weight": 1.5},
            {"value": "B", "text": "자료를 분석하며 학습", "weight": 2.0},
            {"value": "C", "text": "독립적으로 연구하며 학습", "weight": 2.5}
        ]
    },
    # Q11 - 수정 (투자 계획 → 시뮬레이션 패턴)
    {
        "id": 11,
        "category": "amount",
        "question": "시뮬레이션에서 학습해 보고 싶은 자산 운용 패턴은 무엇인가요?",
        "options": [
            {"value": "A", "text": "단기 변동성 중심 패턴", "weight": 1.0},
            {"value": "B", "text": "비정기적 투입 패턴", "weight": 2.0},
            {"value": "C", "text": "정기적 적립 패턴", "weight": 3.0}
        ]
    },
    # Q12 - 수정 (월 투자 가능액 → 가상 월 투자금액)
    {
        "id": 12,
        "category": "amount",
        "question": "시뮬레이션에 사용할 가상 월 투자금액 범위는 어느 정도인가요?",
        "options": [
            {"value": "A", "text": "소액 (10~50만원)", "weight": 1.0},
            {"value": "B", "text": "중액 (50~300만원)", "weight": 2.0},
            {"value": "C", "text": "고액 (300만원 이상)", "weight": 3.0}
        ]
    },
    # Q13 - 수정 (오타 수정 + 확인 빈도 표현 개선)
    {
        "id": 13,
        "category": "risk",
        "question": "자산 운용 결과를 확인하는 빈도는 어느 정도가 적절하다고 생각하시나요?",
        "options": [
            {"value": "A", "text": "매일 확인", "weight": 1.0},
            {"value": "B", "text": "주 1~2회 확인", "weight": 2.0},
            {"value": "C", "text": "월 1회 이상 확인", "weight": 3.0}
        ]
    },
    # Q14 - 수정 (시장 급락 반응 → 급변 시나리오 전략 학습)
    {
        "id": 14,
        "category": "risk",
        "question": "시장 급변 상황을 가정한 시나리오에서 학습해 보고 싶은 전략은 무엇인가요?",
        "options": [
            {"value": "A", "text": "리스크 회피 전략", "weight": 1.0},
            {"value": "B", "text": "관망 전략", "weight": 2.0},
            {"value": "C", "text": "역발상 대응 전략", "weight": 3.0}
        ]
    },
    # Q15 - 수정 (금융 생활 안정성 → 재정 상황 인식)
    {
        "id": 15,
        "category": "duration",
        "question": "자산 관리 학습 외의 전반적인 재정 상황은 어떠한 편인가요?",
        "options": [
            {"value": "A", "text": "여유가 거의 없습니다", "weight": 1.0},
            {"value": "B", "text": "크지는 않지만 일정한 여유가 있습니다", "weight": 2.0},
            {"value": "C", "text": "여유 자금을 중심으로 학습할 수 있습니다", "weight": 3.0}
        ]
    },
]

@router.get("/questions")
async def get_survey_questions(current_user = Depends(get_current_user)):
    """
    투자 성향 진단 설문 문항 조회 (교육용)

    ⚠️ 본 설문은 교육 및 정보 제공 목적의 자가 점검 도구이며,
    투자 권유·추천·자문을 제공하지 않습니다.
    """
    return {"total": len(SURVEY_QUESTIONS), "questions": SURVEY_QUESTIONS}

@router.post("/submit")
async def submit_survey(data: dict, current_user = Depends(get_current_user)):
    """
    설문 제출 (교육용)

    ⚠️ 제출된 응답은 전략 학습 시뮬레이션 생성에만 사용되며,
    투자 권유·자문 목적으로 사용되지 않습니다.
    """
    return {"status": "success", "message": "설문이 접수되었습니다"}