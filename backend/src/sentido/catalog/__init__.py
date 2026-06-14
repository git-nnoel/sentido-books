"""Catalog module — books, authors, editions, collections (the core domain).

This module owns the shared persistence schema (per skill M7). Other
modules may import its ORM classes (`BookORM`, `AuthorORM`, etc.) for
queries directly.
"""
