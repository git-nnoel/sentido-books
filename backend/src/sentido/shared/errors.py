"""API error type + FastAPI exception handlers.

Convention (skill R7, R8):

- Routes never construct ``HTTPException`` directly. Service code
  (``service.py``) raises :class:`ApiError` (or a domain-defined
  subclass) when it needs to signal a non-success HTTP outcome. The
  registered exception handler translates that into the standard
  response shape ``{"detail": "..."}``.
- Any ``ValueError`` that escapes a service / route is translated to
  HTTP 400 with the value's stringified message as ``detail``. This
  preserves the convention from skill R8 without sprinkling defensive
  ``try/except`` through routes.
- Unhandled exceptions fall through to FastAPI's default 500 handler
  (we deliberately do not register a catch-all here — that would mask
  real bugs).

Error body shape mirrors the plan's contract (§5.1, §5.2): always
``{"detail": "..."}``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Signal an HTTP-shaped error from inside service / orchestration code.

    Carries the desired HTTP status code and a short, user-facing detail
    string. The handler translates instances into a ``JSONResponse`` with
    body ``{"detail": detail}``.

    Domain-specific subclasses (e.g., ``IsbnNotFoundError``) should
    inherit from :class:`ApiError` and pre-fill ``status_code``/``detail``
    in their ``__init__`` so callers can ``raise IsbnNotFoundError()``.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _api_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    # Signature widened to ``Exception`` because FastAPI's
    # ``add_exception_handler`` declares the handler arg as ``Exception``;
    # the runtime type is always :class:`ApiError` here.
    assert isinstance(exc, ApiError)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def _value_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ValueError)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    """Register the project's exception handlers on the FastAPI app.

    Called once from :func:`sentido.main.create_app`.
    """
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(ValueError, _value_error_handler)
