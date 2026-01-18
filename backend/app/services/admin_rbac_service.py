"""
Phase 3-C / Epic C-4: 관리자 RBAC 서비스
"""

from typing import Dict, Iterable, List, Optional, Set

from sqlalchemy.orm import Session

from app.models.admin_controls import (
    AdminRole,
    AdminPermission,
    AdminRolePermission,
    AdminUserRole,
)
from app.models.user import User


class AdminRBACService:
    """관리자 권한(RBAC) 서비스"""

    DEFAULT_ROLES: Dict[str, str] = {
        "ADMIN_VIEWER": "조회 전용",
        "ADMIN_OPERATOR": "실행/중단/재처리 수행",
        "ADMIN_APPROVER": "정정/버전 전환 승인",
        "SUPER_ADMIN": "모든 권한 및 권한 관리",
    }

    DEFAULT_PERMISSIONS: Dict[str, str] = {
        "ADMIN_VIEW": "관리자 조회 권한",
        "ADMIN_RUN": "배치 수동 실행",
        "ADMIN_STOP": "배치 중단/재개",
        "ADMIN_REPLAY": "재처리 실행",
        "ADMIN_ACTIVATE_VERSION": "결과 버전 전환",
        "ADMIN_ADJUST": "수동 정정",
        "ADMIN_APPROVE": "승인 처리",
        "ADMIN_ROLE_MANAGE": "관리자 권한 관리",
    }

    ROLE_PERMISSIONS: Dict[str, Set[str]] = {
        "ADMIN_VIEWER": {"ADMIN_VIEW"},
        "ADMIN_OPERATOR": {"ADMIN_VIEW", "ADMIN_RUN", "ADMIN_STOP", "ADMIN_REPLAY"},
        "ADMIN_APPROVER": {"ADMIN_VIEW", "ADMIN_APPROVE", "ADMIN_ACTIVATE_VERSION", "ADMIN_ADJUST"},
        "SUPER_ADMIN": set(DEFAULT_PERMISSIONS.keys()),
    }

    def __init__(self, db: Session):
        self.db = db

    def bootstrap_defaults(self) -> None:
        """기본 역할/권한/매핑 생성 (idempotent)"""
        roles = {}
        for role_name, role_desc in self.DEFAULT_ROLES.items():
            role = self.db.query(AdminRole).filter_by(role_name=role_name).first()
            if not role:
                role = AdminRole(role_name=role_name, role_desc=role_desc, is_active=True)
                self.db.add(role)
                self.db.commit()
                self.db.refresh(role)
            roles[role_name] = role

        permissions = {}
        for perm_key, perm_desc in self.DEFAULT_PERMISSIONS.items():
            perm = self.db.query(AdminPermission).filter_by(permission_key=perm_key).first()
            if not perm:
                perm = AdminPermission(permission_key=perm_key, permission_desc=perm_desc)
                self.db.add(perm)
                self.db.commit()
                self.db.refresh(perm)
            permissions[perm_key] = perm

        for role_name, perm_keys in self.ROLE_PERMISSIONS.items():
            role = roles.get(role_name)
            if not role:
                continue
            for perm_key in perm_keys:
                perm = permissions.get(perm_key)
                if not perm:
                    continue
                exists = (
                    self.db.query(AdminRolePermission)
                    .filter_by(role_id=role.role_id, permission_id=perm.permission_id)
                    .first()
                )
                if not exists:
                    self.db.add(
                        AdminRolePermission(
                            role_id=role.role_id,
                            permission_id=perm.permission_id,
                        )
                    )
                    self.db.commit()

    def assign_role(
        self,
        user_id: str,
        role_name: str,
        assigned_by: Optional[str] = None,
    ) -> AdminUserRole:
        """사용자에게 관리자 역할 부여"""
        role = self.db.query(AdminRole).filter_by(role_name=role_name).first()
        if not role:
            raise ValueError(f"Unknown admin role: {role_name}")

        mapping = (
            self.db.query(AdminUserRole)
            .filter_by(user_id=user_id, role_id=role.role_id)
            .first()
        )
        if mapping:
            if not mapping.is_active:
                mapping.is_active = True
                mapping.assigned_by = assigned_by
                self.db.commit()
            return mapping

        mapping = AdminUserRole(
            user_id=user_id,
            role_id=role.role_id,
            assigned_by=assigned_by,
            is_active=True,
        )
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def revoke_role(self, user_id: str, role_name: str) -> None:
        """사용자 관리자 역할 비활성화"""
        role = self.db.query(AdminRole).filter_by(role_name=role_name).first()
        if not role:
            return
        mapping = (
            self.db.query(AdminUserRole)
            .filter_by(user_id=user_id, role_id=role.role_id)
            .first()
        )
        if mapping and mapping.is_active:
            mapping.is_active = False
            self.db.commit()

    def list_user_roles(self, user_id: str) -> List[str]:
        """사용자 관리자 역할 목록"""
        roles = (
            self.db.query(AdminRole)
            .join(AdminUserRole, AdminUserRole.role_id == AdminRole.role_id)
            .filter(AdminUserRole.user_id == user_id, AdminUserRole.is_active.is_(True))
            .all()
        )
        return [role.role_name for role in roles]

    def list_user_permissions(self, user_id: str, allow_legacy_admin: bool = True) -> Set[str]:
        """사용자 권한 목록"""
        if allow_legacy_admin and self._legacy_admin(user_id):
            return set(self.DEFAULT_PERMISSIONS.keys())

        perms = (
            self.db.query(AdminPermission.permission_key)
            .join(AdminRolePermission, AdminRolePermission.permission_id == AdminPermission.permission_id)
            .join(AdminUserRole, AdminUserRole.role_id == AdminRolePermission.role_id)
            .filter(AdminUserRole.user_id == user_id, AdminUserRole.is_active.is_(True))
            .all()
        )
        return {perm_key for (perm_key,) in perms}

    def has_permission(
        self,
        user_id: str,
        permission_key: str,
        allow_legacy_admin: bool = True,
    ) -> bool:
        """권한 보유 여부"""
        if allow_legacy_admin and self._legacy_admin(user_id):
            return True
        permissions = self.list_user_permissions(user_id, allow_legacy_admin=False)
        return permission_key in permissions

    def require_permissions(
        self,
        user_id: str,
        permissions: Iterable[str],
        allow_legacy_admin: bool = True,
    ) -> bool:
        """복수 권한 확인 (모두 필요)"""
        if allow_legacy_admin and self._legacy_admin(user_id):
            return True
        permission_set = self.list_user_permissions(user_id, allow_legacy_admin=False)
        return all(permission in permission_set for permission in permissions)

    def _legacy_admin(self, user_id: str) -> bool:
        """기존 admin 플래그 하위 호환성"""
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            return False
        return user.is_admin or user.role == "admin"
