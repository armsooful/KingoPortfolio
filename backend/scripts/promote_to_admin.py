"""
사용자를 관리자로 승격시키는 스크립트
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.user import User
from sqlalchemy import update


def promote_user_to_admin(email: str):
    """사용자를 관리자로 승격"""
    db = SessionLocal()
    try:
        # 사용자 찾기
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"❌ 사용자를 찾을 수 없습니다: {email}")
            return False

        # 이미 관리자인 경우
        if user.role == "admin":
            print(f"ℹ️  이미 관리자입니다: {email}")
            return True

        # 관리자로 승격
        user.role = "admin"
        db.commit()

        print(f"✅ 관리자로 승격되었습니다: {email}")
        print(f"   - 이전 역할: user")
        print(f"   - 새 역할: admin")
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
        return False
    finally:
        db.close()


def list_users():
    """모든 사용자 목록 표시"""
    db = SessionLocal()
    try:
        users = db.query(User).all()

        if not users:
            print("사용자가 없습니다.")
            return

        print("\n📋 등록된 사용자 목록:")
        print("-" * 70)
        print(f"{'이메일':<30} {'역할':<10} {'이름':<20}")
        print("-" * 70)

        for user in users:
            name = user.name or "(없음)"
            print(f"{user.email:<30} {user.role:<10} {name:<20}")

        print("-" * 70)
        print(f"총 {len(users)}명\n")

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 70)
    print("관리자 승격 스크립트")
    print("=" * 70)
    print()

    # 사용자 목록 표시
    list_users()

    # 이메일 입력 받기
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("관리자로 승격할 사용자 이메일을 입력하세요: ").strip()

    if not email:
        print("❌ 이메일이 입력되지 않았습니다.")
        sys.exit(1)

    # 승격 실행
    success = promote_user_to_admin(email)

    if success:
        print("\n✅ 완료! 이제 해당 사용자는 관리자 권한으로 재무 분석 기능에 접근할 수 있습니다.")

    sys.exit(0 if success else 1)
