#!/usr/bin/env python3
"""
P1-E1: 월단위 파티션 자동 생성 스크립트

파티셔닝된 테이블(일봉가격, 일간수익률, 시뮬레이션경로)에 대해
미래 6개월 파티션을 선생성하여 적재 실패를 방지합니다.

Usage:
    # 미래 6개월 파티션 생성 (기본값)
    python scripts/create_partitions.py

    # 특정 개월 수 지정
    python scripts/create_partitions.py --months 12

    # 드라이런 모드 (실제 생성 없이 확인만)
    python scripts/create_partitions.py --dry-run

    # 특정 테이블만 생성
    python scripts/create_partitions.py --table 일봉가격
    python scripts/create_partitions.py --table daily_price

운영 절차:
    1. 매월 1일 cron으로 실행 권장
    2. 실패 시 수동 재실행: python scripts/create_partitions.py
    3. 로그 확인: 생성된 파티션 목록 출력됨
"""

import argparse
import sys
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# 파티셔닝 대상 테이블
# ============================================================================

# 한글 테이블명 (foresto 스키마) - PostgreSQL DDL 기준
KOREAN_PARTITIONED_TABLES = [
    "foresto.일봉가격",
    "foresto.일간수익률",
    "foresto.시뮬레이션경로",
]

# 영문 테이블명 (public 스키마) - SQLAlchemy ORM 모델 기준
ENGLISH_PARTITIONED_TABLES = [
    "daily_price",
    "daily_return",
    "simulation_path",
]

# 테이블명 매핑 (영문 -> 한글)
TABLE_NAME_MAP = {
    "daily_price": "foresto.일봉가격",
    "daily_return": "foresto.일간수익률",
    "simulation_path": "foresto.시뮬레이션경로",
    "일봉가격": "foresto.일봉가격",
    "일간수익률": "foresto.일간수익률",
    "시뮬레이션경로": "foresto.시뮬레이션경로",
}


def get_database_url() -> str:
    """환경변수에서 DATABASE_URL 가져오기"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        print("   PostgreSQL 연결 문자열을 설정하세요:")
        print("   export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
        sys.exit(1)
    return db_url


def check_foresto_schema(engine) -> bool:
    """foresto 스키마 존재 여부 확인"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = 'foresto'
        """))
        return result.fetchone() is not None


def get_existing_partitions(engine, parent_table: str) -> list:
    """기존 파티션 목록 조회"""
    # 스키마와 테이블명 분리
    if "." in parent_table:
        schema, table = parent_table.split(".", 1)
    else:
        schema = "public"
        table = parent_table

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                child.relname AS partition_name,
                pg_get_expr(child.relpartbound, child.oid) AS partition_range
            FROM pg_inherits
            JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
            JOIN pg_class child ON pg_inherits.inhrelid = child.oid
            JOIN pg_namespace ns ON parent.relnamespace = ns.oid
            WHERE parent.relname = :table_name
              AND ns.nspname = :schema_name
            ORDER BY child.relname
        """), {"table_name": table, "schema_name": schema})
        return [(row[0], row[1]) for row in result.fetchall()]


