"""Text normalization helpers."""

import re

_WHITESPACE_RE = re.compile(r"\s+")


def clean_query(text: str) -> str:
    """Collapse whitespace and strip surrounding noise."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def truncate_text(text: str, max_chars: int = 300) -> str:
    """Cut a string to max_chars without cutting mid-word."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    if " " in cut[max_chars - 20 :]:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "..."
