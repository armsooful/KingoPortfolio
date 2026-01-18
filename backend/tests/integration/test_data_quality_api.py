"""
Phase 3-C / Epic C-2: 데이터 품질 API 통합 테스트
"""

from datetime import datetime, date

from app.models.ops import BatchJob, BatchExecution, OpsAlert
from app.services.batch_execution import ExecutionStatus, RunType
from app.services.data_quality_service import DataQualityService, ValidationStatus


def _seed_job_and_execution(db, job_id: str) -> str:
    job = BatchJob(
        job_id=job_id,
        job_name="DQ Test Job",
        job_description="Data quality integration test",
        job_type="DAILY",
        is_active=True,
    )
    db.add(job)
    db.commit()

    execution = BatchExecution(
        execution_id="exec-dq-001",
        job_id=job_id,
        run_type=RunType.MANUAL.value,
        status=ExecutionStatus.RUNNING.value,
        scheduled_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    return execution.execution_id


def test_data_quality_report_and_enforcement(client, admin_headers, db):
    job_id = "DAILY_SIMULATION"
    execution_id = _seed_job_and_execution(db, job_id)

    dq_service = DataQualityService(db)
    dq_service.register_rule(
        rule_code="C2-DQ-001",
        rule_type="REQ",
        rule_name="Required field check",
        severity="FAIL",
    )

    dq_service.record_result(
        execution_id=execution_id,
        rule_code="C2-DQ-001",
        status=ValidationStatus.FAIL,
        target_ref_type="SIMULATION",
        target_ref_id="sim-1",
        violation_count=2,
        sample_detail={"missing": ["field_a", "field_b"]},
    )

    # C2-T06: 정책 적용 (FAIL -> execution FAILED + 알림)
    result = dq_service.enforce_policy(execution_id)
    assert result["status"] == ValidationStatus.FAIL.value

    execution = db.query(BatchExecution).filter_by(execution_id=execution_id).first()
    assert execution.status == ExecutionStatus.FAILED.value

    alerts = db.query(OpsAlert).filter_by(execution_id=execution_id).all()
    assert any(alert.alert_level == "ERROR" for alert in alerts)

    # C2-T05: 리포트 생성/조회 API
    create_response = client.post(
        "/admin/data-quality/reports",
        headers={**admin_headers, "X-Idempotency-Key": "dq-report"},
        json={"execution_id": execution_id, "report_date": date.today().isoformat()},
    )
    assert create_response.status_code == 200
    report_id = create_response.json()["data"]["report_id"]

    list_response = client.get(
        "/admin/data-quality/reports",
        headers=admin_headers,
    )
    assert list_response.status_code == 200
    assert any(r["report_id"] == report_id for r in list_response.json()["data"])

    detail_response = client.get(
        f"/admin/data-quality/reports/{report_id}",
        headers=admin_headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["report_id"] == report_id
