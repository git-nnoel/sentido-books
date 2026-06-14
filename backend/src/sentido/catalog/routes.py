"""Public catalog routes (books, authors, collections).

Convention: this router uses ``prefix=""`` and individual endpoints
carry their own full ``/v1/...`` paths (e.g. ``/v1/books/{slug}``).
The same convention is used in :mod:`sentido.search.routes`. The admin
router is the only exception — it owns ``prefix="/v1/admin"`` so the
``require_admin`` dependency can be applied once at the router level
to every admin endpoint.

Endpoints land in B3+. This file ships only the router definition so
``main.py`` can mount it.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["catalog"])
