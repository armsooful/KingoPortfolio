"""
Phase 3-C / Epic C-4: 관리자 통제 모델 (RBAC)
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class AdminRole(Base):
    """관리자 역할"""
    __tablename__ = "admin_role"

    role_id = Column(String(36), primary_key=True, default=_uuid_str)
    role_name = Column(String(50), nullable=False, unique=True)
    role_desc = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminPermission(Base):
    """관리자 권한"""
    __tablename__ = "admin_permission"

    permission_id = Column(String(36), primary_key=True, default=_uuid_str)
    permission_key = Column(String(100), nullable=False, unique=True)
    permission_desc = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminRolePermission(Base):
    """역할-권한 매핑"""
    __tablename__ = "admin_role_permission"

    role_id = Column(String(36), ForeignKey("admin_role.role_id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(String(36), ForeignKey("admin_permission.permission_id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_admin_role_permission_role", "role_id"),
        Index("idx_admin_role_permission_perm", "permission_id"),
    )


class AdminUserRole(Base):
    """사용자-역할 매핑"""
    __tablename__ = "admin_user_role"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(String(36), ForeignKey("admin_role.role_id", ondelete="CASCADE"), primary_key=True)
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("idx_admin_user_role_user", "user_id"),
        Index("idx_admin_user_role_role", "role_id"),
    )


class AdminAuditLog(Base):
    """관리자 감사 로그"""
    __tablename__ = "admin_audit_log"

    audit_id = Column(String(36), primary_key=True, default=_uuid_str)
    operator_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    operator_role = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    request_id = Column(String(100), nullable=True)
    idempotency_key = Column(String(100), nullable=True)
    before_state = Column(JSONB, nullable=True)
    after_state = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_admin_audit_operator", "operator_id"),
        Index("idx_admin_audit_target", "target_type", "target_id"),
        Index("idx_admin_audit_created", "created_at"),
    )


class AdminApproval(Base):
    """승인 워크플로우"""
    __tablename__ = "admin_approval"

    approval_id = Column(String(36), primary_key=True, default=_uuid_str)
    request_type = Column(String(50), nullable=False)
    request_payload = Column(JSONB, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="PENDING")
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_reason = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    request_id = Column(String(100), nullable=True)
    idempotency_key = Column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_admin_approval_status", "status"),
        Index("idx_admin_approval_request", "request_type"),
    )


class AdminAdjustment(Base):
    """수동 정정(보정)"""
    __tablename__ = "admin_adjustment"

    adjustment_id = Column(String(36), primary_key=True, default=_uuid_str)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False)
    adjustment_type = Column(String(50), nullable=False)
    adjustment_data = Column(JSONB, nullable=False, default=dict)
    reason = Column(Text, nullable=False)
    approval_id = Column(String(36), ForeignKey("admin_approval.approval_id"), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_admin_adjustment_target", "target_type", "target_id"),
        Index("idx_admin_adjustment_status", "status"),
    )
