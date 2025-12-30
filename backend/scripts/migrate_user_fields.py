"""
사용자 테이블에 상세 프로필 필드 추가 마이그레이션
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine
from sqlalchemy import text, inspect

def check_column_exists(table_name: str, column_name: str) -> bool:
    """컬럼이 이미 존재하는지 확인"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    """마이그레이션 실행"""
    print("=" * 70)
    print("사용자 프로필 필드 마이그레이션")
    print("=" * 70)
    print()

    # 추가할 컬럼 정의
    new_columns = [
        # 기본 정보
        ("phone", "VARCHAR(20)"),
        ("birth_date", "DATE"),

        # 직업 및 재무 정보
        ("occupation", "VARCHAR(100)"),
        ("company", "VARCHAR(100)"),
        ("annual_income", "INTEGER"),
        ("total_assets", "INTEGER"),

        # 주소 정보
        ("city", "VARCHAR(50)"),
        ("district", "VARCHAR(50)"),

        # 투자 성향 정보
        ("investment_experience", "VARCHAR(20)"),
        ("investment_goal", "VARCHAR(100)"),
        ("risk_tolerance", "VARCHAR(20)"),
    ]

    db = SessionLocal()
    try:
        added_count = 0
        skipped_count = 0

        for column_name, column_type in new_columns:
            if check_column_exists('users', column_name):
                print(f"⏭️  {column_name}: 이미 존재함 (스킵)")
                skipped_count += 1
                continue

            try:
                # SQLite는 ALTER TABLE ADD COLUMN을 지원
                sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                db.execute(text(sql))
                db.commit()
                print(f"✅ {column_name}: 추가 완료 ({column_type})")
                added_count += 1
            except Exception as e:
                db.rollback()
                print(f"❌ {column_name}: 추가 실패 - {str(e)}")

        print()
        print("-" * 70)
        print(f"마이그레이션 완료: {added_count}개 추가, {skipped_count}개 스킵")
        print("-" * 70)

        # 최종 컬럼 목록 확인
        print()
        print("📋 현재 users 테이블 컬럼:")
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")

    except Exception as e:
        db.rollback()
        print(f"❌ 마이그레이션 실패: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
