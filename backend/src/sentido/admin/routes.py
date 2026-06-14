"""Admin routes (``/v1/admin/...``).

The router carries ``prefix="/v1/admin"`` and ``dependencies=[Depends(
require_admin)]`` so EVERY admin endpoint added in later tasks (B3+)
inherits bearer-token auth by default. Future endpoints should NOT
re-declare ``require_admin`` per route — that's the whole point of
attaching it here.

Public catalog/search routers do not share this prefix; they each carry
their own full ``/v1/...`` paths. See :mod:`sentido.catalog.routes` for
the convention.

Endpoints land in B3+. This file ships only the router definition.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sentido.shared.auth import require_admin

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
