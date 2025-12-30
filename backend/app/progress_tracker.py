# backend/app/progress_tracker.py

from typing import Dict, Optional
from datetime import datetime
import threading

class ProgressTracker:
    """데이터 수집 진행 상황 추적"""

    def __init__(self):
        self._progress: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def start_task(self, task_id: str, total_items: int, description: str = ""):
        """작업 시작"""
        with self._lock:
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

                if success is True:
                    self._progress[task_id]["success_count"] += 1
                elif success is False:
                    self._progress[task_id]["failed_count"] += 1

                if error:
                    self._progress[task_id]["error_message"] = error

    def complete_task(self, task_id: str, status: str = "completed"):
        """작업 완료"""
        with self._lock:
            if task_id in self._progress:
                self._progress[task_id]["status"] = status
                self._progress[task_id]["completed_at"] = datetime.utcnow().isoformat()
                self._progress[task_id]["updated_at"] = datetime.utcnow().isoformat()

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
progress_tracker = ProgressTracker()
