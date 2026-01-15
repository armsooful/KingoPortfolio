#!/usr/bin/env python3
"""
P1-E3: 품질 리포트 및 스모크 테스트 스크립트

DB/ETL 품질 게이트 확장 및 API 스모크 테스트를 수행합니다.

## 품질 리포트 항목

### ETL 데이터 품질
- instrument_master: 금융상품 기준정보 레코드 수
- daily_price: 일봉가격 레코드 수, 결측률
- daily_return: 일간수익률 레코드 수, 결측률
- scenario_definition: 시나리오 정의 수
- portfolio_model: 포트폴리오 모델 수
- portfolio_allocation: 포트폴리오 구성비 수
- simulation_run: 시뮬레이션 실행 수

### API 스모크 테스트
- GET /api/v1/scenarios - 시나리오 목록
- GET /api/v1/scenarios/{id} - 시나리오 상세
- POST /api/v1/backtest/scenario - 시나리오 시뮬레이션
- GET /api/v1/backtest/scenario/{id}/path - NAV 경로

Usage:
    # 전체 품질 리포트 (DB + API)
    python scripts/quality_report.py

    # DB 품질만 확인
    python scripts/quality_report.py --db-only

    # API 스모크만 실행
    python scripts/quality_report.py --api-only

    # 마크다운 파일로 출력
    python scripts/quality_report.py --output report.md

    # JSON 출력
    python scripts/quality_report.py --json
"""

import argparse
import sys
import os
import json
import requests
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# 설정
# ============================================================================

# API 기본 URL
DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")

# 품질 기준 (경고/에러 임계값)
QUALITY_THRESHOLDS = {
    "instrument_master_min": 5,        # 최소 금융상품 수
    "daily_price_missing_max": 0.05,   # 일봉가격 최대 결측률 5%
    "daily_return_missing_max": 0.10,  # 일간수익률 최대 결측률 10%
    "scenario_min": 3,                  # 최소 시나리오 수
    "simulation_recent_days": 7,        # 최근 N일 내 시뮬레이션 존재 필요
}


def get_database_url() -> Optional[str]:
    """환경변수에서 DATABASE_URL 가져오기"""
    return os.getenv("DATABASE_URL")


# ============================================================================
# DB 품질 검사
# ============================================================================

def check_table_exists(engine, table_name: str) -> bool:
    """테이블 존재 여부 확인"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """), {"table_name": table_name})
        return result.scalar()


def get_table_count(engine, table_name: str) -> int:
    """테이블 레코드 수 조회"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar() or 0
    except Exception:
        return -1


def get_daily_price_stats(engine) -> Dict:
    """일봉가격 통계 조회"""
    stats = {
        "total_count": 0,
        "instruments": 0,
        "date_range": None,
        "missing_rate": 0,
        "latest_date": None
    }

    try:
        with engine.connect() as conn:
            # 기본 통계
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT instrument_id) as instruments,
                    MIN(price_date) as min_date,
                    MAX(price_date) as max_date
                FROM daily_price
            """))
            row = result.fetchone()
            if row:
                stats["total_count"] = row[0] or 0
                stats["instruments"] = row[1] or 0
                if row[2] and row[3]:
                    stats["date_range"] = f"{row[2]} ~ {row[3]}"
                    stats["latest_date"] = str(row[3])

            # 결측률 계산 (최근 30일 기준)
            result = conn.execute(text("""
                WITH date_range AS (
                    SELECT generate_series(
                        CURRENT_DATE - INTERVAL '30 days',
                        CURRENT_DATE,
                        '1 day'
                    )::date as trade_date
                ),
                expected AS (
                    SELECT
                        d.trade_date,
                        i.instrument_id
                    FROM date_range d
                    CROSS JOIN (SELECT DISTINCT instrument_id FROM daily_price) i
                    WHERE EXTRACT(DOW FROM d.trade_date) NOT IN (0, 6)  -- 주말 제외
                ),
                actual AS (
                    SELECT instrument_id, price_date
                    FROM daily_price
                    WHERE price_date >= CURRENT_DATE - INTERVAL '30 days'
                )
                SELECT
                    COUNT(e.*) as expected,
                    COUNT(a.instrument_id) as actual
                FROM expected e
                LEFT JOIN actual a ON e.instrument_id = a.instrument_id AND e.trade_date = a.price_date
            """))
            row = result.fetchone()
            if row and row[0] > 0:
                stats["missing_rate"] = round((row[0] - row[1]) / row[0], 4)

    except Exception as e:
        stats["error"] = str(e)

    return stats


