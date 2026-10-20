from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformConfig:
    """Configuration for one registered LTI platform (Moodle or Open edX)."""
    issuer: str
    client_id: str
    deployment_id: str
    authorization_endpoint: str
    jwks_uri: str
    token_endpoint: str | None = None
    scopes: tuple[str, ...] = ()
    max_age_seconds: int = 600
