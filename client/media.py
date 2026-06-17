"""WordPress Media REST API client."""
from __future__ import annotations
import mimetypes
from pathlib import Path
from typing import Optional
from .http import WPClient


class MediaClient:
    def __init__(self, client: WPClient):
        self._client = client

    def list(self, *, media_type: Optional[str] = None, per_page: int = 10, page: int = 1) -> tuple[list[dict], int, int]:
        params: dict = {"per_page": per_page, "page": page}
        if media_type:
            params["media_type"] = media_type
        return self._client.get_list("media", params=params)

    def get(self, media_id: int) -> dict:
        return self._client.get(f"media/{media_id}")

    def upload(self, file_path: str, *, alt_text: Optional[str] = None, caption: Optional[str] = None, title: Optional[str] = None) -> dict:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Media file not found: {file_path}")
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        file_data = path.read_bytes()
        data = self._client.post_file("media", file_data=file_data, filename=path.name, content_type=content_type)
        update_payload: dict = {}
        if alt_text:
            update_payload["alt_text"] = alt_text
        if caption:
            update_payload["caption"] = caption
        if title:
            update_payload["title"] = title
        if update_payload:
            data = self._client.post(f"media/{data['id']}", json=update_payload)
        return data

    def delete(self, media_id: int, *, force: bool = False) -> dict:
        params = {"force": "true"} if force else {}
        return self._client.delete(f"media/{media_id}", params=params)
