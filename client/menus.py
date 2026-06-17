"""WordPress Menus REST API client (/wp/v2/menus + /wp/v2/menu-items)."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class MenusClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list(self) -> list[dict]:
        return self._client.get("menus", params={"context": "edit", "per_page": 100})

    def get(self, menu_id: int) -> dict:
        return self._client.get(f"menus/{menu_id}", params={"context": "edit"})

    def create(self, *, name: str, locations: Optional[list[str]] = None) -> dict:
        payload: dict[str, Any] = {"name": name}
        if locations:
            payload["locations"] = locations
        return self._client.post("menus", json=payload)

    def delete(self, menu_id: int) -> dict:
        return self._client.delete(f"menus/{menu_id}", params={"force": "true"})

    def assign_location(self, menu_id: int, locations: list[str]) -> dict:
        return self._client.post(f"menus/{menu_id}", json={"locations": locations})

    def list_items(self, menu_id: int) -> list[dict]:
        return self._client.get("menu-items", params={"menus": menu_id, "context": "edit", "per_page": 100})

    def add_item(self, *, menu_id: int, title: str, url: Optional[str] = None,
                 object_id: Optional[int] = None, item_type: Optional[str] = None,
                 object_name: Optional[str] = None, parent: Optional[int] = None) -> dict:
        payload: dict[str, Any] = {"menus": menu_id, "title": title, "status": "publish"}
        if url:
            payload["url"] = url
        if item_type:
            payload["type"] = item_type            # custom | post_type | taxonomy
        if object_name:
            payload["object"] = object_name        # e.g. post, page, category
        if object_id is not None:
            payload["object_id"] = object_id
        if parent is not None:
            payload["parent"] = parent
        return self._client.post("menu-items", json=payload)

    def delete_item(self, item_id: int) -> dict:
        return self._client.delete(f"menu-items/{item_id}", params={"force": "true"})