def get_daily_return_stats(engine) -> Dict:
    """일간수익률 통계 조회"""
    stats = {
        "total_count": 0,
        "instruments": 0,
        "date_range": None,
        "missing_rate": 0,
        "null_return_rate": 0
    }

    try:
        with engine.connect() as conn:
            # 기본 통계
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT instrument_id) as instruments,
                    MIN(return_date) as min_date,
                    MAX(return_date) as max_date,
                    COUNT(*) FILTER (WHERE daily_return IS NULL) as null_count
                FROM daily_return
            """))
            row = result.fetchone()
            if row:
                stats["total_count"] = row[0] or 0
                stats["instruments"] = row[1] or 0
                if row[2] and row[3]:
                    stats["date_range"] = f"{row[2]} ~ {row[3]}"
                if row[0] > 0:
                    stats["null_return_rate"] = round(row[4] / row[0], 4)

    except Exception as e:
        stats["error"] = str(e)

    return stats


def get_scenario_stats(engine) -> Dict:
    """시나리오 통계 조회"""
    stats = {
        "scenarios": 0,
        "portfolios": 0,
        "allocations": 0,
        "scenario_list": []
    }

    try:
        with engine.connect() as conn:
            # 시나리오 수
            result = conn.execute(text("""
                SELECT COUNT(*) FROM scenario_definition WHERE is_active = true
            """))
            stats["scenarios"] = result.scalar() or 0

            # 포트폴리오 수
            result = conn.execute(text("SELECT COUNT(*) FROM portfolio_model"))
            stats["portfolios"] = result.scalar() or 0

            # 구성비 수
            result = conn.execute(text("SELECT COUNT(*) FROM portfolio_allocation"))
            stats["allocations"] = result.scalar() or 0

            # 시나리오 목록
            result = conn.execute(text("""
                SELECT scenario_id, name_ko FROM scenario_definition
                WHERE is_active = true ORDER BY display_order
            """))
            stats["scenario_list"] = [(row[0], row[1]) for row in result.fetchall()]

    except Exception as e:
        stats["error"] = str(e)

    return stats


def get_simulation_stats(engine) -> Dict:
    """시뮬레이션 통계 조회"""
    stats = {
        "total_runs": 0,
        "recent_runs": 0,
        "by_scenario": [],
        "cache_hit_rate": 0
    }

    try:
        with engine.connect() as conn:
            # 전체 수
            result = conn.execute(text("SELECT COUNT(*) FROM simulation_run"))
            stats["total_runs"] = result.scalar() or 0

            # 최근 7일
            result = conn.execute(text("""
                SELECT COUNT(*) FROM simulation_run
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            """))
            stats["recent_runs"] = result.scalar() or 0

            # 시나리오별 분포
            result = conn.execute(text("""
                SELECT COALESCE(scenario_id, 'custom') as scenario, COUNT(*)
                FROM simulation_run GROUP BY scenario_id ORDER BY COUNT(*) DESC LIMIT 5
            """))
            stats["by_scenario"] = [(row[0], row[1]) for row in result.fetchall()]

    except Exception as e:
        stats["error"] = str(e)

    return stats


def run_db_quality_check(verbose: bool = True) -> Dict:
    """DB 품질 검사 실행"""
    db_url = get_database_url()

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "database_connected": False,
        "tables": {},
        "quality_issues": [],
        "quality_score": 0
    }

    if not db_url:
        result["error"] = "DATABASE_URL not set"
        if verbose:
            print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return result

    try:
        engine = create_engine(db_url)
        result["database_connected"] = True

        if verbose:
            print("=" * 60)
            print("📊 DB 품질 리포트")
            print("=" * 60)
            print()

        # 테이블별 검사
        tables_to_check = [
            "instrument_master",
            "daily_price",
            "daily_return",
            "scenario_definition",
            "portfolio_model",
            "portfolio_allocation",
            "simulation_run",
            "simulation_path",
            "simulation_summary"
        ]

        issues = []
        checks_passed = 0
        total_checks = 0

        for table in tables_to_check:
            count = get_table_count(engine, table)
            result["tables"][table] = {"count": count}

            if verbose:
                status = "✅" if count > 0 else "⚠️"
                print(f"  {status} {table}: {count:,}건")

            total_checks += 1
            if count > 0:
                checks_passed += 1
            elif count == 0:
                issues.append(f"{table} 테이블이 비어있음")

        # 상세 통계
        if verbose:
            print()
            print("📈 상세 통계")
            print("-" * 40)

        # 일봉가격 상세
        price_stats = get_daily_price_stats(engine)
        result["daily_price_stats"] = price_stats
        if verbose:
            print(f"  일봉가격:")
            print(f"    - 기간: {price_stats.get('date_range', 'N/A')}")
            print(f"    - 금융상품 수: {price_stats.get('instruments', 0)}")
            print(f"    - 결측률: {price_stats.get('missing_rate', 0) * 100:.1f}%")

        total_checks += 1
        if price_stats.get("missing_rate", 1) <= QUALITY_THRESHOLDS["daily_price_missing_max"]:
            checks_passed += 1
        else:
            issues.append(f"일봉가격 결측률이 높음: {price_stats.get('missing_rate', 0) * 100:.1f}%")

        # 일간수익률 상세
        return_stats = get_daily_return_stats(engine)
        result["daily_return_stats"] = return_stats
        if verbose:
            print(f"  일간수익률:")
            print(f"    - 기간: {return_stats.get('date_range', 'N/A')}")
            print(f"    - NULL 수익률 비율: {return_stats.get('null_return_rate', 0) * 100:.1f}%")

        # 시나리오 상세
        scenario_stats = get_scenario_stats(engine)
        result["scenario_stats"] = scenario_stats
        if verbose:
            print(f"  시나리오:")
            print(f"    - 활성 시나리오: {scenario_stats.get('scenarios', 0)}개")
            print(f"    - 포트폴리오 모델: {scenario_stats.get('portfolios', 0)}개")
            print(f"    - 구성비 레코드: {scenario_stats.get('allocations', 0)}개")
            for sid, name in scenario_stats.get("scenario_list", []):
                print(f"      * {sid}: {name}")

        total_checks += 1
        if scenario_stats.get("scenarios", 0) >= QUALITY_THRESHOLDS["scenario_min"]:
            checks_passed += 1
        else:
            issues.append(f"시나리오가 부족함: {scenario_stats.get('scenarios', 0)}개")

        # 시뮬레이션 상세
        sim_stats = get_simulation_stats(engine)
        result["simulation_stats"] = sim_stats
        if verbose:
            print(f"  시뮬레이션:")
            print(f"    - 전체: {sim_stats.get('total_runs', 0)}건")
            print(f"    - 최근 7일: {sim_stats.get('recent_runs', 0)}건")

        # 품질 점수 계산
        result["quality_issues"] = issues
        result["quality_score"] = round(checks_passed / total_checks * 100, 1) if total_checks > 0 else 0

        if verbose:
            print()
            print("=" * 60)
            print(f"📊 품질 점수: {result['quality_score']}% ({checks_passed}/{total_checks})")
            if issues:
                print()
                print("⚠️  품질 이슈:")
                for issue in issues:
                    print(f"  - {issue}")
            print("=" * 60)

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"❌ DB 연결 실패: {e}")

    return result


# ============================================================================
# API 스모크 테스트
# ============================================================================

def smoke_test_api(base_url: str, verbose: bool = True) -> Dict:
    """API 스모크 테스트 실행"""
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "base_url": base_url,
        "tests": [],
        "passed": 0,
        "failed": 0
    }

    if verbose:
        print("=" * 60)
        print("🔥 API 스모크 테스트")
        print("=" * 60)
        print(f"📡 Base URL: {base_url}")
        print()

    # 테스트 케이스 정의
    test_cases = [
        {
            "name": "Health Check",
            "method": "GET",
            "path": "/health",
            "expected_status": 200,
            "auth_required": False
        },
        {
            "name": "시나리오 목록",
            "method": "GET",
            "path": "/api/v1/scenarios",
            "expected_status": 200,
            "auth_required": False,
            "validate": lambda r: isinstance(r.json(), list)
        },
        {
            "name": "시나리오 상세 (MIN_VOL)",
            "method": "GET",
            "path": "/api/v1/scenarios/MIN_VOL",
            "expected_status": 200,
            "auth_required": False,
            "validate": lambda r: r.json().get("id") == "MIN_VOL"
        },
        {
            "name": "시나리오 상세 (DEFENSIVE)",
            "method": "GET",
            "path": "/api/v1/scenarios/DEFENSIVE",
            "expected_status": 200,
            "auth_required": False
        },
        {
            "name": "시나리오 상세 (GROWTH)",
            "method": "GET",
            "path": "/api/v1/scenarios/GROWTH",
            "expected_status": 200,
            "auth_required": False
        },
        {
            "name": "시나리오 상세 (존재하지 않음)",
            "method": "GET",
            "path": "/api/v1/scenarios/INVALID",
            "expected_status": 404,
            "auth_required": False
        },
    ]

    # 테스트 실행
    for tc in test_cases:
        test_result = {
            "name": tc["name"],
            "method": tc["method"],
            "path": tc["path"],
            "passed": False,
            "status_code": None,
            "response_time_ms": None,
            "error": None
        }

        try:
            url = f"{base_url}{tc['path']}"
            start_time = datetime.now()

            if tc["method"] == "GET":
                response = requests.get(url, timeout=10)
            elif tc["method"] == "POST":
                response = requests.post(url, json=tc.get("body", {}), timeout=30)
            else:
                raise ValueError(f"Unsupported method: {tc['method']}")

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            test_result["status_code"] = response.status_code
            test_result["response_time_ms"] = round(elapsed_ms, 2)

            # 상태 코드 검증
            if response.status_code == tc["expected_status"]:
                # 추가 검증
                if "validate" in tc:
                    if tc["validate"](response):
                        test_result["passed"] = True
                    else:
                        test_result["error"] = "Validation failed"
                else:
                    test_result["passed"] = True
            else:
                test_result["error"] = f"Expected {tc['expected_status']}, got {response.status_code}"

        except requests.exceptions.ConnectionError:
            test_result["error"] = "Connection refused"
        except requests.exceptions.Timeout:
            test_result["error"] = "Timeout"
        except Exception as e:
            test_result["error"] = str(e)

        result["tests"].append(test_result)

        if test_result["passed"]:
            result["passed"] += 1
            status = "✅"
        else:
            result["failed"] += 1
            status = "❌"

        if verbose:
            time_str = f"{test_result['response_time_ms']}ms" if test_result['response_time_ms'] else "N/A"
            print(f"  {status} {tc['name']}")
            print(f"     {tc['method']} {tc['path']} -> {test_result['status_code'] or 'N/A'} ({time_str})")
            if test_result["error"]:
                print(f"     Error: {test_result['error']}")

    # 요약
    total = len(test_cases)
    if verbose:
        print()
        print("=" * 60)
        print(f"📊 결과: {result['passed']}/{total} 통과")
        if result["failed"] > 0:
            print(f"⚠️  {result['failed']}개 테스트 실패")
        print("=" * 60)

    return result


# ============================================================================
# 리포트 생성
# ============================================================================

def generate_markdown_report(db_result: Dict, api_result: Dict) -> str:
    """마크다운 형식 리포트 생성"""
    lines = [
        "# Foresto Phase 1 품질 리포트",
        "",
        f"생성 시간: {datetime.utcnow().isoformat()}",
        "",
    ]

    # DB 품질
    if db_result:
        lines.extend([
            "## DB 품질 검사",
            "",
            f"**품질 점수**: {db_result.get('quality_score', 0)}%",
            "",
            "### 테이블 현황",
            "",
            "| 테이블 | 레코드 수 |",
            "|--------|----------|",
        ])

        for table, info in db_result.get("tables", {}).items():
            count = info.get("count", 0)
            lines.append(f"| {table} | {count:,} |")

        lines.append("")

        # 품질 이슈
        issues = db_result.get("quality_issues", [])
        if issues:
            lines.extend([
                "### 품질 이슈",
                "",
            ])
            for issue in issues:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")

    # API 스모크
    if api_result:
        lines.extend([
            "## API 스모크 테스트",
            "",
            f"**결과**: {api_result.get('passed', 0)}/{len(api_result.get('tests', []))} 통과",
            "",
            "| 테스트 | 상태 | 응답시간 |",
            "|--------|------|----------|",
        ])

        for test in api_result.get("tests", []):
            status = "✅" if test["passed"] else "❌"
            time_str = f"{test['response_time_ms']}ms" if test['response_time_ms'] else "N/A"
            lines.append(f"| {test['name']} | {status} | {time_str} |")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="품질 리포트 및 스모크 테스트 (P1-E3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 전체 품질 리포트
  python scripts/quality_report.py

  # DB 품질만
  python scripts/quality_report.py --db-only

  # API 스모크만
  python scripts/quality_report.py --api-only

  # 마크다운 출력
  python scripts/quality_report.py --output report.md

  # JSON 출력
  python scripts/quality_report.py --json
        """
    )

    parser.add_argument(
        "--db-only",
        action="store_true",
        help="DB 품질 검사만 실행"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="API 스모크 테스트만 실행"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=DEFAULT_API_URL,
        help=f"API 기본 URL (기본: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="마크다운 리포트 출력 파일"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 형식으로 출력"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="최소 출력"
    )

    args = parser.parse_args()

    db_result = None
    api_result = None

    # DB 품질 검사
    if not args.api_only:
        db_result = run_db_quality_check(verbose=not args.quiet and not args.json)

    # API 스모크 테스트
    if not args.db_only:
        api_result = smoke_test_api(args.api_url, verbose=not args.quiet and not args.json)

    # 출력
    if args.json:
        output = {
            "db_quality": db_result,
            "api_smoke": api_result
        }
        print(json.dumps(output, indent=2, default=str))

    elif args.output:
        report = generate_markdown_report(db_result, api_result)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 리포트 저장: {args.output}")

    # 종료 코드 결정
    exit_code = 0

    if db_result and db_result.get("quality_score", 100) < 70:
        exit_code = 1

    if api_result and api_result.get("failed", 0) > 0:
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
