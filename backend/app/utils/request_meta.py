"""
Admin request metadata helpers.
"""

import uuid
from typing import Dict, Optional

from fastapi import HTTPException, Request, status


def request_meta(require_idempotency: bool = False):
    """Inject request_id/idempotency_key from headers."""

    async def _get_meta(request: Request) -> Dict[str, Optional[str]]:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        idempotency_key = request.headers.get("x-idempotency-key")
        if require_idempotency and not idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="idempotency_key is required",
            )
        return {"request_id": request_id, "idempotency_key": idempotency_key}

    return _get_meta


async def require_idempotency(request: Request) -> None:
    """Enforce idempotency key on write requests."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not request.headers.get("x-idempotency-key"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="idempotency_key is required",
            )
