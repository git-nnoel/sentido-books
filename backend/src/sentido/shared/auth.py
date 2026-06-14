"""Admin bearer-token guard (FastAPI dependency).

Plan §5.2 / D3 — v1 has no user accounts. A single static bearer token
loaded from ``ADMIN_TOKEN`` gates every admin endpoint. Missing,
malformed, or wrong tokens all return ``401 {"detail": "unauthorized"}``
per the plan's exact wording.

Wired at the admin router level (``admin.routes.router``) so every
admin endpoint added in later tasks inherits the dependency by default
— specialist tasks never need to remember to add it per-endpoint.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header

from sentido.shared.config import get_settings
from sentido.shared.errors import ApiError

_BEARER_PREFIX = "Bearer "


async def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Reject the request unless ``Authorization: Bearer <ADMIN_TOKEN>`` matches.

    Constant-time comparison via :func:`secrets.compare_digest` to avoid
    leaking token bytes through response-time differences.

    Raises:
        ApiError: 401 ``"unauthorized"`` when the header is missing, the
            scheme is not ``Bearer``, or the token does not match the
            configured ``ADMIN_TOKEN``.
    """
    if authorization is None or not authorization.startswith(_BEARER_PREFIX):
        raise ApiError(401, "unauthorized")

    presented = authorization[len(_BEARER_PREFIX):]
    expected = get_settings().ADMIN_TOKEN

    if not secrets.compare_digest(presented, expected):
        raise ApiError(401, "unauthorized")
