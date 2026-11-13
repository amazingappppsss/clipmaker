"""Development-only login: mint a local token without a Supabase project.

Mounted only when ENABLE_DEV_AUTH=true, which Settings refuses in production. The token is
an ordinary HS256 JWT verified by the same code path as real Supabase tokens.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from clipmaker.api.deps import AppSettings
from clipmaker.core.security import mint_dev_token
from clipmaker.schemas import DevTokenOut, DevTokenRequest

router = APIRouter(prefix="/dev", tags=["dev"])

# Stable namespace so the same email always maps to the same dev user id.
_DEV_NAMESPACE = uuid.UUID("6f1c2a52-3c0e-4f5b-9a57-2b6a8f6f9d11")


@router.post("/token")
def dev_token(body: DevTokenRequest, settings: AppSettings) -> DevTokenOut:
    """Return an access token for a deterministic dev user derived from the email."""
    email = body.email.strip().lower()
    user_id = uuid.uuid5(_DEV_NAMESPACE, email)
    return DevTokenOut(access_token=mint_dev_token(user_id, email, settings), user_id=user_id)
