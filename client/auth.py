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
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from .guards import MissingCredentialsError


def _normalise_base(wp_base: str) -> str:
    """Strip a trailing resource segment (e.g. '/posts') down to '.../wp/v2'."""
    b = wp_base.rstrip("/")
    if b.endswith("/wp/v2/posts"):
        b = b[: -len("/posts")]
    return b


def _auth_from_mcp_json(host: str) -> tuple[str, str]:
    """Read the WP MCP server's Application-Password auth from .mcp.json for `host`.

    Supports both the native remote form ({"url","headers":{"Authorization"}}) and the
    legacy mcp-remote form (auth passed as a `--header` arg). Read-only; never prints.
    Returns (rest_base, auth_header) or ('', '').
    """
    if not host:
        return "", ""
    for p in (Path(".mcp.json"), Path.home() / ".claude" / ".mcp.json", Path.home() / ".mcp.json"):
        if not p.is_file():
            continue
        try:
            servers = json.loads(p.read_text(encoding="utf-8")).get("mcpServers", {})
        except Exception:
            continue
        for _name, cfg in servers.items():
            url = str(cfg.get("url", "") or "")
            hdrs = cfg.get("headers", {}) or {}
            if host in url and isinstance(hdrs, dict):
                a = hdrs.get("Authorization") or hdrs.get("authorization")
                if a:
                    return f"https://{host}/wp-json/wp/v2", str(a).strip()
            args = cfg.get("args", []) or []
            blob = " ".join(str(a) for a in args)
            if "wp-json" not in blob or host not in blob:
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
    """Resolve (rest_base, auth_header). Raises MissingCredentialsError if none found."""
    if site_config_path:
        cfg = json.loads(Path(site_config_path).read_text(encoding="utf-8"))
        return _normalise_base(cfg["wp_base"]), _auth_from_cfg(cfg)

    if site:
        candidate = Path("sites") / site / "wp-auth.json"
        if candidate.is_file():
            cfg = json.loads(candidate.read_text(encoding="utf-8"))
            return _normalise_base(cfg["wp_base"]), _auth_from_cfg(cfg)

    wp_base = os.environ.get("CLAUDE_WP_BASE")
    auth = os.environ.get("CLAUDE_WP_AUTH")
    if wp_base and auth:
        return _normalise_base(wp_base), auth

    if site and "." in site and "/" not in site:
        mcp_base, mcp_auth = _auth_from_mcp_json(site)
        if mcp_base and mcp_auth:
            return mcp_base, mcp_auth

    # Last resort: the wp-cli native config.yaml + .env.site (username/app-password).
    if site:
        try:
            from models.loader import SiteRegistry

            config = SiteRegistry().get_site(site)
            secrets = config.wp_secrets
            if secrets and secrets.wp_username and secrets.wp_app_password.get_secret_value():
                base = config.wordpress.rest_url or f"{config.wordpress.site_url.rstrip('/')}/wp-json/wp/v2"
                token = base64.b64encode(
                    f"{secrets.wp_username}:{secrets.wp_app_password.get_secret_value()}".encode()
                ).decode()
                return _normalise_base(base), f"Basic {token}"
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
