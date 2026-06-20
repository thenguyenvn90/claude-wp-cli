"""WordPress Media REST API client."""
from __future__ import annotations
import mimetypes
from pathlib import Path
from typing import Optional
from .http import WPClient
from .guards import safe_read_bytes

# Explicit map first — mimetypes.guess_type is unreliable for webp/avif on some
# Windows installs and would yield application/octet-stream (which WP rejects).
CONTENT_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    ".avif": "image/avif",
}


def _content_type(path: Path, *, allow_svg: bool = False) -> str:
    ext = path.suffix.lower()
    if ext == ".svg" and not allow_svg:
        # SVG can carry <script>/onload payloads → stored XSS once served from the WP
        # origin. Refuse by default; require an explicit opt-in (CWE-434).
        raise ValueError(
            "SVG upload is disabled (it can carry stored-XSS payloads). "
            "Re-run with --allow-svg if you trust this file."
        )
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
               title: Optional[str] = None, filename: Optional[str] = None, allow_svg: bool = False) -> dict:
        path = Path(file_path)
        content_type = _content_type(path, allow_svg=allow_svg)  # raises on disallowed SVG
        file_bytes = safe_read_bytes(file_path)  # size-capped; raises FileNotFoundError/FileTooLargeError
        data = self._client.post_file("media", file_data=file_bytes,
                                      filename=filename or path.name, content_type=content_type)
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
