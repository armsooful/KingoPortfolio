"""
Phase 3-C / Epic C-3: 벤치마크 비교 서비스
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.performance import BenchmarkResult, PerformanceResult


class BenchmarkService:
    """벤치마크 비교"""

    def __init__(self, db: Session):
        self.db = db

    def add_benchmark_result(
        self,
        performance_id: str,
        benchmark_type: str,
        benchmark_code: str,
        benchmark_return: Optional[float],
        performance_return: Optional[float],
    ) -> BenchmarkResult:
        """벤치마크 결과 저장"""
        excess = None
        if benchmark_return is not None and performance_return is not None:
            excess = performance_return - benchmark_return

        result = BenchmarkResult(
            performance_id=performance_id,
            benchmark_type=benchmark_type,
            benchmark_code=benchmark_code,
            benchmark_return=benchmark_return,
            excess_return=excess,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def link_by_performance(
        self,
        performance: PerformanceResult,
        benchmark_type: str,
        benchmark_code: str,
        benchmark_return: Optional[float],
    ) -> BenchmarkResult:
        """성과 결과 기반 벤치마크 결과 생성"""
        return self.add_benchmark_result(
            performance_id=performance.performance_id,
            benchmark_type=benchmark_type,
            benchmark_code=benchmark_code,
            benchmark_return=benchmark_return,
            performance_return=performance.period_return,
        )
