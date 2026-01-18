"""
Phase 3-C / Epic C-2: 실행 컨텍스트 저장 서비스
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.data_quality import ExecutionContext


class ExecutionContextService:
    """실행 컨텍스트 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create_context(
        self,
        execution_id: str,
        snapshot_ids: List[str],
        rule_version_ids: List[str],
        calc_params: Optional[Dict[str, Any]] = None,
        code_version: Optional[str] = None,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
    ) -> ExecutionContext:
        """실행 컨텍스트 생성"""
        context = ExecutionContext(
            context_id=None,
            execution_id=execution_id,
            snapshot_ids=snapshot_ids,
            rule_version_ids=rule_version_ids,
            calc_params=calc_params or {},
            code_version=code_version,
            started_at=started_at,
            ended_at=ended_at,
        )
        self.db.add(context)
        self.db.commit()
        self.db.refresh(context)
        return context

    def get_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """execution_id 기준 컨텍스트 조회"""
        return self.db.query(ExecutionContext).filter_by(
            execution_id=execution_id
        ).first()

    def list_contexts(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExecutionContext]:
        """최근 컨텍스트 목록 조회"""
        return (
            self.db.query(ExecutionContext)
            .order_by(ExecutionContext.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
