"""
Phase 3-C / Epic C-1: 운영 예외 처리 체계
생성일: 2026-01-18
목적: 표준화된 오류 코드 체계와 예외 처리 클래스
"""

from typing import Optional, Dict, Any


class OpsException(Exception):
    """운영 예외 기본 클래스"""

    error_code: str = "C1-SYS-000"
    category: str = "SYS"
    user_message: str = "시스템 오류가 발생했습니다."

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        user_message: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        if error_code:
            self.error_code = error_code
        if user_message:
            self.user_message = user_message
        self.detail = detail or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "category": self.category,
            "message": self.message,
            "user_message": self.user_message,
            "detail": self.detail,
        }


# =============================================================================
# 입력 데이터 오류 (INP)
# =============================================================================

class InputDataException(OpsException):
    """입력 데이터 오류"""
    error_code = "C1-INP-001"
    category = "INP"
    user_message = "데이터 처리 중 오류가 발생했습니다."


class InputDataMissingException(InputDataException):
    """입력 데이터 누락"""
    error_code = "C1-INP-001"

    def __init__(self, field_name: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"입력 데이터 누락: 필수 필드 '{field_name}'가 NULL",
            detail={"field": field_name, **(detail or {})}
        )


class InputDataFormatException(InputDataException):
    """입력 데이터 포맷 오류"""
    error_code = "C1-INP-002"

    def __init__(self, field_name: str, expected_format: str, actual_value: Any = None):
        super().__init__(
            message=f"입력 데이터 포맷 오류: '{field_name}' 필드의 형식 불일치 (기대: {expected_format})",
            detail={"field": field_name, "expected": expected_format, "actual": str(actual_value)}
        )


class InputDataRangeException(InputDataException):
    """입력 데이터 범위 오류"""
    error_code = "C1-INP-003"

    def __init__(self, field_name: str, min_val: Any = None, max_val: Any = None, actual: Any = None):
        super().__init__(
            message=f"입력 데이터 범위 오류: '{field_name}' 값이 허용 범위 초과",
            detail={"field": field_name, "min": min_val, "max": max_val, "actual": actual}
        )


# =============================================================================
# 외부 연동 오류 (EXT)
# =============================================================================

class ExternalApiException(OpsException):
    """외부 API 연동 오류"""
    error_code = "C1-EXT-001"
    category = "EXT"
    user_message = "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


class ExternalApiTimeoutException(ExternalApiException):
    """외부 API 타임아웃"""
    error_code = "C1-EXT-001"

    def __init__(self, api_name: str, timeout_seconds: int):
        super().__init__(
            message=f"외부 API 연결 실패: {api_name} 타임아웃 ({timeout_seconds}초)",
            detail={"api": api_name, "timeout": timeout_seconds}
        )


class ExternalApiResponseException(ExternalApiException):
    """외부 API 응답 오류"""
    error_code = "C1-EXT-002"

    def __init__(self, api_name: str, status_code: int, response_body: str = None):
        super().__init__(
            message=f"외부 API 응답 오류: {api_name} HTTP {status_code}",
            detail={"api": api_name, "status_code": status_code, "response": response_body}
        )


class ExternalDataDelayException(ExternalApiException):
    """외부 데이터 수신 지연"""
    error_code = "C1-EXT-003"
    user_message = "데이터 수신 지연이 발생했습니다."

    def __init__(self, data_source: str, expected_time: str = None):
        super().__init__(
            message=f"시세 데이터 수신 지연: {data_source}",
            detail={"data_source": data_source, "expected_time": expected_time}
        )


# =============================================================================
# 배치 실행 오류 (BAT)
# =============================================================================

class BatchExecutionException(OpsException):
    """배치 실행 오류"""
    error_code = "C1-BAT-001"
    category = "BAT"
    user_message = "처리 중 오류가 발생했습니다."


class BatchExecutionFailedException(BatchExecutionException):
    """배치 실행 중 예외 발생"""
    error_code = "C1-BAT-001"

    def __init__(self, job_id: str, execution_id: str, cause: str):
        super().__init__(
            message=f"배치 실행 중 예외 발생: {job_id} (execution: {execution_id[:8]}...)",
            detail={"job_id": job_id, "execution_id": execution_id, "cause": cause}
        )


class BatchExecutionStoppedException(BatchExecutionException):
    """배치 실행 수동 중단"""
    error_code = "C1-BAT-002"
    user_message = "처리가 중단되었습니다."

    def __init__(self, execution_id: str, operator_id: str, reason: str):
        super().__init__(
            message=f"배치 실행 수동 중단: {execution_id[:8]}... by {operator_id}",
            detail={"execution_id": execution_id, "operator_id": operator_id, "reason": reason}
        )


