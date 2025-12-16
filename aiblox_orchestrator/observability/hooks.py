"""Observability hooks (tracing/MLflow) placeholder implementations."""

from __future__ import annotations

import contextlib
from typing import Iterator


@contextlib.contextmanager
def trace_span(name: str) -> Iterator[None]:
    """No-op tracing span placeholder."""
    yield
