"""Auth module — JWT validation, tenant extraction, RBAC."""

import os
from typing import Any

import structlog
from fastapi import HTTPException, Request

logger = structlog.get_logger(__name__)

# Roles in ascending privilege order
ROLES = ("viewer", "developer", "project_admin", "risk_officer", "compliance_officer", "admin")

AUTH_DISABLED = os.environ.get("HARBOR_AUTH_DISABLED", "false").lower() == "true"
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_REGION = os.environ.get("AWS_REGION", "us-east-1")

# JWKS cache (loaded once per Lambda cold start)
_jwks: dict[str, Any] | None = None


def _get_jwks() -> dict[str, Any]:
    """Fetch Cognito JWKS (cached)."""
    global _jwks  # noqa: PLW0603
    if _jwks is not None:
        return _jwks
    import httpx

    url = (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )
    resp = httpx.get(url, timeout=5.0)
    resp.raise_for_status()
    _jwks = resp.json()
    return _jwks


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a Cognito JWT."""
    import jwt
    from jwt import PyJWKClient

    jwks_url = (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )
    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)

    claims: dict[str, Any] = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}",
        options={"verify_aud": False},  # M2M tokens have no aud
    )
    return claims


class AuthContext:
    """Authenticated user/service context."""

    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        role: str,
        email: str = "",
    ) -> None:
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
        self.email = email

    def has_role(self, required: str) -> bool:
        """Check if user has at least the required role level."""
        if self.role not in ROLES or required not in ROLES:
            return False
        return ROLES.index(self.role) >= ROLES.index(required)


# Dev bypass context
_DEV_CONTEXT = AuthContext(
    tenant_id="dev-tenant-000000000000",
    user_id="dev-user",
    role="admin",
    email="dev@harbor.local",
)


def get_auth_context(request: Request) -> AuthContext:
    """Extract auth context from request. FastAPI dependency."""
    if AUTH_DISABLED:
        return _DEV_CONTEXT

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header[7:]
    try:
        claims = _decode_token(token)
    except Exception as e:
        logger.warning("auth_failed", error=str(e))
        raise HTTPException(401, "Invalid token")

    # Extract tenant_id from custom attribute or client metadata
    tenant_id = claims.get("custom:tenant_id", "")
    if not tenant_id:
        # For M2M tokens, tenant_id may be in scope or client metadata
        tenant_id = claims.get("client_id", "unknown")

    return AuthContext(
        tenant_id=tenant_id,
        user_id=claims.get("sub", ""),
        role=claims.get("custom:role", "viewer"),
        email=claims.get("email", ""),
    )


def require_role(ctx: AuthContext, role: str) -> None:
    """Raise 403 if user doesn't have the required role."""
    if not ctx.has_role(role):
        raise HTTPException(403, f"Requires role: {role}")
