"""Route SEO meta + schema writes to whichever WordPress SEO plugin a site runs.

The kit ships to many buyers — we cannot assume RankMath. This maps title /
description / focus-keyword and JSON-LD schema to RankMath, Yoast, a generic
post-meta fallback, or none. Pure and deterministic: it returns *what* request
to make; the HTTP call happens in the meta/posts client.

Ported from the kit's `scripts/wp_seo_router.py` (behavior parity).

  detect_plugin(namespaces)                          -> 'rankmath'|'yoast'|'generic'
  meta_request(plugin, post_id, title, desc, fks=[]) -> {method,endpoint,payload}|None
  schema_request(plugin, post_id, schema)            -> {method,endpoint,payload}|None
"""

from __future__ import annotations

import json

PLUGINS = {"rankmath", "yoast", "generic", "none"}


def detect_plugin(namespaces) -> str:
    """Guess the SEO plugin from GET /wp-json `namespaces` (or route strings)."""
    ns = " ".join(str(n).lower() for n in (namespaces or []))
    if "rankmath" in ns:
        return "rankmath"
    if "yoast" in ns:
        return "yoast"
    return "generic"


def _fk(focus_keywords) -> str:
    return ", ".join(focus_keywords or [])


def meta_request(plugin, post_id, title, description, focus_keywords=None, post_type="posts"):
    """Build the meta-write request for the given plugin (None when plugin == 'none')."""
    if plugin == "none":
        return None
    if plugin == "rankmath":
        return {
            "method": "POST",
            "endpoint": "/wp-json/rankmath/v1/updateMeta",
            "payload": {
                "objectID": post_id,
                "objectType": "post",
                "meta": {
                    "rank_math_title": title,
                    "rank_math_description": description,
                    "rank_math_focus_keyword": _fk(focus_keywords),
                },
            },
        }
    if plugin == "yoast":
        return {
            "method": "POST",
            "endpoint": f"/wp-json/wp/v2/{post_type}/{post_id}",
            "payload": {
                "meta": {
                    "_yoast_wpseo_title": title,
                    "_yoast_wpseo_metadesc": description,
                    "_yoast_wpseo_focuskw": _fk(focus_keywords),
                }
            },
        }
    if plugin == "generic":
        return {
            "method": "POST",
            "endpoint": f"/wp-json/wp/v2/{post_type}/{post_id}",
            "payload": {"meta": {"_seo_title": title, "_seo_description": description}},
        }
    raise ValueError(f"unknown seo_plugin '{plugin}'; allowed: {sorted(PLUGINS)}")


def schema_request(plugin, post_id, schema, post_type="posts"):
    """Build the JSON-LD schema-write request for the given plugin."""
    if plugin == "none":
        return None
    if plugin == "rankmath":
        return {
            "method": "POST",
            "endpoint": "/wp-json/rankmath/v1/updateSchemas",
            "payload": {"objectID": post_id, "schemas": schema},
        }
    if plugin in ("yoast", "generic"):
        return {
            "method": "POST",
            "endpoint": f"/wp-json/wp/v2/{post_type}/{post_id}",
            "payload": {"meta": {"_schema_jsonld": json.dumps(schema, ensure_ascii=False)}},
        }
    raise ValueError(f"unknown seo_plugin '{plugin}'; allowed: {sorted(PLUGINS)}")
