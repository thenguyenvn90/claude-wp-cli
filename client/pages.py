"""WordPress Pages REST API client."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class PagesClient:
    def __init__(self, client: WPClient, default_status: str = "draft"):
        self._client = client
        self._default_status = default_status

    def list(self, *, status: str = "any", per_page: int = 10, page: int = 1) -> tuple[list[dict], int, int]:
        return self._client.get_list("pages", params={"status": status, "per_page": per_page, "page": page})

    def get(self, page_id: int) -> dict:
        return self._client.get(f"pages/{page_id}")

    def create(self, *, title: str, content: str, status: Optional[str] = None, parent_id: Optional[int] = None, template: Optional[str] = None, meta: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {"title": title, "content": content, "status": status or self._default_status}
        if parent_id is not None:
            payload["parent"] = parent_id
        if template is not None:
            payload["template"] = template
        if meta:
            payload["meta"] = meta
        return self._client.post("pages", json=payload)

    def update(self, page_id: int, *, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None, parent_id: Optional[int] = None, template: Optional[str] = None, meta: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if status is not None:
            payload["status"] = status
        if parent_id is not None:
            payload["parent"] = parent_id
        if template is not None:
            payload["template"] = template
        if meta is not None:
            payload["meta"] = meta
        return self._client.post(f"pages/{page_id}", json=payload)

    def delete(self, page_id: int, *, force: bool = False) -> dict:
        params = {"force": "true"} if force else {}
        return self._client.delete(f"pages/{page_id}", params=params)
