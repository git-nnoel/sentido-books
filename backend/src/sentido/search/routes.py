"""Search routes (``POST /v1/search``).

Convention: this router uses ``prefix=""`` and individual endpoints
carry their own full ``/v1/...`` paths, matching
:mod:`sentido.catalog.routes`. The admin router is the only exception
— see :mod:`sentido.admin.routes`.

Endpoints land in B3+. This file ships only the router definition.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["search"])
