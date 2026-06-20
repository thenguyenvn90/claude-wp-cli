"""WordPress Posts REST API client."""
from __future__ import annotations
from typing import Any, Optional
from .http import WPClient, WPAPIError
from . import guards


class PostsClient:
    def __init__(self, client: WPClient, default_status: str = "draft", default_category_ids: Optional[list[int]] = None, default_tag_ids: Optional[list[int]] = None):
        self._client = client
        self._default_status = default_status
        self._default_category_ids = default_category_ids or []
        self._default_tag_ids = default_tag_ids or []

    def list(self, *, status: str = "any", per_page: int = 10, page: int = 1) -> tuple[list[dict], int, int]:
        return self._client.get_list("posts", params={"status": status, "per_page": per_page, "page": page})

    def get(self, post_id: int) -> dict:
        return self._client.get(f"posts/{post_id}")

    def create(self, *, title: str, content: str, status: Optional[str] = None, date: Optional[str] = None, category_ids: Optional[list[int]] = None, tag_ids: Optional[list[int]] = None, featured_media: Optional[int] = None, meta: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {"title": title, "content": content, "status": status or self._default_status}
        if date is not None:
            payload["date"] = date
        cats = category_ids if category_ids is not None else self._default_category_ids
        if cats:
            payload["categories"] = cats
        tags = tag_ids if tag_ids is not None else self._default_tag_ids
        if tags:
            payload["tags"] = tags
        if featured_media is not None:
            payload["featured_media"] = featured_media
        if meta:
            payload["meta"] = meta
        return self._client.post("posts", json=payload)

    def update(self, post_id: int, *, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None, date: Optional[str] = None, featured_media: Optional[int] = None, meta: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if status is not None:
            payload["status"] = status
        if date is not None:
            payload["date"] = date
        if featured_media is not None:
            payload["featured_media"] = featured_media
        if meta is not None:
            payload["meta"] = meta
        return self._client.post(f"posts/{post_id}", json=payload)

    def delete(self, post_id: int, *, force: bool = False) -> dict:
        params = {"force": "true"} if force else {}
        return self._client.delete(f"posts/{post_id}", params=params)

    def revisions(self, post_id: int) -> list[dict]:
        return self._client.get(f"posts/{post_id}/revisions")

    # ----------------------------------------------------------------- #
    # Safe publish path (parity with the kit's wp_push_safe guards)
    # ----------------------------------------------------------------- #

    def fetch_live(self, post_id: int, *, post_type: str = "posts") -> dict:
        """Fetch live post with raw content + meta (the fetch-before-edit rule)."""
        return self._client.get(
            f"{post_type}/{post_id}",
            params={"context": "edit", "_fields": "id,slug,status,modified,content,title"},
        )

    def verify_slug(self, post_id: int, expected_slug: str, *, post_type: str = "posts") -> tuple[bool, str, str]:
        """GET the post and confirm its slug matches. Returns (ok, actual_slug, message)."""
        try:
            data = self._client.get(f"{post_type}/{post_id}", params={"_fields": "id,slug"})
        except WPAPIError as e:
            if e.http_status == 404:
                return False, "", f"POST NOT FOUND: {post_type}/{post_id} (HTTP 404)"
            return False, "", f"HTTP {e.http_status}: {e.code}"
        actual = data.get("slug", "")
        if actual == expected_slug:
            return True, actual, "slug matches"
        return False, actual, (
            f"SLUG MISMATCH: {post_type}/{post_id} has slug '{actual}', expected "
            f"'{expected_slug}'. Refusing push to prevent cross-corruption."
        )

    def check_drift(self, post_id: int, content_html: str, *, post_type: str = "posts",
                    threshold_pct: float = 2.0) -> tuple[bool, str, dict]:
        """Compare live char count vs local. Returns (ok, message, report). Bands match the kit."""
        try:
            data = self._client.get(f"{post_type}/{post_id}", params={"context": "edit",
                                                                       "_fields": "id,content,modified,status"})
        except WPAPIError as e:
            return False, f"HTTP {e.http_status}: drift check failed", {}
        live = (data.get("content") or {}).get("raw") or (data.get("content") or {}).get("rendered", "")
        local_chars, live_chars = len(content_html), len(live)
        drift = live_chars - local_chars
        drift_pct = (abs(drift) / max(local_chars, 1)) * 100
        report = {"local_chars": local_chars, "live_chars": live_chars, "drift": drift,
                  "drift_pct": round(drift_pct, 2), "live_modified": data.get("modified"),
                  "live_status": data.get("status")}
        if drift_pct < 0.5:
            return True, f"drift OK ({drift:+d} chars, {drift_pct:.2f}%)", report
        if drift_pct < threshold_pct:
            return True, f"drift minor ({drift:+d} chars, {drift_pct:.2f}%) within threshold", report
        if drift_pct < 10.0:
            return False, (f"DRIFT SIGNIFICANT: live {drift:+d} chars vs local ({drift_pct:.2f}%). "
                           "External edits detected; reconcile then re-push with allow_drift."), report
        return False, (f"DRIFT MAJOR: live {drift:+d} chars vs local ({drift_pct:.2f}%). "
                       "REFUSING to avoid overwriting external work; back up live first."), report

    def push_safe(self, post_id: int, content_html: str, *, expected_slug: Optional[str] = None,
                  force: bool = False, strip_emdash: bool = True, check_drift_enabled: bool = True,
                  allow_drift: bool = False, status: Optional[str] = None,
                  post_type: str = "posts", expected_modified: Optional[str] = None) -> dict:
        """Guarded content push. Returns a structured result; never raises on a guard refusal.

        Order: slug-guard -> em-dash strip -> drift check -> stale-edit (modified) check ->
        markdown-leak -> meta-comment strip -> POST -> post-write slug re-verify. Mirrors the
        kit's wp_push_safe.push_content behavior.

        expected_modified: the `modified` timestamp captured at fetch-time. If the live post's
        `modified` changed since then, an external edit landed in between — refuse so concurrent
        editorial work is never silently overwritten (closes the TOCTOU window a char-count-only
        drift check misses).
        """
        if expected_slug:
            ok, _actual, msg = self.verify_slug(post_id, expected_slug, post_type=post_type)
            if not ok:
                return {"pushed": False, "refused": msg}

        em_count = 0
        if strip_emdash:
            content_html, em_count = guards.strip_em_dashes(content_html)

        if check_drift_enabled and not allow_drift:
            ok, msg, _report = self.check_drift(post_id, content_html, post_type=post_type)
            if not ok:
                return {"pushed": False, "refused": msg}

        # Stale-edit guard (TOCTOU): refuse if the post changed since it was fetched, even when
        # the char-count drift looks small (equal-length external edits would slip through otherwise).
        if expected_modified and not allow_drift:
            try:
                cur = self._client.get(f"{post_type}/{post_id}",
                                       params={"context": "edit", "_fields": "id,modified"})
            except WPAPIError as e:
                return {"pushed": False, "refused": f"could not re-check 'modified' before push: {e}"}
            live_modified = cur.get("modified")
            if live_modified and live_modified != expected_modified:
                return {"pushed": False, "refused": (
                    f"stale edit: post was modified at {live_modified} after you fetched it "
                    f"({expected_modified}). Re-fetch + reconcile, or pass allow_drift to override.")}

        fails = guards.detect_md_leak(content_html)
        if fails and not force:
            return {"pushed": False, "refused": (
                f"raw-markdown leak detected: {fails}. Convert markdown to HTML first, "
                "or pass force=True if intentional.")}

        # strip the leading "Meta description:" artifact AND any body <h1> (WP renders the title
        # as the page H1 — a body H1 is a duplicate). Matches the kit's legacy push behavior.
        payload: dict[str, Any] = {"content": guards.strip_body_h1(guards.strip_meta_comment(content_html))}
        if status:
            payload["status"] = status
        data = self._client.post(f"{post_type}/{post_id}", json=payload)

        result: dict[str, Any] = {
            "pushed": True, "id": data.get("id"), "modified": data.get("modified"),
            "link": data.get("link"), "status": data.get("status"),
            "em_dashes_stripped": em_count,
        }
        # Post-write confirmation: re-verify the slug we just wrote is the one we intended, so a
        # wrong --id is detectable after the fact (CWE-807 — don't blindly trust the write target).
        if expected_slug:
            ok, actual, _msg = self.verify_slug(post_id, expected_slug, post_type=post_type)
            result["slug_verified"] = ok
            if not ok:
                result["warning"] = f"post-write slug check: expected {expected_slug!r}, got {actual!r}"
        return result
