"""
Phase 3-C / Epic C-2: 데이터 품질/계보/재현성 모델
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, Date, DateTime, Text,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.database import Base
from app.utils.kst_now import kst_now


class DataSnapshot(Base):
    """원천 데이터 스냅샷"""
    __tablename__ = "data_snapshot"

    snapshot_id = Column(String(36), primary_key=True)
    vendor = Column(String(50), nullable=False)
    dataset_type = Column(String(50), nullable=False)
    asof_date = Column(Date, nullable=False)
    snapshot_label = Column(String(100), nullable=True)
    source_uri = Column(Text, nullable=True)
    record_count = Column(Integer, default=0)
    checksum = Column(String(128), nullable=True)
    collected_at = Column(DateTime, default=kst_now)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_data_snapshot_key", "vendor", "dataset_type", "asof_date"),
        Index("idx_data_snapshot_active", "is_active"),
    )


class DataLineageNode(Base):
    """계보 노드"""
    __tablename__ = "data_lineage_node"

    node_id = Column(String(36), primary_key=True)
    node_type = Column(String(30), nullable=False)
    ref_type = Column(String(50), nullable=False)
    ref_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=kst_now)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_lineage_node_ref", "ref_type", "ref_id"),
    )


class DataLineageEdge(Base):
    """계보 엣지"""
    __tablename__ = "data_lineage_edge"

    edge_id = Column(String(36), primary_key=True)
    from_node_id = Column(String(36), ForeignKey("data_lineage_node.node_id", ondelete="CASCADE"), nullable=False)
    to_node_id = Column(String(36), ForeignKey("data_lineage_node.node_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index("idx_lineage_edge_from", "from_node_id"),
        Index("idx_lineage_edge_to", "to_node_id"),
    )


class ValidationRuleMaster(Base):
    """정합성 규칙 마스터"""
    __tablename__ = "validation_rule_master"

    rule_code = Column(String(30), primary_key=True)
    rule_type = Column(String(10), nullable=False)
    rule_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(10), nullable=False)  # WARN/FAIL
    scope_type = Column(String(20), nullable=False, default="GLOBAL")
    scope_key = Column(String(50), nullable=True)
    scope_value = Column(String(100), nullable=True)
    scope_json = Column(JSONB, nullable=False, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

    __table_args__ = (
        Index("idx_validation_rule_type", "rule_type"),
        Index("idx_validation_rule_scope", "scope_type", "scope_key", "scope_value"),
    )


class ValidationRuleVersion(Base):
    """정합성 규칙 버전"""
    __tablename__ = "validation_rule_version"

    rule_version_id = Column(String(36), primary_key=True)
    rule_code = Column(String(30), ForeignKey("validation_rule_master.rule_code"), nullable=False)
    version_no = Column(Integer, nullable=False)
    rule_params = Column(JSONB, nullable=False, default={})
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index("ux_validation_rule_version", "rule_code", "version_no", unique=True),
    )


class ValidationResult(Base):
    """정합성 실행 결과"""
    __tablename__ = "validation_result"

    result_id = Column(String(36), primary_key=True)
    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id", ondelete="CASCADE"), nullable=False)
    rule_code = Column(String(30), ForeignKey("validation_rule_master.rule_code"), nullable=False)
    rule_version_id = Column(String(36), ForeignKey("validation_rule_version.rule_version_id"), nullable=True)
    target_ref_type = Column(String(50), nullable=False)
    target_ref_id = Column(String(100), nullable=False)
    status = Column(String(10), nullable=False)  # PASS/WARN/FAIL
    violation_count = Column(Integer, default=0)
    sample_detail = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index("idx_validation_result_exec", "execution_id"),
        Index("idx_validation_result_rule", "rule_code", "status"),
    )


class ExecutionContext(Base):
    """실행 컨텍스트(재현성)"""
    __tablename__ = "execution_context"

    context_id = Column(String(36), primary_key=True)
    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id", ondelete="CASCADE"), nullable=False)
    snapshot_ids = Column(JSONB, nullable=False)
    rule_version_ids = Column(JSONB, nullable=False)
    calc_params = Column(JSONB, nullable=False, default={})
    code_version = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index("ux_execution_context_execution", "execution_id", unique=True),
    )


class DataQualityReport(Base):
    """데이터 품질 리포트"""
    __tablename__ = "data_quality_report"

    report_id = Column(String(36), primary_key=True)
    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id", ondelete="CASCADE"), nullable=False)
    report_date = Column(Date, nullable=False)
    summary_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index("idx_dq_report_date", "report_date"),
    )


class DataQualityReportItem(Base):
    """데이터 품질 리포트 항목"""
    __tablename__ = "data_quality_report_item"

    item_id = Column(String(36), primary_key=True)
    report_id = Column(String(36), ForeignKey("data_quality_report.report_id", ondelete="CASCADE"), nullable=False)
    dataset_type = Column(String(50), nullable=False)
    status = Column(String(10), nullable=False)
    detail_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index("idx_dq_item_report", "report_id"),
    )
