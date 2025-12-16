import os
import json
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "KingoPortfolio"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./kingo.db"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: List[str] = [
        "https://kingo-portfolio-d0je2u1t8-changrims-projects.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    class Config:
        case_sensitive = False
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 환경변수에서 ALLOWED_ORIGINS 읽기 (쉼표 구분 문자열)
        env_origins = os.getenv("ALLOWED_ORIGINS", "")
        if env_origins:
            self.allowed_origins = [
                o.strip() for o in env_origins.split(",") if o.strip()
            ]
        
        print(f"✅ Allowed Origins: {self.allowed_origins}")


settings = Settings()