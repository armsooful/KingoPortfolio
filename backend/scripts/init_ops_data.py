"""
Phase 3-C / Epic C-1: 운영 안정성 초기 데이터 삽입
생성일: 2026-01-18
용도: batch_job 및 error_code_master 초기 데이터 삽입
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine, SessionLocal, Base
from app.models.ops import BatchJob, ErrorCodeMaster


def create_tables():
    """테이블 생성 (ops 테이블만 선택적으로)"""
    from app.models.ops import (
        BatchJob, BatchExecution, BatchExecutionLog,
        OpsAuditLog, ResultVersion, OpsAlert, ErrorCodeMaster
    )
    # ops 테이블만 생성 (기존 JSONB 사용 테이블 제외)
    ops_tables = [
        BatchJob.__table__,
        BatchExecution.__table__,
        BatchExecutionLog.__table__,
        OpsAuditLog.__table__,
        ResultVersion.__table__,
        OpsAlert.__table__,
        ErrorCodeMaster.__table__,
    ]
    for table in ops_tables:
        table.create(bind=engine, checkfirst=True)
    print("✓ C1 테이블 생성 완료")


def init_batch_jobs(session):
    """배치 작업 마스터 데이터 삽입"""
    jobs = [
        BatchJob(
            job_id='DAILY_PRICE_LOAD',
            job_name='일간 시세 적재',
            job_description='일봉 시세 데이터 수집 및 적재',
            job_type='DAILY'
        ),
        BatchJob(
            job_id='DAILY_RETURN_CALC',
            job_name='일간 수익률 계산',
            job_description='일간 수익률 계산 및 저장',
            job_type='DAILY'
        ),
        BatchJob(
            job_id='DAILY_SIMULATION',
            job_name='일간 시뮬레이션',
            job_description='포트폴리오 시뮬레이션 실행',
            job_type='DAILY'
        ),
        BatchJob(
            job_id='DAILY_EXPLANATION',
            job_name='일간 설명 생성',
            job_description='Phase A 설명 자동 생성',
            job_type='DAILY'
        ),
        BatchJob(
            job_id='MONTHLY_REPORT',
            job_name='월간 리포트',
            job_description='월간 성과 리포트 생성',
            job_type='MONTHLY'
        ),
        BatchJob(
            job_id='ON_DEMAND_REPLAY',
            job_name='수동 재처리',
            job_description='운영자 수동 재처리 작업',
            job_type='ON_DEMAND'
        ),
    ]

    for job in jobs:
        existing = session.query(BatchJob).filter_by(job_id=job.job_id).first()
        if not existing:
            session.add(job)
            print(f"  + BatchJob: {job.job_id}")
        else:
            print(f"  - BatchJob: {job.job_id} (이미 존재)")

    session.commit()
    print("✓ BatchJob 마스터 데이터 삽입 완료")


def init_error_codes(session):
    """오류 코드 마스터 데이터 삽입"""
    error_codes = [
        # 입력 데이터 오류 (INP)
        ErrorCodeMaster(
            error_code='C1-INP-001', category='INP', severity='MEDIUM',
            user_message='데이터 처리 중 오류가 발생했습니다.',
            ops_message='입력 데이터 누락: 필수 필드가 NULL',
            action_guide='원천 데이터 확인 후 재처리 필요',
            auto_alert=True, alert_level='WARN'
        ),
        ErrorCodeMaster(
            error_code='C1-INP-002', category='INP', severity='MEDIUM',
            user_message='데이터 처리 중 오류가 발생했습니다.',
            ops_message='입력 데이터 포맷 오류: 날짜/숫자 형식 불일치',
            action_guide='데이터 포맷 검증 후 재처리',
            auto_alert=True, alert_level='WARN'
        ),
        ErrorCodeMaster(
            error_code='C1-INP-003', category='INP', severity='LOW',
            user_message='데이터 처리 중 오류가 발생했습니다.',
            ops_message='입력 데이터 범위 오류: 값이 허용 범위 초과',
            action_guide='데이터 정합성 확인',
            auto_alert=False, alert_level='INFO'
        ),

        # 외부 연동 오류 (EXT)
        ErrorCodeMaster(
            error_code='C1-EXT-001', category='EXT', severity='HIGH',
            user_message='일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
            ops_message='외부 API 연결 실패: 타임아웃',
            action_guide='API 상태 확인 후 재시도',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-EXT-002', category='EXT', severity='HIGH',
            user_message='일시적인 오류가 발생했습니다.',
            ops_message='외부 API 응답 오류: HTTP 5xx',
            action_guide='API 서버 상태 확인',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-EXT-003', category='EXT', severity='MEDIUM',
            user_message='데이터 수신 지연이 발생했습니다.',
            ops_message='시세 데이터 수신 지연',
            action_guide='데이터 제공사 확인',
            auto_alert=True, alert_level='WARN'
        ),

        # 배치 실행 오류 (BAT)
        ErrorCodeMaster(
            error_code='C1-BAT-001', category='BAT', severity='HIGH',
            user_message='처리 중 오류가 발생했습니다.',
            ops_message='배치 실행 중 예외 발생',
            action_guide='로그 확인 후 원인 분석',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-BAT-002', category='BAT', severity='MEDIUM',
            user_message='처리가 중단되었습니다.',
            ops_message='배치 실행 수동 중단',
            action_guide='운영자 중단 사유 확인',
            auto_alert=True, alert_level='WARN'
        ),
        ErrorCodeMaster(
            error_code='C1-BAT-003', category='BAT', severity='HIGH',
            user_message='처리 시간이 초과되었습니다.',
            ops_message='배치 실행 시간 초과',
            action_guide='처리량 확인 및 분할 실행 검토',
            auto_alert=True, alert_level='ERROR'
        ),

        # 데이터 무결성 오류 (DQ)
        ErrorCodeMaster(
            error_code='C1-DQ-001', category='DQ', severity='HIGH',
            user_message='데이터 검증 중 오류가 발생했습니다.',
            ops_message='데이터 정합성 위반: 중복 레코드',
            action_guide='중복 데이터 정리 후 재처리',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-DQ-002', category='DQ', severity='HIGH',
            user_message='데이터 검증 중 오류가 발생했습니다.',
            ops_message='데이터 정합성 위반: 참조 무결성 오류',
            action_guide='관련 데이터 확인',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-DQ-003', category='DQ', severity='MEDIUM',
            user_message='데이터 검증 중 오류가 발생했습니다.',
            ops_message='데이터 누락: 필수 기간 데이터 없음',
            action_guide='누락 기간 데이터 적재 필요',
            auto_alert=True, alert_level='WARN'
        ),

        # 로직 오류 (LOG)
        ErrorCodeMaster(
            error_code='C1-LOG-001', category='LOG', severity='CRITICAL',
            user_message='시스템 오류가 발생했습니다.',
            ops_message='계산 로직 오류: 산식 결과 이상',
            action_guide='로직 검토 및 수정 필요',
            auto_alert=True, alert_level='CRITICAL'
        ),
        ErrorCodeMaster(
            error_code='C1-LOG-002', category='LOG', severity='HIGH',
            user_message='시스템 오류가 발생했습니다.',
            ops_message='분기 로직 오류: 예상치 못한 조건',
            action_guide='로직 검토 필요',
            auto_alert=True, alert_level='ERROR'
        ),

        # 시스템 오류 (SYS)
        ErrorCodeMaster(
            error_code='C1-SYS-001', category='SYS', severity='CRITICAL',
            user_message='시스템 점검 중입니다.',
            ops_message='DB 연결 실패',
            action_guide='DB 서버 상태 확인',
            auto_alert=True, alert_level='CRITICAL'
        ),
        ErrorCodeMaster(
            error_code='C1-SYS-002', category='SYS', severity='CRITICAL',
            user_message='시스템 점검 중입니다.',
            ops_message='서버 리소스 부족: 메모리/디스크',
            action_guide='서버 리소스 확인',
            auto_alert=True, alert_level='CRITICAL'
        ),
        ErrorCodeMaster(
            error_code='C1-SYS-003', category='SYS', severity='HIGH',
            user_message='시스템 오류가 발생했습니다.',
            ops_message='파일 I/O 오류',
            action_guide='파일 시스템 확인',
            auto_alert=True, alert_level='ERROR'
        ),
    ]

    for code in error_codes:
        existing = session.query(ErrorCodeMaster).filter_by(error_code=code.error_code).first()
        if not existing:
            session.add(code)
            print(f"  + ErrorCode: {code.error_code}")
        else:
            print(f"  - ErrorCode: {code.error_code} (이미 존재)")

    session.commit()
    print("✓ ErrorCodeMaster 데이터 삽입 완료")


def verify_tables(session):
    """테이블 생성 확인"""
    job_count = session.query(BatchJob).count()
    error_count = session.query(ErrorCodeMaster).count()

    print(f"\n=== 검증 결과 ===")
    print(f"BatchJob 레코드 수: {job_count}")
    print(f"ErrorCodeMaster 레코드 수: {error_count}")

    if job_count >= 6 and error_count >= 17:
        print("✓ C1-T01 DDL 스키마 적용 완료")
        return True
    else:
        print("✗ 데이터 적재 불완전")
        return False


def main():
    print("=" * 50)
    print("Phase 3-C / Epic C-1 DDL 스키마 적용")
    print("=" * 50)

    # 1. 테이블 생성
    create_tables()

    # 2. 초기 데이터 삽입
    session = SessionLocal()
    try:
        init_batch_jobs(session)
        init_error_codes(session)

        # 3. 검증
        verify_tables(session)
    finally:
        session.close()

    print("=" * 50)


if __name__ == '__main__':
    main()
