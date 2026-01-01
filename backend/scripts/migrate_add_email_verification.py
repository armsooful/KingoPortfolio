#!/usr/bin/env python3
"""
User 테이블에 이메일 인증 필드 추가 마이그레이션

실행 방법:
    python backend/scripts/migrate_add_email_verification.py
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal


def migrate():
    """이메일 인증 필드 추가"""
    print("=" * 70)
    print("🔧 User 테이블에 이메일 인증 필드 추가 중...")
    print("=" * 70)

    db = SessionLocal()

    try:
        # SQLite에서 컬럼 존재 여부 확인
        result = db.execute(text("PRAGMA table_info(users)")).fetchall()
        existing_columns = [row[1] for row in result]

        print(f"\n현재 users 테이블의 컬럼: {existing_columns}\n")

        # 추가할 컬럼 정의
        columns_to_add = [
            ("is_email_verified", "BOOLEAN DEFAULT 0"),
            ("email_verification_token", "VARCHAR(100)"),
            ("email_verification_sent_at", "DATETIME"),
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