class BatchExecutionTimeoutException(BatchExecutionException):
    """배치 실행 시간 초과"""
    error_code = "C1-BAT-003"
    user_message = "처리 시간이 초과되었습니다."

    def __init__(self, job_id: str, execution_id: str, timeout_seconds: int):
        super().__init__(
            message=f"배치 실행 시간 초과: {job_id} ({timeout_seconds}초 초과)",
            detail={"job_id": job_id, "execution_id": execution_id, "timeout": timeout_seconds}
        )


# =============================================================================
# 데이터 무결성 오류 (DQ)
# =============================================================================

class DataQualityException(OpsException):
    """데이터 무결성 오류"""
    error_code = "C1-DQ-001"
    category = "DQ"
    user_message = "데이터 검증 중 오류가 발생했습니다."


class DuplicateDataException(DataQualityException):
    """중복 레코드 오류"""
    error_code = "C1-DQ-001"

    def __init__(self, table_name: str, key_fields: Dict[str, Any]):
        super().__init__(
            message=f"데이터 정합성 위반: {table_name}에 중복 레코드",
            detail={"table": table_name, "key_fields": key_fields}
        )


class ReferentialIntegrityException(DataQualityException):
    """참조 무결성 오류"""
    error_code = "C1-DQ-002"

    def __init__(self, source_table: str, target_table: str, key_value: Any):
        super().__init__(
            message=f"데이터 정합성 위반: {source_table} -> {target_table} 참조 무결성 오류",
            detail={"source_table": source_table, "target_table": target_table, "key": key_value}
        )


class MissingPeriodDataException(DataQualityException):
    """필수 기간 데이터 누락"""
    error_code = "C1-DQ-003"

    def __init__(self, data_type: str, start_date: str, end_date: str):
        super().__init__(
            message=f"데이터 누락: {data_type} 필수 기간 데이터 없음 ({start_date} ~ {end_date})",
            detail={"data_type": data_type, "start_date": start_date, "end_date": end_date}
        )


# =============================================================================
# 로직 오류 (LOG)
# =============================================================================

class LogicException(OpsException):
    """로직 오류"""
    error_code = "C1-LOG-001"
    category = "LOG"
    user_message = "시스템 오류가 발생했습니다."


class CalculationLogicException(LogicException):
    """계산 로직 오류"""
    error_code = "C1-LOG-001"

    def __init__(self, calculation_name: str, expected: Any = None, actual: Any = None):
        super().__init__(
            message=f"계산 로직 오류: {calculation_name} 산식 결과 이상",
            detail={"calculation": calculation_name, "expected": expected, "actual": actual}
        )


class BranchLogicException(LogicException):
    """분기 로직 오류"""
    error_code = "C1-LOG-002"

    def __init__(self, condition_name: str, unexpected_value: Any):
        super().__init__(
            message=f"분기 로직 오류: {condition_name} 예상치 못한 조건",
            detail={"condition": condition_name, "value": unexpected_value}
        )


# =============================================================================
# 시스템 오류 (SYS)
# =============================================================================

class SystemException(OpsException):
    """시스템 오류"""
    error_code = "C1-SYS-001"
    category = "SYS"
    user_message = "시스템 점검 중입니다."


class DatabaseConnectionException(SystemException):
    """DB 연결 실패"""
    error_code = "C1-SYS-001"

    def __init__(self, db_name: str = "main", cause: str = None):
        super().__init__(
            message=f"DB 연결 실패: {db_name}",
            detail={"database": db_name, "cause": cause}
        )


class ResourceExhaustedException(SystemException):
    """서버 리소스 부족"""
    error_code = "C1-SYS-002"

    def __init__(self, resource_type: str, current_usage: float = None, threshold: float = None):
        super().__init__(
            message=f"서버 리소스 부족: {resource_type}",
            detail={"resource": resource_type, "usage": current_usage, "threshold": threshold}
        )


class FileIOException(SystemException):
    """파일 I/O 오류"""
    error_code = "C1-SYS-003"
    user_message = "시스템 오류가 발생했습니다."

    def __init__(self, file_path: str, operation: str, cause: str = None):
        super().__init__(
            message=f"파일 I/O 오류: {operation} - {file_path}",
            detail={"file": file_path, "operation": operation, "cause": cause}
        )
