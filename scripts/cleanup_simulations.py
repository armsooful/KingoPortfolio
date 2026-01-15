#!/usr/bin/env python3
"""
P1-E2: 시뮬레이션 결과 TTL/보관 정책 스크립트

저장 비용/개인정보 위험 최소화를 위해 만료된 시뮬레이션 결과를 정리합니다.

## TTL 정책

| 테이블           | 기본 보관 기간 | 설명                                |
|------------------|----------------|-------------------------------------|
| simulation_run   | 90일           | 요청 메타데이터                     |
| simulation_path  | 90일           | 일별 NAV 경로 (run과 함께 삭제)      |
| simulation_summary| 1년           | 요약 지표 (run과 함께 삭제)          |

## 삭제 기준
- simulation_run.expires_at < 현재시간 인 레코드 삭제
- CASCADE로 path, summary 자동 삭제

Usage:
    # 드라이런 (삭제 대상 확인만)
    python scripts/cleanup_simulations.py --dry-run

    # 실제 삭제 실행
    python scripts/cleanup_simulations.py

    # 배치 크기 지정 (대량 데이터)
    python scripts/cleanup_simulations.py --batch-size 500

    # 특정 날짜 기준 삭제 (테스트용)
    python scripts/cleanup_simulations.py --before 2025-01-01

    # 아카이브 후 삭제
    python scripts/cleanup_simulations.py --archive /path/to/archive

운영 절차:
    1. 매일 새벽 cron으로 드라이런 실행 (알림용)
    2. 주 1회 실제 삭제 실행
    3. 삭제 전 --archive 옵션으로 백업 권장
"""

import argparse
import sys
import os
import json
import gzip
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker


# ============================================================================
# TTL 정책 정의
# ============================================================================

DEFAULT_TTL_POLICY = {
    "simulation_run": 90,      # 90일 (기본값, expires_at 컬럼 사용)
    "simulation_path": 90,     # run과 함께 CASCADE 삭제
    "simulation_summary": 365, # 1년 (참고용, 실제로는 run과 함께 삭제)
}


def get_database_url() -> str:
    """환경변수에서 DATABASE_URL 가져오기"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    return db_url


def get_expired_runs_count(engine, before_date: datetime = None) -> int:
    """만료된 시뮬레이션 run 수 조회"""
    if before_date is None:
        before_date = datetime.utcnow()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM simulation_run
            WHERE expires_at IS NOT NULL AND expires_at < :before_date
        """), {"before_date": before_date})
        return result.scalar() or 0


