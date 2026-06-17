"""Tests for the shared HTTP client — auth header + WAF-surviving User-Agent."""

from client.http import WPClient, WP_USER_AGENT


def test_client_sets_browser_user_agent():
    # WAF survival: a non-browser UA gets blocked by Cloudflare before reaching /wp-json.
    c = WPClient(rest_url="https://example.com/wp-json/wp/v2", auth_header="Basic x")
    assert c._headers["User-Agent"] == WP_USER_AGENT
    assert "Mozilla/5.0" in WP_USER_AGENT


def test_auth_header_takes_precedence_over_userpass():
    c = WPClient(rest_url="https://e.com/wp-json/wp/v2", username="u", password="p",
                 auth_header="Basic PROVIDED")
    assert c._headers["Authorization"] == "Basic PROVIDED"


def test_auth_built_from_userpass_when_no_header():
    c = WPClient(rest_url="https://e.com/wp-json/wp/v2", username="u", password="p")
    assert c._headers["Authorization"].startswith("Basic ")
