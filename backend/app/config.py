import os
from typing import List

class Settings:
    """애플리케이션 설정 (환경변수 기반 CORS)"""
    
    # 앱 정보
    app_name: str = "KingoPortfolio"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 데이터베이스
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./kingo.db"
    )
    
    # 보안
    secret_key: str = os.getenv(
        "SECRET_KEY",
        "your-secret-key-change-in-production-min-32-chars"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Claude AI
    anthropic_api_key: str = os.getenv(
        "ANTHROPIC_API_KEY",
        ""
    )
    
    # CORS
    allowed_origins: List[str] = []
    
    def __init__(self):
        """환경변수 기반 CORS 설정"""
        # 환경변수에서 origin 읽기
        env_origins = os.getenv("ALLOWED_ORIGINS", "")
        
        if env_origins:
            # 환경변수가 설정되면 사용
            self.allowed_origins = [
                o.strip() for o in env_origins.split(",") if o.strip()
            ]
        else:
            # 기본값: 개발 + 프로덕션
            self.allowed_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                # Vercel 배포 (모든 배포 URL 수용)
                "https://kingo-portfolio-*.vercel.app",
            ]
        
        print(f"✅ CORS Allowed Origins: {self.allowed_origins}")
        print(f"✅ Database URL: {self.database_url[:30]}...")
        print(f"✅ App Name: {self.app_name}")
        print(f"✅ App Version: {self.app_version}")


# 싱글톤 인스턴스
settings = Settings()