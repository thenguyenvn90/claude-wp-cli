"""WordPress Search REST API client (/wp/v2/search)."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class SearchClient:
    def __init__(self, client: WPClient):
        self._client = client

    def query(self, term: str, *, search_type: Optional[str] = None,
              subtype: Optional[str] = None, per_page: int = 10, page: int = 1) -> tuple[list[dict], int, int]:
        params: dict[str, Any] = {"search": term, "per_page": per_page, "page": page}
        if search_type:
            params["type"] = search_type  # post | term | post-format
        if subtype:
            params["subtype"] = subtype
        return self._client.get_list("search", params=params)
