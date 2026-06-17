"""WordPress Users REST API client (admin-only routes)."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient


class UsersClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list(self, *, per_page: int = 20, page: int = 1) -> tuple[list[dict], int, int]:
        return self._client.get_list("users", params={"per_page": per_page, "page": page, "context": "edit"})

    def get(self, user_id: int) -> dict:
        return self._client.get(f"users/{user_id}", params={"context": "edit"})

    def create(self, *, username: str, email: str, password: str,
               roles: Optional[list[str]] = None) -> dict:
        payload: dict[str, Any] = {"username": username, "email": email, "password": password}
        if roles:
            payload["roles"] = roles
        return self._client.post("users", json=payload)

    def update(self, user_id: int, *, email: Optional[str] = None,
               roles: Optional[list[str]] = None, name: Optional[str] = None) -> dict:
        payload: dict[str, Any] = {}
        if email is not None:
            payload["email"] = email
        if roles is not None:
            payload["roles"] = roles
        if name is not None:
            payload["name"] = name
        return self._client.post(f"users/{user_id}", json=payload)

    def delete(self, user_id: int, *, reassign: Optional[int] = None) -> dict:
        # WordPress requires force=true and a reassign target to delete a user.
        params: dict[str, Any] = {"force": "true"}
        if reassign is not None:
            params["reassign"] = reassign
        return self._client.delete(f"users/{user_id}", params=params)
