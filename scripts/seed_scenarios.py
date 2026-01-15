#!/usr/bin/env python3
"""
P1-C1: 시나리오/포트폴리오 구성비 Seed 스크립트

scenario_definition, portfolio_model, portfolio_allocation 테이블에
관리형 시나리오 및 구성비를 적재

Usage:
    # 전체 seed
    python scripts/seed_scenarios.py

    # 특정 시나리오만
    python scripts/seed_scenarios.py --scenario MIN_VOL

    # Dry-run (실제 적재 없이 확인)
    python scripts/seed_scenarios.py --dry-run
"""

import argparse
import sys
import os
from datetime import date
from decimal import Decimal

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# 설정
# ============================================================================

ENGINE_VERSION = os.getenv("ENGINE_VERSION", "1.0.0")

# 시나리오 정의 (scenarios.py의 SCENARIOS와 동기화)
SCENARIOS = {
    "MIN_VOL": {
        "scenario_id": "MIN_VOL",
        "name_ko": "변동성 최소화",
        "name_en": "Minimum Volatility",
        "description": "변동성을 최소화하는 전략을 학습하기 위한 시나리오입니다. 시장 변동에 덜 민감한 자산 배분을 통해 안정적인 포트폴리오 구성 방법을 이해할 수 있습니다.",
        "objective": "변동성 최소화를 통한 안정적 자산 운용 학습",
        "target_investor": "변동성에 민감하며 안정적인 자산 운용을 학습하고자 하는 분",
        "risk_level": "LOW",
        "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",
        "display_order": 1,
        "risk_metrics": {
            "expected_volatility": "5-8% (연간)",
            "historical_max_drawdown": "8-12%",
            "recovery_expectation": "상대적으로 짧은 회복 기간 예상"
        },
        "learning_points": [
            "변동성과 위험의 관계 이해",
            "방어적 자산 배분의 원리",
            "안정성 중심 포트폴리오 구성 방법",
            "낮은 변동성이 장기 성과에 미치는 영향"
        ],
        # 포트폴리오 구성비 (자산클래스 → 비중)
        "allocation": {
            "EQUITY": 0.15,      # 주식 15%
            "BOND": 0.45,        # 채권 45%
            "CASH": 0.25,        # 단기금융 25%
            "COMMODITY": 0.10,   # 금 10%
            "OTHER": 0.05,       # 기타 5%
        },
        # 자산클래스별 대표 ETF 매핑 (instrument_master ticker)
        "instrument_mapping": {
            "EQUITY": "069500",      # KODEX 200
            "BOND": "148070",        # KOSEF 국고채10년
            "CASH": "148020",        # KBSTAR 200 (대용, 실제로는 MMF 필요)
            "COMMODITY": "132030",   # KODEX 골드선물(H)
            "OTHER": "152100",       # ARIRANG 200 (대용)
        }
    },
    "DEFENSIVE": {
        "scenario_id": "DEFENSIVE",
        "name_ko": "방어형",
        "name_en": "Defensive",
        "description": "시장 하락기에 대비하는 방어적 전략을 학습하기 위한 시나리오입니다. 손실 최소화와 자산 보존에 중점을 둔 포트폴리오 구성 방법을 이해할 수 있습니다.",
        "objective": "시장 하락 시 손실 최소화 전략 학습",
        "target_investor": "손실 회피 성향이 강하며 자산 보존을 우선시하는 분",
        "risk_level": "LOW",
        "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",
        "display_order": 2,
        "risk_metrics": {
            "expected_volatility": "7-10% (연간)",
            "historical_max_drawdown": "10-15%",
            "recovery_expectation": "중간 수준의 회복 기간 예상"
        },
        "learning_points": [
            "방어적 투자 전략의 개념",
            "채권과 안전자산의 역할",
            "시장 하락기 대응 방법",
            "분산투자를 통한 위험 관리"
        ],
        "allocation": {
            "EQUITY": 0.25,      # 주식 25%
            "BOND": 0.40,        # 채권 40%
            "CASH": 0.20,        # 단기금융 20%
            "COMMODITY": 0.10,   # 금 10%
            "OTHER": 0.05,       # 기타 5%
        },
        "instrument_mapping": {
            "EQUITY": "069500",      # KODEX 200
            "BOND": "148070",        # KOSEF 국고채10년
            "CASH": "148020",        # KBSTAR 200
            "COMMODITY": "132030",   # KODEX 골드선물(H)
            "OTHER": "152100",       # ARIRANG 200
        }
    },
    "GROWTH": {
        "scenario_id": "GROWTH",
        "name_ko": "성장형",
        "name_en": "Growth",
        "description": "장기적 자산 성장을 목표로 하는 전략을 학습하기 위한 시나리오입니다. 높은 변동성을 감내하면서 성장 잠재력이 높은 자산에 대해 학습할 수 있습니다.",
        "objective": "장기 자산 성장 전략 학습",
        "target_investor": "장기적 관점에서 높은 변동성을 감내할 수 있는 분",
        "risk_level": "HIGH",
        "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",
        "display_order": 3,
        "risk_metrics": {
            "expected_volatility": "12-18% (연간)",
            "historical_max_drawdown": "20-30%",
            "recovery_expectation": "긴 회복 기간이 필요할 수 있음"
        },
        "learning_points": [
            "성장주 투자의 특성",
            "장기 투자와 복리 효과",
            "높은 변동성과 심리적 대응",
            "시간 분산의 중요성"
        ],
        "allocation": {
            "EQUITY": 0.55,      # 주식 55%
            "BOND": 0.20,        # 채권 20%
            "CASH": 0.10,        # 단기금융 10%
            "COMMODITY": 0.10,   # 금 10%
            "OTHER": 0.05,       # 기타 5%
        },
        "instrument_mapping": {
            "EQUITY": "069500",      # KODEX 200
            "BOND": "148070",        # KOSEF 국고채10년
            "CASH": "148020",        # KBSTAR 200
            "COMMODITY": "132030",   # KODEX 골드선물(H)
            "OTHER": "152100",       # ARIRANG 200
        }
    }
}


