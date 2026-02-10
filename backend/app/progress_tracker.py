# backend/app/progress_tracker.py

from typing import Dict, Optional
from datetime import datetime, timedelta
import threading
from app.config import settings

# 완료된 태스크 보존 시간 (기본 30분)
COMPLETED_TASK_RETENTION_MINUTES = 30


class ProgressTracker:
    """데이터 수집 진행 상황 추적"""

    def __init__(self, history_limit: int = 200):
        self._progress: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._history_limit = history_limit

    def _cleanup_expired(self):
        """보존 기간이 지난 완료 태스크 자동 정리 (lock 내부에서 호출)"""
        now = datetime.utcnow()
        expired = []
        for task_id, task in self._progress.items():
            if task["status"] in ("completed", "failed") and task.get("completed_at"):
                try:
                    completed_at = datetime.fromisoformat(task["completed_at"])
                    if now - completed_at > timedelta(minutes=COMPLETED_TASK_RETENTION_MINUTES):
                        expired.append(task_id)
                except (ValueError, TypeError):
                    pass
        for task_id in expired:
            del self._progress[task_id]

    def start_task(self, task_id: str, total_items: int, description: str = ""):
        """작업 시작"""
        with self._lock:
            # 새 태스크 시작 시 만료된 태스크 정리
            self._cleanup_expired()
            self._progress[task_id] = {
                "task_id": task_id,
                "description": description,
                "total": total_items,
                "current": 0,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "success_count": 0,
                "failed_count": 0,
                "phase": "Phase 1",  # 현재 단계 (Phase 1 / Phase 2)
                "phase1_count": 0,   # Phase 1 성공 건수
                "phase2_count": 0,   # Phase 2 성공 건수
                "current_item": None,
                "error_message": None,
                "items_history": []  # 완료된 항목 히스토리
            }

    def update_progress(self, task_id: str, current: int, current_item: str = None,
                       success: bool = None, error: str = None):
        """진행 상황 업데이트

        Args:
            task_id: 작업 ID
            current: 현재 진행 상황 (인덱스)
            current_item: 현재 처리 중인 항목명
            success: True이면 success_count 증가, False이면 failed_count 증가, None이면 카운트 변경 없음
            error: 에러 메시지
        """
        with self._lock:
            if task_id in self._progress:
                self._progress[task_id]["current"] = current
                self._progress[task_id]["updated_at"] = datetime.utcnow().isoformat()

                if current_item:
                    self._progress[task_id]["current_item"] = current_item

                    # 성공/실패 시 히스토리에 추가
                    if success is not None:
                        self._progress[task_id]["items_history"].append({
                            "item": current_item,
                            "index": current,
                            "success": success,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        if len(self._progress[task_id]["items_history"]) > self._history_limit:
                            self._progress[task_id]["items_history"] = self._progress[task_id]["items_history"][-self._history_limit:]

                if success is True:
                    self._progress[task_id]["success_count"] += 1
                elif success is False:
                    self._progress[task_id]["failed_count"] += 1

                if error:
                    self._progress[task_id]["error_message"] = error

    def set_phase(self, task_id: str, phase: str, reset_counts: bool = False):
        """현재 단계 설정 (Phase 1 / Phase 2)"""
        with self._lock:
            if task_id in self._progress:
                self._progress[task_id]["phase"] = phase
                self._progress[task_id]["updated_at"] = datetime.utcnow().isoformat()
                if reset_counts:
                    # Phase 전환 시 성공 건수 리셋
                    self._progress[task_id]["success_count"] = 0
                    self._progress[task_id]["failed_count"] = 0

    def complete_task(self, task_id: str, status: str = "completed", error: str = None):
        """작업 완료

        Args:
            task_id: 작업 ID
            status: 완료 상태 ('completed' 또는 'failed')
            error: 에러 메시지 (실패 시)
        """
        with self._lock:
            if task_id in self._progress:
                self._progress[task_id]["status"] = status
                self._progress[task_id]["completed_at"] = datetime.utcnow().isoformat()
                self._progress[task_id]["updated_at"] = datetime.utcnow().isoformat()
                if error:
                    self._progress[task_id]["error_message"] = error

    def get_progress(self, task_id: str) -> Optional[dict]:
        """진행 상황 조회"""
        with self._lock:
            return self._progress.get(task_id, None)

    def get_all_progress(self) -> Dict[str, dict]:
        """모든 진행 상황 조회"""
        with self._lock:
            return dict(self._progress)

    def clear_completed(self):
        """완료된 작업 정리"""
        with self._lock:
            self._progress = {
                k: v for k, v in self._progress.items()
                if v["status"] == "running"
            }

    def clear_task(self, task_id: str):
        """특정 작업 제거"""
        with self._lock:
            if task_id in self._progress:
                del self._progress[task_id]


# 전역 인스턴스
progress_tracker = ProgressTracker(history_limit=settings.progress_history_limit)
