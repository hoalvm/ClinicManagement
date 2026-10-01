"""Phone-number normalization shared by API and legacy Admin flows."""

from __future__ import annotations

import re


def normalize_phone(value: str | None) -> str | None:
    """Remove formatting whitespace while preserving an optional leading ``+``.

    Users commonly paste numbers such as ``090 123 4567``.  Persisting a
    canonical value makes exact lookup reliable without changing the number's
    country-code semantics.
    """

    if value is None:
        return None
    normalized = re.sub(r"\s+", "", str(value)).strip()
    return normalized or None
