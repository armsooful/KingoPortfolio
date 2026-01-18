"""
관리자 데이터 계보(Lineage) API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Optional

from app.auth import require_admin_permission
from app.database import get_db
from app.models.user import User
from app.services.lineage_service import LineageService
from app.utils.request_meta import request_meta, require_idempotency


router = APIRouter(
    prefix="/admin/lineage",
    tags=["Admin Lineage"],
    dependencies=[Depends(require_idempotency)],
)


class LineageNodeCreate(BaseModel):
    node_type: str = Field(..., min_length=1)
    ref_type: str = Field(..., min_length=1)
    ref_id: str = Field(..., min_length=1)


class LineageEdgeCreate(BaseModel):
    from_node_id: str = Field(..., min_length=1)
    to_node_id: str = Field(..., min_length=1)


@router.post("/nodes")
def create_lineage_node(
    payload: LineageNodeCreate,
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """계보 노드 생성"""
    service = LineageService(db)
    node = service.create_node(payload.node_type, payload.ref_type, payload.ref_id)
    return {
        "success": True,
        "data": {"node_id": node.node_id},
        "request_id": meta["request_id"],
    }


@router.post("/edges")
def create_lineage_edge(
    payload: LineageEdgeCreate,
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """계보 엣지 생성"""
    service = LineageService(db)
    edge = service.create_edge(payload.from_node_id, payload.to_node_id)
    return {
        "success": True,
        "data": {"edge_id": edge.edge_id},
        "request_id": meta["request_id"],
    }


@router.get("/nodes/by-ref")
def get_nodes_by_ref(
    ref_type: str,
    ref_id: str,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """참조 기반 노드 조회"""
    service = LineageService(db)
    nodes = service.find_nodes_by_ref(ref_type, ref_id)
    return {
        "success": True,
        "data": [{"node_id": n.node_id, "node_type": n.node_type, "ref_type": n.ref_type, "ref_id": n.ref_id} for n in nodes],
    }


@router.get("/nodes/{node_id}/upstream")
def get_upstream(
    node_id: str,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """상위 노드 조회"""
    service = LineageService(db)
    node = service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    nodes = service.get_upstream_nodes(node_id)
    return {
        "success": True,
        "data": [{"node_id": n.node_id, "node_type": n.node_type, "ref_type": n.ref_type, "ref_id": n.ref_id} for n in nodes],
    }


@router.get("/nodes/{node_id}/downstream")
def get_downstream(
    node_id: str,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """하위 노드 조회"""
    service = LineageService(db)
    node = service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    nodes = service.get_downstream_nodes(node_id)
    return {
        "success": True,
        "data": [{"node_id": n.node_id, "node_type": n.node_type, "ref_type": n.ref_type, "ref_id": n.ref_id} for n in nodes],
    }
