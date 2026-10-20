from __future__ import annotations
import secrets
import time
from urllib.parse import urlencode
import jwt
from jwt import PyJWKClient
from .config import PlatformConfig
from .models import LaunchContext
from .store import MemoryTransactionStore

CONTEXT_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/context"
DEPLOYMENT_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
MESSAGE_TYPE_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/message_type"
VERSION_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/version"
RESOURCE_LINK_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
ROLES_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/roles"


class LtiError(ValueError):
    """Invalid or incomplete LTI OIDC login/launch."""


class LtiService:
    def __init__(self, platform: PlatformConfig, redirect_uri: str,
                 transactions: MemoryTransactionStore | None = None):
        self.platform = platform
        self.redirect_uri = redirect_uri
        self.transactions = transactions or MemoryTransactionStore(platform.max_age_seconds)

    def begin_login(self, *, login_hint: str, lti_message_hint: str, iss: str | None = None,
                    target_link_uri: str | None = None, client_id: str | None = None,
                    extra_params: dict[str, str] | None = None) -> str:
        """Create an OIDC login redirect from LMS login-initiation parameters."""
        if not login_hint or not lti_message_hint:
            raise LtiError("login_hint and lti_message_hint are required")
        if iss and iss != self.platform.issuer:
            raise LtiError("Unknown platform issuer")
        if client_id and client_id != self.platform.client_id:
            raise LtiError("Unknown client_id")
        state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.transactions.create(state, nonce)
        params = {
            "scope": "openid", "response_type": "id_token", "response_mode": "form_post",
            "prompt": "none", "client_id": self.platform.client_id,
            "redirect_uri": self.redirect_uri, "login_hint": login_hint,
            "lti_message_hint": lti_message_hint, "state": state, "nonce": nonce,
        }
        if target_link_uri:
            params["target_link_uri"] = target_link_uri
        params.update(extra_params or {})
        return f"{self.platform.authorization_endpoint}?{urlencode(params)}"

    def validate_launch(self, *, state: str, id_token: str) -> LaunchContext:
        transaction = self.transactions.consume(state)
        if not transaction:
            raise LtiError("Unknown, expired, or already-used state")
        try:
            key = PyJWKClient(self.platform.jwks_uri).get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token, key.key, algorithms=["RS256", "ES256"],
                audience=self.platform.client_id, issuer=self.platform.issuer,
                leeway=60, options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]},
            )
        except Exception as exc:
            raise LtiError(f"ID token validation failed: {exc}") from exc
        if claims.get("nonce") != transaction.nonce:
            raise LtiError("Nonce mismatch")
        if time.time() - int(claims.get("iat", 0)) > self.platform.max_age_seconds:
            raise LtiError("ID token is too old")
        if claims.get(VERSION_CLAIM) != "1.3.0":
            raise LtiError("Unsupported LTI version")
        if claims.get(MESSAGE_TYPE_CLAIM) != "LtiResourceLinkRequest":
            raise LtiError("Unsupported LTI message type")
        if claims.get(DEPLOYMENT_CLAIM) != self.platform.deployment_id:
            raise LtiError("Deployment ID mismatch")
        context, link = claims.get(CONTEXT_CLAIM) or {}, claims.get(RESOURCE_LINK_CLAIM) or {}
        return LaunchContext(
            issuer=claims["iss"], client_id=self.platform.client_id,
            deployment_id=claims[DEPLOYMENT_CLAIM], subject=claims["sub"],
            name=claims.get("name"), email=claims.get("email"),
            roles=tuple(claims.get(ROLES_CLAIM, [])), context_id=context.get("id"),
            context_title=context.get("title"), resource_link_id=link.get("id"), claims=claims,
        )
