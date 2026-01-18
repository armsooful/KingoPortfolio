"""
Phase 3-C / Epic C-2: 데이터 계보(Lineage) 서비스
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.data_quality import DataLineageNode, DataLineageEdge


class LineageService:
    """계보 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create_node(
        self,
        node_type: str,
        ref_type: str,
        ref_id: str,
    ) -> DataLineageNode:
        """계보 노드 생성"""
        node = DataLineageNode(
            node_id=None,
            node_type=node_type,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def create_edge(
        self,
        from_node_id: str,
        to_node_id: str,
    ) -> DataLineageEdge:
        """계보 엣지 생성"""
        edge = DataLineageEdge(
            edge_id=None,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
        )
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[DataLineageNode]:
        """노드 조회"""
        return self.db.query(DataLineageNode).filter_by(node_id=node_id).first()

    def find_nodes_by_ref(
        self,
        ref_type: str,
        ref_id: str,
    ) -> List[DataLineageNode]:
        """참조 기반 노드 조회"""
        return self.db.query(DataLineageNode).filter_by(ref_type=ref_type, ref_id=ref_id).all()

    def get_upstream_nodes(self, node_id: str) -> List[DataLineageNode]:
        """상위 노드 조회"""
        edges = self.db.query(DataLineageEdge).filter_by(to_node_id=node_id).all()
        node_ids = [edge.from_node_id for edge in edges]
        if not node_ids:
            return []
        return self.db.query(DataLineageNode).filter(DataLineageNode.node_id.in_(node_ids)).all()

    def get_downstream_nodes(self, node_id: str) -> List[DataLineageNode]:
        """하위 노드 조회"""
        edges = self.db.query(DataLineageEdge).filter_by(from_node_id=node_id).all()
        node_ids = [edge.to_node_id for edge in edges]
        if not node_ids:
            return []
        return self.db.query(DataLineageNode).filter(DataLineageNode.node_id.in_(node_ids)).all()
