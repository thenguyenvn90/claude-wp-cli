"""WordPress Media REST API client."""
from __future__ import annotations
import mimetypes
from pathlib import Path
from typing import Optional
from .http import WPClient

# Explicit map first — mimetypes.guess_type is unreliable for webp/avif on some
# Windows installs and would yield application/octet-stream (which WP rejects).
CONTENT_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    ".avif": "image/avif",
}


def _content_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in CONTENT_TYPES:
        return CONTENT_TYPES[ext]
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"


class MediaClient:
    def __init__(self, client: WPClient, *, post_type: str = "posts"):
        self._client = client
        self._post_type = post_type

    def list(self, *, media_type: Optional[str] = None, per_page: int = 10, page: int = 1) -> tuple[list[dict], int, int]:
        params: dict = {"per_page": per_page, "page": page}
        if media_type:
            params["media_type"] = media_type
        return self._client.get_list("media", params=params)

    def get(self, media_id: int) -> dict:
        return self._client.get(f"media/{media_id}")

    def upload(self, file_path: str, *, alt_text: Optional[str] = None, caption: Optional[str] = None,
               title: Optional[str] = None, filename: Optional[str] = None) -> dict:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Media file not found: {file_path}")
        data = self._client.post_file("media", file_data=path.read_bytes(),
                                      filename=filename or path.name, content_type=_content_type(path))
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

    def set_featured(self, post_id: int, media_id: int) -> dict:
        """Set a post's featured image (hero) to the given media id."""
        return self._client.post(f"{self._post_type}/{post_id}", json={"featured_media": media_id})

    def delete(self, media_id: int, *, force: bool = False) -> dict:
        params = {"force": "true"} if force else {}
        return self._client.delete(f"media/{media_id}", params=params)
