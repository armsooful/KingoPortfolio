"""
Phase 3-C / Epic C-1: 오류 코드 및 예외 처리 테스트
생성일: 2026-01-18
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.ops import ErrorCodeMaster
from app.services.error_code_service import ErrorCodeService, format_error_response
from app.services.ops_exceptions import (
    OpsException,
    InputDataMissingException,
    InputDataFormatException,
    ExternalApiTimeoutException,
    ExternalApiResponseException,
    BatchExecutionFailedException,
    BatchExecutionStoppedException,
    DuplicateDataException,
    ReferentialIntegrityException,
    CalculationLogicException,
    DatabaseConnectionException,
    ResourceExhaustedException,
)


@pytest.fixture
def db_session():
    """테스트용 인메모리 DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    ErrorCodeMaster.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 테스트용 오류 코드 생성
    error_codes = [
        ErrorCodeMaster(
            error_code='C1-INP-001', category='INP', severity='MEDIUM',
            user_message='데이터 처리 중 오류가 발생했습니다.',
            ops_message='입력 데이터 누락: 필수 필드가 NULL',
            action_guide='원천 데이터 확인 후 재처리 필요',
            auto_alert=True, alert_level='WARN'
        ),
        ErrorCodeMaster(
            error_code='C1-EXT-001', category='EXT', severity='HIGH',
            user_message='일시적인 오류가 발생했습니다.',
            ops_message='외부 API 연결 실패: 타임아웃',
            action_guide='API 상태 확인 후 재시도',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-SYS-001', category='SYS', severity='CRITICAL',
            user_message='시스템 점검 중입니다.',
            ops_message='DB 연결 실패',
            action_guide='DB 서버 상태 확인',
            auto_alert=True, alert_level='CRITICAL'
        ),
    ]

    for ec in error_codes:
        session.add(ec)
    session.commit()

    yield session

    session.close()


@pytest.fixture
def service(db_session):
    """ErrorCodeService 인스턴스"""
    return ErrorCodeService(db_session)


class TestOpsExceptions:
    """OpsException 테스트"""

    def test_base_exception(self):
        """기본 예외 생성"""
        exc = OpsException("Test error message")
        assert exc.message == "Test error message"
        assert exc.error_code == "C1-SYS-000"
        assert exc.category == "SYS"

    def test_exception_to_dict(self):
        """예외 딕셔너리 변환"""
        exc = OpsException(
            "Test error",
            error_code="C1-TEST-001",
            detail={"key": "value"}
        )
        result = exc.to_dict()

        assert result["error_code"] == "C1-TEST-001"
        assert result["message"] == "Test error"
        assert result["detail"]["key"] == "value"

    def test_input_data_missing_exception(self):
        """입력 데이터 누락 예외"""
        exc = InputDataMissingException("user_id")
        assert exc.error_code == "C1-INP-001"
        assert "user_id" in exc.message
        assert exc.detail["field"] == "user_id"

    def test_input_data_format_exception(self):
        """입력 데이터 포맷 예외"""
        exc = InputDataFormatException("birth_date", "YYYY-MM-DD", "2026/01/18")
        assert exc.error_code == "C1-INP-002"
        assert "birth_date" in exc.message
        assert exc.detail["expected"] == "YYYY-MM-DD"

    def test_external_api_timeout_exception(self):
        """외부 API 타임아웃 예외"""
        exc = ExternalApiTimeoutException("price_api", 30)
        assert exc.error_code == "C1-EXT-001"
        assert exc.detail["api"] == "price_api"
        assert exc.detail["timeout"] == 30

    def test_external_api_response_exception(self):
        """외부 API 응답 예외"""
        exc = ExternalApiResponseException("market_api", 503, "Service Unavailable")
        assert exc.error_code == "C1-EXT-002"
        assert exc.detail["status_code"] == 503

    def test_batch_execution_failed_exception(self):
        """배치 실행 실패 예외"""
        exc = BatchExecutionFailedException(
            "DAILY_PRICE_LOAD",
            "abc-123-def",
            "Database connection lost"
        )
        assert exc.error_code == "C1-BAT-001"
        assert "DAILY_PRICE_LOAD" in exc.message
        assert exc.detail["cause"] == "Database connection lost"

    def test_batch_execution_stopped_exception(self):
        """배치 실행 중단 예외"""
        exc = BatchExecutionStoppedException(
            "abc-123-def",
            "admin",
            "Emergency maintenance"
        )
        assert exc.error_code == "C1-BAT-002"
        assert exc.user_message == "처리가 중단되었습니다."

    def test_duplicate_data_exception(self):
        """중복 데이터 예외"""
        exc = DuplicateDataException(
            "portfolio",
            {"user_id": "123", "date": "2026-01-18"}
        )
        assert exc.error_code == "C1-DQ-001"
        assert exc.detail["table"] == "portfolio"

    def test_referential_integrity_exception(self):
        """참조 무결성 예외"""
        exc = ReferentialIntegrityException(
            "simulation",
            "portfolio",
            "port-123"
        )
        assert exc.error_code == "C1-DQ-002"
        assert "참조 무결성" in exc.message

    def test_calculation_logic_exception(self):
        """계산 로직 예외"""
        exc = CalculationLogicException(
            "expected_return",
            expected="0.05",
            actual="-999"
        )
        assert exc.error_code == "C1-LOG-001"
        assert exc.detail["calculation"] == "expected_return"

    def test_database_connection_exception(self):
        """DB 연결 예외"""
        exc = DatabaseConnectionException("primary", "Connection refused")
        assert exc.error_code == "C1-SYS-001"
        assert exc.user_message == "시스템 점검 중입니다."

    def test_resource_exhausted_exception(self):
        """리소스 부족 예외"""
        exc = ResourceExhaustedException("memory", 95.5, 90.0)
        assert exc.error_code == "C1-SYS-002"
        assert exc.detail["usage"] == 95.5


