#!/usr/bin/env python3
"""
User 테이블에 복합 등급 체계 필드 추가 마이그레이션

복합 등급 체계:
1. VIP 등급 (활동 기반): bronze, silver, gold, platinum, diamond
2. 멤버십 플랜 (유료 구독): free, starter, pro, enterprise

실행 방법:
    python backend/scripts/migrate_add_tier_system.py
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal


def migrate():
    """복합 등급 체계 필드 추가"""
    print("=" * 70)
    print("🔧 User 테이블에 복합 등급 체계 필드 추가 중...")
    print("=" * 70)

    db = SessionLocal()

    try:
        # SQLite에서 컬럼 존재 여부 확인
        result = db.execute(text("PRAGMA table_info(users)")).fetchall()
        existing_columns = [row[1] for row in result]

        print(f"\n현재 users 테이블의 컬럼: {len(existing_columns)}개\n")

        # 추가할 컬럼 정의
        columns_to_add = [
            # VIP 등급 시스템
            ("vip_tier", "VARCHAR(20) DEFAULT 'bronze'"),
            ("activity_points", "INTEGER DEFAULT 0"),

            # 멤버십 플랜
            ("membership_plan", "VARCHAR(20) DEFAULT 'free'"),
            ("membership_start_date", "DATETIME"),
            ("membership_end_date", "DATETIME"),

            # 사용량 추적
            ("monthly_ai_requests", "INTEGER DEFAULT 0"),
            ("monthly_reports_generated", "INTEGER DEFAULT 0"),
            ("last_usage_reset", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ]

        added_count = 0

        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                try:
                    # SQLite에서 컬럼 추가
                    sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                    db.execute(text(sql))
                    db.commit()
                    print(f"✅ 컬럼 추가 완료: {column_name} ({column_type})")
                    added_count += 1
                except Exception as e:
                    print(f"❌ 컬럼 추가 실패: {column_name} - {str(e)}")
                    db.rollback()
            else:
                print(f"ℹ️  컬럼이 이미 존재합니다: {column_name}")

        print(f"\n{'=' * 70}")
        print(f"✅ 마이그레이션 완료! ({added_count}개 컬럼 추가됨)")
        print(f"{'=' * 70}\n")

        # 마이그레이션 후 테이블 구조 확인
        result = db.execute(text("PRAGMA table_info(users)")).fetchall()
        print("\n업데이트된 users 테이블 구조:")
        print("-" * 70)
        for row in result:
            print(f"  {row[1]:30s} {row[2]:20s} NULL={row[3] == 0}")
        print("-" * 70)

        # 기존 사용자 데이터 초기화
        print("\n🔄 기존 사용자 데이터 초기화 중...")

        # 기존 사용자들에게 Bronze VIP 등급 부여
        db.execute(text("""
            UPDATE users
            SET vip_tier = 'bronze',
                membership_plan = 'free',
                activity_points = 0,
                monthly_ai_requests = 0,
                monthly_reports_generated = 0
            WHERE vip_tier IS NULL OR vip_tier = ''
        """))

        # role='admin'인 사용자는 Platinum VIP로 설정
        db.execute(text("""
            UPDATE users
            SET vip_tier = 'platinum',
                activity_points = 1000
            WHERE role = 'admin'
        """))

        # role='premium'인 사용자는 Pro 멤버십으로 설정
        db.execute(text("""
            UPDATE users
            SET membership_plan = 'pro',
                vip_tier = 'gold',
                activity_points = 500
            WHERE role = 'premium'
        """))

        db.commit()
        print("✅ 기존 사용자 데이터 초기화 완료")

        # 초기화 결과 확인
        result = db.execute(text("""
            SELECT
                vip_tier,
                membership_plan,
                COUNT(*) as count
            FROM users
            GROUP BY vip_tier, membership_plan
        """)).fetchall()

        print("\n📊 사용자 등급 분포:")
        print("-" * 70)
        for row in result:
            print(f"  VIP: {row[0]:10s} | Membership: {row[1]:10s} | Count: {row[2]}")
        print("-" * 70)

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()

    return True


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