def get_expired_runs(
    engine,
    before_date: datetime = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """만료된 시뮬레이션 run 목록 조회"""
    if before_date is None:
        before_date = datetime.utcnow()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                run_id,
                request_hash,
                scenario_id,
                start_date,
                end_date,
                created_at,
                expires_at,
                (SELECT COUNT(*) FROM simulation_path WHERE run_id = simulation_run.run_id) as path_count
            FROM simulation_run
            WHERE expires_at IS NOT NULL AND expires_at < :before_date
            ORDER BY expires_at ASC
            LIMIT :limit OFFSET :offset
        """), {"before_date": before_date, "limit": limit, "offset": offset})

        return [
            {
                "run_id": row[0],
                "request_hash": row[1],
                "scenario_id": row[2],
                "start_date": row[3].isoformat() if row[3] else None,
                "end_date": row[4].isoformat() if row[4] else None,
                "created_at": row[5].isoformat() if row[5] else None,
                "expires_at": row[6].isoformat() if row[6] else None,
                "path_count": row[7]
            }
            for row in result.fetchall()
        ]


def archive_simulation_run(engine, run_id: int) -> Dict:
    """
    시뮬레이션 run을 JSON으로 아카이브

    Returns:
        아카이브된 데이터 dict
    """
    with engine.connect() as conn:
        # run 조회
        run_result = conn.execute(text("""
            SELECT * FROM simulation_run WHERE run_id = :run_id
        """), {"run_id": run_id})
        run_row = run_result.fetchone()
        if not run_row:
            return None

        run_keys = run_result.keys()
        run_data = dict(zip(run_keys, run_row))

        # summary 조회
        summary_result = conn.execute(text("""
            SELECT * FROM simulation_summary WHERE run_id = :run_id
        """), {"run_id": run_id})
        summary_row = summary_result.fetchone()
        summary_data = None
        if summary_row:
            summary_keys = summary_result.keys()
            summary_data = dict(zip(summary_keys, summary_row))

        # path 조회
        path_result = conn.execute(text("""
            SELECT * FROM simulation_path WHERE run_id = :run_id ORDER BY path_date
        """), {"run_id": run_id})
        path_rows = path_result.fetchall()
        path_keys = path_result.keys()
        path_data = [dict(zip(path_keys, row)) for row in path_rows]

    # datetime/date/Decimal을 문자열로 변환
    def serialize(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__float__'):
            return float(obj)
        return obj

    def serialize_dict(d):
        if d is None:
            return None
        return {k: serialize(v) for k, v in d.items()}

    return {
        "run": serialize_dict(run_data),
        "summary": serialize_dict(summary_data),
        "paths": [serialize_dict(p) for p in path_data],
        "archived_at": datetime.utcnow().isoformat()
    }


def delete_simulation_run(engine, run_id: int) -> bool:
    """
    시뮬레이션 run 삭제 (CASCADE로 path, summary 함께 삭제)
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            DELETE FROM simulation_run WHERE run_id = :run_id
        """), {"run_id": run_id})
        conn.commit()
        return result.rowcount > 0


def run_cleanup(
    before_date: datetime = None,
    batch_size: int = 100,
    dry_run: bool = False,
    archive_path: str = None,
    verbose: bool = True
) -> Dict:
    """
    만료된 시뮬레이션 결과 정리

    Args:
        before_date: 이 날짜 이전 expires_at인 레코드 삭제 (기본: 현재시간)
        batch_size: 배치 당 처리 건수
        dry_run: True면 실제 삭제 없이 확인만
        archive_path: 아카이브 디렉토리 경로 (지정 시 삭제 전 백업)
        verbose: 상세 출력

    Returns:
        결과 통계
    """
    db_url = get_database_url()
    engine = create_engine(db_url)

    if before_date is None:
        before_date = datetime.utcnow()

    if verbose:
        print("=" * 60)
        print("🧹 Foresto Phase 1 - 시뮬레이션 결과 정리")
        print("=" * 60)
        print(f"📅 기준 시간: {before_date.isoformat()}")
        print(f"📦 배치 크기: {batch_size}")
        print(f"🔍 모드: {'드라이런 (확인만)' if dry_run else '실행'}")
        if archive_path:
            print(f"📁 아카이브: {archive_path}")
        print()

    # 만료 대상 수 조회
    total_expired = get_expired_runs_count(engine, before_date)

    if verbose:
        print(f"📊 만료된 시뮬레이션: {total_expired}건")
        print()

    if total_expired == 0:
        if verbose:
            print("✅ 삭제할 레코드가 없습니다.")
        return {
            "total_expired": 0,
            "deleted": 0,
            "archived": 0,
            "failed": 0
        }

    # 아카이브 디렉토리 생성
    if archive_path and not dry_run:
        os.makedirs(archive_path, exist_ok=True)

    # 배치 처리
    deleted_count = 0
    archived_count = 0
    failed_count = 0
    offset = 0

    while True:
        # 배치 조회 (삭제 후 offset 유지 - 순차 삭제이므로)
        batch = get_expired_runs(engine, before_date, batch_size, 0 if not dry_run else offset)

        if not batch:
            break

        if verbose and not dry_run:
            print(f"📋 배치 처리: {len(batch)}건")

        for run_info in batch:
            run_id = run_info["run_id"]

            if verbose:
                scenario = run_info.get("scenario_id") or "custom"
                path_count = run_info.get("path_count", 0)
                expires = run_info.get("expires_at", "N/A")
                print(f"  - run_id={run_id} scenario={scenario} "
                      f"paths={path_count} expires={expires}")

            if dry_run:
                offset += 1
                continue

            try:
                # 아카이브
                if archive_path:
                    archive_data = archive_simulation_run(engine, run_id)
                    if archive_data:
                        archive_file = os.path.join(
                            archive_path,
                            f"sim_run_{run_id}_{datetime.utcnow().strftime('%Y%m%d')}.json.gz"
                        )
                        with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                            json.dump(archive_data, f, ensure_ascii=False, indent=2)
                        archived_count += 1

                # 삭제
                if delete_simulation_run(engine, run_id):
                    deleted_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                print(f"  ❌ run_id={run_id} 처리 실패: {e}")
                failed_count += 1

        if dry_run:
            # 드라이런에서는 offset으로 다음 페이지
            if len(batch) < batch_size:
                break
        else:
            # 실제 삭제에서는 첫 번째 배치 반복
            if deleted_count + failed_count >= total_expired:
                break

    # 결과 요약
    result = {
        "total_expired": total_expired,
        "deleted": deleted_count,
        "archived": archived_count,
        "failed": failed_count,
        "before_date": before_date.isoformat()
    }

    if verbose:
        print()
        print("=" * 60)
        print("📊 결과 요약")
        print("=" * 60)
        print(f"  총 만료: {total_expired}건")
        print(f"  삭제됨: {deleted_count}건")
        if archive_path:
            print(f"  아카이브됨: {archived_count}건")
        print(f"  실패: {failed_count}건")

        if dry_run:
            print()
            print("💡 --dry-run 플래그를 제거하고 다시 실행하면 실제로 삭제됩니다.")
        else:
            print()
            print("✅ 정리 완료")

    return result


def show_retention_stats(verbose: bool = True) -> Dict:
    """현재 시뮬레이션 데이터 보관 현황 출력"""
    db_url = get_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 전체 통계
        total_runs = conn.execute(text("SELECT COUNT(*) FROM simulation_run")).scalar() or 0
        total_paths = conn.execute(text("SELECT COUNT(*) FROM simulation_path")).scalar() or 0
        total_summaries = conn.execute(text("SELECT COUNT(*) FROM simulation_summary")).scalar() or 0

        # 만료 예정
        now = datetime.utcnow()
        expired = conn.execute(text("""
            SELECT COUNT(*) FROM simulation_run
            WHERE expires_at IS NOT NULL AND expires_at < :now
        """), {"now": now}).scalar() or 0

        # 7일 내 만료 예정
        week_later = now + timedelta(days=7)
        expiring_soon = conn.execute(text("""
            SELECT COUNT(*) FROM simulation_run
            WHERE expires_at IS NOT NULL AND expires_at >= :now AND expires_at < :week
        """), {"now": now, "week": week_later}).scalar() or 0

        # 시나리오별 분포
        scenario_dist = conn.execute(text("""
            SELECT
                COALESCE(scenario_id, 'custom') as scenario,
                COUNT(*) as count
            FROM simulation_run
            GROUP BY scenario_id
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()

    stats = {
        "total_runs": total_runs,
        "total_paths": total_paths,
        "total_summaries": total_summaries,
        "expired": expired,
        "expiring_in_7_days": expiring_soon,
        "by_scenario": [(row[0], row[1]) for row in scenario_dist]
    }

    if verbose:
        print("=" * 60)
        print("📊 시뮬레이션 데이터 보관 현황")
        print("=" * 60)
        print(f"  simulation_run: {total_runs}건")
        print(f"  simulation_path: {total_paths}건")
        print(f"  simulation_summary: {total_summaries}건")
        print()
        print(f"  ⏰ 만료됨 (삭제 대상): {expired}건")
        print(f"  ⚠️  7일 내 만료 예정: {expiring_soon}건")
        print()
        print("  시나리오별 분포:")
        for scenario, count in stats["by_scenario"]:
            print(f"    - {scenario}: {count}건")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="시뮬레이션 결과 TTL/보관 정책 관리 (P1-E2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
TTL 정책:
  - simulation_run: 90일 (expires_at 컬럼 기준)
  - simulation_path: run과 함께 CASCADE 삭제
  - simulation_summary: run과 함께 CASCADE 삭제

예시:
  # 삭제 대상 확인 (드라이런)
  python scripts/cleanup_simulations.py --dry-run

  # 실제 삭제 실행
  python scripts/cleanup_simulations.py

  # 아카이브 후 삭제
  python scripts/cleanup_simulations.py --archive ./archive

  # 현재 보관 현황 확인
  python scripts/cleanup_simulations.py --stats

운영 절차:
  1. 매일: python scripts/cleanup_simulations.py --stats
  2. 주 1회: python scripts/cleanup_simulations.py --archive ./backup
        """
    )

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="실제 삭제 없이 대상 확인만"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=100,
        help="배치 당 처리 건수 (기본: 100)"
    )
    parser.add_argument(
        "--before",
        type=str,
        help="이 날짜 이전 만료된 레코드 삭제 (YYYY-MM-DD, 기본: 현재시간)"
    )
    parser.add_argument(
        "--archive", "-a",
        type=str,
        help="삭제 전 아카이브할 디렉토리 경로"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="보관 현황만 출력"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="최소 출력"
    )

    args = parser.parse_args()

    if args.stats:
        show_retention_stats(verbose=not args.quiet)
        return

    # 날짜 파싱
    before_date = None
    if args.before:
        try:
            before_date = datetime.strptime(args.before, "%Y-%m-%d")
        except ValueError:
            print(f"❌ 날짜 형식이 올바르지 않습니다: {args.before}")
            print("   YYYY-MM-DD 형식을 사용하세요.")
            sys.exit(1)

    result = run_cleanup(
        before_date=before_date,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        archive_path=args.archive,
        verbose=not args.quiet
    )

    # 실패가 있으면 exit code 1
    if result.get("failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
