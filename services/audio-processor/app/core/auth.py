"""Auth0 JWT verification dependency."""

import urllib.request
import json
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _get_jwks() -> dict:
    settings = get_settings()
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def verify_token(token: str) -> dict:
    settings = get_settings()
    jwks = _get_jwks()
    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Require a valid Auth0 JWT. Returns the decoded payload."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return verify_token(credentials.credentials)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[dict]:
    """Return decoded JWT payload if token present, else None (guest allowed)."""
    if not credentials:
        return None
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None
