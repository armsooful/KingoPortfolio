"""
시뮬레이션 캐시 서비스
동일 요청에 대해 결과를 재사용하기 위한 캐싱 로직
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

from sqlalchemy.orm import Session

from app.models.portfolio import SimulationCache

logger = logging.getLogger(__name__)


def canonicalize_request(request_data: Dict[str, Any]) -> str:
    """
    요청 데이터를 정규화하여 일관된 해시를 생성할 수 있도록 함

    - 키를 정렬
    - 불필요한 필드 제거 (예: 타임스탬프)
    - JSON 문자열로 변환
    """
    def sort_dict(d):
        if isinstance(d, dict):
            return {k: sort_dict(v) for k, v in sorted(d.items())}
        elif isinstance(d, list):
            return [sort_dict(item) for item in d]
        else:
            return d

    # 캐시에 영향을 주지 않아야 하는 필드 제거
    excluded_keys = {'timestamp', 'request_id', 'user_id'}
    filtered_data = {k: v for k, v in request_data.items() if k not in excluded_keys}

    sorted_data = sort_dict(filtered_data)
    return json.dumps(sorted_data, ensure_ascii=False, separators=(',', ':'))


def generate_request_hash(request_type: str, request_data: Dict[str, Any]) -> str:
    """
    요청에 대한 SHA-256 해시 생성

    Args:
        request_type: 요청 유형 (backtest, compare 등)
        request_data: 요청 파라미터

    Returns:
        64자리 SHA-256 해시 문자열
    """
    canonical = canonicalize_request(request_data)
    hash_input = f"{request_type}:{canonical}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def get_cached_result(
    db: Session,
    request_hash: str
) -> Optional[Dict[str, Any]]:
    """
    캐시에서 결과 조회

    Args:
        db: DB 세션
        request_hash: 요청 해시

    Returns:
        캐시된 결과 데이터 또는 None
    """
    cache_entry = db.query(SimulationCache).filter(
        SimulationCache.request_hash == request_hash
    ).first()

    if cache_entry:
        # 만료 확인
        if cache_entry.expires_at and cache_entry.expires_at < datetime.utcnow():
            logger.info(f"Cache expired for hash {request_hash[:8]}...")
            db.delete(cache_entry)
            db.commit()
            return None

        # 히트 카운트 증가 및 접근 시간 갱신
        cache_entry.hit_count += 1
        cache_entry.last_accessed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Cache HIT for hash {request_hash[:8]}... (hits: {cache_entry.hit_count})")
        return cache_entry.result_data

    logger.info(f"Cache MISS for hash {request_hash[:8]}...")
    return None


def save_to_cache(
    db: Session,
    request_hash: str,
    request_type: str,
    request_params: Dict[str, Any],
    result_data: Dict[str, Any],
    ttl_days: Optional[int] = 7
) -> SimulationCache:
    """
    결과를 캐시에 저장

    Args:
        db: DB 세션
        request_hash: 요청 해시
        request_type: 요청 유형
        request_params: 원본 요청 파라미터
        result_data: 저장할 결과 데이터
        ttl_days: 캐시 유효 기간 (일), None이면 무기한

    Returns:
        생성된 캐시 엔트리
    """
    expires_at = None
    if ttl_days:
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

    cache_entry = SimulationCache(
        request_hash=request_hash,
        request_type=request_type,
        request_params=request_params,
        result_data=result_data,
        expires_at=expires_at
    )

    db.add(cache_entry)
    db.commit()
    db.refresh(cache_entry)

    logger.info(f"Cached result for hash {request_hash[:8]}... (type: {request_type})")
    return cache_entry


def get_or_compute(
    db: Session,
    request_type: str,
    request_params: Dict[str, Any],
    compute_fn: callable,
    ttl_days: Optional[int] = 7
) -> tuple[Dict[str, Any], str, bool]:
    """
    캐시에서 결과를 조회하거나, 없으면 계산 후 캐시에 저장

    Args:
        db: DB 세션
        request_type: 요청 유형
        request_params: 요청 파라미터
        compute_fn: 결과를 계산하는 함수 (인자 없이 호출)
        ttl_days: 캐시 유효 기간 (일)

    Returns:
        (결과 데이터, request_hash, cache_hit 여부) 튜플
    """
    request_hash = generate_request_hash(request_type, request_params)

    # 캐시 조회
    cached_result = get_cached_result(db, request_hash)
    if cached_result is not None:
        return cached_result, request_hash, True

    # 결과 계산
    result = compute_fn()

    # 캐시에 저장
    try:
        save_to_cache(db, request_hash, request_type, request_params, result, ttl_days)
    except Exception as e:
        # 중복 해시 등 예외 발생 시 로깅만 하고 진행
        logger.warning(f"Failed to cache result: {e}")

    return result, request_hash, False


def cleanup_expired_cache(db: Session) -> int:
    """
    만료된 캐시 엔트리 삭제

    Returns:
        삭제된 엔트리 수
    """
    deleted = db.query(SimulationCache).filter(
        SimulationCache.expires_at < datetime.utcnow()
    ).delete()
    db.commit()

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} expired cache entries")

    return deleted
