"""
운영 관리자 API - 배치 실행/감사 로그/알림
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_admin_permission
from app.database import get_db
from app.models.ops import BatchExecution, BatchExecutionLog, OpsAuditLog, OpsAlert
from app.models.user import User
from app.services.audit_log_service import AuditLogService, AuditType, AuditAction
from app.services.batch_execution import BatchExecutionService, RunType, ExecutionStatus, BatchExecutionError
from app.services.ops_alert_service import OpsAlertService, AlertError
from app.services.replay_service import ReplayService, ReplayType, ReplayError
from app.utils.request_meta import request_meta, require_idempotency


router = APIRouter(
    prefix="/admin",
    tags=["Admin Ops"],
    dependencies=[Depends(require_idempotency)],
)


class BatchStartRequest(BaseModel):
    """배치 수동 실행 요청"""
    operator_reason: str = Field(..., min_length=1)
    target_date: Optional[datetime] = None
    target_start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    operator_note: Optional[str] = None
    execution_id: Optional[str] = None


class BatchStopRequest(BaseModel):
    """배치 중단 요청"""
    reason: str = Field(..., min_length=1)


class ReplayRequest(BaseModel):
    """재처리 요청"""
    job_id: str = Field(..., min_length=1)
    replay_type: ReplayType
    replay_reason: str = Field(..., min_length=1)
    operator_note: Optional[str] = None
    parent_execution_id: Optional[str] = None
    target_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None


def _serialize_execution(execution: BatchExecution) -> Dict[str, Any]:
    return {
        "execution_id": execution.execution_id,
        "job_id": execution.job_id,
        "run_type": execution.run_type,
        "status": execution.status,
        "scheduled_at": execution.scheduled_at,
        "started_at": execution.started_at,
        "ended_at": execution.ended_at,
        "target_date": execution.target_date,
        "target_start_date": execution.target_start_date,
        "target_end_date": execution.target_end_date,
        "processed_count": execution.processed_count,
        "success_count": execution.success_count,
        "failed_count": execution.failed_count,
        "error_code": execution.error_code,
        "error_message": execution.error_message,
        "error_detail": execution.error_detail,
        "operator_id": execution.operator_id,
        "operator_note": execution.operator_note,
        "parent_execution_id": execution.parent_execution_id,
        "replay_reason": execution.replay_reason,
        "created_at": execution.created_at,
        "updated_at": execution.updated_at,
    }


def _serialize_log(log: BatchExecutionLog) -> Dict[str, Any]:
    return {
        "log_id": log.log_id,
        "execution_id": log.execution_id,
        "log_level": log.log_level,
        "log_category": log.log_category,
        "log_code": log.log_code,
        "log_message": log.log_message,
        "log_detail": log.log_detail,
        "logged_at": log.logged_at,
    }


def _serialize_audit_log(log: OpsAuditLog) -> Dict[str, Any]:
    return {
        "audit_id": log.audit_id,
        "audit_type": log.audit_type,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "action": log.action,
        "before_state": log.before_state,
        "after_state": log.after_state,
        "operator_id": log.operator_id,
        "operator_ip": log.operator_ip,
        "operator_reason": log.operator_reason,
        "approved_by": log.approved_by,
        "approved_at": log.approved_at,
        "created_at": log.created_at,
    }


def _serialize_alert(alert: OpsAlert) -> Dict[str, Any]:
    return {
        "alert_id": alert.alert_id,
        "alert_type": alert.alert_type,
        "alert_level": alert.alert_level,
        "execution_id": alert.execution_id,
        "related_error_code": alert.related_error_code,
        "alert_title": alert.alert_title,
        "alert_message": alert.alert_message,
        "alert_detail": alert.alert_detail,
        "channels_sent": alert.channels_sent,
        "sent_at": alert.sent_at,
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_at": alert.acknowledged_at,
        "created_at": alert.created_at,
    }


@router.get("/batch/executions")
def list_batch_executions(
    job_id: Optional[str] = None,
    status: Optional[ExecutionStatus] = None,
    run_type: Optional[RunType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """배치 실행 이력 조회"""
    query = db.query(BatchExecution)

    if job_id:
        query = query.filter(BatchExecution.job_id == job_id)
    if status:
        query = query.filter(BatchExecution.status == status.value)
    if run_type:
        query = query.filter(BatchExecution.run_type == run_type.value)
    if start_date:
        query = query.filter(BatchExecution.created_at >= start_date)
    if end_date:
        query = query.filter(BatchExecution.created_at <= end_date)

    executions = (
        query
        .order_by(BatchExecution.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "data": {
            "items": [_serialize_execution(e) for e in executions],
            "count": len(executions),
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/batch/executions/{execution_id}")
def get_batch_execution(
    execution_id: str,
    include_logs: bool = True,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """배치 실행 상세 조회"""
    service = BatchExecutionService(db)
    execution = service.get_execution(execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    logs: List[BatchExecutionLog] = []
    if include_logs:
        logs = service.get_logs(execution_id)

    return {
        "success": True,
        "data": {
            "execution": _serialize_execution(execution),
            "logs": [_serialize_log(log) for log in logs],
        },
    }


@router.post("/batch/executions/{job_id}/start")
def start_batch_execution(
    job_id: str,
    payload: BatchStartRequest,
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """수동 배치 실행"""
    batch_service = BatchExecutionService(db)
    audit_service = AuditLogService(db)
    alert_service = OpsAlertService(db)

    try:
        execution = batch_service.start_execution(
            job_id=job_id,
            run_type=RunType.MANUAL,
            target_date=payload.target_date,
            target_start_date=payload.target_start_date,
            target_end_date=payload.target_end_date,
            operator_id=current_user.id,
            operator_note=payload.operator_note,
            execution_id=payload.execution_id,
        )

        audit_service.log_batch_action(
            audit_type=AuditType.BATCH_START,
            execution_id=execution.execution_id,
            action=AuditAction.START,
            operator_id=current_user.id,
            operator_reason=payload.operator_reason,
            after_state={
                "job_id": job_id,
                "run_type": RunType.MANUAL.value,
                "target_date": payload.target_date.isoformat() if payload.target_date else None,
                "target_start_date": payload.target_start_date.isoformat() if payload.target_start_date else None,
                "target_end_date": payload.target_end_date.isoformat() if payload.target_end_date else None,
            },
        )

        alert_service.send_manual_start_alert(
            execution_id=execution.execution_id,
            job_id=job_id,
            operator_id=current_user.id,
            reason=payload.operator_reason,
        )

        return {
            "success": True,
            "data": _serialize_execution(execution),
            "request_id": meta["request_id"],
        }

    except BatchExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_code": e.error_code},
        )


@router.post("/batch/executions/{execution_id}/stop")
def stop_batch_execution(
    execution_id: str,
    payload: BatchStopRequest,
    current_user: User = Depends(require_admin_permission("ADMIN_STOP")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """수동 배치 중단"""
    batch_service = BatchExecutionService(db)
    audit_service = AuditLogService(db)
    alert_service = OpsAlertService(db)

    try:
        execution = batch_service.stop_execution(
            execution_id=execution_id,
            operator_id=current_user.id,
            reason=payload.reason,
        )

        audit_service.log_batch_action(
            audit_type=AuditType.BATCH_STOP,
            execution_id=execution.execution_id,
            action=AuditAction.STOP,
            operator_id=current_user.id,
            operator_reason=payload.reason,
            after_state={
                "status": execution.status,
                "job_id": execution.job_id,
            },
        )

        alert_service.send_batch_stopped_alert(
            execution_id=execution.execution_id,
            job_id=execution.job_id,
            operator_id=current_user.id,
            reason=payload.reason,
        )

        return {
            "success": True,
            "data": _serialize_execution(execution),
            "request_id": meta["request_id"],
        }

    except BatchExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_code": e.error_code},
        )


@router.post("/batch/replay")
def replay_batch_execution(
    payload: ReplayRequest,
    current_user: User = Depends(require_admin_permission("ADMIN_REPLAY")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """재처리 실행"""
    replay_service = ReplayService(db)
    alert_service = OpsAlertService(db)

    try:
        if payload.replay_type == ReplayType.FULL:
            if not payload.target_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="target_date is required for FULL replay",
                )
            execution = replay_service.replay_full(
                job_id=payload.job_id,
                target_date=payload.target_date,
                operator_id=current_user.id,
                replay_reason=payload.replay_reason,
                parent_execution_id=payload.parent_execution_id,
            )
        elif payload.replay_type == ReplayType.RANGE:
            if not payload.start_date or not payload.end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date and end_date are required for RANGE replay",
                )
            execution = replay_service.replay_range(
                job_id=payload.job_id,
                start_date=payload.start_date,
                end_date=payload.end_date,
                operator_id=current_user.id,
                replay_reason=payload.replay_reason,
                parent_execution_id=payload.parent_execution_id,
            )
        elif payload.replay_type == ReplayType.SINGLE:
            if not payload.target_type or not payload.target_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="target_type and target_id are required for SINGLE replay",
                )
            execution = replay_service.replay_single(
                job_id=payload.job_id,
                target_type=payload.target_type,
                target_id=payload.target_id,
                operator_id=current_user.id,
                replay_reason=payload.replay_reason,
                parent_execution_id=payload.parent_execution_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid replay_type",
            )

        alert_service.send_replay_alert(
            execution_id=execution.execution_id,
            job_id=payload.job_id,
            operator_id=current_user.id,
            replay_reason=payload.replay_reason,
            replay_type=payload.replay_type.value,
        )

        return {
            "success": True,
            "data": _serialize_execution(execution),
            "request_id": meta["request_id"],
        }

    except ReplayError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_code": e.error_code},
        )


@router.get("/audit-logs")
def list_audit_logs(
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    audit_type: Optional[str] = None,
    operator_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """감사 로그 조회"""
    service = AuditLogService(db)
    logs = service.get_audit_logs(
        target_type=target_type,
        target_id=target_id,
        audit_type=audit_type,
        operator_id=operator_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": {
            "items": [_serialize_audit_log(log) for log in logs],
            "count": len(logs),
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/alerts")
def list_alerts(
    alert_type: Optional[str] = None,
    alert_level: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """알림 목록 조회"""
    service = OpsAlertService(db)
    alerts = service.get_alerts(
        alert_type=alert_type,
        alert_level=alert_level,
        acknowledged=acknowledged,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": {
            "items": [_serialize_alert(alert) for alert in alerts],
            "count": len(alerts),
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """알림 확인 처리"""
    service = OpsAlertService(db)
    try:
        alert = service.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=current_user.id,
        )
        return {
            "success": True,
            "data": _serialize_alert(alert),
            "request_id": meta["request_id"],
        }
    except AlertError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_code": e.error_code},
        )
