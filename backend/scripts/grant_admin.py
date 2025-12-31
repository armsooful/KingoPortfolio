#!/usr/bin/env python3
"""
특정 사용자에게 관리자 권한 부여 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.auth import hash_password


def grant_admin_role(email: str, create_if_not_exists: bool = False, password: str = None):
    """특정 이메일의 사용자에게 관리자 권한 부여"""
    db = SessionLocal()

    try:
        # 사용자 조회
        user = db.query(User).filter(User.email == email).first()

        if not user:
            if create_if_not_exists and password:
                # 사용자 생성
                print(f"ℹ️  사용자가 존재하지 않습니다. 새로 생성합니다...")
                hashed_password = hash_password(password)
                user = User(
                    email=email,
                    hashed_password=hashed_password,
                    name="관리자",
                    role='admin',
                    is_admin=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                print(f"✅ 관리자 계정 생성 완료!")
                print(f"   이메일: {email}")
                print(f"   비밀번호: {password}")
                print(f"   역할: {user.role}")
                return True
            else:
                print(f"❌ 사용자를 찾을 수 없습니다: {email}")
                return False

        # 이미 관리자인지 확인
        if user.role == 'admin':
            print(f"ℹ️  {email}는 이미 관리자입니다.")
            print(f"   현재 역할: {user.role}")
            print(f"   is_admin: {user.is_admin}")
            return True

        # 관리자 권한 부여
        old_role = user.role
        user.role = 'admin'
        user.is_admin = True  # 하위 호환성

        db.commit()
        db.refresh(user)

        print(f"✅ 관리자 권한 부여 완료!")
        print(f"   이메일: {email}")
        print(f"   이름: {user.name}")
        print(f"   이전 역할: {old_role}")
        print(f"   새 역할: {user.role}")
        print(f"   is_admin: {user.is_admin}")

        return True

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    # test@test.com에 관리자 권한 부여
    email = "test@test.com"

    print(f"🔧 {email}에 관리자 권한 부여 중...")
    print("-" * 50)

    # 기존 계정에만 권한 부여 (create_if_not_exists=False)
    success = grant_admin_role(email, create_if_not_exists=False)

    if success:
        print("\n✨ 작업 완료!")
        print("\n로그인 정보:")
        print(f"  이메일: {email}")
        print(f"  역할: admin")
    else:
        print("\n❌ 작업 실패")
        sys.exit(1)
