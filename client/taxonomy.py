"""WordPress Taxonomy (Categories & Tags) REST API client."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class TaxonomyClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list_categories(self, *, per_page: int = 100, page: int = 1) -> tuple[list[dict], int, int]:
        return self._client.get_list("categories", params={"per_page": per_page, "page": page})

    def create_category(self, *, name: str, parent_id: Optional[int] = None) -> dict:
        payload: dict[str, Any] = {"name": name}
        if parent_id is not None:
            payload["parent"] = parent_id
        return self._client.post("categories", json=payload)

    def delete_category(self, category_id: int) -> dict:
        return self._client.delete(f"categories/{category_id}", params={"force": "true"})

    def list_tags(self, *, per_page: int = 100, page: int = 1) -> tuple[list[dict], int, int]:
        return self._client.get_list("tags", params={"per_page": per_page, "page": page})

    def create_tag(self, *, name: str) -> dict:
        return self._client.post("tags", json={"name": name})

    def delete_tag(self, tag_id: int) -> dict:
        return self._client.delete(f"tags/{tag_id}", params={"force": "true"})
