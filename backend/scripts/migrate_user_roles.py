#!/usr/bin/env python3
"""
User 테이블에 role 컬럼을 추가하는 마이그레이션 스크립트

기존 사용자:
- is_admin = True → role = 'admin'
- is_admin = False → role = 'user'
"""

from sqlalchemy import text
from app.database import SessionLocal, engine

def migrate_user_roles():
    """User 테이블에 role 컬럼 추가 및 데이터 마이그레이션"""

    db = SessionLocal()

    try:
        print("🔄 Starting user role migration...")

        # 1. role 컬럼 추가 (이미 있으면 무시)
        try:
            db.execute(text("""
                ALTER TABLE users
                ADD COLUMN role VARCHAR(20) DEFAULT 'user'
            """))
            db.commit()
            print("✅ Added 'role' column to users table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  'role' column already exists, skipping...")
                db.rollback()
            else:
                raise

        # 2. is_admin = True인 사용자들을 role = 'admin'으로 업데이트
        result = db.execute(text("""
            UPDATE users
            SET role = 'admin'
            WHERE is_admin = 1 AND role != 'admin'
        """))
        db.commit()
        print(f"✅ Updated {result.rowcount} admin users")

        # 3. is_admin = False인 사용자들을 role = 'user'로 업데이트
        result = db.execute(text("""
            UPDATE users
            SET role = 'user'
            WHERE (is_admin = 0 OR is_admin IS NULL) AND role != 'user'
        """))
        db.commit()
        print(f"✅ Updated {result.rowcount} regular users")

        # 4. 결과 확인
        result = db.execute(text("""
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
        """))

        print("\n📊 User role distribution:")
        for row in result:
            print(f"   {row[0]}: {row[1]} users")

        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_user_roles()
