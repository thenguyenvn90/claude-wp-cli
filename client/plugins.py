"""WordPress Plugins REST API client (admin-only routes)."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class PluginsClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list(self, *, status: Optional[str] = None) -> list[dict]:
        params: dict[str, Any] = {"context": "edit"}
        if status:
            params["status"] = status  # active | inactive
        return self._client.get("plugins", params=params)

    def get(self, plugin: str) -> dict:
        """plugin = folder/file slug without .php, e.g. 'code-block-pro/code-block-pro'."""
        return self._client.get(f"plugins/{plugin}", params={"context": "edit"})

    def set_status(self, plugin: str, status: str) -> dict:
        """status: active | inactive."""
        return self._client.post(f"plugins/{plugin}", json={"status": status})

    def install(self, slug: str, *, activate: bool = False) -> dict:
        """Install from the WordPress.org directory by `slug` (e.g. 'classic-editor')."""
        payload: dict[str, Any] = {"slug": slug}
        if activate:
            payload["status"] = "active"
        return self._client.post("plugins", json=payload)

    def delete(self, plugin: str) -> dict:
        return self._client.delete(f"plugins/{plugin}")
