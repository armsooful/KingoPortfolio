"""
Phase 3-C / Epic C-1: 통합 테스트 (운영 안정성)
"""

from datetime import date, datetime

from app.models.ops import BatchJob, ResultVersion, OpsAlert, OpsAuditLog
from app.services.batch_execution import BatchExecutionService, ExecutionStatus


def _seed_batch_job(db, job_id: str) -> None:
    job = BatchJob(
        job_id=job_id,
        job_name="Daily Simulation",
        job_description="Test job for ops reliability",
        job_type="DAILY",
        is_active=True,
    )
    db.add(job)
    db.commit()


def test_ops_flow_batch_failure_replay_and_alerts(client, admin_headers, db):
    """
    배치 실행 -> 실패 -> 재처리 흐름 통합 테스트
    - 배치 실행 생성
    - 실패 처리
    - 재처리 실행
    - 감사 로그/알림 기록 확인
    """
    job_id = "DAILY_SIMULATION"
    _seed_batch_job(db, job_id)

    # 1) 수동 배치 실행
    response = client.post(
        f"/admin/batch/executions/{job_id}/start",
        headers={**admin_headers, "X-Idempotency-Key": "batch-start"},
        json={
            "operator_reason": "manual run for test",
            "target_date": datetime.utcnow().isoformat(),
        },
    )
    assert response.status_code == 200
    execution_id = response.json()["data"]["execution_id"]

    # 2) 실패 처리
    service = BatchExecutionService(db)
    service.fail_execution(
        execution_id=execution_id,
        error_code="C1-BAT-001",
        error_message="forced failure for test",
    )

    # 3) 기존 결과 버전 생성 (재처리 시 비활성화 확인용)
    result_version = ResultVersion(
        result_type="SIMULATION",
        result_id="sim-1",
        is_active=True,
    )
    db.add(result_version)
    db.commit()

    # 4) 재처리 실행
    replay_response = client.post(
        "/admin/batch/replay",
        headers={**admin_headers, "X-Idempotency-Key": "batch-replay"},
        json={
            "job_id": job_id,
            "replay_type": "FULL",
            "replay_reason": "replay for test",
            "parent_execution_id": execution_id,
            "target_date": date.today().isoformat(),
        },
    )
    assert replay_response.status_code == 200
    replay_data = replay_response.json()["data"]
    assert replay_data["run_type"] == "REPLAY"

    # 5) 결과 버전 비활성화 확인
    db.refresh(result_version)
    assert result_version.is_active is False

    # 6) 실행 조회 API 확인
    list_response = client.get(
        "/admin/batch/executions",
        headers=admin_headers,
        params={"job_id": job_id},
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"]["count"] >= 2

    detail_response = client.get(
        f"/admin/batch/executions/{execution_id}",
        headers=admin_headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["execution"]["status"] == ExecutionStatus.FAILED.value

    # 7) 감사 로그 및 알림 기록 확인
    audit_logs = db.query(OpsAuditLog).all()
    assert any(log.audit_type == "BATCH_START" for log in audit_logs)
    assert any(log.audit_type == "BATCH_REPLAY" for log in audit_logs)

    alerts = db.query(OpsAlert).all()
    assert any(alert.alert_type == "REPLAY_EXECUTED" for alert in alerts)

    # 8) 알림 확인 처리
    replay_alert = next(alert for alert in alerts if alert.alert_type == "REPLAY_EXECUTED")
    ack_response = client.post(
        f"/admin/alerts/{replay_alert.alert_id}/acknowledge",
        headers={**admin_headers, "X-Idempotency-Key": "alert-ack"},
    )
    assert ack_response.status_code == 200
    assert ack_response.json()["data"]["acknowledged_by"] is not None


def test_ops_duplicate_execution_id(client, admin_headers, db):
    job_id = "DAILY_SIMULATION"
    _seed_batch_job(db, job_id)

    execution_id = "exec-dup-001"
    start_response = client.post(
        f"/admin/batch/executions/{job_id}/start",
        headers={**admin_headers, "X-Idempotency-Key": "batch-dup-1"},
        json={
            "operator_reason": "manual run for test",
            "execution_id": execution_id,
        },
    )
    assert start_response.status_code == 200

    dup_response = client.post(
        f"/admin/batch/executions/{job_id}/start",
        headers={**admin_headers, "X-Idempotency-Key": "batch-dup-2"},
        json={
            "operator_reason": "manual run for test",
            "execution_id": execution_id,
        },
    )
    assert dup_response.status_code == 400
    payload = dup_response.json()
    assert payload["error"]["code"] == "HTTP_400"


def test_ops_stop_execution_creates_alert_and_audit(client, admin_headers, db):
    job_id = "DAILY_SIMULATION"
    _seed_batch_job(db, job_id)

    start_response = client.post(
        f"/admin/batch/executions/{job_id}/start",
        headers={**admin_headers, "X-Idempotency-Key": "batch-stop-start"},
        json={
            "operator_reason": "manual run for stop test",
            "target_date": datetime.utcnow().isoformat(),
        },
    )
    assert start_response.status_code == 200
    execution_id = start_response.json()["data"]["execution_id"]

    stop_response = client.post(
        f"/admin/batch/executions/{execution_id}/stop",
        headers={**admin_headers, "X-Idempotency-Key": "batch-stop"},
        json={"reason": "manual stop"},
    )
    assert stop_response.status_code == 200
    assert stop_response.json()["data"]["status"] == ExecutionStatus.STOPPED.value

    audit_logs = db.query(OpsAuditLog).all()
    assert any(log.audit_type == "BATCH_STOP" for log in audit_logs)

    alerts = db.query(OpsAlert).filter_by(execution_id=execution_id).all()
    assert any(alert.alert_type == "BATCH_STOPPED" for alert in alerts)


def test_admin_batch_requires_admin(client, auth_headers):
    response = client.get("/admin/batch/executions", headers=auth_headers)
    assert response.status_code == 403
