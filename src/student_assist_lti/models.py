from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LaunchContext:
    issuer: str
    client_id: str
    deployment_id: str
    subject: str
    name: str | None = None
    email: str | None = None
    roles: tuple[str, ...] = ()
    context_id: str | None = None
    context_title: str | None = None
    resource_link_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)
