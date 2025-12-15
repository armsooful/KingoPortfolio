from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_name: str = "KingoPortfolio"
    app_version: str = "0.1.0"
    debug: bool = True
    
    database_url: str = "sqlite:///./kingo.db"
    
    secret_key: str = "your-secret-key-change-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    allowed_origins: List[str] = [
        "*",  # ← 임시로 모든 origin 허용
    ]
    
    class Config:
        case_sensitive = False

settings = Settings()