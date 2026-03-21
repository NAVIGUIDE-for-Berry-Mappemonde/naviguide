"""
NavSecOps — Bearer token authentication dependency.

Expects: Authorization: Bearer <NAVSECOPS_INGEST_SECRET>
The secret is read from the NAVSECOPS_INGEST_SECRET environment variable.
"""

import os

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_security = HTTPBearer()


def verify_navsecops_token(
    credentials: HTTPAuthorizationCredentials = Security(_security),
) -> str:
    """FastAPI dependency — validates the Bearer token against env var."""
    expected = os.getenv("NAVSECOPS_INGEST_SECRET", "").strip()
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="NAVSECOPS_INGEST_SECRET is not configured on the server",
        )
    if credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials.credentials