class TestErrorCodeService:
    """ErrorCodeService 테스트"""

    def test_get_error_code(self, service):
        """오류 코드 조회"""
        error = service.get_error_code("C1-INP-001")
        assert error is not None
        assert error.category == "INP"

    def test_get_error_code_not_found(self, service):
        """존재하지 않는 오류 코드"""
        error = service.get_error_code("C1-XXX-999")
        assert error is None

    def test_get_user_message(self, service):
        """사용자 메시지 조회"""
        msg = service.get_user_message("C1-INP-001")
        assert "데이터 처리" in msg

    def test_get_user_message_fallback(self, service):
        """없는 코드의 기본 메시지"""
        msg = service.get_user_message("C1-XXX-999")
        assert "시스템 오류" in msg

    def test_get_ops_message(self, service):
        """운영자 메시지 조회"""
        msg = service.get_ops_message("C1-INP-001")
        assert "입력 데이터 누락" in msg

    def test_get_action_guide(self, service):
        """조치 가이드 조회"""
        guide = service.get_action_guide("C1-INP-001")
        assert "원천 데이터" in guide

    def test_should_auto_alert(self, service):
        """자동 알림 여부"""
        assert service.should_auto_alert("C1-INP-001") is True
        assert service.should_auto_alert("C1-XXX-999") is False

    def test_get_alert_level(self, service):
        """알림 레벨 조회"""
        assert service.get_alert_level("C1-INP-001") == "WARN"
        assert service.get_alert_level("C1-EXT-001") == "ERROR"
        assert service.get_alert_level("C1-SYS-001") == "CRITICAL"

    def test_get_severity(self, service):
        """심각도 조회"""
        assert service.get_severity("C1-INP-001") == "MEDIUM"
        assert service.get_severity("C1-EXT-001") == "HIGH"
        assert service.get_severity("C1-SYS-001") == "CRITICAL"

    def test_get_category(self, service):
        """카테고리 조회"""
        assert service.get_category("C1-INP-001") == "INP"
        assert service.get_category("C1-EXT-001") == "EXT"
        # 없는 코드는 코드에서 추출
        assert service.get_category("C1-BAT-999") == "BAT"

    def test_get_full_info(self, service):
        """전체 정보 조회"""
        info = service.get_full_info("C1-EXT-001")
        assert info["error_code"] == "C1-EXT-001"
        assert info["category"] == "EXT"
        assert info["severity"] == "HIGH"
        assert info["auto_alert"] is True

    def test_get_full_info_unknown(self, service):
        """알 수 없는 코드 전체 정보"""
        info = service.get_full_info("C1-XXX-999")
        assert info["error_code"] == "C1-XXX-999"
        assert "Unknown" in info["ops_message"]

    def test_get_errors_by_category(self, service, db_session):
        """카테고리별 조회"""
        inp_errors = service.get_errors_by_category("INP")
        assert len(inp_errors) == 1
        assert inp_errors[0].error_code == "C1-INP-001"

    def test_get_errors_by_severity(self, service, db_session):
        """심각도별 조회"""
        critical_errors = service.get_errors_by_severity("CRITICAL")
        assert len(critical_errors) == 1
        assert critical_errors[0].error_code == "C1-SYS-001"

    def test_get_auto_alert_errors(self, service, db_session):
        """자동 알림 대상 조회"""
        auto_alerts = service.get_auto_alert_errors()
        assert len(auto_alerts) == 3  # 테스트 데이터 모두 auto_alert=True

    def test_cache(self, service):
        """캐시 동작"""
        # 첫 조회
        error1 = service.get_error_code("C1-INP-001")
        # 두 번째 조회 (캐시에서)
        error2 = service.get_error_code("C1-INP-001")
        assert error1 is error2  # 같은 객체

        # 캐시 초기화
        service.clear_cache()
        assert "C1-INP-001" not in service._cache


class TestFormatErrorResponse:
    """format_error_response 테스트"""

    def test_format_with_all_params(self):
        """전체 파라미터로 포맷"""
        response = format_error_response(
            error_code="C1-INP-001",
            ops_message="입력 데이터 누락",
            user_message="데이터 오류입니다.",
            detail={"field": "user_id"}
        )

        assert response["success"] is False
        assert response["error"]["code"] == "C1-INP-001"
        assert response["error"]["message"] == "데이터 오류입니다."
        assert response["error"]["ops_detail"] == "입력 데이터 누락"
        assert response["error"]["detail"]["field"] == "user_id"

    def test_format_without_user_message(self):
        """사용자 메시지 없이 포맷"""
        response = format_error_response(
            error_code="C1-SYS-001",
            ops_message="DB 연결 실패",
        )

        assert response["error"]["message"] == "시스템 오류가 발생했습니다."

    def test_format_without_detail(self):
        """상세 정보 없이 포맷"""
        response = format_error_response(
            error_code="C1-BAT-001",
            ops_message="배치 실패",
        )

        assert response["error"]["detail"] == {}
