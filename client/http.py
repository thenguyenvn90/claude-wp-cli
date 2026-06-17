"""Shared HTTP client for WordPress REST API.

Uses httpx with HTTP Basic Auth (Application Passwords).
All errors are captured and converted to structured JSON.
"""

import base64
import json
from typing import Any, Optional

import httpx


# WordPress sites behind Cloudflare/WAF routinely block non-browser User-Agents
# (httpx's default "python-httpx/...") so the request never reaches /wp-json. A
# browser-like UA survives that — the same fix the kit's wp_push_safe.py applies (_WP_UA).
WP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class WPAPIError(Exception):
    """WordPress REST API error with structured details."""

    def __init__(self, code: str, message: str, http_status: int):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{http_status}] {code}: {message}")


def json_output(
    data: Any,
    *,
    total: Optional[int] = None,
    total_pages: Optional[int] = None,
    page: Optional[int] = None,
) -> str:
    """Format a success response as JSON."""
    result: dict[str, Any] = {"status": "success", "data": data}
    if total is not None:
        result["total"] = total
    if total_pages is not None:
        result["total_pages"] = total_pages
    if page is not None:
        result["page"] = page
    return json.dumps(result, indent=2, default=str)


def error_output(code: str, message: str, http_status: int = 1) -> str:
    """Format an error response as JSON."""
    return json.dumps(
        {"status": "error", "code": code, "message": message, "http_status": http_status},
        indent=2,
    )


class WPClient:
    """Low-level WordPress REST API client."""

    def __init__(self, rest_url: str, username: str = "", password: str = "", timeout: int = 30, *, auth_header: Optional[str] = None):
        self._base_url = rest_url.rstrip("/")
        self._timeout = timeout
        # auth_header (a ready "Basic <token>" value) wins when provided — this is how the
        # kit no-secret sources (.mcp.json / wp-auth.json) hand over credentials without
        # ever exposing username:password. Otherwise build the header from username:password.
        if auth_header:
            authz = auth_header
        else:
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            authz = f"Basic {token}"
        self._headers = {
            "Authorization": authz,
            "Content-Type": "application/json",
            "User-Agent": WP_USER_AGENT,
        }
        self._client = httpx.Client(timeout=self._timeout, headers=self._headers)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _url(self, endpoint: str) -> str:
        return f"{self._base_url}/{endpoint.lstrip('/')}"

    def _handle_error(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                body = resp.json()
                code = body.get("code", "unknown_error")
                message = body.get("message", resp.text[:200])
            except Exception:
                code = "unknown_error"
                message = resp.text[:200]
            raise WPAPIError(code, message, resp.status_code)

    def get(self, endpoint: str, *, params: Optional[dict] = None) -> Any:
        resp = self._client.get(self._url(endpoint), params=params)
        self._handle_error(resp)
        return resp.json()

    def get_list(self, endpoint: str, *, params: Optional[dict] = None) -> tuple[list, int, int]:
        resp = self._client.get(self._url(endpoint), params=params)
        self._handle_error(resp)
        total = int(resp.headers.get("X-WP-Total", 0))
        total_pages = int(resp.headers.get("X-WP-TotalPages", 0))
        return resp.json(), total, total_pages

    def post(self, endpoint: str, *, json: Optional[dict] = None, **kwargs) -> Any:
        resp = self._client.post(self._url(endpoint), json=json, **kwargs)
        self._handle_error(resp)
        return resp.json()

    def post_file(self, endpoint: str, *, file_data: bytes, filename: str, content_type: str) -> Any:
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type,
        }
        resp = self._client.post(self._url(endpoint), headers=headers, content=file_data)
        self._handle_error(resp)
        return resp.json()

    def delete(self, endpoint: str, *, params: Optional[dict] = None) -> Any:
        resp = self._client.delete(self._url(endpoint), params=params)
        self._handle_error(resp)
        return resp.json()

    def request_path(self, method: str, path: str, *, json: Optional[dict] = None,
                     params: Optional[dict] = None) -> Any:
        """Call a path relative to the SITE root (e.g. '/wp-json/rankmath/v1/updateMeta').

        Resource clients use endpoints relative to '.../wp-json/wp/v2'; SEO plugins expose
        routes outside that namespace, so this resolves against the domain root instead.
        """
        site_root = self._base_url.split("/wp-json")[0]
        url = f"{site_root}/{path.lstrip('/')}"
        resp = self._client.request(method.upper(), url, json=json, params=params)
        self._handle_error(resp)
        return resp.json()
