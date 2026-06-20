"""Security-hardening regression tests (audit fixes F1-F17)."""

import base64

import pytest

from client.auth import (
    _validate_site_id, _require_https, _host_eq, _assert_host_binding, _load_cfg,
)
from client.guards import (
    MissingCredentialsError, safe_read_text, safe_read_bytes, FileTooLargeError,
)
from client.http import _redact
from client.media import _content_type
from client.posts import PostsClient
from pathlib import Path


# ---- F3: --site filesystem sanitization -------------------------------------
@pytest.mark.parametrize("bad", ["../../etc", "a/b", "a\\b", "..", ".", ""])
def test_site_id_rejects_traversal(bad):
    with pytest.raises(MissingCredentialsError):
        _validate_site_id(bad)


@pytest.mark.parametrize("good", ["ongboit.com", "my-blog", "site_1", "a.b.c"])
def test_site_id_accepts_safe(good):
    assert _validate_site_id(good) is None


# ---- F2: HTTPS-only credential transmission ---------------------------------
def test_require_https_rejects_http():
    with pytest.raises(MissingCredentialsError):
        _require_https("http://example.com/wp-json/wp/v2")


def test_require_https_allows_localhost_http():
    assert _require_https("http://localhost:8080/wp-json/wp/v2").startswith("http://localhost")


def test_require_https_allows_https():
    assert _require_https("https://example.com/wp-json/wp/v2").startswith("https://")


# ---- F1: exact host match (no substring) ------------------------------------
def test_host_eq_exact_only():
    assert _host_eq("a.com", "a.com") is True
    assert _host_eq("a.com", "a.com.evil.net") is False
    assert _host_eq("a.com", None) is False


def test_host_binding_rejects_mismatch():
    with pytest.raises(MissingCredentialsError):
        _assert_host_binding("ongboit.com", "https://evil.net/wp-json/wp/v2")


def test_host_binding_allows_match_and_subdomain():
    assert _assert_host_binding("ongboit.com", "https://ongboit.com/wp-json/wp/v2") is None
    assert _assert_host_binding("ongboit.com", "https://www.ongboit.com/wp-json/wp/v2") is None


# ---- F12: config load validation --------------------------------------------
def test_load_cfg_rejects_bad_json(tmp_path):
    p = tmp_path / "wp-auth.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(MissingCredentialsError):
        _load_cfg(p)


def test_load_cfg_requires_wp_base(tmp_path):
    p = tmp_path / "wp-auth.json"
    p.write_text('{"auth": "Basic x"}', encoding="utf-8")
    with pytest.raises(MissingCredentialsError):
        _load_cfg(p)


# ---- F7: SVG upload gate -----------------------------------------------------
def test_svg_blocked_by_default():
    with pytest.raises(ValueError):
        _content_type(Path("x.svg"))


def test_svg_allowed_with_flag():
    assert _content_type(Path("x.svg"), allow_svg=True) == "image/svg+xml"


# ---- F6: file-read size cap --------------------------------------------------
def test_safe_read_text_size_cap(tmp_path):
    p = tmp_path / "big.html"
    p.write_text("x" * 100, encoding="utf-8")
    with pytest.raises(FileTooLargeError):
        safe_read_text(p, max_bytes=10)


def test_safe_read_bytes_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        safe_read_bytes(tmp_path / "nope.webp")


# ---- F13: error redaction ----------------------------------------------------
def test_redact_masks_basic_token():
    out = _redact("failed with Authorization: Basic YWRtaW46c2VjcmV0cGFzc3dvcmQ=")
    assert "YWRtaW46" not in out
    assert "Basic ****" in out


# ---- F8 + F17: push_safe stale-edit guard + post-write slug re-verify --------
class _FakeClient:
    """Records POSTs; serves GETs for slug + modified."""
    def __init__(self, slug="my-slug", modified="2026-01-01T00:00:00"):
        self._slug = slug
        self._modified = modified
        self.posted = []

    def get(self, endpoint, *, params=None):
        return {"id": 1, "slug": self._slug, "modified": self._modified}

    def post(self, endpoint, *, json):
        self.posted.append(json)
        return {"id": 1, "modified": self._modified, "link": "x", "status": "draft"}


def test_push_safe_refuses_on_stale_modified():
    c = _FakeClient(modified="2026-02-02T00:00:00")
    pc = PostsClient(c)
    res = pc.push_safe(1, "<p>hi</p>", check_drift_enabled=False,
                       expected_modified="2026-01-01T00:00:00")  # differs from live
    assert res["pushed"] is False
    assert "stale edit" in res["refused"]
    assert c.posted == []  # never wrote


def test_push_safe_writes_when_modified_matches_and_reverifies_slug():
    c = _FakeClient(slug="my-slug", modified="2026-01-01T00:00:00")
    pc = PostsClient(c)
    res = pc.push_safe(1, "<p>hi</p>", check_drift_enabled=False,
                       expected_slug="my-slug", expected_modified="2026-01-01T00:00:00")
    assert res["pushed"] is True
    assert res["slug_verified"] is True
    assert len(c.posted) == 1
