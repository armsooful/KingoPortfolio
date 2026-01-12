#!/usr/bin/env python3
"""
이메일 인증 자동 활성화 마이그레이션

모든 기존 사용자의 is_email_verified를 True로 설정합니다.
교육용 플랫폼이므로 이메일 인증 절차를 생략합니다.

실행 방법:
    python backend/scripts/migrate_auto_verify_emails.py

주의:
    - 이 스크립트는 프로덕션 데이터베이스에서도 안전하게 실행할 수 있습니다
    - 모든 사용자의 이메일 인증 상태를 True로 변경합니다
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
backend_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

def migrate_auto_verify_emails():
    """모든 사용자의 이메일 인증을 활성화"""

    print("\n" + "="*60)
    print("📧 이메일 인증 자동 활성화 마이그레이션")
    print("="*60 + "\n")

    # 데이터베이스 연결
    print(f"📂 데이터베이스: {settings.database_url}")
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 현재 인증되지 않은 사용자 수 확인
        result = session.execute(
            text("SELECT COUNT(*) FROM users WHERE is_email_verified = 0 OR is_email_verified IS NULL")
        )
        unverified_count = result.scalar()

        print(f"📊 인증되지 않은 사용자: {unverified_count}명")

        if unverified_count == 0:
            print("✅ 모든 사용자가 이미 인증되었습니다.")
            return

        # 모든 사용자의 이메일 인증 활성화
        print(f"\n🔄 {unverified_count}명의 사용자 이메일 인증 활성화 중...")

        result = session.execute(
            text("UPDATE users SET is_email_verified = 1 WHERE is_email_verified = 0 OR is_email_verified IS NULL")
        )
        session.commit()

        print(f"✅ {result.rowcount}명의 사용자 이메일 인증이 활성화되었습니다.")

        # 검증
        result = session.execute(
            text("SELECT COUNT(*) FROM users WHERE is_email_verified = 1")
        )
        verified_count = result.scalar()

        result = session.execute(
            text("SELECT COUNT(*) FROM users")
        )
        total_count = result.scalar()

        print(f"\n📊 최종 상태:")
        print(f"   - 전체 사용자: {total_count}명")
        print(f"   - 인증된 사용자: {verified_count}명")
        print(f"   - 인증되지 않은 사용자: {total_count - verified_count}명")

        print("\n" + "="*60)
        print("✅ 마이그레이션 완료")
        print("="*60 + "\n")

    except Exception as e:
        session.rollback()
        print(f"\n❌ 마이그레이션 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    migrate_auto_verify_emails()
