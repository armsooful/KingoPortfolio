"""
Phase 3-C / Epic C-1: 결과 버전 관리 서비스
생성일: 2026-01-18
목적: 시뮬레이션/성과/설명 등 결과 데이터의 버전 관리
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.ops import ResultVersion


class ResultType(str, Enum):
    """결과 유형"""
    SIMULATION = "SIMULATION"
    PERFORMANCE = "PERFORMANCE"
    EXPLANATION = "EXPLANATION"


class VersionError(Exception):
    """버전 관리 관련 예외"""
    def __init__(self, message: str, error_code: str = "C1-VER-001"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ActiveVersionNotFoundError(VersionError):
    """활성 버전 없음"""
    def __init__(self, result_type: str, result_id: str):
        super().__init__(
            f"No active version found for {result_type}/{result_id}",
            error_code="C1-VER-002"
        )


class DuplicateActiveVersionError(VersionError):
    """중복 활성 버전"""
    def __init__(self, result_type: str, result_id: str):
        super().__init__(
            f"Duplicate active version for {result_type}/{result_id}",
            error_code="C1-VER-003"
        )


class ResultVersionService:
    """결과 버전 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create_version(
        self,
        result_type: str,
        result_id: str,
        execution_id: Optional[str] = None,
        deactivate_previous: bool = True,
        deactivated_by: Optional[str] = None,
        deactivate_reason: Optional[str] = None,
    ) -> ResultVersion:
        """
        신규 버전 생성

        Args:
            result_type: 결과 유형 (SIMULATION/PERFORMANCE/EXPLANATION)
            result_id: 원본 결과 ID
            execution_id: 생성한 배치 실행 ID
            deactivate_previous: 이전 버전 비활성화 여부
            deactivated_by: 비활성화 수행자
            deactivate_reason: 비활성화 사유

        Returns:
            ResultVersion: 생성된 버전
        """
        # 현재 최대 버전 번호 조회
        max_version = self._get_max_version_no(result_type, result_id)
        new_version_no = max_version + 1

        # 이전 활성 버전 비활성화
        previous_version = None
        if deactivate_previous:
            previous_version = self.get_active_version(result_type, result_id)
            if previous_version:
                self._deactivate_version(
                    previous_version,
                    deactivated_by=deactivated_by,
                    reason=deactivate_reason,
                )

        # 새 버전 생성
        version = ResultVersion(
            result_type=result_type,
            result_id=result_id,
            execution_id=execution_id,
            version_no=new_version_no,
            is_active=True,
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        # 이전 버전에 superseded_by 설정
        if previous_version:
            previous_version.superseded_by = version.version_id
            self.db.commit()

        return version

    def create_performance_version(
        self,
        performance_id: str,
        execution_id: Optional[str] = None,
        deactivate_previous: bool = True,
        deactivated_by: Optional[str] = None,
        deactivate_reason: Optional[str] = None,
    ) -> ResultVersion:
        """성과 결과 버전 생성 (PERFORMANCE)"""
        return self.create_version(
            result_type=ResultType.PERFORMANCE.value,
            result_id=performance_id,
            execution_id=execution_id,
            deactivate_previous=deactivate_previous,
            deactivated_by=deactivated_by,
            deactivate_reason=deactivate_reason,
        )

    def deactivate_version(
        self,
        result_type: str,
        result_id: str,
        deactivated_by: str,
        reason: str,
    ) -> Optional[ResultVersion]:
        """
        기존 버전 비활성화

        Args:
            result_type: 결과 유형
            result_id: 원본 결과 ID
            deactivated_by: 비활성화 수행자 (필수)
            reason: 비활성화 사유 (필수)

        Returns:
            ResultVersion: 비활성화된 버전 (없으면 None)
        """
        if not deactivated_by:
            raise VersionError("deactivated_by is required", "C1-VER-004")
        if not reason:
            raise VersionError("reason is required", "C1-VER-005")

        version = self.get_active_version(result_type, result_id)
        if version:
            self._deactivate_version(version, deactivated_by, reason)
            return version

        return None

    def _deactivate_version(
        self,
        version: ResultVersion,
        deactivated_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """내부: 버전 비활성화"""
        version.is_active = False
        version.deactivated_at = datetime.utcnow()
        version.deactivated_by = deactivated_by
        version.deactivate_reason = reason
        self.db.commit()

    def get_active_version(
        self,
        result_type: str,
        result_id: str,
    ) -> Optional[ResultVersion]:
        """
        현재 유효 버전 조회

        Args:
            result_type: 결과 유형
            result_id: 원본 결과 ID

        Returns:
            ResultVersion: 활성 버전 (없으면 None)
        """
        return self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.result_id == result_id,
            ResultVersion.is_active == True,
        ).first()

    def get_active_version_or_raise(
        self,
        result_type: str,
        result_id: str,
    ) -> ResultVersion:
        """
        현재 유효 버전 조회 (없으면 예외)

        Args:
            result_type: 결과 유형
            result_id: 원본 결과 ID

        Returns:
            ResultVersion: 활성 버전

        Raises:
            ActiveVersionNotFoundError: 활성 버전 없음
        """
        version = self.get_active_version(result_type, result_id)
        if not version:
            raise ActiveVersionNotFoundError(result_type, result_id)
        return version

    def get_version_history(
        self,
        result_type: str,
        result_id: str,
        include_active: bool = True,
    ) -> List[ResultVersion]:
        """
        버전 이력 조회

        Args:
            result_type: 결과 유형
            result_id: 원본 결과 ID
            include_active: 활성 버전 포함 여부

        Returns:
            List[ResultVersion]: 버전 이력 (최신순)
        """
        query = self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.result_id == result_id,
        )

        if not include_active:
            query = query.filter(ResultVersion.is_active == False)

        return query.order_by(ResultVersion.version_no.desc()).all()

    def get_version_by_no(
        self,
        result_type: str,
        result_id: str,
        version_no: int,
    ) -> Optional[ResultVersion]:
        """
        특정 버전 번호로 조회

        Args:
            result_type: 결과 유형
            result_id: 원본 결과 ID
            version_no: 버전 번호

        Returns:
            ResultVersion: 해당 버전 (없으면 None)
        """
        return self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.result_id == result_id,
            ResultVersion.version_no == version_no,
        ).first()

    def get_version_by_id(self, version_id: int) -> Optional[ResultVersion]:
        """버전 ID로 조회"""
        return self.db.query(ResultVersion).filter_by(version_id=version_id).first()

    def _get_max_version_no(self, result_type: str, result_id: str) -> int:
        """최대 버전 번호 조회"""
        result = self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.result_id == result_id,
        ).order_by(ResultVersion.version_no.desc()).first()

        return result.version_no if result else 0

    def count_versions(
        self,
        result_type: str,
        result_id: str,
    ) -> int:
        """버전 수 조회"""
        return self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.result_id == result_id,
        ).count()

    def validate_single_active(
        self,
        result_type: str,
        result_id: str,
    ) -> bool:
        """
        단일 활성 버전 유지 검증

        Args:
            result_type: 결과 유형
            result_id: 원본 결과 ID

        Returns:
            bool: 유효성 (True=정상, False=중복 활성)

        Raises:
            DuplicateActiveVersionError: 중복 활성 버전 존재
        """
        active_count = self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.result_id == result_id,
            ResultVersion.is_active == True,
        ).count()

        if active_count > 1:
            raise DuplicateActiveVersionError(result_type, result_id)

        return True

    def get_all_active_versions(
        self,
        result_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResultVersion]:
        """
        모든 활성 버전 조회

        Args:
            result_type: 결과 유형 필터 (선택)
            limit: 조회 건수

        Returns:
            List[ResultVersion]: 활성 버전 목록
        """
        query = self.db.query(ResultVersion).filter(
            ResultVersion.is_active == True
        )

        if result_type:
            query = query.filter(ResultVersion.result_type == result_type)

        return query.order_by(ResultVersion.created_at.desc()).limit(limit).all()

    def get_versions_by_execution(
        self,
        execution_id: str,
    ) -> List[ResultVersion]:
        """
        배치 실행으로 생성된 버전 조회

        Args:
            execution_id: 배치 실행 ID

        Returns:
            List[ResultVersion]: 해당 실행으로 생성된 버전
        """
        return self.db.query(ResultVersion).filter(
            ResultVersion.execution_id == execution_id,
        ).order_by(ResultVersion.created_at.desc()).all()

    def reactivate_version(
        self,
        version_id: int,
        reactivated_by: str,
        reason: str,
    ) -> ResultVersion:
        """
        이전 버전 재활성화 (롤백)

        Args:
            version_id: 재활성화할 버전 ID
            reactivated_by: 수행자
            reason: 사유

        Returns:
            ResultVersion: 재활성화된 버전
        """
        if not reactivated_by:
            raise VersionError("reactivated_by is required", "C1-VER-006")
        if not reason:
            raise VersionError("reason is required", "C1-VER-007")

        version = self.get_version_by_id(version_id)
        if not version:
            raise VersionError(f"Version not found: {version_id}", "C1-VER-008")

        if version.is_active:
            raise VersionError(f"Version {version_id} is already active", "C1-VER-009")

        # 현재 활성 버전 비활성화
        current_active = self.get_active_version(version.result_type, version.result_id)
        if current_active:
            self._deactivate_version(
                current_active,
                deactivated_by=reactivated_by,
                reason=f"Rollback to version {version.version_no}: {reason}",
            )

        # 대상 버전 재활성화
        version.is_active = True
        version.deactivated_at = None
        version.deactivated_by = None
        version.deactivate_reason = None
        self.db.commit()
        self.db.refresh(version)

        return version
