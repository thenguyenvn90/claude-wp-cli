"""Credential resolution for the publish path — kit no-secret contract.

Resolves a (rest_base, auth_header) pair WITHOUT ever taking a secret on argv.
Resolution order (first hit wins), ported from the kit's `wp_push_safe`:

  1. --site-config PATH : JSON {"wp_base": "...", "auth": "Basic ..."}
  2. sites/<site>/wp-auth.json : same JSON shape
  3. env : CLAUDE_WP_BASE + CLAUDE_WP_AUTH
  4. .mcp.json : the WP MCP server entry matched by host (native http or mcp-remote form)
  5. SiteRegistry : config.yaml + .env.site (username + application password)

`rest_base` is always normalised to the `.../wp-json/wp/v2` collection root so the
existing resource clients (posts, media, comments, ...) work unchanged.

Security guarantees enforced here (the credential trust boundary):
  - HTTPS-only: the Basic-auth header is never returned for a non-HTTPS base
    (http:// is allowed only for localhost). Basic auth is reversible to
    username:app_password, so cleartext transmission would leak it.
  - Exact host match: the .mcp.json resolver matches the requested host by exact
    hostname (urlparse), never a substring — so `--site a.com` can never pull the
    credential of a server configured for `a.com.evil.net`.
  - Host binding: when `--site` looks like a domain, the resolved base URL's host
    must match it — catches the copy-paste "wrong wp_base host" mistake that would
    otherwise forward one site's App Password to another host.
  - Site-id sanitization: `--site` is used in filesystem paths; values containing
    path separators or `..` are rejected before any path is built.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
import os
from urllib.parse import urlparse

from .guards import MissingCredentialsError, warn_if_world_readable

# A site id is used both as a domain key AND a filesystem directory name
# (sites/<site>/...). Restrict it to a safe charset so it cannot traverse.
_SITE_ID_RE = re.compile(r"[A-Za-z0-9._-]+")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _normalise_base(wp_base: str) -> str:
    """Strip a trailing resource segment (e.g. '/posts') down to '.../wp/v2'."""
    b = wp_base.rstrip("/")
    if b.endswith("/wp/v2/posts"):
        b = b[: -len("/posts")]
    return b


def _host_of(url: str) -> str:
    """Lowercased hostname of a URL, or '' if unparseable."""
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _host_eq(host: str, candidate: str | None) -> bool:
    """Exact (case-insensitive) hostname equality — never a substring match."""
    return bool(candidate) and candidate.lower() == host.lower()


def _validate_site_id(site: str) -> None:
    """Reject a --site value that could traverse the filesystem (F3, CWE-22)."""
    if not site or site in (".", "..") or not _SITE_ID_RE.fullmatch(site):
        raise MissingCredentialsError(
            f"invalid --site {site!r}: only letters, digits, '.', '-', '_' are allowed "
            "(no '/', '\\', or '..' path components)."
        )


def _require_https(base: str) -> str:
    """Refuse to hand back a base URL that would send credentials in cleartext (F2).

    http:// is permitted only for localhost (local dev). Everything else must be https://.
    """
    if base.lower().startswith("https://"):
        return base
    if _host_of(base) in _LOCAL_HOSTS:
        return base
    raise MissingCredentialsError(
        f"refusing to send credentials over a non-HTTPS base URL: {base!r}. "
        "Use https:// (http is allowed only for localhost)."
    )


def _assert_host_binding(site: str, base: str) -> None:
    """When --site looks like a domain, the resolved base host must match it (F1 host-binding).

    Catches the project's #1 failure mode: a wp-auth.json whose wp_base points at a
    different host than the site it belongs to, which would forward this site's
    Application Password to the wrong server.
    """
    if not site or "." not in site:
        return  # non-domain site id (e.g. "myblog") — nothing to bind against
    host = _host_of(base)
    s = site.lower()
    if host and not (host == s or host.endswith("." + s) or s.endswith("." + host)):
        raise MissingCredentialsError(
            f"host mismatch: --site={site!r} but wp_base host is {host!r}. Refusing to "
            "send this site's credentials to a different host (check wp_base in wp-auth.json)."
        )


def _load_cfg(path) -> dict:
    """Load + validate a wp-auth JSON config (F12). Raises MissingCredentialsError on
    unreadable/malformed input instead of leaking a raw JSONDecodeError/KeyError."""
    warn_if_world_readable(path)
    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise MissingCredentialsError(f"cannot read wp-auth config {path}: {e}")
    if not isinstance(cfg, dict) or "wp_base" not in cfg:
        raise MissingCredentialsError(
            f"wp-auth config {path} must be a JSON object containing 'wp_base'."
        )
    return cfg


def _auth_from_mcp_json(host: str) -> tuple[str, str]:
    """Read the WP MCP server's Application-Password auth from .mcp.json for `host`.

    Supports both the native remote form ({"url","headers":{"Authorization"}}) and the
    legacy mcp-remote form (auth passed as a `--header` arg). Matches the server by
    EXACT hostname (never substring). Read-only; never prints.
    Returns (rest_base, auth_header) or ('', '').
    """
    if not host:
        return "", ""
    for p in (Path(".mcp.json"), Path.home() / ".claude" / ".mcp.json", Path.home() / ".mcp.json"):
        if not p.is_file():
            continue
        try:
            servers = json.loads(p.read_text(encoding="utf-8")).get("mcpServers", {})
        except (OSError, json.JSONDecodeError):
            continue
        for _name, cfg in servers.items():
            # native remote form: {"url": ..., "headers": {"Authorization": ...}}
            url = str(cfg.get("url", "") or "")
            hdrs = cfg.get("headers", {}) or {}
            if url and _host_eq(host, _host_of(url)) and isinstance(hdrs, dict):
                a = hdrs.get("Authorization") or hdrs.get("authorization")
                if a:
                    return f"https://{host}/wp-json/wp/v2", str(a).strip()
            # mcp-remote form: auth is a `Authorization: ...` arg; require a URL arg
            # whose host EXACTLY matches before trusting the header.
            args = cfg.get("args", []) or []
            arg_url_hosts = [_host_of(str(x)) for x in args if str(x).lower().startswith("http")]
            if not any(_host_eq(host, h) for h in arg_url_hosts):
                continue
            for a in args:
                s = str(a)
                if s.startswith("Authorization:"):
                    return f"https://{host}/wp-json/wp/v2", s.split(":", 1)[1].strip()
    return "", ""


def _auth_from_cfg(cfg: dict) -> str:
    """Basic auth header from a wp-auth cfg dict — a pre-built ``auth`` (``Basic <base64>``),
    or ``username`` + ``app_password``/``password`` (App Password spaces are stripped, so it can
    be pasted exactly as WordPress shows it)."""
    auth = cfg.get("auth")
    if auth:
        return auth
    user = cfg.get("username") or cfg.get("wp_username")
    pw = cfg.get("app_password") or cfg.get("password")
    if user and pw:
        token = base64.b64encode(f"{user}:{pw.replace(' ', '')}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"
    raise MissingCredentialsError(
        'wp-auth.json needs either "auth" (Basic <base64>) or "username" + "app_password"'
    )


def resolve_auth(site: str | None = None, site_config_path: str | None = None) -> tuple[str, str]:
    """Resolve (rest_base, auth_header). Raises MissingCredentialsError if none found.

    All return paths pass through _require_https so credentials are never emitted for a
    non-HTTPS base (localhost excepted).
    """
    if site:
        _validate_site_id(site)  # F3 — before any filesystem path is built

    if site_config_path:
        cfg = _load_cfg(site_config_path)
        return _require_https(_normalise_base(cfg["wp_base"])), _auth_from_cfg(cfg)

    if site:
        candidate = Path("sites") / site / "wp-auth.json"
        if candidate.is_file():
            cfg = _load_cfg(candidate)
            base = _normalise_base(cfg["wp_base"])
            _assert_host_binding(site, base)  # F1 host-binding
            return _require_https(base), _auth_from_cfg(cfg)

    wp_base = os.environ.get("CLAUDE_WP_BASE")
    auth = os.environ.get("CLAUDE_WP_AUTH")
    if wp_base and auth:
        return _require_https(_normalise_base(wp_base)), auth

    if site and "." in site:  # "/" already rejected by _validate_site_id
        mcp_base, mcp_auth = _auth_from_mcp_json(site)
        if mcp_base and mcp_auth:
            return _require_https(mcp_base), mcp_auth

    # Last resort: the wp-cli native config.yaml + .env.site (username/app-password).
    if site:
        try:
            from models.loader import SiteRegistry

            config = SiteRegistry().get_site(site)
            secrets = config.wp_secrets
            if secrets and secrets.wp_username and secrets.wp_app_password.get_secret_value():
                base = config.wordpress.rest_url or f"{config.wordpress.site_url.rstrip('/')}/wp-json/wp/v2"
                base = _normalise_base(base)
                _assert_host_binding(site, base)
                token = base64.b64encode(
                    f"{secrets.wp_username}:{secrets.wp_app_password.get_secret_value()}".encode()
                ).decode()
                return _require_https(base), f"Basic {token}"
        except FileNotFoundError:
            pass

    raise MissingCredentialsError(
        "No WP credentials resolved. Provide one of:\n"
        "  --site-config PATH (JSON: wp_base + auth)\n"
        "  sites/<site>/wp-auth.json\n"
        "  env CLAUDE_WP_BASE + CLAUDE_WP_AUTH\n"
        "  --site DOMAIN (reads the WP MCP auth from .mcp.json)\n"
        "  sites/<site>/config.yaml + .env.site"
    )
