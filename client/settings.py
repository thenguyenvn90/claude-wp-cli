"""WordPress Settings REST API client (/wp/v2/settings — a singleton object).

Only the options WordPress (and plugins) expose via the settings endpoint are
readable/writable here; arbitrary wp_options are not exposed by core REST.
"""
from __future__ import annotations
from typing import Any
from .http import WPClient


class SettingsClient:
    def __init__(self, client: WPClient):
        self._client = client

    def get(self) -> dict:
        return self._client.get("settings")

    def get_one(self, key: str) -> Any:
        return self.get().get(key)

    def update(self, values: dict) -> dict:
        return self._client.post("settings", json=values)
