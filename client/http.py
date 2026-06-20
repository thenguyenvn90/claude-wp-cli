"""Shared HTTP client for WordPress REST API.

Uses httpx with HTTP Basic Auth (Application Passwords).
All errors are captured and converted to structured JSON.
"""

import base64
import json
import re
import time
from typing import Any, Optional

import httpx


# WordPress sites behind Cloudflare/WAF routinely block non-browser User-Agents
# (httpx's default "python-httpx/...") so the request never reaches /wp-json. A
# browser-like UA survives that — the same fix the kit's wp_push_safe.py applies (_WP_UA).
WP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Cap the response body we will parse — a hostile/compromised endpoint could otherwise
# return a multi-GB body and exhaust memory (CWE-400).
MAX_RESPONSE_BYTES = 25 * 1024 * 1024  # 25 MB

# Transient upstream statuses worth a small bounded retry with backoff.
_RETRY_STATUS = {429, 502, 503, 504}
_MAX_RETRIES = 2

# Mask any Basic-auth token that might surface in an error body/message (CWE-532).
_SECRET_RE = re.compile(r"Basic\s+[A-Za-z0-9+/=]{8,}", re.IGNORECASE)


def _redact(text: str) -> str:
    return _SECRET_RE.sub("Basic ****", text or "")


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
        # trust_env=False: ignore HTTP(S)_PROXY / NO_PROXY / .netrc so a hostile proxy
        # env var cannot route the Basic-auth header through an attacker (CWE-918).
        # follow_redirects=False: never replay the Authorization header to a redirected
        # (possibly cross-host) URL.
        self._client = httpx.Client(
            timeout=self._timeout, headers=self._headers,
            trust_env=False, follow_redirects=False,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _url(self, endpoint: str) -> str:
        return f"{self._base_url}/{endpoint.lstrip('/')}"

    def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Issue a request with a bounded retry + backoff on transient upstream errors."""
        resp = None
        for attempt in range(_MAX_RETRIES + 1):
            resp = self._client.request(method.upper(), url, **kwargs)
            if resp.status_code in _RETRY_STATUS and attempt < _MAX_RETRIES:
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else float(2 ** attempt)
                except ValueError:
                    wait = float(2 ** attempt)
                time.sleep(min(wait, 10.0))
                continue
            return resp
        return resp

    def _handle_error(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                body = resp.json()
                code = body.get("code", "unknown_error")
                message = body.get("message", "")
            except Exception:
                code = "unknown_error"
                message = ""
            if not message:
                # Don't echo a raw WAF/HTML error body (info disclosure) — summarise it.
                message = f"HTTP {resp.status_code} (non-JSON body, {len(resp.content)} bytes)"
            raise WPAPIError(code, _redact(message)[:300], resp.status_code)

    def _finish(self, resp: httpx.Response) -> Any:
        """Shared post-flight: error check, size guard, then parse JSON."""
        self._handle_error(resp)
        if len(resp.content) > MAX_RESPONSE_BYTES:
            raise WPAPIError("response_too_large",
                             f"response body exceeds {MAX_RESPONSE_BYTES} bytes", resp.status_code)
        return resp.json()

    def get(self, endpoint: str, *, params: Optional[dict] = None) -> Any:
        return self._finish(self._send("GET", self._url(endpoint), params=params))

    def get_list(self, endpoint: str, *, params: Optional[dict] = None) -> tuple[list, int, int]:
        resp = self._send("GET", self._url(endpoint), params=params)
        data = self._finish(resp)
        total = int(resp.headers.get("X-WP-Total", 0))
        total_pages = int(resp.headers.get("X-WP-TotalPages", 0))
        return data, total, total_pages

    def post(self, endpoint: str, *, json: Optional[dict] = None, **kwargs) -> Any:
        return self._finish(self._send("POST", self._url(endpoint), json=json, **kwargs))

    def post_file(self, endpoint: str, *, file_data: bytes, filename: str, content_type: str) -> Any:
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type,
        }
        return self._finish(self._send("POST", self._url(endpoint), headers=headers, content=file_data))

    def delete(self, endpoint: str, *, params: Optional[dict] = None) -> Any:
        return self._finish(self._send("DELETE", self._url(endpoint), params=params))

    def request_path(self, method: str, path: str, *, json: Optional[dict] = None,
                     params: Optional[dict] = None) -> Any:
        """Call a path relative to the SITE root (e.g. '/wp-json/rankmath/v1/updateMeta').

        Resource clients use endpoints relative to '.../wp-json/wp/v2'; SEO plugins expose
        routes outside that namespace, so this resolves against the domain root instead.
        """
        site_root = self._base_url.split("/wp-json")[0]
        url = f"{site_root}/{path.lstrip('/')}"
        return self._finish(self._send(method, url, json=json, params=params))
