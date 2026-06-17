"""SEO meta read-modify-write with focus-keyword MERGE, routed per SEO plugin.

Parity with the kit's `wp_meta_push`: a refresh that changes a SERP-snippet fact must
update the meta too, and focus keywords must MERGE (never clobber a tuned set). Routing
(RankMath / Yoast / generic) is delegated to `seo_router`.

Critical safety rule (learned live): some sites expose RankMath's `updateMeta` but NOT
`getMeta`, and `rank_math_*` are not in the REST `meta` object — so existing focus
keywords are UNREADABLE. In that case `--focus-add` (merge) is SKIPPED with a warning
rather than written, because writing only the new keywords would clobber the tuned set.
Only `--focus-set` (explicit replace) writes when current state is unreadable. Likewise,
title/description fields are only written when provided or readable, so a partial update
never wipes an unset field.
"""

from __future__ import annotations

from typing import Optional

from .http import WPClient, WPAPIError
from . import seo_router


# logical-field -> per-plugin payload meta key
_KEYS = {
    "rankmath": {"title": "rank_math_title", "desc": "rank_math_description",
                 "focus": "rank_math_focus_keyword"},
    "yoast": {"title": "_yoast_wpseo_title", "desc": "_yoast_wpseo_metadesc",
              "focus": "_yoast_wpseo_focuskw"},
    "generic": {"title": "_seo_title", "desc": "_seo_description"},
}


def _split_focus(value: str) -> list[str]:
    return [k.strip() for k in (value or "").split(",") if k.strip()]


def _merge_focus(existing: list[str], add: list[str]) -> list[str]:
    """Union preserving order; case-insensitive dedupe."""
    seen, out = set(), []
    for kw in [*existing, *add]:
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            out.append(kw)
    return out


class MetaClient:
    def __init__(self, client: WPClient, *, post_type: str = "posts"):
        self._client = client
        self._post_type = post_type

    def get_meta(self, post_id: int, *, plugin: str) -> dict:
        """Return {title, description, focus_keywords[], readable, focus_readable}.

        `readable` is False when the plugin's stored meta cannot be read back (e.g. RankMath
        getMeta absent); `focus_readable` is False additionally for plugins with no readable
        focus keyword. Callers must not clobber fields that aren't readable.
        """
        if plugin == "rankmath":
            try:
                data = self._client.request_path(
                    "POST", "/wp-json/rankmath/v1/getMeta",
                    json={"objectID": post_id, "objectType": "post"},
                )
                meta = data if isinstance(data, dict) else {}
                return {"title": meta.get("rank_math_title", ""),
                        "description": meta.get("rank_math_description", ""),
                        "focus_keywords": _split_focus(meta.get("rank_math_focus_keyword", "")),
                        "readable": True, "focus_readable": True}
            except WPAPIError:
                # getMeta route absent — current RankMath meta is UNREADABLE.
                return {"title": "", "description": "", "focus_keywords": [],
                        "readable": False, "focus_readable": False}

        # Yoast / generic store in post meta (when registered in REST).
        post = self._client.get(f"{self._post_type}/{post_id}",
                                params={"context": "edit", "_fields": "meta"})
        meta = post.get("meta") or {}
        if plugin == "yoast":
            return {"title": meta.get("_yoast_wpseo_title", ""),
                    "description": meta.get("_yoast_wpseo_metadesc", ""),
                    "focus_keywords": _split_focus(meta.get("_yoast_wpseo_focuskw", "")),
                    "readable": True, "focus_readable": True}
        return {"title": meta.get("_seo_title", ""), "description": meta.get("_seo_description", ""),
                "focus_keywords": [], "readable": True, "focus_readable": False}

    def update_meta(self, post_id: int, *, plugin: str, title: Optional[str] = None,
                    description: Optional[str] = None, focus_add: Optional[list[str]] = None,
                    focus_set: Optional[list[str]] = None) -> dict:
        """Read-modify-write that never clobbers unreadable/unset fields.

        title/description: written when provided, or preserved when readable. focus keywords:
        focus_set replaces; focus_add merges (only if current is readable, else SKIPPED with a
        warning). Returns the fields actually written + any warnings.
        """
        if plugin == "none":
            return {"updated": False, "reason": "seo_plugin is 'none'"}

        current = self.get_meta(post_id, plugin=plugin)
        warnings: list[str] = []
        write: set[str] = set()

        final_title = title if title is not None else current["title"]
        if title is not None or current["readable"]:
            write.add("title")
        final_desc = description if description is not None else current["description"]
        if description is not None or current["readable"]:
            write.add("desc")

        final_focus: list[str] = []
        if focus_set is not None:
            final_focus = focus_set
            write.add("focus")
        elif focus_add:
            if current["focus_readable"]:
                final_focus = _merge_focus(current["focus_keywords"], focus_add)
                write.add("focus")
            else:
                warnings.append("focus_add skipped: existing focus keywords are not readable "
                                "on this site (would clobber). Use --focus-set to replace.")
        elif current["focus_readable"]:
            final_focus = current["focus_keywords"]
            write.add("focus")

        req = seo_router.meta_request(plugin, post_id, final_title, final_desc,
                                      final_focus, post_type=self._post_type)
        if req is None:
            return {"updated": False, "reason": "seo_plugin is 'none'"}

        # Prune any field we must not write so a partial update can't wipe it.
        keymap = _KEYS.get(plugin, {})
        meta_obj = req["payload"].get("meta", {})
        for logical, payload_key in keymap.items():
            if logical not in write and payload_key in meta_obj:
                del meta_obj[payload_key]

        if not meta_obj:
            return {"updated": False, "reason": "nothing to write", "warnings": warnings}

        self._client.request_path(req["method"], req["endpoint"], json=req["payload"])
        result = {"updated": True, "plugin": plugin, "written_fields": sorted(write)}
        if "title" in write:
            result["title"] = final_title
        if "desc" in write:
            result["description"] = final_desc
        if "focus" in write:
            result["focus_keywords"] = final_focus
        if warnings:
            result["warnings"] = warnings
        return result
