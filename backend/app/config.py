import logging
import os
from typing import List
from dotenv import load_dotenv

# Settings가 import되는 시점에 반드시 .env가 로드되어야 함
# main.py 외 스크립트·테스트에서도 올바르게 동작
load_dotenv()


class Settings:
    """애플리케이션 설정 (환경변수 기반 CORS)"""
    
    # 앱 정보
    app_name: str = "Foresto Compass"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 데이터베이스 - __init__에서 설정
    database_url: str = ""
    
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

    # Alpha Vantage API
    alpha_vantage_api_key: str = os.getenv(
        "ALPHA_VANTAGE_API_KEY",
        ""
    )

    # User disclaimer (Phase 5)
    user_disclaimer: str = os.getenv(
        "USER_DISCLAIMER",
        "본 서비스는 교육 및 정보 제공 목적의 플랫폼입니다. 투자 권유·추천·자문·일임을 제공하지 않습니다. "
        "제공되는 내용은 과거 데이터 및 공개 정보를 기반으로 하며, 미래 수익을 보장하지 않습니다. "
        "모든 투자 결정은 사용자 본인의 판단과 책임 하에 이루어져야 합니다."
    )

    # Ops alerting (Phase 5)
    ops_alert_email_enabled: bool = os.getenv(
        "OPS_ALERT_EMAIL_ENABLED",
        "1"
    ) in ("1", "true", "True", "yes")
    ops_alert_slack_enabled: bool = os.getenv(
        "OPS_ALERT_SLACK_ENABLED",
        "0"
    ) in ("1", "true", "True", "yes")
    ops_alert_webhook_url: str = os.getenv(
        "OPS_ALERT_WEBHOOK_URL",
        ""
    )
    alert_email: str = os.getenv("ALERT_EMAIL", "")
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")

    # 데이터베이스 초기화 옵션
    reset_db_on_startup: bool = os.getenv(
        "RESET_DB_ON_STARTUP",
        "false"
    ).lower() in ("true", "1", "yes")

    # Feature Flags
    feature_recommendation_engine: bool = os.getenv(
        "FEATURE_RECOMMENDATION_ENGINE",
        "0"
    ) in ("1", "true", "True", "yes")

    # 시뮬레이션 엔진 버전 (결과 재현성 추적용)
    engine_version: str = os.getenv(
        "ENGINE_VERSION",
        "1.0.0"
    )

    # Phase 1: sim_* 구조 사용 여부 (PostgreSQL 환경에서 True)
    use_sim_store: bool = os.getenv(
        "USE_SIM_STORE",
        "0"
    ) in ("1", "true", "True")

    # Phase 1: 시나리오 DB 조회 사용 여부 (PostgreSQL 환경에서 True)
    use_scenario_db: bool = os.getenv(
        "USE_SCENARIO_DB",
        "0"
    ) in ("1", "true", "True")

    # Phase 2: 리밸런싱 엔진 사용 여부
    use_rebalancing: bool = os.getenv(
        "USE_REBALANCING",
        "0"
    ) in ("1", "true", "True")

    # Phase 2: 기본 비용률 (10bp = 0.001)
    default_cost_rate: float = float(os.getenv(
        "DEFAULT_COST_RATE",
        "0.001"
    ))

    # Phase 2: 결측 데이터 처리 정책 ('SKIP' 또는 'ZERO_RETURN')
    missing_data_policy: str = os.getenv(
        "MISSING_DATA_POLICY",
        "SKIP"
    )

    # 진행 로그 히스토리 최대 보관 개수
    progress_history_limit: int = int(os.getenv(
        "PROGRESS_HISTORY_LIMIT",
        "200"
    ))

    # CORS
    allowed_origins: List[str] = []
    
    def __init__(self):
        """환경변수 기반 설정"""
        # 데이터베이스 URL 설정 (인스턴스 생성 시점에 환경변수 읽기)
        raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./kingo.db")
        # Render uses postgres:// but SQLAlchemy requires postgresql://
        if raw_db_url.startswith("postgres://"):
            self.database_url = raw_db_url.replace("postgres://", "postgresql://", 1)
        else:
            self.database_url = raw_db_url

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
                "http://127.0.0.1:8000",
                # Vercel 배포 (모든 배포 URL 수용)
                "https://kingo-portfolio-*.vercel.app",
            ]
        
        _logger = logging.getLogger(__name__)
        _logger.info("CORS Allowed Origins: %s", self.allowed_origins)
        _logger.info("Database URL: %s...", self.database_url[:30])
        _logger.info("App: %s v%s (engine %s)", self.app_name, self.app_version, self.engine_version)
        _logger.info(
            "Feature Flags — Recommendation: %s, SimStore: %s, ScenarioDB: %s, Rebalancing: %s",
            self.feature_recommendation_engine, self.use_sim_store,
            self.use_scenario_db, self.use_rebalancing,
        )


# 싱글톤 인스턴스
settings = Settings()
