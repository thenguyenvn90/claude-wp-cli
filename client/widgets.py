"""WordPress Widgets REST API client (/wp/v2/widgets, /sidebars, /widget-types)."""
from __future__ import annotations
from .http import WPClient


class WidgetsClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list_sidebars(self) -> list[dict]:
        return self._client.get("sidebars", params={"context": "edit"})

    def get_sidebar(self, sidebar_id: str) -> dict:
        return self._client.get(f"sidebars/{sidebar_id}", params={"context": "edit"})

    def list_widgets(self) -> list[dict]:
        return self._client.get("widgets", params={"context": "edit"})

    def list_types(self) -> list[dict]:
        return self._client.get("widget-types", params={"context": "edit", "per_page": 100})
