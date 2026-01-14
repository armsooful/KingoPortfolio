from fastapi import APIRouter, Depends
from app.auth import get_current_user

router = APIRouter(prefix="/api/survey", tags=["Survey"])

# ⚠️ 법적 검토 완료: 투자자문업 위반 요소 제거 (2026-01-10)
# - "투자 목표", "금융상품", "투자 결정", "매수/매도" 등 규제 용어 제거
# - "학습", "시뮬레이션", "전략 탐색" 등 교육 목적 용어로 전면 교체

SURVEY_QUESTIONS = [
    # Q1 - 유지 (법적 문제 없음)
    {
        "id": 1,
        "category": "experience",
        "question": "당신의 투자 경험은?",
        "options": [
            {"value": "A", "text": "처음입니다", "weight": 1.0},
            {"value": "B", "text": "약간 있습니다", "weight": 2.0},
            {"value": "C", "text": "충분합니다", "weight": 3.0}
        ]
    },

    # Q2 - 유지 (법적 문제 없음)
    {
        "id": 2,
        "category": "experience",
        "question": "투자로 손실을 본 경험이 있으신가요?",
        "options": [
            {"value": "A", "text": "없습니다", "weight": 1.0},
            {"value": "B", "text": "작은 손실을 본 적 있습니다", "weight": 2.0},
            {"value": "C", "text": "큰 손실을 본 적 있습니다", "weight": 3.0}
        ]
    },

    # Q3 - 유지 (법적 문제 없음)
    {
        "id": 3,
        "category": "duration",
        "question": "투자 계획 기간은?",
        "options": [
            {"value": "A", "text": "1년 이하", "weight": 1.0},
            {"value": "B", "text": "1-3년", "weight": 2.5},
            {"value": "C", "text": "3년 이상", "weight": 3.0}
        ]
    },

    # Q4 - 수정 (투자 목표 → 학습 방향)
    {
        "id": 4,
        "category": "duration",
        "question": "선호하는 투자 전략 학습 방향은?",
        "options": [
            {"value": "A", "text": "안정성 중심 전략", "weight": 1.0},
            {"value": "B", "text": "균형형 전략", "weight": 2.0},
            {"value": "C", "text": "성장성 중심 전략", "weight": 3.0}
        ]
    },

    # Q5 - 수정 (포트폴리오 하락 → 시뮬레이션 학습)
    {
        "id": 5,
        "category": "risk",
        "question": "가상 시뮬레이션에서 자산이 10% 하락했을 때 학습하고 싶은 대응 전략은?",
        "options": [
            {"value": "A", "text": "손절 전략", "weight": 1.0},
            {"value": "B", "text": "관망 전략", "weight": 2.0},
            {"value": "C", "text": "역발상 매수 전략", "weight": 3.0}
        ]
    },

    # Q6 - 유지 (법적 문제 없음)
    {
        "id": 6,
        "category": "risk",
        "question": "자산 변동성을 얼마나 견딜 수 있나요?",
        "options": [
            {"value": "A", "text": "거의 못 견딥니다", "weight": 1.0},
            {"value": "B", "text": "어느 정도 견딜 수 있습니다", "weight": 2.0},
            {"value": "C", "text": "충분히 견딜 수 있습니다", "weight": 3.0}
        ]
    },

    # Q7 - 유지 (법적 문제 없음)
    {
        "id": 7,
        "category": "risk",
        "question": "위험을 감수할 의향이 있으신가요?",
        "options": [
            {"value": "A", "text": "아니요, 안정성을 원합니다", "weight": 1.0},
            {"value": "B", "text": "적정 수준의 위험은 괜찮습니다", "weight": 2.0},
            {"value": "C", "text": "높은 수익을 위해 위험을 감수하겠습니다", "weight": 3.0}
        ]
    },

    # Q8 - 유지 (법적 문제 없음)
    {
        "id": 8,
        "category": "risk",
        "question": "투자금의 최대 손실을 어느 정도까지 허용하나요?",
        "options": [
            {"value": "A", "text": "0% (손실 불가)", "weight": 1.0},
            {"value": "B", "text": "10% 이내", "weight": 2.0},
            {"value": "C", "text": "20% 이상", "weight": 3.0}
        ]
    },

    # Q9 - 수정 (금융상품 → 투자 지식)
    {
        "id": 9,
        "category": "knowledge",
        "question": "투자 관련 일반 지식 수준은?",
        "options": [
            {"value": "A", "text": "초보자", "weight": 1.0},
            {"value": "B", "text": "중급자", "weight": 2.0},
            {"value": "C", "text": "고급자", "weight": 3.0}
        ]
    },

    # Q10 - 수정 (투자 결정 → 학습 방식)
    {
        "id": 10,
        "category": "knowledge",
        "question": "투자 전략 학습 시 선호하는 방식은?",
        "options": [
            {"value": "A", "text": "전문가 의견 참고형", "weight": 1.5},
            {"value": "B", "text": "자가 분석형", "weight": 2.0},
            {"value": "C", "text": "독립 연구형", "weight": 2.5}
        ]
    },

    # Q11 - 수정 (투자 계획 → 시뮬레이션 패턴)
    {
        "id": 11,
        "category": "amount",
        "question": "시뮬레이션에서 학습하고 싶은 투자 패턴은?",
        "options": [
            {"value": "A", "text": "단기 매매 전략", "weight": 1.0},
            {"value": "B", "text": "비정기 투자 전략", "weight": 2.0},
            {"value": "C", "text": "정기 적립식 전략", "weight": 3.0}
        ]
    },

    # Q12 - 수정 (투자 가능액 → 시뮬레이션 금액)
    {
        "id": 12,
        "category": "amount",
        "question": "시뮬레이션에 사용할 가상 월 투자금액 범위는?",
        "options": [
            {"value": "A", "text": "소액 (10-50만원)", "weight": 1.0},
            {"value": "B", "text": "중액 (50-300만원)", "weight": 2.0},
            {"value": "C", "text": "고액 (300만원 이상)", "weight": 3.0}
        ]
    },

    # Q13 - 유지 (오타만 수정: "어자" → "얼마나")
    {
        "id": 13,
        "category": "risk",
        "question": "투자 성과를 얼마나 자주 확인하나요?",
        "options": [
            {"value": "A", "text": "매일 확인합니다", "weight": 1.0},
            {"value": "B", "text": "주 1-2회 확인합니다", "weight": 2.0},
            {"value": "C", "text": "월 1회 이상 확인합니다", "weight": 3.0}
        ]
    },

    # Q14 - 수정 (매도/매수 → 전략 학습)
    {
        "id": 14,
        "category": "risk",
        "question": "시장 급락 시나리오에서 학습하고 싶은 전략은?",
        "options": [
            {"value": "A", "text": "리스크 회피 전략", "weight": 1.0},
            {"value": "B", "text": "관망 전략", "weight": 2.0},
            {"value": "C", "text": "역발상 매수 전략", "weight": 3.0}
        ]
    },

    # Q15 - 유지 (법적 문제 없음)
    {
        "id": 15,
        "category": "duration",
        "question": "투자 외 금융 생활은 안정적인가요?",
        "options": [
            {"value": "A", "text": "생활비 충당이 어렵습니다", "weight": 1.0},
            {"value": "B", "text": "생활비는 괜찮지만 여유가 적습니다", "weight": 2.0},
            {"value": "C", "text": "여유로운 자금으로 투자합니다", "weight": 3.0}
        ]
    },
]

@router.get("/questions")
async def get_survey_questions(current_user = Depends(get_current_user)):
    """
    투자 성향 진단 설문 문항 조회 (교육용)

    ⚠️ 본 설문은 교육 목적의 자가 점검 도구이며,
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
