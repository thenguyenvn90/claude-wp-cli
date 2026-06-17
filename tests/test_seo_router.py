"""Unit tests for the SEO plugin router (parity with legacy wp_seo_router)."""

import pytest

from client.seo_router import detect_plugin, meta_request, schema_request


def test_detect_rankmath():
    assert detect_plugin(["rankmath/v1", "wp/v2"]) == "rankmath"


def test_detect_yoast():
    assert detect_plugin(["yoast/v1", "wp/v2"]) == "yoast"


def test_detect_generic_fallback():
    assert detect_plugin(["wp/v2", "oembed/1.0"]) == "generic"


def test_detect_empty_is_generic():
    assert detect_plugin([]) == "generic"


def test_meta_none_returns_none():
    assert meta_request("none", 1, "t", "d") is None


def test_meta_rankmath_payload_and_focus_join():
    req = meta_request("rankmath", 42, "Title", "Desc", ["a", "b"])
    assert req["endpoint"] == "/wp-json/rankmath/v1/updateMeta"
    meta = req["payload"]["meta"]
    assert meta["rank_math_title"] == "Title"
    assert meta["rank_math_focus_keyword"] == "a, b"
    assert req["payload"]["objectID"] == 42


def test_meta_yoast_uses_post_endpoint_and_meta_keys():
    req = meta_request("yoast", 7, "T", "D", ["kw"])
    assert req["endpoint"] == "/wp-json/wp/v2/posts/7"
    assert req["payload"]["meta"]["_yoast_wpseo_focuskw"] == "kw"


def test_meta_generic_minimal_keys():
    req = meta_request("generic", 9, "T", "D")
    assert req["payload"]["meta"] == {"_seo_title": "T", "_seo_description": "D"}


def test_meta_unknown_plugin_raises():
    with pytest.raises(ValueError):
        meta_request("bogus", 1, "t", "d")


def test_schema_rankmath_uses_updateschemas():
    req = schema_request("rankmath", 5, {"@type": "FAQPage"})
    assert req["endpoint"] == "/wp-json/rankmath/v1/updateSchemas"
    assert req["payload"]["schemas"] == {"@type": "FAQPage"}


def test_schema_yoast_stores_jsonld_meta():
    req = schema_request("yoast", 5, {"@type": "Article"})
    assert "_schema_jsonld" in req["payload"]["meta"]
    assert "Article" in req["payload"]["meta"]["_schema_jsonld"]


def test_schema_none_returns_none():
    assert schema_request("none", 5, {}) is None