def create_monthly_partition(
    engine,
    parent_table: str,
    start_date: date,
    dry_run: bool = False
) -> tuple:
    """
    월단위 파티션 생성

    Returns:
        (partition_name, created: bool, message: str)
    """
    # 스키마와 테이블명 분리
    if "." in parent_table:
        schema, table = parent_table.split(".", 1)
        full_table = parent_table
    else:
        schema = "public"
        table = parent_table
        full_table = f"{schema}.{table}"

    # 파티션명 생성 (예: foresto_일봉가격_p202601)
    partition_name = f"{schema}_{table}_p{start_date.strftime('%Y%m')}"

    # 날짜 범위
    end_date = start_date + relativedelta(months=1)

    # 파티션 존재 여부 확인
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = :part_name AND n.nspname = :schema
        """), {"part_name": partition_name.split(".")[-1] if "." in partition_name else partition_name,
               "schema": schema})

        if result.fetchone():
            return (partition_name, False, "이미 존재")

    if dry_run:
        return (partition_name, False, f"생성 예정 ({start_date} ~ {end_date})")

    # 파티션 생성
    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name}
        PARTITION OF {full_table}
        FOR VALUES FROM ('{start_date}') TO ('{end_date}')
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()
        return (partition_name, True, f"생성 완료 ({start_date} ~ {end_date})")
    except Exception as e:
        return (partition_name, False, f"생성 실패: {e}")


def create_partitions_for_table(
    engine,
    parent_table: str,
    months_ahead: int = 6,
    dry_run: bool = False
) -> dict:
    """
    테이블에 대해 미래 N개월 파티션 생성

    Returns:
        {
            "table": parent_table,
            "created": [...],
            "skipped": [...],
            "failed": [...]
        }
    """
    result = {
        "table": parent_table,
        "created": [],
        "skipped": [],
        "failed": []
    }

    # 이번 달부터 미래 N개월
    current_month = date.today().replace(day=1)

    for i in range(months_ahead + 1):  # 이번 달 포함
        target_month = current_month + relativedelta(months=i)
        partition_name, created, message = create_monthly_partition(
            engine, parent_table, target_month, dry_run
        )

        if created:
            result["created"].append((partition_name, message))
        elif "실패" in message:
            result["failed"].append((partition_name, message))
        else:
            result["skipped"].append((partition_name, message))

    return result


def run_partition_creation(
    months_ahead: int = 6,
    dry_run: bool = False,
    target_table: str = None,
    verbose: bool = True
) -> dict:
    """
    파티션 생성 메인 함수

    Args:
        months_ahead: 미래 생성할 개월 수 (기본 6)
        dry_run: True면 실제 생성 없이 확인만
        target_table: 특정 테이블만 처리 (None이면 전체)
        verbose: 상세 출력 여부

    Returns:
        전체 결과 딕셔너리
    """
    db_url = get_database_url()
    engine = create_engine(db_url)

    # foresto 스키마 확인
    has_foresto = check_foresto_schema(engine)

    if verbose:
        print("=" * 60)
        print("🔧 Foresto Phase 1 - 월단위 파티션 생성")
        print("=" * 60)
        print(f"📅 현재 날짜: {date.today()}")
        print(f"📊 생성 범위: 이번 달 ~ 미래 {months_ahead}개월")
        print(f"🔍 모드: {'드라이런 (확인만)' if dry_run else '실행'}")
        print(f"🗄️  foresto 스키마: {'존재' if has_foresto else '없음'}")
        print()

    # 대상 테이블 결정
    if target_table:
        # 특정 테이블 지정
        if target_table in TABLE_NAME_MAP:
            tables = [TABLE_NAME_MAP[target_table]]
        else:
            print(f"❌ 알 수 없는 테이블: {target_table}")
            print(f"   가능한 값: {list(TABLE_NAME_MAP.keys())}")
            sys.exit(1)
    else:
        # 전체 테이블
        if has_foresto:
            tables = KOREAN_PARTITIONED_TABLES
        else:
            print("⚠️  foresto 스키마가 없습니다.")
            print("   PostgreSQL DDL을 먼저 실행하세요:")
            print("   psql -f Foresto_Phase1_PostgreSQL_DDL_파티셔닝포함.sql")
            sys.exit(1)

    # 파티션 생성
    all_results = []

    for table in tables:
        if verbose:
            print(f"\n📋 테이블: {table}")
            print("-" * 40)

        result = create_partitions_for_table(
            engine, table, months_ahead, dry_run
        )
        all_results.append(result)

        if verbose:
            if result["created"]:
                print(f"  ✅ 생성: {len(result['created'])}개")
                for name, msg in result["created"]:
                    print(f"     - {name}: {msg}")

            if result["skipped"]:
                print(f"  ⏭️  건너뜀: {len(result['skipped'])}개")
                for name, msg in result["skipped"]:
                    print(f"     - {name}: {msg}")

            if result["failed"]:
                print(f"  ❌ 실패: {len(result['failed'])}개")
                for name, msg in result["failed"]:
                    print(f"     - {name}: {msg}")

    # 요약
    if verbose:
        print("\n" + "=" * 60)
        print("📊 요약")
        print("=" * 60)

        total_created = sum(len(r["created"]) for r in all_results)
        total_skipped = sum(len(r["skipped"]) for r in all_results)
        total_failed = sum(len(r["failed"]) for r in all_results)

        print(f"  총 생성: {total_created}개")
        print(f"  총 건너뜀: {total_skipped}개")
        print(f"  총 실패: {total_failed}개")

        if total_failed > 0:
            print("\n⚠️  일부 파티션 생성에 실패했습니다. 로그를 확인하세요.")
        elif dry_run:
            print("\n💡 --dry-run 플래그를 제거하고 다시 실행하면 실제로 생성됩니다.")
        else:
            print("\n✅ 파티션 생성 완료")

    return {
        "tables": all_results,
        "summary": {
            "total_created": sum(len(r["created"]) for r in all_results),
            "total_skipped": sum(len(r["skipped"]) for r in all_results),
            "total_failed": sum(len(r["failed"]) for r in all_results)
        }
    }


def list_existing_partitions(verbose: bool = True) -> dict:
    """기존 파티션 목록 출력"""
    db_url = get_database_url()
    engine = create_engine(db_url)

    has_foresto = check_foresto_schema(engine)

    if not has_foresto:
        print("❌ foresto 스키마가 없습니다.")
        return {}

    if verbose:
        print("=" * 60)
        print("📋 기존 파티션 목록")
        print("=" * 60)

    result = {}

    for table in KOREAN_PARTITIONED_TABLES:
        partitions = get_existing_partitions(engine, table)
        result[table] = partitions

        if verbose:
            print(f"\n📋 {table}: {len(partitions)}개")
            for name, range_expr in partitions:
                print(f"   - {name}: {range_expr}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="월단위 파티션 자동 생성 (P1-E1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 미래 6개월 파티션 생성
  python scripts/create_partitions.py

  # 12개월 파티션 생성
  python scripts/create_partitions.py --months 12

  # 드라이런 (확인만)
  python scripts/create_partitions.py --dry-run

  # 특정 테이블만 생성
  python scripts/create_partitions.py --table 일봉가격

  # 기존 파티션 목록 확인
  python scripts/create_partitions.py --list

운영 절차:
  1. 매월 1일 cron 등록: 0 0 1 * * python /path/to/create_partitions.py >> /var/log/partitions.log 2>&1
  2. 실패 시 수동 재실행 가능
  3. --list로 현재 상태 확인
        """
    )

    parser.add_argument(
        "--months", "-m",
        type=int,
        default=6,
        help="미래 생성할 개월 수 (기본: 6)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="실제 생성 없이 확인만"
    )
    parser.add_argument(
        "--table", "-t",
        type=str,
        help="특정 테이블만 처리 (예: 일봉가격, daily_price)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="기존 파티션 목록만 출력"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="최소 출력"
    )

    args = parser.parse_args()

    if args.list:
        list_existing_partitions(verbose=not args.quiet)
    else:
        result = run_partition_creation(
            months_ahead=args.months,
            dry_run=args.dry_run,
            target_table=args.table,
            verbose=not args.quiet
        )

        # 실패가 있으면 exit code 1
        if result["summary"]["total_failed"] > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