# ============================================================================
# 유틸리티
# ============================================================================

def get_database_url():
    """데이터베이스 URL 반환 (PostgreSQL 우선)"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url or "sqlite" in db_url:
        print("⚠️  PostgreSQL DATABASE_URL이 설정되지 않았습니다.")
        print("   예: export DATABASE_URL=postgresql://user:pass@localhost:5432/foresto_dev")
        sys.exit(1)
    return db_url


def create_session():
    """SQLAlchemy 세션 생성"""
    db_url = get_database_url()
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def get_instrument_id(session, ticker: str) -> int | None:
    """티커로 instrument_id 조회"""
    sql = text("""
        SELECT instrument_id FROM instrument_master
        WHERE ticker = :ticker AND is_active = TRUE
    """)
    result = session.execute(sql, {"ticker": ticker}).fetchone()
    return result[0] if result else None


def validate_allocation_sum(allocation: dict) -> bool:
    """구성비 합계 검증 (1.0 ± 0.0001)"""
    total = sum(allocation.values())
    return abs(total - 1.0) < 0.0001


# ============================================================================
# Seed 함수
# ============================================================================

def upsert_scenario(session, scenario: dict) -> bool:
    """
    시나리오 정의 upsert

    Returns:
        True if inserted, False if updated
    """
    check_sql = text("""
        SELECT 1 FROM scenario_definition
        WHERE scenario_id = :scenario_id
    """)
    exists = session.execute(check_sql, {"scenario_id": scenario["scenario_id"]}).fetchone()

    # JSON 필드 (risk_metrics, learning_points)
    import json
    risk_metrics_json = json.dumps(scenario.get("risk_metrics", {}), ensure_ascii=False)
    learning_points_json = json.dumps(scenario.get("learning_points", []), ensure_ascii=False)

    if exists:
        update_sql = text("""
            UPDATE scenario_definition
            SET name_ko = :name_ko,
                name_en = :name_en,
                description = :description,
                objective = :objective,
                target_investor = :target_investor,
                risk_level = :risk_level,
                disclaimer = :disclaimer,
                display_order = :display_order,
                updated_at = NOW()
            WHERE scenario_id = :scenario_id
        """)
        session.execute(update_sql, {
            "scenario_id": scenario["scenario_id"],
            "name_ko": scenario["name_ko"],
            "name_en": scenario["name_en"],
            "description": scenario["description"],
            "objective": scenario["objective"],
            "target_investor": scenario["target_investor"],
            "risk_level": scenario["risk_level"],
            "disclaimer": scenario["disclaimer"],
            "display_order": scenario["display_order"],
        })
        return False
    else:
        insert_sql = text("""
            INSERT INTO scenario_definition
            (scenario_id, name_ko, name_en, description, objective, target_investor,
             risk_level, disclaimer, display_order, is_active)
            VALUES (:scenario_id, :name_ko, :name_en, :description, :objective, :target_investor,
                    :risk_level, :disclaimer, :display_order, TRUE)
        """)
        session.execute(insert_sql, {
            "scenario_id": scenario["scenario_id"],
            "name_ko": scenario["name_ko"],
            "name_en": scenario["name_en"],
            "description": scenario["description"],
            "objective": scenario["objective"],
            "target_investor": scenario["target_investor"],
            "risk_level": scenario["risk_level"],
            "disclaimer": scenario["disclaimer"],
            "display_order": scenario["display_order"],
        })
        return True


def upsert_portfolio_model(session, scenario_id: str, effective_date: date) -> int:
    """
    포트폴리오 모델 upsert

    Returns:
        portfolio_id
    """
    check_sql = text("""
        SELECT portfolio_id FROM portfolio_model
        WHERE scenario_id = :scenario_id AND effective_date = :effective_date
    """)
    result = session.execute(check_sql, {
        "scenario_id": scenario_id,
        "effective_date": effective_date
    }).fetchone()

    if result:
        return result[0]

    insert_sql = text("""
        INSERT INTO portfolio_model
        (scenario_id, portfolio_name, effective_date, rebalance_freq, engine_version)
        VALUES (:scenario_id, :portfolio_name, :effective_date, 'NONE', :engine_version)
        RETURNING portfolio_id
    """)
    result = session.execute(insert_sql, {
        "scenario_id": scenario_id,
        "portfolio_name": f"{scenario_id}_v1",
        "effective_date": effective_date,
        "engine_version": ENGINE_VERSION
    })
    return result.fetchone()[0]


def upsert_allocation(session, portfolio_id: int, instrument_id: int,
                      weight: float, asset_class: str) -> bool:
    """
    포트폴리오 구성비 upsert

    Returns:
        True if inserted, False if updated
    """
    check_sql = text("""
        SELECT 1 FROM portfolio_allocation
        WHERE portfolio_id = :portfolio_id AND instrument_id = :instrument_id
    """)
    exists = session.execute(check_sql, {
        "portfolio_id": portfolio_id,
        "instrument_id": instrument_id
    }).fetchone()

    if exists:
        update_sql = text("""
            UPDATE portfolio_allocation
            SET weight = :weight, asset_class = :asset_class
            WHERE portfolio_id = :portfolio_id AND instrument_id = :instrument_id
        """)
        session.execute(update_sql, {
            "portfolio_id": portfolio_id,
            "instrument_id": instrument_id,
            "weight": weight,
            "asset_class": asset_class
        })
        return False
    else:
        insert_sql = text("""
            INSERT INTO portfolio_allocation
            (portfolio_id, instrument_id, weight, asset_class)
            VALUES (:portfolio_id, :instrument_id, :weight, :asset_class)
        """)
        session.execute(insert_sql, {
            "portfolio_id": portfolio_id,
            "instrument_id": instrument_id,
            "weight": weight,
            "asset_class": asset_class
        })
        return True


def seed_scenario(session, scenario_id: str, effective_date: date) -> dict:
    """
    시나리오 전체 seed (scenario_definition + portfolio_model + portfolio_allocation)

    Returns:
        {"scenario": bool, "portfolio_id": int, "allocations": int}
    """
    if scenario_id not in SCENARIOS:
        print(f"❌ 알 수 없는 시나리오: {scenario_id}")
        return {"error": f"Unknown scenario: {scenario_id}"}

    scenario = SCENARIOS[scenario_id]

    # 구성비 검증
    if not validate_allocation_sum(scenario["allocation"]):
        total = sum(scenario["allocation"].values())
        print(f"❌ {scenario_id}: 구성비 합계 오류 ({total} != 1.0)")
        return {"error": f"Weight sum error: {total}"}

    # 1. 시나리오 정의
    is_new = upsert_scenario(session, scenario)
    print(f"  {'✅ INSERT' if is_new else '🔄 UPDATE'}: scenario_definition/{scenario_id}")

    # 2. 포트폴리오 모델
    portfolio_id = upsert_portfolio_model(session, scenario_id, effective_date)
    print(f"  📦 portfolio_model: portfolio_id={portfolio_id}")

    # 3. 포트폴리오 구성비
    allocation_count = 0
    for asset_class, weight in scenario["allocation"].items():
        ticker = scenario["instrument_mapping"].get(asset_class)
        if not ticker:
            print(f"    ⚠️  {asset_class}: 매핑된 티커 없음")
            continue

        instrument_id = get_instrument_id(session, ticker)
        if not instrument_id:
            print(f"    ⚠️  {ticker}: instrument_master에 없음 (seed_instruments.py 먼저 실행)")
            continue

        is_new = upsert_allocation(session, portfolio_id, instrument_id, weight, asset_class)
        print(f"    {'✅' if is_new else '🔄'} {asset_class}: {ticker} → {weight:.2%}")
        allocation_count += 1

    session.commit()
    return {
        "scenario": scenario_id,
        "portfolio_id": portfolio_id,
        "allocations": allocation_count
    }


# ============================================================================
# 메인
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="시나리오/포트폴리오 구성비 Seed (P1-C1)")
    parser.add_argument("--scenario", help="특정 시나리오만 처리 (예: MIN_VOL)")
    parser.add_argument("--effective-date", default="2025-01-01",
                        help="포트폴리오 적용일 (기본: 2025-01-01)")
    parser.add_argument("--dry-run", action="store_true", help="실제 적재 없이 대상만 출력")
    args = parser.parse_args()

    print("=" * 60)
    print("Foresto Phase 1 - 시나리오/포트폴리오 Seed (P1-C1)")
    print("=" * 60)
    print(f"📌 Engine Version: {ENGINE_VERSION}")

    # 대상 시나리오
    if args.scenario:
        scenario_ids = [args.scenario.upper()]
    else:
        scenario_ids = list(SCENARIOS.keys())

    print(f"\n📊 대상 시나리오: {len(scenario_ids)}개")
    for sid in scenario_ids:
        if sid in SCENARIOS:
            print(f"  - {sid}: {SCENARIOS[sid]['name_ko']}")
        else:
            print(f"  - {sid}: ❌ 알 수 없는 시나리오")

    if args.dry_run:
        print("\n⚠️  DRY RUN 모드 - 실제 적재하지 않음")
        print("\n구성비 검증:")
        for sid in scenario_ids:
            if sid not in SCENARIOS:
                continue
            scenario = SCENARIOS[sid]
            total = sum(scenario["allocation"].values())
            valid = "✅" if abs(total - 1.0) < 0.0001 else "❌"
            print(f"  {sid}: {total:.4f} {valid}")
            for asset_class, weight in scenario["allocation"].items():
                ticker = scenario["instrument_mapping"].get(asset_class, "N/A")
                print(f"    - {asset_class}: {weight:.2%} ({ticker})")
        return

    # 날짜 파싱
    from datetime import datetime
    effective_date = datetime.strptime(args.effective_date, "%Y-%m-%d").date()

    # DB 연결
    session, engine = create_session()
    print(f"\n📦 Database: {str(engine.url)[:40]}...")

    # Seed 실행
    total_scenarios = 0
    total_allocations = 0

    for scenario_id in scenario_ids:
        print(f"\n[{scenario_id}] 처리 중...")
        result = seed_scenario(session, scenario_id, effective_date)

        if "error" not in result:
            total_scenarios += 1
            total_allocations += result.get("allocations", 0)

    print("\n" + "=" * 60)
    print(f"✅ 완료: 시나리오 {total_scenarios}개, 구성비 {total_allocations}건")
    print("=" * 60)

    session.close()


if __name__ == "__main__":
    main()
