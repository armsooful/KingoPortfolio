import os
from typing import List

class Settings:
    """애플리케이션 설정 (환경변수 자동 감지 제거)"""
    
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
    
    # CORS - 환경변수에서 쉼표 구분 문자열로 처리
    allowed_origins: List[str] = [
        "https://kingo-portfolio-5oy16z2so-changrims-projects.vercel.app",  # ← 새 URL 추가
        "https://kingo-portfolio-d0je2u1t8-changrims-projects.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    def __init__(self):
        """환경변수 로드"""
        # ALLOWED_ORIGINS 환경변수 처리
        env_origins = os.getenv("ALLOWED_ORIGINS", "")
        if env_origins:
            self.allowed_origins = [
                o.strip() for o in env_origins.split(",") if o.strip()
            ]
        
        print(f"✅ CORS Allowed Origins: {self.allowed_origins}")
        print(f"✅ Database URL: {self.database_url[:30]}...")
        print(f"✅ App Name: {self.app_name}")
        print(f"✅ App Version: {self.app_version}")


# 싱글톤 인스턴스
settings = Settings()