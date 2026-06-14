"""Compatibility shim — the real test config lives at ``backend/conftest.py``.

This file is retained because pytest still discovers it during
collection under ``tests/``. All environment bootstrap and shared
fixtures (``test_engine``, ``test_session``, ``admin_token``) moved up
to the repo-rootdir conftest in B4 so they are visible to module-level
test directories under ``src/sentido/<module>/tests/`` as well.
"""

from __future__ import annotations
