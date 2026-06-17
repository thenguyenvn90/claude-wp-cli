"""WordPress Comments REST API client."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class CommentsClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list(self, *, status: Optional[str] = None, post: Optional[int] = None,
             per_page: int = 20, page: int = 1) -> tuple[list[dict], int, int]:
        params: dict[str, Any] = {"per_page": per_page, "page": page, "context": "edit"}
        if status:
            params["status"] = status  # approve | hold | spam | trash
        if post:
            params["post"] = post
        return self._client.get_list("comments", params=params)

    def get(self, comment_id: int) -> dict:
        return self._client.get(f"comments/{comment_id}", params={"context": "edit"})

    def set_status(self, comment_id: int, status: str) -> dict:
        """status: approved | hold | spam (use delete for trash/remove)."""
        return self._client.post(f"comments/{comment_id}", json={"status": status})

    def create(self, *, post: int, content: str, parent: Optional[int] = None) -> dict:
        payload: dict[str, Any] = {"post": post, "content": content}
        if parent:
            payload["parent"] = parent
        return self._client.post("comments", json=payload)

    def delete(self, comment_id: int, *, force: bool = False) -> dict:
        params = {"force": "true"} if force else {}
        return self._client.delete(f"comments/{comment_id}", params=params)
