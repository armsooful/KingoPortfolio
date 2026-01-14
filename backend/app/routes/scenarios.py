"""
관리형 시나리오 API 엔드포인트

⚠️ 교육 목적: 본 API는 투자 전략 학습을 위한 시나리오 정보를 제공합니다.
투자 권유·추천·자문·일임 서비스를 제공하지 않습니다.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


# 시나리오 Pydantic 모델
class ScenarioAllocation(BaseModel):
    """자산 배분 비율"""
    stocks: float = Field(..., description="주식 비율 (%)")
    bonds: float = Field(..., description="채권 비율 (%)")
    money_market: float = Field(..., description="단기금융 비율 (%)")
    gold: float = Field(..., description="금 비율 (%)")
    other: float = Field(..., description="기타 비율 (%)")


class ScenarioRiskMetrics(BaseModel):
    """시나리오 위험 지표 (과거 데이터 기반 참고치)"""
    expected_volatility: str = Field(..., description="예상 변동성 범위")
    historical_max_drawdown: str = Field(..., description="과거 최대 낙폭 범위")
    recovery_expectation: str = Field(..., description="회복 기간 예상")


class ScenarioSummary(BaseModel):
    """시나리오 요약 정보"""
    id: str
    name: str
    name_ko: str
    short_description: str


class ScenarioDetail(BaseModel):
    """시나리오 상세 정보"""
    id: str
    name: str
    name_ko: str
    description: str
    objective: str
    target_investor: str
    allocation: ScenarioAllocation
    risk_metrics: ScenarioRiskMetrics
    disclaimer: str
    learning_points: List[str]


# 관리형 시나리오 데이터 (코드 상수)
# DB 반영은 Phase 2로 미룸
SCENARIOS: Dict[str, dict] = {
    "MIN_VOL": {
        "id": "MIN_VOL",
        "name": "Minimum Volatility",
        "name_ko": "변동성 최소화",
        "description": "변동성을 최소화하는 전략을 학습하기 위한 시나리오입니다. 시장 변동에 덜 민감한 자산 배분을 통해 안정적인 포트폴리오 구성 방법을 이해할 수 있습니다.",
        "objective": "변동성 최소화를 통한 안정적 자산 운용 학습",
        "target_investor": "변동성에 민감하며 안정적인 자산 운용을 학습하고자 하는 분",
        "allocation": {
            "stocks": 15,
            "bonds": 45,
            "money_market": 25,
            "gold": 10,
            "other": 5
        },
        "risk_metrics": {
            "expected_volatility": "5-8% (연간)",
            "historical_max_drawdown": "8-12%",
            "recovery_expectation": "상대적으로 짧은 회복 기간 예상"
        },
        "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",
        "learning_points": [
            "변동성과 위험의 관계 이해",
            "방어적 자산 배분의 원리",
            "안정성 중심 포트폴리오 구성 방법",
            "낮은 변동성이 장기 성과에 미치는 영향"
        ]
    },
    "DEFENSIVE": {
        "id": "DEFENSIVE",
        "name": "Defensive",
        "name_ko": "방어형",
        "description": "시장 하락기에 대비하는 방어적 전략을 학습하기 위한 시나리오입니다. 손실 최소화와 자산 보존에 중점을 둔 포트폴리오 구성 방법을 이해할 수 있습니다.",
        "objective": "시장 하락 시 손실 최소화 전략 학습",
        "target_investor": "손실 회피 성향이 강하며 자산 보존을 우선시하는 분",
        "allocation": {
            "stocks": 25,
            "bonds": 40,
            "money_market": 20,
            "gold": 10,
            "other": 5
        },
        "risk_metrics": {
            "expected_volatility": "7-10% (연간)",
            "historical_max_drawdown": "10-15%",
            "recovery_expectation": "중간 수준의 회복 기간 예상"
        },
        "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",
        "learning_points": [
            "방어적 투자 전략의 개념",
            "채권과 안전자산의 역할",
            "시장 하락기 대응 방법",
            "분산투자를 통한 위험 관리"
        ]
    },
    "GROWTH": {
        "id": "GROWTH",
        "name": "Growth",
        "name_ko": "성장형",
        "description": "장기적 자산 성장을 목표로 하는 전략을 학습하기 위한 시나리오입니다. 높은 변동성을 감내하면서 성장 잠재력이 높은 자산에 대해 학습할 수 있습니다.",
        "objective": "장기 자산 성장 전략 학습",
        "target_investor": "장기적 관점에서 높은 변동성을 감내할 수 있는 분",
        "allocation": {
            "stocks": 55,
            "bonds": 20,
            "money_market": 10,
            "gold": 10,
            "other": 5
        },
        "risk_metrics": {
            "expected_volatility": "12-18% (연간)",
            "historical_max_drawdown": "20-30%",
            "recovery_expectation": "긴 회복 기간이 필요할 수 있음"
        },
        "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",
        "learning_points": [
            "성장주 투자의 특성",
            "장기 투자와 복리 효과",
            "높은 변동성과 심리적 대응",
            "시간 분산의 중요성"
        ]
    }
}


@router.get(
    "",
    response_model=List[ScenarioSummary],
    summary="시나리오 목록 조회",
    description="학습 가능한 관리형 시나리오 목록을 반환합니다."
)
async def get_scenarios():
    """
    관리형 시나리오 목록 조회

    현재 제공되는 시나리오:
    - **MIN_VOL**: 변동성 최소화 전략
    - **DEFENSIVE**: 방어형 전략
    - **GROWTH**: 성장형 전략

    ⚠️ 본 시나리오는 교육 목적이며, 투자 권유가 아닙니다.
    """
    scenarios_list = [
        ScenarioSummary(
            id=scenario["id"],
            name=scenario["name"],
            name_ko=scenario["name_ko"],
            short_description=scenario["objective"]
        )
        for scenario in SCENARIOS.values()
    ]
    return scenarios_list


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetail,
    summary="시나리오 상세 조회",
    description="특정 시나리오의 상세 정보를 반환합니다."
)
async def get_scenario_detail(scenario_id: str):
    """
    시나리오 상세 정보 조회

    시나리오 ID로 해당 시나리오의 상세 정보를 조회합니다.

    **포함 정보:**
    - 시나리오 설명 및 목표
    - 자산 배분 비율
    - 위험 지표 (과거 데이터 기반 참고치)
    - 학습 포인트

    ⚠️ 본 시나리오는 교육 목적이며, 투자 권유가 아닙니다.
    """
    scenario_id_upper = scenario_id.upper()

    if scenario_id_upper not in SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found. Available: {list(SCENARIOS.keys())}"
        )

    scenario = SCENARIOS[scenario_id_upper]

    return ScenarioDetail(
        id=scenario["id"],
        name=scenario["name"],
        name_ko=scenario["name_ko"],
        description=scenario["description"],
        objective=scenario["objective"],
        target_investor=scenario["target_investor"],
        allocation=ScenarioAllocation(**scenario["allocation"]),
        risk_metrics=ScenarioRiskMetrics(**scenario["risk_metrics"]),
        disclaimer=scenario["disclaimer"],
        learning_points=scenario["learning_points"]
    )
