from __future__ import annotations

from typing import Literal

from sqlalchemy import func
from sqlalchemy.sql.elements import ClauseElement


TsqueryMode = Literal["web", "plain", "phrase", "strict"]


def build_tsquery(
    query_text: str,
    mode: TsqueryMode = "web",
    config: str | None = None,
    allow_strict: bool = False,
) -> ClauseElement:
    """
    Build a Postgres tsquery expression for SQLAlchemy.
    websearch_to_tsquery is the default; strict is opt-in.
    """
    mode = mode or "web"
    if mode == "strict" and not allow_strict:
        raise ValueError("strict tsquery mode requires allow_strict=True")

    func_map = {
        "web": func.websearch_to_tsquery,
        "plain": func.plainto_tsquery,
        "phrase": func.phraseto_tsquery,
        "strict": func.to_tsquery,
    }
    if mode not in func_map:
        raise ValueError(f"unsupported tsquery mode: {mode}")

    builder = func_map[mode]
    return builder(config, query_text) if config else builder(query_text)
